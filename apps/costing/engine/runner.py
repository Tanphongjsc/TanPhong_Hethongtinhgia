"""Domain pipeline, independent of HTTP. DB reads occur in dated resolvers."""
from dataclasses import dataclass
from decimal import Decimal, DecimalException, localcontext
import decimal
from apps.formula_engine.ast_nodes import fingerprint
from apps.formula_engine.evaluator import Budget, checked_value
from apps.formula_engine.errors import FormulaError
from apps.formula_engine.limits import limits
from apps.formula_engine.validator import element_type, ValueType, NUMERIC
from apps.costing.configuration import analyze_formula, validate_costing_scheme
from apps.costing.selectors import line_queryset
from apps.core.models import Uom
from .context import json_data, digest, ResolvedValue, step
from .errors import CostingError
from .registry import check_source, RESOLVERS
from .resolvers.common import active
from .resolvers.uom import UomResolver
from .resolvers.prices import PriceResolver, ResourceRateResolver
from .resolvers.manufacturing import ManufacturingResolver
from .resolvers.allocation import allocate
from .resolvers.scheme import resolve_scheme


@dataclass(frozen=True)
class CostingResult:
    version: object
    lines: tuple
    total: Decimal
    per_unit: Decimal
    snapshot: dict
    warnings: tuple


def stored_number(value, *, places=8):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CostingError("Giá trị tính toán không hợp lệ.", stage="calculation")
    if abs(value) >= Decimal(10) ** (8 if places == 10 else 16):
        raise CostingError("Kết quả vượt giới hạn lưu trữ.", code="PRECISION_OVERFLOW", stage="persistence")
    rounded = value.quantize(Decimal(1).scaleb(-places), rounding=decimal.ROUND_HALF_EVEN)
    if rounded != value:
        raise CostingError("Kết quả vượt độ chính xác lưu trữ; cần cấu hình làm tròn tại phần tử chi phí hoặc dòng phương án.", code="PRECISION_OVERFLOW", stage="persistence")
    return value


def round_value(value, row):
    if not isinstance(value, Decimal): return value, ()
    element = row.cost_element
    scale = row.rounding_scale if row.rounding_scale is not None else element.rounding_scale if element else 8
    mode = element.rounding_mode if element else "HALF_EVEN"
    rounding = getattr(decimal, "ROUND_" + mode, None)
    if rounding is None or not 0 <= scale <= 12: raise CostingError("Cấu hình làm tròn không hợp lệ.")
    result = value.quantize(Decimal(1).scaleb(-scale), rounding=rounding)
    return result, (step("Làm tròn tại ranh giới phần tử chi phí", **{"Giá trị trước làm tròn": value, "Số chữ số": scale, "Phương pháp": mode, "Giá trị được sử dụng": result}),)


def manual_value(raw, spec):
    try:
        value = Decimal(raw) if spec.kind in NUMERIC and isinstance(raw, (str, Decimal, int)) and type(raw) is not bool else raw
        return checked_value(value, spec)
    except (DecimalException, FormulaError):
        raise CostingError("Dữ liệu nhập thủ công không đúng kiểu hoặc vượt giới hạn.", code="INVALID_INPUT", stage="manual") from None


def execute(ctx, scheme_id):
    try:
        with localcontext() as arithmetic:
            arithmetic.prec = limits().precision
            arithmetic.Emax, arithmetic.Emin = limits().magnitude, -limits().magnitude
            return _execute(ctx, scheme_id)
    except FormulaError as error:
        raise CostingError(str(error), code="FORMULA_ERROR", stage="formula") from None
    except DecimalException:
        raise CostingError("Không thể tính giá trị số hoặc dữ liệu vượt giới hạn.", code="CALCULATION_ERROR", stage="calculation") from None


