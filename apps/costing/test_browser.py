"""Chromium verifies Vietnamese UI, real HTMX drawers and responsive layout."""
import os
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone
from apps.core.models import CostingScheme, CostingSchemeVersion, CostingSchemeLine, CostElement, Currency, Formula, FormulaVersion, Organization


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright.")
class SchemeBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="SCHEME_BROWSER", name="Công ty kiểm thử")
        self.currency = Currency.objects.create(code="VND", name="Đồng Việt Nam")
        def element(code, name):
            return CostElement.objects.create(organization=self.company, code=code, name=name, value_type="MONEY", currency_code=self.currency,
                default_source_mode="MANUAL", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING", dimension_code="MONEY")
        self.input = element("MATERIAL_COST", "Nguyên vật liệu")
        self.output = element("FULL_COST", "Tổng chi phí")
        self.formula = Formula.objects.create(organization=self.company, code="TOTAL", name="Công thức tổng hợp", output_element=self.output)
        self.formula_version = FormulaVersion.objects.create(formula=self.formula, version_no=1, expression="$MATERIAL_COST", effective_from=timezone.localdate(), status="EFFECTIVE", validation_status="VALID")
    def tearDown(self):
        for model in (CostingSchemeLine, CostingSchemeVersion, CostingScheme): model.objects.all().delete()
        # Formula is a readonly test reference. Delete through the local fixture
        # cleanup by truncating after dependent schemes, not a business operation.
        from django.db import connection
        if connection.settings_dict["NAME"] != "test_costing_slice" or connection.settings_dict["HOST"] != "127.0.0.1":
            raise RuntimeError("Fixture cleanup requires isolated localhost tests.")
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE public.formula_version CASCADE")
        for model in (Formula, CostElement, Currency, Organization): model.objects.all().delete()
        super().tearDown()
    def test_scheme_drawer_sources_validation_clone_and_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        errors = []
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/costing/schemes/")
            expect(page.locator("tbody")).to_contain_text("Chưa có phương án tính giá thành.")
            page.get_by_role("link", name="+ Thêm phương án", exact=True).first.click()
            page.locator("#id_code").fill(" std ")
            page.locator("#id_name").fill("Giá thành chuẩn")
            page.locator("#id_purpose").fill("STANDARD_COST")
            page.locator("#id_initial-effective_from").fill(timezone.localdate().isoformat())
            page.get_by_role("button", name="Lưu phương án tính giá thành", exact=True).click()
            expect(page.locator("#scheme-detail")).to_contain_text("Phiên bản 1")
            page.get_by_role("link", name="+ Thêm thành phần", exact=True).click()
            dialog = page.get_by_role("dialog", name="Thêm thành phần tính giá", exact=True)
            expect(dialog).to_be_visible()
            page.locator("#id_line_code").fill("INPUT")
            page.locator("#id_label").fill("Chi phí nguyên vật liệu")
            page.locator("#id_cost_element").select_option(str(self.input.pk))
            expect(page.locator("#scheme-source-fields")).to_contain_text("Giá trị sẽ được nhập")
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page.locator("#scheme-lines-table")).to_contain_text("Chi phí nguyên vật liệu")
            expect(dialog).to_have_count(0)
            page.get_by_role("link", name="+ Thêm thành phần", exact=True).click()
            page.locator("#id_line_code").fill("TOTAL")
            page.locator("#id_label").fill("Tổng giá thành")
            page.locator("#id_line_type").select_option("OUTPUT")
            page.locator("#id_cost_element").select_option(str(self.output.pk))
            page.locator("#id_source_mode").select_option("FORMULA")
            expect(page.locator("#id_formula_version")).to_be_visible()
            page.locator("#id_formula_version").select_option(str(self.formula_version.pk))
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page.locator("#scheme-lines-table")).to_contain_text("Công thức")
            page.get_by_role("link", name="Kiểm tra cấu hình", exact=True).click()
            expect(page.locator("#scheme-validation")).to_contain_text("Cấu hình không có lỗi")
            expect(page.locator("#scheme-validation")).to_contain_text("Đã cung cấp")
            page.screenshot(path=str(screenshots / "scheme-detail-desktop.png"), full_page=True)
            page.get_by_role("link", name="Chỉnh sửa thành phần INPUT", exact=True).click()
            page.locator("#id_label").fill("")
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page.locator("#id_label")).to_have_attribute("aria-invalid", "true")
            page.locator("#id_label").fill("Nguyên liệu đã sửa")
            page.get_by_role("button", name="Lưu thành phần", exact=True).click()
            expect(page.locator("#scheme-validation")).to_contain_text("Cấu hình đã thay đổi")
            page.get_by_role("link", name="Tạo phiên bản mới từ phiên bản 1", exact=True).click()
            expect(page.locator("#id_effective_from")).to_have_value(timezone.localdate().isoformat())
            page.get_by_role("button", name="Lưu phiên bản phương án", exact=True).click()
            expect(page.locator("#scheme-detail")).to_contain_text("Phiên bản 2")
            expect(page.locator("#scheme-lines-table")).to_contain_text("Nguyên liệu đã sửa")
            page.get_by_role("link", name="Xóa thành phần INPUT", exact=True).click()
            expect(page.get_by_role("dialog", name="Xóa thành phần tính giá")).to_contain_text("Bạn có chắc")
            page.get_by_role("button", name="Xác nhận xóa", exact=True).click()
            expect(page.locator("#scheme-lines-table")).not_to_contain_text("Nguyên liệu đã sửa")
            page.get_by_role("link", name="Kiểm tra cấu hình", exact=True).click()
            expect(page.locator("#scheme-validation")).to_contain_text("Phương án chưa cung cấp dữ liệu")
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
            page.screenshot(path=str(screenshots / "scheme-detail-mobile.png"), full_page=True)
            page.get_by_role("link", name="Chỉnh sửa thành phần TOTAL", exact=True).click()
            expect(page.get_by_role("dialog", name="Chỉnh sửa thành phần tính giá")).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog", name="Chỉnh sửa thành phần tính giá")).not_to_be_visible()
            self.assertEqual(errors, [])
            browser.close()
