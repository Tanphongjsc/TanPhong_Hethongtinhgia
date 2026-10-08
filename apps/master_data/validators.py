from django.core.exceptions import ValidationError
from django.db.models import Q

from decimal import Decimal

from apps.core.models import CostElement, Currency, Item, Supplier, Uom, UomCategory, UomConversion
from .constants import ACCOUNTING_SCOPES, COST_SCOPES, ROUNDING_MAX, ROUNDING_MIN, ROUNDING_MODES, SOURCE_MODES, VALUE_TYPES


def normalize_cost_element(data):
    values = dict(data)
    values["code"] = str(values.get("code") or "").strip().upper()
    values["name"] = str(values.get("name") or "").strip()
    for field in ("description", "dimension_code"):
        values[field] = (values.get(field) or "").strip() or None
    return values


def validate_cost_element(*, data, organization, instance=None):
    errors = {}
    if not data["code"]:
        errors["code"] = "Vui lòng nhập mã phần tử chi phí."
    if not data["name"]:
        errors["name"] = "Vui lòng nhập tên phần tử chi phí."
    for field, choices in (
        ("value_type", VALUE_TYPES), ("default_source_mode", SOURCE_MODES),
        ("accounting_scope", ACCOUNTING_SCOPES), ("cost_scope", COST_SCOPES),
        ("rounding_mode", ROUNDING_MODES),
    ):
        if data.get(field) not in dict(choices):
            errors[field] = "Giá trị không hợp lệ."
    scale = data.get("rounding_scale")
    if not isinstance(scale, int) or isinstance(scale, bool) or not ROUNDING_MIN <= scale <= ROUNDING_MAX:
        errors["rounding_scale"] = "Số chữ số làm tròn phải từ 0 đến 12."
    group = data.get("group")
    if group and group.organization_id != organization.pk:
        errors["group"] = "Nhóm không thuộc công ty hiện tại."
    for field in ("group", "currency_code", "default_uom"):
        reference = data.get(field)
        previous_id = getattr(instance, f"{field}_id", None)
        if reference and not reference.is_active and reference.pk != previous_id:
            errors[field] = "Không thể chọn danh mục đã ngừng hoạt động."
    if data.get("value_type") == "MONEY" and not data.get("currency_code"):
        errors["currency_code"] = "Giá trị tiền tệ cần khai báo đơn vị tiền tệ."
    if data.get("value_type") == "QUANTITY" and not data.get("default_uom"):
        errors["default_uom"] = "Giá trị số lượng cần khai báo đơn vị tính."
    uom = data.get("default_uom")
    if uom and data.get("dimension_code") and uom.category.dimension_code != data["dimension_code"]:
        errors["dimension_code"] = "Đại lượng phải phù hợp với nhóm đơn vị tính đã chọn."
    duplicates = CostElement.objects.filter(organization=organization, code__iexact=data["code"])
    if instance and instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = "Mã phần tử chi phí đã tồn tại trong công ty."
    if errors:
        raise ValidationError(errors)


def normalize_reference_values(data, *, uppercase=("code",)):
    values = dict(data)
    for field in ("code", "name", "symbol", "dimension_code", "description", "source_reference"):
        if field in values:
            value = (values[field] or "").strip()
            values[field] = value.upper() if field in uppercase else value
            if field in ("description", "source_reference"):
                values[field] = values[field] or None
    return values


def normalize_supplier_values(data, *, uppercase=("code",)):
    values = normalize_reference_values(data, uppercase=uppercase)
    for field in ("tax_code", "payment_terms", "source_type"):
        if field in values:
            values[field] = (values[field] or "").strip() or None
    return values


def _supplier_reference_error(errors, *, data, field, model, label, organization, instance, required=True):
    reference = data.get(field)
    if reference is None:
        if required:
            errors[field] = f"Vui lòng chọn {label}."
    elif not isinstance(reference, model):
        errors[field] = "Danh mục tham chiếu không hợp lệ."
    elif model in (Supplier, Item) and reference.organization_id != organization.pk:
        errors[field] = "Danh mục không thuộc công ty hiện tại."
    elif not reference.is_active and reference.pk != getattr(instance, f"{field}_id", None):
        errors[field] = f"Không thể chọn {label} đã ngừng hoạt động."


def validate_supplier(*, data, organization, instance=None):
    errors = {}
    for field, label in (("code", "mã nhà cung cấp"), ("name", "tên nhà cung cấp")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label}."
    duplicates = Supplier.objects.filter(organization=organization, code__iexact=data.get("code", ""))
    if instance and instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = "Mã nhà cung cấp đã tồn tại."
    _supplier_reference_error(errors, data=data, field="default_currency_code", model=Currency,
        label="tiền tệ", organization=organization, instance=instance, required=False)
    if errors:
        raise ValidationError(errors)


