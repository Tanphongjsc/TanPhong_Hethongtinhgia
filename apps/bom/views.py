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
from . import selectors, services
from .constants import DATE_STATUSES, EDITABLE_STATUSES, VERSION_STATUSES
from .forms import RecipeForm, RecipeLineForm, RecipeVersionForm
from .definition_helpers import table_context as _table_context


def _context(request, *, recipe=None, **extra):
    request.costing_resource_label = "định mức nguyên vật liệu"
    breadcrumbs = (("Sản xuất", None), ("Định mức nguyên vật liệu", reverse("bom:bom_list")))
    if recipe:
        breadcrumbs += ((recipe.code, reverse("bom:bom_detail", args=[recipe.pk])),)
    return {"resource": "bom", "resource_label": "định mức nguyên vật liệu", "recipe": recipe,
        "page_title": "Định mức nguyên vật liệu", "breadcrumbs": breadcrumbs,
        "page_description": "Quản lý công thức sản xuất theo sản phẩm, sản lượng chuẩn và phiên bản; chưa bao gồm tính giá.", **extra}


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_list(request):
    context = _context(request)
    workspace = require_access(request, resource="bom")
    page, sort, per_page = selectors.recipe_list(organization=workspace.organization, filters=request.GET)
    columns = (("code", "Mã", False), ("name", "Tên", False), (None, "Sản phẩm", False), ("version", "Phiên bản mới nhất", True),
        (None, "Sản lượng chuẩn", True), (None, "Đơn vị tính", False), (None, "Trạng thái phiên bản", False), ("effective_from", "Hiệu lực từ ngày", False), (None, "Trạng thái định mức", False))
    filters = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")}
        for name, label, choices in selectors.recipe_filter_options(organization=workspace.organization))
    context.update(_table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("bom:bom_list"), columns=columns,
        rows_template="bom/partials/recipe_rows.html", sort_labels=(("code", "Mã"), ("name", "Tên"), ("version", "Phiên bản mới nhất"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filter_options=filters, filters=request.GET, search_placeholder="Tìm mã, tên định mức, sản phẩm hoặc SKU…",
        has_filters=any(request.GET.get(name) for name in ("q", *(entry["name"] for entry in filters))),
        can_edit=workspace.permissions.can_edit_bom, detail_url_name="bom:bom_detail", edit_url_name="bom:bom_edit",
        primary_action_url=reverse("bom:bom_create"), primary_action_label="+ Thêm định mức"))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _version_context(request, recipe, version, workspace):
    detail_url = reverse("bom:bom_version_detail", args=[recipe.pk, version.pk])
    editable = version.status in EDITABLE_STATUSES
    return _context(request, recipe=recipe, version=version, version_url=detail_url, editable=editable,
        page_title=f"{recipe.name} · Phiên bản {version.version_no}", primary_action_url=(
            reverse("bom:bom_version_edit", args=[recipe.pk, version.pk]) if editable
            else reverse("bom:bom_version_create", args=[recipe.pk]) + f"?source={version.pk}"),
        primary_action_label="Chỉnh sửa phiên bản" if editable else "+ Tạo phiên bản mới")


def _lines_context(request, recipe, version, workspace):
    page, sort, per_page = selectors.line_list(version=version, organization=workspace.organization, filters=request.GET)
    version_url = reverse("bom:bom_version_detail", args=[recipe.pk, version.pk])
    return {"recipe": recipe, "version": version, "page_obj": page, "lines": page.object_list, "per_page": per_page,
        "page_sizes": PAGE_SIZES, "list_url": version_url, "query_base_url": version_url,
        "table_id": "bom-lines-table", "filter_form_id": "bom-lines-table",
        "editable": version.status in EDITABLE_STATUSES,
        "line_create_url": reverse("bom:bom_line_create", args=[recipe.pk, version.pk]),
    }


def _detail(request, pk, version_pk=None):
    context = _context(request)
    workspace = require_access(request, resource="bom")
    recipe = selectors.recipe_detail(organization=workspace.organization, pk=pk)
    version = (selectors.version_detail(recipe=recipe, pk=version_pk) if version_pk is not None else
        selectors.version_queryset(recipe=recipe).order_by("-version_no", "-pk").first())
    context = _version_context(request, recipe, version, workspace) if version else _context(request, recipe=recipe,
        page_title=recipe.name, primary_action_url=reverse("bom:bom_version_create", args=[recipe.pk]), primary_action_label="+ Tạo phiên bản mới")
    if version:
        context.update(_lines_context(request, recipe, version, workspace))
    return render(request, "bom/partials/detail_content.html" if is_htmx(request) else "bom/detail.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_detail(request, pk):
    return _detail(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_version_detail(request, pk, version_pk):
    if request.headers.get("HX-Target") == "bom-lines-table" and is_htmx(request):
        _context(request)
        workspace = require_access(request, resource="bom")
        recipe = selectors.recipe_detail(organization=workspace.organization, pk=pk)
        version = selectors.version_detail(recipe=recipe, pk=version_pk)
        return render(request, "bom/partials/lines_table.html", _lines_context(request, recipe, version, workspace))
    return _detail(request, pk, version_pk)


def _recipe_form(request, pk=None):
    context = _context(request)
    workspace = require_access(request, "edit" if pk is not None else "create", resource="bom")
    recipe = selectors.recipe_detail(organization=workspace.organization, pk=pk) if pk is not None else None
    data = request.POST if request.method == "POST" else None
    form = RecipeForm(data, workspace=workspace, instance=recipe)
    version_form = RecipeVersionForm(data, workspace=workspace, prefix="initial") if recipe is None else None
    if request.method == "POST":
        valid = form.is_valid()
        version_valid = version_form.is_valid() if version_form else True
        if valid and version_valid:
            try:
                saved = services.save_recipe(workspace=workspace, data=form.cleaned_data, instance=recipe,
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
                messages.success(request, "Đã cập nhật định mức nguyên vật liệu." if recipe else "Đã tạo định mức nguyên vật liệu.")
                return saved_response(request, reverse("bom:bom_detail", args=[saved.pk]))
        form.mark_errors()
        if version_form:
            version_form.mark_errors()
    context = _context(request, recipe=recipe, record=recipe, form=form, version_form=version_form,
        page_title="Chỉnh sửa định mức" if recipe else "Thêm định mức", cancel_url=reverse("bom:bom_detail", args=[recipe.pk]) if recipe else reverse("bom:bom_list"))
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_create(request):
    return _recipe_form(request)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_edit(request, pk):
    return _recipe_form(request, pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_version_list(request, pk):
    _context(request)
    workspace = require_access(request, resource="bom")
    recipe = selectors.recipe_detail(organization=workspace.organization, pk=pk)
    page, sort, per_page = selectors.version_list(recipe=recipe, filters=request.GET)
    columns = (("version", "Phiên bản", True), (None, "Sản lượng chuẩn", True), (None, "Đơn vị tính", False),
        (None, "Thu hồi", True), (None, "Trạng thái bản ghi", False), ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False))
    context = _context(request, recipe=recipe, page_title=f"Phiên bản · {recipe.code}", primary_action_url=reverse("bom:bom_version_create", args=[pk]), primary_action_label="+ Tạo phiên bản mới")
    context.update(_table_context(page=page, sort=sort, per_page=per_page, list_url=reverse("bom:bom_version_list", args=[pk]),
        columns=columns, rows_template="bom/partials/version_rows.html", sort_labels=(("version", "Phiên bản"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        filters=request.GET, has_filters=any(request.GET.get(name) for name in ("status", "effective")),
        filter_options=tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")}
            for name, label, choices in (("status", "Trạng thái", VERSION_STATUSES), ("effective", "Hiệu lực theo ngày", DATE_STATUSES)))))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "bom/version_list.html", context)


def _version_form(request, pk, version_pk=None):
    _context(request)
    workspace = require_access(request, "edit" if version_pk is not None else "create", resource="bom_version")
    recipe = selectors.recipe_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(recipe=recipe, pk=version_pk) if version_pk is not None else None
    source = None
    if version is None and request.GET.get("source"):
        try:
            source_id = int(request.GET["source"])
        except ValueError:
            raise Http404 from None
        source = selectors.version_detail(recipe=recipe, pk=source_id)
    kwargs = {"instance": version} if version else {"source": source}
    form = RecipeVersionForm(request.POST if request.method == "POST" else None, workspace=workspace, **kwargs)
    if request.method == "POST" and form.is_valid():
        try:
            saved = (services.update_version(workspace=workspace, recipe=recipe, instance=version, data=form.cleaned_data)
                if version else services.create_version(workspace=workspace, recipe=recipe, data=form.cleaned_data, source=source))
        except ValidationError as error:
            add_form_error(form, error)
            if version:
                version.refresh_from_db(fields=["status"])
        else:
            messages.success(request, "Đã cập nhật phiên bản định mức." if version else "Đã tạo phiên bản định mức mới.")
            return saved_response(request, reverse("bom:bom_version_detail", args=[recipe.pk, saved.pk]))
    readonly = version is not None and version.status not in EDITABLE_STATUSES
    if readonly:
        for field in form.fields.values():
            field.widget.attrs["disabled"] = True
    if form.is_bound:
        form.mark_errors()
    context = _context(request, recipe=recipe, form=form, resource_label="phiên bản định mức", form_readonly=readonly,
        form_action=request.get_full_path(), page_title="Chỉnh sửa phiên bản" if version else "Tạo phiên bản định mức mới",
        cancel_url=reverse("bom:bom_version_detail", args=[recipe.pk, version.pk]) if version else reverse("bom:bom_detail", args=[recipe.pk]),
        form_notice=("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới." if readonly else
            f"Sao chép cấu hình và thành phần từ phiên bản {source.version_no}; phiên bản cũ được giữ nguyên. Phiên bản mới ở trạng thái Nháp." if source else "Phiên bản mới ở trạng thái Nháp."))
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_version_create(request, pk):
    return _version_form(request, pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_version_edit(request, pk, version_pk):
    return _version_form(request, pk, version_pk)


def _line_result(request, recipe, version, workspace):
    context = _lines_context(request, recipe, version, workspace)
    response = render(request, "bom/partials/line_saved.html", context)
    response["HX-Retarget"] = "#bom-lines-table"
    response["HX-Reswap"] = "outerHTML"
    return response


def _line_form(request, pk, version_pk, line_pk=None, removing=False):
    _context(request)
    workspace = require_access(request, "edit" if line_pk is not None else "create", resource="bom_line")
    recipe = selectors.recipe_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(recipe=recipe, pk=version_pk)
    line = selectors.line_detail(version=version, organization=workspace.organization, pk=line_pk) if line_pk is not None else None
    form = RecipeLineForm(request.POST if request.method == "POST" else None, workspace=workspace, version=version, instance=line)
    error = None
    if request.method == "POST" and (removing or form.is_valid()):
        try:
            if removing:
                services.remove_line(workspace=workspace, recipe=recipe, version=version, instance=line)
            else:
                services.save_line(workspace=workspace, recipe=recipe, version=version, data=form.cleaned_data, instance=line)
        except ValidationError as exception:
            error = " ".join(exception.messages)
            if not removing:
                add_form_error(form, exception)
            version.refresh_from_db(fields=["status"])
        else:
            messages.success(request, "Đã xóa thành phần." if removing else "Đã cập nhật thành phần." if line else "Đã thêm thành phần.")
            if is_htmx(request):
                return _line_result(request, recipe, version, workspace)
            return saved_response(request, reverse("bom:bom_version_detail", args=[recipe.pk, version.pk]))
    editable = version.status in EDITABLE_STATUSES
    if not editable:
        error = "Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới."
    if form.is_bound:
        form.mark_errors()
    context = _version_context(request, recipe, version, workspace)
    context.update(form=form, line=line, removing=removing, line_error=error, editable=editable,
        inline_editor=is_htmx(request),
        resource_label="thành phần định mức", form_action=request.get_full_path(),
        editor_title="Xóa thành phần" if removing else "Chỉnh sửa thành phần" if line else "Thêm thành phần")
    return render(request, "bom/partials/line_editor.html" if is_htmx(request) else "bom/line_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_line_create(request, pk, version_pk):
    return _line_form(request, pk, version_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_line_edit(request, pk, version_pk, line_pk):
    return _line_form(request, pk, version_pk, line_pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def bom_line_remove(request, pk, version_pk, line_pk):
    return _line_form(request, pk, version_pk, line_pk, removing=True)
