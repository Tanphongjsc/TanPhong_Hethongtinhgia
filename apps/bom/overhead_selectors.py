"""ORM-only, database-side overhead search/filter/sort/pagination."""
from django.db.models import CharField, Count, Q, Value
from django.db.models.functions import Concat

from apps.core.models import AllocationRule, CostPool, Uom
from apps.master_data.query_helpers import filter_id, paginate_queryset, search_queryset
from .definition_helpers import date_status, get_by_pk
from .overhead_constants import ALLOCATION_BASES, DATE_STATUSES, POOL_TYPES, RULE_STATUSES


def pool_queryset(*, organization):
    return CostPool.objects.filter(organization=organization).annotate(rule_count=Count("allocationrule", filter=Q(allocationrule__organization=organization)))


def rule_queryset(*, organization):
    return AllocationRule.objects.filter(organization=organization, pool__organization=organization).select_related("pool", "basis_uom").annotate(date_status=date_status())


def cost_pool_list(*, organization, filters):
    query = search_queryset(pool_queryset(organization=organization), filters.get("q", ""), ("code", "name", "description"))
    active = filters.get("active", filters.get("is_active"))
    if active in ("true", "false"):
        query = query.filter(is_active=active == "true")
    if filters.get("pool_type"):
        query = query.filter(pool_type=filters["pool_type"])
    return paginate_queryset(query, filters, {field: field for field in ("code", "name", "created_at")})


def allocation_rule_list(*, organization, filters, pool=None):
    query = rule_queryset(organization=organization)
    if pool is not None:
        query = query.filter(pool=pool)
    else:
        query = filter_id(query, filters, "pool", "pool_id")
    query = filter_id(query, filters, "basis_uom", "basis_uom_id")
    query = search_queryset(query, filters.get("q", ""), ("code", "name", "pool__code", "pool__name"))
    for parameter, field in (("basis_type", "basis_type"), ("status", "status"), ("effective", "date_status")):
        if filters.get(parameter):
            query = query.filter(**{field: filters[parameter]})
    return paginate_queryset(query, filters, {field: field for field in ("code", "name", "priority", "effective_from", "created_at")})


def overhead_detail(*, resource, organization, pk):
    query = {"cost_pool": pool_queryset, "allocation_rule": rule_queryset}[resource](organization=organization)
    return get_by_pk(query, pk)


def _named_choices(query):
    return query.annotate(filter_label=Concat("code", Value(" — "), "name", output_field=CharField())).order_by("code", "pk").values_list("pk", "filter_label")


def filter_options(*, resource, organization, pool=None):
    if resource == "cost_pool":
        return (("pool_type", "Loại nhóm chi phí", POOL_TYPES), ("active", "Trạng thái", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động"))))
    # Include inactive catalogs in filters so historical configuration stays findable.
    choices = () if pool is not None else (("pool", "Nhóm chi phí", _named_choices(CostPool.objects.filter(organization=organization))),)
    return (*choices, ("basis_type", "Tiêu thức phân bổ", ALLOCATION_BASES),
        ("basis_uom", "Đơn vị tiêu thức", tuple((unit.pk, f"{unit.name} ({unit.symbol})") for unit in Uom.objects.order_by("name", "pk"))),
        ("status", "Trạng thái bản ghi", RULE_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES))
