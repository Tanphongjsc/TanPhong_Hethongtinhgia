"""Small ORM helpers shared by master data selectors; no CRUD framework."""
from django.core.paginator import Paginator
from django.db.models import Q

from .constants import PAGE_SIZES


def search_queryset(queryset, keyword, fields):
    keyword = keyword.strip()
    if keyword:
        condition = Q()
        for field in fields:
            condition |= Q(**{f"{field}__icontains": keyword})
        queryset = queryset.filter(condition)
    return queryset


def filter_id(queryset, filters, parameter, field):
    value = filters.get(parameter)
    if not value:
        return queryset
    if not value.isascii() or not value.isdecimal() or len(value) > 18:
        return queryset.none()
    return queryset.filter(**{field: value})


def paginate_queryset(queryset, filters, sort_fields, default="code"):
    sort = filters.get("sort", default)
    if sort.lstrip("-") not in sort_fields or sort.startswith("--"):
        sort = default
    field = sort_fields[sort.lstrip("-")]
    ordering = f"-{field}" if sort.startswith("-") else field
    try:
        per_page = int(filters.get("per_page", PAGE_SIZES[0]))
    except (ValueError, TypeError):
        per_page = PAGE_SIZES[0]
    if per_page not in PAGE_SIZES:
        per_page = PAGE_SIZES[0]
    page = Paginator(queryset.order_by(ordering, "pk"), per_page).get_page(filters.get("page", 1))
    return page, sort, per_page
