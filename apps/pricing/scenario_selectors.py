"""Persisted costing inputs and DB-side scenario lists, without recosting."""
from datetime import date
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import Http404
from apps.core.models import PriceScenario, CostingRun, CostingRunLine, Product, Sku, Channel, Currency
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset
from apps.master_data.presentation import format_number
from .scenario_constants import STATUSES


def unit_cost(run):
    """Use the persisted unit result, never today's source prices or engine."""
    try:
        value = run.context_jsonb["per_unit"]
        if not isinstance(value, str): raise ValueError
        result = Decimal(value)
        if not result.is_finite() or result < 0: raise ValueError
    except (KeyError, TypeError, InvalidOperation, ValueError):
        raise ValidationError("Lần tính giá thành chưa có kết quả đơn vị hợp lệ đã lưu.") from None
    return result


def completed_runs(organization):
    lines = CostingRunLine.objects.filter(run_id=OuterRef("pk"))
    return CostingRun.objects.filter(organization=organization, run_status="LOCKED", full_cost__gte=0,
        quantity__gt=0, context_jsonb__has_key="per_unit").filter(Exists(lines))


def run_label(run):
    display = run.context_jsonb.get("display", {})
    day = run.context_jsonb.get("request", {}).get("costing_date", "")
    try: day = date.fromisoformat(day).strftime("%d/%m/%Y")
    except (ValueError, TypeError): pass
    try: amount = format_number(unit_cost(run))
    except ValidationError: amount = "Kết quả không hợp lệ"
    return f"{display.get('sku') or display.get('product') or run.run_no} · {day} · {amount} {run.result_currency_code_id}/{display.get('uom', '')} · {display.get('scheme', '')} · {run.run_no}"


def queryset(organization):
    return PriceScenario.objects.filter(organization=organization).select_related("base_run").defer("base_run__version_snapshot_jsonb", "base_run__fx_snapshot_jsonb")


def detail(*, organization, pk):
    if not str(pk).isascii() or not str(pk).isdecimal() or len(str(pk)) > 19 or not 0 < int(pk) <= 9223372036854775807:
        raise Http404("Không tìm thấy kịch bản giá bán.")
    try: return queryset(organization).get(pk=pk)
    except PriceScenario.DoesNotExist: raise Http404("Không tìm thấy kịch bản giá bán.") from None


SORTS = {"code": "code", "name": "name", "pricing_date": "scenario_context_jsonb__pricing_date", "created_at": "created_at", "suggested_price": "suggested_price"}


def list_scenarios(*, organization, filters):
    query = search_queryset(queryset(organization), filters.get("q", ""), ("code", "name", "scenario_context_jsonb__display__product", "scenario_context_jsonb__display__sku"))
    for name, field in (("product", "base_run__product_id"), ("sku", "base_run__sku_id"), ("channel", "channel_id")):
        query = filter_id(query, filters, name, field)
    for name in ("status", "currency_code"):
        if filters.get(name): query = query.filter(**{name: filters[name]})
    for name, lookup in (("date_from", "gte"), ("date_to", "lte")):
        if not filters.get(name): continue
        try: day = date.fromisoformat(filters[name])
        except (TypeError, ValueError): query = query.none()
        else: query = query.filter(**{f"scenario_context_jsonb__pricing_date__{lookup}": day.isoformat()})
    return paginate_queryset(query, filters, SORTS, "-created_at")


def filter_options(organization):
    def options(model):
        return tuple((row.pk, f"{row.code} — {row.name}") for row in model.objects.filter(organization=organization).order_by("code"))
    return (("product", "Sản phẩm", options(Product)), ("sku", "SKU", options(Sku)),
        ("channel", "Kênh bán", options(Channel)), ("currency_code", "Tiền tệ", tuple(Currency.objects.order_by("code").values_list("code", "name"))),
        ("status", "Trạng thái", STATUSES))
