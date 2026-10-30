"""Deletion contract: isolated real PostgreSQL, real requests, no live data."""
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.db import IntegrityError
from apps.core.models import Supplier, SupplierPrice, CostingRun, RecipeVersion, RecipeLine, FormulaDependency, CostElement, CostingSchemeLine, FormulaVersion
from apps.costing.run_test_data import golden_data

class DeleteHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = golden_data()

    def setUp(self):
        config = override_settings(DEFAULT_ORGANIZATION_ID=self.data.company.pk)
        config.enable(); self.addCleanup(config.disable)

    def url(self, resource, record):
        return f'/master-data/delete/{resource}/{record.pk}/'

    def preview(self, resource, record, **headers):
        return self.client.get(self.url(resource, record), **headers)

    def submit(self, resource, record, **headers):
        preview = self.preview(resource, record)
        self.assertEqual(preview.status_code, 200)
        return self.client.post(self.url(resource, record), {'confirmation': preview.context['confirmation_token']}, **headers)

    def test_independent_supplier_confirm_then_delete(self):
        record = Supplier.objects.create(organization=self.data.company, code='UNUSED', name='Nhập nhầm')
        preview = self.preview('supplier', record)
        self.assertContains(preview, 'Xác nhận xóa')
        self.assertTrue(Supplier.objects.filter(pk=record.pk).exists())
        self.assertContains(preview, 'csrfmiddlewaretoken')
        response = self.submit('supplier', record)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/master-data/suppliers/')
        self.assertFalse(Supplier.objects.filter(pk=record.pk).exists())

    def test_supplier_with_prices_blocked_including_expired_inactive_relations(self):
        preview = self.preview('supplier', self.data.supplier)
        self.assertContains(preview, 'giá nhà cung cấp')
        self.assertFalse(preview.context['can_delete'])
        response = self.submit('supplier', self.data.supplier)
        self.assertContains(response, 'Không thể xóa')
        self.assertEqual(SupplierPrice.objects.count(), 3)
        self.assertTrue(Supplier.objects.filter(pk=self.data.supplier.pk).exists())

    def test_get_does_not_delete_and_post_needs_confirmation(self):
        record=Supplier.objects.create(organization=self.data.company,code='SAFE',name='An toàn')
        self.assertEqual(self.preview('supplier',record).status_code,200)
        response=self.client.post(self.url('supplier',record))
        self.assertContains(response,'xác nhận')
        self.assertTrue(Supplier.objects.filter(pk=record.pk).exists())

    def test_csrf_required(self):
        record=Supplier.objects.create(organization=self.data.company,code='CSRF',name='CSRF')
        client=Client(enforce_csrf_checks=True)
        page=client.get(self.url('supplier',record))
        self.assertEqual(page.status_code,200)
        self.assertEqual(client.post(self.url('supplier',record),{'confirmation':page.context['confirmation_token']}).status_code,403)
        self.assertTrue(Supplier.objects.filter(pk=record.pk).exists())

    def test_stale_or_other_record_confirmation_cannot_delete(self):
        first=Supplier.objects.create(organization=self.data.company,code='FIRST',name='Ban đầu')
        second=Supplier.objects.create(organization=self.data.company,code='SECOND',name='Khác')
        token=self.preview('supplier',first).context['confirmation_token']
        Supplier.objects.filter(pk=first.pk).update(name='Đã thay đổi')
        for record in (first,second):
            response=self.client.post(self.url('supplier',record),{'confirmation':token})
            self.assertContains(response,'xác nhận')
            self.assertTrue(Supplier.objects.filter(pk=record.pk).exists())

    def test_missing_and_repeated_delete_safe(self):
        record=Supplier.objects.create(organization=self.data.company,code='ONCE',name='Một lần')
        url=self.url('supplier',record)
        token=self.preview('supplier',record).context['confirmation_token']
        self.assertEqual(self.client.post(url,{'confirmation':token}).status_code,302)
        response=self.client.post(url,{'confirmation':token})
        self.assertContains(response,'không còn tồn tại')
        self.assertEqual(self.client.get('/master-data/delete/supplier/9223372036854775808/').status_code,404)
        self.assertEqual(self.client.get('/master-data/delete/not_allowed/1/').status_code,404)

    def test_htmx_confirmation_and_success(self):
        record=Supplier.objects.create(organization=self.data.company,code='HX',name='HTMX')
        page=self.preview('supplier',record,HTTP_HX_REQUEST='true')
        self.assertContains(page,'role="dialog"')
        self.assertNotContains(page,'<!doctype')
        token=page.context['confirmation_token']
        result=self.client.post(self.url('supplier',record),{'confirmation':token},HTTP_HX_REQUEST='true')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result['HX-Redirect'],'/master-data/suppliers/')

    def test_published_price_never_deletable(self):
        response=self.submit('supplier_price',self.data.prices[0],HTTP_HX_REQUEST='true')
        self.assertContains(response,'đã chốt')
        self.assertTrue(SupplierPrice.objects.filter(pk=self.data.prices[0].pk).exists())

    def test_draft_version_deletes_only_owned_lines(self):
        version=self.data.recipe_version
        material_ids=[i.pk for i in self.data.items]
        response=self.submit('bom_version',version)
        self.assertEqual(response.status_code,302)
        self.assertFalse(RecipeVersion.objects.filter(pk=version.pk).exists())
        self.assertFalse(RecipeLine.objects.filter(recipe_version_id=version.pk).exists())
        self.assertEqual(list(self.data.recipe.__class__.objects.values_list('pk',flat=True)),[self.data.recipe.pk])
        self.assertEqual(list(self.data.items[0].__class__.objects.order_by('pk').values_list('pk',flat=True)),material_ids)

    def test_header_with_version_blocked(self):
        page=self.preview('bom',self.data.recipe)
        self.assertFalse(page.context['can_delete'])
        self.assertContains(self.submit('bom',self.data.recipe),'Không thể xóa')

    def test_draft_price_deleted_without_touching_supplier_or_item(self):
        price=SupplierPrice.objects.create(organization=self.data.company,supplier=self.data.supplier,item=self.data.items[0],
            currency_code=self.data.currency,price_uom=self.data.kg,unit_price=Decimal(1),effective_from=self.data.day)
        response=self.submit('supplier_price',price)
        self.assertEqual(response.status_code,302)
        self.assertFalse(SupplierPrice.objects.filter(pk=price.pk).exists())
        self.assertTrue(Supplier.objects.filter(pk=self.data.supplier.pk).exists())

    def test_detail_shows_delete_but_list_and_create_do_not_gain_header_action(self):
        record=Supplier.objects.create(organization=self.data.company,code='ACTION',name='Thao tác')
        self.assertContains(self.client.get(f'/master-data/suppliers/{record.pk}/'),self.url('supplier',record))
        self.assertNotContains(self.client.get('/master-data/suppliers/create/'),'data-delete-action')

    def test_database_failure_does_not_report_success_or_leave_partial_delete(self):
        record=Supplier.objects.create(organization=self.data.company,code='DBFAIL',name='Giữ lại')
        with patch.object(Supplier,'delete',side_effect=IntegrityError('private database details')):
            response=self.submit('supplier',record)
        self.assertContains(response,'Không thể xóa')
        self.assertNotContains(response,'private database details')
        self.assertTrue(Supplier.objects.filter(pk=record.pk).exists())
    def test_draft_version_action_visible_from_parent_overview(self):
        for parent_url,resource,row in [('/bom/%s/'%self.data.recipe.pk,'bom_version',self.data.recipe_version),
            ('/bom/packaging/%s/'%self.data.packaging.pk,'packaging_version',self.data.packaging_version),
            ('/bom/routings/%s/'%self.data.routing.pk,'routing_version',self.data.routing_version),
            ('/costing/schemes/%s/'%self.data.scheme.pk,'scheme_version',self.data.scheme_version)]:
            with self.subTest(resource=resource): self.assertContains(self.client.get(parent_url),self.url(resource,row))

    def test_assignment_list_has_delete_and_htmx_removes_row_without_redirect(self):
        listing=f'/bom/packaging/{self.data.packaging.pk}/skus/'
        from django.urls import reverse
        listing=reverse('bom:packaging_assignment_list',args=[self.data.packaging.pk])
        self.assertContains(self.client.get(listing),self.url('packaging_assignment',self.data.assignment))
        response=self.submit('packaging_assignment',self.data.assignment,HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('HX-Redirect',response)
        self.assertContains(response,'hx-swap-oob')
        self.assertFalse(self.data.assignment.__class__.objects.filter(pk=self.data.assignment.pk).exists())
    def test_currency_delete_preserves_existing_three_character_route_contract(self):
        from apps.core.models import Currency
        from django.urls import reverse
        row=Currency.objects.create(code='A/B',name='Three character code')
        detail=self.client.get(reverse('master_data:currency_detail',args=[row.pk]))
        self.assertEqual(detail.status_code,200)
        self.assertContains(detail,reverse('master_data:record_delete',args=['currency',row.pk]))
        self.assertEqual(self.submit('currency',row).status_code,302)
        self.assertFalse(Currency.objects.filter(pk='A/B').exists())
