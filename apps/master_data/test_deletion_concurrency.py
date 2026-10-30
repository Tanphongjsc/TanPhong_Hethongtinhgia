"""Deletion versus in-flight writers: never change an existing calculation service."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from django.test import TransactionTestCase
from django.db import transaction,connections
from django.core.exceptions import ValidationError
from apps.core.models import Formula,AllocationRule
from apps.master_data.access import Workspace
from apps.master_data.deletion import confirmation_token,delete_record
from apps.costing.run_test_data import golden_data,cleanup

class DeleteConcurrencyTests(TransactionTestCase):
    def setUp(self): self.d=golden_data()
    def tearDown(self): cleanup(); super().tearDown()
    def test_inflight_symbolic_reference_is_not_lost(self):
        formula=Formula.objects.create(organization=self.d.company,code='RACE',name='Đồng thời')
        ready,release=Event(),Event()
        def writer():
            try:
                with transaction.atomic():
                    AllocationRule.objects.create(organization_id=self.d.company.pk,pool_id=self.d.pool.pk,code='RACE_RULE',name='Quy tắc',basis_type='NORMAL_CAPACITY',formula_code=formula.code,effective_from=self.d.day)
                    ready.set()
                    if not release.wait(10): raise AssertionError('Writer release timed out')
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(writer)
            try:
                self.assertTrue(ready.wait(5))
                with self.assertRaises(ValidationError):
                    delete_record(workspace=Workspace(self.d.company),resource='formula',identifier=str(formula.pk),token=confirmation_token('formula',formula))
            finally:
                release.set(); future.result(timeout=10)
        self.assertTrue(Formula.objects.filter(pk=formula.pk).exists())
        self.assertTrue(AllocationRule.objects.filter(code='RACE_RULE').exists())
    def test_inflight_unit_changes_cannot_lose_required_conversion(self):
        from apps.core.models import Uom,UomConversion
        gram=Uom.objects.create(category=self.d.kg.category,code='G',name='Gam',symbol='g')
        conversion=UomConversion.objects.create(organization=self.d.company,from_uom=self.d.kg,to_uom=gram,factor=1000,effective_from=self.d.day)
        for row,field in [(self.d.items[0],'base_uom_id'),(self.d.product,'costing_uom_id'),(self.d.sku,'net_quantity_uom_id'),(self.d.period,'capacity_uom_id')]:
            ready,release=Event(),Event();model=type(row);old=getattr(row,field)
            def writer():
                try:
                    with transaction.atomic():
                        model.objects.filter(pk=row.pk).update(**{field:gram.pk})
                        ready.set()
                        if not release.wait(10): raise AssertionError('Writer release timed out')
                finally: connections.close_all()
            with self.subTest(model=model.__name__),ThreadPoolExecutor(max_workers=1) as executor:
                future=executor.submit(writer)
                try:
                    self.assertTrue(ready.wait(5))
                    with self.assertRaises(ValidationError):
                        delete_record(workspace=Workspace(self.d.company),resource='uom_conversion',identifier=str(conversion.pk),token=confirmation_token('uom_conversion',conversion))
                finally:
                    release.set();future.result(timeout=10)
            self.assertTrue(UomConversion.objects.filter(pk=conversion.pk).exists())
            self.assertEqual(model.objects.get(pk=row.pk).__dict__[field],gram.pk)
            model.objects.filter(pk=row.pk).update(**{field:old})

    def test_deferred_fk_commit_failure_is_safe_validation_error(self):
        from unittest.mock import patch
        from apps.master_data.deletion import DeletionPreview
        from apps.core.models import Supplier,SupplierPrice
        row=self.d.supplier
        # A deferred FK can fail at outer commit, beyond the inner savepoint.
        with patch('apps.master_data.deletion.inspect_deletion',return_value=DeletionPreview(())):
            with self.assertRaises(ValidationError):
                delete_record(workspace=Workspace(self.d.company),resource='supplier',identifier=str(row.pk),token=confirmation_token('supplier',row))
        self.assertTrue(Supplier.objects.filter(pk=row.pk).exists())
        self.assertEqual(SupplierPrice.objects.count(),3)
