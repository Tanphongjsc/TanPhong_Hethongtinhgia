from django.db.models import Count, Exists, OuterRef, Q, Subquery

from apps.core.models import PackagingConfig, PackagingConfigVersion, PackagingLine, Product, Sku, SkuPackagingAssignment
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset
from .constants import DATE_STATUSES, VERSION_STATUSES
from .definition_helpers import date_status, get_by_pk


def config_queryset(*, organization):
    return PackagingConfig.objects.filter(organization=organization, product__organization=organization).select_related("product")


def assignment_queryset(*, config, organization):
    return SkuPackagingAssignment.objects.filter(packaging_config=config, sku__organization=organization,
        sku__product_id=config.product_id, sku__product__organization=organization).select_related("sku", "sku__product").annotate(date_status=date_status())


def config_list(*, organization, filters):
    queryset = config_queryset(organization=organization)
    latest = PackagingConfigVersion.objects.filter(packaging_config_id=OuterRef("pk")).order_by("-version_no", "-pk")
    queryset = queryset.annotate(**{f"latest_{field}": Subquery(latest.values(field)[:1])
        for field in ("pk", "version_no", "status", "effective_from", "effective_to")}).annotate(date_status=date_status("latest_effective_from", "latest_effective_to"))
    assignments = SkuPackagingAssignment.objects.filter(packaging_config_id=OuterRef("pk"), sku__organization=organization,
        sku__product_id=OuterRef("product_id"), sku__product__organization=organization)
    counts = assignments.values("packaging_config_id").annotate(total=Count("pk"))
    queryset = queryset.annotate(assignment_count=Subquery(counts.values("total")[:1]))
    keyword = filters.get("q", "").strip()
    if keyword:
        queryset = queryset.annotate(sku_match=Exists(assignments.filter(Q(sku__code__icontains=keyword) | Q(sku__name__icontains=keyword)))).filter(
            Q(code__icontains=keyword) | Q(name__icontains=keyword) | Q(description__icontains=keyword)
            | Q(product__code__icontains=keyword) | Q(product__name__icontains=keyword) | Q(sku_match=True))
    queryset = filter_id(queryset, filters, "product", "product_id")
    if filters.get("sku"):
        scoped = filter_id(Sku.objects.filter(organization=organization, product__organization=organization), filters, "sku", "pk")
        queryset = queryset.filter(Exists(assignments.filter(sku_id__in=scoped.values("pk"))))
    if filters.get("active") in ("true", "false"):
        queryset = queryset.filter(is_active=filters["active"] == "true")
    for parameter, field in (("status", "latest_status"), ("effective", "date_status")):
        if filters.get(parameter):
            queryset = queryset.filter(**{field: filters[parameter]})
    return paginate_queryset(queryset, filters, {"code": "code", "name": "name", "created_at": "created_at", "effective_from": "latest_effective_from", "version": "latest_version_no"})


def config_detail(*, organization, pk):
    return get_by_pk(config_queryset(organization=organization), pk)


def version_queryset(*, config):
    return PackagingConfigVersion.objects.filter(packaging_config=config).select_related("weight_uom", "dimension_uom").annotate(date_status=date_status())


def version_detail(*, config, pk):
    return get_by_pk(version_queryset(config=config), pk)


def version_list(*, config, filters):
    queryset = version_queryset(config=config)
    for parameter, field in (("status", "status"), ("effective", "date_status")):
        if filters.get(parameter):
            queryset = queryset.filter(**{field: filters[parameter]})
    return paginate_queryset(queryset, filters, {"version": "version_no", "effective_from": "effective_from", "created_at": "created_at"}, "-version")


def line_queryset(*, version, organization):
    return PackagingLine.objects.filter(packaging_config_version=version, packaging_item__organization=organization).select_related("packaging_item", "uom")


def line_detail(*, version, organization, pk):
    return get_by_pk(line_queryset(version=version, organization=organization), pk)


def line_list(*, version, organization, filters):
    return paginate_queryset(line_queryset(version=version, organization=organization), filters, {"order": "display_order"}, "order")


def assignment_list(*, config, organization, filters):
    queryset = search_queryset(assignment_queryset(config=config, organization=organization), filters.get("q", ""), ("sku__code", "sku__name"))
    if filters.get("effective"):
        queryset = queryset.filter(date_status=filters["effective"])
    return paginate_queryset(queryset, filters, {"sku": "sku__code", "effective_from": "effective_from", "created_at": "created_at"}, "sku")


def assignment_detail(*, config, organization, pk):
    return get_by_pk(assignment_queryset(config=config, organization=organization), pk)


def filter_options(*, organization):
    return (("product", "Sản phẩm", ((p.pk, f"{p.code} — {p.name}") for p in Product.objects.filter(organization=organization).order_by("code"))),
        ("sku", "SKU đã gán", ((s.pk, f"{s.code} — {s.name}") for s in Sku.objects.filter(organization=organization, product__organization=organization).order_by("code"))),
        ("status", "Trạng thái phiên bản mới nhất", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES),
        ("active", "Trạng thái cấu hình", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động"))))
