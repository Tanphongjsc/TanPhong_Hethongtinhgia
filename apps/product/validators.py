"""Company-scoped master data rules shared by forms and write services."""
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.core.models import Item, Product, ProductCategory, Sku, Uom
from apps.master_data.validators import normalize_reference_values
from .constants import ITEM_TYPES, MEASUREMENT_FIELDS, PRODUCT_UNIT_FIELDS, SKU_UNIT_FIELDS, UNIT_FIELDS


def normalize_product_values(data, *, uppercase=("code",)):
    values = normalize_reference_values(data, uppercase=uppercase)
    if "tax_class_code" in values:
        values["tax_class_code"] = (values["tax_class_code"] or "").strip() or None
    if "barcode" in values:
        # Empty barcodes are NULL, so uq_sku_barcode allows multiple omissions.
        # Preserve casing: barcodes are identifiers, not business codes.
        values["barcode"] = (values["barcode"] or "").strip() or None
    return values


def _catalog_errors(model, data, organization, instance):
    errors = {}
    for field in ("code", "name"):
        if not data.get(field):
            errors[field] = "Trường này là bắt buộc."
    duplicates = model.objects.filter(organization=organization, code__iexact=data.get("code", ""))
    if instance and instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = {Product: "Mã sản phẩm đã tồn tại.", Sku: "Mã SKU đã tồn tại."}.get(model, "Mã này đã tồn tại.")
    return errors


def validate_category(*, data, organization, instance=None):
    errors = _catalog_errors(ProductCategory, data, organization, instance)
    if errors:
        raise ValidationError(errors)


def validate_item(*, data, organization, instance=None):
    errors = _catalog_errors(Item, data, organization, instance)
    if data.get("item_type") not in dict(ITEM_TYPES):
        errors["item_type"] = "Loại vật tư / hàng hóa không hợp lệ."
    if not data.get("base_uom"):
        errors["base_uom"] = "Vui lòng chọn đơn vị tính."
    category = data.get("category")
    if category:
        if not isinstance(category, ProductCategory) or category.organization_id != organization.pk:
            errors["category"] = "Nhóm sản phẩm không thuộc công ty hiện tại."
        elif not category.is_active and category.pk != getattr(instance, "category_id", None):
            errors["category"] = "Không thể chọn nhóm sản phẩm đã ngừng hoạt động."
    for field in UNIT_FIELDS:
        unit = data.get(field)
        if unit is None:
            continue
        if not isinstance(unit, Uom):
            errors[field] = "Đơn vị tính không hợp lệ."
        elif not unit.is_active and unit.pk != getattr(instance, f"{field}_id", None):
            errors[field] = "Không thể chọn đơn vị tính đã ngừng hoạt động."
    for field in MEASUREMENT_FIELDS:
        value = data.get(field)
        if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or value < 0):
            errors[field] = "Giá trị phải lớn hơn hoặc bằng 0."
    net, gross = data.get("net_weight"), data.get("gross_weight")
    if "net_weight" not in errors and "gross_weight" not in errors and net is not None and gross is not None and gross < net:
        errors["gross_weight"] = "Khối lượng tổng không được nhỏ hơn khối lượng tịnh."
    for fields, unit_field, dimension, message in (
        (("net_weight", "gross_weight"), "weight_uom", "MASS", "Vui lòng chọn đơn vị tính thuộc đại lượng khối lượng."),
        (("length", "width", "height"), "dimension_uom", "LENGTH", "Vui lòng chọn đơn vị tính thuộc đại lượng chiều dài."),
    ):
        unit = data.get(unit_field)
        has_value = any(data.get(field) is not None for field in fields)
        if unit_field not in errors and (has_value or unit is not None):
            if not unit or unit.category.dimension_code != dimension:
                errors[unit_field] = message
    if errors:
        raise ValidationError(errors)


def _validate_reference(errors, *, data, field, model, label, instance, organization=None, required=False):
    reference = data.get(field)
    if reference is None:
        if required:
            errors[field] = f"Vui lòng chọn {label}."
        return
    if not isinstance(reference, model):
        errors[field] = f"{label.capitalize()} không hợp lệ."
    elif organization is not None and reference.organization_id != organization.pk:
        errors[field] = f"{label.capitalize()} không thuộc công ty hiện tại."
    elif not reference.is_active and reference.pk != getattr(instance, f"{field}_id", None):
        errors[field] = f"Không thể chọn {label} đã ngừng hoạt động."


def validate_product(*, data, organization, instance=None):
    errors = _catalog_errors(Product, data, organization, instance)
    for field, label in (("code", "mã sản phẩm"), ("name", "tên sản phẩm")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label}."
    _validate_reference(errors, data=data, field="category", model=ProductCategory, label="nhóm sản phẩm", instance=instance, organization=organization)
    _validate_reference(errors, data=data, field="output_item", model=Item, label="vật tư / hàng hóa đầu ra", instance=instance, organization=organization)
    for field in PRODUCT_UNIT_FIELDS:
        _validate_reference(errors, data=data, field=field, model=Uom, label="đơn vị tính giá thành", instance=instance, required=True)
    if errors:
        raise ValidationError(errors)


def validate_sku(*, data, organization, instance=None):
    errors = _catalog_errors(Sku, data, organization, instance)
    for field, label in (("code", "mã SKU"), ("name", "tên SKU")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label}."
    _validate_reference(errors, data=data, field="product", model=Product, label="sản phẩm", instance=instance, organization=organization, required=True)
    _validate_reference(errors, data=data, field="sell_item", model=Item, label="vật tư / hàng hóa bán", instance=instance, organization=organization)
    for field, label in zip(SKU_UNIT_FIELDS, ("đơn vị bán", "đơn vị lượng tịnh")):
        _validate_reference(errors, data=data, field=field, model=Uom, label=label, instance=instance, required=True)
    quantity = data.get("net_quantity")
    if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0:
        errors["net_quantity"] = "Lượng tịnh phải lớn hơn 0."
    barcode = data.get("barcode")
    if barcode:
        duplicates = Sku.objects.filter(organization=organization, barcode=barcode)
        if instance and instance.pk:
            duplicates = duplicates.exclude(pk=instance.pk)
        if duplicates.exists():
            errors["barcode"] = "Mã vạch đã tồn tại."
    # No implicit mass-only or conversion rule: quantity UoM may be MASS,
    # VOLUME, COUNT, etc. Recipe/packaging remain separate from this master.
    if errors:
        raise ValidationError(errors)
