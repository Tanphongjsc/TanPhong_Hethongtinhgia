"""Browser regression for native submits, CSRF feedback and workspace widths."""
import os
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from apps.core.models import Organization, RecipeVersion
from .demo_data import seed_demo
from .run_test_data import cleanup


@skipUnless(os.environ.get("COSTING_BROWSER_TESTS") == "1", "Enable COSTING_BROWSER_TESTS=1 for Chromium")
class HardeningBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        cleanup()
        Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        self.demo = seed_demo()

    def tearDown(self):
        cleanup()
        super().tearDown()

    def test_breakpoints_and_native_new_version_double_submit(self):
        from playwright.sync_api import sync_playwright, expect
        folder = Path(settings.BASE_DIR) / "artifacts" / "screenshots"
        folder.mkdir(exist_ok=True)
        source = self.demo.records["recipe_version"]
        before = RecipeVersion.objects.filter(recipe=source.recipe_id).count()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(locale="vi-VN")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for width in (1366, 1440, 900):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(self.live_server_url + reverse("product:item_list"))
                expect(page.get_by_role("heading", name="Danh mục vật tư / hàng hóa", exact=True)).to_be_visible()
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                page.screenshot(path=str(folder / f"hardening-{width}.png"), full_page=True)
            url = reverse("bom:bom_version_create", args=[source.recipe_id]) + f"?source={source.pk}"
            page.goto(self.live_server_url + url)
            page.wait_for_function("window.Alpine !== undefined")
            page.evaluate("""() => {
                const form = document.querySelector('#reference-data-form');
                const button = form.querySelector('button[type=submit]');
                form.requestSubmit(button);
                form.requestSubmit(button);
            }""")
            expect(page.locator('#toast-root')).to_contain_text("Đã tạo phiên bản định mức mới.")
            self.assertEqual(errors, [])
            browser.close()
        self.assertEqual(RecipeVersion.objects.filter(recipe=source.recipe_id).count(), before + 1)

    def test_htmx_csrf_failure_has_actionable_feedback(self):
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(self.live_server_url + reverse("costing:run_create"))
            page.wait_for_function("window.htmx !== undefined")
            page.evaluate("""() => {
                document.querySelector('meta[name=csrf-token]').remove();
                htmx.ajax('POST', window.location.pathname, {target: '#run-form-content'});
            }""")
            expect(page.locator('#request-error')).to_be_visible()
            expect(page.locator('#request-error')).to_contain_text("Vui lòng tải lại trang")
            expect(page.locator('#request-error')).to_contain_text("Mã tham chiếu:")
            browser.close()
