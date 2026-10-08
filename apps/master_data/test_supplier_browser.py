"""Browser CRUD and HTMX checks use local assets and isolated PostgreSQL."""
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

from apps.core.models import Currency, Item, Organization, Supplier, SupplierPrice, Uom, UomCategory


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class SupplierBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="SUPPLIER_BROWSER", name="Công ty nội bộ")
        self.currency = Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
        category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        self.kg = Uom.objects.create(category=category, code="KG", name="Kilôgam", symbol="kg")
        self.item = Item.objects.create(organization=self.company, code="COFFEE", name="Cà phê nguyên liệu", item_type="RAW_MATERIAL", base_uom=self.kg)
        self.start = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.end = (timezone.localdate() + timedelta(days=90)).isoformat()

    def tearDown(self):
        for model in (SupplierPrice, Supplier, Item, Uom, UomCategory, Currency, Organization):
            model.objects.all().delete()
        super().tearDown()

    def pagination_data(self, supplier_id):
        try:
            Supplier.objects.bulk_create([Supplier(organization_id=self.company.pk, code=f"TEST_{i:03}", name=f"Nhà cung cấp {i}") for i in range(31)])
            SupplierPrice.objects.bulk_create([SupplierPrice(organization_id=self.company.pk, supplier_id=supplier_id, item_id=self.item.pk,
                price_uom_id=self.kg.pk, currency_code_id=self.currency.pk, unit_price=i + 1, effective_from=self.start) for i in range(31)])
        finally:
            connections.close_all()

    def test_crud_htmx_query_history_and_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/master-data/suppliers/")
            expect(page.locator("h1")).to_have_text("Danh mục nhà cung cấp")
            expect(page.locator("tbody")).to_contain_text("Chưa có nhà cung cấp.")
            expect(page.locator('a[aria-current="page"]')).to_have_text("Nhà cung cấp")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            page.get_by_role("button", name="Lưu nhà cung cấp", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã nhà cung cấp.")
            page.locator("#id_code").fill(" ncc_a ")
            page.locator("#id_name").fill("Nhà cung cấp cà phê")
            page.locator("#id_tax_code").fill("0100000001")
            page.locator("#id_default_currency_code").select_option("VND")
            page.locator("#id_payment_terms").fill("Thanh toán sau 30 ngày")
            page.get_by_role("button", name="Lưu nhà cung cấp", exact=True).click()
            expect(page.locator("#reference-data-detail")).to_contain_text("NCC_A")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo nhà cung cấp.")
            supplier_id = int(page.url.rstrip("/").split("/")[-1])
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_payment_terms").fill("Thanh toán sau 45 ngày")
            page.get_by_role("button", name="Lưu nhà cung cấp", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật nhà cung cấp.")
            expect(page.locator("#reference-data-detail")).to_contain_text("Thanh toán sau 45 ngày")

            page.goto(self.live_server_url + "/master-data/supplier-prices/")
            expect(page.locator("tbody")).to_contain_text("Chưa có giá nhà cung cấp.")
            expect(page.locator('a[aria-current="page"]')).to_have_text("Giá nhà cung cấp")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            page.get_by_role("button", name="Lưu giá nhà cung cấp", exact=True).click()
            expect(page.locator("#id_supplier_errors")).to_contain_text("Vui lòng chọn nhà cung cấp.")
            expect(page.locator("#id_supplier")).to_have_attribute("aria-invalid", "true")
            expect(page.locator("#id_organization")).to_have_count(0)
            page.locator("#id_supplier").select_option(str(supplier_id))
            page.locator("#id_item").select_option(str(self.item.pk))
            page.locator("#id_unit_price").fill("125000.12345678")
            page.locator("#id_currency_code").select_option("VND")
            page.locator("#id_price_uom").select_option(str(self.kg.pk))
            page.locator("#id_min_qty").fill("100")
            page.locator("#id_tax_rate").fill("0.1")
            page.locator("#id_effective_from").fill(self.start)
            page.locator("#id_effective_to").fill(self.start)
            page.get_by_role("button", name="Lưu giá nhà cung cấp", exact=True).click()
            expect(page.locator("#id_effective_to_errors")).to_contain_text("phải sau ngày bắt đầu")
            expect(page.locator("#id_unit_price")).to_have_value("125000.12345678")
            page.locator("#id_effective_to").fill(self.end)
            page.locator("#id_source_reference").fill("BG-2026")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(screenshots / "supplier-price-form-desktop.png"), full_page=True)
            page.get_by_role("button", name="Lưu giá nhà cung cấp", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo giá nhà cung cấp.")
            expect(page.locator("#reference-data-detail")).to_contain_text("125.000,12345678 VND")
            expect(page.locator("#reference-data-detail")).to_contain_text("Nháp")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            expect(page.locator("#reference-data-form-content")).to_contain_text("hãy thêm bản ghi mới")
            page.locator("#id_unit_price").fill("130000")
            page.get_by_role("button", name="Lưu giá nhà cung cấp", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật giá nhà cung cấp.")
            expect(page.locator("#reference-data-detail")).to_contain_text("130.000 VND")

            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(self.pagination_data, supplier_id).result()
            page.goto(self.live_server_url + "/master-data/suppliers/")
            page.locator("#reference-data-search").fill("test")
            expect(page).to_have_url(re.compile(r".*q=test.*"))
            expect(page.locator("tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            expect(page.locator("tbody tr")).to_have_count(6)
            page.screenshot(path=str(screenshots / "suppliers-desktop.png"), full_page=True)

            page.goto(self.live_server_url + "/master-data/supplier-prices/")
            page.locator("#reference-data-search").fill("coffee")
            expect(page).to_have_url(re.compile(r".*q=coffee.*"))
            page.locator("#filter-supplier").select_option(str(supplier_id))
            expect(page).to_have_url(re.compile(r".*supplier=\d+.*"))
            page.locator("#filter-effective").select_option("EFFECTIVE")
            expect(page).to_have_url(re.compile(r".*effective=EFFECTIVE.*"))
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            expect(page.locator("tbody tr")).to_have_count(7)
            page.locator("#table-sort").select_option("-unit_price")
            expect(page).to_have_url(re.compile(r".*sort=-unit_price.*"))
            expect(page.locator("tbody tr")).to_have_count(25)
            page.go_back()
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            expect(page.locator("tbody tr")).to_have_count(7)
            expect(page.locator("#reference-data-search")).to_have_value("coffee")
            page.screenshot(path=str(screenshots / "supplier-prices-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator("h1")).to_be_visible()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            page.screenshot(path=str(screenshots / "supplier-prices-mobile.png"), full_page=True)
            self.assertFalse(any(cookie["name"] == "sessionid" for cookie in page.context.cookies()))
            browser.close()
        self.assertEqual(errors, [])