def _execute(ctx, scheme_id):
    active(ctx, ctx.product, ctx.sku, ctx.uom, ctx.currency)
    if ctx.quantity <= 0: raise CostingError("Sản lượng phải lớn hơn 0.")
    if ctx.sku and ctx.sku.product_id != ctx.product.pk: raise CostingError("SKU không thuộc sản phẩm đã chọn.")
    if ctx.sku:
        active(ctx, ctx.sku.sales_uom, ctx.sku.net_quantity_uom, ctx.sku.sell_item)
    active(ctx, ctx.product.costing_uom, ctx.product.output_item)
    version = resolve_scheme(ctx, scheme_id)
    report = validate_costing_scheme(organization=ctx.organization, scheme=version.scheme, version=version, effective_date=ctx.day)
    if report.errors: raise CostingError("Phương án tính giá thành chưa hợp lệ. " + " ".join(report.errors))
    rows = list(line_queryset(version=version)[:limits().graph_nodes + 1])
    by_code = {row.line_code: row for row in rows}
    outputs = [row for row in rows if row.line_type == "OUTPUT"]
    if len(outputs) != 1 or outputs[0].cost_scope != "MANUFACTURING" or not outputs[0].cost_element or outputs[0].cost_element.value_type != "MONEY" or outputs[0].cost_element.default_uom_id:
        raise CostingError("Lần tính cần đúng một dòng đầu ra tổng tiền thuộc phạm vi sản xuất. Không tự cộng các tổng phụ hoặc chọn phần tử kết quả.")
    expected_manual = {row.line_code for row in rows if row.source_mode == "MANUAL"}
    if set(ctx.manual) != expected_manual:
        raise CostingError("Dữ liệu nhập thủ công thiếu hoặc chứa dòng không thuộc phương án.", code="INVALID_INPUT", stage="manual")
    units = UomResolver(ctx)
    prices, rates = PriceResolver(ctx, units), ResourceRateResolver(ctx, units)
    manufacturing = ManufacturingResolver(ctx, units, prices, rates)
    values, results, warnings, formulas = {}, {}, list(report.warnings), {}
    budget = Budget(limits().steps)
    for code in report.order:
        row = by_code[code]
        prior_values = values.copy()
        element = row.cost_element
        active(ctx, element)
        ctx.remember(row)
        if row.condition_jsonb: raise CostingError("Điều kiện dòng chưa có bộ thực thi được hỗ trợ.")
        if row.cost_scope not in ("MANUFACTURING", "ANALYTICS"):
            raise CostingError("Iteration này chỉ tính chi phí sản xuất; chưa thực thi chi phí kênh, giá bán hoặc landed cost.")
        if element and element.value_type == "MONEY" and element.currency_code_id != ctx.currency.pk:
            raise CostingError("Tiền tệ phần tử chi phí khác tiền tệ kết quả; chưa có quy tắc FX.", code="MISSING_FX", stage="currency")
        spec = element_type(element) or ValueType("TEXT" if row.line_type == "INFO" else "NUMBER")
        if row.source_mode == "MANUAL":
            value = manual_value(ctx.manual[code], spec)
            if isinstance(value, Decimal):
                if row.min_override_value is not None and value < row.min_override_value or row.max_override_value is not None and value > row.max_override_value:
                    raise CostingError(f"Dữ liệu nhập cho dòng {code} vượt giới hạn đã cấu hình.", stage="manual")
            resolved = ResolvedValue(value, (step("Dữ liệu đầu vào do người chạy cung cấp", **{"Dòng": code, "Giá trị": value}),))
        elif row.source_mode == "SYSTEM":
            check_source(row, ctx.organization, ctx.day)
            resolver = row.system_resolver_code
            cache_key = (resolver, element.default_uom_id) if resolver == "RUN_QUANTITY" else resolver
            if cache_key not in ctx.cache:
                if resolver.startswith("ALLOCATION:"):
                    ctx.cache[cache_key] = allocate(ctx, units, resolver[11:], output_quantity=manufacturing.output_quantity)
                elif resolver == "RUN_QUANTITY":
                    quantity, conversions = manufacturing.output_quantity(element.default_uom)
                    ctx.cache[cache_key] = ResolvedValue(quantity, conversions)
                else: ctx.cache[cache_key] = getattr(manufacturing, RESOLVERS[resolver][0])()
            resolved = ctx.cache[cache_key]
        elif row.source_mode == "FORMULA":
            key = (row.formula_version_id, row.cost_element_id)
            if key not in ctx.cache:
                ctx.cache[key] = analyze_formula(organization=ctx.organization, version=row.formula_version, target=element, effective_date=ctx.day)
            plan = ctx.cache[key]
            spec = plan.types[plan.root_code]
            if spec.kind == "MONEY" and (spec.currency != ctx.currency.pk or spec.unit):
                raise CostingError("Kết quả công thức phải là tổng tiền theo tiền tệ của lần tính.", stage="formula")
            prior_values = {name: values[name] for name in plan.inputs}
            result = plan.run(values, budget=budget)
            for name, dep_version in {plan.root_code: row.formula_version, **plan.versions}.items():
                ctx.remember(dep_version, dep_version.formula)
                for dependency in plan.inputs.values(): active(ctx, dependency, dependency.currency_code, dependency.default_uom)
                ast, ast_hash = fingerprint(plan.roots[name])
                formulas[str(dep_version.pk)] = json_data({"id": dep_version.pk, "code": name, "version": dep_version.version_no, "expression": dep_version.expression, "ast": ast, "ast_hash": ast_hash, "bindings": {f"{kind}:{ref}": {"kind": target_kind, "id": target.pk, "code": target.code} for (kind, ref), (target_kind, target) in plan.bindings[name].items()}, "order": plan.order})
            formula_steps = (
                step(f"Công thức {plan.root_code}", **{"Phiên bản": row.formula_version.version_no, "Biểu thức": row.formula_version.expression, "Kết quả": result.value}),
                step("Phần tử chi phí đầu vào của công thức", **prior_values),
                *tuple({"title": f"Phép tính trong công thức {entry['formula']}", "fields": [("Phiên bản", entry["version"] or row.formula_version.version_no), ("Phép tính", entry["expression"]), ("Đầu vào", list(entry["arguments"])), ("Kết quả", entry["value"])]} for entry in result.trace),
            )
            resolved = ResolvedValue(result.value, formula_steps, tuple(item for item in result.warnings if not item.startswith("Kiểm thử dùng")))
        else: raise CostingError("Nguồn dữ liệu chưa có bộ thực thi an toàn được hỗ trợ.", code="UNSUPPORTED_SOURCE")
        value, rounding = round_value(resolved.value, row)
        checked_value(value, spec)
        if element: values[element.code.upper()] = value
        result_fields = {"scheme_line": row, "cost_element": element, "formula_version": row.formula_version if row.source_mode == "FORMULA" else None,
            "line_code": code, "label": row.label, "line_type": row.line_type, "source_mode": row.source_mode, "value_type": spec.kind, "display_order": row.display_order,
            "input_snapshot_jsonb": json_data({"schema": 1, "inputs": prior_values, "raw_value": resolved.value, "definition": {"condition": row.condition_jsonb, "cost_scope": row.cost_scope, "rounding_scale": row.rounding_scale}}),
            "source_trace_jsonb": json_data({"schema": 1, "resolver": row.system_resolver_code, "steps": (*resolved.steps, *rounding)}), "warnings_jsonb": list(resolved.warnings)}
        name = {"MONEY": "amount", "QUANTITY": "quantity", "NUMBER": "number_value", "PERCENT": "percent_value", "BOOLEAN": "boolean_value", "TEXT": "text_value"}[spec.kind]
        result_fields[name] = stored_number(value, places=10 if spec.kind == "PERCENT" else 8) if isinstance(value, Decimal) else value
        if spec.kind == "MONEY": result_fields["currency_code"] = ctx.currency
        if spec.kind == "QUANTITY":
            if element: unit = element.default_uom
            else:
                key = ("unit", spec.unit)
                if key not in ctx.cache: ctx.cache[key] = Uom.objects.select_related("category").get(pk=spec.unit)
                unit = ctx.cache[key]
            active(ctx, unit)
            result_fields["quantity_uom"] = unit
            result_fields["input_snapshot_jsonb"]["unit_label"] = unit.name
        results[code] = result_fields
        warnings.extend(resolved.warnings)
    total = results[outputs[0].line_code]["amount"]
    if total < 0: raise CostingError("Tổng giá thành sản xuất không được âm.", stage="aggregation")
    snapshot = json_data({"schema": 1, "engine": "costing-v1", "sources": ctx.sources, "formulas": formulas, "order": report.order,
        "rules": {"recipe_quantity": "qty * scale / yield_rate / (1 - scrap_rate)", "setup": "once_per_run", "packaging_basis": "explicit_run_input", "price_selection": "exactly_one_eligible", "allocation": "normal_capacity_only"}})
    snapshot["sha256"] = digest(snapshot)
    return CostingResult(version, tuple(results[row.line_code] for row in rows), total, total / ctx.quantity, snapshot, tuple(dict.fromkeys(warnings)))
