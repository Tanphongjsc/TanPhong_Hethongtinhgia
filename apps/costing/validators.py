"""Input invariants; configuration analysis lives in configuration.py."""
from django.core.exceptions import ValidationError
from apps.core.models import CostingScheme, CostingSchemeLine
from apps.master_data.validators import normalize_reference_values
from .constants import EDITABLE_STATUSES, LINE_TYPES, VISIBILITY_SCOPES, SOURCE_MODES, COST_SCOPES


def normalize_values(data, *, uppercase=("code",)):
    values = normalize_reference_values(data, uppercase=uppercase)
    for name in ("purpose", "context_scope", "line_code", "label", "system_resolver_code", "external_adapter_code", "notes", "change_reason"):
        if name in values:
            value = (values[name] or "").strip()
            values[name] = value.upper() if name in uppercase else value
            if name not in ("purpose", "context_scope", "line_code", "label"):
                values[name] = values[name] or None
    return values


def ensure_editable(version):
    if version.status not in EDITABLE_STATUSES:
        raise ValidationError("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới.")


def validate_version(*, data, organization=None, instance=None):
    start, end = data.get("effective_from"), data.get("effective_to")
    if end and not start:
        raise ValidationError({"effective_from": "Vui lòng nhập ngày bắt đầu hiệu lực."})
    if start and end and end <= start:
        raise ValidationError({"effective_to": "Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực."})


def validate_scheme(*, data, organization, instance=None):
    errors = {}
    for field, message in (("code", "Vui lòng nhập mã phương án."), ("name", "Vui lòng nhập tên phương án."),
        ("purpose", "Vui lòng nhập mã mục đích."), ("context_scope", "Vui lòng nhập mã phạm vi áp dụng.")):
        if not data.get(field): errors[field] = message
    query = CostingScheme.objects.filter(organization=organization, code=data.get("code"))
    if instance and instance.pk: query = query.exclude(pk=instance.pk)
    if query.exists(): errors["code"] = "Mã phương án đã tồn tại."
    if instance and instance.pk and instance.costingschemeversion_set.exclude(status__in=EDITABLE_STATUSES).exists():
        for field in ("code", "purpose", "context_scope"):
            if data.get(field) != getattr(instance, field):
                errors[field] = "Định danh và phạm vi được giữ cố định vì đã có phiên bản được chốt."
    if errors: raise ValidationError(errors)


def validate_line(*, data, organization, instance=None, version=None, check_unique=True):
    errors = {}
    for field, vocabulary in (("line_type", LINE_TYPES), ("source_mode", SOURCE_MODES),
        ("visibility_scope", VISIBILITY_SCOPES), ("cost_scope", COST_SCOPES)):
        if data.get(field) not in dict(vocabulary): errors[field] = "Vui lòng chọn giá trị hợp lệ."
    for field in ("line_code", "label"):
        if not data.get(field): errors[field] = "Vui lòng nhập thông tin dòng cấu hình."
    order = data.get("display_order")
    if not isinstance(order, int) or not -2147483648 <= order <= 2147483647:
        errors["display_order"] = "Thứ tự phải là số nguyên trong phạm vi cho phép."
    scale = data.get("rounding_scale")
    if scale is not None and (not isinstance(scale, int) or not 0 <= scale <= 12):
        errors["rounding_scale"] = "Số chữ số làm tròn phải từ 0 đến 12."
    minimum, maximum = data.get("min_override_value"), data.get("max_override_value")
    if minimum is not None and maximum is not None and minimum > maximum:
        errors["max_override_value"] = "Giá trị tối đa không được nhỏ hơn giá trị tối thiểu."
    reference_field = {"SYSTEM": "system_resolver_code", "FORMULA": "formula_version", "LOOKUP": "rule_table", "EXTERNAL": "external_adapter_code"}.get(data.get("source_mode"))
    if reference_field and not data.get(reference_field): errors[reference_field] = "Vui lòng chọn hoặc nhập nguồn dữ liệu tương ứng."
    for field in ("cost_element", "rule_table", "formula_version"):
        reference = data.get(field)
        if reference is None: continue
        parent = reference.formula if field == "formula_version" else reference
        current_id = getattr(instance, f"{field}_id", None) if instance else None
        if parent.organization_id != organization.pk:
            errors[field] = "Tham chiếu không thuộc dữ liệu hệ thống."
        elif not parent.is_active and reference.pk != current_id:
            errors[field] = "Tham chiếu đã ngừng hoạt động."
        elif field == "formula_version" and (reference.status != "EFFECTIVE" or reference.validation_status != "VALID"):
            # Retain legacy references for review; never select a new invalid version.
            if reference.pk != current_id:
                errors[field] = "Vui lòng chọn phiên bản công thức hợp lệ đã được kích hoạt."
    if check_unique and version:
        query = CostingSchemeLine.objects.filter(scheme_version=version)
        if instance and instance.pk: query = query.exclude(pk=instance.pk)
        for field, message in (("line_code", "Mã dòng đã tồn tại trong phiên bản này."), ("display_order", "Thứ tự đã tồn tại trong phiên bản này.")):
            if query.filter(**{field: data.get(field)}).exists(): errors[field] = message
    if errors: raise ValidationError(errors)
