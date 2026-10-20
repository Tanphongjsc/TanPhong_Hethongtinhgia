"""Browser checks for the existing confirmation pattern and packaging cells."""
import os
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse

from apps.costing.run_test_data import golden_data, cleanup


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Opt-in Playwright check.")
class DefinitionActivationBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.data = golden_data()
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.data.company.pk)
        company.enable()
        self.addCleanup(company.disable)

    def tearDown(self):
        cleanup()  # guarded test-only localhost fixture cleanup; no Supabase
        super().tearDown()

    def test_confirmation_activation_and_packaging_action_column(self):
        from playwright.sync_api import expect, sync_playwright
        errors = []
        screenshots = Path(settings.BASE_DIR) / "artifacts" / "bom-packaging-activation"
        screenshots.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 960}, locale="vi-VN")
            page.on("pageerror", lambda error: errors.append(str(error)))
            for name, parent, version in (
                ("bom", self.data.recipe, self.data.recipe_version),
                ("packaging", self.data.packaging, self.data.packaging_version),
            ):
                url = reverse(f"bom:{name}_version_detail", args=[parent.pk, version.pk])
                page.goto(self.live_server_url + url)
                activate = page.get_by_role("button", name="Kích hoạt phiên bản", exact=True)
                activate.click()
                dialog = page.get_by_role("dialog")
                expect(dialog).to_be_visible()
                dialog.get_by_role("button", name="Hủy", exact=True).click()
                expect(dialog).not_to_be_visible()
                activate.click()
                dialog.get_by_role("button", name="Xác nhận kích hoạt", exact=True).click()
                expect(activate).to_have_count(0)
                expect(page.locator("#toast-root")).to_contain_text("Đã kích hoạt phiên bản")
                expect(page.get_by_role("link", name="+ Thêm thành phần", exact=True)).to_have_count(0)
                page.screenshot(path=str(screenshots / f"{name}-activated.png"), full_page=True)
            page.goto(self.live_server_url + reverse("bom:packaging_list"))
            row = page.locator("tbody tr").first
            expect(row.locator("td")).to_have_count(9)
            last_cell = row.locator("td").last
            expect(last_cell.locator('a[data-tooltip="Xem chi tiết"]')).to_be_visible()
            expect(last_cell.locator('a[data-tooltip="Chỉnh sửa"]')).to_be_visible()
            self.assertGreater(last_cell.locator("a").first.bounding_box()["x"], row.locator("td").first.bounding_box()["x"])
            page.screenshot(path=str(screenshots / "packaging-actions-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(self.live_server_url + reverse("bom:packaging_detail", args=[self.data.packaging.pk]))
            expect(page.locator("#packaging-detail")).to_be_visible()
            page.screenshot(path=str(screenshots / "packaging-mobile.png"), full_page=True)
            browser.close()
        for version in (self.data.recipe_version, self.data.packaging_version):
            version.refresh_from_db()
            self.assertEqual(version.status, "EFFECTIVE")
        self.assertEqual(errors, [])