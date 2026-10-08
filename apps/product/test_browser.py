"""Opt-in real-browser CRUD/HTMX coverage against isolated PostgreSQL."""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections

from apps.core.models import Item, Organization, ProductCategory, Uom, UomCategory


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class CatalogBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.organization = Organization.objects.create(code="BROWSER_PRODUCT", name="Công ty kiểm thử")
        mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        length = UomCategory.objects.create(code="LENGTH", name="Chiều dài", dimension_code="LENGTH")
        self.kg = Uom.objects.create(category=mass, code="KG", name="Kilôgam", symbol="kg")
        self.m = Uom.objects.create(category=length, code="M", name="Mét", symbol="m")

    def tearDown(self):
        for model in (Item, ProductCategory, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def create_pagination_data(self):
        try:
            Item.objects.bulk_create([Item(organization_id=self.organization.pk, code=f"TEST_{i:03}", name=f"Vật tư {i}", item_type="PACKAGING", base_uom_id=self.kg.pk) for i in range(30)])
        finally:
            connections.close_all()

    def test_category_item_forms_htmx_filters_and_responsive_pages(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/product/categories/")
            expect(page.locator("tbody")).to_contain_text("Chưa có nhóm sản phẩm.")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            page.get_by_role("button", name="Lưu nhóm sản phẩm", exact=True).click()
            expect(page.locator("#id_code")).to_have_attribute("aria-invalid", "true")
            page.get_by_label("Mã", exact=False).first.fill(" nl ")
            page.locator("#id_name").fill("Nguyên liệu")
            page.locator("#id_description").fill("Dùng cho sản xuất")
            page.get_by_role("button", name="Lưu nhóm sản phẩm", exact=True).click()
            expect(page.locator("#product-detail")).to_contain_text("NL")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo nhóm sản phẩm.")
            category_id = int(page.url.rstrip("/").split("/")[-1])
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_name").fill("Nhóm nguyên liệu")
            page.get_by_role("button", name="Lưu nhóm sản phẩm", exact=True).click()
            expect(page.locator("h1")).to_have_text("Nhóm nguyên liệu")
            page.goto(self.live_server_url + "/product/categories/")
            page.locator("#reference-data-search").fill("NL")
            expect(page).to_have_url(re.compile(r".*q=NL.*"))
            expect(page.locator("tbody tr")).to_have_count(1)
            self.assertIn("q=NL", page.url)
            page.screenshot(path=str(screenshots / "product-categories-desktop.png"), full_page=True)

            page.goto(self.live_server_url + "/product/items/")
            expect(page.locator("tbody")).to_contain_text("Chưa có vật tư / hàng hóa.")
            page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
            expect(page.locator("#id_organization")).to_have_count(0)
            expect(page.locator("#id_metadata")).to_have_count(0)
            page.locator("#id_category").select_option(str(category_id))
            page.locator("#id_code").fill(" bot ")
            page.locator("#id_name").fill("Bột nguyên liệu")
            page.locator("#id_item_type").select_option("RAW_MATERIAL")
            page.locator("#id_base_uom").select_option(str(self.kg.pk))
            page.locator("#id_purchase_uom").select_option(str(self.kg.pk))
            page.locator("#id_production_uom").select_option(str(self.kg.pk))
            page.locator("#id_net_weight").fill("2")
            page.locator("#id_gross_weight").fill("1")
            page.locator("#id_weight_uom").select_option(str(self.kg.pk))
            page.get_by_role("button", name="Lưu vật tư / hàng hóa", exact=True).click()
            expect(page.locator("#id_gross_weight_errors")).to_contain_text("Khối lượng tổng không được nhỏ hơn khối lượng tịnh.")
            expect(page.locator("#id_code")).to_have_value(" bot ")
            page.locator("#id_gross_weight").fill("2.5")
            page.locator("#id_length").fill("1.25")
            page.locator("#id_dimension_uom").select_option(str(self.m.pk))
            page.get_by_role("button", name="Lưu vật tư / hàng hóa", exact=True).click()
            expect(page.locator("#product-detail")).to_contain_text("BOT")
            expect(page.locator("#product-detail")).to_contain_text("2,5")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo vật tư / hàng hóa.")
            page.get_by_role("link", name="Chỉnh sửa", exact=True).click()
            page.locator("#id_name").fill("Bột đã cập nhật")
            page.locator("#id_is_active").uncheck()
            page.get_by_role("button", name="Lưu vật tư / hàng hóa", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.keyboard.press("Tab")
            self.assertTrue(page.get_by_role("dialog").evaluate("dialog => dialog.contains(document.activeElement)"))
            page.get_by_role("button", name="Xác nhận và lưu", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật vật tư / hàng hóa.")
            page.goto(self.live_server_url + "/product/items/")
            page.locator("#filter-active").select_option("false")
            expect(page).to_have_url(re.compile(r".*active=false.*"))
            expect(page.locator("tbody")).to_contain_text("Bột đã cập nhật")
            page.locator("#filter-item_type").select_option("SERVICE")
            expect(page.locator("tbody")).to_contain_text("Không có kết quả phù hợp.")
            self.assertIn("item_type=SERVICE", page.url)
            page.go_back()
            expect(page.locator("tbody")).to_contain_text("Bột đã cập nhật")
            expect(page.locator("#filter-item_type")).to_have_value("")
            page.get_by_role("link", name="Đặt lại", exact=True).click()
            page.screenshot(path=str(screenshots / "items-desktop.png"), full_page=True)
            # Playwright owns an event loop in this thread; perform fixture ORM
            # work on a separate thread, without bypassing Django async checks.
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(self.create_pagination_data).result()
            page.reload()
            expect(page.locator("tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(6)
            page.locator("#table-sort").select_option("-code")
            expect(page.locator("tbody tr").first).to_contain_text("TEST_029")
            expect(page.locator('#reference-data-filters input[name="sort"]')).to_have_value("-code")
            expect(page.locator("#list-loading")).not_to_be_visible()
            for path in ("categories", "items"):
                for width in (1100, 800, 390):
                    page.set_viewport_size({"width": width, "height": 844})
                    page.goto(self.live_server_url + f"/product/{path}/")
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (path, width))
                    page.get_by_role("link", name="+ Thêm mới", exact=True).first.click()
                    self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (path, width, "form"))
                page.screenshot(path=str(screenshots / f"{path}-mobile-form.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
