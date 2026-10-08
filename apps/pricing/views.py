from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers
from apps.master_data.access import require_access
from apps.master_data.constants import PAGE_SIZES
from apps.master_data.ui_helpers import is_htmx, add_form_error, saved_response
from . import selectors, services
from .constants import TITLES, LABELS
from .forms import ChannelForm, ChannelFeeRuleForm, TaxRuleForm, FxRateForm, ClosePeriodForm
from .presentation import PAGE_COLUMNS, FIELD_LABELS, decorate, field_value

FORMS = dict(zip(TITLES, (ChannelForm, ChannelFeeRuleForm, TaxRuleForm, FxRateForm)))
DESCRIPTIONS = {"channel": "Quản lý kênh bán và thông tin giao dịch.", "channel_fee_rule": "Quản lý phí kênh theo phạm vi sản phẩm và thời gian áp dụng.", "tax_rule": "Quản lý thuế theo khu vực, loại giao dịch và thời gian áp dụng.", "fx_rate": "Quản lý tỷ giá theo chiều quy đổi, loại tỷ giá và thời gian áp dụng."}


def _context(resource):
    listing = reverse(f"pricing:{resource}_list")
    return {"resource": resource, "resource_label": LABELS[resource], "page_title": TITLES[resource], "page_description": DESCRIPTIONS[resource], "breadcrumbs": (("Giá bán", None), (TITLES[resource], listing)), "list_url": listing, "detail_url_name": f"pricing:{resource}_detail", "edit_url_name": f"pricing:{resource}_edit", "columns": PAGE_COLUMNS[resource], "column_count": len(PAGE_COLUMNS[resource]) + 1, "rows_template": "pricing/partials/rows.html", "table_id": "reference-data-table", "filter_form_id": "reference-data-filters", "search_id": "reference-data-search", "search_placeholder": "Tìm theo mã hoặc thông tin cấu hình…"}


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def list_view(request, resource):
    workspace = require_access(request, resource=resource)
    context = _context(resource)
    page, sort, per_page = selectors.list_records(resource=resource, organization=workspace.organization, filters=request.GET)
    options = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, "")} for name, label, choices in selectors.filter_options(resource=resource, organization=workspace.organization))
    context.update(page_obj=page, records=[decorate(record, resource) for record in page.object_list], current_sort=sort, per_page=per_page,
        filters=request.GET, page_sizes=PAGE_SIZES, filter_options=options, has_filters=bool(request.GET.get("q") or any(option["selected"] for option in options)),
        sort_options=tuple((prefix + field, FIELD_LABELS.get(field, field) + (" ↓" if prefix else " ↑")) for field in selectors.SORTS[resource] for prefix in ("", "-")), can_edit=True,
        primary_action_url=reverse(f"pricing:{resource}_create"), primary_action_label="+ Thêm mới")
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "pricing/list.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def detail_view(request, resource, pk):
    workspace = require_access(request, resource=resource)
    record = selectors.detail(resource=resource, organization=workspace.organization, pk=pk)
    context = _context(resource)
    sections = []
    for title, names in FORMS[resource].groups:
        fields = [{"label": "Tỷ giá" if name == "rate" and resource == "fx_rate" else FIELD_LABELS[name], "value": field_value(record, name, resource), "numeric": name in ("rate", "fixed_amount", "cap_amount", "floor_amount", "priority", "refundable_ratio", "recoverable_ratio")} for name in names if name != "status"]
        sections.append((title, fields))
    editable = resource == "channel" or record.status == "DRAFT"
    context.update(record=record, detail_sections=sections, direction=field_value(record, "direction", resource) if resource == "fx_rate" else None,
        primary_action_url=reverse(context["edit_url_name"], args=[record.pk]) if editable else None, primary_action_label="Chỉnh sửa", readonly=not editable,
        close_url=reverse(f"pricing:{resource}_close", args=[record.pk]) if resource != "channel" and record.status == "EFFECTIVE" and getattr(record, "valid_to" if resource == "fx_rate" else "effective_to") is None else None)
    return render(request, "pricing/partials/detail_content.html" if is_htmx(request) else "pricing/detail.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def form_view(request, resource, pk=None):
    workspace = require_access(request, "edit" if pk is not None else "create", resource=resource)
    context = _context(resource)
    record = selectors.detail(resource=resource, organization=workspace.organization, pk=pk) if pk is not None else None
    form = FORMS[resource](request.POST if request.method == "POST" else None, workspace=workspace, instance=record)
    if request.method == "POST" and form.is_valid():
        try: saved = services.save_record(resource=resource, workspace=workspace, data=form.cleaned_data, instance=record)
        except ValidationError as error: add_form_error(form, error)
        else:
            messages.success(request, f"Đã {'cập nhật' if record else 'tạo'} {LABELS[resource]}.")
            return saved_response(request, reverse(context["detail_url_name"], args=[saved.pk]))
    if form.is_bound: form.mark_errors()
    context.update(form=form, record=record, page_title=f"{'Chỉnh sửa' if record else 'Thêm mới'} {LABELS[resource]}", form_readonly=bool(record and resource != "channel" and record.status != "DRAFT"),
        cancel_url=reverse(context["detail_url_name"], args=[record.pk]) if record else context["list_url"],
        form_notice=None if resource == "channel" else "Bản đã đưa vào hiệu lực chỉ được xem; hãy thêm bản mới khi thay đổi kỳ hoặc mức áp dụng. Ngày/thời điểm kết thúc không thuộc khoảng hiệu lực. Không tự chọn bản mới nhất khi có dữ liệu chồng nhau.")
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "pricing/form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def close_view(request, resource, pk):
    workspace = require_access(request, "edit", resource=resource)
    record = selectors.detail(resource=resource, organization=workspace.organization, pk=pk)
    form = ClosePeriodForm(request.POST if request.method == "POST" else None, resource=resource)
    destination = reverse(f"pricing:{resource}_detail", args=[pk])
    if request.method == "POST" and form.is_valid():
        try: services.close_period(resource=resource, workspace=workspace, instance=record, end=form.cleaned_data[form.name])
        except ValidationError as error: add_form_error(form, error)
        else:
            messages.success(request, "Đã đặt mốc kết thúc hiệu lực.")
            return saved_response(request, destination)
    if form.is_bound: form.mark_errors()
    context = _context(resource)
    context.update(form=form, record=record, page_title="Kết thúc hiệu lực", resource_label="thời gian hiệu lực", cancel_url=destination,
        form_notice="Chỉ đặt mốc kết thúc tương lai cho bản chưa có ngày kết thúc. Mốc kết thúc không thuộc khoảng áp dụng; mức và điều kiện cũ được giữ nguyên.")
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "pricing/form.html", context)
