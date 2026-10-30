"""Deletion invariants across all registered screens and indirect references."""
from datetime import timedelta
from decimal import Decimal
import uuid
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core import models as m
from apps.master_data.access import Workspace
from apps.master_data.deletion import confirmation_token, delete_record, inspect_deletion
from apps.costing.run_test_data import golden_data, seal, request_data
from apps.costing.engine.context import ExecutionContext, digest
from apps.costing.run_services import create_run

class DeletePolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls): cls.d=golden_data()
    def setUp(self):
        self.workspace=Workspace(self.d.company)
        config=override_settings(DEFAULT_ORGANIZATION_ID=self.d.company.pk); config.enable(); self.addCleanup(config.disable)
    def remove(self,resource,row):
        return delete_record(workspace=self.workspace,resource=resource,identifier=str(row.pk),token=confirmation_token(resource,row))
    def saved_run(self, **extra):
        return m.CostingRun.objects.create(organization=self.d.company,run_no=str(uuid.uuid4()),scheme_version=self.d.scheme_version,
            product=self.d.product,quantity=1,quantity_uom=self.d.box,result_currency_code=self.d.currency,run_type='STANDARD',effective_at=timezone.now(),idempotency_key=str(uuid.uuid4()),**extra)
    def test_independent_catalog_and_draft_rule_matrix(self):
        d=self.d
        currency=m.Currency.objects.create(code='ABC',name='Tiền kiểm thử')
        category=m.UomCategory.objects.create(code='NEW',name='Nhóm mới',dimension_code='COUNT')
        channel=m.Channel.objects.create(organization=d.company,code='DELETE_CH',name='Trực tiếp',channel_type='D2C')
        rows=[
          ('currency',currency),('uom_category',category),
          ('uom',m.Uom.objects.create(category=d.kg.category,code='TON',name='Tấn',symbol='t')),
          ('product_category',m.ProductCategory.objects.create(organization=d.company,code='CAT',name='Nhóm')),
          ('item',m.Item.objects.create(organization=d.company,code='UNUSED_ITEM',name='Vật tư',item_type='RAW_MATERIAL',base_uom=d.kg)),
          ('product',m.Product.objects.create(organization=d.company,code='UNUSED_PRODUCT',name='Sản phẩm',costing_uom=d.kg)),
          ('sku',m.Sku.objects.create(organization=d.company,product=d.product,code='UNUSED_SKU',name='SKU',sales_uom=d.box,net_quantity=1,net_quantity_uom=d.kg)),
          ('work_center',m.WorkCenter.objects.create(organization=d.company,code='UNUSED_WC',name='Trung tâm')),
          ('resource',m.Resource.objects.create(organization=d.company,code='UNUSED_RESOURCE',name='Máy',resource_type='MACHINE')),
          ('cost_pool',m.CostPool.objects.create(organization=d.company,code='UNUSED_POOL',name='Nhóm',pool_type='FACTORY_FIXED')),
          ('allocation_rule',m.AllocationRule.objects.create(organization=d.company,pool=d.pool,code='UNUSED_RULE',name='Quy tắc',basis_type='NORMAL_CAPACITY',effective_from=d.day)),
          ('resource_rate',m.ResourceRate.objects.create(organization=d.company,resource=d.resource,rate_type='STANDARD',amount=10,currency_code=d.currency,per_uom=d.h,effective_from=d.day)),
          ('channel_fee_rule',m.ChannelFeeRule.objects.create(organization=d.company,channel=channel,fee_type='TEST',fee_base='LIST_PRICE',rate=Decimal('.1'),effective_from=d.day)),
          ('tax_rule',m.TaxRule.objects.create(organization=d.company,jurisdiction_code='VN',tax_type='VAT',tax_base='LIST_PRICE',rate=Decimal('.1'),effective_from=d.day)),
          ('fx_rate',m.FxRate.objects.create(organization=d.company,from_currency_code=d.currency,to_currency_code=currency,rate=1,rate_type='SPOT',effective_at=timezone.now(),source_name='Test',status='DRAFT')),
          ('bom',m.Recipe.objects.create(organization=d.company,product=d.product,code='EMPTY_BOM',name='Định mức trống')),
          ('packaging',m.PackagingConfig.objects.create(organization=d.company,product=d.product,code='EMPTY_PACK',name='Bao bì trống')),
          ('routing',m.Routing.objects.create(organization=d.company,product=d.product,code='EMPTY_ROUTE',name='Quy trình trống')),
          ('formula',m.Formula.objects.create(organization=d.company,code='EMPTY_FORMULA',name='Công thức trống')),
          ('scheme',m.CostingScheme.objects.create(organization=d.company,code='EMPTY_SCHEME',name='Phương án trống',purpose='STANDARD_COST')),
        ]
        # References must be removed first; no implicit cascade from Currency/Channel.
        for resource,row in reversed(rows):
            with self.subTest(resource=resource):
                self.remove(resource,row)
                self.assertFalse(type(row).objects.filter(pk=row.pk).exists())
        self.remove('channel',channel)
    def test_every_master_blocks_its_real_references(self):
        for resource,row in [('currency',self.d.currency),('uom_category',self.d.kg.category),('uom',self.d.kg),('item',self.d.items[0]),
            ('product',self.d.product),('sku',self.d.sku),('work_center',self.d.center),('resource',self.d.resource),('cost_pool',self.d.pool),('cost_element',self.d.elements['MATERIAL_COST'])]:
            with self.subTest(resource=resource):
                self.assertFalse(inspect_deletion(row).allowed)
                with self.assertRaises(ValidationError): self.remove(resource,row)
                self.assertTrue(type(row).objects.filter(pk=row.pk).exists())
    def test_inactive_child_category_is_still_a_dependency(self):
        parent=m.ProductCategory.objects.create(organization=self.d.company,code='PARENT',name='Cha')
        m.ProductCategory.objects.create(organization=self.d.company,parent=parent,code='CHILD',name='Con',is_active=False)
        self.assertFalse(inspect_deletion(parent).allowed)
    def test_formula_code_in_allocation_rule_blocks_formula_deletion(self):
        formula=m.Formula.objects.create(organization=self.d.company,code='FORMULA_REF',name='Tham chiếu mã')
        m.AllocationRule.objects.create(organization=self.d.company,pool=self.d.pool,code='REF',name='Quy tắc',basis_type='NORMAL_CAPACITY',formula_code=formula.code,effective_from=self.d.day)
        with self.assertRaisesMessage(ValidationError,'mã công thức'): self.remove('formula',formula)
    def test_allocation_code_in_scheme_blocks_rule_deletion(self):
        rule=m.AllocationRule.objects.create(organization=self.d.company,pool=self.d.pool,code='DRAFT_REF',name='Quy tắc',basis_type='NORMAL_CAPACITY',effective_from=self.d.day)
        m.CostingSchemeLine.objects.create(scheme_version=self.d.scheme_version,line_code='REF',label='Tham chiếu',source_mode='SYSTEM',system_resolver_code='ALLOCATION:DRAFT_REF',line_type='INPUT',display_order=99,cost_scope='MANUFACTURING')
        with self.assertRaisesMessage(ValidationError,'mã quy tắc'): self.remove('allocation_rule',rule)
    def test_expression_parser_uses_exact_identifiers(self):
        first=m.CostElement.objects.create(organization=self.d.company,code='CODE1',name='Một',value_type='NUMBER',default_source_mode='MANUAL',accounting_scope='ANALYTICS',cost_scope='ANALYTICS',dimension_code='NUMBER')
        second=m.CostElement.objects.create(organization=self.d.company,code='CODE10',name='Mười',value_type='NUMBER',default_source_mode='MANUAL',accounting_scope='ANALYTICS',cost_scope='ANALYTICS',dimension_code='NUMBER')
        f=m.Formula.objects.create(organization=self.d.company,code='PARSE',name='Biểu thức')
        m.FormulaVersion.objects.create(formula=f,version_no=1,expression='$CODE10 + 1')
        self.remove('cost_element',first)
        with self.assertRaisesMessage(ValidationError,'công thức PARSE'): self.remove('cost_element',second)
    def test_complete_historical_snapshot_warns_and_does_not_recompute(self):
        record=m.Supplier.objects.create(organization=self.d.company,code='HISTORY',name='Nhà cung cấp cũ')
        ctx=ExecutionContext(self.d.company,self.d.product,None,self.d.day,Decimal(1),self.d.box,self.d.currency)
        ctx.remember(record)
        snapshot={'schema':1,'sources':ctx.sources}; snapshot['sha256']=digest(snapshot)
        run=self.saved_run(version_snapshot_jsonb=snapshot)
        before=m.CostingRun.objects.values().get(pk=run.pk)
        preview=inspect_deletion(record)
        self.assertTrue(preview.allowed); self.assertTrue(preview.warnings)
        self.remove('supplier',record)
        self.assertEqual(m.CostingRun.objects.values().get(pk=run.pk),before)
    def test_partial_historical_snapshot_blocks(self):
        record=m.Supplier.objects.create(organization=self.d.company,code='PARTIAL',name='Nguồn thiếu')
        self.saved_run(version_snapshot_jsonb={'schema':1,'sources':{f'supplier:{record.pk}':{'table':'supplier','id':record.pk}}})
        self.assertFalse(inspect_deletion(record).allowed)
    def test_hash_mismatch_must_not_be_reported_as_complete_evidence(self):
        record=m.Supplier.objects.create(organization=self.d.company,code='BROKEN_HASH',name='Sai hash')
        ctx=ExecutionContext(self.d.company,self.d.product,None,self.d.day,Decimal(1),self.d.box,self.d.currency); ctx.remember(record)
        self.saved_run(version_snapshot_jsonb={'schema':1,'sources':ctx.sources,'sha256':'0'*64})
        self.assertFalse(inspect_deletion(record).allowed)
    def test_saved_packaging_basis_uom_blocks_even_on_failed_run(self):
        unit=m.Uom.objects.create(category=self.d.box.category,code='BAG',name='Túi',symbol='túi')
        self.saved_run(run_status='FAILED',context_jsonb={'schema':1,'request':{'packaging_uom':unit.pk}})
        self.assertFalse(inspect_deletion(unit).allowed)
    def test_completed_and_failed_runs_preserve_request_identity(self):
        for status in ('DRAFT','FAILED','LOCKED'):
            run=self.saved_run(run_status=status)
            with self.subTest(status=status),self.assertRaisesMessage(ValidationError,'chống gửi lặp'): self.remove('run',run)
            self.assertTrue(m.CostingRun.objects.filter(pk=run.pk).exists())
    def test_draft_scenario_can_delete_but_calculated_cannot(self):
        run=self.saved_run()
        for status in ('DRAFT','CALCULATED'):
            row=m.PriceScenario.objects.create(organization=self.d.company,code=status,name='Kịch bản',base_run=run,currency_code=self.d.currency,pricing_method='MARGIN',status=status)
            if status=='DRAFT': self.remove('scenario',row)
            else:
                with self.assertRaises(ValidationError): self.remove('scenario',row)
        self.assertTrue(m.CostingRun.objects.filter(pk=run.pk).exists())
    def test_unknown_draft_scenario_output_requires_review(self):
        row=m.PriceScenario.objects.create(organization=self.d.company,code='LEGACY',name='Dữ liệu cũ',base_run=self.saved_run(),currency_code=self.d.currency,pricing_method='MARGIN',output_snapshot_jsonb={'schema':99,'legacy_result':'100'})
        self.assertFalse(inspect_deletion(row).allowed)
    def test_published_versions_protected_for_all_five_families(self):
        for resource,row in [('bom_version',self.d.recipe_version),('packaging_version',self.d.packaging_version),('routing_version',self.d.routing_version),('formula_version',self.d.formula_version),('scheme_version',self.d.scheme_version)]:
            if row.status=='DRAFT': type(row).objects.filter(pk=row.pk).update(status='EFFECTIVE'); row.refresh_from_db()
            with self.subTest(resource=resource),self.assertRaisesMessage(ValidationError,'đã chốt'): self.remove(resource,row)
    def test_draft_version_owned_rows_and_shared_formula_tests(self):
        case=m.FormulaTestCase.objects.create(formula=self.d.formula,name='Giữ dùng chung',input_context={},expected_value_numeric=0)
        version=m.FormulaVersion.objects.create(formula=self.d.formula,version_no=2,expression='1')
        dependency=m.FormulaDependency.objects.create(formula_version=version,depends_on_element=self.d.elements['MATERIAL_COST'],dependency_kind='ELEMENT',dependency_code='MATERIAL_COST')
        self.remove('formula_version',version)
        self.assertFalse(m.FormulaDependency.objects.filter(pk=dependency.pk).exists())
        self.assertTrue(m.FormulaTestCase.objects.filter(pk=case.pk).exists())
        self.assertTrue(m.Formula.objects.filter(pk=self.d.formula.pk).exists())
    def test_delete_draft_packaging_and_routing_versions(self):
        self.remove('packaging_version',self.d.packaging_version)
        self.remove('routing_version',self.d.routing_version)
        self.assertFalse(m.PackagingLine.objects.filter(pk=self.d.packaging_line.pk).exists())
        self.assertFalse(m.RoutingOperation.objects.filter(pk=self.d.operation.pk).exists())
        self.assertTrue(m.Resource.objects.filter(pk=self.d.resource.pk).exists())
        self.assertTrue(m.SkuPackagingAssignment.objects.filter(pk=self.d.assignment.pk).exists())
    def test_duplicate_material_lines_delete_one_id_only(self):
        first=self.d.recipe_lines[0]
        other=m.RecipeLine.objects.create(recipe_version=first.recipe_version,component_item=first.component_item,qty=3,uom=first.uom)
        self.remove('bom_line',first)
        self.assertTrue(m.RecipeLine.objects.filter(pk=other.pk).exists())
        self.assertTrue(m.Item.objects.filter(pk=first.component_item_id).exists())
    def test_draft_assignment_not_used_in_snapshot_can_delete(self):
        self.remove('packaging_assignment',self.d.assignment)
        self.assertTrue(m.Sku.objects.filter(pk=self.d.sku.pk).exists())
        self.assertTrue(m.PackagingConfig.objects.filter(pk=self.d.packaging.pk).exists())
    def test_used_conversion_cannot_delete_and_unused_conversion_can(self):
        gram=m.Uom.objects.create(category=self.d.kg.category,code='G',name='Gam',symbol='g')
        conversion=m.UomConversion.objects.create(organization=self.d.company,from_uom=gram,to_uom=self.d.kg,factor=Decimal('.001'),effective_from=self.d.day)
        self.d.recipe_lines[0].uom=gram; self.d.recipe_lines[0].save(update_fields=['uom'])
        with self.assertRaises(ValidationError): self.remove('uom_conversion',conversion)
        self.d.recipe_lines[0].uom=self.d.kg; self.d.recipe_lines[0].save(update_fields=['uom'])
        self.remove('uom_conversion',conversion)
    def test_core_source_record_from_other_scope_cannot_be_deleted(self):
        company=m.Organization.objects.create(code='OTHER',name='Dữ liệu khác')
        row=m.Supplier.objects.create(organization=company,code='OTHER',name='Không thuộc ngữ cảnh')
        self.assertEqual(self.client.get(f'/master-data/delete/supplier/{row.pk}/').status_code,404)
        response=self.client.post(f'/master-data/delete/supplier/{row.pk}/',{'confirmation':confirmation_token('supplier',row)})
        self.assertContains(response,'không còn tồn tại')
        self.assertTrue(m.Supplier.objects.filter(pk=row.pk).exists())
    def test_existing_scheme_remove_url_blocks_hidden_override(self):
        line=self.d.scheme_lines['MATERIAL_COST']
        m.CostingOverride.objects.create(run=self.saved_run(),scheme_line=line,override_value=2,reason='Giữ lại')
        from apps.costing.services import remove_line
        with self.assertRaisesMessage(ValidationError,'điều chỉnh'):
            remove_line(workspace=self.workspace,scheme=self.d.scheme,version=self.d.scheme_version,instance=line)
        self.assertTrue(m.CostingSchemeLine.objects.filter(pk=line.pk).exists())
    def gram_conversion(self):
        gram=m.Uom.objects.create(category=self.d.kg.category,code='G',name='Gam',symbol='g')
        conversion=m.UomConversion.objects.create(organization=self.d.company,from_uom=self.d.kg,to_uom=gram,factor=1000,effective_from=self.d.day)
        return gram,conversion
    def test_conversion_to_supplier_price_unit_is_protected(self):
        gram,conversion=self.gram_conversion()
        price=self.d.prices[0];price.price_uom=gram;price.save(update_fields=['price_uom'])
        with self.assertRaises(ValidationError): self.remove('uom_conversion',conversion)
    def test_output_routing_capacity_and_run_quantity_conversion_paths(self):
        gram,conversion=self.gram_conversion()
        targets=[(self.d.sku,'net_quantity_uom'),(self.d.recipe_version,'output_uom'),
            (self.d.routing_version,'batch_uom'),(self.d.period,'capacity_uom')]
        for row,field in targets:
            old=getattr(row,field);setattr(row,field,gram);row.save(update_fields=[field])
            with self.subTest(model=type(row).__name__):
                self.assertFalse(inspect_deletion(conversion).allowed)
            setattr(row,field,old);row.save(update_fields=[field])
        operation=self.d.operation;operation.quantity_basis=1;operation.quantity_uom=gram
        operation.save(update_fields=['quantity_basis','quantity_uom'])
        with self.assertRaises(ValidationError): self.remove('uom_conversion',conversion)
        operation.quantity_basis=None;operation.quantity_uom=None;operation.save(update_fields=['quantity_basis','quantity_uom'])
        element=m.CostElement.objects.create(organization=self.d.company,code='RUN_KG',name='Quantity',value_type='NUMBER',dimension_code='QUANTITY',default_uom=gram,default_source_mode='SYSTEM',accounting_scope='ANALYTICS',cost_scope='ANALYTICS')
        m.CostingSchemeLine.objects.create(scheme_version=self.d.scheme_version,cost_element=element,line_code='RUN_KG',label='Quantity',source_mode='SYSTEM',system_resolver_code='RUN_QUANTITY',line_type='INPUT',display_order=99,cost_scope='MANUFACTURING')
        with self.assertRaises(ValidationError): self.remove('uom_conversion',conversion)
    def test_version_confirmation_rejects_changed_owned_lines(self):
        version=self.d.recipe_version;token=confirmation_token('bom_version',version)
        line=self.d.recipe_lines[0];line.qty=5;line.save(update_fields=['qty'])
        with self.assertRaisesMessage(ValidationError,'\u0111\u00e3 thay \u0111\u1ed5i'):
            delete_record(workspace=self.workspace,resource='bom_version',identifier=str(version.pk),token=token)
        self.assertTrue(m.RecipeVersion.objects.filter(pk=version.pk).exists())
        self.assertEqual(m.RecipeLine.objects.get(pk=line.pk).qty,5)
    def test_malformed_typed_source_keys_block_incomplete_history(self):
        row=m.Supplier.objects.create(organization=self.d.company,code='BAD_SOURCE',name='History')
        run=self.saved_run()
        for value in (None,[],{'id':None,'fields':None},{'table':{},'id':row.pk}):
            run.version_snapshot_jsonb={'schema':1,'sources':{f'supplier:{row.pk}':value}}
            run.save(update_fields=['version_snapshot_jsonb'])
            with self.subTest(value=value): self.assertFalse(inspect_deletion(row).allowed)
    def test_malformed_unrelated_history_does_not_crash_or_block(self):
        row=m.Supplier.objects.create(organization=self.d.company,code='OTHER_HISTORY',name='History')
        run=self.saved_run(version_snapshot_jsonb={'schema':1,'sources':[{'table':{},'id':row.pk}]},context_jsonb={'request':None})
        scenario=m.PriceScenario.objects.create(organization=self.d.company,code='BAD_TRACE',name='History',base_run=run,currency_code=self.d.currency,pricing_method='MARGIN',output_snapshot_jsonb={'trace':None,'note':str(row.pk)})
        self.assertTrue(inspect_deletion(row).allowed)
        unit=m.Uom.objects.create(category=self.d.box.category,code='BAD_TRACE_UNIT',name='Unit',symbol='u')
        run.context_jsonb={'request':None};run.save(update_fields=['context_jsonb'])
        self.assertTrue(inspect_deletion(unit).allowed)
    def test_invalid_formula_in_other_scope_does_not_block(self):
        row=m.CostElement.objects.create(organization=self.d.company,code='LOCAL_ONLY',name='Local',value_type='NUMBER',dimension_code='NUMBER',default_source_mode='MANUAL',accounting_scope='ANALYTICS',cost_scope='ANALYTICS')
        company=m.Organization.objects.create(code='OTHER_FORMULA',name='Other')
        formula=m.Formula.objects.create(organization=company,code='BAD',name='Other')
        m.FormulaVersion.objects.create(formula=formula,version_no=1,expression='$LOCAL_ONLY +')
        self.assertTrue(inspect_deletion(row).allowed)

    def test_real_foreign_key_failure_rolls_back_owned_version_removal(self):
        from unittest.mock import patch
        from django.db import connection
        from apps.master_data.deletion import DeletionPreview
        line=self.d.scheme_lines['MATERIAL_COST'];version=self.d.scheme_version
        m.CostingOverride.objects.create(run=self.saved_run(),scheme_line=line,override_value=2,reason='Keep history')
        before=m.CostingSchemeLine.objects.filter(scheme_version=version).count()
        # Simulate a reference discovered after preview. The real PostgreSQL FK,
        # not a mocked delete() exception, must still preserve the whole version.
        with connection.cursor() as cursor: cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        with patch('apps.master_data.deletion.inspect_deletion',return_value=DeletionPreview(())):
            with self.assertRaises(ValidationError): self.remove('scheme_version',version)
        self.assertTrue(m.CostingSchemeVersion.objects.filter(pk=version.pk).exists())
        self.assertEqual(m.CostingSchemeLine.objects.filter(scheme_version=version).count(),before)
        self.assertTrue(m.CostingOverride.objects.filter(scheme_line=line).exists())
