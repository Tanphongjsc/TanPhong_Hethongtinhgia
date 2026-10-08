"""Compact actual-model fixture used by Run integration/concurrency/browser tests."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from apps.core.models import (
    Organization, Currency, UomCategory, Uom, Product, Sku, Item, Supplier, SupplierPrice,
    Recipe, RecipeVersion, RecipeLine, PackagingConfig, PackagingConfigVersion, PackagingLine, SkuPackagingAssignment,
    WorkCenter, Resource, ResourceRate, Routing, RoutingVersion, RoutingOperation,
    CostPool, CostPoolPeriod, AllocationRule, CostElement, Formula, FormulaVersion,
    CostingScheme, CostingSchemeVersion, CostingSchemeLine,
)


def golden_data():
    data = SimpleNamespace(day=date(2026, 10, 7))
    data.company = Organization.objects.create(code="RUN_TEST", name="Công ty kiểm thử")
    data.currency = Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
    for dimension, code, name, symbol in (("MASS", "KG", "Kilôgam", "kg"), ("COUNT", "BOX", "Hộp", "hộp"), ("TIME", "H", "Giờ", "h")):
        category = UomCategory.objects.create(code=dimension, name=dimension, dimension_code=dimension)
        setattr(data, code.lower(), Uom.objects.create(category=category, code=code, name=name, symbol=symbol))
    data.product = Product.objects.create(organization=data.company, code="CAP", name="Cà phê", costing_uom=data.kg)
    data.sku = Sku.objects.create(organization=data.company, product=data.product, code="CAP_BOX", name="Cà phê đóng hộp", sales_uom=data.box, net_quantity=1, net_quantity_uom=data.kg)
    data.supplier = Supplier.objects.create(organization=data.company, code="SUP", name="Nhà cung cấp thử nghiệm")
    data.items, data.prices = [], []
    for code, kind, unit, price in (("A", "RAW_MATERIAL", data.kg, "10000"), ("B", "RAW_MATERIAL", data.kg, "20000"), ("BOX_ITEM", "PACKAGING", data.box, "5000")):
        item = Item.objects.create(organization=data.company, code=code, name="Vật tư " + code, item_type=kind, base_uom=unit)
        data.items.append(item)
        data.prices.append(SupplierPrice.objects.create(organization=data.company, supplier=data.supplier, item=item, price_uom=unit,
            currency_code=data.currency, unit_price=Decimal(price), status="EFFECTIVE", effective_from=data.day - timedelta(days=30)))
    data.recipe = Recipe.objects.create(organization=data.company, product=data.product, code="RECIPE", name="Định mức cà phê")
    data.recipe_version = RecipeVersion.objects.create(recipe=data.recipe, version_no=1, output_qty=1, output_uom=data.kg, effective_from=data.day-timedelta(days=30))
    data.recipe_lines = [RecipeLine.objects.create(recipe_version=data.recipe_version, component_item=item, qty=qty, uom=data.kg, display_order=i*10)
        for i, (item, qty) in enumerate(zip(data.items[:2], (2, 1)), start=1)]
    data.packaging = PackagingConfig.objects.create(organization=data.company, product=data.product, code="PACK", name="Bao bì hộp")
    data.packaging_version = PackagingConfigVersion.objects.create(packaging_config=data.packaging, version_no=1, effective_from=data.day-timedelta(days=30))
    data.packaging_line = PackagingLine.objects.create(packaging_config_version=data.packaging_version, packaging_item=data.items[2], level_code="PRIMARY", qty=1, uom=data.box)
    data.assignment = SkuPackagingAssignment.objects.create(sku=data.sku, packaging_config=data.packaging, effective_from=data.day-timedelta(days=30))
    data.center = WorkCenter.objects.create(organization=data.company, code="WC", name="Khu phối trộn")
    data.resource = Resource.objects.create(organization=data.company, work_center=data.center, code="MIXER", name="Máy trộn", resource_type="MACHINE")
    data.rate = ResourceRate.objects.create(organization=data.company, resource=data.resource, rate_type="STANDARD", amount=10000, currency_code=data.currency, per_uom=data.h, status="EFFECTIVE", effective_from=data.day-timedelta(days=30))
    data.routing = Routing.objects.create(organization=data.company, product=data.product, code="ROUTE", name="Quy trình cà phê")
    data.routing_version = RoutingVersion.objects.create(routing=data.routing, version_no=1, batch_size=1, batch_uom=data.kg, effective_from=data.day-timedelta(days=30))
    data.operation = RoutingOperation.objects.create(routing_version=data.routing_version, sequence_no=10, operation_code="MIX", operation_name="Phối trộn", work_center=data.center, primary_resource=data.resource, run_time=1, time_uom=data.h)
    data.pool = CostPool.objects.create(organization=data.company, code="POOL", name="Chi phí chung", pool_type="FACTORY_FIXED")
    data.period = CostPoolPeriod.objects.create(pool=data.pool, period_start=data.day-timedelta(days=30), period_end=data.day+timedelta(days=30),
        amount=500000, currency_code=data.currency, normal_capacity=100, capacity_uom=data.box, status="EFFECTIVE")
    data.rule = AllocationRule.objects.create(organization=data.company, pool=data.pool, code="OVERHEAD", name="Phân bổ chi phí chung", basis_type="NORMAL_CAPACITY", basis_uom=data.box, status="EFFECTIVE", effective_from=data.day-timedelta(days=30))
    def element(code, label):
        return CostElement.objects.create(organization=data.company, code=code, name=label, value_type="MONEY", dimension_code="MONEY", currency_code=data.currency,
            default_source_mode="SYSTEM", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING", rounding_scale=6)
    data.elements = {code: element(code, label) for code, label in (("MATERIAL_COST", "Nguyên vật liệu"), ("PACKAGING_COST", "Bao bì"), ("RESOURCE_COST", "Nguồn lực"), ("OVERHEAD_COST", "Chi phí chung"), ("FULL_COST", "Tổng giá thành"))}
    data.formula = Formula.objects.create(organization=data.company, code="TOTAL", name="Tổng giá thành", output_element=data.elements["FULL_COST"])
    data.formula_version = FormulaVersion.objects.create(formula=data.formula, version_no=1, expression="$MATERIAL_COST + $PACKAGING_COST + $RESOURCE_COST + $OVERHEAD_COST", status="EFFECTIVE", validation_status="VALID", effective_from=data.day-timedelta(days=30))
    data.scheme = CostingScheme.objects.create(organization=data.company, code="STD", name="Giá thành sản xuất", purpose="STANDARD_COST")
    data.scheme_version = CostingSchemeVersion.objects.create(scheme=data.scheme, version_no=1, effective_from=data.day-timedelta(days=30))
    data.scheme_lines = {}
    for i, (code, element) in enumerate(data.elements.items(), start=1):
        source = {"source_mode": "FORMULA", "formula_version": data.formula_version} if code == "FULL_COST" else {"source_mode": "SYSTEM", "system_resolver_code": "ALLOCATION:OVERHEAD" if code == "OVERHEAD_COST" else code}
        data.scheme_lines[code] = CostingSchemeLine.objects.create(scheme_version=data.scheme_version, cost_element=element, line_code=code, label=element.name,
            line_type="OUTPUT" if code == "FULL_COST" else "INPUT", cost_scope="MANUFACTURING", display_order=1 if code == "FULL_COST" else i*10, **source)
    return data


def seal(data):
    for record in (data.recipe_version, data.packaging_version, data.routing_version, data.scheme_version):
        type(record).objects.filter(pk=record.pk, status="DRAFT").update(status="EFFECTIVE")


def request_data(data, **changes):
    result = dict(product=data.product, sku=data.sku, scheme=data.scheme, costing_date=data.day, quantity=Decimal(1), quantity_uom=data.box,
        result_currency_code=data.currency, run_type="STANDARD", packaging_quantity=Decimal(1), packaging_uom=data.box, notes="Kiểm thử", manual={})
    result.update(changes)
    return result


def cleanup():
    # Test fixtures only: locked histories cannot be deleted by ordinary ORM.
    from django.db import connection
    if (connection.settings_dict["NAME"], connection.settings_dict["HOST"], connection.settings_dict["USER"]) != ("test_costing_slice", "127.0.0.1", "costing_test"):
        raise RuntimeError("Fixture cleanup requires isolated localhost tests.")
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE public.organization, public.currency, public.uom_category CASCADE")
