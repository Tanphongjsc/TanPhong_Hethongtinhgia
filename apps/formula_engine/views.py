"""HTTP orchestration; DSL/domain behavior stays in engine/services."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.decorators.vary import vary_on_headers
from apps.core.models import Formula
from apps.master_data.access import require_access
from apps.master_data.ui_helpers import add_form_error, is_htmx, saved_response
from apps.bom.definition_helpers import table_context
from . import selectors, services
from .constants import VERSION_FIELDS
from .engine import build_plan
from .errors import FormulaError
from .forms import FormulaForm, TestForm, VersionForm, style_fields
from .functions import FUNCTIONS


def _context(request):
    request.costing_resource_label = "công thức tính"
    url = reverse("formula_engine:formula_list")
    return {"resource": "formula", "resource_label": "công thức tính", "page_title": "Công thức tính",
        "page_description": "Quản lý biểu thức, phiên bản, phụ thuộc và kiểm thử công thức an toàn.",
        "list_url": url, "breadcrumbs": (("Công thức & quy tắc", None), ("Công thức tính", url)),
        "detail_url_name": "formula_engine:formula_detail", "edit_url_name": "formula_engine:formula_edit"}


def _version_url(formula, version):
    return reverse("formula_engine:formula_version_detail", args=[formula.pk, version.pk])


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_list(request):
    workspace = require_access(request, resource="formula")
    page, sort, size = selectors.formula_list(organization=workspace.organization, filters=request.GET)
    context = _context(request)
    options = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")} for name, label, choices in selectors.filter_options())
    context.update(table_context(page=page, sort=sort, per_page=size, list_url=context["list_url"],
        columns=(("code", "Mã", False), ("name", "Tên công thức", False), (None, "Kết quả", False), ("version", "Phiên bản mới nhất", False),
            (None, "Trạng thái phiên bản", False), (None, "Kiểm tra đã lưu", False), (None, "Hiệu lực", False), ("updated_at", "Cập nhật lần cuối", False)),
        rows_template="formula_engine/partials/formula_rows.html", sort_labels=(("code", "Mã"), ("name", "Tên"), ("version", "Phiên bản"), ("updated_at", "Cập nhật lần cuối")),
        filter_options=options, has_filters=bool(request.GET), search_placeholder="Tìm mã, tên hoặc mô tả công thức…", can_edit=workspace.permissions.can_edit_formula),
        primary_action_url=reverse("formula_engine:formula_create") if workspace.permissions.can_create_formula else None, primary_action_label="+ Thêm công thức")
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _show_plan(context, plan):
    unique = dict(((kind, target.pk), (kind, target)) for kind, target in plan.bindings[plan.root_code].values())
    context.update(plan=plan, output_type=plan.types[plan.root_code], dependency_rows=tuple(
        {"kind": kind, "code": target.code, "name": target.name} for kind, target in unique.values()),
        referenced_versions=tuple(plan.versions.items()))


def _plan(context, workspace, formula, expression):
    try: plan = build_plan(organization=workspace.organization, formula=formula, expression=expression)
    except FormulaError as error:
        context["plan_error"] = error.describe(expression)
        return None
    _show_plan(context, plan)
    return plan


def _test_context(request, context, workspace, formula, plan, *, allow_save=True):
    bound = request.method == "POST" and request.POST.get("action") in ("test", "save_test")
    form = TestForm(request.POST if bound else None, plan=plan)
    context.update(test_form=form, allow_save_test=allow_save and bool(formula.pk))
    action = request.POST.get("action") if request.method == "POST" else None
    if action == "run_cases":
        context["case_results"] = services.run_cases(plan, selectors.test_cases(formula))
        return
    if bound and form.is_valid():
        try:
            if action == "save_test":
                if not allow_save or not formula.pk: raise ValidationError("Lưu phiên bản trước khi lưu bộ kiểm thử.")
                if not form.cleaned_data.get("test_name"): raise ValidationError({"test_name": "Vui lòng nhập tên bộ kiểm thử."})
                services.save_test_case(workspace=workspace, formula=formula, plan=plan, data=form.cleaned_data)
                context["test_saved"] = True
            result = plan.run(form.cleaned_data["inputs"])
            expected = form.cleaned_data.get("expected")
            context.update(result=result, has_expected=expected is not None, expected=expected, passed=result.value == expected)
        except ValidationError as error: add_form_error(form, error)
        except FormulaError as error: form.add_error(None, error.describe())
    style_fields(form)


def _detail(request, pk, version_id=None, activation_error=None):
    workspace = require_access(request, resource="formula")
    formula = selectors.formula_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(formula=formula, pk=version_id) if version_id else selectors.latest_version(formula)
    context = _context(request)
    context.update(formula=formula, version=version, activation_error=activation_error, page_title=formula.name,
        primary_action_url=reverse("formula_engine:formula_edit", args=[pk]), primary_action_label="Chỉnh sửa",
        version_create_url=reverse("formula_engine:formula_version_create", args=[pk]),
        version_list_url=reverse("formula_engine:formula_version_list", args=[pk]))
    if version:
        context.update(editable=version.status in ("DRAFT", "IN_REVIEW"), version_url=_version_url(formula, version),
            version_edit_url=reverse("formula_engine:formula_version_edit", args=[pk, version.pk]),
            activate_url=reverse("formula_engine:formula_version_activate", args=[pk, version.pk]))
        plan = _plan(context, workspace, formula, version.expression)
        if plan: _test_context(request, context, workspace, formula, plan)
    context["cases"] = selectors.test_cases(formula)
    if is_htmx(request) and request.headers.get("HX-Target") == "formula-test-panel":
        return render(request, "formula_engine/partials/test_panel.html", context)
    return render(request, "formula_engine/partials/detail_content.html" if is_htmx(request) else "formula_engine/detail.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_detail(request, pk): return _detail(request, pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_version_detail(request, pk, version_id): return _detail(request, pk, version_id)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_test(request, pk): return _detail(request, pk)


@require_POST
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_test_deactivate(request, pk, case_id):
    workspace = require_access(request, "edit", resource="formula_test")
    formula = selectors.formula_detail(organization=workspace.organization, pk=pk)
    try: services.deactivate_test_case(workspace=workspace, formula=formula, case_id=case_id)
    except ValidationError as error: return _detail(request, pk, activation_error="; ".join(error.messages))
    messages.success(request, "Đã ngừng sử dụng bộ kiểm thử.")
    return saved_response(request, reverse("formula_engine:formula_detail", args=[pk]))


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_edit(request, pk):
    workspace = require_access(request, "edit", resource="formula")
    record = selectors.formula_detail(organization=workspace.organization, pk=pk)
    form = FormulaForm(request.POST if request.method == "POST" else None, workspace=workspace, instance=record)
    if request.method == "POST" and form.is_valid():
        try: saved = services.save_formula(workspace=workspace, data=form.cleaned_data, instance=record)
        except ValidationError as error: add_form_error(form, error)
        else:
            messages.success(request, "Đã cập nhật công thức.")
            return saved_response(request, reverse("formula_engine:formula_detail", args=[saved.pk]))
    form.mark_errors()
    context = _context(request)
    context.update(form=form, record=record, page_title="Chỉnh sửa công thức", cancel_url=reverse("formula_engine:formula_detail", args=[pk]))
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


def _studio(request, pk=None, version_id=None):
    editing = version_id is not None
    workspace = require_access(request, "edit" if editing else "create", resource="formula_version" if pk else "formula")
    record = selectors.formula_detail(organization=workspace.organization, pk=pk) if pk else None
    source = None
    if record:
        source = selectors.version_detail(formula=record, pk=version_id) if editing else selectors.latest_version(record)
        if editing: services.ensure_editable(source)
    bound = request.method == "POST"
    header = FormulaForm(request.POST if bound else None, workspace=workspace) if record is None else None
    formula = record
    header_valid = header.is_valid() if bound and header else True
    if header and bound and header_valid: formula = Formula(organization=workspace.organization, **header.cleaned_data)
    if formula is None: formula = Formula(organization=workspace.organization, code="NEW_FORMULA", name="Công thức mới")
    initial = {key: getattr(source, key) for key in VERSION_FIELDS} if source else {}
    version_form = VersionForm(request.POST if bound else None, workspace=workspace, formula=formula, initial=initial)
    valid = version_form.is_valid() if bound else False
    context = _context(request)
    context.update(header_form=header, version_form=version_form, formula=record, source=source, editing=editing,
        page_title="Thiết lập công thức" if record is None else f"{'Chỉnh sửa' if editing else 'Tạo'} phiên bản · {record.code}",
        cancel_url=_version_url(record, source) if source else context["list_url"],
        catalogue=selectors.catalogue(organization=workspace.organization), function_help=FUNCTIONS.items())
    plan = version_form.plan if bound and valid else _plan(context, workspace, formula, source.expression) if not bound and source else None
    if plan:
        _show_plan(context, plan)
        _test_context(request, context, workspace, formula, plan, allow_save=False)
    if bound and valid and header_valid and request.POST.get("action", "save") == "save":
        try:
            if record is None:
                record = services.save_formula(workspace=workspace, data=header.cleaned_data, version_data=version_form.cleaned_data)
                saved = selectors.latest_version(record)
            else:
                saved = services.save_version(workspace=workspace, formula=record, data=version_form.cleaned_data, instance=source if editing else None, source=source if not editing else None)
        except ValidationError as error:
            if hasattr(error, "message_dict") and "code" in error.message_dict and header: add_form_error(header, error)
            else: add_form_error(version_form, error)
        else:
            messages.success(request, "Đã tạo công thức." if pk is None else "Đã cập nhật phiên bản công thức." if editing else "Đã tạo phiên bản công thức mới.")
            return saved_response(request, _version_url(record, saved))
    style_fields(version_form)
    if header: header.mark_errors()
    return render(request, "formula_engine/partials/studio_content.html" if is_htmx(request) else "formula_engine/studio.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_create(request): return _studio(request)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_version_create(request, pk): return _studio(request, pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_version_edit(request, pk, version_id):
    try: return _studio(request, pk, version_id)
    except ValidationError as error: return _detail(request, pk, version_id, "; ".join(error.messages))


@require_POST
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_version_activate(request, pk, version_id):
    workspace = require_access(request, "edit", resource="formula_version")
    formula = selectors.formula_detail(organization=workspace.organization, pk=pk)
    version = selectors.version_detail(formula=formula, pk=version_id)
    try: services.activate_version(workspace=workspace, formula=formula, version=version)
    except ValidationError as error: return _detail(request, pk, version_id, "; ".join(error.messages))
    messages.success(request, "Đã kích hoạt phiên bản công thức.")
    return saved_response(request, _version_url(formula, version))


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_version_list(request, pk):
    workspace = require_access(request, resource="formula")
    formula = selectors.formula_detail(organization=workspace.organization, pk=pk)
    page, sort, size = selectors.version_list(formula=formula, filters=request.GET)
    context = _context(request)
    context.update(formula=formula, resource_label="phiên bản công thức", page_title=f"Phiên bản · {formula.code}",
        primary_action_url=reverse("formula_engine:formula_version_create", args=[pk]), primary_action_label="+ Tạo phiên bản mới")
    context.update(table_context(page=page, sort=sort, per_page=size, list_url=request.path,
        columns=(("version", "Phiên bản", False), (None, "Trạng thái", False), (None, "Kiểm tra đã lưu", False), ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False)),
        rows_template="formula_engine/partials/version_rows.html", sort_labels=(("version", "Phiên bản"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")), filter_options=(), has_filters=False))
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "formula_engine/versions.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def formula_catalogue(request):
    workspace = require_access(request, resource="formula")
    return render(request, "formula_engine/partials/catalogue.html", {"catalogue": selectors.catalogue(organization=workspace.organization, keyword=request.GET.get("q", ""))})
