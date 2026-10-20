"""Real drawer, table disclosures, glossary labels and responsive checks."""
import os
from pathlib import Path
from unittest import skipUnless
import uuid

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse

from apps.core.models import CostingRunLine
from apps.master_data.access import Workspace
from .run_services import create_run
from .run_test_data import golden_data, seal, request_data, cleanup


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Opt-in Chromium check.")
class ExplanationBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.data = golden_data()
        seal(self.data)
        self.run = create_run(workspace=Workspace(self.data.company), data=request_data(self.data), idempotency_key=uuid.uuid4())
        self.material = CostingRunLine.objects.get(run=self.run, line_code="MATERIAL_COST")
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.data.company.pk)
        company.enable()
        self.addCleanup(company.disable)
        self.folder = Path(settings.BASE_DIR) / "artifacts" / "explanation-readability"
        self.folder.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        cleanup()
        super().tearDown()

    def test_trace_drawer_disclosure_material_table_and_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url + reverse("costing:run_detail", args=[self.run.public_id]))
            page.get_by_role("link", name="Nguồn dữ liệu / Diễn giải", exact=True).first.click()
            dialog = page.get_by_role("dialog", name="Tổng giá thành", exact=True)
            expect(dialog).to_be_visible()
            self.assertGreaterEqual(dialog.bounding_box()["width"], 800)
            expect(dialog.locator("#trace-inputs-title")).to_be_visible()
            expect(dialog).to_contain_text("Nguyên vật liệu")
            math = dialog.locator("details").filter(has=page.locator("summary", has_text="bước tính trong công thức"))
            self.assertIsNone(math.get_attribute("open"))
            math.locator("summary").click()
            expect(math.get_by_role("columnheader", name="Kết quả", exact=True)).to_be_visible()
            expect(math).to_contain_text("Cộng (+)")
            page.screenshot(path=str(self.folder / "formula-trace-desktop.png"), full_page=True)
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
            row = page.locator("#run-lines-table tbody tr").filter(has_text="MATERIAL_COST")
            row.get_by_role("link", name="Nguồn dữ liệu / Diễn giải", exact=True).click()
            dialog = page.get_by_role("dialog", name="Nguyên vật liệu", exact=True)
            expect(dialog.locator("#trace-materials-title")).to_be_visible()
            expect(dialog.locator(".ui-trace-table tbody tr")).to_have_count(2)
            page.screenshot(path=str(self.folder / "material-trace-desktop.png"), full_page=True)
            for width in (768, 390):
                page.set_viewport_size({"width": width, "height": 844})
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                self.assertLessEqual(dialog.bounding_box()["width"], width)
                page.screenshot(path=str(self.folder / f"material-trace-{width}.png"), full_page=True)
            browser.close()
        self.assertEqual(errors, [])

    def test_saved_sources_and_friendly_form_labels_keep_bindings(self):
        from playwright.sync_api import expect, sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
            page.goto(self.live_server_url + reverse("costing:run_snapshot", args=[self.run.public_id]))
            page.locator("summary").filter(has_text="Định mức, bao bì và công đoạn").click()
            expect(page.get_by_text("Định mức cà phê", exact=True).first).to_be_visible()
            page.screenshot(path=str(self.folder / "sources-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            page.goto(self.live_server_url + reverse("master_data:uom_edit", args=[self.data.kg.pk]))
            expect(page.get_by_label("Số chữ số thập phân", exact=False)).to_have_attribute("name", "precision")
            page.goto(self.live_server_url + reverse("costing:run_create"))
            expect(page.get_by_label("Tiền tệ tính giá", exact=False)).to_have_attribute("name", "result_currency_code")
            page.locator("#id_costing_date").fill(self.data.day.isoformat())
            page.locator("#id_product").select_option(str(self.data.product.pk))
            page.locator("#id_sku").select_option(str(self.data.sku.pk))
            page.locator("#id_scheme").select_option(str(self.data.scheme.pk))
            expect(page.get_by_label("Số thành phẩm theo định mức bao bì", exact=False)).to_have_attribute("name", "packaging_quantity")
            expect(page.get_by_text("Bảng định mức bao bì đã nhập đủ", exact=False)).to_be_visible()
            page.screenshot(path=str(self.folder / "run-labels-mobile.png"), full_page=True)
            browser.close()