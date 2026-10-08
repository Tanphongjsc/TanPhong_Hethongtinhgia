"""Opt-in Product/SKU browser flow using isolated PostgreSQL and local assets."""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections

from apps.core.models import Item, Organization, Product, ProductCategory, Sku, Uom, UomCategory


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class ProductSkuBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="PRODUCT_BROWSER", name="Công ty kiểm thử sản phẩm")
        self.category = ProductCategory.objects.create(organization=self.company, code="CAFE", name="Cà phê")
        mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        count = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        self.kg = Uom.objects.create(category=mass, code="KG", name="Kilôgam", symbol="kg")
        self.g = Uom.objects.create(category=mass, code="G", name="Gam", symbol="g")
        self.pack = Uom.objects.create(category=count, code="PACK", name="Gói", symbol="gói")
        self.item = Item.objects.create(organization=self.company, code="OUTPUT", name="Hàng hóa cà phê", item_type="FINISHED_GOOD", base_uom=self.kg)

    def tearDown(self):
        for model in (Sku, Product, Item, ProductCategory, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def create_pagination_data(self):
        try:
            products = Product.objects.bulk_create([Product(organization_id=self.company.pk, category_id=self.category.pk, code=f"TEST_{i:03}", name=f"Sản phẩm {i:03}", costing_uom_id=self.kg.pk) for i in range(31)])
            Sku.objects.bulk_create([Sku(organization_id=self.company.pk, product_id=record.pk, code=f"TEST_{i:03}", name=f"Quy cách {i:03}", sales_uom_id=self.pack.pk, net_quantity="25", net_quantity_uom_id=self.g.pk) for i, record in enumerate(products)])
        finally:
            connections.close_all()

    def test_product_sku_crud_htmx_history_and_responsive(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/product/products/")
            expect(page.locator("h1")).to_have_text("Danh mục sản phẩm")
            expect(page.locator("tbody")).to_contain_text("Chưa có sản phẩm.")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            page.get_by_role("button", name="Lưu sản phẩm", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã sản phẩm.")
            expect(page.locator("#id_costing_uom")).to_have_attribute("aria-invalid", "true")
            page.locator("#id_category").select_option(str(self.category.pk))
            page.locator("#id_code").fill(" cappuccino ")
            page.locator("#id_name").fill("Cà phê Cappuccino")
            page.locator("#id_description").fill("Cà phê hòa tan")
            page.locator("#id_costing_uom").select_option(str(self.kg.pk))
            page.locator("#id_output_item").select_option(str(self.item.pk))
            page.locator("#id_tax_class_code").fill("VAT")
            page.get_by_role("button", name="Lưu sản phẩm", exact=True).click()
            expect(page.locator("#product-detail")).to_contain_text("CAPPUCCINO")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo sản phẩm.")
            product_id = int(page.url.rstrip("/").split("/")[-1])
            product_url = page.url
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_name").fill("Cà phê Cappuccino mới")
            page.get_by_role("button", name="Lưu sản phẩm", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật sản phẩm.")
            page.goto(self.live_server_url + "/product/products/")
            page.locator("#reference-data-search").fill("cappuccino")
            expect(page).to_have_url(re.compile(r".*q=cappuccino.*"))
            expect(page.locator("tbody tr")).to_have_count(1)
            page.locator("#filter-category").select_option(str(self.category.pk))
            expect(page).to_have_url(re.compile(r".*category=.*"))
            expect(page.locator('a[aria-current="page"]')).to_have_text("Sản phẩm")
            page.screenshot(path=str(screenshots / "products-desktop.png"), full_page=True)

            page.goto(self.live_server_url + "/product/skus/")
            expect(page.locator("tbody")).to_contain_text("Chưa có SKU.")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            expect(page.locator("#id_organization")).to_have_count(0)
            expect(page.locator("#id_attributes")).to_have_count(0)
            page.get_by_role("button", name="Lưu SKU", exact=True).click()
            expect(page.locator("#id_product_errors")).to_contain_text("Vui lòng chọn sản phẩm.")
            page.locator("#id_product").select_option(str(product_id))
            page.locator("#id_code").fill(" cap_25g ")
            page.locator("#id_name").fill("Cappuccino 25g")
            page.locator("#id_barcode").fill("8930001")
            page.locator("#id_sales_uom").select_option(str(self.pack.pk))
            page.locator("#id_net_quantity").fill("0")
            page.locator("#id_net_quantity_uom").select_option(str(self.g.pk))
            page.locator("#id_sell_item").select_option(str(self.item.pk))
            page.get_by_role("button", name="Lưu SKU", exact=True).click()
            expect(page.locator("#id_net_quantity_errors")).to_contain_text("Lượng tịnh phải lớn hơn 0.")
            expect(page.locator("#id_code")).to_have_value(" cap_25g ")
            page.locator("#id_net_quantity").fill("25.5")
            page.get_by_role("button", name="Lưu SKU", exact=True).click()
            expect(page.locator("#product-detail")).to_contain_text("CAP_25G")
            expect(page.locator("#product-detail")).to_contain_text("25,5")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo SKU.")
            sku_url = page.url
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_name").fill("Cappuccino 25,5g")
            page.get_by_role("button", name="Lưu SKU", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật SKU.")
            page.goto(self.live_server_url + "/product/skus/")
            page.locator("#filter-product").select_option(str(product_id))
            expect(page).to_have_url(re.compile(r".*product=.*"))
            expect(page.locator("tbody tr")).to_have_count(1)
            expect(page.locator("tbody")).to_contain_text("25,5")
            page.locator("#reference-data-search").fill("absent")
            expect(page.locator("tbody")).to_contain_text("Không có kết quả phù hợp.")
            page.go_back()
            expect(page.locator("tbody")).to_contain_text("CAP_25G")
            expect(page.locator("#filter-product")).to_have_value(str(product_id))
            expect(page.locator("#reference-data-search")).to_have_value("")
            page.screenshot(path=str(screenshots / "skus-desktop.png"), full_page=True)

            # An inactive Product remains readable and retained on old SKU edit,
            # while the create dropdown excludes it.
            page.goto(product_url)
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_is_active").uncheck()
            page.get_by_role("button", name="Lưu sản phẩm", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.keyboard.press("Tab")
            self.assertTrue(page.get_by_role("dialog").evaluate("dialog => dialog.contains(document.activeElement)"))
            page.get_by_role("button", name="Xác nhận và lưu", exact=True).click()
            expect(page.locator("#product-detail")).to_contain_text("Ngừng hoạt động")
            page.goto(self.live_server_url + "/product/skus/create/")
            expect(page.locator(f'#id_product option[value="{product_id}"]')).to_have_count(0)
            page.goto(sku_url)
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            expect(page.locator("#id_product")).to_have_value(str(product_id))
            expect(page.locator(f'#id_product option[value="{product_id}"]')).to_contain_text("ngừng hoạt động")
            page.locator("#id_is_active").uncheck()
            page.get_by_role("button", name="Lưu SKU", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.get_by_role("button", name="Xác nhận và lưu", exact=True).click()
            expect(page.locator("#product-detail")).to_contain_text("Ngừng hoạt động")

            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(self.create_pagination_data).result()
            for path in ("products", "skus"):
                page.goto(self.live_server_url + f"/product/{path}/")
                expect(page.locator("tbody tr")).to_have_count(25)
                page.get_by_role("link", name="Sau", exact=True).click()
                expect(page.locator("tbody tr")).to_have_count(7)
                page.locator("#page-size").select_option("50")
                expect(page.locator("tbody tr")).to_have_count(32)
                page.locator("#table-sort").select_option("-code")
                expect(page.locator("tbody tr").first).to_contain_text("TEST_030")
                expect(page.locator('#reference-data-filters input[name="sort"]')).to_have_value("-code")
                page.locator("#filter-active").select_option("true")
                expect(page.locator("tbody tr")).to_have_count(31)
                page.locator("#reference-data-search").fill("TEST_015")
                expect(page.locator("tbody tr")).to_have_count(1)
                self.assertIn("per_page=50", page.url)
                page.reload()
                expect(page.locator("#reference-data-search")).to_have_value("TEST_015")
                page.get_by_role("link", name="Đặt lại", exact=True).click()
                expect(page.locator("#list-loading")).not_to_be_visible()
                for width in (1100, 800, 390):
                    page.set_viewport_size({"width": width, "height": 844})
                    page.goto(self.live_server_url + f"/product/{path}/")
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (path, width))
                    page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (path, width, "form"))
                page.screenshot(path=str(screenshots / f"{path}-mobile-form.png"), full_page=True)
                page.set_viewport_size({"width": 1440, "height": 960})
            self.assertNotIn("sessionid", {cookie["name"] for cookie in page.context.cookies()})
            self.assertEqual(errors, [])
            browser.close()
