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
from . import packaging_selectors as selectors, packaging_services as services
from .constants import DATE_STATUSES, EDITABLE_STATUSES, VERSION_STATUSES
from .packaging_forms import PackagingConfigForm, PackagingLineForm, PackagingVersionForm, PackagingAssignmentForm
from .definition_helpers import table_context as _table_context


def _context(request, *, config=None, **extra):
    request.costing_resource_label = "cấu hình bao bì"
    breadcrumbs = (("Sản xuất", None), ("Cấu hình bao bì", reverse("bom:packaging_list")))
    if config:
        breadcrumbs += ((config.code, reverse("bom:packaging_detail", args=[config.pk])),)
    return {"resource": "packaging", "resource_label": "cấu hình bao bì", "config": config,
        "page_title": "Cấu hình bao bì", "breadcrumbs": breadcrumbs,
        "page_description": "Quản lý thành phần bao bì theo sản phẩm, SKU sử dụng và phiên bản.", **extra}



@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_list(request):
    context = _context(request)
    workspace = require_access(request, resource="packaging")
    page, sort, per_page = selectors.config_list(organization=workspace.organization, filters=request.GET)
    columns = (("code", "Mã", False), ("name", "Tên cấu hình", False), (None, "Sản phẩm", False), (None, "Liên kết SKU", True),
        ("version", "Phiên bản mới nhất", True), (None, "Trạng thái phiên bản", False), ("effective_from", "Hiệu lực từ ngày", False), (None, "Trạng thái cấu hình", False))
    filters = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")}
        for name, label, choices in selectors.filter_options(organization=workspace.organization))
    context.update(_table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("bom:packaging_list"), columns=columns,
        rows_template="bom/packaging/partials/config_rows.html", sort_labels=(("code", "Mã"), ("name", "Tên"), ("version", "Phiên bản mới nhất"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filter_options=filters, filters=request.GET, search_placeholder="Tìm mã, tên cấu hình bao bì, sản phẩm hoặc SKU…",
        has_filters=any(request.GET.get(name) for name in ("q", *(entry["name"] for entry in filters))),
        can_edit=workspace.permissions.can_edit_packaging, detail_url_name="bom:packaging_detail", edit_url_name="bom:packaging_edit",
        primary_action_url=reverse("bom:packaging_create"), primary_action_label="+ Thêm cấu hình bao bì"))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _version_context(request, config, version, workspace):
    detail_url = reverse("bom:packaging_version_detail", args=[config.pk, version.pk])
    editable = version.status in EDITABLE_STATUSES
    return _context(request, config=config, version=version, version_url=detail_url, editable=editable,
        page_title=f"{config.name} · Phiên bản {version.version_no}", primary_action_url=(
            reverse("bom:packaging_version_edit", args=[config.pk, version.pk]) if editable
            else reverse("bom:packaging_version_create", args=[config.pk]) + f"?source={version.pk}"),
        primary_action_label="Chỉnh sửa phiên bản" if editable else "+ Tạo phiên bản mới")


def _lines_context(request, config, version, workspace):
    page, sort, per_page = selectors.line_list(version=version, organization=workspace.organization, filters=request.GET)
    version_url = reverse("bom:packaging_version_detail", args=[config.pk, version.pk])
    return {"config": config, "version": version, "page_obj": page, "lines": page.object_list, "per_page": per_page,
        "page_sizes": PAGE_SIZES, "list_url": version_url, "query_base_url": version_url,
        "table_id": "packaging-lines-table", "filter_form_id": "packaging-lines-table",
        "editable": version.status in EDITABLE_STATUSES,
        "line_create_url": reverse("bom:packaging_line_create", args=[config.pk, version.pk]),
    }


def _detail(request, pk, version_pk=None):
    context = _context(request)
    workspace = require_access(request, resource="packaging")
    config = selectors.config_detail(organization=workspace.organization, pk=pk)
    version = (selectors.version_detail(config=config, pk=version_pk) if version_pk is not None else
        selectors.version_queryset(config=config).order_by("-version_no", "-pk").first())
    context = _version_context(request, config, version, workspace) if version else _context(request, config=config,
        page_title=config.name, primary_action_url=reverse("bom:packaging_version_create", args=[config.pk]), primary_action_label="+ Tạo phiên bản mới")
    if version:
        context.update(_lines_context(request, config, version, workspace))
    assignments = selectors.assignment_queryset(config=config, organization=workspace.organization)
    context.update(assignment_count=assignments.count(), assignments=assignments.order_by("-effective_from", "pk")[:5])
    return render(request, "bom/packaging/partials/detail_content.html" if is_htmx(request) else "bom/packaging/detail.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_detail(request, pk):
    return _detail(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_version_detail(request, pk, version_pk):
    if request.headers.get("HX-Target") == "packaging-lines-table" and is_htmx(request):
        _context(request)
        workspace = require_access(request, resource="packaging")
        config = selectors.config_detail(organization=workspace.organization, pk=pk)
        version = selectors.version_detail(config=config, pk=version_pk)
        return render(request, "bom/packaging/partials/lines_table.html", _lines_context(request, config, version, workspace))
    return _detail(request, pk, version_pk)


def _config_form(request, pk=None):
    context = _context(request)
    workspace = require_access(request, "edit" if pk is not None else "create", resource="packaging")
    config = selectors.config_detail(organization=workspace.organization, pk=pk) if pk is not None else None
    data = request.POST if request.method == "POST" else None
    form = PackagingConfigForm(data, workspace=workspace, instance=config)
    version_form = PackagingVersionForm(data, workspace=workspace, prefix="initial") if config is None else None
    if request.method == "POST":
        valid = form.is_valid()
        version_valid = version_form.is_valid() if version_form else True
        if valid and version_valid:
            try:
                saved = services.save_config(workspace=workspace, data=form.cleaned_data, instance=config,
                    initial_version=version_form.cleaned_data if version_form else None)
            except ValidationError as error:
                # Persistence errors can belong to either part of the atomic form.
                if hasattr(error, "message_dict"):
                    for field, errors in error.message_dict.items():
                        target = version_form if version_form and field in version_form.fields else form
                        add_form_error(target, ValidationError({field: errors}))
                else:
                    add_form_error(form, error)
            else:
                messages.success(request, "Đã cập nhật cấu hình bao bì." if config else "Đã tạo cấu hình bao bì.")
                return saved_response(request, reverse("bom:packaging_detail", args=[saved.pk]))
        form.mark_errors()
        if version_form:
            version_form.mark_errors()
    context = _context(request, config=config, record=config, form=form, version_form=version_form,
        page_title="Chỉnh sửa cấu hình bao bì" if config else "Thêm cấu hình bao bì", cancel_url=reverse("bom:packaging_detail", args=[config.pk]) if config else reverse("bom:packaging_list"))
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_create(request):
    return _config_form(request)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_edit(request, pk):
    return _config_form(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_version_list(request, pk):
    _context(request)
    workspace = require_access(request, resource="packaging")
    config = selectors.config_detail(organization=workspace.organization, pk=pk)
    page, sort, per_page = selectors.version_list(config=config, filters=request.GET)
    columns = (("version", "Phiên bản", True), (None, "Khối lượng tổng", True), (None, "Trạng thái bản ghi", False),
        ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False))
    context = _context(request, config=config, page_title=f"Phiên bản · {config.code}", primary_action_url=reverse("bom:packaging_version_create", args=[pk]), primary_action_label="+ Tạo phiên bản mới")
    context.update(_table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("bom:packaging_version_list", args=[pk]),
        columns=columns, rows_template="bom/packaging/partials/version_rows.html", sort_labels=(("version", "Phiên bản"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filters=request.GET, has_filters=any(request.GET.get(name) for name in ("status", "effective")),
        filter_options=tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")}
            for name, label, choices in (("status", "Trạng thái", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES)))))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "bom/version_list.html", context)


def _version_form(request, pk, version_pk=None):
    _context(request)
    workspace = require_access(request, "edit" if version_pk is not None else "create", resource="packaging_version")
    config = selectors.config_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(config=config, pk=version_pk) if version_pk is not None else None
    source = None
    if version is None and request.GET.get("source"):
        try:
            source_id = int(request.GET["source"])
        except ValueError:
            raise Http404 from None
        source = selectors.version_detail(config=config, pk=source_id)
    kwargs = {"instance": version} if version else {"source": source}
    form = PackagingVersionForm(request.POST if request.method == "POST" else None, workspace=workspace, **kwargs)
    if request.method == "POST" and form.is_valid():
        try:
            saved = (services.update_version(workspace=workspace, config=config, instance=version, data=form.cleaned_data)
                if version else services.create_version(workspace=workspace, config=config, data=form.cleaned_data, source=source))
        except ValidationError as error:
            add_form_error(form, error)
            if version:
                current_status = selectors.version_queryset(config=config).filter(pk=version.pk).values_list("status", flat=True).first()
                if current_status is None:
                    raise Http404 from None
                version.status = current_status
        else:
            messages.success(request, "Đã cập nhật phiên bản bao bì." if version else "Đã tạo phiên bản bao bì mới.")
            return saved_response(request, reverse("bom:packaging_version_detail", args=[config.pk, saved.pk]))
    readonly = version is not None and version.status not in EDITABLE_STATUSES
    if readonly:
        for field in form.fields.values():
            field.widget.attrs["disabled"] = True
    if form.is_bound:
        form.mark_errors()
    context = _context(request, config=config, form=form, resource_label="phiên bản bao bì", form_readonly=readonly,
        form_action=request.get_full_path(), page_title="Chỉnh sửa phiên bản" if version else "Tạo phiên bản bao bì mới",
        cancel_url=reverse("bom:packaging_version_detail", args=[config.pk, version.pk]) if version else reverse("bom:packaging_detail", args=[config.pk]),
        form_notice=("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới." if readonly else
            f"Sao chép cấu hình và thành phần từ phiên bản {source.version_no}; phiên bản cũ được giữ nguyên. Phiên bản mới ở trạng thái Nháp." if source else "Phiên bản mới ở trạng thái Nháp."))
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_version_create(request, pk):
    return _version_form(request, pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_version_edit(request, pk, version_pk):
    return _version_form(request, pk, version_pk)


def _line_result(request, config, version, workspace):
    context = _lines_context(request, config, version, workspace)
    response = render(request, "bom/packaging/partials/line_saved.html", context)
    response["HX-Retarget"] = "#packaging-lines-table"
    response["HX-Reswap"] = "outerHTML"
    return response


def _line_form(request, pk, version_pk, line_pk=None, removing=False):
    _context(request)
    workspace = require_access(request, "edit" if line_pk is not None else "create", resource="packaging_line")
    config = selectors.config_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(config=config, pk=version_pk)
    line = selectors.line_detail(version=version, organization=workspace.organization, pk=line_pk) if line_pk is not None else None
    form = PackagingLineForm(request.POST if request.method == "POST" else None, workspace=workspace, version=version, instance=line)
    error = None
    if request.method == "POST" and (removing or form.is_valid()):
        try:
            if removing:
                services.remove_line(workspace=workspace, config=config, version=version, instance=line)
            else:
                services.save_line(workspace=workspace, config=config, version=version, data=form.cleaned_data, instance=line)
        except ValidationError as exception:
            if removing:
                error = " ".join(exception.messages)
            else:
                add_form_error(form, exception)
            current_status = selectors.version_queryset(config=config).filter(pk=version.pk).values_list("status", flat=True).first()
            if current_status is None:
                raise Http404 from None
            version.status = current_status
        else:
            messages.success(request, "Đã xóa thành phần bao bì." if removing else "Đã cập nhật thành phần bao bì." if line else "Đã thêm thành phần bao bì.")
            if is_htmx(request):
                return _line_result(request, config, version, workspace)
            return saved_response(request, reverse("bom:packaging_version_detail", args=[config.pk, version.pk]))
    editable = version.status in EDITABLE_STATUSES
    if not editable:
        error = "Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới."
    if form.is_bound:
        form.mark_errors()
    context = _version_context(request, config, version, workspace)
    context.update(form=form, line=line, removing=removing, line_error=error, editable=editable,
        inline_editor=is_htmx(request),
        resource_label="thành phần bao bì", form_action=request.get_full_path(),
        editor_title="Xóa thành phần bao bì" if removing else "Chỉnh sửa thành phần bao bì" if line else "Thêm thành phần bao bì")
    return render(request, "bom/packaging/partials/line_editor.html" if is_htmx(request) else "bom/packaging/line_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_line_create(request, pk, version_pk):
    return _line_form(request, pk, version_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_line_edit(request, pk, version_pk, line_pk):
    return _line_form(request, pk, version_pk, line_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_line_remove(request, pk, version_pk, line_pk):
    return _line_form(request, pk, version_pk, line_pk, removing=True)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_assignment_list(request, pk):
    _context(request)
    workspace = require_access(request, resource="packaging_assignment")
    config = selectors.config_detail(organization=workspace.organization, pk=pk)
    page, sort, per_page = selectors.assignment_list(config=config, organization=workspace.organization, filters=request.GET)
    context = _context(request, config=config, resource_label="liên kết SKU", page_title=f"SKU sử dụng · {config.code}")
    context.update(_table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("bom:packaging_assignment_list", args=[pk]),
        columns=(("sku", "SKU", False), (None, "Cấu hình chính", False), ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False)),
        rows_template="bom/packaging/partials/assignment_rows.html", sort_labels=(("sku", "SKU"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filters=request.GET, filter_options=({"name": "effective", "label": "Hiệu lực theo ngày", "choices": DATE_STATUSES, "selected": request.GET.get("effective", "")},),
        search_placeholder="Tìm mã hoặc tên SKU…", has_filters=any(request.GET.get(name) for name in ("q", "effective")),
        primary_action_url=reverse("bom:packaging_assignment_create", args=[pk]), primary_action_label="+ Gán SKU"))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _assignment_form(request, pk, assignment_pk=None):
    _context(request)
    workspace = require_access(request, "edit" if assignment_pk is not None else "create", resource="packaging_assignment")
    config = selectors.config_detail(organization=workspace.organization, pk=pk)
    assignment = selectors.assignment_detail(config=config, organization=workspace.organization, pk=assignment_pk) if assignment_pk is not None else None
    form = PackagingAssignmentForm(request.POST if request.method == "POST" else None, workspace=workspace, config=config, instance=assignment)
    if request.method == "POST" and form.is_valid():
        try:
            services.save_assignment(workspace=workspace, config=config, data=form.cleaned_data, instance=assignment)
        except ValidationError as error:
            add_form_error(form, error)
        else:
            messages.success(request, "Đã cập nhật liên kết SKU." if assignment else "Đã gán SKU cho cấu hình bao bì.")
            return saved_response(request, reverse("bom:packaging_detail", args=[config.pk]))
    if form.is_bound:
        form.mark_errors()
    context = _context(request, config=config, form=form, resource_label="liên kết SKU", page_title="Chỉnh sửa liên kết SKU" if assignment else "Gán SKU cho cấu hình bao bì",
        cancel_url=reverse("bom:packaging_detail", args=[pk]), form_notice="Chọn SKU của cùng sản phẩm. Ngày áp dụng cho liên kết SKU, độc lập với ngày hiệu lực từng phiên bản bao bì.")
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_assignment_create(request, pk):
    return _assignment_form(request, pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def packaging_assignment_edit(request, pk, assignment_pk):
    return _assignment_form(request, pk, assignment_pk)
