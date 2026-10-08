from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers

from apps.core.models import CostElement

from .access import require_access
from .constants import COST_SCOPES, PAGE_SIZES, SOURCE_MODES, SORT_FIELDS, VALUE_TYPES
from .forms import CostElementForm, CurrencyForm, SupplierForm, SupplierPriceForm, UomCategoryForm, UomForm, UomConversionForm
from . import selectors, services
from .selectors import cost_element_detail as get_element, cost_element_groups, cost_element_list as get_list
from .services import save_cost_element
from .presentation import format_number, supplier_detail_fields, supplier_price_detail_fields
from .ui_helpers import is_htmx, add_form_error, saved_response


def page_context(title, **extra):
    return {
        "page_title": title,
        "resource_label": "phần tử chi phí",
        "page_description": "Quản lý các biến nghiệp vụ được sử dụng trong công thức và phương án tính giá thành.",
        "breadcrumbs": (("Dữ liệu danh mục", None), ("Danh mục phần tử chi phí", reverse("master_data:cost_element_list"))),
        **extra,
    }


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def cost_element_list(request):
    workspace = require_access(request)
    page, sort, per_page = get_list(organization=workspace.organization, permissions=workspace.permissions, filters=request.GET)
    context = page_context("Danh mục phần tử chi phí", page_obj=page, elements=page.object_list,
        filters=request.GET, current_sort=sort, per_page=per_page, page_sizes=PAGE_SIZES,
        groups=cost_element_groups(organization=workspace.organization),
        value_types=VALUE_TYPES, source_modes=SOURCE_MODES, cost_scopes=COST_SCOPES,
        sort_options=tuple((prefix + field, {"code": "Mã", "name": "Tên", "value_type": "Loại giá trị", "created_at": "Ngày tạo"}[field] + (" ↓" if prefix else " ↑")) for field in SORT_FIELDS for prefix in ("", "-")),
        has_filters=any(request.GET.get(name) for name in ("q", "group", "value_type", "source_mode", "cost_scope", "active")))
    context["primary_action_url"] = reverse("master_data:cost_element_create") if workspace.permissions.can_create_cost_element else None
    context["primary_action_label"] = "+ Thêm mới"
    return render(request, "master_data/partials/cost_element_table.html" if is_htmx(request) else "master_data/cost_element_list.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def cost_element_detail(request, pk):
    request.costing_resource_label = "phần tử chi phí"
    workspace = require_access(request)
    element = get_element(organization=workspace.organization, permissions=workspace.permissions, pk=pk)
    can_edit = workspace.permissions.can_edit_cost_element and (not element.is_sensitive or workspace.permissions.can_manage_sensitive_cost_element)
    context = page_context(element.name, element=element, page_description=element.description or "Cấu hình phần tử chi phí.",
        primary_action_url=reverse("master_data:cost_element_edit", args=[element.pk]) if can_edit else None,
        primary_action_label="Chỉnh sửa")
    return render(request, "master_data/partials/cost_element_detail_content.html" if is_htmx(request) else "master_data/cost_element_detail.html", context)


def element_form(request, *, pk=None):
    request.costing_resource_label = "phần tử chi phí"
    workspace = require_access(request, "edit" if pk else "create")
    element = get_element(organization=workspace.organization, permissions=workspace.permissions, pk=pk) if pk else None
    if element and element.is_sensitive and not workspace.permissions.can_manage_sensitive_cost_element:
        raise PermissionDenied("Bạn không có quyền thực hiện thao tác này.")
    form = CostElementForm(request.POST if request.method == "POST" else None,
        organization=workspace.organization, permissions=workspace.permissions, instance=element)
    if request.method == "POST" and form.is_valid():
        try:
            saved = save_cost_element(workspace=workspace, data=form.cleaned_data, instance=element)
        except ValidationError as error:
            add_form_error(form, error)
        except CostElement.DoesNotExist:
            raise Http404("Không tìm thấy phần tử chi phí.") from None
        else:
            messages.success(request, "Đã cập nhật phần tử chi phí." if element else "Đã tạo phần tử chi phí.")
            destination = reverse("master_data:cost_element_detail", args=[saved.pk])
            return saved_response(request, destination)
    if form.is_bound:
        form.mark_errors()
    context = page_context("Chỉnh sửa phần tử chi phí" if element else "Thêm mới phần tử chi phí", form=form, element=element)
    return render(request, "master_data/partials/cost_element_form_content.html" if is_htmx(request) else "master_data/cost_element_form.html", context)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def cost_element_create(request):
    return element_form(request)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def cost_element_edit(request, pk):
    return element_form(request, pk=pk)


# Presentation metadata shared by reference pages. Domain rules remain in
# validators/services and each module keeps an explicit selector and form.
REFERENCE_PAGES = {
    "supplier": ("nhà cung cấp", "Danh mục nhà cung cấp", "Quản lý nhà cung cấp và điều khoản giao dịch.",
        (("code", "Mã", False), ("name", "Tên nhà cung cấp", False), (None, "Mã số thuế", False), (None, "Tiền tệ mặc định", False), (None, "Trạng thái", False), ("created_at", "Ngày tạo", False))),
    "supplier_price": ("giá nhà cung cấp", "Giá nhà cung cấp", "Lịch sử giá mua theo nhà cung cấp, vật tư / hàng hóa và thời gian. Hiệu lực theo ngày hiển thị riêng với trạng thái bản ghi.",
        (("supplier", "Nhà cung cấp", False), ("item", "Vật tư / Hàng hóa", False), ("unit_price", "Đơn giá", True), (None, "Tiền tệ", False), (None, "Đơn vị tính", False), (None, "Số lượng tối thiểu", True), ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False), (None, "Hiệu lực theo ngày", False), (None, "Trạng thái bản ghi", False))),
    "currency": ("tiền tệ", "Danh mục tiền tệ", "Danh mục tiền tệ dùng chung trong tính giá thành và giá bán.",
        (("code", "Mã", False), ("name", "Tên", False), ("decimal_places", "Số chữ số thập phân", True), (None, "Trạng thái", False))),
    "uom_category": ("nhóm đơn vị tính", "Danh mục nhóm đơn vị tính", "Quản lý nhóm đơn vị tính và mã đại lượng dùng chung.",
        (("code", "Mã", False), ("name", "Tên", False), ("dimension_code", "Mã đại lượng", False), (None, "Trạng thái", False))),
    "uom": ("đơn vị tính", "Danh mục đơn vị tính", "Quản lý đơn vị tính, độ chính xác và nhóm đơn vị tính.",
        (("code", "Mã", False), ("name", "Tên", False), (None, "Ký hiệu", False), ("category", "Nhóm đơn vị tính", False), ("precision", "Độ chính xác", True), (None, "Đơn vị cơ sở", False), (None, "Trạng thái", False))),
    "uom_conversion": ("quy đổi đơn vị tính", "Danh mục quy đổi đơn vị tính", "Quản lý hệ số quy đổi đơn vị tính theo thời gian.",
        (("from_uom", "Đơn vị nguồn", False), ("to_uom", "Đơn vị đích", False), (None, "Hệ số quy đổi", True), (None, "Vật tư / Hàng hóa", False), ("effective_from", "Hiệu lực từ ngày", False), (None, "Hiệu lực đến ngày", False))),
}


