"""Thin orchestration for production resource CRUD using existing UI patterns."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers

from apps.master_data.access import require_access
from apps.master_data.presentation import display_label, format_number
from apps.master_data.ui_helpers import add_form_error, is_htmx, saved_response
from . import resource_selectors as selectors, resource_services as services
from .definition_helpers import table_context
from .resource_forms import ResourceForm, ResourceRateForm, WorkCenterForm

PAGES = {
    "work_center": {
        "label": "trung tâm sản xuất", "title": "Trung tâm sản xuất", "form": WorkCenterForm,
        "selector": selectors.work_center_list, "service": services.save_work_center,
        "description": "Quản lý trung tâm, địa điểm và công suất sản xuất.",
        "columns": (("code", "Mã", False), ("name", "Tên trung tâm", False), (None, "Mã địa điểm", False),
            (None, "Công suất", True), (None, "Công suất bình thường", True), (None, "Đơn vị công suất", False), (None, "Trạng thái", False)),
        "sorts": (("code", "Mã"), ("name", "Tên"), ("created_at", "Ngày tạo")),
        "search": "Tìm theo mã, tên trung tâm hoặc mã địa điểm…",
    },
    "resource": {
        "label": "nguồn lực sản xuất", "title": "Nguồn lực sản xuất", "form": ResourceForm,
        "selector": selectors.resource_list, "service": services.save_resource,
        "description": "Quản lý nguồn lực và trung tâm sản xuất sử dụng nguồn lực.",
        "columns": (("code", "Mã", False), ("name", "Tên nguồn lực", False), ("resource_type", "Loại nguồn lực", False),
            (None, "Trung tâm sản xuất", False), (None, "Công suất", True), (None, "Đơn vị công suất", False), (None, "Trạng thái", False)),
        "sorts": (("code", "Mã"), ("name", "Tên"), ("resource_type", "Loại nguồn lực"), ("created_at", "Ngày tạo")),
        "search": "Tìm theo mã hoặc tên nguồn lực…",
    },
    "resource_rate": {
        "label": "đơn giá nguồn lực", "title": "Đơn giá nguồn lực", "form": ResourceRateForm,
        "selector": selectors.resource_rate_list, "service": services.save_resource_rate,
        "description": "Lưu đơn giá theo loại giá, tiền tệ, đơn vị sử dụng và khoảng hiệu lực.",
        "columns": (("resource", "Nguồn lực", False), (None, "Loại nguồn lực", False), (None, "Trung tâm sản xuất", False),
            (None, "Mã loại đơn giá", False), ("rate", "Đơn giá", True), (None, "Tiền tệ", False), (None, "Đơn vị tính giá", False),
            ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False), (None, "Trạng thái bản ghi", False)),
        "sorts": (("resource", "Nguồn lực"), ("rate", "Đơn giá"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        "search": "Tìm theo mã, tên nguồn lực hoặc trung tâm sản xuất…",
    },
}


def _context(request, resource):
    page = PAGES[resource]
    request.costing_resource_label = page["label"]
    list_url = reverse(f"bom:{resource}_list")
    return {"resource": resource, "resource_label": page["label"], "page_title": page["title"],
        "page_description": page["description"], "list_url": list_url,
        "breadcrumbs": (("Sản xuất", None), (page["title"], list_url)),
        "detail_url_name": f"bom:{resource}_detail", "edit_url_name": f"bom:{resource}_edit"}


def _table(request, workspace, resource, *, record=None, list_url=None):
    page = PAGES[resource]
    arguments = {"organization": workspace.organization, "filters": request.GET}
    if record is not None:
        arguments["resource"] = record
    records, sort, per_page = page["selector"](**arguments)
    options = tuple({"name": name, "label": label, "choices": choices,
        "selected": request.GET.get(name, request.GET.get("is_active", "") if name == "active" else "")}
        for name, label, choices in selectors.filter_options(resource=resource, organization=workspace.organization)) if record is None else ()
    return table_context(page=records, sort=sort, per_page=per_page, list_url=list_url or reverse(f"bom:{resource}_list"),
        columns=page["columns"], rows_template=f"bom/resources/partials/{resource}_rows.html", sort_labels=page["sorts"],
        filters=request.GET, filter_options=options, search_placeholder=page["search"],
        has_filters=any(request.GET.get(name) for name in ("q", "is_active", *(option["name"] for option in options))),
        can_edit=getattr(workspace.permissions, f"can_edit_{resource}"))


def _list(request, resource):
    context = _context(request, resource)
    workspace = require_access(request, resource=resource)
    context.update(_table(request, workspace, resource),
        primary_action_url=reverse(f"bom:{resource}_create") if getattr(workspace.permissions, f"can_create_{resource}") else None,
        primary_action_label="+ Thêm mới")
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _field(label, value, *, numeric=False, technical=False):
    return {"label": label, "value": format_number(value) if numeric else value, "numeric": numeric, "technical": technical}


def _unit(unit):
    return f"{unit.name} ({unit.symbol})" if unit else "—"


def _detail(request, resource, pk):
    context = _context(request, resource)
    workspace = require_access(request, resource=resource)
    record = selectors.production_detail(resource=resource, organization=workspace.organization, pk=pk)
    if resource == "work_center":
        sections = (("Thông tin trung tâm", (_field("Mã", record.code, technical=True), _field("Tên trung tâm", record.name), _field("Mã địa điểm", record.site_code, technical=True))),
            ("Công suất", (_field("Công suất", record.capacity_value, numeric=True), _field("Công suất bình thường", record.normal_capacity_value, numeric=True), _field("Đơn vị công suất", _unit(record.capacity_uom)))))
        context.update(center_resources=selectors.center_resources(organization=workspace.organization, center=record),
            resources_url=reverse("bom:resource_list") + f"?work_center={record.pk}")
    elif resource == "resource":
        sections = (("Thông tin nguồn lực", (_field("Mã", record.code, technical=True), _field("Tên nguồn lực", record.name), _field("Loại nguồn lực", display_label(record.resource_type)),
            _field("Trung tâm sản xuất", f"{record.work_center.code} — {record.work_center.name}" if record.work_center else "—"))),
            ("Năng lực", (_field("Công suất", record.capacity_value, numeric=True), _field("Đơn vị công suất", _unit(record.capacity_uom)))))
        # One paginated table on this page; full GET falls back to the detail.
        history_url = reverse("bom:resource_detail", args=[record.pk])
        history = _table(request, workspace, "resource_rate", record=record, list_url=history_url)
        history.update(resource="resource_rate", resource_label="đơn giá nguồn lực", detail_url_name="bom:resource_rate_detail", edit_url_name="bom:resource_rate_edit",
            primary_action_url=reverse("bom:resource_rate_create") + f"?resource={record.pk}" if workspace.permissions.can_create_resource_rate and record.is_active else None,
            primary_action_label="Thêm đơn giá")
        context["rate_history"] = history
        context["rate_list_url"] = reverse("bom:resource_rate_list") + f"?resource={record.pk}"
        if is_htmx(request) and request.headers.get("HX-Target") == "reference-data-table":
            return render(request, "master_data/partials/reference_data_table.html", history)
    else:
        sections = (("Nguồn lực", (_field("Nguồn lực", f"{record.resource.code} — {record.resource.name}"), _field("Loại nguồn lực", display_label(record.resource.resource_type)),
            _field("Trung tâm sản xuất", f"{record.resource.work_center.code} — {record.resource.work_center.name}" if record.resource.work_center else "—"), _field("Mã loại đơn giá", record.rate_type, technical=True))),
            ("Đơn giá", (_field("Đơn giá", f"{format_number(record.amount)} {record.currency_code_id} / {record.per_uom.name}"), _field("Tiền tệ", f"{record.currency_code.code} — {record.currency_code.name}"), _field("Đơn vị tính giá", _unit(record.per_uom)))),
            ("Hiệu lực", (_field("Hiệu lực từ ngày", record.effective_from.strftime("%d/%m/%Y")), _field("Hiệu lực đến ngày", record.effective_to.strftime("%d/%m/%Y") if record.effective_to else "Không giới hạn"),
                _field("Hiệu lực theo ngày", display_label(record.date_status)), _field("Trạng thái bản ghi", display_label(record.status)))),
            ("Tham chiếu", (_field("Nguồn dữ liệu / Tham chiếu", record.source_reference),)))
    context.update(record=record, page_title=record.name if resource != "resource_rate" else f"Đơn giá · {record.resource.name}", detail_sections=sections,
        primary_action_url=reverse(context["edit_url_name"], args=[record.pk]) if getattr(workspace.permissions, f"can_edit_{resource}") else None, primary_action_label="Chỉnh sửa")
    return render(request, "bom/resources/partials/detail_content.html" if is_htmx(request) else "bom/resources/detail.html", context)


def _form(request, resource, pk=None):
    context = _context(request, resource)
    workspace = require_access(request, "edit" if pk is not None else "create", resource=resource)
    record = selectors.production_detail(resource=resource, organization=workspace.organization, pk=pk) if pk is not None else None
    initial = {}
    if resource == "resource_rate" and pk is None and request.GET.get("resource"):
        value = request.GET["resource"]
        if value.isascii() and value.isdecimal() and len(value) <= 18:
            candidate = selectors.resource_queryset(organization=workspace.organization).filter(pk=value, is_active=True).first()
            if candidate:
                initial["resource"] = candidate
    page = PAGES[resource]
    form = page["form"](request.POST if request.method == "POST" else None, workspace=workspace, instance=record, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            saved = page["service"](workspace=workspace, data=form.cleaned_data, instance=record)
        except ValidationError as error:
            add_form_error(form, error)
        else:
            label = "nguồn lực" if resource == "resource" else page["label"]
            messages.success(request, f"Đã {'cập nhật' if record else 'tạo'} {label}.")
            return saved_response(request, reverse(context["detail_url_name"], args=[saved.pk]))
    if form.is_bound:
        form.mark_errors()
    context.update(form=form, record=record, page_title=f"{'Chỉnh sửa' if record else 'Thêm'} {page['label']}",
        primary_action_url=None, cancel_url=reverse(context["detail_url_name"], args=[record.pk]) if record else context["list_url"],
        form_notice="Khi thay đổi đơn giá từ một thời điểm mới, hãy thêm bản ghi mới để giữ lịch sử. Chỉnh sửa chỉ dùng để điều chỉnh bản ghi hiện tại." if resource == "resource_rate" else None)
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def work_center_list(request):
    return _list(request, "work_center")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def work_center_detail(request, pk):
    return _detail(request, "work_center", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def work_center_create(request):
    return _form(request, "work_center")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def work_center_edit(request, pk):
    return _form(request, "work_center", pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def resource_list(request):
    return _list(request, "resource")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def resource_detail(request, pk):
    return _detail(request, "resource", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def resource_create(request):
    return _form(request, "resource")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def resource_edit(request, pk):
    return _form(request, "resource", pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def resource_rate_list(request):
    return _list(request, "resource_rate")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def resource_rate_detail(request, pk):
    return _detail(request, "resource_rate", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def resource_rate_create(request):
    return _form(request, "resource_rate")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def resource_rate_edit(request, pk):
    return _form(request, "resource_rate", pk)
