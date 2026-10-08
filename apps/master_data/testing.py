"""Create only test fixtures for unmanaged models in an isolated test database.

This does not alter managed=False or use/create business migrations. PostgreSQL
CHECK constraints below mirror the existing production constraints inspected
read-only, so tests exercise real uniqueness/check/FK behavior.
"""
from django.db import connections, models
from django.test.runner import DiscoverRunner

from apps.core.models import CostElement, CostElementGroup, Currency, Item, Organization, OrganizationMember, PackagingConfig, PackagingConfigVersion, PackagingLine, Product, ProductCategory, Recipe, RecipeLine, RecipeVersion, Sku, SkuPackagingAssignment, Supplier, SupplierPrice, Uom, UomCategory, UomConversion
from apps.bom.constants import VERSION_STATUSES
from apps.bom.testing import install_recipe_triggers, install_packaging_triggers
from apps.bom.packaging_constants import LEVELS
from .constants import SUPPLIER_PRICE_STATUSES
from .constants import ACCOUNTING_SCOPES, COST_SCOPES, ROUNDING_MODES, SOURCE_MODES, VALUE_TYPES
from apps.product.constants import ITEM_TYPES
from apps.core.models import WorkCenter, Resource, ResourceRate
from apps.core.models import Routing, RoutingVersion, RoutingOperation
from apps.core.models import CostPool, AllocationRule
from apps.bom.overhead_constants import POOL_TYPES, ALLOCATION_BASES, RULE_STATUSES
from apps.bom.testing import install_routing_triggers
from apps.bom.resource_constants import RESOURCE_TYPES, RATE_STATUSES

TEST_MODELS = (Organization, OrganizationMember, Currency, UomCategory, Uom, ProductCategory, Item, Product, Sku, Supplier, SupplierPrice, UomConversion, CostElementGroup, CostElement, Recipe, RecipeVersion, RecipeLine, PackagingConfig, PackagingConfigVersion, PackagingLine, SkuPackagingAssignment, WorkCenter, Resource, ResourceRate, Routing, RoutingVersion, RoutingOperation, CostPool, AllocationRule)


class CostingTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        connection = connections["default"]
        if connection.settings_dict["HOST"] != "127.0.0.1" or connection.settings_dict.get("USER") != "costing_test":
            raise RuntimeError("Tests require the isolated localhost costing_test instance.")
        if self.keepdb:
            raise RuntimeError("Use a fresh test database; --keepdb is unsupported for unmanaged fixtures.")
        if self.parallel > 1:
            raise RuntimeError("Unmanaged fixture setup supports serial tests only.")
        configuration = super().setup_databases(**kwargs)
        if connection.settings_dict["NAME"] != "test_costing_slice":
            raise RuntimeError("Refusing fixture DDL outside test_costing_slice.")
        with connection.schema_editor() as editor:
            for model in TEST_MODELS:
                editor.create_model(model)
            for field, choices, name in (
                ("value_type", VALUE_TYPES, "value_type"),
                ("default_source_mode", SOURCE_MODES, "source_mode"),
                ("accounting_scope", ACCOUNTING_SCOPES, "accounting_scope"),
                ("cost_scope", COST_SCOPES, "cost_scope"),
                ("rounding_mode", ROUNDING_MODES, "rounding_mode"),
            ):
                editor.add_constraint(CostElement, models.CheckConstraint(condition=models.Q(**{f"{field}__in": tuple(dict(choices))}), name=f"ck_cost_element_{name}"))
            editor.add_constraint(CostElement, models.CheckConstraint(condition=models.Q(rounding_scale__gte=0, rounding_scale__lte=12), name="ck_cost_element_rounding_scale"))
            editor.add_constraint(Currency, models.CheckConstraint(condition=models.Q(decimal_places__gte=0, decimal_places__lte=8), name="ck_currency_decimal_places"))
            editor.add_constraint(Uom, models.CheckConstraint(condition=models.Q(precision__gte=0, precision__lte=12), name="ck_uom_precision"))
            editor.add_constraint(UomConversion, models.CheckConstraint(condition=~models.Q(from_uom=models.F("to_uom")), name="ck_uom_conversion_distinct"))
            editor.add_constraint(UomConversion, models.CheckConstraint(condition=models.Q(factor__gt=0), name="ck_uom_conversion_factor"))
            editor.add_constraint(UomConversion, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_uom_conversion_period"))
            editor.add_constraint(Item, models.CheckConstraint(condition=models.Q(item_type__in=tuple(dict(ITEM_TYPES))), name="ck_item_type"))
            editor.add_constraint(Item, models.CheckConstraint(condition=(models.Q(net_weight__isnull=True) | models.Q(net_weight__gte=0)) & (models.Q(gross_weight__isnull=True) | models.Q(gross_weight__gte=0)), name="ck_item_weight"))
            dimension = models.Q()
            for field in ("length", "width", "height"):
                dimension &= models.Q(**{f"{field}__isnull": True}) | models.Q(**{f"{field}__gte": 0})
            editor.add_constraint(Item, models.CheckConstraint(condition=dimension, name="ck_item_dimension"))
            editor.add_constraint(Sku, models.CheckConstraint(condition=models.Q(net_quantity__gt=0), name="ck_sku_net_quantity"))
            for field in ("min_qty", "unit_price"):
                editor.add_constraint(SupplierPrice, models.CheckConstraint(condition=models.Q(**{f"{field}__gte": 0}), name=f"ck_supplier_price_{field}"))
            editor.add_constraint(SupplierPrice, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_supplier_price_period"))
            editor.add_constraint(SupplierPrice, models.CheckConstraint(condition=models.Q(tax_rate__isnull=True) | models.Q(tax_rate__gte=0, tax_rate__lte=1), name="ck_supplier_price_tax_rate"))
            editor.add_constraint(SupplierPrice, models.CheckConstraint(condition=models.Q(tax_recoverable_ratio__gte=0, tax_recoverable_ratio__lte=1), name="ck_supplier_price_recoverable"))
            editor.add_constraint(SupplierPrice, models.CheckConstraint(condition=models.Q(status__in=tuple(dict(SUPPLIER_PRICE_STATUSES))), name="ck_supplier_price_status"))
            editor.add_constraint(RecipeVersion, models.CheckConstraint(condition=models.Q(output_qty__gt=0), name="ck_recipe_output_qty"))
            editor.add_constraint(RecipeVersion, models.CheckConstraint(condition=models.Q(yield_rate__gt=0, yield_rate__lte=1), name="ck_recipe_yield_rate"))
            editor.add_constraint(RecipeVersion, models.CheckConstraint(condition=models.Q(status__in=tuple(dict(VERSION_STATUSES))), name="ck_recipe_version_status"))
            editor.add_constraint(RecipeVersion, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_recipe_version_period"))
            editor.add_constraint(RecipeVersion, models.CheckConstraint(condition=models.Q(status__in=("DRAFT", "IN_REVIEW")) | models.Q(effective_from__isnull=False), name="ck_recipe_effective_date_required"))
            editor.add_constraint(RecipeLine, models.CheckConstraint(condition=models.Q(qty__gt=0), name="ck_recipe_line_qty"))
            editor.add_constraint(RecipeLine, models.CheckConstraint(condition=models.Q(scrap_rate__gte=0, scrap_rate__lt=1), name="ck_recipe_line_scrap"))
            install_recipe_triggers(editor)
            editor.add_constraint(PackagingConfigVersion, models.CheckConstraint(condition=models.Q(status__in=tuple(dict(VERSION_STATUSES))), name="ck_packaging_config_status"))
            editor.add_constraint(PackagingConfigVersion, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_packaging_config_period"))
            editor.add_constraint(PackagingConfigVersion, models.CheckConstraint(condition=models.Q(status__in=("DRAFT", "IN_REVIEW")) | models.Q(effective_from__isnull=False), name="ck_packaging_effective_date_required"))
            editor.add_constraint(PackagingConfigVersion, models.CheckConstraint(condition=models.Q(gross_weight__isnull=True) | models.Q(gross_weight__gte=0), name="ck_packaging_weight"))
            editor.add_constraint(PackagingConfigVersion, models.CheckConstraint(condition=(models.Q(length__isnull=True) | models.Q(length__gte=0)) & (models.Q(width__isnull=True) | models.Q(width__gte=0)) & (models.Q(height__isnull=True) | models.Q(height__gte=0)), name="ck_packaging_dimension"))
            editor.add_constraint(PackagingLine, models.CheckConstraint(condition=models.Q(qty__gt=0), name="ck_packaging_line_qty"))
            editor.add_constraint(PackagingLine, models.CheckConstraint(condition=models.Q(level_code__in=tuple(dict(LEVELS))), name="ck_packaging_line_level"))
            editor.add_constraint(PackagingLine, models.CheckConstraint(condition=models.Q(units_per_parent__isnull=True) | models.Q(units_per_parent__gt=0), name="ck_packaging_units_parent"))
            editor.add_constraint(SkuPackagingAssignment, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_sku_packaging_period"))
            install_packaging_triggers(editor)
            editor.add_constraint(RoutingVersion, models.CheckConstraint(condition=models.Q(batch_size__isnull=True) | models.Q(batch_size__gt=0), name="ck_routing_batch_size"))
            editor.add_constraint(RoutingVersion, models.CheckConstraint(condition=models.Q(status__in=tuple(dict(VERSION_STATUSES))), name="ck_routing_version_status"))
            editor.add_constraint(RoutingVersion, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_routing_version_period"))
            editor.add_constraint(RoutingVersion, models.CheckConstraint(condition=models.Q(status__in=("DRAFT", "IN_REVIEW")) | models.Q(effective_from__isnull=False), name="ck_routing_effective_date_required"))
            editor.add_constraint(RoutingOperation, models.CheckConstraint(condition=models.Q(setup_time__gte=0, run_time__gte=0), name="ck_routing_operation_time"))
            editor.add_constraint(RoutingOperation, models.CheckConstraint(condition=models.Q(quantity_basis__isnull=True) | models.Q(quantity_basis__gt=0), name="ck_routing_operation_qty"))
            install_routing_triggers(editor)
            from apps.formula_engine.testing import install_formula_fixtures
            install_formula_fixtures(editor)
            from apps.costing.testing import install_scheme_fixtures
            install_scheme_fixtures(editor)
            from apps.costing.run_testing import install_run_fixtures
            install_run_fixtures(editor)
            from apps.pricing.testing import install_pricing_fixtures
            install_pricing_fixtures(editor)
            editor.add_constraint(CostPool, models.CheckConstraint(condition=models.Q(pool_type__in=tuple(dict(POOL_TYPES))), name="ck_cost_pool_type"))
            editor.add_constraint(AllocationRule, models.CheckConstraint(condition=models.Q(basis_type__in=tuple(dict(ALLOCATION_BASES))), name="ck_allocation_basis"))
            editor.add_constraint(AllocationRule, models.CheckConstraint(condition=models.Q(status__in=tuple(dict(RULE_STATUSES))), name="ck_allocation_rule_status"))
            editor.add_constraint(AllocationRule, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_allocation_rule_period"))
            editor.add_constraint(WorkCenter, models.CheckConstraint(condition=(models.Q(capacity_value__isnull=True) | models.Q(capacity_value__gte=0)) & (models.Q(normal_capacity_value__isnull=True) | models.Q(normal_capacity_value__gte=0)), name="ck_work_center_capacity"))
            editor.add_constraint(Resource, models.CheckConstraint(condition=models.Q(resource_type__in=tuple(dict(RESOURCE_TYPES))), name="ck_resource_type"))
            editor.add_constraint(ResourceRate, models.CheckConstraint(condition=models.Q(amount__gte=0), name="ck_resource_rate_amount"))
            editor.add_constraint(ResourceRate, models.CheckConstraint(condition=models.Q(status__in=tuple(dict(RATE_STATUSES))), name="ck_resource_rate_status"))
            editor.add_constraint(ResourceRate, models.CheckConstraint(condition=models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=models.F("effective_from")), name="ck_resource_rate_period"))
        # Django generates names for unique_together. Match the inspected
        # production names so race tests exercise the correct error mapping.
        with connection.schema_editor() as editor, connection.cursor() as cursor:
            from apps.core.models import Channel, CostingScheme, CostingSchemeVersion, CostingSchemeLine, Formula, FormulaVersion, CostingRun, CostingRunLine
            for model, names in (
                (Channel, {("organization_id", "code"): "uq_channel"}),
                (CostingRun, {("organization_id", "idempotency_key"): "uq_costing_run_idempotency", ("organization_id", "run_no"): "uq_costing_run_no", ("public_id",): "uq_costing_run_public_id"}),
                (CostingRunLine, {("run_id", "line_code"): "uq_costing_run_line_code", ("run_id", "display_order"): "uq_costing_run_line_order"}),
                (CostingScheme, {("organization_id", "code"): "uq_costing_scheme"}),
                (CostingSchemeVersion, {("scheme_id", "version_no"): "uq_costing_scheme_version"}),
                (CostingSchemeLine, {("scheme_version_id", "line_code"): "uq_costing_scheme_line_code", ("scheme_version_id", "display_order"): "uq_costing_scheme_line_order"}),
                (Formula, {("organization_id", "code"): "uq_formula"}),
                (FormulaVersion, {("formula_id", "version_no"): "uq_formula_version"}),
                (CostPool, {("organization_id", "code"): "uq_cost_pool"}),
                (AllocationRule, {("organization_id", "code"): "uq_allocation_rule"}),
                (Routing, {("organization_id", "code"): "uq_routing"}),
                (RoutingVersion, {("routing_id", "version_no"): "uq_routing_version"}),
                (RoutingOperation, {("routing_version_id", "sequence_no"): "uq_routing_operation_sequence"}),
                (WorkCenter, {("organization_id", "code"): "uq_work_center"}),
                (Resource, {("organization_id", "code"): "uq_resource"}),
                (Product, {("organization_id", "code"): "uq_product"}),
                (Supplier, {("organization_id", "code"): "uq_supplier"}),
                (Recipe, {("organization_id", "code"): "uq_recipe"}),
                (RecipeVersion, {("recipe_id", "version_no"): "uq_recipe_version"}),
                (PackagingConfig, {("organization_id", "code"): "uq_packaging_config"}),
                (PackagingConfigVersion, {("packaging_config_id", "version_no"): "uq_packaging_config_version"}),
                (SkuPackagingAssignment, {("sku_id", "packaging_config_id", "effective_from"): "uq_sku_packaging_assignment"}),
                (Sku, {("organization_id", "code"): "uq_sku", ("organization_id", "barcode"): "uq_sku_barcode"}),
            ):
                for name, constraint in connection.introspection.get_constraints(cursor, model._meta.db_table).items():
                    target = names.get(tuple(constraint["columns"])) if constraint["unique"] else None
                    if target and name != target:
                        editor.execute("ALTER TABLE %s RENAME CONSTRAINT %s TO %s" % (
                            editor.quote_name(model._meta.db_table), editor.quote_name(name), editor.quote_name(target),
                        ))
        return configuration
