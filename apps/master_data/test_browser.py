"""Opt-in browser check against the isolated PostgreSQL test fixtures."""
import os
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from apps.core.models import CostElement, CostElementGroup, Currency, Organization, Uom, UomCategory


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class CostElementBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.organization = Organization.objects.create(code="BROWSER_ORG", name="Công ty kiểm thử")
        self.currency = Currency.objects.create(code="VND", name="Việt Nam đồng")
        category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        self.uom = Uom.objects.create(code="KG", name="Kilogram", symbol="kg", category=category)
        self.group = CostElementGroup.objects.create(organization=self.organization, code="MATERIAL", name="Nguyên liệu", category_code="MATERIAL")
        CostElement.objects.bulk_create([CostElement(organization=self.organization, group=self.group, code=f"COST_{i:03}", name=f"Chi phí {i:03}", value_type="MONEY", default_source_mode="MANUAL", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING", currency_code=self.currency) for i in range(31)])

    def tearDown(self):
        for model in (CostElement, CostElementGroup, Organization, Uom, UomCategory, Currency):
            model.objects.all().delete()
        super().tearDown()

    def test_browser_cost_element_flow_and_responsive_shell(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/")
            expect(page).to_have_url(self.live_server_url + "/master-data/cost-elements/")
            expect(page.locator("#organization-switch")).to_have_count(0)
            expect(page.get_by_role("button", name="Đăng xuất", exact=True)).to_have_count(0)
            self.assertNotIn("sessionid", {cookie["name"] for cookie in page.context.cookies()})
            expect(page.locator("tbody tr")).to_have_count(25)
            expect(page.locator("#workspace-sidebar")).to_have_css("width", "240px")
            page.screenshot(path=str(screenshots / "cost-elements-desktop.png"), full_page=True)
            page.get_by_role("button", name="Đóng hoặc mở thanh điều hướng").click()
            expect(page.locator("#workspace-sidebar")).to_have_css("width", "72px")
            page.get_by_role("button", name="Mở dữ liệu danh mục").click()
            expect(page.locator("#workspace-sidebar")).to_have_css("width", "240px")

            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(6)
            self.assertIn("page=2", page.url)
            page.go_back()
            expect(page.locator("tbody tr")).to_have_count(25)
            page.locator("#page-size").select_option("50")
            expect(page.locator("tbody tr")).to_have_count(31)
            page.locator("#cost-element-search").fill("COST_007")
            expect(page.locator("tbody tr")).to_have_count(1)
            expect(page.locator("tbody")).to_contain_text("COST_007")
            self.assertIn("q=COST_007", page.url)
            self.assertIn("per_page=50", page.url)
            page.reload()
            expect(page.locator("#cost-element-search")).to_have_value("COST_007")
            page.get_by_role("link", name="Đặt lại", exact=True).click()
            page.locator("#table-sort").select_option("-code")
            expect(page.locator("tbody tr").first).to_contain_text("COST_030")
            expect(page.locator('#cost-element-filters input[name="sort"]')).to_have_value("-code")
            page.locator("#filter-active").select_option("false")
            expect(page.locator("tbody")).to_contain_text("Không có kết quả phù hợp.")
            self.assertIn("sort=-code", page.url)
            page.get_by_role("link", name="Đặt lại", exact=True).click()

            page.get_by_role("link", name="+ Thêm mới", exact=True).click()
            page.get_by_role("button", name="Lưu phần tử chi phí").click()
            expect(page.get_by_role("alert").filter(has_text="Không thể lưu phần tử chi phí.")).to_be_visible()
            page.locator("#id_code").fill(" browser_cost ")
            page.locator("#id_name").fill(" Chi phí browser ")
            page.locator("#id_group").select_option(str(self.group.pk))
            page.locator("#id_value_type").select_option("MONEY")
            page.locator("#id_default_source_mode").select_option("MANUAL")
            page.locator("#id_currency_code").select_option("VND")
            page.locator("#id_default_uom").select_option(str(self.uom.pk))
            page.locator("#id_rounding_scale").fill("0")
            page.get_by_role("button", name="Lưu phần tử chi phí").click()
            expect(page.locator("#cost-element-detail")).to_contain_text("BROWSER_COST")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo phần tử chi phí.")
            page.get_by_role("button", name="Thao tác khác", exact=True).click()
            page.get_by_role("button", name="Thông tin bản ghi", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.keyboard.press("Tab")
            self.assertTrue(page.get_by_role("dialog").evaluate("dialog => dialog.contains(document.activeElement)"))
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog")).not_to_be_visible()
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_name").fill("Chi phí đã cập nhật")
            page.locator("#id_is_active").uncheck()
            page.get_by_role("button", name="Lưu phần tử chi phí").click()
            expect(page.get_by_role("dialog")).to_be_visible()
            expect(page.get_by_role("dialog")).to_contain_text("BROWSER_COST")
            page.keyboard.press("Tab")
            self.assertTrue(page.get_by_role("dialog").evaluate("dialog => dialog.contains(document.activeElement)"))
            page.get_by_role("button", name="Hủy", exact=True).click()
            expect(page.get_by_role("dialog")).not_to_be_visible()
            page.get_by_role("button", name="Lưu phần tử chi phí").click()
            page.get_by_role("button", name="Xác nhận và lưu", exact=True).click()
            expect(page.locator("h1")).to_have_text("Chi phí đã cập nhật")
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật phần tử chi phí.")

            for width in (1100, 800, 390):
                page.set_viewport_size({"width": width, "height": 844})
                page.goto(self.live_server_url + "/master-data/cost-elements/")
                self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
                if width < 992:
                    page.get_by_role("button", name="Đóng hoặc mở thanh điều hướng").click()
                    expect(page.locator("#workspace-sidebar[inert]")).to_have_count(0)
                    page.keyboard.press("Escape")
                    expect(page.locator("#workspace-sidebar[inert]")).to_have_count(1)
                page.screenshot(path=str(screenshots / f"cost-elements-{width}.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
