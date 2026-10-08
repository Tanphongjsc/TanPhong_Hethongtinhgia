from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers

from apps.master_data.access import require_access
from apps.master_data.constants import PAGE_SIZES
from apps.master_data.ui_helpers import add_form_error, is_htmx, saved_response
from . import routing_selectors as selectors, routing_services as services
from .definition_helpers import table_context
from .routing_constants import DATE_STATUSES, EDITABLE_STATUSES, VERSION_STATUSES
from .routing_forms import RoutingForm, RoutingOperationForm, RoutingVersionForm


def _context(request, *, routing=None, **extra):
    request.costing_resource_label = "quy trình sản xuất"
    breadcrumbs = (("Sản xuất", None), ("Quy trình sản xuất", reverse("bom:routing_list")))
    if routing:
        breadcrumbs += ((routing.code, reverse("bom:routing_detail", args=[routing.pk])),)
    return {"resource": "routing", "resource_label": "quy trình sản xuất", "routing": routing,
        "page_title": "Quy trình sản xuất", "breadcrumbs": breadcrumbs,
        "page_description": "Quản lý thứ tự công đoạn, thời gian sử dụng nguồn lực và phiên bản theo sản phẩm.", **extra}


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_list(request):
    context = _context(request)
    workspace = require_access(request, resource="routing")
    page, sort, per_page = selectors.routing_list(organization=workspace.organization, filters=request.GET)
    options = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, request.GET.get("is_active", "") if name == "active" else "")}
        for name, label, choices in selectors.filter_options(organization=workspace.organization))
    context.update(table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("bom:routing_list"),
        columns=(("code", "Mã", False), ("name", "Tên quy trình", False), (None, "Sản phẩm", False), ("version", "Phiên bản mới nhất", True),
            (None, "Số công đoạn", True), (None, "Trạng thái phiên bản", False), ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực theo ngày", False), (None, "Trạng thái quy trình", False)),
        rows_template="bom/routing/partials/routing_rows.html", sort_labels=(("code", "Mã"), ("name", "Tên"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filter_options=options, filters=request.GET, search_placeholder="Tìm mã, tên quy trình, sản phẩm hoặc SKU…",
        has_filters=any(request.GET.get(name) for name in ("q", "is_active", *(option["name"] for option in options))),
        can_edit=workspace.permissions.can_edit_routing, detail_url_name="bom:routing_detail", edit_url_name="bom:routing_edit",
        primary_action_url=reverse("bom:routing_create") if workspace.permissions.can_create_routing else None, primary_action_label="+ Thêm quy trình"))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _version_context(request, routing, version, workspace):
    editable = version.status in EDITABLE_STATUSES
    action = "routing_version_edit" if editable else "routing_version_create"
    args = [routing.pk, version.pk] if editable else [routing.pk]
    primary_url = reverse(f"bom:{action}", args=args)
    if not editable:
        primary_url += f"?source={version.pk}"
    can_act = workspace.permissions.can_edit_routing_version if editable else workspace.permissions.can_create_routing_version
    return _context(request, routing=routing, version=version,
        version_url=reverse("bom:routing_version_detail", args=[routing.pk, version.pk]),
        editable=editable, page_title=f"{routing.name} · Phiên bản {version.version_no}",
        primary_action_url=primary_url if can_act else None, primary_action_label="Chỉnh sửa phiên bản" if editable else "+ Tạo phiên bản mới")


def _operations_context(request, routing, version, workspace):
    page, sort, per_page = selectors.operation_list(version=version, organization=workspace.organization, filters=request.GET)
    version_url = reverse("bom:routing_version_detail", args=[routing.pk, version.pk])
    return {"routing": routing, "version": version, "page_obj": page, "operations": page.object_list,
        "per_page": per_page, "page_sizes": PAGE_SIZES, "list_url": version_url, "query_base_url": version_url,
        "table_id": "routing-operations-table", "filter_form_id": "routing-operations-table",
        "editable": version.status in EDITABLE_STATUSES,
        "can_add_operation": workspace.permissions.can_create_routing_operation,
        "can_edit_operation": workspace.permissions.can_edit_routing_operation,
        "can_remove_operation": workspace.permissions.can_delete_routing_operation,
        "operation_create_url": reverse("bom:routing_operation_create", args=[routing.pk, version.pk])}


def _detail(request, pk, version_pk=None):
    _context(request)
    workspace = require_access(request, resource="routing")
    routing = selectors.routing_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(routing=routing, pk=version_pk) if version_pk is not None else selectors.version_queryset(routing=routing).order_by("-version_no", "-pk").first()
    context = _version_context(request, routing, version, workspace) if version else _context(request, routing=routing, page_title=routing.name,
        primary_action_url=reverse("bom:routing_version_create", args=[pk]) if workspace.permissions.can_create_routing_version else None, primary_action_label="+ Tạo phiên bản mới")
    if version:
        context.update(_operations_context(request, routing, version, workspace))
        if is_htmx(request) and request.headers.get("HX-Target") == "routing-operations-table":
            return render(request, "bom/routing/partials/operations_table.html", context)
    return render(request, "bom/routing/partials/detail_content.html" if is_htmx(request) else "bom/routing/detail.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def routing_detail(request, pk):
    return _detail(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def routing_version_detail(request, pk, version_pk):
    return _detail(request, pk, version_pk)


def _routing_form(request, pk=None):
    _context(request)
    workspace = require_access(request, "edit" if pk is not None else "create", resource="routing")
    routing = selectors.routing_detail(organization=workspace.organization, pk=pk) if pk is not None else None
    data = request.POST if request.method == "POST" else None
    form = RoutingForm(data, workspace=workspace, instance=routing)
    version_form = RoutingVersionForm(data, workspace=workspace, prefix="initial") if routing is None else None
    if request.method == "POST":
        valid = form.is_valid()
        version_valid = version_form.is_valid() if version_form else True
        if valid and version_valid:
            try:
                saved = services.save_routing(workspace=workspace, data=form.cleaned_data, instance=routing, initial_version=version_form.cleaned_data if version_form else None)
            except ValidationError as error:
                if hasattr(error, "message_dict"):
                    for field, errors in error.message_dict.items():
                        target = version_form if version_form and field in version_form.fields else form
                        add_form_error(target, ValidationError({field: errors}))
                else:
                    add_form_error(form, error)
            else:
                messages.success(request, "Đã cập nhật quy trình sản xuất." if routing else "Đã tạo quy trình sản xuất.")
                return saved_response(request, reverse("bom:routing_detail", args=[saved.pk]))
        form.mark_errors()
        if version_form:
            version_form.mark_errors()
    context = _context(request, routing=routing, record=routing, form=form, version_form=version_form,
        page_title="Chỉnh sửa quy trình sản xuất" if routing else "Thêm quy trình sản xuất",
        cancel_url=reverse("bom:routing_detail", args=[pk]) if routing else reverse("bom:routing_list"))
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_create(request):
    return _routing_form(request)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_edit(request, pk):
    return _routing_form(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_version_list(request, pk):
    _context(request)
    workspace = require_access(request, resource="routing")
    routing = selectors.routing_detail(organization=workspace.organization, pk=pk)
    page, sort, per_page = selectors.version_list(routing=routing, filters=request.GET)
    context = _context(request, routing=routing, page_title=f"Phiên bản · {routing.code}")
    context.update(table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("bom:routing_version_list", args=[pk]),
        columns=(("version", "Phiên bản", True), (None, "Sản lượng lô chuẩn", True), (None, "Trạng thái bản ghi", False),
            ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False)),
        rows_template="bom/routing/partials/version_rows.html", sort_labels=(("version", "Phiên bản"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filters=request.GET, has_filters=any(request.GET.get(name) for name in ("status", "effective")),
        filter_options=tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")}
            for name, label, choices in (("status", "Trạng thái", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES))),
        primary_action_url=reverse("bom:routing_version_create", args=[pk]) if workspace.permissions.can_create_routing_version else None,
        primary_action_label="+ Tạo phiên bản mới"))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "bom/version_list.html", context)


def _version_form(request, pk, version_pk=None):
    _context(request)
    workspace = require_access(request, "edit" if version_pk is not None else "create", resource="routing_version")
    routing = selectors.routing_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(routing=routing, pk=version_pk) if version_pk is not None else None
    source = None
    if version is None and request.GET.get("source"):
        try:
            source_id = int(request.GET["source"])
        except ValueError:
            raise Http404 from None
        source = selectors.version_detail(routing=routing, pk=source_id)
    kwargs = {"instance": version} if version else {"source": source}
    form = RoutingVersionForm(request.POST if request.method == "POST" else None, workspace=workspace, **kwargs)
    if request.method == "POST" and form.is_valid():
        try:
            saved = services.update_version(workspace=workspace, routing=routing, instance=version, data=form.cleaned_data) if version else services.create_version(workspace=workspace, routing=routing, data=form.cleaned_data, source=source)
        except ValidationError as error:
            add_form_error(form, error)
            if version:
                version = selectors.version_detail(routing=routing, pk=version.pk)
        else:
            messages.success(request, "Đã cập nhật phiên bản quy trình." if version else "Đã tạo phiên bản quy trình mới.")
            return saved_response(request, reverse("bom:routing_version_detail", args=[routing.pk, saved.pk]))
    readonly = version is not None and version.status not in EDITABLE_STATUSES
    if readonly:
        for field in form.fields.values():
            field.widget.attrs["disabled"] = True
    if form.is_bound:
        form.mark_errors()
    context = _context(request, routing=routing, form=form, resource_label="phiên bản quy trình", form_readonly=readonly,
        form_action=request.get_full_path(), page_title="Chỉnh sửa phiên bản" if version else "Tạo phiên bản quy trình mới",
        cancel_url=reverse("bom:routing_version_detail", args=[pk, version.pk]) if version else reverse("bom:routing_detail", args=[pk]),
        form_notice="Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới." if readonly else
            f"Sao chép cấu hình và công đoạn từ phiên bản {source.version_no}. Phiên bản cũ được giữ nguyên; phiên bản mới ở trạng thái Nháp." if source else "Phiên bản mới ở trạng thái Nháp.")
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_version_create(request, pk):
    return _version_form(request, pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_version_edit(request, pk, version_pk):
    return _version_form(request, pk, version_pk)


def _operation_form(request, pk, version_pk, operation_pk=None, removing=False):
    _context(request)
    workspace = require_access(request, "edit" if operation_pk is not None else "create", resource="routing_operation")
    routing = selectors.routing_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(routing=routing, pk=version_pk)
    operation = selectors.operation_detail(version=version, organization=workspace.organization, pk=operation_pk) if operation_pk is not None else None
    options_url = reverse("bom:routing_operation_resources", args=[pk, version_pk]) + (f"?operation={operation.pk}" if operation else "")
    form = RoutingOperationForm(request.POST if request.method == "POST" else None, workspace=workspace, version=version, instance=operation, resource_options_url=options_url)
    error = None
    if request.method == "POST" and (removing or form.is_valid()):
        try:
            if removing:
                services.remove_operation(workspace=workspace, routing=routing, version=version, instance=operation)
            else:
                services.save_operation(workspace=workspace, routing=routing, version=version, data=form.cleaned_data, instance=operation)
        except ValidationError as exception:
            if removing:
                error = " ".join(exception.messages)
            else:
                add_form_error(form, exception)
            version = selectors.version_detail(routing=routing, pk=version.pk)
        else:
            messages.success(request, "Đã xóa công đoạn." if removing else "Đã cập nhật công đoạn." if operation else "Đã thêm công đoạn.")
            if is_htmx(request):
                response = render(request, "bom/routing/partials/operation_saved.html", _operations_context(request, routing, version, workspace))
                response["HX-Retarget"] = "#routing-operations-table"
                response["HX-Reswap"] = "outerHTML"
                return response
            return saved_response(request, reverse("bom:routing_version_detail", args=[pk, version.pk]))
    editable = version.status in EDITABLE_STATUSES
    if not editable:
        error = "Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới."
        for field in form.fields.values():
            field.widget.attrs["disabled"] = True
    if form.is_bound:
        form.mark_errors()
    context = _version_context(request, routing, version, workspace)
    context.update(form=form, operation=operation, removing=removing, operation_error=error, editable=editable,
        inline_editor=is_htmx(request), resource_label="công đoạn", form_action=request.get_full_path(),
        editor_title="Xóa công đoạn" if removing else "Chỉnh sửa công đoạn" if operation else "Thêm công đoạn")
    return render(request, "bom/routing/partials/operation_editor.html" if is_htmx(request) else "bom/routing/operation_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_operation_create(request, pk, version_pk):
    return _operation_form(request, pk, version_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_operation_edit(request, pk, version_pk, operation_pk):
    return _operation_form(request, pk, version_pk, operation_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_operation_remove(request, pk, version_pk, operation_pk):
    return _operation_form(request, pk, version_pk, operation_pk, removing=True)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def routing_operation_resources(request, pk, version_pk):
    _context(request)
    workspace = require_access(request, resource="routing_operation")
    routing = selectors.routing_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(routing=routing, pk=version_pk)
    operation = None
    if request.GET.get("operation"):
        try:
            operation_pk = int(request.GET["operation"])
        except ValueError:
            raise Http404 from None
        operation = selectors.operation_detail(version=version, organization=workspace.organization, pk=operation_pk)
    if not is_htmx(request):
        return saved_response(request, reverse("bom:routing_version_detail", args=[pk, version_pk]))
    form = RoutingOperationForm(request.GET, workspace=workspace, version=version, instance=operation)
    return render(request, "bom/routing/partials/resource_field.html", {"field": form["primary_resource"]})
