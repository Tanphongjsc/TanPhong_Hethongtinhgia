"""Opt-in real browser flow: local assets, HTMX and isolated PostgreSQL only."""
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

from apps.core.models import Item, Organization, Product, Recipe, RecipeLine, RecipeVersion, Uom, UomCategory, UomConversion


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class BomBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="BOM_BROWSER", name="Công ty kiểm thử")
        category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        self.kg = Uom.objects.create(category=category, code="KG", name="Kilôgam", symbol="kg")
        self.g = Uom.objects.create(category=category, code="G", name="Gam", symbol="g")
        self.product = Product.objects.create(organization=self.company, code="CAPPUCCINO", name="Cà phê Cappuccino", costing_uom=self.kg)
        self.item = Item.objects.create(organization=self.company, code="COFFEE", name="Cà phê nguyên liệu", item_type="RAW_MATERIAL", base_uom=self.kg)
        self.start = timezone.localdate().isoformat()
        self.end = (timezone.localdate() + timedelta(days=30)).isoformat()
        UomConversion.objects.create(organization=self.company, from_uom=self.g, to_uom=self.kg,
            factor="0.001", effective_from=timezone.localdate() - timedelta(days=1))

    def tearDown(self):
        for model in (RecipeLine, RecipeVersion, Recipe, UomConversion, Product, Item, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def pagination_data(self, recipe_id, version_id):
        try:
            recipes = Recipe.objects.bulk_create([Recipe(organization_id=self.company.pk, product_id=self.product.pk,
                code=f"TEST_{i:03}", name=f"Định mức kiểm thử {i}") for i in range(31)])
            RecipeVersion.objects.bulk_create([RecipeVersion(recipe=recipe, version_no=1, output_qty=100, output_uom_id=self.kg.pk) for recipe in recipes])
            RecipeLine.objects.bulk_create([RecipeLine(recipe_version_id=version_id, component_item_id=self.item.pk, qty=i + 1, uom_id=self.kg.pk,
                display_order=i + 2, notes=f"Thành phần {i + 2}") for i in range(31)])
        finally:
            connections.close_all()

    def test_recipe_lines_clone_history_htmx_and_responsive(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/bom/")
            expect(page.locator("h1")).to_have_text("Định mức nguyên vật liệu")
            expect(page.locator('#workspace-sidebar a[aria-current="page"]')).to_be_visible()
            expect(page.locator("tbody")).to_contain_text("Chưa có định mức nguyên vật liệu.")
            page.get_by_role("link", name="+ Thêm định mức", exact=True).first.click()
            expect(page.locator("#id_initial-yield_rate")).to_have_value("100")
            page.get_by_role("button", name="Lưu định mức nguyên vật liệu", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã định mức.")
            expect(page.locator("#id_initial-output_qty_errors")).to_contain_text("Vui lòng nhập sản lượng chuẩn.")
            page.locator("#id_product").select_option(str(self.product.pk))
            page.locator("#id_code").fill(" bom_cap ")
            page.locator("#id_name").fill("Định mức Cappuccino")
            page.locator("#id_initial-output_qty").fill("100")
            page.locator("#id_initial-output_uom").select_option(str(self.kg.pk))
            page.locator("#id_initial-yield_rate").fill("98")
            page.locator("#id_initial-effective_from").fill(self.start)
            page.locator("#id_initial-effective_to").fill(self.end)
            page.get_by_role("button", name="Lưu định mức nguyên vật liệu", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo định mức nguyên vật liệu.")
            expect(page.locator("#bom-detail")).to_contain_text("Phiên bản 1")
            recipe_id = int(page.url.rstrip("/").split("/")[-1])
            expect(page.locator("#bom-lines-table")).to_contain_text("Định mức chưa có thành phần.")
            page.get_by_role("link", name="+ Thêm thành phần", exact=True).click()
            expect(page.locator("#bom-line-editor")).to_contain_text("Thêm thành phần")
            expect(page.locator("#id_component_item")).to_be_focused()
            page.locator("#id_component_item").select_option(str(self.item.pk))
            page.locator("#id_qty").fill("0")
            page.locator("#id_uom").select_option(str(self.g.pk))
            page.locator("#id_scrap_rate").fill("2")
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page.locator("#id_qty_errors")).to_contain_text("Số lượng phải lớn hơn 0.")
            expect(page.locator("#id_qty")).to_have_attribute("aria-invalid", "true")
            page.locator("#id_qty").fill("0.5")
            page.locator("#id_display_order").fill("1")
            page.locator("#id_notes").fill("Cà phê hòa tan")
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page.locator("#bom-lines-table tbody tr")).to_have_count(1)
            expect(page.locator("#bom-lines-table")).to_contain_text("0,5")
            expect(page.locator("#bom-line-editor")).to_be_empty()
            expect(page.locator("#toast-root")).to_contain_text("Đã thêm thành phần.")
            page.locator("#bom-lines-table").get_by_role("link", name=re.compile("Chỉnh sửa thành phần")).click()
            expect(page.locator("#id_scrap_rate")).to_have_value("2")
            page.locator("#id_qty").fill("1.5")
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page.locator("#bom-lines-table")).to_contain_text("1,5")
            expect(page.locator("#toast-root")).to_contain_text("Đã cập nhật thành phần.")
            page.get_by_role("link", name="Tạo phiên bản mới từ phiên bản 1", exact=True).click()
            expect(page.locator("#id_yield_rate")).to_have_value("98")
            page.locator("#id_output_qty").fill("120")
            page.locator("#id_change_reason").fill("Thử định mức mới")
            page.get_by_role("button", name="Lưu phiên bản định mức", exact=True).click()
            expect(page.locator("#bom-detail")).to_contain_text("Phiên bản 2")
            expect(page.locator('#workspace-sidebar a[aria-current="page"]')).to_be_visible()
            expect(page.locator("#bom-lines-table")).to_contain_text("1,5")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo phiên bản định mức mới.")
            second_url = page.url
            page.locator("#bom-lines-table").get_by_role("link", name=re.compile("Xóa thành phần")).click()
            expect(page.locator("#bom-line-editor")).to_contain_text("Bạn có chắc muốn xóa thành phần này khỏi định mức?")
            page.get_by_role("button", name="Xác nhận xóa", exact=True).click()
            expect(page.locator("#bom-lines-table")).to_contain_text("Định mức chưa có thành phần.")
            expect(page.locator("#toast-root")).to_contain_text("Đã xóa thành phần.")
            page.get_by_role("link", name="Lịch sử phiên bản", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(2)
            page.get_by_role("link", name="Phiên bản 1", exact=True).click()
            expect(page.locator("#bom-lines-table")).to_contain_text("1,5")
            first_version_id = int(page.url.rstrip("/").split("/")[-1])
            first_url = page.url
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(self.pagination_data, recipe_id, first_version_id).result()
            page.reload()
            expect(page.locator("#bom-lines-table tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            expect(page.locator("#bom-lines-table tbody tr")).to_have_count(7)
            page.locator("#page-size").select_option("50")
            expect(page.locator("#bom-lines-table tbody tr")).to_have_count(32)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(screenshots / "bom-detail-desktop.png"))
            page.goto(self.live_server_url + "/bom/")
            page.locator("#reference-data-search").fill("test")
            expect(page).to_have_url(re.compile(r".*q=test.*"))
            expect(page.locator("tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(6)
            page.locator("#table-sort").select_option("-code")
            expect(page.locator("tbody tr").first).to_contain_text("TEST_030")
            page.locator("#filter-product").select_option(str(self.product.pk))
            expect(page).to_have_url(re.compile(r".*product=\d+.*"))
            expect(page.locator('a[aria-current="page"]')).to_have_text("BOM / Công thức sản xuất")
            page.reload()
            expect(page.locator("#reference-data-search")).to_have_value("test")
            expect(page.locator("#table-sort")).to_have_value("-code")
            page.screenshot(path=str(screenshots / "bom-list-desktop.png"), full_page=True)
            # Direct access to the fallback line form must submit a normal POST;
            # it has no inline table target to receive an HTMX retarget response.
            second_id = int(second_url.rstrip("/").split("/")[-1])
            page.goto(self.live_server_url + f"/bom/{recipe_id}/versions/{second_id}/lines/create/")
            page.locator("#id_component_item").select_option(str(self.item.pk))
            page.locator("#id_qty").fill("2")
            page.locator("#id_uom").select_option(str(self.kg.pk))
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page).to_have_url(second_url)
            expect(page.locator("#bom-lines-table tbody tr")).to_have_count(1)
            for width in (1100, 800, 390):
                page.set_viewport_size({"width": width, "height": 844})
                page.goto(second_url)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.get_by_role("link", name="+ Thêm thành phần", exact=True).click()
                expect(page.locator("#id_component_item")).to_be_visible()
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(screenshots / "bom-line-mobile.png"), full_page=True)
            self.assertFalse(any(cookie["name"] == "sessionid" for cookie in page.context.cookies()))
            browser.close()
        self.assertEqual(errors, [])
