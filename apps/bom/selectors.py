from django.db.models import Exists, OuterRef, Q, Subquery

from apps.core.models import Product, Recipe, RecipeLine, RecipeVersion, Sku
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset
from .constants import DATE_STATUSES, VERSION_STATUSES
from .definition_helpers import date_status as _date_status, get_by_pk as _get


def recipe_queryset(*, organization):
    return Recipe.objects.filter(organization=organization, product__organization=organization).select_related("product")


def recipe_list(*, organization, filters):
    queryset = recipe_queryset(organization=organization)
    latest = RecipeVersion.objects.filter(recipe_id=OuterRef("pk")).order_by("-version_no", "-pk")
    queryset = queryset.annotate(**{f"latest_{field.replace('__', '_')}": Subquery(latest.values(field)[:1])
        for field in ("pk", "version_no", "status", "output_qty", "output_uom__name", "output_uom__symbol", "effective_from", "effective_to")})
    queryset = queryset.annotate(date_status=_date_status("latest_effective_from", "latest_effective_to"))
    keyword = filters.get("q", "").strip()
    if keyword:
        sku_match = Sku.objects.filter(product_id=OuterRef("product_id"), organization=organization).filter(
            Q(code__icontains=keyword) | Q(name__icontains=keyword))
        queryset = queryset.annotate(sku_match=Exists(sku_match)).filter(
            Q(code__icontains=keyword) | Q(name__icontains=keyword) | Q(product__code__icontains=keyword)
            | Q(product__name__icontains=keyword) | Q(sku_match=True))
    queryset = filter_id(queryset, filters, "product", "product_id")
    if filters.get("sku"):
        skus = filter_id(Sku.objects.filter(organization=organization), filters, "sku", "pk")
        queryset = queryset.filter(product_id__in=skus.values("product_id"))
    if filters.get("active") in ("true", "false"):
        queryset = queryset.filter(is_active=filters["active"] == "true")
    for parameter, field in (("status", "latest_status"), ("effective", "date_status")):
        if filters.get(parameter):
            queryset = queryset.filter(**{field: filters[parameter]})
    return paginate_queryset(queryset, filters, {"code": "code", "name": "name", "created_at": "created_at",
        "effective_from": "latest_effective_from", "version": "latest_version_no"})


def recipe_detail(*, organization, pk):
    return _get(recipe_queryset(organization=organization), pk)


def version_queryset(*, recipe):
    return RecipeVersion.objects.filter(recipe=recipe).select_related("output_uom").annotate(date_status=_date_status())


def version_detail(*, recipe, pk):
    return _get(version_queryset(recipe=recipe), pk)


def version_list(*, recipe, filters):
    queryset = version_queryset(recipe=recipe)
    for field in ("status", "date_status"):
        parameter = "effective" if field == "date_status" else field
        if filters.get(parameter):
            queryset = queryset.filter(**{field: filters[parameter]})
    return paginate_queryset(queryset, filters, {"version": "version_no", "created_at": "created_at", "effective_from": "effective_from"}, "-version")


def line_queryset(*, version, organization):
    return RecipeLine.objects.filter(recipe_version=version, component_item__organization=organization).select_related("component_item", "uom")


def line_detail(*, version, organization, pk):
    return _get(line_queryset(version=version, organization=organization), pk)


def line_list(*, version, organization, filters):
    return paginate_queryset(line_queryset(version=version, organization=organization), filters, {"order": "display_order"}, "order")


def recipe_filter_options(*, organization):
    return (
        ("product", "Sản phẩm", ((p.pk, f"{p.code} — {p.name}") for p in Product.objects.filter(organization=organization).order_by("code"))),
        ("sku", "SKU của sản phẩm", ((s.pk, f"{s.code} — {s.name}") for s in Sku.objects.filter(organization=organization, product__organization=organization).order_by("code"))),
        ("status", "Trạng thái phiên bản mới nhất", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES),
        ("active", "Trạng thái định mức", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động"))),
    )
