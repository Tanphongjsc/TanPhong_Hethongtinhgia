"""Real Chromium confirmation, cancel, submit-once and HTMX row refresh."""
import os
from pathlib import Path
from unittest import skipUnless
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.urls import reverse
from apps.core.models import Supplier,RecipeVersion,RecipeLine,SkuPackagingAssignment,Item
from apps.costing.run_test_data import golden_data,cleanup

@skipUnless(os.environ.get('COSTING_BROWSER_TESTS')=='1','Opt-in real Chromium checks.')
class DeleteBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.d=golden_data()
        setting=override_settings(DEFAULT_ORGANIZATION_ID=self.d.company.pk);setting.enable();self.addCleanup(setting.disable)
        self.folder=Path(settings.BASE_DIR)/'artifacts/delete-feature/browser';self.folder.mkdir(parents=True,exist_ok=True)
    def tearDown(self): cleanup();super().tearDown()
    def test_modal_cancel_double_submit_and_mobile(self):
        from playwright.sync_api import sync_playwright,expect
        row=Supplier.objects.create(organization=self.d.company,code='DELETE_UI',name='Nhập nhầm <b>giữ nguyên chữ</b>')
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000},locale='vi-VN')
            errors,posts=[],[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:posts.append(r.url) if r.method=='POST' and '/master-data/delete/' in r.url else None)
            url=self.live_server_url+reverse('master_data:supplier_detail',args=[row.pk])
            page.goto(url)
            action=page.get_by_role('link',name='Xóa nhà cung cấp',exact=True)
            action.click()
            dialog=page.get_by_role('dialog',name='Xác nhận xóa',exact=True)
            expect(dialog).to_be_visible();expect(dialog).to_contain_text(row.name)
            self.assertEqual(dialog.locator('b').count(),0)
            page.screenshot(path=str(self.folder/'confirm-desktop.png'),full_page=True)
            dialog.get_by_role('button',name='Hủy',exact=True).click();expect(dialog).not_to_be_visible()
            self.assertEqual(posts,[])
            for width in (768,390):
                page.set_viewport_size({'width':width,'height':844});action.click();expect(dialog).to_be_visible()
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width)
                self.assertLessEqual(dialog.bounding_box()['width'],width)
                page.screenshot(path=str(self.folder/f'confirm-{width}.png'),full_page=True)
                page.keyboard.press('Escape');expect(dialog).not_to_be_visible()
            action.click();expect(dialog).to_be_visible()
            page.locator('#delete-record-form').evaluate('(f)=>{f.requestSubmit();f.requestSubmit();}')
            expect(page).to_have_url(self.live_server_url+reverse('master_data:supplier_list'))
            self.assertEqual(len(posts),1)
            expect(page.get_by_text('Đã xóa nhà cung cấp.',exact=True)).to_be_visible()
            self.assertEqual(errors,[]);browser.close()
        self.assertFalse(Supplier.objects.filter(pk=row.pk).exists())
    def test_dependency_rejection_and_draft_version_owned_rows(self):
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000},locale='vi-VN')
            page.goto(self.live_server_url+reverse('master_data:supplier_detail',args=[self.d.supplier.pk]))
            page.get_by_role('link',name='Xóa nhà cung cấp',exact=True).click()
            dialog=page.get_by_role('dialog',name='Xác nhận xóa',exact=True)
            expect(dialog).to_be_visible();expect(dialog).to_contain_text('giá nhà cung cấp')
            expect(dialog.get_by_role('button',name='Xóa',exact=True)).to_have_count(0)
            page.screenshot(path=str(self.folder/'blocked.png'),full_page=True)
            dialog.get_by_role('button',name='Đóng',exact=True).click()
            page.goto(self.live_server_url+reverse('bom:bom_detail',args=[self.d.recipe.pk]))
            page.get_by_role('link',name='Xóa phiên bản định mức',exact=True).click()
            expect(dialog).to_be_visible();expect(dialog).to_contain_text('2 thành phần định mức')
            dialog.get_by_role('button',name='Xóa',exact=True).click()
            expect(page.get_by_text('Định mức chưa có phiên bản.',exact=True)).to_be_visible()
            browser.close()
        self.assertFalse(RecipeVersion.objects.filter(pk=self.d.recipe_version.pk).exists())
        self.assertEqual(Item.objects.count(),3)
    def test_assignment_delete_updates_table_preserves_query_and_closes_modal(self):
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000},locale='vi-VN')
            path=reverse('bom:packaging_assignment_list',args=[self.d.packaging.pk])+'?q=CAP&sort=-effective_from&per_page=50'
            url=self.live_server_url+path
            page.goto(url)
            page.get_by_role('link',name='Xóa liên kết SKU với bao bì',exact=True).click()
            dialog=page.get_by_role('dialog',name='Xác nhận xóa',exact=True)
            expect(dialog).to_be_visible()
            dialog.get_by_role('button',name='Xóa',exact=True).click()
            expect(dialog).to_have_count(0)
            expect(page).to_have_url(url)
            expect(page.get_by_text('Đã xóa liên kết SKU với bao bì.',exact=True)).to_be_visible()
            expect(page.locator('#reference-data-table')).to_have_attribute('data-per-page','50')
            page.screenshot(path=str(self.folder/'assignment-after.png'),full_page=True)
            browser.close()
        self.assertFalse(SkuPackagingAssignment.objects.filter(pk=self.d.assignment.pk).exists())
