"""Bounded, read-only scenario selection. No rule or rate resolution."""
from datetime import date
from django.db.models import Subquery
from apps.core.models import PriceScenario, Product, Sku, Channel, Currency
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset


RESULT_KEYS = ("unit_cost", "fees", "tax", "gross_price", "pre_tax_revenue", "net_revenue", "profit", "actual_margin", "actual_markup")


def queryset(organization):
    return PriceScenario.objects.filter(organization=organization).select_related("base_run").only(
        "id", "organization_id", "code", "name", "base_run_id", "status", "output_snapshot_jsonb",
        "base_run__id", "base_run__organization_id", "base_run__run_no", "base_run__run_status",
        "base_run__product_id", "base_run__sku_id", "base_run__quantity_uom_id")


def eligible(organization):
    return queryset(organization).filter(status="CALCULATED", base_run__run_status="LOCKED",
        base_run__organization=organization, output_snapshot_jsonb__schema=1,
        output_snapshot_jsonb__result__has_keys=list(RESULT_KEYS),
        output_snapshot_jsonb__hash__regex=r"^[0-9a-f]{64}$")


def candidates(*, organization, filters):
    query = eligible(organization)
    # A product is required to avoid loading the entire scenario catalog.
    if not filters.get("product"):
        query = query.none()
    for name, field in (("product", "base_run__product_id"), ("sku", "base_run__sku_id"), ("channel", "channel_id")):
        query = filter_id(query, filters, name, field)
    query = search_queryset(query, filters.get("q", ""), ("code", "name"))
    if filters.get("currency_code"):
        query = query.filter(output_snapshot_jsonb__inputs__currency=filters["currency_code"])
    for name, lookup in (("date_from", "gte"), ("date_to", "lte")):
        value = filters.get(name)
        if not value:
            continue
        try:
            value = date.fromisoformat(value).isoformat()
        except (TypeError, ValueError):
            query = query.none()
        else:
            query = query.filter(**{f"output_snapshot_jsonb__inputs__pricing_date__{lookup}": value})
    return paginate_queryset(query, filters, {"code": "code", "name": "name", "pricing_date": "output_snapshot_jsonb__inputs__pricing_date"}, "code")


def filter_options(organization, filters):
    available = eligible(organization)
    products = Product.objects.filter(organization=organization, pk__in=Subquery(available.values("base_run__product_id"))).order_by("code")
    skus = Sku.objects.filter(organization=organization, pk__in=Subquery(available.values("base_run__sku_id")))
    skus = filter_id(skus, filters, "product", "product_id") if filters.get("product") else skus.none()
    channels = Channel.objects.filter(organization=organization, pk__in=Subquery(available.values("channel_id"))).order_by("code")
    return (("product", "Sản phẩm", tuple((r.pk, f"{r.code} — {r.name}") for r in products)),
        ("sku", "SKU", tuple((r.pk, f"{r.code} — {r.name}") for r in skus.order_by("code"))),
        ("channel", "Kênh bán", tuple((r.pk, f"{r.code} — {r.name}") for r in channels)),
        ("currency_code", "Tiền tệ", tuple(Currency.objects.order_by("code").values_list("code", "name"))))
