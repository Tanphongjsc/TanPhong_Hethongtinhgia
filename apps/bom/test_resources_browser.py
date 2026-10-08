"""Real browser CRUD, CSRF, HTMX and history checks on isolated localhost."""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections
from django.utils import timezone

from apps.core.models import Currency, Organization, Resource, ResourceRate, Uom, UomCategory, WorkCenter


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class ProductionResourceBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="RESOURCE_BROWSER", name="Công ty nội bộ")
        self.currency = Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
        category = UomCategory.objects.create(code="TIME", name="Thời gian", dimension_code="TIME")
        self.hour = Uom.objects.create(category=category, code="H", name="Giờ", symbol="h")
        self.today = timezone.localdate().isoformat()

    def tearDown(self):
        for model in (ResourceRate, Resource, WorkCenter, Uom, UomCategory, Currency, Organization):
            model.objects.all().delete()
        super().tearDown()

    def pagination_data(self, resource_pk):
        try:
            ResourceRate.objects.bulk_create([ResourceRate(organization_id=self.company.pk, resource_id=resource_pk,
                rate_type="OPERATING", amount=i + 1, currency_code_id=self.currency.pk,
                per_uom_id=self.hour.pk, effective_from=self.today) for i in range(31)])
        finally:
            connections.close_all()

    def test_three_slices_history_htmx_and_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/bom/work-centers/")
            expect(page.locator("h1")).to_have_text("Trung tâm sản xuất")
            expect(page.locator("tbody")).to_contain_text("Chưa có trung tâm sản xuất.")
            expect(page.locator('a[aria-current="page"]')).to_have_text("Trung tâm sản xuất")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            page.get_by_role("button", name="Lưu trung tâm sản xuất", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã trung tâm sản xuất.")
            expect(page.locator("#id_code")).to_have_attribute("aria-invalid", "true")
            page.locator("#id_code").fill(" wc_mixing ")
            page.locator("#id_name").fill("Khu vực trộn")
            page.locator("#id_site_code").fill("SITE_A")
            page.locator("#id_capacity_value").fill("40")
            page.locator("#id_normal_capacity_value").fill("30")
            page.locator("#id_capacity_uom").select_option(str(self.hour.pk))
            page.get_by_role("button", name="Lưu trung tâm sản xuất", exact=True).click()
            expect(page.locator("#production-detail")).to_contain_text("WC_MIXING")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo trung tâm sản xuất.")
            center_pk = int(page.url.rstrip("/").split("/")[-1])

            page.goto(self.live_server_url + "/bom/resources/create/")
            expect(page.locator("#id_organization")).to_have_count(0)
            expect(page.locator("#id_work_center option")).to_contain_text(["---------", "WC_MIXING — Khu vực trộn"])
            page.locator("#id_code").fill(" mixer_01 ")
            page.locator("#id_name").fill("Máy trộn số 1")
            page.locator("#id_resource_type").select_option("MACHINE")
            page.locator("#id_work_center").select_option(str(center_pk))
            page.locator("#id_capacity_value").fill("1.12345678")
            page.locator("#id_capacity_uom").select_option(str(self.hour.pk))
            page.get_by_role("button", name="Lưu nguồn lực sản xuất", exact=True).click()
            expect(page.locator("#production-detail")).to_contain_text("Máy móc")
            expect(page.locator("#rate-history-title")).to_have_text("Lịch sử đơn giá")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo nguồn lực.")
            resource_pk = int(page.url.rstrip("/").split("/")[-1])
            page.get_by_role("link", name="Thêm đơn giá", exact=True).first.click()
            expect(page.locator("#id_resource")).to_have_value(str(resource_pk))
            page.get_by_role("button", name="Lưu đơn giá nguồn lực", exact=True).click()
            expect(page.locator("#id_amount_errors")).to_contain_text("Vui lòng nhập đơn giá.")
            page.locator("#id_rate_type").fill("OPERATING")
            page.locator("#id_amount").fill("250000.12345678")
            page.locator("#id_currency_code").select_option("VND")
            page.locator("#id_per_uom").select_option(str(self.hour.pk))
            page.locator("#id_effective_from").fill(self.today)
            page.locator("#id_effective_to").fill(self.today)
            page.get_by_role("button", name="Lưu đơn giá nguồn lực", exact=True).click()
            expect(page.locator("#id_effective_to_errors")).to_contain_text("phải sau ngày bắt đầu")
            expect(page.locator("#id_amount")).to_have_value("250000.12345678")
            page.locator("#id_effective_to").fill("")
            page.locator("#id_source_reference").fill("BG-2026")
            page.get_by_role("button", name="Lưu đơn giá nguồn lực", exact=True).click()
            expect(page.locator("#production-detail")).to_contain_text("250.000,12345678 VND / Giờ")
            expect(page.locator("#production-detail")).to_contain_text("Nháp")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo đơn giá nguồn lực.")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            expect(page.locator("#reference-data-form-content")).to_contain_text("hãy thêm bản ghi mới")
            page.locator("#id_amount").fill("230000")
            page.get_by_role("button", name="Lưu đơn giá nguồn lực", exact=True).click()
            expect(page.locator("#production-detail")).to_contain_text("230.000 VND / Giờ")
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật đơn giá nguồn lực.")

            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(self.pagination_data, resource_pk).result()
            page.goto(self.live_server_url + f"/bom/resources/{resource_pk}/")
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(7)
            expect(page.locator("#rate-history-title")).to_be_visible()
            page.locator("#table-sort").select_option("-rate")
            expect(page).to_have_url(re.compile(r".*sort=-rate.*"))
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(25)
            page.go_back()
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            expect(page.locator("#reference-data-table tbody tr")).to_have_count(7)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(screenshots / "resource-history-desktop.png"), full_page=True)

            page.goto(self.live_server_url + "/bom/resource-rates/")
            expect(page.locator('a[aria-current="page"]')).to_have_text("Đơn giá nguồn lực")
            page.locator("#reference-data-search").fill("mixer")
            expect(page).to_have_url(re.compile(r".*q=mixer.*"))
            page.locator("#filter-work_center").select_option(str(center_pk))
            expect(page).to_have_url(re.compile(r".*work_center=\d+.*"))
            page.locator("#filter-effective").select_option("EFFECTIVE")
            expect(page).to_have_url(re.compile(r".*effective=EFFECTIVE.*"))
            page.locator("#page-size").select_option("50")
            expect(page).to_have_url(re.compile(r".*per_page=50.*"))
            expect(page.locator("tbody tr")).to_have_count(32)
            expect(page.locator("#reference-data-filters input[name=per_page]")).to_have_value("50")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(screenshots / "resource-rates-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator("h1")).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            page.screenshot(path=str(screenshots / "resource-rates-mobile.png"), full_page=True)
            page.goto(self.live_server_url + f"/bom/resources/{resource_pk}/")
            expect(page.locator("#rate-history-title")).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            self.assertFalse(any(cookie["name"] == "sessionid" for cookie in page.context.cookies()))
            browser.close()
        self.assertEqual(errors, [])
