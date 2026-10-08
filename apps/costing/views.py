"""HTTP orchestration for configuration only."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.decorators.vary import vary_on_headers
from apps.master_data.access import require_access
from apps.master_data.constants import PAGE_SIZES
from apps.master_data.ui_helpers import add_form_error, is_htmx, saved_response
from apps.bom.definition_helpers import table_context
from . import selectors, services
from .configuration import validate_costing_scheme
from .constants import EDITABLE_STATUSES, VERSION_STATUSES, DATE_STATUSES
from .forms import SchemeForm, SchemeVersionForm, SchemeLineForm


def _context(request, scheme=None, **extra):
    request.costing_resource_label = "phương án tính giá thành"
    breadcrumbs = (("Công thức & Quy tắc", None), ("Phương án tính giá thành", reverse("costing:scheme_list")))
    if scheme: breadcrumbs += ((scheme.code, reverse("costing:scheme_detail", args=[scheme.pk])),)
    return {"resource": "scheme", "resource_label": "phương án tính giá thành", "scheme": scheme,
        "page_title": "Phương án tính giá thành", "breadcrumbs": breadcrumbs,
        "page_description": "Quản lý nguồn dữ liệu, phần tử chi phí và công thức theo phiên bản.", **extra}


def _resolve(request, pk, version_pk=None):
    _context(request)
    workspace = require_access(request, resource="scheme")
    scheme = selectors.scheme_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(scheme=scheme, pk=version_pk) if version_pk is not None else selectors.version_queryset(scheme=scheme).order_by("-version_no", "-pk").first()
    return workspace, scheme, version


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_list(request):
    context = _context(request)
    workspace = require_access(request, resource="scheme")
    page, sort, per_page = selectors.scheme_list(organization=workspace.organization, filters=request.GET)
    options = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")} for name, label, choices in selectors.filter_options(organization=workspace.organization))
    context.update(table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("costing:scheme_list"),
        columns=(("code", "Mã", False), ("name", "Tên phương án", False), (None, "Mục đích", False), (None, "Phạm vi áp dụng", False),
            ("version", "Phiên bản mới nhất", True), (None, "Trạng thái phiên bản", False), ("effective_from", "Hiệu lực từ ngày", False),
            (None, "Hiệu lực theo ngày", False), (None, "Trạng thái phương án", False)),
        rows_template="costing/partials/scheme_rows.html", sort_labels=(("code", "Mã"), ("name", "Tên"), ("version", "Phiên bản"), ("effective_from", "Hiệu lực từ ngày"), ("updated_at", "Ngày cập nhật")),
        filter_options=options, filters=request.GET, has_filters=any(request.GET.get(name) for name in ("q", *(option["name"] for option in options))),
        search_placeholder="Tìm mã, tên, mô tả hoặc mục đích phương án…", can_edit=workspace.permissions.can_edit_scheme,
        detail_url_name="costing:scheme_detail", edit_url_name="costing:scheme_edit",
        primary_action_url=reverse("costing:scheme_create") if workspace.permissions.can_create_scheme else None, primary_action_label="+ Thêm phương án"))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _lines_context(request, scheme, version, workspace):
    page, sort, per_page = selectors.line_list(version=version, filters=request.GET)
    url = reverse("costing:scheme_version_detail", args=[scheme.pk, version.pk])
    return {"scheme": scheme, "version": version, "page_obj": page, "lines": page.object_list,
        "per_page": per_page, "page_sizes": PAGE_SIZES, "list_url": url, "query_base_url": url,
        "table_id": "scheme-lines-table", "filter_form_id": "scheme-lines-table",
        "editable": version.status in EDITABLE_STATUSES,
        "line_create_url": reverse("costing:scheme_line_create", args=[scheme.pk, version.pk])}


def _detail(request, pk, version_pk=None):
    workspace, scheme, version = _resolve(request, pk, version_pk)
    context = _context(request, scheme, version=version)
    if version:
        context.update(_lines_context(request, scheme, version, workspace))
        context.update(version_url=reverse("costing:scheme_version_detail", args=[pk, version.pk]),
            validate_url=reverse("costing:scheme_version_validate", args=[pk, version.pk]),
            activate_url=reverse("costing:scheme_version_activate", args=[pk, version.pk]),
            page_title=f"{scheme.name} · Phiên bản {version.version_no}")
        if is_htmx(request) and request.headers.get("HX-Target") == "scheme-lines-table":
            return render(request, "costing/partials/lines_table.html", context)
    return render(request, "costing/partials/detail_content.html" if is_htmx(request) else "costing/detail.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def scheme_detail(request, pk): return _detail(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def scheme_version_detail(request, pk, version_pk): return _detail(request, pk, version_pk)


def _header_form(request, pk=None):
    _context(request)
    workspace = require_access(request, "edit" if pk is not None else "create", resource="scheme")
    scheme = selectors.scheme_detail(organization=workspace.organization, pk=pk) if pk is not None else None
    data = request.POST if request.method == "POST" else None
    form = SchemeForm(data, workspace=workspace, instance=scheme)
    version_form = SchemeVersionForm(data, workspace=workspace, prefix="initial") if scheme is None else None
    if request.method == "POST":
        valid = form.is_valid()
        version_valid = version_form.is_valid() if version_form else True
        if valid and version_valid:
            try: saved = services.save_scheme(workspace=workspace, data=form.cleaned_data, instance=scheme, initial_version=version_form.cleaned_data if version_form else None)
            except ValidationError as error: add_form_error(form, error)
            else:
                messages.success(request, "Đã cập nhật phương án tính giá thành." if scheme else "Đã tạo phương án tính giá thành.")
                return saved_response(request, reverse("costing:scheme_detail", args=[saved.pk]))
        form.mark_errors()
        if version_form: version_form.mark_errors()
    context = _context(request, scheme, record=scheme, form=form, version_form=version_form,
        page_title="Chỉnh sửa phương án tính giá thành" if scheme else "Thêm phương án tính giá thành",
        cancel_url=reverse("costing:scheme_detail", args=[pk]) if scheme else reverse("costing:scheme_list"))
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_create(request): return _header_form(request)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_edit(request, pk): return _header_form(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_version_list(request, pk):
    workspace, scheme, _ = _resolve(request, pk)
    page, sort, per_page = selectors.version_list(scheme=scheme, filters=request.GET)
    context = _context(request, scheme, page_title=f"Phiên bản · {scheme.code}")
    context.update(table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("costing:scheme_version_list", args=[pk]),
        columns=(("version", "Phiên bản", True), (None, "Số dòng", True), (None, "Trạng thái", False), ("effective_from", "Hiệu lực từ ngày", False),
            (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False)),
        rows_template="costing/partials/version_rows.html", sort_labels=(("version", "Phiên bản"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filters=request.GET, has_filters=any(request.GET.get(name) for name in ("status", "effective")),
        filter_options=tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")} for name, label, choices in (("status", "Trạng thái", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES))),
        primary_action_url=reverse("costing:scheme_version_create", args=[pk]), primary_action_label="+ Tạo phiên bản mới"))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "bom/version_list.html", context)


def _version_form(request, pk, version_pk=None):
    workspace, scheme, selected = _resolve(request, pk, version_pk)
    require_access(request, "edit" if version_pk is not None else "create", resource="scheme_version")
    version = selected if version_pk is not None else None
    source = None
    if not version and request.GET.get("source"):
        source_pk = request.GET["source"]
        source = selectors.version_detail(scheme=scheme, pk=int(source_pk) if source_pk.isascii() and source_pk.isdecimal() and len(source_pk) <= 19 else None)
    form = SchemeVersionForm(request.POST if request.method == "POST" else None, workspace=workspace, instance=version, source=source)
    if request.method == "POST" and form.is_valid():
        try: saved = services.save_version(workspace=workspace, scheme=scheme, instance=version, source=source, data=form.cleaned_data)
        except ValidationError as error:
            add_form_error(form, error)
            if version: version = selectors.version_detail(scheme=scheme, pk=version.pk)
        else:
            messages.success(request, "Đã cập nhật phiên bản phương án." if version else "Đã tạo phiên bản phương án mới.")
            return saved_response(request, reverse("costing:scheme_version_detail", args=[pk, saved.pk]))
    readonly = version is not None and version.status not in EDITABLE_STATUSES
    if readonly:
        for field in form.fields.values(): field.widget.attrs["disabled"] = True
    if form.is_bound: form.mark_errors()
    context = _context(request, scheme, form=form, form_readonly=readonly, resource_label="phiên bản phương án",
        page_title="Chỉnh sửa phiên bản phương án" if version else "Tạo phiên bản phương án mới", form_action=request.get_full_path(),
        cancel_url=reverse("costing:scheme_version_detail", args=[pk, version.pk]) if version else reverse("costing:scheme_detail", args=[pk]),
        form_notice="Phiên bản đã được chốt. Vui lòng tạo phiên bản mới." if readonly else
            f"Sao chép toàn bộ dòng cấu hình từ phiên bản {source.version_no}; bản mới ở trạng thái Nháp." if source else "Phiên bản mới ở trạng thái Nháp.")
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_version_create(request, pk): return _version_form(request, pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_version_edit(request, pk, version_pk): return _version_form(request, pk, version_pk)


def _line_form(request, pk, version_pk, line_pk=None, removing=False):
    workspace, scheme, version = _resolve(request, pk, version_pk)
    require_access(request, "edit" if line_pk is not None else "create", resource="scheme_line")
    line = selectors.line_detail(version=version, pk=line_pk) if line_pk is not None else None
    url = reverse("costing:scheme_line_sources", args=[pk, version_pk]) + (f"?line={line.pk}" if line else "")
    form = SchemeLineForm(request.POST if request.method == "POST" else None, workspace=workspace, version=version, instance=line, options_url=url)
    error = None
    if request.method == "POST" and (removing or form.is_valid()):
        try:
            if removing: services.remove_line(workspace=workspace, scheme=scheme, version=version, instance=line)
            else: services.save_line(workspace=workspace, scheme=scheme, version=version, data=form.cleaned_data, instance=line)
        except ValidationError as exception:
            if removing: error = " ".join(exception.messages)
            else: add_form_error(form, exception)
            version = selectors.version_detail(scheme=scheme, pk=version_pk)
        else:
            messages.success(request, "Đã xóa thành phần tính giá." if removing else "Đã cập nhật thành phần tính giá." if line else "Đã thêm thành phần tính giá.")
            if is_htmx(request):
                response = render(request, "costing/partials/line_saved.html", _lines_context(request, scheme, version, workspace))
                response["HX-Retarget"] = "#scheme-lines-table"; response["HX-Reswap"] = "outerHTML"
                return response
            return saved_response(request, reverse("costing:scheme_version_detail", args=[pk, version_pk]))
    editable = version.status in EDITABLE_STATUSES
    if not editable:
        error = "Phiên bản đã được chốt. Vui lòng tạo phiên bản mới."
        for field in form.fields.values(): field.widget.attrs["disabled"] = True
    if form.is_bound: form.mark_errors()
    context = _context(request, scheme, version=version, line=line, form=form, removing=removing, line_error=error,
        inline_editor=is_htmx(request), editable=editable, form_action=request.get_full_path(), resource_label="thành phần tính giá",
        editor_title="Xóa thành phần tính giá" if removing else "Chỉnh sửa thành phần tính giá" if line else "Thêm thành phần tính giá",
        version_url=reverse("costing:scheme_version_detail", args=[pk, version_pk]))
    return render(request, "costing/partials/line_editor.html" if is_htmx(request) else "costing/line_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_line_create(request, pk, version_pk): return _line_form(request, pk, version_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_line_edit(request, pk, version_pk, line_pk): return _line_form(request, pk, version_pk, line_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_line_remove(request, pk, version_pk, line_pk): return _line_form(request, pk, version_pk, line_pk, removing=True)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_line_sources(request, pk, version_pk):
    workspace, scheme, version = _resolve(request, pk, version_pk)
    line = None
    if request.GET.get("line"):
        value = request.GET["line"]
        line = selectors.line_detail(version=version, pk=int(value) if value.isascii() and value.isdecimal() and len(value) <= 19 else None)
    form = SchemeLineForm(request.GET, workspace=workspace, version=version, instance=line)
    if not is_htmx(request): return saved_response(request, reverse("costing:scheme_version_detail", args=[pk, version_pk]))
    return render(request, "costing/partials/source_fields.html", {"form": form})


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def scheme_version_validate(request, pk, version_pk):
    workspace, scheme, version = _resolve(request, pk, version_pk)
    report = validate_costing_scheme(organization=workspace.organization, scheme=scheme, version=version)
    context = _context(request, scheme, version=version, report=report, version_url=reverse("costing:scheme_version_detail", args=[pk, version_pk]))
    return render(request, "costing/partials/validation.html" if is_htmx(request) else "costing/validation.html", context)


@require_POST
def scheme_version_activate(request, pk, version_pk):
    workspace, scheme, version = _resolve(request, pk, version_pk)
    try: services.activate_version(workspace=workspace, scheme=scheme, version=version)
    except ValidationError as error:
        context = _context(request, scheme, version=version, activation_errors=error.messages,
            report=validate_costing_scheme(organization=workspace.organization, scheme=scheme, version=version),
            version_url=reverse("costing:scheme_version_detail", args=[pk, version_pk]))
        return render(request, "costing/partials/validation.html" if is_htmx(request) else "costing/validation.html", context)
    messages.success(request, "Đã kích hoạt phiên bản phương án. Cấu hình phiên bản đã được khóa.")
    return saved_response(request, reverse("costing:scheme_version_detail", args=[pk, version_pk]))
