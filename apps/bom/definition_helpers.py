"""Small presentation/query helpers shared by Recipe and Packaging."""
from django.db.models import Case, CharField, Value, When
from django.http import Http404
from django.utils import timezone

from apps.master_data.constants import PAGE_SIZES


def date_status(start="effective_from", end="effective_to"):
    today = timezone.localdate()
    return Case(When(**{f"{start}__isnull": True}, then=Value("UNDATED")),
        When(**{f"{start}__gt": today}, then=Value("FUTURE")),
        When(**{f"{end}__lt": today}, then=Value("EXPIRED")), default=Value("EFFECTIVE"), output_field=CharField())


def get_by_pk(queryset, pk):
    if not isinstance(pk, int) or not 0 < pk <= 9223372036854775807:
        raise Http404
    try:
        return queryset.get(pk=pk)
    except queryset.model.DoesNotExist:
        raise Http404 from None


def table_context(*, page, sort, per_page, list_url, columns, rows_template, sort_labels, **extra):
    return {"page_obj": page, "records": page.object_list, "current_sort": sort, "per_page": per_page,
        "page_sizes": PAGE_SIZES, "list_url": list_url, "columns": columns, "column_count": len(columns) + 1,
        "rows_template": rows_template, "table_id": "reference-data-table", "filter_form_id": "reference-data-filters",
        "search_id": "reference-data-search", "sort_options": tuple((prefix + field, label + (" ↓" if prefix else " ↑"))
            for field, label in sort_labels for prefix in ("", "-")), **extra}
