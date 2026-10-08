"""Real HTMX dependent fields, execution, history drawer and responsive UI."""
import os
import re
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from apps.core.models import CostingRun
from .run_test_data import golden_data, seal, cleanup


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright.")
class RunBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.data = golden_data(); seal(self.data)
    def tearDown(self):
        cleanup(); super().tearDown()
    def test_execution_dependent_fields_trace_rerun_filters_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/costing/runs/")
            expect(page.locator("tbody")).to_contain_text("Chưa có lần tính giá thành.")
            page.get_by_role("link", name="+ Chạy tính giá", exact=True).first.click()
            page.locator("#id_costing_date").fill(self.data.day.isoformat())
            page.locator("#id_product").select_option(str(self.data.product.pk))
            expect(page.locator("#id_sku")).to_contain_text("Cà phê đóng hộp")
            page.locator("#id_sku").select_option(str(self.data.sku.pk))
            expect(page.locator("#id_sku")).to_have_value(str(self.data.sku.pk))
            page.locator("#id_scheme").select_option(str(self.data.scheme.pk))
            expect(page.locator("#id_packaging_quantity")).to_be_visible()
            expect(page.locator("#id_packaging_quantity_errors")).to_be_empty()
            page.locator("#id_quantity_uom").select_option(str(self.data.box.pk))
            page.locator("#id_result_currency_code").select_option(self.data.currency.pk)
            page.locator("#id_packaging_quantity").fill("1")
            page.locator("#id_packaging_uom").select_option(str(self.data.box.pk))
            # Invalid POST keeps input and marks the actual field.
            page.locator("#id_quantity").fill("0")
            page.get_by_role("button", name="Chạy tính giá", exact=True).click()
            expect(page.locator("#id_quantity")).to_have_attribute("aria-invalid", "true")
            expect(page.locator("#id_packaging_quantity")).to_have_value("1")
            page.locator("#id_quantity").fill("1")
            page.get_by_role("button", name="Chạy tính giá", exact=True).click()
            expect(page.locator("#run-detail")).to_contain_text("60.000 VND")
            expect(page.locator("#run-lines-table")).to_contain_text("Nguyên vật liệu")
            page.screenshot(path=str(screenshots / "costing-run-desktop.png"), full_page=True)
            page.get_by_role("link", name="Nguồn dữ liệu / Diễn giải", exact=True).first.click()
            dialog = page.get_by_role("dialog", name="Tổng giá thành", exact=True)
            expect(dialog).to_be_visible()
            expect(dialog).to_contain_text("Công thức TOTAL")
            expect(dialog).to_contain_text("60.000")
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
            page.get_by_role("link", name="Xem dữ liệu và phiên bản đã sử dụng", exact=True).click()
            expect(page.locator("#run-snapshot")).to_contain_text("Phiên bản định mức")
            expect(page.locator("#run-snapshot")).to_contain_text("07/10/2026")
            page.get_by_role("link", name="Quay lại kết quả", exact=True).click()
            page.get_by_role("link", name="Tạo lần tính mới", exact=True).click()
            expect(page.locator("#id_packaging_quantity")).to_have_value("1")
            page.locator("#id_quantity").fill("2")
            page.get_by_role("button", name="Chạy tính giá", exact=True).click()
            expect(page.locator("#run-detail")).to_contain_text("120.000 VND")
            page.get_by_role("link", name="Quay lại danh sách", exact=True).click()
            page.locator("#filter-date_from").fill(self.data.day.isoformat())
            page.locator("#filter-date_from").press("Tab")
            expect(page).to_have_url(re.compile(r"date_from=2026-10-07"))
            page.locator("#table-sort").select_option("-total_cost")
            expect(page.locator("#reference-data-table")).to_have_attribute("data-sort", "-total_cost")
            page.locator("#filter-status").select_option("LOCKED")
            expect(page).to_have_url(re.compile(r"(?=.*date_from=2026-10-07)(?=.*status=LOCKED)"))
            expect(page.locator("#reference-data-table")).to_contain_text("2 bản ghi")
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
            page.screenshot(path=str(screenshots / "costing-run-mobile.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
        self.assertEqual(CostingRun.objects.count(), 2)
