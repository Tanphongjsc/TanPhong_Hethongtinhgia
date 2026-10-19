"""Presentation regression: real fixtures, frozen payloads and responsive DOM."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import skipUnless

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.test import SimpleTestCase

from apps.core.models import Organization, PriceScenario
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import create_golden_run
from apps.costing.run_test_data import cleanup
from apps.pricing.demo_scenario import verify_pricing_demo
from apps.master_data.navigation import DESTINATIONS


class UIContractTests(SimpleTestCase):
    def test_frozen_routes_forms_menu_python_and_htmx_attributes(self):
        report = Path(settings.BASE_DIR) / 'artifacts/ui-redesign/test-contract.json'
        result = subprocess.run([sys.executable, 'scripts/audit_ui_contract.py', 'compare', '--report', str(report)],
                                cwd=settings.BASE_DIR, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(data['errors'], [])
        self.assertEqual(data['routes'], 163)


@skipUnless(os.environ.get('COSTING_BROWSER_TESTS') == '1', 'Enable Chromium UI checks.')
class RedesignBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        cleanup()
        Organization.objects.create(code='INTERNAL', name='Công ty nội bộ')
        self.demo = seed_demo()
        self.run = create_golden_run(self.demo)
        verify_pricing_demo()
        self.scenario = PriceScenario.objects.get(code='DEMO_PRICING_GOLDEN')
        self.folder = Path(settings.BASE_DIR) / 'artifacts/ui-redesign/after'
        self.folder.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        cleanup()
        super().tearDown()

    def assert_fits(self, page, context):
        page.wait_for_function("document.querySelector('.ui-shell')?.dataset.collapsed !== undefined")
        if page.viewport_size['width'] >= 992:
            sidebar = page.locator('#workspace-sidebar').bounding_box()
            topbar = page.locator('.ui-topbar').bounding_box()
            self.assertGreaterEqual(topbar['x'], sidebar['x'] + sidebar['width'] - 1,
                                    f'{context}: sidebar overlaps workspace on first render')
        overflow = page.evaluate('''() => [...document.querySelectorAll('body *')]
          .filter(e => { const r=e.getBoundingClientRect(); return r.width && r.right>innerWidth+1; })
          .slice(0,12).map(e => ({tag:e.tagName,id:e.id,class:e.className,
            right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width,
            overflow:getComputedStyle(e).overflowX,
            parents:[...function*(n){while(n){yield n;n=n.parentElement;}}(e.parentElement)]
              .slice(0,4).map(n=>({tag:n.tagName,class:n.className,width:n.clientWidth,overflow:getComputedStyle(n).overflowX}))}))''')
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),
                             page.viewport_size['width'], f'{context}: {json.dumps(overflow, ensure_ascii=False)}')

    def test_reference_layout_and_focus(self):
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(locale='vi-VN')
            errors, missing = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('response', lambda r: missing.append(r.url) if '/static/' in r.url and r.status >= 400 else None)
            paths = [('items', reverse('product:item_list')),
                     ('categories', reverse('product:category_list')),
                     ('item-form', reverse('product:item_create')),
                     ('costing', reverse('costing:run_detail', args=[self.run.public_id])),
                     ('snapshot', reverse('costing:run_snapshot', args=[self.run.public_id])),
                     ('pricing', reverse('pricing:scenario_detail', args=[self.scenario.pk]))]
            for width in (1440, 1280, 768, 390):
                page.set_viewport_size({'width': width, 'height': 960 if width >= 1280 else 844})
                for slug, path in paths:
                    page.goto(self.live_server_url + path)
                    page.wait_for_function('window.Alpine !== undefined')
                    self.assert_fits(page, (slug, width))
                    page.screenshot(path=str(self.folder / f'{slug}-{width}.png'), full_page=True)
            page.goto(self.live_server_url + reverse('product:item_create'))
            page.get_by_role('button', name='Lưu vật tư / hàng hóa', exact=True).click()
            expect(page.locator('#id_code')).to_be_focused()
            expect(page.locator('#id_code')).to_have_attribute('aria-invalid', 'true')
            self.assertEqual(errors, [])
            self.assertEqual(missing, [])
            browser.close()

    def test_resize_fits_without_navigation_or_animation_wait(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1600, 'height': 1050})
            for name, args in (('costing:run_snapshot', [self.run.public_id]),
                               ('costing:scheme_detail', [self.demo.records['scheme'].pk])):
                page.set_viewport_size({'width': 1600, 'height': 1050})
                page.goto(self.live_server_url + reverse(name, args=args))
                page.set_viewport_size({'width': 390, 'height': 844})
                self.assert_fits(page, name)
            browser.close()

    def test_all_menu_lists_and_top_level_forms_responsive(self):
        from playwright.sync_api import sync_playwright, expect
        from django.urls import NoReverseMatch
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(locale='vi-VN')
            errors, missing = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('response', lambda r: missing.append(r.url) if '/static/' in r.url and r.status >= 400 else None)
            for width in (1440, 1280, 768, 390):
                page.set_viewport_size({'width': width, 'height': 960 if width >= 1280 else 844})
                for resource, url_name in DESTINATIONS.values():
                    response = page.goto(self.live_server_url + reverse(url_name))
                    self.assertEqual(response.status, 200, (width, url_name))
                    expect(page.locator('h1')).to_have_count(1)
                    expect(page.locator('#workspace-sidebar .ui-nav-link')).to_have_count(28)
                    self.assert_fits(page, (url_name, width))
                if width in (1440, 390):
                    for resource, url_name in DESTINATIONS.values():
                        if not url_name.endswith('_list'):
                            continue
                        try:
                            path = reverse(url_name[:-5] + '_create')
                        except NoReverseMatch:
                            continue
                        response = page.goto(self.live_server_url + path)
                        self.assertEqual(response.status, 200, (width, path))
                        self.assert_fits(page, (path, width))
            self.assertEqual(errors, [])
            self.assertEqual(missing, [])
            browser.close()

    def test_density_collapsed_navigation_tooltip_mobile_and_reduced_motion(self):
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1440, 'height': 960}, locale='vi-VN')
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(self.live_server_url + reverse('product:item_list'))
            row = page.locator('table tbody tr').first
            compact_height = row.bounding_box()['height']
            page.get_by_role('button', name='Mật độ thoáng', exact=True).click()
            expect(page.locator('html')).to_have_attribute('data-density', 'comfortable')
            self.assertGreater(row.bounding_box()['height'], compact_height)
            page.reload()
            expect(page.locator('html')).to_have_attribute('data-density', 'comfortable')
            page.get_by_role('button', name='Mật độ gọn', exact=True).click()
            expect(page.locator('html')).to_have_attribute('data-density', 'compact')
            page.get_by_role('button', name='Đóng hoặc mở thanh điều hướng').click()
            expect(page.locator('#workspace-sidebar')).to_have_css('width', '72px')
            links = page.locator('#workspace-sidebar .ui-nav-link')
            self.assertEqual(links.count(), 28)
            self.assertTrue(all(links.nth(i).is_visible() for i in range(28)))
            links.first.focus()
            expect(page.get_by_role('tooltip')).to_have_text('Lần tính giá thành')
            page.keyboard.press('Escape')
            expect(page.get_by_role('tooltip')).to_have_count(0)
            page.screenshot(path=str(self.folder / 'collapsed-navigation-1440.png'), full_page=True)
            page.set_viewport_size({'width': 390, 'height': 844})
            page.get_by_role('button', name='Đóng hoặc mở thanh điều hướng').click()
            expect(page.locator('#workspace-sidebar[inert]')).to_have_count(0)
            page.keyboard.press('Escape')
            expect(page.locator('#workspace-sidebar[inert]')).to_have_count(1)
            self.assert_fits(page, 'mobile-sidebar')
            page.emulate_media(reduced_motion='reduce')
            spinner = page.locator('.ui-spinner').first
            self.assertLessEqual(float(spinner.evaluate('e => parseFloat(getComputedStyle(e).animationDuration)')), .001)
            self.assertEqual(errors, [])
            browser.close()
