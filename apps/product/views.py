from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.vary import vary_on_headers

from apps.master_data.access import require_access
from apps.master_data.constants import PAGE_SIZES
from apps.master_data.presentation import display_label, format_number
from apps.master_data.ui_helpers import is_htmx, add_form_error, saved_response
from . import selectors, services
from .forms import ItemForm, ProductCategoryForm, ProductForm, SkuForm

CATALOG_PAGES = {
    "product_category": {
        "route": "category", "label": "nhóm sản phẩm", "title": "Danh mục nhóm sản phẩm",
        "description": "Quản lý nhóm dùng để phân loại vật tư / hàng hóa và sản phẩm.",
        "columns": (("code", "Mã", False), ("name", "Tên nhóm sản phẩm", False), (None, "Mô tả", False), (None, "Trạng thái", False)),
        "sorts": (("code", "Mã"), ("name", "Tên"), ("created_at", "Ngày tạo")),
        "selector": selectors.category_list, "form": ProductCategoryForm, "service": services.save_category,
    },
    "item": {
        "route": "item", "label": "vật tư / hàng hóa", "title": "Danh mục vật tư / hàng hóa",
        "description": "Quản lý nguyên liệu, bao bì, bán thành phẩm, thành phẩm, dịch vụ và phụ phẩm.",
        "columns": (("code", "Mã", False), ("name", "Tên", False), ("item_type", "Loại", False),
            (None, "Nhóm sản phẩm", False), (None, "Đơn vị cơ sở", False), (None, "Đơn vị mua", False),
            (None, "Đơn vị sản xuất", False), (None, "Hàng tồn kho", False), (None, "Trạng thái", False)),
        "sorts": (("code", "Mã"), ("name", "Tên"), ("item_type", "Loại"), ("created_at", "Ngày tạo")),
        "selector": selectors.item_list, "form": ItemForm, "service": services.save_item,
    },
    "product": {
        "route": "product", "label": "sản phẩm", "title": "Danh mục sản phẩm",
        "description": "Quản lý sản phẩm gốc, nhóm sản phẩm và đơn vị tính giá thành.",
        "columns": (("code", "Mã", False), ("name", "Tên sản phẩm", False), ("category", "Nhóm sản phẩm", False),
            (None, "Đơn vị tính giá thành", False), (None, "Trạng thái", False), ("created_at", "Ngày tạo", False)),
        "sorts": (("code", "Mã"), ("name", "Tên"), ("category", "Nhóm sản phẩm"), ("created_at", "Ngày tạo")),
        "search_placeholder": "Tìm theo mã, tên hoặc mô tả…",
        "selector": selectors.product_list, "form": ProductForm, "service": services.save_product,
    },
    "sku": {
        "route": "sku", "label": "SKU", "title": "Danh mục SKU",
        "description": "Quản lý mã bán cụ thể, sản phẩm gốc và lượng tịnh trên một đơn vị bán.",
        "columns": (("code", "Mã SKU", False), ("name", "Tên SKU", False), ("product", "Sản phẩm", False),
            (None, "Lượng tịnh", True), (None, "Đơn vị lượng tịnh", False), (None, "Đơn vị bán", False), (None, "Trạng thái", False)),
        "sorts": (("code", "Mã SKU"), ("name", "Tên SKU"), ("product", "Sản phẩm"), ("created_at", "Ngày tạo")),
        "search_placeholder": "Tìm mã SKU, tên SKU hoặc sản phẩm…",
        "selector": selectors.sku_list, "form": SkuForm, "service": services.save_sku,
    },
}


