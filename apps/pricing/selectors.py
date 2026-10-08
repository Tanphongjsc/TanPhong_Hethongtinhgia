"""DB-side lists and context selectors; never compute selling prices."""
from datetime import date, datetime
from django.db.models import Case, CharField, Q, Value, When
from django.db.models.functions import Concat
from django.http import Http404
from django.utils import timezone
from apps.core.models import Channel, Currency, ProductCategory, Sku
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset
from .constants import MODELS, CHANNEL_TYPES, LEGACY_STATUSES, code_label

RELATIONS = {"channel": ("default_currency_code",), "channel_fee_rule": ("channel", "currency_code", "product_category", "sku", "sku__product"), "tax_rule": ("currency_code",), "fx_rate": ("from_currency_code", "to_currency_code")}
SORTS = {"channel": {f: f for f in ("code", "name", "channel_type", "created_at")}, "channel_fee_rule": {"channel": "channel__code", "fee_type": "fee_type", "rate": "rate", "priority": "priority", "effective_from": "effective_from", "created_at": "created_at"}, "tax_rule": {f: f for f in ("jurisdiction_code", "tax_type", "rate", "priority", "effective_from", "created_at")}, "fx_rate": {f: f for f in ("from_currency_code", "to_currency_code", "rate", "rate_type", "effective_at", "created_at")}}


def queryset(*, resource, organization):
    query = MODELS[resource].objects.filter(organization=organization).select_related(*RELATIONS[resource])
    if resource != "channel":
        start, end, today = ("effective_at", "valid_to", timezone.now()) if resource == "fx_rate" else ("effective_from", "effective_to", timezone.localdate())
        # Half-open periods [start, end), as the canonical business rule defines.
        query = query.annotate(date_status=Case(When(**{start + "__gt": today}, then=Value("FUTURE")), When(**{end + "__lte": today}, then=Value("EXPIRED")), default=Value("EFFECTIVE"), output_field=CharField()))
    return query


def list_records(*, resource, organization, filters):
    query = queryset(resource=resource, organization=organization)
    fields = {"channel": ("code", "name", "platform_code", "market_code"), "channel_fee_rule": ("channel__code", "channel__name", "fee_type", "fee_base", "sku__code", "sku__name", "product_category__code", "product_category__name"), "tax_rule": ("jurisdiction_code", "tax_type", "tax_class_code", "seller_type", "transaction_type", "tax_base"), "fx_rate": ("from_currency_code__code", "to_currency_code__code", "source_name", "rate_type")}[resource]
    query = search_queryset(query, filters.get("q", ""), fields)
    if resource == "channel":
        if filters.get("active") in ("true", "false"): query = query.filter(is_active=filters["active"] == "true")
        if filters.get("channel_type"): query = query.filter(channel_type=filters["channel_type"])
    if resource == "channel_fee_rule":
        for name in ("channel", "sku", "product_category"): query = filter_id(query, filters, name, name + "_id")
    for name in {"channel": ("default_currency_code",), "channel_fee_rule": ("fee_type", "fee_base", "currency_code", "status", "effective"), "tax_rule": ("jurisdiction_code", "tax_type", "tax_class_code", "seller_type", "transaction_type", "currency_code", "status", "effective"), "fx_rate": ("rate_type", "from_currency_code", "to_currency_code", "status", "effective")}[resource]:
        if filters.get(name): query = query.filter(**{"date_status" if name == "effective" else name: filters[name]})
    return paginate_queryset(query, filters, SORTS[resource], default="code" if resource == "channel" else "-effective_at" if resource == "fx_rate" else "-effective_from")


def detail(*, resource, organization, pk):
    try: return queryset(resource=resource, organization=organization).get(pk=pk)
    except MODELS[resource].DoesNotExist: raise Http404("Không tìm thấy dữ liệu.") from None


