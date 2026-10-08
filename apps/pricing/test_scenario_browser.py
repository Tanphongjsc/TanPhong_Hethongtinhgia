import os
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from apps.core.models import Organization, PriceScenario
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import create_golden_run
from apps.costing.run_test_data import cleanup
from .demo_scenario import verify_pricing_demo


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright.")
class PricingScenarioBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        cleanup()
        Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        self.demo = seed_demo()
        self.costing_run = create_golden_run(self.demo)
        verify_pricing_demo()

    def tearDown(self):
        cleanup()
        super().tearDown()

    def test_real_create_dependent_fields_calculate_waterfall_history_and_mobile(self):
        from playwright.sync_api import sync_playwright, expect
        folder = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, locale="vi-VN")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(self.live_server_url + "/pricing/scenarios/create/")
            page.locator("#id_code").fill("BROWSER_PRICING")
            page.locator("#id_name").fill("Giá bán kiểm thử trình duyệt")
            page.locator("#id_product").select_option(str(self.costing_run.product_id))
            expect(page.locator(f'#id_sku option[value="{self.costing_run.sku_id}"]')).to_have_count(1)
            page.locator("#id_sku").select_option(str(self.costing_run.sku_id))
            expect(page.locator(f'#id_base_run option[value="{self.costing_run.pk}"]')).to_have_count(1)
            page.locator("#id_base_run").select_option(str(self.costing_run.pk))
            page.locator("#id_channel").select_option(label="DEMO_DIRECT — Kênh bán trực tiếp mẫu")
            expect(page.locator("#id_currency_code")).to_have_value("VND")
            expect(page.locator("#id_jurisdiction_code")).to_have_value("VN")
            page.locator("#id_pricing_date").fill("2026-10-08")
            page.locator("#id_target_margin").fill("100")
            page.get_by_role("button", name="Lưu Nháp", exact=True).click()
            expect(page.locator("#id_target_margin_errors")).not_to_be_empty()
            page.locator("#id_target_margin").fill("20")
            page.get_by_role("button", name="Lưu Nháp", exact=True).click()
            expect(page.locator("#scenario-detail-content")).to_contain_text("BROWSER_PRICING")
            page.get_by_role("button", name="Tính giá bán", exact=True).click()
            expect(page.locator("#scenario-detail-content")).to_contain_text("Cấu thành giá bán")
            expect(page.locator("#scenario-detail-content")).to_contain_text("89.972,4137931")
            expect(page.locator("#toast-root")).to_contain_text("Đã lưu kết quả giá bán.")
            expect(page.get_by_role("link", name="Chỉnh sửa", exact=True)).to_have_count(0)
            page.get_by_text("Nguồn và diễn giải đã lưu", exact=True).click()
            expect(page.locator("#scenario-detail-content")).to_contain_text("Hoa hồng")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(folder / "pricing-scenario-desktop.png"), full_page=True)
            page.get_by_role("link", name="Quay lại danh sách", exact=True).click()
            page.locator('#scenario-search').fill("BROWSER_PRICING")
            expect(page.locator("#pricing-scenarios-table tbody tr")).to_have_count(1)
            expect(page).to_have_url(__import__("re").compile("q=BROWSER_PRICING"))
            page.locator("#table-sort").select_option("code")
            expect(page).to_have_url(__import__("re").compile("sort=code"))
            page.go_back()
            expect(page.locator('#scenario-search')).to_have_value("BROWSER_PRICING")
            page.set_viewport_size({"width": 390, "height": 844})
            page.reload()
            expect(page.locator("tbody")).to_contain_text("BROWSER_PRICING")
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            page.screenshot(path=str(folder / "pricing-scenario-mobile.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
        self.assertEqual(PriceScenario.objects.get(code="BROWSER_PRICING").status, "CALCULATED")
