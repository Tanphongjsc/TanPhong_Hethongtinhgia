import os
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from apps.costing.run_test_data import cleanup
from . import test_comparison as fixtures


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright.")
class ComparisonBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        cleanup()
        fixtures.ComparisonTests.setUpTestData.__func__(type(self))

    def tearDown(self):
        cleanup()
        super().tearDown()

    def test_selection_comparison_baseline_search_history_and_mobile(self):
        from playwright.sync_api import sync_playwright, expect
        folder = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        product, sku = str(self.costing_run.product_id), str(self.costing_run.sku_id)
        ids = [str(r.pk) for r in self.rows]
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, locale="vi-VN")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(self.live_server_url + "/pricing/scenarios/compare/")
            page.locator("#filter-product").select_option(product)
            expect(page.locator(f'#filter-sku option[value="{sku}"]')).to_have_count(1)
            page.locator("#filter-sku").select_option(sku)
            expect(page.locator('#comparison-form input[type=checkbox]')).to_have_count(3)
            page.locator(f'#scenario-{ids[0]}').check()
            expect(page.locator(f'#scenario-{ids[0]}')).to_be_checked()
            expect(page.locator("#scenario-comparison")).to_contain_text("Đã chọn 1/5")
            page.locator(f'#scenario-{ids[1]}').check()
            expect(page.locator("#scenario-comparison")).to_contain_text("Đã chọn 2/5")
            page.get_by_role("button", name="So sánh kịch bản", exact=True).click()
            expect(page.locator("#comparison-results")).to_contain_text("89.972,4137931 VND")
            expect(page.locator("#comparison-results")).to_contain_text("+2.553,59126734 VND")
            page.locator(f'#scenario-{ids[2]}').check()
            expect(page.locator('#comparison-results thead th')).to_have_count(4)
            page.locator('#comparison-baseline').select_option(ids[1])
            expect(page.locator("#comparison-results")).to_contain_text("-2.553,59126734 VND")
            page.locator('#comparison-search').fill("KHONG_CO_KET_QUA")
            expect(page.locator('#comparison-form input[type=checkbox]')).to_have_count(0)
            expect(page.locator('#comparison-results thead th')).to_have_count(4)
            page.go_back()
            expect(page.locator('#comparison-search')).to_have_value("")
            expect(page.locator('#comparison-results thead th')).to_have_count(4)
            page.get_by_text("Chi tiết phí, thuế và tỷ giá đã lưu", exact=True).click()
            expect(page.locator('#comparison-results')).to_contain_text("Phí theo cấu hình đã lưu")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(folder / "scenario-comparison-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.reload()
            expect(page.locator('#comparison-results')).to_contain_text("Lợi nhuận")
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            page.screenshot(path=str(folder / "scenario-comparison-mobile.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
