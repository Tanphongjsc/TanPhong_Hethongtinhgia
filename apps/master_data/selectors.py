from django.core.paginator import Paginator
from django.db.models import Case, CharField, Q, Value, When
from django.db.models.functions import Concat
from django.utils import timezone
from django.http import Http404

from apps.core.models import CostElement, CostElementGroup, Currency, Item, Supplier, SupplierPrice, Uom, UomCategory, UomConversion
from .constants import PRICE_DATE_STATUSES, SUPPLIER_PRICE_STATUSES
from .constants import PAGE_SIZES, SORT_FIELDS
from .query_helpers import search_queryset as _search, filter_id as _id_filter, paginate_queryset as _sorted_page


def cost_element_queryset(*, organization, permissions):
    queryset = CostElement.objects.filter(organization=organization).select_related(
        "organization", "group", "currency_code", "default_uom"
    )
    if not permissions.can_view_sensitive_cost_element:
        queryset = queryset.filter(is_sensitive=False)
    return queryset


def cost_element_detail(*, organization, permissions, pk):
    try:
        return cost_element_queryset(organization=organization, permissions=permissions).get(pk=pk)
    except CostElement.DoesNotExist:
        raise Http404("Không tìm thấy phần tử chi phí.") from None


def cost_element_list(*, organization, permissions, filters):
    queryset = cost_element_queryset(organization=organization, permissions=permissions)
    keyword = filters.get("q", "").strip()
    if keyword:
        queryset = queryset.filter(Q(code__icontains=keyword) | Q(name__icontains=keyword) | Q(description__icontains=keyword))
    for parameter, field in (
        ("group", "group_id"), ("value_type", "value_type"),
        ("source_mode", "default_source_mode"), ("cost_scope", "cost_scope"),
    ):
        value = filters.get(parameter)
        if value:
            if parameter == "group":
                if not value.isascii() or not value.isdecimal() or len(value) > 18:
                    queryset = queryset.none()
                    continue
            queryset = queryset.filter(**{field: value})
    active = filters.get("active")
    if active in ("true", "false"):
        queryset = queryset.filter(is_active=active == "true")
    sort = filters.get("sort", "code")
    if sort not in {*SORT_FIELDS, *(f"-{field}" for field in SORT_FIELDS)}:
        sort = "code"
    queryset = queryset.order_by(sort, "pk")
    try:
        per_page = int(filters.get("per_page", PAGE_SIZES[0]))
    except (ValueError, TypeError):
        per_page = PAGE_SIZES[0]
    if per_page not in PAGE_SIZES:
        per_page = PAGE_SIZES[0]
    page = Paginator(queryset, per_page).get_page(filters.get("page", 1))
    return page, sort, per_page


def cost_element_groups(*, organization):
    return CostElementGroup.objects.filter(organization=organization).order_by("display_order", "code")


def _reference_page(queryset, filters, sort_fields, default="code"):
    active = filters.get("active", filters.get("is_active"))
    if active in ("true", "false"):
        queryset = queryset.filter(is_active=active == "true")
    return _sorted_page(queryset, filters, sort_fields, default)


def currency_list(*, filters, **context):
    queryset = _search(Currency.objects.all(), filters.get("q", ""), ("code", "name"))
    return _reference_page(queryset, filters, {name: name for name in ("code", "name", "decimal_places")})


def uom_category_list(*, filters, **context):
    queryset = _search(UomCategory.objects.all(), filters.get("q", ""), ("code", "name", "dimension_code"))
    return _reference_page(queryset, filters, {name: name for name in ("code", "name", "dimension_code")})


def uom_queryset():
    return Uom.objects.select_related("category")


def uom_list(*, filters, **context):
    queryset = _search(uom_queryset(), filters.get("q", ""), ("code", "name", "symbol"))
    queryset = _id_filter(queryset, filters, "category", "category_id")
    if filters.get("is_base") in ("true", "false"):
        queryset = queryset.filter(is_base=filters["is_base"] == "true")
    return _reference_page(queryset, filters, {"code": "code", "name": "name", "category": "category__code", "precision": "precision"})


def uom_conversion_queryset(*, organization):
    # Shared conversions are readable; item references must never expose another
    # organization's catalog, even if a legacy record has inconsistent scope.
    return UomConversion.objects.filter(
        Q(organization=organization) | Q(organization__isnull=True)
    ).filter(Q(item__isnull=True) | Q(item__organization=organization)).select_related(
        "organization", "from_uom", "to_uom", "item"
    )


