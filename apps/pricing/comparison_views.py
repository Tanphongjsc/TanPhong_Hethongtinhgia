from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.decorators.vary import vary_on_headers
from apps.master_data.access import require_access
from apps.master_data.constants import PAGE_SIZES
from apps.master_data.ui_helpers import is_htmx
from . import comparison_selectors as selectors
from .comparison import load_selection, stored, validate_compatibility
from .comparison_presentation import column, matrix


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scenario_compare(request):
    workspace = require_access(request, resource="scenario")
    filters = request.GET.copy()
    errors, selected, comparison = [], [], None
    requested = filters.get("compare") == "1"
    try:
        selected = load_selection(organization=workspace.organization, values=filters.getlist("scenario"), required=requested)
        if requested:
            validate_compatibility(selected)
            baseline = filters.get("baseline") or str(selected[0].record.pk)
            if baseline not in {str(s.record.pk) for s in selected}:
                raise ValidationError("Kịch bản mốc phải thuộc danh sách đã chọn.")
            comparison = matrix(selected, int(baseline))
    except ValidationError as error:
        errors = error.messages
    if selected and not filters.get("product"):
        filters["product"] = str(selected[0].key[0])
        if selected[0].key[1]:
            filters["sku"] = str(selected[0].key[1])
    page, sort, size = selectors.candidates(organization=workspace.organization, filters=filters)
    candidates = []
    for record in page.object_list:
        try:
            candidates.append(column(stored(record)))
        except ValidationError:
            # Corrupt legacy rows cannot be selected; never repair historical data here.
            continue
    selected_columns = [column(s) for s in selected]
    selected_ids = [s.record.pk for s in selected]
    page_ids = {c["id"] for c in candidates}
    url = reverse("pricing:scenario_compare")
    for c in selected_columns:
        query = filters.copy()
        query.setlist("scenario", [str(pk) for pk in selected_ids if pk != c["id"]])
        if query.get("baseline") == str(c["id"]):
            query.pop("baseline", None)
        if len(selected_ids) <= 2:
            query.pop("compare", None)
        c["remove_url"] = url + "?" + query.urlencode()
    sku = filters.get("sku", "")
    insufficient = False
    if sku.isascii() and sku.isdecimal() and len(sku) <= 18:
        # Read at most two IDs; no need to count an entire SKU history.
        insufficient = len(list(selectors.eligible(workspace.organization).filter(base_run__sku_id=sku).values_list("pk", flat=True)[:2])) < 2
    ctx = {"page_title": "So sánh kịch bản", "page_description": "Chọn 2–5 kịch bản đã tính của cùng SKU và cùng cơ sở đơn vị. Kết quả được đọc từ dữ liệu đã lưu.",
        "breadcrumbs": (("Giá bán", ""), ("So sánh kịch bản", url)), "resource_label": "kịch bản so sánh",
        "list_url": url, "table_id": "scenario-comparison", "filter_form_id": "comparison-form", "search_id": "comparison-search",
        "search_placeholder": "Tìm mã hoặc tên kịch bản…", "filters": filters, "errors": errors, "selected": selected_columns,
        "selected_ids": selected_ids, "hidden_ids": [pk for pk in selected_ids if pk not in page_ids], "candidates": candidates,
        "comparison": comparison, "compared": requested, "page_obj": page, "current_sort": sort, "per_page": size, "page_sizes": PAGE_SIZES,
        "filter_options": tuple({"name": name, "label": label, "choices": choices, "selected": filters.get(name, "")} for name, label, choices in selectors.filter_options(workspace.organization, filters)),
        "preserved_query_items": [(k, v) for k, values in filters.lists() for v in values],
        "insufficient": insufficient}
    return render(request, "pricing/comparison/partials/content.html" if is_htmx(request) else "pricing/comparison/page.html", ctx)
