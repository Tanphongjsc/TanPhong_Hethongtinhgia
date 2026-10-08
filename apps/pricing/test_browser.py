"""Actual browser CRUD, query-state HTMX, Vietnamese labels and mobile layout."""
import os
import re
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from apps.core.models import Organization, Currency, Channel, ChannelFeeRule, TaxRule, FxRate


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright.")
class PricingBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        Organization.objects.create(code="EXISTING", name="Công ty nội bộ")
        Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
        Currency.objects.create(code="USD", name="Đô la Mỹ", decimal_places=2)

    def tearDown(self):
        for model in (ChannelFeeRule, TaxRule, FxRate, Channel, Currency, Organization): model.objects.all().delete()
        super().tearDown()

    def test_pricing_crud_htmx_history_and_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1000}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/pricing/channels/")
            expect(page.locator("tbody")).to_contain_text("Chưa có kênh bán")
            expect(page.locator('a[aria-current="page"]')).to_have_text("Kênh bán")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            page.locator("#id_code").fill(" direct ")
            page.locator("#id_name").fill("Kênh trực tiếp")
            page.locator("#id_channel_type").select_option("D2C")
            page.locator("#id_default_currency_code").select_option("VND")
            page.get_by_role("button", name="Lưu kênh bán", exact=True).click()
            expect(page.locator("#pricing-detail")).to_contain_text("DIRECT")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo kênh bán.")
            page.goto(self.live_server_url + "/pricing/channel-fee-rules/create/")
            page.locator("#id_channel").select_option(label="DIRECT — Kênh trực tiếp")
            page.locator("#id_fee_type").fill("COMMISSION")
            page.locator("#id_fee_base").fill("LIST_PRICE")
            page.locator("#id_rate").fill("101")
            page.locator("#id_tax_inclusive").select_option("False")
            page.locator("#id_effective_from").fill("2026-01-01")
            page.locator("#id_effective_to").fill("2027-01-01")
            page.get_by_role("button", name="Lưu quy tắc phí kênh", exact=True).click()
            expect(page.locator("#id_rate_errors")).not_to_be_empty()
            page.locator("#id_rate").fill("8")
            page.get_by_role("button", name="Lưu quy tắc phí kênh", exact=True).click()
            expect(page.locator("#pricing-detail")).to_contain_text("8%")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            expect(page.locator("#id_rate")).to_have_value("8")
            page.locator("#id_rate").fill("9")
            page.get_by_role("button", name="Lưu quy tắc phí kênh", exact=True).click()
            expect(page.locator("#pricing-detail")).to_contain_text("9%")
            page.goto(self.live_server_url + "/pricing/channel-fee-rules/")
            page.locator("#reference-data-search").fill("DIRECT")
            expect(page).to_have_url(re.compile(r"q=DIRECT"))
            expect(page.locator("tbody tr")).to_have_count(1)
            page.locator("#filter-status").select_option("DRAFT")
            expect(page).to_have_url(re.compile(r"status=DRAFT"))
            page.locator("#table-sort").select_option("-priority")
            expect(page).to_have_url(re.compile(r"sort=-priority"))
            page.reload()
            expect(page.locator("#filter-status")).to_have_value("DRAFT")
            expect(page.locator("#reference-data-search")).to_have_value("DIRECT")
            page.screenshot(path=str(screenshots / "pricing-fees-desktop.png"), full_page=True)
            page.locator("#reference-data-search").fill("NOT_FOUND")
            expect(page.locator("tbody")).to_contain_text("Không có kết quả phù hợp")
            page.go_back()
            expect(page.locator("tbody")).to_contain_text("DIRECT")
            page.goto(self.live_server_url + "/pricing/fx-rates/create/")
            page.locator("#id_from_currency_code").select_option("USD")
            page.locator("#id_to_currency_code").select_option("VND")
            page.locator("#id_rate").fill("26000.123456789012")
            page.locator("#id_rate_type").fill("SPOT")
            page.locator("#id_source_name").fill("Nguồn nội bộ")
            page.get_by_role("button", name="Lưu tỷ giá", exact=True).click()
            expect(page.locator("#pricing-detail")).to_contain_text("1 USD = 26.000,123456789012 VND")
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(screenshots / "pricing-fx-mobile.png"), full_page=True)
            page.get_by_role("button", name="Đóng hoặc mở thanh điều hướng", exact=True).click()
            expect(page.locator("#workspace-sidebar")).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            self.assertNotIn("sessionid", {cookie["name"] for cookie in page.context.cookies()})
            self.assertEqual(errors, [])
            browser.close()