def uom_conversion_list(*, organization, filters, **context):
    queryset = _search(uom_conversion_queryset(organization=organization), filters.get("q", ""),
        ("from_uom__code", "from_uom__name", "to_uom__code", "to_uom__name", "item__code", "item__name"))
    for name in ("from_uom", "to_uom", "item"):
        queryset = _id_filter(queryset, filters, name, f"{name}_id")
    return _sorted_page(queryset, filters,
        {"effective_from": "effective_from", "from_uom": "from_uom__code", "to_uom": "to_uom__code"}, "-effective_from")


def reference_detail(*, resource, pk, organization):
    if resource != "currency" and not 0 < pk <= 9223372036854775807:
        raise Http404
    queryset = {
        "currency": Currency.objects.all(),
        "uom_category": UomCategory.objects.all(),
        "uom": uom_queryset(),
        "uom_conversion": uom_conversion_queryset(organization=organization),
        "supplier": supplier_queryset(organization=organization),
        "supplier_price": supplier_price_queryset(organization=organization),
    }[resource]
    try:
        return queryset.get(pk=pk)
    except queryset.model.DoesNotExist:
        raise Http404 from None


def reference_filter_options(*, resource, organization):
    """Only reference choices needed by this page; no Python-side filtering."""
    active = ("active", "Trạng thái", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động")))
    if resource in ("currency", "uom_category"):
        return (active,)
    if resource == "supplier":
        return (active, ("currency", "Tiền tệ mặc định", _named_filter_choices(Currency.objects.all())))
    if resource == "supplier_price":
        return (
            ("supplier", "Nhà cung cấp", _named_filter_choices(Supplier.objects.filter(organization=organization))),
            ("item", "Vật tư / Hàng hóa", _named_filter_choices(Item.objects.filter(organization=organization))),
            ("currency", "Tiền tệ", _named_filter_choices(Currency.objects.all())),
            ("uom", "Đơn vị tính", Uom.objects.annotate(filter_label=Concat("name", Value(" ("), "symbol", Value(")"), output_field=CharField())).order_by("name", "code").values_list("pk", "filter_label")),
            ("effective", "Hiệu lực theo ngày", PRICE_DATE_STATUSES),
            ("status", "Trạng thái bản ghi", SUPPLIER_PRICE_STATUSES),
        )
    if resource == "uom":
        return (
            ("category", "Nhóm đơn vị tính", UomCategory.objects.order_by("code").values_list("pk", "code")),
            ("is_base", "Đơn vị cơ sở", (("true", "Đơn vị cơ sở"), ("false", "Đơn vị khác"))), active,
        )
    units = tuple(Uom.objects.order_by("code").values_list("pk", "code"))
    return (
        ("from_uom", "Đơn vị nguồn", units), ("to_uom", "Đơn vị đích", units),
        ("item", "Vật tư / Hàng hóa", Item.objects.filter(organization=organization).order_by("code").values_list("pk", "code")),
    )


def supplier_queryset(*, organization):
    return Supplier.objects.filter(organization=organization).select_related("default_currency_code")


def _named_filter_choices(queryset):
    return queryset.annotate(filter_label=Concat("code", Value(" — "), "name", output_field=CharField())).order_by("code").values_list("pk", "filter_label")


def supplier_list(*, organization, filters):
    queryset = _search(supplier_queryset(organization=organization), filters.get("q", ""), ("code", "name", "tax_code"))
    if filters.get("currency"):
        queryset = queryset.filter(default_currency_code_id=filters["currency"])
    return _reference_page(queryset, filters, {field: field for field in ("code", "name", "created_at")})


def supplier_price_queryset(*, organization, today=None):
    today = today or timezone.localdate()
    # Organization on the quote and company-owned references must all agree.
    # Inactive references remain readable on historical records.
    return SupplierPrice.objects.filter(organization=organization, supplier__organization=organization,
        item__organization=organization).select_related("supplier", "item", "price_uom", "currency_code").annotate(
        date_status=Case(
            When(effective_from__gt=today, then=Value("FUTURE")),
            When(effective_to__lt=today, then=Value("EXPIRED")),
            default=Value("EFFECTIVE"), output_field=CharField(),
        )
    )


def supplier_price_list(*, organization, filters):
    queryset = _search(supplier_price_queryset(organization=organization), filters.get("q", ""),
        ("supplier__code", "supplier__name", "item__code", "item__name"))
    for parameter, field in (("supplier", "supplier_id"), ("item", "item_id"), ("uom", "price_uom_id")):
        queryset = _id_filter(queryset, filters, parameter, field)
    if filters.get("currency"):
        queryset = queryset.filter(currency_code_id=filters["currency"])
    for parameter, field in (("effective", "date_status"), ("status", "status")):
        if filters.get(parameter):
            queryset = queryset.filter(**{field: filters[parameter]})
    return _sorted_page(queryset, filters, {"effective_from": "effective_from", "supplier": "supplier__code",
        "item": "item__code", "unit_price": "unit_price"}, "-effective_from")
