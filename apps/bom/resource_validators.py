"""Resource rules shared by forms and transactional services; no cost calculation."""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.core.models import Currency, Resource, Uom, WorkCenter
from apps.master_data.validators import normalize_reference_values
from .resource_constants import RESOURCE_TYPES


def normalize_resource_values(data, *, uppercase=("code",)):
    values = normalize_reference_values(data, uppercase=uppercase)
    if "rate_type" in values:
        values["rate_type"] = (values["rate_type"] or "").strip()
    for field in ("site_code", "source_reference"):
        if field in values:
            values[field] = (values[field] or "").strip() or None
    return values


def _reference(errors, data, field, model, organization, instance, *, required=False):
    reference = data.get(field)
    if reference is None:
        if required:
            errors[field] = "Vui lòng chọn danh mục tham chiếu."
        return
    if not isinstance(reference, model) or (model in (WorkCenter, Resource) and reference.organization_id != organization.pk):
        errors[field] = "Danh mục tham chiếu không hợp lệ."
    elif not reference.is_active and reference.pk != getattr(instance, f"{field}_id", None):
        errors[field] = "Không thể chọn danh mục đã ngừng hoạt động."


def _nonnegative(errors, data, field):
    value = data.get(field)
    if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or value < 0):
        errors[field] = "Giá trị phải lớn hơn hoặc bằng 0."


def _catalog_errors(model, data, organization, instance):
    errors = {}
    for field in ("code", "name"):
        if not data.get(field):
            errors[field] = "Trường này là bắt buộc."
    query = model.objects.filter(organization=organization, code__iexact=data.get("code", ""))
    if instance and instance.pk:
        query = query.exclude(pk=instance.pk)
    if query.exists():
        errors["code"] = "Mã trung tâm sản xuất đã tồn tại." if model is WorkCenter else "Mã nguồn lực đã tồn tại."
    return errors


def _capacity(errors, data, organization, instance, fields):
    for field in fields:
        _nonnegative(errors, data, field)
    _reference(errors, data, "capacity_uom", Uom, organization, instance,
        required=any(data.get(field) is not None for field in fields))


def validate_work_center(*, data, organization, instance=None):
    errors = _catalog_errors(WorkCenter, data, organization, instance)
    _capacity(errors, data, organization, instance, ("capacity_value", "normal_capacity_value"))
    if errors:
        raise ValidationError(errors)


def validate_resource(*, data, organization, instance=None):
    errors = _catalog_errors(Resource, data, organization, instance)
    if data.get("resource_type") not in dict(RESOURCE_TYPES):
        errors["resource_type"] = "Vui lòng chọn loại nguồn lực hợp lệ."
    _reference(errors, data, "work_center", WorkCenter, organization, instance)
    _capacity(errors, data, organization, instance, ("capacity_value",))
    if errors:
        raise ValidationError(errors)


def validate_resource_rate(*, data, organization, instance=None):
    errors = {}
    for field, model in (("resource", Resource), ("currency_code", Currency), ("per_uom", Uom)):
        _reference(errors, data, field, model, organization, instance, required=True)
    rate_type = data.get("rate_type")
    if not isinstance(rate_type, str) or not rate_type.strip():
        errors["rate_type"] = "Vui lòng nhập mã loại đơn giá."
    if data.get("amount") is None:
        errors["amount"] = "Vui lòng nhập đơn giá."
    _nonnegative(errors, data, "amount")
    start, end = data.get("effective_from"), data.get("effective_to")
    if not isinstance(start, date):
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu hiệu lực hợp lệ."
    if end is not None:
        if not isinstance(end, date):
            errors["effective_to"] = "Ngày kết thúc không hợp lệ."
        elif isinstance(start, date) and end <= start:
            errors["effective_to"] = "Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực."
    if errors:
        raise ValidationError(errors)