def validate_supplier_price(*, data, organization, instance=None):
    errors = {}
    for field, model, label in (
        ("supplier", Supplier, "nhà cung cấp"), ("item", Item, "vật tư / hàng hóa"),
        ("price_uom", Uom, "đơn vị tính"), ("currency_code", Currency, "tiền tệ"),
    ):
        _supplier_reference_error(errors, data=data, field=field, model=model, label=label,
            organization=organization, instance=instance)
    for field, label in (("unit_price", "Đơn giá"), ("min_qty", "Số lượng tối thiểu")):
        value = data.get(field)
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            errors[field] = f"{label} phải lớn hơn hoặc bằng 0."
    for field, label in (("tax_rate", "Tỷ lệ thuế"), ("tax_recoverable_ratio", "Tỷ lệ thuế được khấu trừ")):
        value = data.get(field)
        if field == "tax_rate" and value is None:
            continue
        if not isinstance(value, Decimal) or not value.is_finite() or not 0 <= value <= 1:
            errors[field] = f"{label} phải từ 0 đến 1."
    start, end = data.get("effective_from"), data.get("effective_to")
    if not start:
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu hiệu lực."
    if start and end and end <= start:
        errors["effective_to"] = "Ngày kết thúc hiệu lực phải sau ngày bắt đầu hiệu lực."
    # PostgreSQL has no uniqueness/exclusion rule for quantity breaks or periods.
    if errors:
        raise ValidationError(errors)


def _coded_reference_errors(model, data, instance):
    errors = {}
    for field in ("code", "name"):
        if not data.get(field):
            errors[field] = "Trường này là bắt buộc."
    duplicates = model.objects.filter(code__iexact=data.get("code", ""))
    if instance and not instance._state.adding:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = "Mã đã tồn tại trong danh mục."
    return errors


def validate_currency(*, data, instance=None, **context):
    errors = _coded_reference_errors(Currency, data, instance)
    if len(data.get("code", "")) != 3:
        errors["code"] = "Mã tiền tệ phải có đúng 3 ký tự."
    decimal_places = data.get("decimal_places")
    if not isinstance(decimal_places, int) or isinstance(decimal_places, bool) or not 0 <= decimal_places <= 8:
        errors["decimal_places"] = "Số chữ số thập phân phải từ 0 đến 8."
    if instance and not instance._state.adding and data.get("code") != instance.pk:
        errors["code"] = "Không được thay đổi mã tiền tệ của bản ghi đã tồn tại."
    if errors:
        raise ValidationError(errors)


def validate_uom_category(*, data, instance=None, **context):
    errors = _coded_reference_errors(UomCategory, data, instance)
    if not data.get("dimension_code"):
        errors["dimension_code"] = "Vui lòng nhập mã đại lượng."
    if errors:
        raise ValidationError(errors)


def _inactive_reference_error(errors, *, data, field, instance):
    reference = data.get(field)
    retained_id = getattr(instance, f"{field}_id", None)
    if reference and not reference.is_active and reference.pk != retained_id:
        errors[field] = "Không thể chọn danh mục đã ngừng hoạt động."


def validate_uom(*, data, instance=None, **context):
    errors = _coded_reference_errors(Uom, data, instance)
    if not data.get("symbol"):
        errors["symbol"] = "Vui lòng nhập ký hiệu đơn vị đo."
    precision = data.get("precision")
    if not isinstance(precision, int) or isinstance(precision, bool) or not 0 <= precision <= 12:
        errors["precision"] = "Độ chính xác phải từ 0 đến 12."
    category = data.get("category")
    if not category:
        errors["category"] = "Vui lòng chọn nhóm đơn vị đo."
    _inactive_reference_error(errors, data=data, field="category", instance=instance)
    if instance and instance.pk and category and category.pk != instance.category_id:
        # Preserve the same-category rule for already saved general conversions.
        incompatible = UomConversion.objects.filter(item__isnull=True).filter(
            Q(from_uom=instance) & ~Q(to_uom__category=category)
            | Q(to_uom=instance) & ~Q(from_uom__category=category)
        )
        if incompatible.exists():
            errors["category"] = "Đổi nhóm sẽ làm quy đổi chung hiện có khác nhóm đơn vị tính. Vui lòng điều chỉnh quy đổi trước."
    # No one-base-unit policy: it is absent from canonical docs and database.
    if errors:
        raise ValidationError(errors)


def validate_uom_conversion(*, data, organization, instance=None):
    errors = {}
    from_uom, to_uom, item = (data.get(field) for field in ("from_uom", "to_uom", "item"))
    if not from_uom:
        errors["from_uom"] = "Vui lòng chọn đơn vị nguồn."
    if not to_uom:
        errors["to_uom"] = "Vui lòng chọn đơn vị đích."
    if from_uom and to_uom:
        if from_uom.pk == to_uom.pk:
            errors["to_uom"] = "Đơn vị nguồn và đơn vị đích phải khác nhau."
        if item is None and from_uom.category_id != to_uom.category_id:
            errors["to_uom"] = "Quy đổi chung phải sử dụng các đơn vị cùng nhóm đơn vị tính."
    factor = data.get("factor")
    if not isinstance(factor, Decimal) or not factor.is_finite() or factor <= 0:
        errors["factor"] = "Hệ số quy đổi phải lớn hơn 0."
    start, end = data.get("effective_from"), data.get("effective_to")
    if not start:
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu hiệu lực."
    if start and end and end <= start:
        errors["effective_to"] = "Ngày kết thúc phải sau ngày bắt đầu hiệu lực."
    if item and item.organization_id != organization.pk:
        errors["item"] = "Vật tư / hàng hóa không thuộc công ty hiện tại."
    for field in ("from_uom", "to_uom", "item"):
        _inactive_reference_error(errors, data=data, field=field, instance=instance)
    # No duplicate/overlap rule: production has no unique/exclusion constraint.
    if errors:
        raise ValidationError(errors)
