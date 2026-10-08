"""Real pool/rule and paginated history UI on isolated local PostgreSQL."""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections
from django.utils import timezone

from apps.core.models import AllocationRule, CostPool, Organization, Uom, UomCategory


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class OverheadBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="OVERHEAD_BROWSER", name="Công ty kiểm thử")
        time = UomCategory.objects.create(code="TIME", name="Thời gian", dimension_code="TIME")
        self.hour = Uom.objects.create(category=time, code="H", name="Giờ", symbol="h")
        self.today = timezone.localdate()

    def tearDown(self):
        for model in (AllocationRule, CostPool, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def pagination_data(self, pool_id):
        try:
            AllocationRule.objects.bulk_create([AllocationRule(organization_id=self.company.pk, pool_id=pool_id, code=f"RULE_{i:03}", name=f"Quy tắc kiểm thử {i}",
                basis_type="UNIT", effective_from=self.today, priority=i) for i in range(31)])
            CostPool.objects.bulk_create([CostPool(organization_id=self.company.pk, code=f"POOL_{i:03}", name=f"Nhóm kiểm thử {i}", pool_type="OTHER") for i in range(31)])
        finally:
            connections.close_all()

    def test_configuration_history_filters_query_state_and_responsive(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/bom/cost-pools/")
            expect(page.locator("h1")).to_have_text("Nhóm chi phí chung")
            expect(page.locator("tbody")).to_contain_text("Chưa có nhóm chi phí chung.")
            expect(page.locator('#workspace-sidebar a[aria-current="page"]')).to_be_visible()
            page.get_by_role("link", name="+ Thêm nhóm chi phí", exact=True).first.click()
            page.get_by_role("button", name="Lưu nhóm chi phí chung", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã nhóm chi phí.")
            page.locator("#id_code").fill(" factory ")
            page.locator("#id_name").fill("Chi phí chung nhà máy")
            page.locator("#id_pool_type").select_option("FACTORY_FIXED")
            page.locator("#id_description").fill("Điện và nhà xưởng")
            page.get_by_role("button", name="Lưu nhóm chi phí chung", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo nhóm chi phí chung.")
            pool_url = page.url
            pool_id = int(pool_url.rstrip("/").split("/")[-1])
            expect(page.locator("#overhead-detail")).to_contain_text("Chi phí cố định nhà máy")
            page.get_by_role("link", name="+ Thêm quy tắc phân bổ", exact=True).first.click()
            expect(page.locator("#id_pool")).to_have_value(str(pool_id))
            page.get_by_role("button", name="Lưu quy tắc phân bổ", exact=True).click()
            expect(page.locator("#id_basis_type_errors")).to_contain_text("Vui lòng chọn tiêu thức phân bổ.")
            page.locator("#id_code").fill(" electricity ")
            page.locator("#id_name").fill("Phân bổ điện theo giờ máy")
            page.locator("#id_basis_type").select_option("MACHINE_HOUR")
            page.locator("#id_basis_uom").select_option(str(self.hour.pk))
            page.locator("#id_priority").fill("100")
            page.locator("#id_effective_to").fill(self.today.isoformat())
            page.get_by_role("button", name="Lưu quy tắc phân bổ", exact=True).click()
            expect(page.locator("#id_effective_to_errors")).to_contain_text("Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực.")
            expect(page.locator("#id_effective_to")).to_have_attribute("aria-invalid", "true")
            expect(page.locator("#id_basis_type")).to_have_value("MACHINE_HOUR")
            page.locator("#id_effective_to").fill("")
            page.get_by_role("button", name="Lưu quy tắc phân bổ", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo quy tắc phân bổ.")
            rule_url = page.url
            expect(page.locator("#overhead-detail")).to_contain_text("Giờ máy")
            expect(page.locator("#overhead-detail")).to_contain_text("Nháp")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_priority").fill("0")
            page.locator("#id_formula_code").fill(" ref_Case ")
            page.get_by_role("button", name="Lưu quy tắc phân bổ", exact=True).click()
            expect(page).to_have_url(rule_url)
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật quy tắc phân bổ.")
            expect(page.locator("#overhead-detail")).to_contain_text("ref_Case")
            page.get_by_role("link", name="Xem nhóm chi phí →", exact=True).click()
            expect(page.locator("#reference-data-table")).to_contain_text("ELECTRICITY")
            page.get_by_role("link", name="+ Thêm quy tắc phân bổ", exact=True).first.click()
            page.locator("#id_code").fill(" electricity ")
            page.locator("#id_name").fill("Quy tắc trùng")
            page.locator("#id_basis_type").select_option("UNIT")
            page.get_by_role("button", name="Lưu quy tắc phân bổ", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Mã quy tắc phân bổ đã tồn tại.")
            page.locator("#id_code").fill("ELECTRICITY_NEXT")
            page.locator("#id_name").fill("Phân bổ điện kỳ tiếp theo")
            page.locator("#id_effective_from").fill((self.today+timedelta(days=30)).isoformat())
            page.get_by_role("button", name="Lưu quy tắc phân bổ", exact=True).click()
            expect(page.locator("#overhead-detail")).to_contain_text("Sắp hiệu lực")
            page.goto(rule_url)
            expect(page.locator("#overhead-detail")).to_contain_text("Giờ máy")
            expect(page.locator("#overhead-detail")).to_contain_text(self.today.strftime("%d/%m/%Y"))
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(self.pagination_data, pool_id).result()
            page.goto(pool_url)
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(8)
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            page.locator("#page-size").select_option("50")
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(33)
            page.locator("#filter-basis_type").select_option("MACHINE_HOUR")
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(1)
            expect(page).to_have_url(re.compile(r".*basis_type=MACHINE_HOUR.*"))
            page.reload()
            expect(page.locator("#filter-basis_type")).to_have_value("MACHINE_HOUR")
            expect(page.locator("#page-size")).to_have_value("50")
            page.screenshot(path=str(screenshots / "cost-pool-detail-desktop.png"))
            page.goto(self.live_server_url + "/bom/allocation-rules/")
            page.locator("#reference-data-search").fill("electricity")
            expect(page.locator("tbody tr")).to_have_count(2)
            expect(page).to_have_url(re.compile(r".*q=electricity.*"))
            page.locator("#filter-pool").select_option(str(pool_id))
            page.locator("#filter-effective").select_option("FUTURE")
            expect(page.locator("tbody tr")).to_have_count(1)
            page.locator("#table-sort").select_option("-priority")
            expect(page).to_have_url(re.compile(r".*sort=-priority.*"))
            page.reload()
            expect(page.locator("#table-sort")).to_have_value("-priority")
            page.screenshot(path=str(screenshots / "allocation-rules-desktop.png"))
            page.goto(self.live_server_url + "/bom/cost-pools/")
            expect(page.locator("tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(7)
            page.locator("#table-sort").select_option("-code")
            expect(page.locator("tbody tr").first).to_contain_text("POOL_030")
            page.locator("#filter-pool_type").select_option("FACTORY_FIXED")
            expect(page.locator("tbody tr")).to_have_count(1)
            page.locator("tbody").get_by_role("link", name=re.compile("^Sửa ")).click()
            page.locator("#id_is_active").uncheck()
            page.get_by_role("button", name="Lưu nhóm chi phí chung", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.get_by_role("button", name="Xác nhận và lưu", exact=True).click()
            expect(page.locator("#overhead-detail")).to_contain_text("Ngừng hoạt động")
            page.goto(self.live_server_url + "/bom/allocation-rules/create/")
            expect(page.locator(f'#id_pool option[value="{pool_id}"]')).to_have_count(0)
            page.goto(rule_url + "edit/")
            expect(page.locator("#id_pool")).to_have_value(str(pool_id))
            for width in (1100, 800, 390):
                page.set_viewport_size({"width": width, "height": 844})
                page.goto(pool_url)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.goto(rule_url + "edit/")
                expect(page.locator("#id_name")).to_be_visible()
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
            page.screenshot(path=str(screenshots / "allocation-rule-form-mobile.png"))
            self.assertFalse(any(cookie["name"] == "sessionid" for cookie in page.context.cookies()))
            browser.close()
        self.assertEqual(errors, [])
