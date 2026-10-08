"""Validate persisted snapshots and compare their values, without executing engines."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from uuid import UUID
from django.core.exceptions import ValidationError
from . import comparison_selectors as selectors
from .engine.context import digest


@dataclass(frozen=True)
class StoredScenario:
    record: object
    snapshot: dict
    values: dict
    key: tuple
    currency: str


def selected_ids(values, *, required=False):
    if len(values) > 5 or (required and len(values) < 2):
        raise ValidationError("Vui lòng chọn từ 2 đến 5 kịch bản để so sánh.")
    ids = []
    for value in values:
        if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or len(value) > 19 or not 0 < int(value) <= 9223372036854775807:
            raise ValidationError("Mã tham chiếu kịch bản không hợp lệ.")
        ids.append(int(value))
    if len(set(ids)) != len(ids):
        raise ValidationError("Không được chọn trùng kịch bản.")
    return ids


def number(value, *, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) > 150:
        raise ValueError
    result = Decimal(value)
    if not result.is_finite() or abs(result) >= Decimal("1e50") or result.as_tuple().exponent < -100:
        raise ValueError
    return result


def stored(record):
    """Fail closed for missing, corrupted or unsupported persisted results."""
    try:
        snapshot = record.output_snapshot_jsonb
        if record.status != "CALCULATED" or snapshot["schema"] != 1 or record.base_run.run_status != "LOCKED":
            raise ValueError
        if snapshot["hash"] != digest({k: v for k, v in snapshot.items() if k != "hash"}):
            raise ValueError
        inputs, costing, policy = snapshot["inputs"], snapshot["costing"], snapshot["policy"]
        request = costing["context"]["request"]
        product, sku = request["product"], request.get("sku")
        if not product or (product, sku) != (record.base_run.product_id, record.base_run.sku_id):
            raise ValueError
        if costing["id"] != record.base_run_id or record.organization_id != record.base_run.organization_id:
            raise ValueError
        if inputs["uom_id"] != record.base_run.quantity_uom_id or not inputs["uom_id"] or number(inputs["quantity"]) != 1:
            raise ValueError
        if policy["version"] != 1 or policy["margin_denominator"] != "CUSTOMER_GROSS_PRICE" or policy["markup_denominator"] != "UNIT_COST" or policy["fixed_fee_basis"] != "ONE_COSTING_OUTPUT_UNIT":
            raise ValueError
        currency = inputs["currency"]
        if not isinstance(currency, str) or len(currency) != 3:
            raise ValueError
        date.fromisoformat(inputs["pricing_date"])
        UUID(costing["public_id"])
        datetime.fromisoformat(costing["effective_at"])
        number(costing["unit_cost"])
        if not isinstance(costing["currency"], str) or len(costing["currency"]) != 3:
            raise ValueError
        if inputs["method"] not in ("MARGIN", "MARKUP", "PROFIT_PER_UNIT"):
            raise ValueError
        number(inputs["target"])
        values = {name: number(snapshot["result"][name], optional=name.startswith("actual_")) for name in selectors.RESULT_KEYS}
        for name in ("fee_lines", "tax_lines"):
            if not isinstance(snapshot["result"][name], list):
                raise ValueError
            for line in snapshot["result"][name]:
                if not isinstance(line["label"], str):
                    raise ValueError
                for field in ("amount", "basis", "rate", "fixed"):
                    number(line[field])
                for field in ("floor", "cap"):
                    number(line.get(field), optional=True)
        if not isinstance(snapshot["trace"].get("fx", []), list):
            raise ValueError
        for fx in snapshot["trace"].get("fx", []):
            number(fx["rate"])
            datetime.fromisoformat(fx["at"])
            if not all(isinstance(fx[key], str) and len(fx[key]) == 3 for key in ("from", "to")):
                raise ValueError
        if not isinstance(snapshot["display"], dict):
            raise ValueError
    except (KeyError, TypeError, ValueError, InvalidOperation, AttributeError):
        raise ValidationError(f"Kịch bản {record.code} chưa có kết quả đã lưu hợp lệ hoặc sử dụng cấu trúc chưa được hỗ trợ.") from None
    return StoredScenario(record, snapshot, values, (product, sku, inputs["uom_id"], number(inputs["quantity"]), policy["version"]), currency)


def load_selection(*, organization, values, required=False):
    ids = selected_ids(values, required=required)
    rows = {r.pk: r for r in selectors.queryset(organization).filter(pk__in=ids)} if ids else {}
    if len(rows) != len(ids):
        raise ValidationError("Không tìm thấy một hoặc nhiều kịch bản đã chọn.")
    return [stored(rows[pk]) for pk in ids]


def validate_compatibility(scenarios):
    first = scenarios[0]
    for scenario in scenarios[1:]:
        if scenario.key[:2] != first.key[:2]:
            raise ValidationError("Chỉ có thể so sánh các kịch bản của cùng một SKU, hoặc cùng sản phẩm khi tất cả không có SKU.")
        if scenario.key[2:] != first.key[2:]:
            raise ValidationError("Các kịch bản phải có cùng đơn vị đầu ra và cơ sở giá đã lưu.")


def difference(value, baseline):
    if value is None or baseline is None:
        return None, None
    with localcontext() as precision:
        precision.prec = 80
        absolute = value - baseline
        relative = absolute / abs(baseline) * 100 if baseline else None
        return absolute, relative
