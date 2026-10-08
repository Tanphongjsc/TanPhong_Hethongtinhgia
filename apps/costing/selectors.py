from django.db.models import Count, OuterRef, Subquery
from apps.core.models import CostingScheme, CostingSchemeVersion, CostingSchemeLine
from apps.master_data.query_helpers import search_queryset, paginate_queryset
from apps.bom.definition_helpers import date_status, get_by_pk
from apps.formula_engine.engine import ELEMENT_RELATIONS, FORMULA_RELATIONS
from .constants import VERSION_STATUSES, DATE_STATUSES

LINE_RELATIONS = ("cost_element", *("cost_element__" + name for name in ELEMENT_RELATIONS),
    "rule_table", "formula_version", "formula_version__formula",
    *("formula_version__formula__" + name for name in FORMULA_RELATIONS))


def scheme_queryset(*, organization):
    return CostingScheme.objects.filter(organization=organization)


def scheme_list(*, organization, filters):
    query = scheme_queryset(organization=organization)
    latest = CostingSchemeVersion.objects.filter(scheme_id=OuterRef("pk")).order_by("-version_no", "-pk")
    query = query.annotate(**{f"latest_{field}": Subquery(latest.values(field)[:1]) for field in ("version_no", "status", "effective_from", "effective_to")})
    query = query.annotate(date_status=date_status("latest_effective_from", "latest_effective_to"))
    query = search_queryset(query, filters.get("q", ""), ("code", "name", "description", "purpose", "context_scope"))
    for parameter, field in (("status", "latest_status"), ("effective", "date_status"), ("purpose", "purpose"), ("context_scope", "context_scope")):
        if filters.get(parameter): query = query.filter(**{field: filters[parameter]})
    if filters.get("active") in ("true", "false"): query = query.filter(is_active=filters["active"] == "true")
    return paginate_queryset(query, filters, {"code": "code", "name": "name", "version": "latest_version_no", "effective_from": "latest_effective_from", "updated_at": "updated_at"})


def scheme_detail(*, organization, pk):
    return get_by_pk(scheme_queryset(organization=organization), pk)


def version_queryset(*, scheme):
    return CostingSchemeVersion.objects.filter(scheme=scheme).annotate(date_status=date_status())


def version_detail(*, scheme, pk):
    return get_by_pk(version_queryset(scheme=scheme), pk)


def version_list(*, scheme, filters):
    query = version_queryset(scheme=scheme).annotate(line_count=Count("costingschemeline"))
    for parameter, field in (("status", "status"), ("effective", "date_status")):
        if filters.get(parameter): query = query.filter(**{field: filters[parameter]})
    return paginate_queryset(query, filters, {"version": "version_no", "effective_from": "effective_from", "created_at": "created_at"}, "-version")


def line_queryset(*, version):
    # Include stale/inactive references for explicit diagnostics, never hide missing inputs.
    return CostingSchemeLine.objects.filter(scheme_version=version).select_related(*LINE_RELATIONS).order_by("display_order", "pk")


def line_detail(*, version, pk):
    return get_by_pk(line_queryset(version=version), pk)


def line_list(*, version, filters):
    values = filters.dict() if hasattr(filters, "dict") else dict(filters)
    return paginate_queryset(line_queryset(version=version), {**values, "sort": "order"}, {"order": "display_order"}, "order")


def filter_options(*, organization):
    query = scheme_queryset(organization=organization)
    return (("purpose", "Mục đích", ((code, code) for code in query.values_list("purpose", flat=True).distinct().order_by("purpose"))),
        ("context_scope", "Phạm vi áp dụng", ((code, code) for code in query.values_list("context_scope", flat=True).distinct().order_by("context_scope"))),
        ("status", "Trạng thái phiên bản mới nhất", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES),
        ("active", "Trạng thái phương án", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động"))))
