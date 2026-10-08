from django.http import Http404

from apps.core.models import Item, Product, ProductCategory, Sku, Uom
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset
from .constants import ITEM_TYPES, UNIT_FIELDS


def category_queryset(*, organization):
    return ProductCategory.objects.filter(organization=organization)


def item_queryset(*, organization):
    return Item.objects.filter(organization=organization).select_related("category", *UNIT_FIELDS)


def product_queryset(*, organization):
    return Product.objects.filter(organization=organization).select_related("category", "costing_uom", "output_item")


def sku_queryset(*, organization):
    return Sku.objects.filter(organization=organization, product__organization=organization).select_related(
        "product", "product__category", "sales_uom", "net_quantity_uom", "sell_item",
    )


def _active(queryset, filters):
    active = filters.get("active", filters.get("is_active"))
    if active in ("true", "false"):
        queryset = queryset.filter(is_active=active == "true")
    return queryset


def category_list(*, organization, filters):
    queryset = search_queryset(category_queryset(organization=organization), filters.get("q", ""), ("code", "name", "description"))
    return paginate_queryset(_active(queryset, filters), filters, {field: field for field in ("code", "name", "created_at")})


def item_list(*, organization, filters):
    queryset = search_queryset(item_queryset(organization=organization), filters.get("q", ""), ("code", "name"))
    for field in ("category", "base_uom"):
        queryset = filter_id(queryset, filters, field, f"{field}_id")
    if filters.get("item_type"):
        queryset = queryset.filter(item_type=filters["item_type"])
    if filters.get("is_stock_item") in ("true", "false"):
        queryset = queryset.filter(is_stock_item=filters["is_stock_item"] == "true")
    return paginate_queryset(_active(queryset, filters), filters, {field: field for field in ("code", "name", "item_type", "created_at")})


def product_list(*, organization, filters):
    queryset = search_queryset(product_queryset(organization=organization), filters.get("q", ""), ("code", "name", "description"))
    for parameter, field in (("category", "category_id"), ("costing_uom", "costing_uom_id")):
        queryset = filter_id(queryset, filters, parameter, field)
    return paginate_queryset(_active(queryset, filters), filters,
        {"code": "code", "name": "name", "category": "category__code", "created_at": "created_at"})


def sku_list(*, organization, filters):
    queryset = search_queryset(sku_queryset(organization=organization), filters.get("q", ""), ("code", "name", "product__code", "product__name"))
    for parameter, field in (("product", "product_id"), ("category", "product__category_id")):
        queryset = filter_id(queryset, filters, parameter, field)
    return paginate_queryset(_active(queryset, filters), filters,
        {"code": "code", "name": "name", "product": "product__code", "created_at": "created_at"})


def product_detail(*, resource, organization, pk):
    if not 0 < pk <= 9223372036854775807:
        raise Http404
    selector = {"product_category": category_queryset, "item": item_queryset, "product": product_queryset, "sku": sku_queryset}[resource]
    queryset = selector(organization=organization)
    try:
        return queryset.get(pk=pk)
    except queryset.model.DoesNotExist:
        raise Http404 from None


def product_filter_options(*, resource, organization):
    active = ("active", "Trạng thái", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động")))
    if resource == "product_category":
        return (active,)
    # Filters can include inactive references to find historical records.
    categories = tuple((row.pk, f"{row.code} — {row.name}") for row in category_queryset(organization=organization).order_by("code"))
    if resource == "sku":
        products = tuple((row.pk, f"{row.code} — {row.name}") for row in Product.objects.filter(organization=organization).order_by("code"))
        return (("product", "Sản phẩm", products), ("category", "Nhóm sản phẩm", categories), active)
    units = tuple((row.pk, f"{row.name} ({row.symbol})") for row in Uom.objects.order_by("name", "code"))
    if resource == "product":
        return (("category", "Nhóm sản phẩm", categories), ("costing_uom", "Đơn vị tính giá thành", units), active)
    return (
        ("category", "Nhóm sản phẩm", categories), ("item_type", "Loại", ITEM_TYPES),
        ("base_uom", "Đơn vị cơ sở", units),
        ("is_stock_item", "Hàng tồn kho", (("true", "Có quản lý tồn kho"), ("false", "Không quản lý tồn kho"))), active,
    )
