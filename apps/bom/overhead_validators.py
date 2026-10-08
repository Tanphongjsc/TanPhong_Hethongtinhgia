"""Validate configuration, without resolving targets or performing allocation."""
from datetime import date

from django.core.exceptions import ValidationError

from apps.core.models import AllocationRule, CostPool, Uom
from apps.master_data.validators import normalize_reference_values
from .overhead_constants import ALLOCATION_BASES, POOL_TYPES


def normalize_overhead_values(data, *, uppercase=("code",)):
    values = normalize_reference_values(data, uppercase=uppercase)
    if "formula_code" in values:
        values["formula_code"] = (values["formula_code"] or "").strip() or None
    return values


def _identity(errors, *, model, data, organization, instance, noun):
    for field, label in (("code", "mã"), ("name", "tên")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label} {noun}."
    duplicates = model.objects.filter(organization=organization, code__iexact=data.get("code", ""))
    if instance and instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = f"Mã {noun} đã tồn tại."


def validate_cost_pool(*, data, organization, instance=None):
    errors = {}
    _identity(errors, model=CostPool, data=data, organization=organization, instance=instance, noun="nhóm chi phí")
    if data.get("pool_type") not in dict(POOL_TYPES):
        errors["pool_type"] = "Vui lòng chọn loại nhóm chi phí hợp lệ."
    if errors:
        raise ValidationError(errors)


def validate_allocation_rule(*, data, organization, instance=None):
    errors = {}
    _identity(errors, model=AllocationRule, data=data, organization=organization, instance=instance, noun="quy tắc phân bổ")
    pool = data.get("pool")
    if not isinstance(pool, CostPool) or pool.organization_id != organization.pk:
        errors["pool"] = "Vui lòng chọn nhóm chi phí hợp lệ."
    elif not pool.is_active and pool.pk != getattr(instance, "pool_id", None):
        errors["pool"] = "Không thể chọn nhóm chi phí đã ngừng hoạt động."
    if data.get("basis_type") not in dict(ALLOCATION_BASES):
        errors["basis_type"] = "Vui lòng chọn tiêu thức phân bổ hợp lệ."
    unit = data.get("basis_uom")
    if unit is not None:
        if not isinstance(unit, Uom):
            errors["basis_uom"] = "Vui lòng chọn đơn vị tiêu thức hợp lệ."
        elif not unit.is_active and unit.pk != getattr(instance, "basis_uom_id", None):
            errors["basis_uom"] = "Không thể chọn đơn vị đã ngừng hoạt động."
    priority = data.get("priority")
    if not isinstance(priority, int) or isinstance(priority, bool) or not -2147483648 <= priority <= 2147483647:
        errors["priority"] = "Mức ưu tiên phải là số nguyên trong phạm vi cho phép."
    start, end = data.get("effective_from"), data.get("effective_to")
    if not isinstance(start, date):
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu hiệu lực hợp lệ."
    if end is not None:
        if not isinstance(end, date):
            errors["effective_to"] = "Vui lòng nhập ngày hết hiệu lực hợp lệ."
        elif isinstance(start, date) and end <= start:
            errors["effective_to"] = "Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực."
    if errors:
        raise ValidationError(errors)
