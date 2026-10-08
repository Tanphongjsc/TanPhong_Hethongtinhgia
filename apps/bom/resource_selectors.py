"""Database search, filtering and pagination with eager-loaded references."""
from django.db.models import CharField, Q, Value
from django.db.models.functions import Concat

from apps.core.models import Currency, Resource, ResourceRate, Uom, WorkCenter
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset
from .definition_helpers import date_status, get_by_pk
from .resource_constants import DATE_STATUSES, RATE_STATUSES, RESOURCE_TYPES


def work_center_queryset(*, organization):
    return WorkCenter.objects.filter(organization=organization).select_related("capacity_uom")


def resource_queryset(*, organization):
    return Resource.objects.filter(organization=organization).filter(
        Q(work_center__isnull=True) | Q(work_center__organization=organization)
    ).select_related("work_center", "capacity_uom")


def rate_queryset(*, organization):
    return ResourceRate.objects.filter(organization=organization, resource__organization=organization).filter(
        Q(resource__work_center__isnull=True) | Q(resource__work_center__organization=organization)
    ).select_related("resource", "resource__work_center", "currency_code", "per_uom").annotate(date_status=date_status())


def _active(query, filters):
    active = filters.get("active", filters.get("is_active"))
    return query.filter(is_active=active == "true") if active in ("true", "false") else query


def work_center_list(*, organization, filters):
    query = search_queryset(work_center_queryset(organization=organization), filters.get("q", ""), ("code", "name", "site_code"))
    return paginate_queryset(_active(query, filters), filters, {field: field for field in ("code", "name", "created_at")})


def resource_list(*, organization, filters):
    query = search_queryset(resource_queryset(organization=organization), filters.get("q", ""), ("code", "name"))
    query = filter_id(query, filters, "work_center", "work_center_id")
    if filters.get("resource_type"):
        query = query.filter(resource_type=filters["resource_type"])
    return paginate_queryset(_active(query, filters), filters, {field: field for field in ("code", "name", "resource_type", "created_at")})


def resource_rate_list(*, organization, filters, resource=None):
    query = rate_queryset(organization=organization)
    if resource is not None:
        query = query.filter(resource=resource)
    query = search_queryset(query, filters.get("q", ""), ("resource__code", "resource__name", "resource__work_center__code", "resource__work_center__name"))
    for name, field in (("resource", "resource_id"), ("work_center", "resource__work_center_id"), ("rate_uom", "per_uom_id")):
        query = filter_id(query, filters, name, field)
    for name, field in (("resource_type", "resource__resource_type"), ("currency", "currency_code_id"),
        ("effective", "date_status"), ("status", "status"), ("rate_type", "rate_type")):
        if filters.get(name):
            query = query.filter(**{field: filters[name]})
    return paginate_queryset(query, filters, {"resource": "resource__code", "rate": "amount", "effective_from": "effective_from", "created_at": "created_at"}, "-effective_from")


def production_detail(*, resource, organization, pk):
    query = {"work_center": work_center_queryset, "resource": resource_queryset, "resource_rate": rate_queryset}[resource](organization=organization)
    return get_by_pk(query, pk)


def _named_choices(query):
    return query.annotate(filter_label=Concat("code", Value(" — "), "name", output_field=CharField())).order_by("code", "pk").values_list("pk", "filter_label")


def filter_options(*, resource, organization):
    active = ("active", "Trạng thái", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động")))
    if resource == "work_center":
        return (active,)
    common = (("resource_type", "Loại nguồn lực", RESOURCE_TYPES),
        ("work_center", "Trung tâm sản xuất", _named_choices(work_center_queryset(organization=organization))))
    if resource == "resource":
        return common + (active,)
    units = Uom.objects.annotate(filter_label=Concat("name", Value(" ("), "symbol", Value(")"), output_field=CharField())).order_by("name", "pk").values_list("pk", "filter_label")
    return (("resource", "Nguồn lực", _named_choices(resource_queryset(organization=organization))),) + common + (
        ("rate_type", "Mã loại đơn giá", rate_queryset(organization=organization).order_by("rate_type").values_list("rate_type", "rate_type").distinct()),
        ("currency", "Tiền tệ", _named_choices(Currency.objects.all())), ("rate_uom", "Đơn vị tính giá", units),
        ("effective", "Hiệu lực theo ngày", DATE_STATUSES), ("status", "Trạng thái bản ghi", RATE_STATUSES))


def center_resources(*, organization, center):
    # Bounded overview; the linked resource list holds full pagination/filters.
    return resource_queryset(organization=organization).filter(work_center=center).order_by("code", "pk")[:10]