def _reference_context(request, resource, **extra):
    label, title, description, columns = REFERENCE_PAGES[resource]
    request.costing_resource_label = label
    list_url = reverse(f"master_data:{resource}_list")
    return {
        "resource": resource, "resource_label": label, "page_title": title,
        "page_description": description, "columns": columns, "column_count": len(columns) + 1,
        "breadcrumbs": (("Dữ liệu danh mục", None), (title, list_url)),
        "list_url": list_url, "detail_url_name": f"master_data:{resource}_detail",
        "edit_url_name": f"master_data:{resource}_edit",
        "table_id": "reference-data-table", "filter_form_id": "reference-data-filters",
        "search_id": "reference-data-search", "search_placeholder": "Tìm theo mã hoặc tên…",
        "rows_template": f"master_data/partials/{resource}_rows.html", **extra,
    }


def _reference_list(request, *, resource, selector):
    context = _reference_context(request, resource)
    workspace = require_access(request, resource=resource)
    page, sort, per_page = selector(organization=workspace.organization, filters=request.GET)
    filter_options = tuple({"name": name, "label": label, "choices": choices, "selected": request.GET.get(name, request.GET.get("is_active", "") if name == "active" else "")}
        for name, label, choices in selectors.reference_filter_options(resource=resource, organization=workspace.organization))
    sort_options = tuple((prefix + field, label + (" ↓" if prefix else " ↑"))
        for field, label, _ in context["columns"] if field for prefix in ("", "-"))
    context.update(page_obj=page, records=page.object_list, filters=request.GET,
        current_sort=sort, per_page=per_page, page_sizes=PAGE_SIZES, sort_options=sort_options,
        filter_options=filter_options, has_filters=any(request.GET.get(name) for name in ("q", "is_active", *(option["name"] for option in filter_options))),
        can_edit=getattr(workspace.permissions, f"can_edit_{resource}"),
        primary_action_url=reverse(f"master_data:{resource}_create") if getattr(workspace.permissions, f"can_create_{resource}") else None,
        primary_action_label="+ Thêm mới")
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "master_data/reference_data_list.html", context)