def _context(request, resource):
    page = CATALOG_PAGES[resource]
    request.costing_resource_label = page["label"]
    route = page["route"]
    list_url = reverse(f"product:{route}_list")
    return {
        "resource": resource, "resource_label": page["label"], "page_title": page["title"],
        "page_description": page["description"], "list_url": list_url,
        "breadcrumbs": (("Dữ liệu danh mục", None), (page["title"], list_url)),
        "columns": page["columns"], "column_count": len(page["columns"]) + 1,
        "table_id": "reference-data-table", "filter_form_id": "reference-data-filters",
        "search_id": "reference-data-search", "search_placeholder": page.get("search_placeholder", "Tìm theo mã, tên hoặc mô tả…" if resource == "product_category" else "Tìm theo mã hoặc tên…"),
        "detail_url_name": f"product:{route}_detail", "edit_url_name": f"product:{route}_edit",
        "rows_template": f"product/partials/{route}_rows.html",
    }


def _list(request, resource):
    context = _context(request, resource)
    workspace = require_access(request, resource=resource)
    page, sort, per_page = CATALOG_PAGES[resource]["selector"](organization=workspace.organization, filters=request.GET)
    options = tuple({"name": name, "label": label, "choices": choices,
        "selected": request.GET.get(name, request.GET.get("is_active", "") if name == "active" else "")}
        for name, label, choices in selectors.product_filter_options(resource=resource, organization=workspace.organization))
    context.update(page_obj=page, records=page.object_list, current_sort=sort, per_page=per_page,
        filters=request.GET, page_sizes=PAGE_SIZES, filter_options=options,
        has_filters=any(request.GET.get(name) for name in ("q", "is_active", *(option["name"] for option in options))),
        sort_options=tuple((prefix + field, label + (" ↓" if prefix else " ↑")) for field, label in CATALOG_PAGES[resource]["sorts"] for prefix in ("", "-")),
        can_edit=getattr(workspace.permissions, f"can_edit_{resource}"),
        primary_action_url=reverse(f"product:{CATALOG_PAGES[resource]['route']}_create") if getattr(workspace.permissions, f"can_create_{resource}") else None,
        primary_action_label="+ Thêm mới")
    return render(request, "master_data/partials/reference_data_table.html" if is_htmx(request) else "product/catalog_list.html", context)


def _field(label, value, *, numeric=False, technical=False):
    return {"label": label, "value": format_number(value) if numeric else value, "numeric": numeric, "technical": technical}


def _unit(unit):
    return f"{unit.name} ({unit.symbol})" if unit else "—"


def _company_reference(reference, organization):
    return f"{reference.code} — {reference.name}" if reference and reference.organization_id == organization.pk else "—"


