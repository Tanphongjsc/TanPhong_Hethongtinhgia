"""Real Chromium: token insertion, HTMX validation/testing and responsive UI."""
import os
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from apps.core.models import CostElement, Currency, Formula, FormulaDependency, FormulaTestCase, FormulaVersion, Organization


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Set COSTING_BROWSER_TESTS=1 for Playwright checks.")
class FormulaBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.company = Organization.objects.create(code="FORMULA_BROWSER", name="Công ty kiểm thử")
        currency = Currency.objects.create(code="VND", name="Đồng Việt Nam")
        self.a = CostElement.objects.create(organization=self.company, code="MATERIAL", name="Nguyên vật liệu", value_type="MONEY", currency_code=currency,
            dimension_code="MONEY", default_source_mode="MANUAL", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING")

    def tearDown(self):
        for model in (FormulaDependency, FormulaTestCase, FormulaVersion, Formula, CostElement, Currency, Organization): model.objects.all().delete()
        super().tearDown()

    def test_editor_token_validation_test_trace_clone_and_responsive(self):
        from playwright.sync_api import expect, sync_playwright
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        screenshots.mkdir(parents=True, exist_ok=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1050}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + "/formula-engine/formulas/")
            expect(page.locator("tbody")).to_contain_text("Chưa có công thức tính.")
            page.get_by_role("link", name="+ Thêm công thức", exact=True).first.click()
            page.get_by_role("button", name="Lưu công thức", exact=True).click()
            expect(page.locator("#id_code_errors")).to_contain_text("Vui lòng nhập mã công thức.")
            page.locator("#id_code").fill(" formula_material ")
            page.locator("#id_name").fill("Chi phí nguyên vật liệu")
            page.locator("#id_effective_from").fill("2026-10-07")
            page.locator("#id_expression").focus()
            page.get_by_role("button", name="Chèn MATERIAL", exact=True).click()
            expect(page.locator("#id_expression")).to_have_value("$MATERIAL")
            page.locator("#id_expression").fill("$MATERIAL * 1.05")
            page.get_by_role("button", name="Kiểm tra công thức", exact=True).click()
            expect(page.locator("#formula-studio-content")).to_contain_text("Cú pháp, kiểu dữ liệu, đơn vị và phụ thuộc hợp lệ.")
            expect(page.locator("#id_code")).to_have_value(" formula_material ")
            page.locator("#id_input_MATERIAL").fill("100000")
            page.locator("#id_expected").fill("105000")
            page.get_by_role("button", name="Kiểm thử", exact=True).click()
            expect(page.locator("#formula-studio-content")).to_contain_text("105.000")
            expect(page.locator("#formula-studio-content")).to_contain_text("Đạt")
            page.screenshot(path=str(screenshots / "formula-studio-desktop.png"), full_page=True)
            page.get_by_role("button", name="Lưu công thức", exact=True).click()
            expect(page.locator("#formula-detail")).to_contain_text("Phiên bản 1")
            expect(page.locator("#toast-root")).to_contain_text("Đã tạo công thức.")
            page.locator("#id_input_MATERIAL").fill("100000")
            page.locator("#id_expected").fill("105000")
            page.locator("#id_test_name").fill("Nguyên vật liệu chuẩn")
            page.get_by_role("button", name="Lưu bộ kiểm thử", exact=True).click()
            expect(page.locator("#formula-test-panel")).to_contain_text("Đã lưu bộ kiểm thử công thức.")
            page.get_by_role("button", name="Chạy bộ kiểm thử đã lưu", exact=True).click()
            expect(page.locator("#formula-test-panel")).to_contain_text("Nguyên vật liệu chuẩn")
            page.get_by_role("link", name="Tạo phiên bản mới", exact=True).click()
            expect(page.locator("#id_expression")).to_have_value("$MATERIAL * 1.05")
            page.locator("#id_expression").fill("$MATERIAL * 1.10")
            page.get_by_role("button", name="Lưu công thức", exact=True).click()
            expect(page.locator("#formula-detail")).to_contain_text("Phiên bản 2")
            page.get_by_role("link", name="Lịch sử phiên bản", exact=True).click()
            expect(page.locator("tbody")).to_contain_text("Phiên bản 1")
            page.get_by_role("link", name="Phiên bản 1", exact=True).click()
            expect(page.locator("pre")).to_have_text("$MATERIAL * 1.05")
            page.get_by_role("link", name="Chỉnh sửa biểu thức", exact=True).click()
            page.locator("#id_expression").fill("MATERIAL +")
            page.get_by_role("button", name="Kiểm tra công thức", exact=True).click()
            expect(page.locator("#id_expression_errors")).to_contain_text("Lỗi cú pháp")
            expect(page.locator("#id_expression")).to_have_attribute("aria-invalid", "true")
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
            page.screenshot(path=str(screenshots / "formula-studio-mobile.png"), full_page=True)
            self.assertEqual(errors, [])
            browser.close()