def _reference_detail(request, *, resource, pk):
    context = _reference_context(request, resource)
    workspace = require_access(request, resource=resource)
    record = selectors.reference_detail(resource=resource, pk=pk, organization=workspace.organization)
    can_edit = getattr(workspace.permissions, f"can_edit_{resource}")
    if resource == "supplier_price":
        fields = supplier_price_detail_fields(record)
        title = f"{record.supplier.code} / {record.item.code}"
    elif resource == "uom_conversion":
        can_edit = can_edit and record.organization_id == workspace.organization.pk
        fields = (("Đơn vị nguồn", record.from_uom.code), ("Đơn vị đích", record.to_uom.code),
            ("Hệ số quy đổi", format_number(record.factor)), ("Vật tư / Hàng hóa", f"{record.item.code} — {record.item.name}" if record.item else "—"),
            ("Hiệu lực từ ngày", record.effective_from.strftime("%d/%m/%Y")), ("Hiệu lực đến ngày", record.effective_to.strftime("%d/%m/%Y") if record.effective_to else "Không giới hạn"),
            ("Nguồn tham chiếu", record.source_reference or "—"))
        title = f"{record.from_uom.code} → {record.to_uom.code}"
    else:
        title = record.name
        fields = (("Mã", record.code), ("Tên", record.name))
        if resource == "currency":
            fields += (("Số chữ số thập phân", record.decimal_places),)
        elif resource == "uom_category":
            fields += (("Mã đại lượng", record.dimension_code), ("Mô tả", record.description or "—"))
        elif resource == "supplier":
            fields = supplier_detail_fields(record)
        else:
            fields += (("Ký hiệu", record.symbol), ("Nhóm đơn vị tính", f"{record.category.code} — {record.category.name}"), ("Độ chính xác", record.precision), ("Đơn vị cơ sở", "Có" if record.is_base else "Không"))
    context.update(record=record, detail_fields=fields, page_title=title,
        primary_action_url=reverse(context["edit_url_name"], args=[record.pk]) if can_edit else None,
        primary_action_label="Chỉnh sửa")
    return render(request, "master_data/partials/reference_data_detail_content.html" if is_htmx(request) else "master_data/reference_data_detail.html", context)


