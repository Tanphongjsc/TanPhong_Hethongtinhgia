from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.decorators.vary import vary_on_headers
from apps.master_data.access import require_access
from apps.master_data.constants import PAGE_SIZES
from apps.master_data.ui_helpers import is_htmx, add_form_error, saved_response
from . import scenario_selectors as selectors, scenario_services as services
from .scenario_forms import ScenarioForm
from .scenario_presentation import decorate, result_fields, sources, trace_rows, display_date


def context():
    url = reverse("pricing:scenario_list")
    return {"page_title": "Kịch bản giá bán", "page_description": "Định giá từ kết quả giá thành đã lưu; giữ nguyên nguồn và cấu thành giá để giải thích lịch sử.",
        "resource_label": "kịch bản giá bán", "breadcrumbs": (("Giá bán", ""), ("Kịch bản giá bán", url)),
        "search_id": "scenario-search",
        "list_url": url, "table_id": "pricing-scenarios-table", "filter_form_id": "pricing-scenarios-filters",
        "rows_template": "pricing/scenarios/partials/rows.html", "column_count": 10, "search_placeholder": "Tìm mã, tên, sản phẩm hoặc SKU…",
        "detail_url_name": "pricing:scenario_detail", "edit_url_name": "pricing:scenario_edit"}


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scenario_list(request):
    workspace = require_access(request, resource="scenario")
    page, sort, size = selectors.list_scenarios(organization=workspace.organization, filters=request.GET)
    ctx = context()
    options = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")} for name, label, choices in selectors.filter_options(workspace.organization))
    ctx.update(page_obj=page, records=[decorate(r) for r in page.object_list], current_sort=sort, per_page=size, page_sizes=PAGE_SIZES,
        filters=request.GET, filter_options=options, has_filters=any(request.GET.get(key) for key in ("q", "product", "sku", "channel", "status", "currency_code", "date_from", "date_to")),
        date_filters=tuple({"name": name, "label": label, "value": request.GET.get(name, "")} for name, label in (("date_from", "Định giá từ ngày"), ("date_to", "Định giá đến ngày"))),
        columns=(("code", "Mã", False), ("name", "Tên kịch bản", False), (None, "Sản phẩm / SKU", False), (None, "Kênh bán", False), ("pricing_date", "Ngày định giá", False),
            (None, "Giá vốn", True), ("suggested_price", "Giá khách trả", True), (None, "Biên lợi nhuận", True), (None, "Trạng thái", False)),
        sort_options=tuple((prefix + name, label + (" ↓" if prefix else " ↑")) for name, label in (("code", "Mã"), ("name", "Tên"), ("pricing_date", "Ngày định giá"), ("suggested_price", "Giá khách trả"), ("created_at", "Ngày tạo")) for prefix in ("", "-")),
        primary_action_url=reverse("pricing:scenario_create"), primary_action_label="+ Thêm kịch bản")
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "pricing/scenarios/list.html", ctx)


def detail_context(record):
    ctx = context()
    snapshot = record.output_snapshot_jsonb or {}
    ctx.update(record=decorate(record), snapshot=snapshot, result=snapshot.get("result"), result_fields=result_fields(snapshot), source_rows=list(sources(snapshot)),
        trace_fee_rows=list(trace_rows(snapshot, "fee_lines")), trace_tax_rows=list(trace_rows(snapshot, "tax_lines")), costing_date=display_date(snapshot.get("costing", {}).get("effective_at")),
        target_margin=record.target_margin, target_markup=record.target_markup, target_profit_per_unit=record.target_profit_per_unit,
        costing=snapshot.get("costing", {}), can_calculate=record.status == "DRAFT",
        primary_action_url=None)
    return ctx


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scenario_detail(request, pk):
    workspace = require_access(request, resource="scenario")
    record = selectors.detail(organization=workspace.organization, pk=pk)
    return render(request, "pricing/scenarios/partials/detail_content.html" if is_htmx(request) else "pricing/scenarios/detail.html", detail_context(record))


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scenario_form(request, pk=None):
    workspace = require_access(request, "edit" if pk else "create", resource="scenario")
    record = selectors.detail(organization=workspace.organization, pk=pk) if pk else None
    if record and record.status != "DRAFT":
        if request.method == "GET": return redirect("pricing:scenario_detail", pk=pk)
        return render(request, "pricing/scenarios/partials/detail_content.html" if is_htmx(request) else "pricing/scenarios/detail.html", detail_context(record) | {"action_error": "Kịch bản đã chốt chỉ được xem; hãy tạo kịch bản mới."}, status=409)
    initial = {}
    if not record and request.GET.get("source", "").isascii() and request.GET.get("source", "").isdecimal() and len(request.GET["source"]) <= 18:
        source = selectors.detail(organization=workspace.organization, pk=request.GET["source"])
        initial = ScenarioForm(workspace=workspace, instance=source).initial
        initial.update(code="", name=source.name)
    form = ScenarioForm(request.POST if request.method == "POST" else None, workspace=workspace, instance=record, initial=initial)
    if request.method == "POST" and form.is_valid():
        try: saved = services.save_scenario(workspace=workspace, data=form.cleaned_data, instance=record)
        except ValidationError as error: add_form_error(form, error)
        else:
            messages.success(request, "Đã cập nhật kịch bản giá bán." if record else "Đã tạo kịch bản giá bán.")
            return saved_response(request, reverse("pricing:scenario_detail", args=[saved.pk]))
    if form.is_bound: form.mark_errors()
    ctx = context()
    ctx.update(form=form, record=record, page_title="Chỉnh sửa kịch bản giá bán" if record else "Thêm kịch bản giá bán",
        cancel_url=reverse("pricing:scenario_detail", args=[record.pk]) if record else ctx["list_url"])
    return render(request, "pricing/scenarios/partials/form_content.html" if is_htmx(request) else "pricing/scenarios/form.html", ctx)


@require_GET
def scenario_options(request):
    workspace = require_access(request, resource="scenario")
    form = ScenarioForm(workspace=workspace, initial=request.GET.dict())
    # A normal GET remains a complete page; history restore follows the same rule.
    ctx = context() | {"form": form, "cancel_url": reverse("pricing:scenario_list"), "form_action": reverse("pricing:scenario_create")}
    return render(request, "pricing/scenarios/partials/dependent_fields.html" if is_htmx(request) else "pricing/scenarios/form.html", ctx)


@require_POST
def scenario_calculate(request, pk):
    workspace = require_access(request, "edit", resource="scenario")
    record = selectors.detail(organization=workspace.organization, pk=pk)
    try: record = services.calculate_scenario(workspace=workspace, instance=record)
    except ValidationError as error:
        return render(request, "pricing/scenarios/partials/detail_content.html" if is_htmx(request) else "pricing/scenarios/detail.html", detail_context(record) | {"action_error": " ".join(error.messages)}, status=409)
    if record.status == "CALCULATED": messages.success(request, "Đã lưu kết quả giá bán.")
    if not is_htmx(request): return redirect("pricing:scenario_detail", pk=pk)
    return render(request, "pricing/scenarios/partials/detail_content.html", detail_context(record) | {"calculated_response": record.status == "CALCULATED"})
