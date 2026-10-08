from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers
from apps.master_data.access import require_access
from apps.master_data.constants import PAGE_SIZES
from apps.master_data.ui_helpers import is_htmx, add_form_error, saved_response
from apps.bom.definition_helpers import table_context
from . import run_selectors as selectors
from .run_forms import RunForm
from .run_services import create_run


def _context(request, **extra):
    request.costing_resource_label = "lần tính giá thành"
    return {"resource": "run", "resource_label": "lần tính giá thành", "page_title": "Lần tính giá thành",
        "page_description": "Kết quả và dữ liệu đã sử dụng được lưu theo từng lần tính.",
        "breadcrumbs": (("Tổng quan", None), ("Lần tính giá thành", reverse("costing:run_list"))), **extra}


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def run_list(request):
    context = _context(request)
    workspace = require_access(request, resource="run")
    page, sort, per_page = selectors.run_list(organization=workspace.organization, filters=request.GET)
    options = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")} for name, label, choices in selectors.filter_options(workspace.organization))
    context.update(table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("costing:run_list"),
        columns=(("run_no", "Mã lần tính", False), ("costing_date", "Ngày tính giá", False), (None, "Sản phẩm / SKU", False), (None, "Phương án", False),
            (None, "Sản lượng", True), ("total_cost", "Giá thành sản xuất", True), (None, "Trạng thái", False)),
        rows_template="costing/runs/partials/rows.html", sort_labels=(("costing_date", "Ngày tính giá"), ("created_at", "Ngày tạo"), ("total_cost", "Giá thành"), ("run_no", "Mã lần tính")),
        filter_options=options, filters=request.GET, has_filters=bool(request.GET), search_placeholder="Tìm mã lần tính, sản phẩm, SKU hoặc phương án…",
        primary_action_url=reverse("costing:run_create"), primary_action_label="+ Chạy tính giá", detail_url_name="costing:run_detail"))
    context["date_filters"] = tuple({"name": name, "label": label, "value": request.GET.get(name, "")} for name, label in (("date_from", "Từ ngày"), ("date_to", "Đến ngày")))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "costing/runs/list.html", context)


def _form(request, source=None):
    workspace = require_access(request, "create", resource="run")
    initial = {}
    if source:
        initial = {name: value for name, value in source.context_jsonb.get("request", {}).items() if name not in ("manual", "supersedes_run")}
    form = RunForm(request.POST if request.method == "POST" else None, workspace=workspace, initial=initial, options_url=reverse("costing:run_options"))
    if source and not form.is_bound:
        manual = source.context_jsonb.get("request", {}).get("manual", {})
        for row, name, kind in form.manual_rows:
            if row.line_code in manual:
                value = manual[row.line_code]
                form.initial[name] = "true" if value is True else "false" if value is False else value
    if request.method == "POST" and form.is_valid():
        data = {**form.cleaned_data, "supersedes_run": source}
        try: run = create_run(workspace=workspace, data=data, idempotency_key=form.cleaned_data["idempotency_key"])
        except ValidationError as error: add_form_error(form, error)
        else:
            if run.run_status == "FAILED": messages.error(request, "Không thể tính giá thành. Vui lòng kiểm tra lỗi.")
            else: messages.success(request, "Đã chạy tính giá thành thành công." if not source else "Đã tạo lần tính giá mới từ kết quả trước.")
            return saved_response(request, reverse("costing:run_detail", args=[run.public_id]))
    if form.is_bound: form.mark_errors()
    context = _context(request, form=form, source=source, page_title="Chạy lại bằng dữ liệu hiện tại" if source else "Chạy tính giá thành", cancel_url=reverse("costing:run_list"))
    return render(request, "costing/runs/partials/form_content.html" if is_htmx(request) else "costing/runs/form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def run_create(request): return _form(request)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def run_rerun(request, public_id):
    _context(request)
    workspace = require_access(request, resource="run")
    source = selectors.run_detail(organization=workspace.organization, public_id=public_id)
    return _form(request, source)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def run_options(request):
    _context(request)
    workspace = require_access(request, resource="run")
    form = RunForm(workspace=workspace, initial=request.GET.dict(), options_url=reverse("costing:run_options"))
    if not is_htmx(request): return saved_response(request, reverse("costing:run_create"))
    return render(request, "costing/runs/partials/dependent_fields.html", {"form": form})


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def run_detail(request, public_id):
    context = _context(request)
    workspace = require_access(request, resource="run")
    run = selectors.run_detail(organization=workspace.organization, public_id=public_id)
    page, _, per_page = selectors.run_lines(run=run, filters=request.GET)
    selectors.display_lines(page.object_list, run.full_cost)
    display = run.context_jsonb.get("display", {})
    currency_places = 2
    currency_snapshot = run.version_snapshot_jsonb.get("sources", {}).get(f"currency:{run.result_currency_code_id}", {})
    currency_places = currency_snapshot.get("fields", {}).get("decimal_places", currency_places)
    per_unit = run.context_jsonb.get("per_unit")
    if per_unit is not None:
        from decimal import localcontext, ROUND_HALF_EVEN
        with localcontext() as arithmetic:
            arithmetic.prec = 50
            per_unit = Decimal(per_unit).quantize(Decimal(1).scaleb(-currency_places), rounding=ROUND_HALF_EVEN)
    context.update(run=run, display=display, per_unit=per_unit, page_obj=page, lines=page.object_list, per_page=per_page,
        page_sizes=PAGE_SIZES, query_base_url=reverse("costing:run_detail", args=[public_id]),
        table_id="run-lines-table", filter_form_id="run-lines-table", list_url=reverse("costing:run_detail", args=[public_id]),
        page_title="Kết quả tính giá thành", errors=run.context_jsonb.get("errors", []), warnings=run.context_jsonb.get("warnings", []),
        started_at=run.context_jsonb.get("started_at"), finished_at=run.context_jsonb.get("finished_at"))
    if is_htmx(request) and request.headers.get("HX-Target") == "run-lines-table": template = "costing/runs/partials/lines.html"
    else: template = "costing/runs/partials/detail_content.html" if is_htmx(request) else "costing/runs/detail.html"
    return render(request, template, context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def run_trace(request, public_id, line_pk):
    _context(request)
    workspace = require_access(request, resource="run")
    run = selectors.run_detail(organization=workspace.organization, public_id=public_id)
    line = selectors.line_detail(run=run, pk=line_pk)
    context = _context(request, run=run, line=line, steps=line.source_trace_jsonb.get("steps", []), inline_editor=is_htmx(request))
    return render(request, "costing/runs/partials/trace.html" if is_htmx(request) else "costing/runs/trace.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def run_snapshot(request, public_id):
    _context(request)
    workspace = require_access(request, resource="run")
    run = selectors.run_detail(organization=workspace.organization, public_id=public_id)
    context = _context(request, run=run, sources=selectors.source_rows(run), inputs=run.context_jsonb.get("request", {}),
        formulas=run.version_snapshot_jsonb.get("formulas", {}).values(), page_title="Dữ liệu đã sử dụng")
    return render(request, "costing/runs/partials/snapshot_content.html" if is_htmx(request) else "costing/runs/snapshot.html", context)
