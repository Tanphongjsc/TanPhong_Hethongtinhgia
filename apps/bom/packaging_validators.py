"""Packaging definitions only; no implicit scale, tree expansion or prices."""
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.core.models import Item, PackagingConfig, Product, Sku, SkuPackagingAssignment, Uom
from .constants import IMMUTABLE_STATUSES
from .packaging_constants import LEVELS, MEASUREMENTS
from .validators import normalize_values as normalize_definition_values, validate_conversions


def normalize_values(data, *, uppercase=("code",)):
    values = normalize_definition_values(data, uppercase=uppercase)
    for field in ("parent_level_code", "market_code", "artwork_code"):
        if field in values:
            values[field] = (values[field] or "").strip() or None
    return values


def _reference(errors, data, field, instance, *, organization=None, required=False, label):
    reference = data.get(field)
    if reference is None:
        if required:
            errors[field] = f"Vui lòng chọn {label}."
    elif organization is not None and reference.organization_id != organization.pk:
        errors[field] = "Danh mục không thuộc công ty hiện tại."
    elif not reference.is_active and reference.pk != getattr(instance, f"{field}_id", None):
        errors[field] = f"Không thể chọn {label} đã ngừng hoạt động."


def validate_config(*, data, organization, instance=None):
    errors = {}
    for field, label in (("code", "mã cấu hình bao bì"), ("name", "tên cấu hình bao bì")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label}."
    duplicates = PackagingConfig.objects.filter(organization=organization, code__iexact=data.get("code", ""))
    if instance and instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = "Mã cấu hình bao bì đã tồn tại."
    if not isinstance(data.get("product"), Product):
        errors["product"] = "Vui lòng chọn sản phẩm."
    else:
        _reference(errors, data, "product", instance, organization=organization, required=True, label="sản phẩm")
    if instance and instance.pk and "product" not in errors and data["product"].pk != instance.product_id:
        if instance.packagingconfigversion_set.filter(status__in=IMMUTABLE_STATUSES).exists() or instance.skupackagingassignment_set.exists():
            errors["product"] = "Không thể đổi sản phẩm vì cấu hình đã được gán SKU hoặc có phiên bản được chốt."
    if errors:
        raise ValidationError(errors)


def validate_version(*, data, organization, instance=None):
    errors = {}
    start, end = data.get("effective_from"), data.get("effective_to")
    if end and not start:
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu khi có ngày kết thúc hiệu lực."
    elif start and end and end <= start:
        errors["effective_to"] = "Ngày kết thúc hiệu lực phải sau ngày bắt đầu hiệu lực."
    for field in MEASUREMENTS:
        value = data.get(field)
        if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or value < 0):
            errors[field] = "Giá trị phải lớn hơn hoặc bằng 0."
    for field, dimension, measurements, label in (
        ("weight_uom", "MASS", ("gross_weight",), "đơn vị trọng lượng"),
        ("dimension_uom", "LENGTH", ("length", "width", "height"), "đơn vị kích thước"),
    ):
        unit = data.get(field)
        if unit is not None and not isinstance(unit, Uom):
            errors[field] = "Đơn vị tính không hợp lệ."
            continue
        _reference(errors, data, field, instance, label=label)
        if any(data.get(name) is not None for name in measurements) or unit is not None:
            if unit is None or unit.category.dimension_code != dimension:
                errors[field] = "Vui lòng chọn đơn vị thuộc đại lượng khối lượng." if dimension == "MASS" else "Vui lòng chọn đơn vị thuộc đại lượng chiều dài."
    if errors:
        raise ValidationError(errors)


def validate_line(*, data, organization, instance=None):
    errors = {}
    for field, model, label in (("packaging_item", Item, "vật tư bao bì"), ("uom", Uom, "đơn vị tính")):
        if not isinstance(data.get(field), model):
            errors[field] = f"Vui lòng chọn {label}."
        else:
            _reference(errors, data, field, instance, organization=organization if model is Item else None, required=True, label=label)
    for field, required, label in (("qty", True, "Số lượng"), ("units_per_parent", False, "Số đơn vị trong cấp cha")):
        value = data.get(field)
        if value is None and not required:
            continue
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            errors[field] = f"{label} phải lớn hơn 0."
    if data.get("level_code") not in dict(LEVELS):
        errors["level_code"] = "Vui lòng chọn cấp đóng gói hợp lệ."
    order = data.get("display_order")
    if not isinstance(order, int) or isinstance(order, bool) or not -2147483648 <= order <= 2147483647:
        errors["display_order"] = "Thứ tự không hợp lệ."
    if errors:
        raise ValidationError(errors)


def validate_assignment(*, data, organization, instance=None):
    errors = {}
    sku = data.get("sku")
    if not isinstance(sku, Sku):
        errors["sku"] = "Vui lòng chọn SKU."
    else:
        _reference(errors, data, "sku", instance, organization=organization, required=True, label="SKU")
        config = instance.packaging_config
        if sku.product_id != config.product_id or sku.product.organization_id != organization.pk:
            errors["sku"] = "SKU phải thuộc sản phẩm của cấu hình bao bì."
    start, end = data.get("effective_from"), data.get("effective_to")
    if not start:
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu hiệu lực."
    elif end and end <= start:
        errors["effective_to"] = "Ngày kết thúc hiệu lực phải sau ngày bắt đầu hiệu lực."
    if isinstance(sku, Sku) and start:
        duplicates = SkuPackagingAssignment.objects.filter(packaging_config=instance.packaging_config, sku=sku, effective_from=start)
        if instance.pk:
            duplicates = duplicates.exclude(pk=instance.pk)
        if duplicates.exists():
            errors["effective_from"] = "SKU đã được gán cấu hình này với cùng ngày bắt đầu."
    if errors:
        raise ValidationError(errors)
