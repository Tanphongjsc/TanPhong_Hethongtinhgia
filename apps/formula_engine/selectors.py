from django.db.models import OuterRef, Q, Subquery
from apps.core.models import CostElement, Formula, FormulaTestCase, FormulaVersion
from apps.master_data.query_helpers import paginate_queryset, search_queryset
from apps.bom.definition_helpers import date_status, get_by_pk
from apps.master_data.constants import VALUE_TYPES
from .constants import VERSION_STATUSES, VALIDATION_STATUSES
from .engine import ELEMENT_RELATIONS, FORMULA_RELATIONS
from .parser import IDENTIFIER


def formula_queryset(organization):
    return Formula.objects.filter(organization=organization).filter(Q(output_element__isnull=True) | Q(output_element__organization=organization)).select_related(*FORMULA_RELATIONS)


def formula_list(*, organization, filters):
    latest = FormulaVersion.objects.filter(formula_id=OuterRef("pk")).order_by("-version_no", "-pk")
    query = formula_queryset(organization).annotate(**{f"latest_{name}": Subquery(latest.values(name)[:1]) for name in
        ("pk", "version_no", "status", "validation_status", "effective_from", "effective_to")})
    query = query.annotate(date_status=date_status("latest_effective_from", "latest_effective_to"))
    query = search_queryset(query, filters.get("q", ""), ("code", "name", "description"))
    for parameter, field in (("status", "latest_status"), ("validation", "latest_validation_status"), ("effective", "date_status"), ("value_type", "output_element__value_type")):
        if filters.get(parameter): query = query.filter(**{field: filters[parameter]})
    if filters.get("active") in ("true", "false"): query = query.filter(is_active=filters["active"] == "true")
    return paginate_queryset(query, filters, {"code": "code", "name": "name", "version": "latest_version_no", "updated_at": "updated_at"})


def formula_detail(*, organization, pk):
    return get_by_pk(formula_queryset(organization), pk)


def version_detail(*, formula, pk):
    return get_by_pk(FormulaVersion.objects.filter(formula=formula).annotate(date_status=date_status()), pk)


def latest_version(formula):
    return FormulaVersion.objects.filter(formula=formula).annotate(date_status=date_status()).order_by("-version_no", "-pk").first()


def version_list(*, formula, filters):
    query = FormulaVersion.objects.filter(formula=formula).annotate(date_status=date_status())
    if filters.get("status"): query = query.filter(status=filters["status"])
    return paginate_queryset(query, filters, {"version": "version_no", "effective_from": "effective_from", "created_at": "created_at"}, "-version")


def test_cases(formula):
    return FormulaTestCase.objects.filter(formula=formula, is_active=True).order_by("name", "pk")[:200]


def catalogue(*, organization, keyword=""):
    elements = search_queryset(CostElement.objects.filter(organization=organization, is_active=True).select_related(*ELEMENT_RELATIONS), keyword, ("code", "name"))
    formulas = search_queryset(formula_queryset(organization).filter(is_active=True), keyword, ("code", "name"))
    # Bounded token palette; search retrieves other codes without loading full tables.
    return tuple({"label": record.name, "code": record.code, "token": prefix + record.code,
        "kind": "Phần tử chi phí" if prefix == "$" else "Công thức"} for prefix, query in (("$", elements), ("@", formulas))
        for record in query.order_by("code")[:60] if IDENTIFIER.fullmatch(record.code))


def filter_options():
    return (("status", "Trạng thái phiên bản mới nhất", VERSION_STATUSES), ("validation", "Kiểm tra đã lưu", VALIDATION_STATUSES),
        ("value_type", "Kiểu đầu ra đã khai báo", VALUE_TYPES), ("active", "Trạng thái công thức", (("true", "Đang hoạt động"), ("false", "Ngừng hoạt động"))),
        ("effective", "Hiệu lực theo ngày", (("UNDATED", "Chưa đặt hiệu lực"), ("FUTURE", "Sắp hiệu lực"), ("EFFECTIVE", "Đang hiệu lực"), ("EXPIRED", "Hết hiệu lực"))))