def filter_options(*, resource, organization):
    query = MODELS[resource].objects.filter(organization=organization)
    currencies = Currency.objects.order_by("code").values_list("code", "name")
    currency_choices = [(code, f"{code} — {name}") for code, name in currencies]
    if resource == "channel":
        return (("active", "Trạng thái", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động"))), ("channel_type", "Loại kênh", CHANNEL_TYPES), ("default_currency_code", "Tiền tệ mặc định", currency_choices))
    options = []
    if resource == "channel_fee_rule":
        for name, label, model in (("channel", "Kênh bán", Channel), ("product_category", "Nhóm sản phẩm", ProductCategory), ("sku", "SKU", Sku)):
            choices = model.objects.filter(organization=organization).annotate(text=Concat("code", Value(" — "), "name")).order_by("code").values_list("pk", "text")
            options.append((name, label, choices))
    for name, label in {"channel_fee_rule": (("fee_type", "Loại phí"), ("fee_base", "Cơ sở tính phí")), "tax_rule": (("jurisdiction_code", "Khu vực"), ("tax_type", "Loại thuế"), ("tax_class_code", "Nhóm thuế"), ("seller_type", "Loại người bán"), ("transaction_type", "Loại giao dịch")), "fx_rate": (("rate_type", "Loại tỷ giá"),)}[resource]:
        options.append((name, label, [(code, code_label(code)) for code in query.exclude(**{name: None}).order_by(name).values_list(name, flat=True).distinct()]))
    for name, label in ((("from_currency_code", "Tiền tệ nguồn"), ("to_currency_code", "Tiền tệ đích")) if resource == "fx_rate" else (("currency_code", "Tiền tệ"),)):
        options.append((name, label, currency_choices))
    statuses = tuple((code, label) for code, label in LEGACY_STATUSES if resource != "fx_rate" or code != "IN_REVIEW")
    return (*options, ("status", "Trạng thái bản ghi", statuses), ("effective", "Hiệu lực theo thời gian", (("EFFECTIVE", "Đang hiệu lực"), ("FUTURE", "Sắp hiệu lực"), ("EXPIRED", "Hết hiệu lực"))))


class PricingResolutionError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _dated(resource, organization, on_date):
    if not isinstance(on_date, date) or isinstance(on_date, datetime):
        raise PricingResolutionError("INVALID_DATE", "Vui lòng truyền ngày áp dụng rõ ràng.")
    return queryset(resource=resource, organization=organization).filter(status="EFFECTIVE", effective_from__lte=on_date).filter(Q(effective_to__isnull=True) | Q(effective_to__gt=on_date))


def get_applicable_channel_fee_rules(*, organization, channel, on_date, sku=None, product_category=None, currency=None, include_all_currencies=False):
    # Do not choose a winning rule or sum fees. Return every matching definition.
    if channel.organization_id != organization.pk or (sku and sku.organization_id != organization.pk) or (product_category and product_category.organization_id != organization.pk):
        raise PricingResolutionError("INVALID_SCOPE", "Phạm vi không thuộc dữ liệu hệ thống.")
    if sku:
        if product_category and sku.product.category_id != product_category.pk:
            raise PricingResolutionError("INVALID_SCOPE", "SKU không thuộc nhóm sản phẩm đã chọn.")
        product_category = sku.product.category
    query = _dated("channel_fee_rule", organization, on_date).filter(channel=channel)
    query = query.filter(Q(sku__isnull=True) | Q(sku=sku)).filter(Q(product_category__isnull=True) | Q(product_category=product_category))
    if not include_all_currencies:
        query = query.filter(Q(currency_code__isnull=True) | Q(currency_code=currency))
    return query.order_by("-priority", "pk")


def get_applicable_tax_rules(*, organization, jurisdiction_code, on_date, tax_type=None, tax_class_code=None, seller_type=None, transaction_type=None, currency=None, include_all_currencies=False):
    if not isinstance(jurisdiction_code, str) or not jurisdiction_code.strip():
        raise PricingResolutionError("INVALID_SCOPE", "Vui lòng truyền mã khu vực áp dụng thuế rõ ràng.")
    query = _dated("tax_rule", organization, on_date).filter(jurisdiction_code=jurisdiction_code)
    if tax_type is not None: query = query.filter(tax_type=tax_type)
    for name, value in (("tax_class_code", tax_class_code), ("seller_type", seller_type), ("transaction_type", transaction_type)):
        query = query.filter(Q(**{name + "__isnull": True}) | Q(**{name: value}))
    if not include_all_currencies:
        query = query.filter(Q(currency_code__isnull=True) | Q(currency_code=currency))
    return query.order_by("-priority", "pk")


def get_effective_fx_rate(*, organization, from_currency, to_currency, rate_type, effective_at):
    from_currency = getattr(from_currency, "pk", from_currency)
    to_currency = getattr(to_currency, "pk", to_currency)
    if not isinstance(effective_at, datetime) or timezone.is_naive(effective_at):
        raise PricingResolutionError("INVALID_INSTANT", "Vui lòng truyền thời điểm có múi giờ rõ ràng.")
    if from_currency == to_currency:
        raise PricingResolutionError("INVALID_PAIR", "Cặp tiền tệ nguồn và đích phải khác nhau.")
    query = queryset(resource="fx_rate", organization=organization).filter(from_currency_code=from_currency, to_currency_code=to_currency, rate_type=rate_type, status="EFFECTIVE", effective_at__lte=effective_at)
    rows = list(query.filter(Q(valid_to__isnull=True) | Q(valid_to__gt=effective_at)).order_by("pk")[:2])
    if not rows: raise PricingResolutionError("MISSING_FX", "Không tìm thấy tỷ giá hiệu lực đúng chiều và loại đã chọn.")
    if len(rows) != 1: raise PricingResolutionError("AMBIGUOUS_FX", "Có nhiều tỷ giá cùng hiệu lực. Vui lòng kiểm tra các khoảng thời gian.")
    return rows[0]