def _reference_form(request, *, resource, form_class, service, pk=None):
    context = _reference_context(request, resource)
    workspace = require_access(request, "edit" if pk is not None else "create", resource=resource)
    record = selectors.reference_detail(resource=resource, pk=pk, organization=workspace.organization) if pk is not None else None
    if resource == "uom_conversion" and record and record.organization_id != workspace.organization.pk:
        raise PermissionDenied("Bạn không có quyền chỉnh sửa quy đổi dùng chung trong phạm vi công ty này.")
    form = form_class(request.POST if request.method == "POST" else None, workspace=workspace, instance=record)
    if request.method == "POST" and form.is_valid():
        try:
            saved = service(workspace=workspace, data=form.cleaned_data, instance=record)
        except ValidationError as error:
            add_form_error(form, error)
        else:
            messages.success(request, f"Đã {'cập nhật' if record else 'tạo'} {context['resource_label']}.")
            destination = reverse(context["detail_url_name"], args=[saved.pk])
            return saved_response(request, destination)
    if form.is_bound:
        form.mark_errors()
    context.update(form=form, record=record, page_title=f"{'Chỉnh sửa' if record else 'Thêm mới'} {context['resource_label']}",
        cancel_url=reverse(context["detail_url_name"], args=[record.pk]) if record else context["list_url"])
    if resource == "supplier_price":
        context["form_notice"] = (
            "Chỉnh sửa sẽ thay đổi bản ghi lịch sử này. Khi cập nhật báo giá cho kỳ mới, hãy thêm bản ghi mới để giữ giá cũ. Trạng thái bản ghi hiện có được giữ nguyên."
            if record else "Giá mới được lưu ở trạng thái Nháp. Khoảng hiệu lực theo ngày không thay thế việc duyệt giá."
        )
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "master_data/reference_data_form.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def currency_list(request):
    return _reference_list(request, resource="currency", selector=selectors.currency_list)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def currency_detail(request, code):
    return _reference_detail(request, resource="currency", pk=code)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def currency_create(request):
    return _reference_form(request, resource="currency", form_class=CurrencyForm, service=services.save_currency)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def currency_edit(request, code):
    return _reference_form(request, resource="currency", form_class=CurrencyForm, service=services.save_currency, pk=code)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_category_list(request):
    return _reference_list(request, resource="uom_category", selector=selectors.uom_category_list)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_category_detail(request, pk):
    return _reference_detail(request, resource="uom_category", pk=pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_category_create(request):
    return _reference_form(request, resource="uom_category", form_class=UomCategoryForm, service=services.save_uom_category)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_category_edit(request, pk):
    return _reference_form(request, resource="uom_category", form_class=UomCategoryForm, service=services.save_uom_category, pk=pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_list(request):
    return _reference_list(request, resource="uom", selector=selectors.uom_list)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_detail(request, pk):
    return _reference_detail(request, resource="uom", pk=pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_create(request):
    return _reference_form(request, resource="uom", form_class=UomForm, service=services.save_uom)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_edit(request, pk):
    return _reference_form(request, resource="uom", form_class=UomForm, service=services.save_uom, pk=pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_conversion_list(request):
    return _reference_list(request, resource="uom_conversion", selector=selectors.uom_conversion_list)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_conversion_detail(request, pk):
    return _reference_detail(request, resource="uom_conversion", pk=pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_conversion_create(request):
    return _reference_form(request, resource="uom_conversion", form_class=UomConversionForm, service=services.save_uom_conversion)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def uom_conversion_edit(request, pk):
    return _reference_form(request, resource="uom_conversion", form_class=UomConversionForm, service=services.save_uom_conversion, pk=pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_list(request):
    return _reference_list(request, resource="supplier", selector=selectors.supplier_list)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_detail(request, pk):
    return _reference_detail(request, resource="supplier", pk=pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_create(request):
    return _reference_form(request, resource="supplier", form_class=SupplierForm, service=services.save_supplier)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_edit(request, pk):
    return _reference_form(request, resource="supplier", form_class=SupplierForm, service=services.save_supplier, pk=pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_price_list(request):
    return _reference_list(request, resource="supplier_price", selector=selectors.supplier_price_list)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_price_detail(request, pk):
    return _reference_detail(request, resource="supplier_price", pk=pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_price_create(request):
    return _reference_form(request, resource="supplier_price", form_class=SupplierPriceForm, service=services.save_supplier_price)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def supplier_price_edit(request, pk):
    return _reference_form(request, resource="supplier_price", form_class=SupplierPriceForm, service=services.save_supplier_price, pk=pk)


