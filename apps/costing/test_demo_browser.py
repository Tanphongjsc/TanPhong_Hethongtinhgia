"""Golden DEMO data through the actual Vietnamese HTMX run form and drawers."""
import os
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from apps.core.models import Organization, CostingRun
from .demo_data import seed_demo
from .demo_verification import reconcile
from .run_test_data import cleanup


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright.")
class DemoBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        Organization.objects.create(code="EXISTING", name="Công ty có sẵn")
        self.demo = seed_demo()

    def tearDown(self):
        # Existing helper is strictly guarded for the isolated localhost test DB.
        cleanup()
        super().tearDown()

    def test_golden_demo_form_htmx_trace_snapshot_and_responsive(self):
        from playwright.sync_api import expect, sync_playwright
        r = self.demo.records
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/costing/runs/create/")
            page.locator("#id_costing_date").fill("2026-10-07")
            page.locator("#id_product").select_option(str(r["product"].pk))
            expect(page.locator("#id_sku")).to_contain_text("Cappuccino 20 gói / hộp")
            page.locator("#id_sku").select_option(str(r["sku"].pk))
            page.locator("#id_scheme").select_option(str(r["scheme"].pk))
            expect(page.locator("#id_packaging_quantity")).to_be_visible()
            page.locator("#id_quantity").fill("10")
            page.locator("#id_quantity_uom").select_option(str(r["box"].pk))
            page.locator("#id_result_currency_code").select_option("VND")
            page.locator("#id_packaging_quantity").fill("1")
            page.locator("#id_packaging_uom").select_option(str(r["box"].pk))
            page.get_by_role("button", name="Chạy tính giá", exact=True).click()
            expect(page.locator("#run-detail")).to_contain_text("583.000 VND")
            expect(page.locator("#run-detail")).to_contain_text("58.300 VND")
            page.screenshot(path=str(screenshots / "demo-golden-desktop.png"), full_page=True)
            page.locator("tr").filter(has_text="DEMO_RESOURCE_COST").get_by_role("link", name="Nguồn dữ liệu / Diễn giải").click()
            dialog = page.get_by_role("dialog", name="Chi phí nguồn lực", exact=True)
            expect(dialog).to_contain_text("DEMO_MIXER")
            expect(dialog).to_contain_text("DEMO_PACKING_LABOR")
            expect(dialog).to_contain_text("Quy đổi đơn vị")
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
            page.get_by_role("link", name="Xem dữ liệu và phiên bản đã sử dụng", exact=True).click()
            expect(page.locator("#run-snapshot")).to_contain_text("DEMO_FULL_FORMULA")
            expect(page.locator("#run-snapshot")).to_contain_text("DEMO_DIRECT_FORMULA")
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
            page.screenshot(path=str(screenshots / "demo-golden-mobile.png"), full_page=True)
            self.assertEqual(errors, [])
            self.assertNotIn("sessionid", {cookie["name"] for cookie in page.context.cookies()})
            browser.close()
        reconcile(self.demo, CostingRun.objects.get())
