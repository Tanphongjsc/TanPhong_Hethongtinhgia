"""Real drawer/HTMX flow on isolated local PostgreSQL only."""
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

from apps.core.models import Item, Organization, PackagingConfig, PackagingConfigVersion, PackagingLine, Product, Sku, SkuPackagingAssignment, Uom, UomCategory, UomConversion


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class PackagingBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="PACK_BROWSER", name="Công ty kiểm thử")
        count = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        self.pc = Uom.objects.create(category=count, code="PC", name="Cái", symbol="cái")
        self.ct = Uom.objects.create(category=count, code="CT", name="Thùng", symbol="thùng")
        self.product = Product.objects.create(organization=self.company, code="CAP", name="Cà phê Cappuccino", costing_uom=self.pc)
        self.sku = Sku.objects.create(organization=self.company, product=self.product, code="CAP_20", name="Cappuccino 20 gói", sales_uom=self.pc, net_quantity=20, net_quantity_uom=self.pc)
        self.item = Item.objects.create(organization=self.company, code="CARTON", name="Thùng Cappuccino", item_type="PACKAGING", base_uom=self.pc)
        self.today = timezone.localdate()
        UomConversion.objects.create(organization=self.company, from_uom=self.ct, to_uom=self.pc, factor=12, effective_from=self.today - timedelta(days=10))

    def tearDown(self):
        for model in (SkuPackagingAssignment, PackagingLine, PackagingConfigVersion, PackagingConfig, UomConversion, Sku, Product, Item, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def pagination_data(self, version_id):
        try:
            PackagingLine.objects.bulk_create([PackagingLine(packaging_config_version_id=version_id, packaging_item_id=self.item.pk, qty=i + 1, uom_id=self.pc.pk, level_code="PRIMARY", display_order=i + 2) for i in range(31)])
            configs = PackagingConfig.objects.bulk_create([PackagingConfig(organization_id=self.company.pk, product_id=self.product.pk, code=f"PACK_{i:03}", name=f"Bao bì kiểm thử {i}") for i in range(31)])
            PackagingConfigVersion.objects.bulk_create([PackagingConfigVersion(packaging_config=config, version_no=1) for config in configs])
        finally:
            connections.close_all()

    def test_packaging_drawer_clone_sku_history_and_responsive(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/bom/packaging/")
            expect(page.locator("h1")).to_have_text("Cấu hình bao bì")
            expect(page.locator("tbody")).to_contain_text("Chưa có cấu hình bao bì.")
            expect(page.locator('#workspace-sidebar a[aria-current="page"]')).to_be_visible()
            page.get_by_role("link", name="+ Thêm cấu hình bao bì", exact=True).first.click()
            page.get_by_role("button", name="Lưu cấu hình bao bì", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã cấu hình bao bì.")
            page.locator("#id_product").select_option(str(self.product.pk))
            page.locator("#id_code").fill(" pack_cap ")
            page.locator("#id_name").fill("Bao bì Cappuccino")
            page.locator("#id_initial-effective_from").fill(self.today.isoformat())
            page.get_by_role("button", name="Lưu cấu hình bao bì", exact=True).click()
            config_id = int(page.url.rstrip("/").split("/")[-1])
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo cấu hình bao bì.")
            page.get_by_role("link", name="+ Gán SKU", exact=True).click()
            page.locator("#id_sku").select_option(str(self.sku.pk))
            page.get_by_role("button", name="Lưu liên kết SKU", exact=True).click()
            expect(page.locator("#packaging-detail")).to_contain_text("CAP_20")
            expect(page.locator("#toast-root")).to_contain_text("Đã gán SKU cho cấu hình bao bì.")
            page.get_by_role("link", name="+ Thêm thành phần", exact=True).click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_be_visible()
            expect(dialog.get_by_role("button", name="Đóng chi tiết")).to_be_focused()
            page.locator("#id_packaging_item").select_option(str(self.item.pk))
            page.locator("#id_qty").fill("0")
            page.locator("#id_uom").select_option(str(self.ct.pk))
            page.locator("#id_level_code").select_option("TERTIARY")
            page.locator("#id_parent_level_code").select_option("PALLET")
            page.locator("#id_units_per_parent").fill("12")
            page.locator("#id_display_order").fill("1")
            page.get_by_role("button", name="Lưu thành phần bao bì", exact=True).click()
            expect(page.locator("#id_qty_errors")).to_contain_text("Số lượng phải lớn hơn 0.")
            expect(page.locator("#id_qty")).to_have_attribute("aria-invalid", "true")
            expect(page.locator("#id_parent_level_code")).to_have_value("PALLET")
            page.locator("#id_qty").fill("0.08333333")
            page.get_by_role("button", name="Lưu thành phần bao bì", exact=True).click()
            expect(page.locator("#packaging-line-editor")).to_be_empty()
            expect(page.locator("#packaging-lines-table")).to_contain_text("0,08333333")
            expect(page.locator("#toast-root")).to_contain_text("Đã thêm thành phần bao bì.")
            page.locator("#packaging-lines-table").get_by_role("link", name=re.compile("Chỉnh sửa thành phần")).click()
            page.locator("#id_qty").fill("0.25")
            page.get_by_role("button", name="Lưu thành phần bao bì", exact=True).click()
            expect(page.locator("#packaging-lines-table")).to_contain_text("0,25")
            page.get_by_role("link", name="Tạo phiên bản mới từ phiên bản 1", exact=True).click()
            page.locator("#id_change_reason").fill("Đổi quy cách bao bì")
            page.get_by_role("button", name="Lưu phiên bản bao bì", exact=True).click()
            second_url = page.url
            expect(page.locator("#packaging-detail")).to_contain_text("Phiên bản 2")
            expect(page.locator("#packaging-lines-table")).to_contain_text("0,25")
            page.locator("#packaging-lines-table").get_by_role("link", name=re.compile("Xóa thành phần")).click()
            expect(page.get_by_role("dialog")).to_contain_text("Bạn có chắc muốn xóa thành phần bao bì này?")
            page.get_by_role("button", name="Hủy", exact=True).click()
            expect(page.get_by_role("dialog")).not_to_be_visible()
            expect(page.locator("#packaging-lines-table tbody tr")).to_have_count(1)
            page.locator("#packaging-lines-table").get_by_role("link", name=re.compile("Xóa thành phần")).click()
            page.get_by_role("button", name="Xác nhận xóa", exact=True).click()
            expect(page.locator("#packaging-lines-table")).to_contain_text("Cấu hình chưa có thành phần bao bì.")
            expect(page.locator("#toast-root")).to_contain_text("Đã xóa thành phần bao bì.")
            page.get_by_role("link", name="Lịch sử phiên bản", exact=True).click()
            page.get_by_role("link", name="Phiên bản 1", exact=True).click()
            first_id = int(page.url.rstrip("/").split("/")[-1])
            expect(page.locator("#packaging-lines-table")).to_contain_text("0,25")
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(self.pagination_data, first_id).result()
            page.reload()
            expect(page.locator("#packaging-lines-table tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("#packaging-lines-table tbody tr")).to_have_count(7)
            page.locator("#page-size").select_option("50")
            expect(page.locator("#packaging-lines-table tbody tr")).to_have_count(32)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(screenshots / "packaging-detail-desktop.png"))
            page.goto(self.live_server_url + "/bom/packaging/")
            page.locator("#reference-data-search").fill("pack_")
            expect(page).to_have_url(re.compile(r".*q=pack_.*"))
            expect(page.locator("tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(7)
            page.locator("#table-sort").select_option("-code")
            expect(page.locator("tbody tr").first).to_contain_text("PACK_CAP")
            page.locator("#filter-sku").select_option(str(self.sku.pk))
            expect(page.locator("tbody tr")).to_have_count(1)
            expect(page).to_have_url(re.compile(r".*sku=\d+.*"))
            page.reload()
            expect(page.locator("#table-sort")).to_have_value("-code")
            page.screenshot(path=str(screenshots / "packaging-list-desktop.png"))
            second_id = int(second_url.rstrip("/").split("/")[-1])
            page.goto(self.live_server_url + f"/bom/packaging/{config_id}/versions/{second_id}/lines/create/")
            page.locator("#id_packaging_item").select_option(str(self.item.pk))
            page.locator("#id_qty").fill("0.08333333")
            page.locator("#id_uom").select_option(str(self.pc.pk))
            page.get_by_role("button", name="Lưu thành phần bao bì", exact=True).click()
            expect(page).to_have_url(second_url)
            for width in (1100, 800, 390):
                page.set_viewport_size({"width": width, "height": 844})
                page.goto(second_url)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.get_by_role("link", name="+ Thêm thành phần", exact=True).click()
                expect(page.get_by_role("dialog")).to_be_visible()
                expect(page.locator("#id_packaging_item")).to_be_visible()
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.keyboard.press("Escape")
                expect(page.get_by_role("dialog")).not_to_be_visible()
                expect(page.get_by_role("link", name="+ Thêm thành phần", exact=True)).to_be_focused()
            page.get_by_role("link", name="+ Thêm thành phần", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.screenshot(path=str(screenshots / "packaging-drawer-mobile.png"))
            self.assertFalse(any(cookie["name"] == "sessionid" for cookie in page.context.cookies()))
            browser.close()
        self.assertEqual(errors, [])
