"""Actual HTMX/drawer/dependent dropdown flow on isolated local PostgreSQL."""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections
from django.utils import timezone

from apps.core.models import Organization, Product, Resource, Routing, RoutingOperation, RoutingVersion, Sku, Uom, UomCategory, WorkCenter


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class RoutingBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="ROUTING_BROWSER", name="Công ty kiểm thử")
        time = UomCategory.objects.create(code="TIME", name="Thời gian", dimension_code="TIME")
        mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        self.minute = Uom.objects.create(category=time, code="MIN", name="Phút", symbol="phút")
        self.kg = Uom.objects.create(category=mass, code="KG", name="Kilôgam", symbol="kg")
        self.product = Product.objects.create(organization=self.company, code="CAP", name="Cà phê Cappuccino", costing_uom=self.kg)
        self.sku = Sku.objects.create(organization=self.company, product=self.product, code="CAP_20", name="Cappuccino 20 gói", sales_uom=self.kg, net_quantity=1, net_quantity_uom=self.kg)
        self.center = WorkCenter.objects.create(organization=self.company, code="MIX", name="Khu phối trộn")
        self.packing = WorkCenter.objects.create(organization=self.company, code="PACK", name="Khu đóng gói")
        self.machine = Resource.objects.create(organization=self.company, work_center=self.center, code="MIXER", name="Máy trộn", resource_type="MACHINE")
        self.packer = Resource.objects.create(organization=self.company, work_center=self.packing, code="PACKER", name="Máy đóng gói", resource_type="MACHINE")

    def tearDown(self):
        for model in (RoutingOperation, RoutingVersion, Routing, Resource, WorkCenter, Sku, Product, Uom, UomCategory, Organization):
            model.objects.all().delete()
        super().tearDown()

    def pagination_data(self, version_id):
        try:
            RoutingOperation.objects.bulk_create([RoutingOperation(routing_version_id=version_id, sequence_no=20+i,
                operation_code=f"OP_{i:03}", operation_name=f"Công đoạn kiểm thử {i}", work_center_id=self.center.pk,
                primary_resource_id=self.machine.pk, run_time=1, time_uom_id=self.minute.pk) for i in range(31)])
            routings = Routing.objects.bulk_create([Routing(organization_id=self.company.pk, product_id=self.product.pk,
                code=f"RT_{i:03}", name=f"Quy trình kiểm thử {i}") for i in range(31)])
            RoutingVersion.objects.bulk_create([RoutingVersion(routing=routing, version_no=1) for routing in routings])
        finally:
            connections.close_all()

    def test_drawer_resources_clone_history_query_state_and_responsive(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(error.stack))
            page.goto(self.live_server_url + "/bom/routings/")
            expect(page.locator("h1")).to_have_text("Quy trình sản xuất")
            expect(page.locator("tbody")).to_contain_text("Chưa có quy trình sản xuất.")
            expect(page.locator('#workspace-sidebar a[aria-current="page"]')).to_be_visible()
            page.get_by_role("link", name="+ Thêm quy trình", exact=True).first.click()
            page.get_by_role("button", name="Lưu quy trình sản xuất", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã quy trình.")
            page.locator("#id_product").select_option(str(self.product.pk))
            page.locator("#id_code").fill(" rt_cap ")
            page.locator("#id_name").fill("Quy trình Cappuccino")
            page.locator("#id_initial-batch_size").fill("100")
            page.locator("#id_initial-batch_uom").select_option(str(self.kg.pk))
            page.locator("#id_initial-effective_from").fill(timezone.localdate().isoformat())
            page.get_by_role("button", name="Lưu quy trình sản xuất", exact=True).click()
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo quy trình sản xuất.")
            routing_id = int(page.url.rstrip("/").split("/")[-1])
            page.get_by_role("link", name="+ Thêm công đoạn", exact=True).click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_be_visible()
            expect(dialog.get_by_role("button", name="Đóng chi tiết")).to_be_focused()
            expect(page.locator("#id_sequence_no")).to_have_value("10")
            page.locator("#id_operation_code").fill(" mix ")
            page.locator("#id_operation_name").fill("Phối trộn")
            page.locator("#id_work_center").select_option(str(self.center.pk))
            expect(page.locator(f'#id_primary_resource option[value="{self.packer.pk}"]')).to_have_count(0)
            page.locator("#id_primary_resource").select_option(str(self.machine.pk))
            page.locator("#id_setup_time").fill("-1")
            page.locator("#id_run_time").fill("30.12345678")
            page.locator("#id_time_uom").select_option(str(self.minute.pk))
            page.locator("#id_quantity_basis").fill("100")
            page.locator("#id_quantity_uom").select_option(str(self.kg.pk))
            page.get_by_role("button", name="Lưu công đoạn", exact=True).click()
            expect(page.locator("#id_setup_time_errors")).to_be_visible()
            expect(page.locator("#id_setup_time")).to_have_attribute("aria-invalid", "true")
            expect(page.locator("#id_primary_resource")).to_have_value(str(self.machine.pk))
            page.locator("#id_setup_time").fill("15.5")
            page.get_by_role("button", name="Lưu công đoạn", exact=True).click()
            expect(page.locator("#routing-operation-editor")).to_be_empty()
            expect(page.locator("#routing-operations-table")).to_contain_text("30,12345678")
            expect(page.locator("#toast-root")).to_contain_text("Đã thêm công đoạn.")
            page.locator("#routing-operations-table").get_by_role("link", name="Chỉnh sửa công đoạn MIX", exact=True).click()
            page.locator("#id_work_center").select_option(str(self.packing.pk))
            expect(page.locator(f'#id_primary_resource option[value="{self.packer.pk}"]')).to_have_count(1)
            expect(page.locator(f'#id_primary_resource option[value="{self.machine.pk}"]')).to_have_count(0)
            page.locator("#id_primary_resource").select_option(str(self.packer.pk))
            page.locator("#id_operation_name").fill("Đóng gói")
            page.get_by_role("button", name="Lưu công đoạn", exact=True).click()
            expect(page.locator("#routing-operation-editor")).to_be_empty()
            expect(page.locator("#routing-operations-table")).to_contain_text("PACKER")
            page.get_by_role("link", name="Tạo phiên bản mới từ phiên bản 1", exact=True).click()
            page.locator("#id_change_reason").fill("Thay đổi công đoạn đóng gói")
            page.get_by_role("button", name="Lưu phiên bản quy trình", exact=True).click()
            expect(page.locator("#routing-detail")).to_contain_text("Phiên bản 2")
            expect(page.locator("#routing-operations-table")).to_contain_text("PACKER")
            expect(page.locator("#routing-operations-table")).to_contain_text("30,12345678")
            second_url = page.url
            page.locator("#routing-operations-table").get_by_role("link", name="Xóa công đoạn MIX", exact=True).click()
            expect(page.get_by_role("dialog")).to_contain_text("Bạn có chắc muốn xóa công đoạn này khỏi quy trình?")
            page.get_by_role("button", name="Hủy", exact=True).click()
            expect(page.get_by_role("dialog")).not_to_be_visible()
            expect(page.locator("#routing-operations-table tbody tr")).to_have_count(1)
            page.locator("#routing-operations-table").get_by_role("link", name="Xóa công đoạn MIX", exact=True).click()
            page.get_by_role("button", name="Xác nhận xóa", exact=True).click()
            expect(page.locator("#routing-operations-table")).to_contain_text("Quy trình chưa có công đoạn.")
            expect(page.locator("#toast-root")).to_contain_text("Đã xóa công đoạn.")
            page.get_by_role("link", name="Lịch sử phiên bản", exact=True).click()
            page.get_by_role("link", name="Phiên bản 1", exact=True).click()
            expect(page.locator("#routing-operations-table")).to_contain_text("PACKER")
            first_url = page.url
            first_id = int(first_url.rstrip("/").split("/")[-1])
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(self.pagination_data, first_id).result()
            page.reload()
            expect(page.locator("#routing-operations-table tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("#routing-operations-table tbody tr")).to_have_count(7)
            expect(page).to_have_url(re.compile(r".*page=2.*"))
            page.locator("#page-size").select_option("50")
            expect(page.locator("#routing-operations-table tbody tr")).to_have_count(32)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(screenshots / "routing-detail-desktop.png"))
            page.goto(self.live_server_url + "/bom/routings/")
            page.locator("#reference-data-search").fill("rt_")
            expect(page).to_have_url(re.compile(r".*q=rt_.*"))
            expect(page.locator("tbody tr")).to_have_count(25)
            page.get_by_role("link", name="Sau", exact=True).click()
            expect(page.locator("tbody tr")).to_have_count(7)
            page.locator("#table-sort").select_option("-code")
            expect(page.locator("tbody tr").first).to_contain_text("RT_CAP")
            page.locator("#filter-sku").select_option(str(self.sku.pk))
            expect(page).to_have_url(re.compile(r".*sku=\d+.*"))
            page.locator("#filter-effective").select_option("EFFECTIVE")
            expect(page.locator("tbody tr")).to_have_count(1)
            page.reload()
            expect(page.locator("#table-sort")).to_have_value("-code")
            expect(page.locator("#filter-sku")).to_have_value(str(self.sku.pk))
            page.screenshot(path=str(screenshots / "routing-list-desktop.png"))
            second_id = int(second_url.rstrip("/").split("/")[-1])
            page.goto(self.live_server_url + f"/bom/routings/{routing_id}/versions/{second_id}/operations/create/")
            page.locator("#id_operation_code").fill("NO_TIME")
            page.locator("#id_operation_name").fill("Công đoạn chưa định thời gian")
            page.get_by_role("button", name="Lưu công đoạn", exact=True).click()
            expect(page).to_have_url(second_url)
            for width in (1100, 800, 390):
                page.set_viewport_size({"width": width, "height": 844})
                page.goto(second_url)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.get_by_role("link", name="+ Thêm công đoạn", exact=True).click()
                expect(page.get_by_role("dialog")).to_be_visible()
                expect(page.locator("#id_operation_name")).to_be_visible()
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.keyboard.press("Escape")
                expect(page.get_by_role("dialog")).not_to_be_visible()
                expect(page.get_by_role("link", name="+ Thêm công đoạn", exact=True)).to_be_focused()
            page.get_by_role("link", name="+ Thêm công đoạn", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.screenshot(path=str(screenshots / "routing-drawer-mobile.png"))
            self.assertFalse(any(cookie["name"] == "sessionid" for cookie in page.context.cookies()))
            browser.close()
        self.assertEqual(errors, [])
