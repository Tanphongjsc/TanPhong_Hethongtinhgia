"""Opt-in end-to-end coverage using local test data and local JS/CSS assets."""
import os
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from apps.core.models import Currency, Item, Organization, ProductCategory, Uom, UomCategory, UomConversion


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class ReferenceDataBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.organization = Organization.objects.create(code="BROWSER_REF", name="Công ty kiểm thử danh mục")
        Currency.objects.bulk_create([Currency(code=f"T{chr(65 + i // 26)}{chr(65 + i % 26)}", name=f"Currency {i:03}") for i in range(31)])
        self.category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        self.kg = Uom.objects.create(category=self.category, code="KG", name="Kilogram", symbol="kg")
        self.gram = Uom.objects.create(category=self.category, code="G", name="Gram", symbol="g")
        self.item = Item.objects.create(organization=self.organization, code="MATERIAL", name="Nguyên liệu", item_type="RAW_MATERIAL", base_uom=self.kg)

    def tearDown(self):
        for model in (UomConversion, Item, ProductCategory, Uom, UomCategory, Currency, Organization):
            model.objects.all().delete()
        super().tearDown()

    def test_reference_crud_htmx_history_and_responsive_pages(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/master-data/currencies/")
            expect(page.locator("tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(6)
            page.go_back()
            expect(page.locator("tbody tr")).to_have_count(25)
            page.locator("#page-size").select_option("50")
            expect(page.locator("tbody tr")).to_have_count(31)
            page.locator("#reference-data-search").fill("TAA")
            expect(page.locator("tbody tr")).to_have_count(1)
            self.assertIn("q=TAA", page.url)
            page.reload()
            expect(page.locator("#reference-data-search")).to_have_value("TAA")
            page.get_by_role("link", name="Đặt lại", exact=True).click()
            page.locator("#table-sort").select_option("-name")
            expect(page.locator("tbody tr").first).to_contain_text("Currency 030")
            expect(page.locator('#reference-data-filters input[name="sort"]')).to_have_value("-name")
            page.locator("#filter-active").select_option("false")
            expect(page.locator("tbody")).to_contain_text("Không có kết quả phù hợp.")
            self.assertIn("sort=-name", page.url)
            page.get_by_role("link", name="Đặt lại", exact=True).click()
            page.screenshot(path=str(screenshots / "currencies-desktop.png"), full_page=True)

            page.get_by_role("link", name="+ Thêm mới", exact=True).click()
            page.locator("#id_code").fill("eur")
            page.locator("#id_name").fill("Euro")
            page.locator("#id_decimal_places").fill("9")
            page.get_by_role("button", name="Lưu tiền tệ", exact=True).click()
            expect(page.get_by_role("alert").filter(has_text="Không thể lưu tiền tệ.")).to_be_visible()
            expect(page.locator("#id_decimal_places")).to_have_attribute("aria-invalid", "true")
            page.locator("#id_decimal_places").fill("2")
            page.get_by_role("button", name="Lưu tiền tệ", exact=True).click()
            expect(page.locator("#reference-data-detail")).to_contain_text("EUR")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo tiền tệ.")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            expect(page.locator("#id_code")).to_be_disabled()
            page.locator("#id_is_active").uncheck()
            page.get_by_role("button", name="Lưu tiền tệ", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.keyboard.press("Tab")
            self.assertTrue(page.get_by_role("dialog").evaluate("dialog => dialog.contains(document.activeElement)"))
            page.get_by_role("button", name="Xác nhận và lưu", exact=True).click()
            expect(page.locator("#reference-data-detail")).to_contain_text("Ngừng hoạt động")

            page.goto(self.live_server_url + "/master-data/uom-categories/")
            page.get_by_role("link", name="+ Thêm mới", exact=True).click()
            page.locator("#id_code").fill("length")
            page.locator("#id_name").fill("Chiều dài")
            page.locator("#id_dimension_code").fill("length")
            page.get_by_role("button", name="Lưu nhóm đơn vị tính", exact=True).click()
            expect(page.locator("#reference-data-detail")).to_contain_text("LENGTH")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_name").fill("Đơn vị chiều dài")
            page.get_by_role("button", name="Lưu nhóm đơn vị tính", exact=True).click()
            expect(page.locator("h1")).to_have_text("Đơn vị chiều dài")

            page.goto(self.live_server_url + "/master-data/uoms/")
            page.locator("#filter-category").select_option(str(self.category.pk))
            expect(page.locator("tbody tr")).to_have_count(2)
            page.get_by_role("link", name="+ Thêm mới", exact=True).click()
            page.locator("#id_category").select_option(str(self.category.pk))
            page.locator("#id_code").fill("mg")
            page.locator("#id_name").fill("Milligram")
            page.locator("#id_symbol").fill("mg")
            page.get_by_role("button", name="Lưu đơn vị tính", exact=True).click()
            expect(page.locator("#reference-data-detail")).to_contain_text("MG")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_precision").fill("9")
            page.get_by_role("button", name="Lưu đơn vị tính", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật đơn vị tính.")

            page.goto(self.live_server_url + "/master-data/uom-conversions/")
            expect(page.locator("tbody")).to_contain_text("Chưa có quy đổi đơn vị tính.")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            expect(page.locator("#id_organization")).to_have_count(0)
            page.locator("#id_from_uom").select_option(str(self.kg.pk))
            page.locator("#id_to_uom").select_option(str(self.gram.pk))
            page.locator("#id_factor").fill("0")
            page.locator("#id_effective_from").fill("2026-01-01")
            page.get_by_role("button", name="Lưu quy đổi đơn vị tính", exact=True).click()
            expect(page.locator("#id_factor_errors")).to_contain_text("lớn hơn 0")
            page.locator("#id_factor").fill("1000.000000000001")
            page.locator("#id_source_reference").fill("Chứng từ kiểm thử")
            page.get_by_role("button", name="Lưu quy đổi đơn vị tính", exact=True).click()
            expect(page.locator("#reference-data-detail")).to_contain_text("Chứng từ kiểm thử")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            expect(page.locator("#id_effective_from")).to_have_value("2026-01-01")
            page.locator("#id_factor").fill("999.5")
            page.locator("#id_effective_to").fill("2026-12-31")
            page.get_by_role("button", name="Lưu quy đổi đơn vị tính", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật quy đổi đơn vị tính.")
            page.goto(self.live_server_url + "/master-data/uom-conversions/")
            page.locator("#filter-from_uom").select_option(str(self.kg.pk))
            expect(page.locator("tbody tr")).to_have_count(1)
            expect(page.locator("tbody")).to_contain_text("999,5")
            expect(page.locator('#workspace-sidebar a[aria-current="page"]')).to_have_count(1)
            expect(page.locator('#workspace-sidebar a[aria-current="page"]')).to_have_text("Quy đổi đơn vị tính")
            expect(page.locator("#list-loading")).not_to_be_visible()
            page.screenshot(path=str(screenshots / "uom-conversions-desktop.png"), full_page=True)

            for path in ("currencies", "uom-categories", "uoms", "uom-conversions"):
                for width in (1100, 800, 390):
                    page.set_viewport_size({"width": width, "height": 844})
                    page.goto(self.live_server_url + f"/master-data/{path}/")
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (path, width))
                page.screenshot(path=str(screenshots / f"{path}-mobile.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
