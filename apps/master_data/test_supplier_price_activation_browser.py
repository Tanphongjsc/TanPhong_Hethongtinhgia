"""Real confirmation/CSRF path on isolated localhost PostgreSQL."""
import os
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Currency, Item, Organization, Supplier, SupplierPrice, Uom, UomCategory


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Opt-in Chromium test.")
class SupplierPriceActivationBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        company = Organization.objects.create(code="PRICE_BROWSER", name="Công ty kiểm thử")
        currency = Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
        category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        kg = Uom.objects.create(category=category, code="KG", name="Kilôgam", symbol="kg")
        self.supplier = Supplier.objects.create(organization=company, code="SUP", name="Nhà cung cấp")
        item = Item.objects.create(organization=company, code="SUGAR", name="Đường", item_type="RAW_MATERIAL", base_uom=kg)
        self.price = SupplierPrice.objects.create(organization=company, supplier=self.supplier, item=item,
            currency_code=currency, price_uom=kg, unit_price=19200, effective_from=timezone.localdate())
        setting = override_settings(DEFAULT_ORGANIZATION_ID=company.pk)
        setting.enable()
        self.addCleanup(setting.disable)
        self.url = reverse("master_data:supplier_price_detail", args=[self.price.pk])

    def tearDown(self):
        for model in (SupplierPrice, Supplier, Item, Uom, UomCategory, Currency, Organization):
            model.objects.all().delete()
        super().tearDown()

    def test_cancel_then_activate_and_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + self.url)
            activate = page.get_by_role("button", name="Kích hoạt giá", exact=True)
            activate.click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_be_visible()
            dialog.get_by_role("button", name="Hủy", exact=True).click()
            expect(dialog).not_to_be_visible()
            expect(activate).to_be_visible()
            activate.click()
            dialog.get_by_role("button", name="Xác nhận kích hoạt", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã kích hoạt giá nhà cung cấp.")
            expect(activate).to_have_count(0)
            expect(page.locator("#reference-data-detail")).to_contain_text("19.200 VND")
            page.set_viewport_size({"width": 390, "height": 844})
            page.reload()
            expect(page.locator("#reference-data-detail")).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            folder = Path(settings.BASE_DIR) / "artifacts" / "supplier-price-activation"
            folder.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(folder / "activated-mobile.png"), full_page=True)
            browser.close()
        self.price.refresh_from_db()
        self.assertEqual(self.price.status, "EFFECTIVE")
        self.assertEqual(errors, [])

    def test_activation_error_visible_and_draft_preserved(self):
        from playwright.sync_api import expect, sync_playwright
        Supplier.objects.filter(pk=self.supplier.pk).update(is_active=False)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.goto(self.live_server_url + self.url)
            page.get_by_role("button", name="Kích hoạt giá", exact=True).click()
            page.get_by_role("button", name="Xác nhận kích hoạt", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("Không thể chọn nhà cung cấp đã ngừng hoạt động.")
            expect(page.get_by_role("button", name="Kích hoạt giá", exact=True)).to_be_visible()
            browser.close()
        self.price.refresh_from_db()
        self.assertEqual(self.price.status, "DRAFT")
