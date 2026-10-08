from django.db.models import Count, Exists, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.core.models import Product, Routing, RoutingOperation, RoutingVersion, Sku
from apps.master_data.query_helpers import filter_id, paginate_queryset
from .definition_helpers import date_status, get_by_pk
from .routing_constants import DATE_STATUSES, VERSION_STATUSES


def routing_queryset(*, organization):
    return Routing.objects.filter(organization=organization, product__organization=organization).select_related("product")


def routing_list(*, organization, filters):
    query = routing_queryset(organization=organization)
    latest = RoutingVersion.objects.filter(routing_id=OuterRef("pk")).order_by("-version_no", "-pk")
    counts = RoutingOperation.objects.filter(routing_version_id=OuterRef("pk")).values("routing_version_id").annotate(number=Count("pk")).values("number")
    latest = latest.annotate(operation_count=Coalesce(Subquery(counts), Value(0), output_field=IntegerField()))
    query = query.annotate(**{f"latest_{field}": Subquery(latest.values(field)[:1]) for field in
        ("pk", "version_no", "status", "effective_from", "effective_to", "operation_count")})
    query = query.annotate(date_status=date_status("latest_effective_from", "latest_effective_to"))
    keyword = filters.get("q", "").strip()
    if keyword:
        sku_match = Sku.objects.filter(product_id=OuterRef("product_id"), organization=organization).filter(Q(code__icontains=keyword) | Q(name__icontains=keyword))
        query = query.annotate(sku_match=Exists(sku_match)).filter(Q(code__icontains=keyword) | Q(name__icontains=keyword)
            | Q(product__code__icontains=keyword) | Q(product__name__icontains=keyword) | Q(sku_match=True))
    query = filter_id(query, filters, "product", "product_id")
    if filters.get("sku"):
        skus = filter_id(Sku.objects.filter(organization=organization), filters, "sku", "pk")
        query = query.filter(product_id__in=skus.values("product_id"))
    active = filters.get("active", filters.get("is_active"))
    if active in ("true", "false"):
        query = query.filter(is_active=active == "true")
    for parameter, field in (("status", "latest_status"), ("effective", "date_status")):
        if filters.get(parameter):
            query = query.filter(**{field: filters[parameter]})
    return paginate_queryset(query, filters, {"code": "code", "name": "name", "effective_from": "latest_effective_from", "created_at": "created_at", "version": "latest_version_no"})


def routing_detail(*, organization, pk):
    return get_by_pk(routing_queryset(organization=organization), pk)


def version_queryset(*, routing):
    return RoutingVersion.objects.filter(routing=routing).select_related("batch_uom").annotate(date_status=date_status())


def version_detail(*, routing, pk):
    return get_by_pk(version_queryset(routing=routing), pk)


def version_list(*, routing, filters):
    query = version_queryset(routing=routing)
    for parameter, field in (("status", "status"), ("effective", "date_status")):
        if filters.get(parameter):
            query = query.filter(**{field: filters[parameter]})
    return paginate_queryset(query, filters, {"version": "version_no", "effective_from": "effective_from", "created_at": "created_at"}, "-version")


def operation_queryset(*, version, organization):
    return RoutingOperation.objects.filter(routing_version=version).filter(
        Q(work_center__isnull=True) | Q(work_center__organization=organization)
    ).filter(Q(primary_resource__isnull=True) | Q(primary_resource__organization=organization)).filter(
        Q(primary_resource__work_center__isnull=True) | Q(primary_resource__work_center__organization=organization)
    ).select_related("work_center", "primary_resource", "primary_resource__work_center", "time_uom", "quantity_uom")


def operation_detail(*, version, organization, pk):
    return get_by_pk(operation_queryset(version=version, organization=organization), pk)


def operation_list(*, version, organization, filters):
    # Operations always follow the actual production sequence, not a UI sort override.
    return paginate_queryset(operation_queryset(version=version, organization=organization), {**filters.dict(), "sort": "sequence"} if hasattr(filters, "dict") else {**filters, "sort": "sequence"}, {"sequence": "sequence_no"}, "sequence")


def filter_options(*, organization):
    return (
        ("product", "Sản phẩm", ((p.pk, f"{p.code} — {p.name}") for p in Product.objects.filter(organization=organization).order_by("code"))),
        ("sku", "SKU của sản phẩm", ((s.pk, f"{s.code} — {s.name}") for s in Sku.objects.filter(organization=organization, product__organization=organization).order_by("code"))),
        ("status", "Trạng thái phiên bản mới nhất", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES),
        ("active", "Trạng thái quy trình", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động"))),
    )
