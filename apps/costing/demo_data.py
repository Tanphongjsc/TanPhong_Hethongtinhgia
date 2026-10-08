"""One deterministic DEMO dataset, using the existing internal company only.

Never updates existing records or disables database protections. Business writes
use the same services as the UI. Publication of upstream demo source definitions
is command-only, after their existing validators; this is not an approval UI.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core import models as m
from apps.master_data.access import Workspace
from apps.master_data.company_context import get_default_organization
from apps.master_data import services as masters, constants as mc
from apps.product import services as products, constants as pc
from apps.bom import services as recipes, constants as rc, validators as rv
from apps.bom import packaging_services as packs, packaging_constants as pac, packaging_validators as pav
from apps.bom import routing_services as routes, routing_constants as rtc, routing_validators as rtv
from apps.bom import resource_services as resources, resource_constants as resc
from apps.bom import overhead_services as overhead, overhead_constants as oc
from apps.formula_engine import services as formulas, constants as fc
from apps.formula_engine.engine import build_plan
from . import services as schemes, constants as sc

D = Decimal
START = date(2026, 10, 1)
OLD_END = date(2026, 10, 31)
FUTURE = date(2026, 11, 1)
DAY = date(2026, 10, 7)
MARKER = "DEMO_CAPPUCCINO_V1"


def values(model, fields, **overrides):
    """Complete service allow-list, retaining model defaults and Decimal types."""
    data = {}
    for name in fields:
        model_field = model._meta.get_field(name)
        value = model_field.get_default()
        if model_field.get_internal_type() == "DecimalField" and value is not None:
            value = D(str(value))
        data[name] = value
    data.update(overrides)
    return data


def matches(record, data):
    for name, expected in data.items():
        model_field = record._meta.get_field(name)
        actual = getattr(record, model_field.attname)
        expected = getattr(expected, "pk", expected)
        if model_field.null and actual in (None, "") and expected in (None, ""):
            continue
        if actual != expected:
            raise ValidationError(f"Dữ liệu mẫu {record._meta.label}:{record.pk} khác định nghĩa ở trường {name}. Không ghi đè; hãy kiểm tra dữ liệu.")
    return record


@dataclass
class DemoData:
    workspace: Workspace
    records: dict = field(default_factory=dict)
    created: dict = field(default_factory=dict)

    def ensure(self, key, model, lookup, data, create):
        found = list(model.objects.filter(**lookup).order_by("pk")[:2])
        if len(found) > 1:
            raise ValidationError(f"Có nhiều bản ghi mẫu {model._meta.label}; không tự chọn dữ liệu.")
        record = matches(found[0], data) if found else create()
        if not found:
            self.created[model.__name__] = self.created.get(model.__name__, 0) + 1
        self.records[key] = record
        return record

    def master(self, key, model, service, fields, **data):
        data = values(model, fields, **data)
        lookup = {"code": data["code"]}
        if any(f.name == "organization" for f in model._meta.fields):
            lookup["organization"] = self.workspace.organization
        return self.ensure(key, model, lookup, data,
            lambda: service(workspace=self.workspace, data=data))


def _reference_masters(demo):
    # Existing global reference masters are shared: do not rename or duplicate.
    for code, name, decimals in (("VND", "Đồng Việt Nam", 0), ("USD", "Đô la Mỹ", 2)):
        found = m.Currency.objects.filter(pk=code).first()
        if found:
            matches(found, {"is_active": True, "decimal_places": decimals})
            demo.records[code] = found
        else:
            demo.master(code, m.Currency, masters.save_currency, mc.CURRENCY_FIELDS,
                code=code, name=name, decimal_places=decimals, is_active=True)
    for dimension, name in (("MASS", "Khối lượng"), ("TIME", "Thời gian"), ("COUNT", "Số lượng")):
        category = m.UomCategory.objects.filter(code=dimension).first()
        if category:
            matches(category, {"dimension_code": dimension, "is_active": True})
            demo.records[dimension] = category
        else:
            demo.master(dimension, m.UomCategory, masters.save_uom_category, mc.UOM_CATEGORY_FIELDS,
                code="DEMO_" + dimension, name=name, dimension_code=dimension, is_active=True)
    units = (("kg", "KG", "Kilôgam", "kg", "MASS", True),
        ("g", "G", "Gam", "g", "MASS", False),
        ("hour", "HOUR", "Giờ", "h", "TIME", True),
        ("minute", "MINUTE", "Phút", "phút", "TIME", False),
        ("piece", "DEMO_PIECE", "Cái", "cái", "COUNT", False),
        ("box", "DEMO_BOX_UOM", "Hộp", "hộp", "COUNT", False))
    for key, code, name, symbol, dimension, base in units:
        found = m.Uom.objects.select_related("category").filter(code=code).first()
        if found and not code.startswith("DEMO_"):
            matches(found, {"category": demo.records[dimension], "is_active": True})
            demo.records[key] = found
        else:
            demo.master(key, m.Uom, masters.save_uom, mc.UOM_FIELDS, code=code, name=name,
                symbol=symbol, category=demo.records[dimension], precision=6, is_base=base, is_active=True)
    for key, from_key, to_key, factor in (("mass_conversion", "g", "kg", D("0.001")),
            ("time_conversion", "hour", "minute", D("60"))):
        data = values(m.UomConversion, mc.UOM_CONVERSION_FIELDS,
            from_uom=demo.records[from_key], to_uom=demo.records[to_key], factor=factor,
            effective_from=START, source_reference=MARKER + ":" + key)
        # Refuse to duplicate an existing global/company conversion of this pair.
        from django.db.models import Q
        pair = Q(from_uom=data["from_uom"], to_uom=data["to_uom"]) | Q(from_uom=data["to_uom"], to_uom=data["from_uom"])
        foreign = m.UomConversion.objects.filter(pair, Q(organization=demo.workspace.organization) | Q(organization__isnull=True),
            item__isnull=True).exclude(source_reference=data["source_reference"])
        if foreign.exists():
            raise ValidationError("Cặp quy đổi của dữ liệu mẫu đã có nguồn khác. Không tạo quy đổi mơ hồ hoặc sửa dữ liệu có sẵn.")
        demo.ensure(key, m.UomConversion, {"organization": demo.workspace.organization, "source_reference": data["source_reference"]}, data,
            lambda data=data: masters.save_uom_conversion(workspace=demo.workspace, data=data))


def _publish_source(record):
    """Only our freshly validated Draft records; never rewrites sealed sources."""
    if record.status == "EFFECTIVE":
        return
    if record.status != "DRAFT":
        raise ValidationError("Nguồn mẫu không ở trạng thái Nháp để chốt dữ liệu.")
    record.status = "EFFECTIVE"
    record.full_clean(exclude=("condition_jsonb",), validate_unique=False, validate_constraints=False)
    record.save(update_fields=["status"])


def _version(demo, key, model, parent_field, parent, data):
    version = model.objects.get(**{parent_field: parent, "version_no": 1})
    matches(version, data)
    demo.records[key] = version
    return version


def _seed_sources(demo):
    w, r = demo.workspace, demo.records
    demo.master("category", m.ProductCategory, products.save_category, pc.CATEGORY_FIELDS,
        code="DEMO_COFFEE", name="Cà phê", description="Nhóm sản phẩm mẫu đối soát giá thành.", is_active=True)
    for key, code, name, kind, unit in (("coffee", "DEMO_INSTANT_COFFEE", "Cà phê hòa tan", "RAW_MATERIAL", r["kg"]),
        ("sugar", "DEMO_SUGAR", "Đường", "RAW_MATERIAL", r["kg"]),
        ("sachet", "DEMO_SACHET", "Túi sachet", "PACKAGING", r["piece"]),
        ("box_item", "DEMO_BOX", "Hộp giấy", "PACKAGING", r["piece"])):
        demo.master(key, m.Item, products.save_item, pc.ITEM_FIELDS, code=code, name=name, item_type=kind,
            category=r["category"], base_uom=unit, purchase_uom=unit, production_uom=unit, is_stock_item=True, is_active=True)
    demo.master("product", m.Product, products.save_product, pc.PRODUCT_FIELDS,
        code="DEMO_CAPPUCCINO", name="Cà phê Cappuccino mẫu", category=r["category"], costing_uom=r["box"],
        description="Dữ liệu mẫu thống nhất để kiểm chứng giá thành.", is_active=True)
    demo.master("sku", m.Sku, products.save_sku, pc.SKU_FIELDS,
        code="DEMO_CAPPUCCINO_BOX20", name="Cappuccino 20 gói / hộp", product=r["product"],
        sales_uom=r["box"], net_quantity=D("0.5"), net_quantity_uom=r["kg"], is_active=True)
    demo.master("supplier", m.Supplier, masters.save_supplier, mc.SUPPLIER_FIELDS,
        code="DEMO_SUPPLIER", name="Nhà cung cấp mẫu", default_currency_code=r["VND"], is_active=True)
    for key, amount in (("coffee", "100000"), ("sugar", "20000"), ("sachet", "500"), ("box_item", "5000")):
        _price(demo, key + "_price", key, D(amount), START, OLD_END if key == "coffee" else None)
    recipe_data = values(m.RecipeVersion, rc.VERSION_FIELDS, output_qty=D(1), output_uom=r["box"], yield_rate=D(1),
        effective_from=START, change_reason="Dữ liệu mẫu ban đầu.")
    demo.ensure("recipe", m.Recipe, {"organization": w.organization, "code": "DEMO_BOM_CAPPUCCINO"},
        {"product": r["product"], "code": "DEMO_BOM_CAPPUCCINO", "name": "Định mức Cappuccino mẫu", "description": None, "is_active": True},
        lambda: recipes.save_recipe(workspace=w, data=values(m.Recipe, rc.RECIPE_FIELDS,
            product=r["product"], code="DEMO_BOM_CAPPUCCINO", name="Định mức Cappuccino mẫu", is_active=True), initial_version=recipe_data))
    version = _version(demo, "recipe_version", m.RecipeVersion, "recipe", r["recipe"], recipe_data)
    for order, key, qty in ((10, "coffee", "200"), (20, "sugar", "300")):
        data = values(m.RecipeLine, rc.LINE_FIELDS, component_item=r[key], qty=D(qty), uom=r["g"], scrap_rate=D(0), display_order=order)
        demo.ensure(key + "_line", m.RecipeLine, {"recipe_version": version, "display_order": order}, data,
            lambda data=data: recipes.save_line(workspace=w, recipe=r["recipe"], version=version, data=data))
    if m.RecipeLine.objects.filter(recipe_version=version).count() != 2:
        raise ValidationError("Định mức mẫu có thành phần ngoài định nghĩa.")
    rv.validate_version(data=recipe_data, organization=w.organization, instance=version)
    rv.validate_conversions(lines=[(r[k], r["g"]) for k in ("coffee", "sugar")], organization=w.organization, effective_from=START)
    _publish_source(version)
    pack_data = values(m.PackagingConfigVersion, pac.VERSION_FIELDS, effective_from=START, change_reason="Dữ liệu mẫu ban đầu.")
    demo.ensure("packaging", m.PackagingConfig, {"organization": w.organization, "code": "DEMO_PACK_CAPPUCCINO"},
        {"product": r["product"], "code": "DEMO_PACK_CAPPUCCINO", "name": "Bao bì Cappuccino 20 gói", "description": None, "is_active": True},
        lambda: packs.save_config(workspace=w, data=values(m.PackagingConfig, pac.CONFIG_FIELDS,
            product=r["product"], code="DEMO_PACK_CAPPUCCINO", name="Bao bì Cappuccino 20 gói", is_active=True), initial_version=pack_data))
    pv = _version(demo, "packaging_version", m.PackagingConfigVersion, "packaging_config", r["packaging"], pack_data)
    for order, key, qty, level in ((10, "sachet", "20", "PRIMARY"), (20, "box_item", "1", "SECONDARY")):
        data = values(m.PackagingLine, pac.LINE_FIELDS, packaging_item=r[key], qty=D(qty), uom=r["piece"], level_code=level, display_order=order)
        demo.ensure(key + "_pack_line", m.PackagingLine, {"packaging_config_version": pv, "display_order": order}, data,
            lambda data=data: packs.save_line(workspace=w, config=r["packaging"], version=pv, data=data))
    if m.PackagingLine.objects.filter(packaging_config_version=pv).count() != 2:
        raise ValidationError("Bao bì mẫu có thành phần ngoài định nghĩa.")
    pav.validate_version(data=pack_data, organization=w.organization, instance=pv)
    _publish_source(pv)
    assignment_data = values(m.SkuPackagingAssignment, pac.ASSIGNMENT_FIELDS, sku=r["sku"], effective_from=START, is_primary=True)
    demo.ensure("assignment", m.SkuPackagingAssignment, {"sku": r["sku"], "packaging_config": r["packaging"], "effective_from": START}, assignment_data,
        lambda: packs.save_assignment(workspace=w, config=r["packaging"], data=assignment_data))
    for key, code, name in (("mixing", "DEMO_WC_MIXING", "Khu vực phối trộn mẫu"), ("packing", "DEMO_WC_PACKING", "Khu vực đóng gói mẫu")):
        demo.master(key, m.WorkCenter, resources.save_work_center, resc.WORK_CENTER_FIELDS, code=code, name=name, is_active=True)
    for key, code, name, kind, center, amount in (("mixer", "DEMO_MIXER", "Máy trộn mẫu", "MACHINE", "mixing", "120000"),
        ("labor", "DEMO_PACKING_LABOR", "Nhân công đóng gói mẫu", "LABOR", "packing", "60000")):
        demo.master(key, m.Resource, resources.save_resource, resc.RESOURCE_FIELDS,
            code=code, name=name, resource_type=kind, work_center=r[center], is_active=True)
        _rate(demo, key + "_rate", key, D(amount), START, OLD_END)
    route_data = values(m.RoutingVersion, rtc.VERSION_FIELDS, batch_size=D(1), batch_uom=r["box"],
        effective_from=START, change_reason="Dữ liệu mẫu ban đầu.")
    demo.ensure("routing", m.Routing, {"organization": w.organization, "code": "DEMO_ROUTE_CAPPUCCINO"},
        {"product": r["product"], "code": "DEMO_ROUTE_CAPPUCCINO", "name": "Quy trình Cappuccino mẫu", "is_active": True},
        lambda: routes.save_routing(workspace=w, data=values(m.Routing, rtc.ROUTING_FIELDS,
            product=r["product"], code="DEMO_ROUTE_CAPPUCCINO", name="Quy trình Cappuccino mẫu", is_active=True), initial_version=route_data))
    tv = _version(demo, "routing_version", m.RoutingVersion, "routing", r["routing"], route_data)
    for sequence, code, name, center, resource, minutes in ((10, "DEMO_MIX", "Phối trộn", "mixing", "mixer", "3"),
        (20, "DEMO_PACK", "Đóng gói", "packing", "labor", "6")):
        data = values(m.RoutingOperation, rtc.OPERATION_FIELDS, sequence_no=sequence, operation_code=code, operation_name=name,
            work_center=r[center], primary_resource=r[resource], setup_time=D(0), run_time=D(minutes), time_uom=r["minute"],
            quantity_basis=D(1), quantity_uom=r["box"])
        demo.ensure(code, m.RoutingOperation, {"routing_version": tv, "sequence_no": sequence}, data,
            lambda data=data: routes.save_operation(workspace=w, routing=r["routing"], version=tv, data=data))
    if m.RoutingOperation.objects.filter(routing_version=tv).count() != 2:
        raise ValidationError("Quy trình mẫu có công đoạn ngoài định nghĩa.")
    rtv.validate_version(data=route_data, organization=w.organization, instance=tv)
    _publish_source(tv)
    demo.master("pool", m.CostPool, overhead.save_cost_pool, oc.COST_POOL_FIELDS, code="DEMO_FACTORY_OVERHEAD",
        name="Chi phí chung nhà máy mẫu", pool_type="FACTORY_FIXED", description="Phân bổ công suất bình thường: 530.000 VND / 100 hộp.", is_active=True)
    period_data = dict(pool=r["pool"], period_start=START, period_end=date(2026, 12, 31), amount=D("530000"),
        currency_code=r["VND"], normal_capacity=D(100), capacity_uom=r["box"], status="EFFECTIVE", source_reference=MARKER)
    def create_period():
        # No CostPoolPeriod UI/service exists. Explicit schema/business validation
        # is performed before the allowed ORM insert; no algorithm is introduced.
        if period_data["amount"] < 0 or period_data["normal_capacity"] <= 0 or period_data["period_end"] < period_data["period_start"]:
            raise ValidationError("Số liệu kỳ mẫu không hợp lệ.")
        record = m.CostPoolPeriod(**period_data)
        record.full_clean(validate_unique=False, validate_constraints=False)
        record.save(force_insert=True)
        return record
    demo.ensure("period", m.CostPoolPeriod, {"pool": r["pool"], "source_reference": MARKER}, period_data, create_period)
    demo.master("rule", m.AllocationRule, overhead.save_allocation_rule, oc.ALLOCATION_RULE_FIELDS,
        code="DEMO_OVERHEAD_NORMAL", name="Phân bổ chi phí chung theo công suất", pool=r["pool"], basis_type="NORMAL_CAPACITY",
        basis_uom=r["box"], priority=100, effective_from=START)
    _publish_source(r["rule"])


def _price(demo, key, item, amount, start, end):
    r = demo.records
    data = values(m.SupplierPrice, mc.SUPPLIER_PRICE_FIELDS, supplier=r["supplier"], item=r[item],
        price_uom=r[item].purchase_uom, currency_code=r["VND"], unit_price=amount, min_qty=D(0),
        tax_inclusive=False, tax_rate=D(0), tax_recoverable_ratio=D(1), effective_from=start, effective_to=end,
        source_type="DEMO", source_reference=MARKER + ":" + key)
    record = demo.ensure(key, m.SupplierPrice, {"organization": demo.workspace.organization, "source_reference": data["source_reference"]}, data,
        lambda: masters.save_supplier_price(workspace=demo.workspace, data=data))
    _publish_source(record)


def _rate(demo, key, resource, amount, start, end):
    r = demo.records
    data = values(m.ResourceRate, resc.RATE_FIELDS, resource=r[resource], rate_type="STANDARD", amount=amount,
        currency_code=r["VND"], per_uom=r["hour"], effective_from=start, effective_to=end, source_reference=MARKER + ":" + key)
    record = demo.ensure(key, m.ResourceRate, {"organization": demo.workspace.organization, "source_reference": data["source_reference"]}, data,
        lambda: resources.save_resource_rate(workspace=demo.workspace, data=data))
    _publish_source(record)


def _seed_configuration(demo):
    w, r = demo.workspace, demo.records
    for key, label, source in (("MATERIAL_COST", "Chi phí nguyên vật liệu", "SYSTEM"), ("PACKAGING_COST", "Chi phí bao bì", "SYSTEM"),
        ("RESOURCE_COST", "Chi phí nguồn lực", "SYSTEM"), ("OVERHEAD_COST", "Chi phí chung", "SYSTEM"),
        ("DIRECT_COST", "Chi phí trực tiếp", "FORMULA"), ("FULL_COST", "Tổng giá thành", "FORMULA")):
        demo.master(key, m.CostElement, masters.save_cost_element, mc.EDITABLE_FIELDS,
            code="DEMO_" + key, name=label, value_type="MONEY", dimension_code="MONEY", currency_code=r["VND"],
            default_source_mode=source, accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING",
            rounding_scale=6, rounding_mode="HALF_UP", is_sensitive=False, is_active=True)
    inputs = {"DEMO_" + code: amount for code, amount in (("MATERIAL_COST", D(260000)), ("PACKAGING_COST", D(150000)),
        ("RESOURCE_COST", D(120000)), ("OVERHEAD_COST", D(53000)))}
    for key, label, output, expression, expected in (("direct_formula", "Tổng chi phí trực tiếp mẫu", "DIRECT_COST",
        "$DEMO_MATERIAL_COST + $DEMO_PACKAGING_COST + $DEMO_RESOURCE_COST", D(530000)),
        ("full_formula", "Tổng giá thành mẫu", "FULL_COST", "@DEMO_DIRECT_FORMULA + $DEMO_OVERHEAD_COST", D(583000))):
        code = "DEMO_DIRECT_FORMULA" if key == "direct_formula" else "DEMO_FULL_FORMULA"
        header = values(m.Formula, fc.HEADER_FIELDS, code=code, name=label, output_element=r[output], is_active=True)
        data = values(m.FormulaVersion, fc.VERSION_FIELDS, expression=expression, effective_from=START, change_reason="Đối soát thủ công bộ mẫu.")
        demo.ensure(key, m.Formula, {"organization": w.organization, "code": code}, header,
            lambda header=header, data=data: formulas.save_formula(workspace=w, data=header, version_data=data))
        version = _version(demo, key + "_version", m.FormulaVersion, "formula", r[key], data)
        plan = build_plan(organization=w.organization, formula=r[key], expression=expression)
        case_name = "DEMO_GOLDEN_10_BOX"
        case_data = {"inputs": {code: inputs[code] for code in plan.inputs}, "expected": expected, "test_name": case_name}
        demo.ensure(key + "_test", m.FormulaTestCase, {"formula": r[key], "name": case_name},
            {"input_context": {code: str(amount) for code, amount in case_data["inputs"].items()}, "expected_value_numeric": expected,
             "tolerance": D(0), "is_active": True},
            lambda key=key, plan=plan, case_data=case_data: formulas.save_test_case(workspace=w, formula=r[key], plan=plan, data=case_data))
        if version.status == "DRAFT":
            r[key + "_version"] = formulas.activate_version(workspace=w, formula=r[key], version=version)
        elif version.status != "EFFECTIVE" or version.validation_status != "VALID":
            raise ValidationError("Công thức mẫu chưa hợp lệ/hiệu lực.")
    header = values(m.CostingScheme, sc.SCHEME_FIELDS, code="DEMO_COSTING_SCHEME", name="Giá thành Cappuccino mẫu",
        purpose="STANDARD_COST", context_scope="SKU", description="Bộ mẫu 10 hộp; phân bổ công suất bình thường.", is_active=True)
    data = values(m.CostingSchemeVersion, sc.VERSION_FIELDS, effective_from=START, change_reason="Dữ liệu mẫu ban đầu.")
    demo.ensure("scheme", m.CostingScheme, {"organization": w.organization, "code": header["code"]}, header,
        lambda: schemes.save_scheme(workspace=w, data=header, initial_version=data))
    sv = _version(demo, "scheme_version", m.CostingSchemeVersion, "scheme", r["scheme"], data)
    for order, code in enumerate(("MATERIAL_COST", "PACKAGING_COST", "RESOURCE_COST", "OVERHEAD_COST", "DIRECT_COST", "FULL_COST"), 1):
        config = {"source_mode": "SYSTEM", "system_resolver_code": "ALLOCATION:DEMO_OVERHEAD_NORMAL" if code == "OVERHEAD_COST" else code}
        if code in ("DIRECT_COST", "FULL_COST"):
            config = {"source_mode": "FORMULA", "formula_version": r[("direct_formula" if code == "DIRECT_COST" else "full_formula") + "_version"]}
        row = values(m.CostingSchemeLine, sc.LINE_FIELDS, line_code="DEMO_" + code, label=r[code].name, cost_element=r[code],
            line_type="OUTPUT" if code == "FULL_COST" else "SUBTOTAL" if code == "DIRECT_COST" else "INPUT",
            cost_scope="MANUFACTURING", display_order=order * 10, **config)
        demo.ensure(code + "_scheme_line", m.CostingSchemeLine, {"scheme_version": sv, "line_code": row["line_code"]}, row,
            lambda row=row: schemes.save_line(workspace=w, scheme=r["scheme"], version=sv, data=row))
    if m.CostingSchemeLine.objects.filter(scheme_version=sv).count() != 6:
        raise ValidationError("Phương án mẫu có dòng ngoài định nghĩa.")
    if sv.status == "DRAFT":
        r["scheme_version"] = schemes.activate_version(workspace=w, scheme=r["scheme"], version=sv)
    elif sv.status != "EFFECTIVE":
        raise ValidationError("Phương án mẫu chưa hiệu lực.")


def _drafts(demo):
    """Actual cloned Drafts for editable UI smoke, never used by the golden run."""
    w, r = demo.workspace, demo.records
    for key, model, parent_field, service, argument, fields in (
        ("recipe", m.RecipeVersion, "recipe", recipes.create_version, "recipe", rc.VERSION_FIELDS),
        ("packaging", m.PackagingConfigVersion, "packaging_config", packs.create_version, "config", pac.VERSION_FIELDS),
        ("routing", m.RoutingVersion, "routing", routes.create_version, "routing", rtc.VERSION_FIELDS),
        ("scheme", m.CostingSchemeVersion, "scheme", schemes.save_version, "scheme", sc.VERSION_FIELDS),
        ("direct_formula", m.FormulaVersion, "formula", formulas.save_version, "formula", fc.VERSION_FIELDS),
        ("full_formula", m.FormulaVersion, "formula", formulas.save_version, "formula", fc.VERSION_FIELDS)):
        source = r[key + "_version"]
        data = {name: getattr(source, name) for name in fields}
        data["change_reason"] = "Bản nháp dùng kiểm tra giao diện; không dùng cho lần tính mẫu."
        draft = demo.ensure(key + "_draft", model, {parent_field: r[key], "version_no": 2}, {**data, "status": "DRAFT"},
            lambda service=service, argument=argument, key=key, data=data, source=source:
                service(workspace=w, **{argument: r[key]}, data=data, source=source))
        # The services clone structure atomically; old effective sources stay intact.
        if draft.version_no != 2:
            raise ValidationError("Số phiên bản Nháp mẫu không còn đúng định nghĩa.")


def seed_demo():
    with transaction.atomic():
        company = get_default_organization()
        # Same compatibility row lock as definition services, not a company flow.
        m.Organization.objects.select_for_update().get(pk=company.pk)
        demo = DemoData(Workspace(company))
        _reference_masters(demo)
        _seed_sources(demo)
        _seed_configuration(demo)
        _drafts(demo)
        matches(demo.records["rule"], {"condition_jsonb": {}, "formula_code": None})
        return demo


def inventory(demo):
    """Include service-created initial versions, cloned children and dependencies."""
    records = {}
    for record in demo.records.values():
        records.setdefault(type(record), set()).add(record.pk)
    for model, field, parent in ((m.RecipeLine, "recipe_version_id", m.RecipeVersion),
        (m.PackagingLine, "packaging_config_version_id", m.PackagingConfigVersion),
        (m.RoutingOperation, "routing_version_id", m.RoutingVersion),
        (m.CostingSchemeLine, "scheme_version_id", m.CostingSchemeVersion),
        (m.FormulaDependency, "formula_version_id", m.FormulaVersion),
        (m.FormulaTestCase, "formula_id", m.Formula)):
        records.setdefault(model, set()).update(model.objects.filter(**{field + "__in": records[parent]}).values_list("pk", flat=True))
    return {model.__name__: {"count": len(ids), "ids": sorted(ids)} for model, ids in sorted(records.items(), key=lambda item: item[0].__name__)}


def seed_future_changes(demo):
    """Called only AFTER the first saved golden result for history verification."""
    with transaction.atomic():
        m.Organization.objects.select_for_update().get(pk=demo.workspace.organization.pk)
        _price(demo, "coffee_future_price", "coffee", D(120000), FUTURE, None)
        _rate(demo, "mixer_future_rate", "mixer", D(144000), FUTURE, None)
        _rate(demo, "labor_future_rate", "labor", D(72000), FUTURE, None)


def manual_expected(*, future=False):
    """Independent arithmetic from frozen demo inputs; never reads the engine."""
    count = D(10)
    coffee = D(200) * count / D(1000) * D(120000 if future else 100000)
    sugar = D(300) * count / D(1000) * D(20000)
    packaging = D(20) * count * D(500) + count * D(5000)
    machine = D(3) * count / D(60) * D(144000 if future else 120000)
    labor = D(6) * count / D(60) * D(72000 if future else 60000)
    direct = coffee + sugar + packaging + machine + labor
    allocation = D(530000) * count / D(100)
    return dict(MATERIAL_COST=coffee + sugar, PACKAGING_COST=packaging,
        MACHINE_COST=machine, LABOR_COST=labor, RESOURCE_COST=machine + labor,
        DIRECT_COST=direct, OVERHEAD_COST=allocation, FULL_COST=direct + allocation,
        UNIT_COST=(direct + allocation) / count)
