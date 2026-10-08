from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from datetime import date, datetime
from apps.master_data.presentation import format_number, format_percent
from .scenario_constants import METHODS, STATUSES


def decorate(record):
    snapshot = record.output_snapshot_jsonb or {}
    display = snapshot.get("display", record.scenario_context_jsonb.get("display", {}))
    result = snapshot.get("result", {})
    record.display_product = display.get("product") or "—"
    record.display_sku = display.get("sku") or "—"
    record.display_channel = display.get("channel") or "—"
    record.display_date = record.scenario_context_jsonb.get("pricing_date", "")
    try: record.display_date = date.fromisoformat(record.display_date).strftime("%d/%m/%Y")
    except (TypeError, ValueError): record.display_date = "Chưa có ngày định giá"
    record.display_cost = format_number(result.get("unit_cost"))
    record.display_price = format_number(result.get("gross_price"))
    record.display_margin = format_percent(Decimal(result["actual_margin"])) if result.get("actual_margin") is not None else "—"
    record.display_status = dict(STATUSES).get(record.status, "Trạng thái dữ liệu cũ")
    record.display_method = dict(METHODS).get(record.pricing_method, "Phương pháp dữ liệu cũ")
    return record


def result_fields(snapshot):
    result = snapshot.get("result", {})
    fields = [(label, format_number(result.get(name))) for name, label in (
        ("gross_price", "Giá khách trả (gồm thuế)"), ("listed_price", "Giá niêm yết theo quy tắc thuế"),
        ("pre_tax_revenue", "Doanh thu trước phí, chưa thuế"), ("net_revenue", "Doanh thu thuần sau phí và thuế"),
        ("unit_cost", "Giá vốn"), ("profit", "Lợi nhuận"))]
    fields.extend((label, format_percent(Decimal(result[name])) if result.get(name) is not None else "—")
        for name, label in (("actual_margin", "Biên lợi nhuận thực tế / giá khách trả"), ("actual_markup", "Tỷ lệ cộng thực tế / giá vốn")))
    return fields


def trace_rows(snapshot, name):
    for original in snapshot.get("result", {}).get(name, []):
        row = dict(original)
        for key in ("basis", "raw", "fixed", "floor", "cap", "amount"):
            value = original.get(key)
            with localcontext() as precision:
                precision.prec = 60
                row[key + "_display"] = format_number(Decimal(value).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)) if value is not None else "—"
        yield row


def display_date(value):
    if not value: return "Không giới hạn"
    try:
        parsed = datetime.fromisoformat(value)
        from django.utils import timezone
        if timezone.is_aware(parsed): parsed = timezone.localtime(parsed)
        return parsed.strftime("%d/%m/%Y %H:%M") if "T" in value else parsed.strftime("%d/%m/%Y")
    except (ValueError, TypeError): return "Chưa có ngày hợp lệ"


def sources(snapshot):
    labels = {"channel_fee_rule": "Quy tắc phí kênh", "tax_rule": "Quy tắc thuế", "fx_rate": "Tỷ giá", "channel": "Kênh bán", "currency": "Tiền tệ", "product": "Sản phẩm"}
    for row in snapshot.get("sources", []):
        fields = row["fields"]
        yield {"label": labels.get(row["table"], "Nguồn dữ liệu"), "reference": row["id"],
            "code": fields.get("code", fields.get("fee_type", fields.get("tax_type", fields.get("rate_type", "")))),
            "rate": format_percent(fields.get("rate")) if row["table"] in ("channel_fee_rule", "tax_rule") else format_number(fields.get("rate")), "fixed": format_number(fields.get("fixed_amount")),
            "currency": fields.get("currency_code", ""), "from": display_date(fields.get("effective_from", fields.get("effective_at", ""))),
            "to": display_date(fields.get("effective_to", fields.get("valid_to", ""))), "reference_text": fields.get("source_reference", "")}
