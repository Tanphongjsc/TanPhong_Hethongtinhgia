"""Request orchestration for the two overhead configuration resources."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers

from apps.master_data.access import require_access
from apps.master_data.presentation import display_label
from apps.master_data.ui_helpers import add_form_error, is_htmx, saved_response
from . import overhead_selectors as selectors, overhead_services as services
from .definition_helpers import table_context
from .overhead_forms import AllocationRuleForm, CostPoolForm

PAGES = {
    "cost_pool": {"title": "Nhóm chi phí chung", "label": "nhóm chi phí chung", "action": "+ Thêm nhóm chi phí",
        "form": CostPoolForm, "selector": selectors.cost_pool_list, "service": services.save_cost_pool,
        "description": "Quản lý nhóm tập hợp chi phí chung và các quy tắc phân bổ liên quan.",
        "columns": (("code", "Mã", False), ("name", "Tên nhóm chi phí", False), (None, "Loại nhóm chi phí", False), (None, "Số quy tắc", True), (None, "Trạng thái", False)),
        "sorts": (("code", "Mã"), ("name", "Tên"), ("created_at", "Ngày tạo")), "search": "Tìm mã, tên hoặc mô tả nhóm chi phí…"},
    "allocation_rule": {"title": "Quy tắc phân bổ", "label": "quy tắc phân bổ", "action": "+ Thêm quy tắc phân bổ",
        "form": AllocationRuleForm, "selector": selectors.allocation_rule_list, "service": services.save_allocation_rule,
        "description": "Quản lý tiêu thức, mức ưu tiên và thời gian áp dụng quy tắc phân bổ chi phí chung.",
        "columns": (("code", "Mã", False), ("name", "Tên quy tắc", False), (None, "Nhóm chi phí", False), (None, "Tiêu thức phân bổ", False),
            (None, "Đơn vị tiêu thức", False), ("priority", "Mức ưu tiên", True), ("effective_from", "Hiệu lực từ ngày", False),
            (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False), (None, "Trạng thái bản ghi", False)),
        "sorts": (("code", "Mã"), ("name", "Tên"), ("priority", "Mức ưu tiên"), ("effective_from", "Hiệu lực từ ngày"), ("created_at", "Ngày tạo")),
        "search": "Tìm mã, tên quy tắc hoặc nhóm chi phí…"},
}


def _context(request, resource):
    page = PAGES[resource]
    request.costing_resource_label = page["label"]
    list_url = reverse(f"bom:{resource}_list")
    return {"resource": resource, "resource_label": page["label"], "page_title": page["title"], "page_description": page["description"],
        "list_url": list_url, "breadcrumbs": (("Sản xuất", None), (page["title"], list_url)),
        "detail_url_name": f"bom:{resource}_detail", "edit_url_name": f"bom:{resource}_edit"}


def _table(request, workspace, resource, *, pool=None, list_url=None):
    page = PAGES[resource]
    arguments = {"organization": workspace.organization, "filters": request.GET}
    if pool is not None:
        arguments["pool"] = pool
    records, sort, per_page = page["selector"](**arguments)
    options = tuple({"name": name, "label": label, "choices": choices,
        "selected": request.GET.get(name, request.GET.get("is_active", "") if name == "active" else "")}
        for name, label, choices in selectors.filter_options(resource=resource, organization=workspace.organization, pool=pool))
    return table_context(page=records, sort=sort, per_page=per_page, list_url=list_url or reverse(f"bom:{resource}_list"),
        columns=page["columns"], rows_template=f"bom/overhead/partials/{resource}_rows.html", sort_labels=page["sorts"],
        filter_options=options, filters=request.GET, search_placeholder=page["search"],
        has_filters=any(request.GET.get(name) for name in ("q", "is_active", *(option["name"] for option in options))),
        resource=resource, resource_label=page["label"], detail_url_name=f"bom:{resource}_detail", edit_url_name=f"bom:{resource}_edit",
        can_edit=getattr(workspace.permissions, f"can_edit_{resource}"))


def _list(request, resource):
    context = _context(request, resource)
    workspace = require_access(request, resource=resource)
    context.update(_table(request, workspace, resource),
        primary_action_url=reverse(f"bom:{resource}_create") if getattr(workspace.permissions, f"can_create_{resource}") else None,
        primary_action_label=PAGES[resource]["action"])
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _field(label, value, *, technical=False, numeric=False):
    return {"label": label, "value": value, "technical": technical, "numeric": numeric}


def _detail(request, resource, pk):
    context = _context(request, resource)
    workspace = require_access(request, resource=resource)
    record = selectors.overhead_detail(resource=resource, organization=workspace.organization, pk=pk)
    if resource == "cost_pool":
        sections = (("Thông tin nhóm chi phí", (_field("Mã nhóm chi phí", record.code, technical=True), _field("Tên nhóm chi phí", record.name),
            _field("Loại nhóm chi phí", display_label(record.pool_type)), _field("Mô tả", record.description))),)
        history = _table(request, workspace, "allocation_rule", pool=record, list_url=reverse("bom:cost_pool_detail", args=[pk]))
        history.update(primary_action_url=reverse("bom:allocation_rule_create") + f"?pool={pk}" if workspace.permissions.can_create_allocation_rule and record.is_active else None,
            primary_action_label="+ Thêm quy tắc phân bổ")
        context["rule_history"] = history
        context["rule_list_url"] = reverse("bom:allocation_rule_list") + f"?pool={pk}"
        if is_htmx(request) and request.headers.get("HX-Target") == "reference-data-table":
            return render(request, "master_data/partials/reference_data_table.html", history)
    else:
        sections = (("Thông tin quy tắc", (_field("Mã quy tắc", record.code, technical=True), _field("Tên quy tắc", record.name),
            _field("Nhóm chi phí", f"{record.pool.code} — {record.pool.name}"))),
            ("Cơ sở phân bổ", (_field("Tiêu thức phân bổ", display_label(record.basis_type)),
                _field("Đơn vị tiêu thức", f"{record.basis_uom.name} ({record.basis_uom.symbol})" if record.basis_uom else None),
                _field("Mã công thức tham chiếu", record.formula_code, technical=True), _field("Mức ưu tiên", record.priority, numeric=True),
                _field("Điều kiện bổ sung", "Có điều kiện áp dụng bổ sung" if record.condition_jsonb else "Không có điều kiện bổ sung"))),
            ("Hiệu lực", (_field("Hiệu lực từ ngày", record.effective_from.strftime("%d/%m/%Y")),
                _field("Hiệu lực đến ngày", record.effective_to.strftime("%d/%m/%Y") if record.effective_to else "Không giới hạn"))))
        context["pool_url"] = reverse("bom:cost_pool_detail", args=[record.pool_id])
    context.update(record=record, detail_sections=sections, created_at=timezone.localtime(record.created_at).strftime("%d/%m/%Y %H:%M"),
        primary_action_url=reverse(f"bom:{resource}_edit", args=[pk]) if getattr(workspace.permissions, f"can_edit_{resource}") else None,
        primary_action_label="Chỉnh sửa")
    return render(request, "bom/overhead/partials/detail_content.html" if is_htmx(request) else "bom/overhead/detail.html", context)


def _form(request, resource, pk=None):
    context = _context(request, resource)
    workspace = require_access(request, "edit" if pk is not None else "create", resource=resource)
    record = selectors.overhead_detail(resource=resource, organization=workspace.organization, pk=pk) if pk is not None else None
    initial = {}
    if resource == "allocation_rule" and record is None and request.GET.get("pool"):
        pool = selectors.overhead_detail(resource="cost_pool", organization=workspace.organization, pk=_pool_id(request.GET["pool"]))
        if pool.is_active:
            initial["pool"] = pool.pk
    form = PAGES[resource]["form"](request.POST if request.method == "POST" else None, workspace=workspace, instance=record, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            saved = PAGES[resource]["service"](workspace=workspace, data=form.cleaned_data, instance=record)
        except ValidationError as error:
            add_form_error(form, error)
        else:
            messages.success(request, f"Đã {'cập nhật' if record else 'tạo'} {PAGES[resource]['label']}.")
            return saved_response(request, reverse(f"bom:{resource}_detail", args=[saved.pk]))
    if form.is_bound:
        form.mark_errors()
    context.update(form=form, record=record, page_title=f"{'Chỉnh sửa' if record else 'Thêm'} {PAGES[resource]['label']}",
        cancel_url=reverse(f"bom:{resource}_detail", args=[pk]) if record else context["list_url"])
    if resource == "allocation_rule":
        context["form_notice"] = "Thêm quy tắc mới với mã khác khi đổi kỳ áp dụng để giữ lịch sử. Chỉnh sửa sẽ cập nhật trực tiếp bản ghi này."
        if record and record.condition_jsonb:
            context["form_notice"] += " Các điều kiện áp dụng bổ sung được giữ nguyên."
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


def _pool_id(value):
    try:
        return int(value)
    except ValueError:
        raise Http404 from None


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def cost_pool_list(request):
    return _list(request, "cost_pool")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request", "HX-Target")
def cost_pool_detail(request, pk):
    return _detail(request, "cost_pool", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def cost_pool_create(request):
    return _form(request, "cost_pool")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def cost_pool_edit(request, pk):
    return _form(request, "cost_pool", pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def allocation_rule_list(request):
    return _list(request, "allocation_rule")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def allocation_rule_detail(request, pk):
    return _detail(request, "allocation_rule", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def allocation_rule_create(request):
    return _form(request, "allocation_rule")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def allocation_rule_edit(request, pk):
    return _form(request, "allocation_rule", pk)
