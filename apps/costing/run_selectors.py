from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from django.http import Http404
from django.utils import timezone
from apps.core.models import CostingRun, CostingRunLine, Product, Sku, CostingScheme
from apps.master_data.query_helpers import filter_id, search_queryset, paginate_queryset
from .run_constants import RUN_STATUSES, SOURCE_LABELS


def run_queryset(organization): return CostingRun.objects.filter(organization=organization)


def run_list(*, organization, filters):
    # Historical names come from context snapshots, not mutable master joins.
    query = search_queryset(run_queryset(organization).defer("version_snapshot_jsonb", "fx_snapshot_jsonb"), filters.get("q", ""), ("run_no", "context_jsonb__display__product", "context_jsonb__display__sku", "context_jsonb__display__scheme"))
    for field in ("product", "sku"):
        query = filter_id(query, filters, field, field + "_id")
    query = filter_id(query, filters, "scheme", "scheme_version__scheme_id")
    if filters.get("status"): query = query.filter(run_status=filters["status"])
    from datetime import date, datetime, time, timedelta
    for name, lookup in (("date_from", "effective_at__gte"), ("date_to", "effective_at__lt")):
        if not filters.get(name): continue
        try:
            day = date.fromisoformat(filters[name])
            if name == "date_to": day += timedelta(days=1)
        except (ValueError, OverflowError):
            query = query.none()
            continue
        query = query.filter(**{lookup: timezone.make_aware(datetime.combine(day, time.min))})
    return paginate_queryset(query, filters, {"costing_date": "effective_at", "created_at": "created_at", "total_cost": "full_cost", "run_no": "run_no"}, "-created_at")


def run_detail(*, organization, public_id):
    try: return run_queryset(organization).get(public_id=public_id)
    except CostingRun.DoesNotExist: raise Http404 from None


def run_lines(*, run, filters):
    values = filters.dict() if hasattr(filters, "dict") else dict(filters)
    return paginate_queryset(CostingRunLine.objects.filter(run=run).order_by("display_order", "pk"), {**values, "sort": "order"}, {"order": "display_order"}, "order")


def line_detail(*, run, pk):
    if not 0 < pk <= 9223372036854775807: raise Http404
    try: return CostingRunLine.objects.get(run=run, pk=pk)
    except CostingRunLine.DoesNotExist: raise Http404 from None


def filter_options(organization):
    def options(model): return tuple((row.pk, f"{row.code} — {row.name}") for row in model.objects.filter(organization=organization).order_by("code"))
    return (("product", "Sản phẩm", options(Product)), ("sku", "SKU", options(Sku)), ("scheme", "Phương án", options(CostingScheme)), ("status", "Trạng thái", RUN_STATUSES))


def source_rows(run):
    snapshot = run.version_snapshot_jsonb
    return ({"label": SOURCE_LABELS.get(source.get("table"), "Nguồn dữ liệu"), "reference": source.get("id"),
        "code": source.get("fields", {}).get("code", ""), "name": source.get("fields", {}).get("name", ""),
        "version": source.get("fields", {}).get("version_no"), "from": source.get("fields", {}).get("effective_from", source.get("fields", {}).get("period_start")),
        "to": source.get("fields", {}).get("effective_to", source.get("fields", {}).get("period_end"))} for source in snapshot.get("sources", {}).values())


def display_lines(lines, total):
    for line in lines:
        line.display_value = getattr(line, {"MONEY": "amount", "QUANTITY": "quantity", "NUMBER": "number_value", "PERCENT": "percent_value", "BOOLEAN": "boolean_value", "TEXT": "text_value"}[line.value_type])
        # Totals/subtotals overlap with input costs. Do not imply that all rows
        # are additive or that their displayed shares must sum to 100%.
        with localcontext() as precision:
            precision.prec = 50
            line.share = (line.amount / total * Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN) / Decimal(100) if total and line.amount is not None else None
    return lines