def _detail(request, resource, pk):
    context = _context(request, resource)
    workspace = require_access(request, resource=resource)
    record = selectors.product_detail(resource=resource, organization=workspace.organization, pk=pk)
    if resource == "product_category":
        sections = (("Thông tin nhóm sản phẩm", (
            _field("Mã", record.code, technical=True), _field("Tên nhóm sản phẩm", record.name), _field("Mô tả", record.description),
        )),)
    elif resource == "item":
        category = f"{record.category.code} — {record.category.name}" if record.category and record.category.organization_id == workspace.organization.pk else "—"
        sections = (
            ("Thông tin chung", (_field("Mã", record.code, technical=True), _field("Tên", record.name), _field("Loại vật tư / hàng hóa", display_label(record.item_type)), _field("Nhóm sản phẩm", category))),
            ("Đơn vị tính", tuple(_field(label, _unit(getattr(record, field))) for field, label in (("base_uom", "Đơn vị cơ sở"), ("purchase_uom", "Đơn vị mua"), ("production_uom", "Đơn vị sản xuất")))),
            ("Thuế", (_field("Mã nhóm thuế", record.tax_class_code, technical=True),)),
            ("Trọng lượng", (_field("Khối lượng tịnh", record.net_weight, numeric=True), _field("Khối lượng tổng", record.gross_weight, numeric=True), _field("Đơn vị trọng lượng", _unit(record.weight_uom)))),
            ("Kích thước", tuple(_field(label, getattr(record, field), numeric=True) for field, label in (("length", "Chiều dài"), ("width", "Chiều rộng"), ("height", "Chiều cao"))) + (_field("Đơn vị kích thước", _unit(record.dimension_uom)),)),
            ("Quản lý", (_field("Hàng tồn kho", "Có quản lý tồn kho" if record.is_stock_item else "Không quản lý tồn kho"),)),
        )
    elif resource == "product":
        sections = (
            ("Thông tin chung", (_field("Mã sản phẩm", record.code, technical=True), _field("Tên sản phẩm", record.name),
                _field("Nhóm sản phẩm", _company_reference(record.category, workspace.organization)), _field("Mô tả", record.description))),
            ("Đơn vị tính", (_field("Đơn vị tính giá thành", _unit(record.costing_uom)),)),
            ("Liên kết và thuế", (_field("Vật tư / Hàng hóa đầu ra", _company_reference(record.output_item, workspace.organization)), _field("Mã nhóm thuế", record.tax_class_code, technical=True))),
        )
    else:
        sections = (
            ("Thông tin chung", (_field("Mã SKU", record.code, technical=True), _field("Tên SKU", record.name),
                _field("Sản phẩm", _company_reference(record.product, workspace.organization)), _field("Mã vạch", record.barcode, technical=True))),
            ("Quy cách", (_field("Đơn vị bán", _unit(record.sales_uom)), _field("Lượng tịnh", record.net_quantity, numeric=True), _field("Đơn vị lượng tịnh", _unit(record.net_quantity_uom)))),
            ("Liên kết hàng hóa", (_field("Vật tư / Hàng hóa bán", _company_reference(record.sell_item, workspace.organization)),)),
        )
    context.update(record=record, page_title=record.name, detail_sections=sections,
        primary_action_url=reverse(context["edit_url_name"], args=[record.pk]) if getattr(workspace.permissions, f"can_edit_{resource}") else None,
        primary_action_label="Chỉnh sửa")
    return render(request, "product/partials/catalog_detail_content.html" if is_htmx(request) else "product/catalog_detail.html", context)


def _form(request, resource, pk=None):
    context = _context(request, resource)
    workspace = require_access(request, "edit" if pk is not None else "create", resource=resource)
    record = selectors.product_detail(resource=resource, organization=workspace.organization, pk=pk) if pk is not None else None
    page = CATALOG_PAGES[resource]
    form = page["form"](request.POST if request.method == "POST" else None, workspace=workspace, instance=record)
    if request.method == "POST" and form.is_valid():
        try:
            saved = page["service"](workspace=workspace, data=form.cleaned_data, instance=record)
        except ValidationError as error:
            add_form_error(form, error)
        else:
            messages.success(request, f"Đã {'cập nhật' if record else 'tạo'} {page['label']}.")
            destination = reverse(context["detail_url_name"], args=[saved.pk])
            return saved_response(request, destination)
    if form.is_bound:
        form.mark_errors()
    context.update(form=form, record=record, page_title=f"{'Chỉnh sửa' if record else 'Thêm mới'} {page['label']}",
        cancel_url=reverse(context["detail_url_name"], args=[record.pk]) if record else context["list_url"])
    return render(request, "master_data/partials/reference_data_form_content.html" if is_htmx(request) else "product/catalog_form.html", context)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def category_list(request):
    return _list(request, "product_category")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def category_detail(request, pk):
    return _detail(request, "product_category", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def category_create(request):
    return _form(request, "product_category")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def category_edit(request, pk):
    return _form(request, "product_category", pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def item_list(request):
    return _list(request, "item")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def item_detail(request, pk):
    return _detail(request, "item", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def item_create(request):
    return _form(request, "item")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def item_edit(request, pk):
    return _form(request, "item", pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def product_list(request):
    return _list(request, "product")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def product_detail(request, pk):
    return _detail(request, "product", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def product_create(request):
    return _form(request, "product")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def product_edit(request, pk):
    return _form(request, "product", pk)


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def sku_list(request):
    return _list(request, "sku")


@require_GET
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def sku_detail(request, pk):
    return _detail(request, "sku", pk)


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def sku_create(request):
    return _form(request, "sku")


@require_http_methods(["GET", "POST"])
@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def sku_edit(request, pk):
    return _form(request, "sku", pk)
