"""Recipe definitions only: no price lookup, expansion or costing calculations."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import Item, Product, Recipe, Uom, UomConversion
from apps.master_data.validators import normalize_reference_values
from .constants import EDITABLE_STATUSES, IMMUTABLE_STATUSES


def normalize_values(data, *, uppercase=("code",)):
    values = normalize_reference_values(data, uppercase=uppercase)
    for field in ("operation_code", "substitute_group", "notes", "change_reason"):
        if field in values:
            values[field] = (values[field] or "").strip() or None
    return values


def ensure_editable(version):
    if version.status not in EDITABLE_STATUSES:
        raise ValidationError("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới.")


def _reference(errors, *, data, field, model, instance, organization=None, label):
    reference = data.get(field)
    if reference is None:
        errors[field] = f"Vui lòng chọn {label}."
    elif not isinstance(reference, model):
        errors[field] = "Danh mục tham chiếu không hợp lệ."
    elif organization is not None and reference.organization_id != organization.pk:
        errors[field] = "Danh mục không thuộc công ty hiện tại."
    elif not reference.is_active and reference.pk != getattr(instance, f"{field}_id", None):
        errors[field] = f"Không thể chọn {label} đã ngừng hoạt động."


def _decimal(errors, data, field, label, *, positive=False, maximum=None, exclusive_max=False):
    value = data.get(field)
    if not isinstance(value, Decimal) or not value.is_finite() or (value <= 0 if positive else value < 0):
        errors[field] = f"{label} phải {'lớn hơn 0' if positive else 'lớn hơn hoặc bằng 0'}."
    elif maximum is not None and (value >= maximum if exclusive_max else value > maximum):
        errors[field] = f"{label} phải {'nhỏ hơn' if exclusive_max else 'không vượt quá'} 100%."


def validate_recipe(*, data, organization, instance=None):
    errors = {}
    for field, label in (("code", "mã định mức"), ("name", "tên định mức")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label}."
    duplicates = Recipe.objects.filter(organization=organization, code__iexact=data.get("code", ""))
    if instance and instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = "Mã định mức đã tồn tại."
    _reference(errors, data=data, field="product", model=Product, instance=instance, organization=organization, label="sản phẩm")
    if instance and instance.pk and "product" not in errors and data["product"].pk != instance.product_id:
        if instance.recipeversion_set.filter(status__in=IMMUTABLE_STATUSES).exists():
            errors["product"] = "Không thể đổi sản phẩm vì định mức đã có phiên bản được chốt."
    if errors:
        raise ValidationError(errors)


def validate_version(*, data, organization, instance=None):
    errors = {}
    _reference(errors, data=data, field="output_uom", model=Uom, instance=instance, label="đơn vị tính đầu ra")
    _decimal(errors, data, "output_qty", "Sản lượng chuẩn", positive=True)
    _decimal(errors, data, "yield_rate", "Tỷ lệ thu hồi", positive=True, maximum=Decimal(1))
    start, end = data.get("effective_from"), data.get("effective_to")
    if end and not start:
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu khi có ngày kết thúc hiệu lực."
    elif start and end and end <= start:
        errors["effective_to"] = "Ngày kết thúc hiệu lực phải sau ngày bắt đầu hiệu lực."
    if errors:
        raise ValidationError(errors)


def validate_line(*, data, organization, instance=None):
    errors = {}
    _reference(errors, data=data, field="component_item", model=Item, instance=instance, organization=organization, label="vật tư / hàng hóa")
    _reference(errors, data=data, field="uom", model=Uom, instance=instance, label="đơn vị tính")
    _decimal(errors, data, "qty", "Số lượng", positive=True)
    _decimal(errors, data, "scrap_rate", "Tỷ lệ hao hụt", maximum=Decimal(1), exclusive_max=True)
    order = data.get("display_order")
    if not isinstance(order, int) or isinstance(order, bool) or not -2147483648 <= order <= 2147483647:
        errors["display_order"] = "Thứ tự không hợp lệ."
    if errors:
        raise ValidationError(errors)


def validate_conversions(*, lines, organization, effective_from=None):
    """One bounded query for direct pairs; no factor selection or chain resolver.

    `lines` contains (Item, Uom). Both directions are accepted. General
    conversions must remain in one category; item-specific pairs may cross it.
    """
    pairs = [(item, unit) for item, unit in lines if item.base_uom_id != unit.pk]
    if not pairs:
        return
    date = effective_from or timezone.localdate()
    units = {unit.pk for _, unit in pairs} | {item.base_uom_id for item, _ in pairs}
    items = {item.pk for item, _ in pairs}
    conversions = UomConversion.objects.filter(
        Q(organization=organization) | Q(organization__isnull=True),
        Q(item_id__in=items) | Q(item__isnull=True, from_uom__category_id=F("to_uom__category_id")),
        Q(effective_to__isnull=True) | Q(effective_to__gte=date),
        from_uom_id__in=units, to_uom_id__in=units, effective_from__lte=date,
    ).values_list("from_uom_id", "to_uom_id", "item_id")
    available = set(conversions)
    for item, unit in pairs:
        if not any(pair in available for pair in (
            (unit.pk, item.base_uom_id, item.pk), (item.base_uom_id, unit.pk, item.pk),
            (unit.pk, item.base_uom_id, None), (item.base_uom_id, unit.pk, None),
        )):
            raise ValidationError(f"{item.code}: không tìm thấy quy đổi đơn vị phù hợp tại ngày {date:%d/%m/%Y}.")
