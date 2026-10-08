"""Routing definitions only: no rate lookup or production cost calculation."""
from django.core.exceptions import ValidationError

from apps.core.models import Product, Resource, Routing, RoutingOperation, Uom, WorkCenter
from .validators import _decimal, _reference, ensure_editable, normalize_values
from .routing_constants import IMMUTABLE_STATUSES


def normalize_routing_values(data, *, uppercase=("code",)):
    values = normalize_values(data, uppercase=uppercase)
    if "operation_code" in values:
        values["operation_code"] = (values["operation_code"] or "").strip().upper()
    if "operation_name" in values:
        values["operation_name"] = (values["operation_name"] or "").strip()
    return values


def validate_routing(*, data, organization, instance=None):
    errors = {}
    for field, label in (("code", "mã quy trình"), ("name", "tên quy trình")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label}."
    duplicates = Routing.objects.filter(organization=organization, code__iexact=data.get("code", ""))
    if instance and instance.pk:
        duplicates = duplicates.exclude(pk=instance.pk)
    if duplicates.exists():
        errors["code"] = "Mã quy trình đã tồn tại."
    _reference(errors, data=data, field="product", model=Product, instance=instance, organization=organization, label="sản phẩm")
    if instance and instance.pk and "product" not in errors and data["product"].pk != instance.product_id:
        if instance.routingversion_set.filter(status__in=IMMUTABLE_STATUSES).exists():
            errors["product"] = "Không thể đổi sản phẩm vì quy trình đã có phiên bản được chốt."
    if errors:
        raise ValidationError(errors)


def _optional_reference(errors, data, field, model, instance, organization=None, label="đơn vị tính"):
    if data.get(field) is not None:
        _reference(errors, data=data, field=field, model=model, instance=instance, organization=organization, label=label)


def validate_version(*, data, organization, instance=None):
    errors = {}
    _optional_reference(errors, data, "batch_uom", Uom, instance)
    if data.get("batch_size") is not None:
        _decimal(errors, data, "batch_size", "Sản lượng lô chuẩn", positive=True)
        if not data.get("batch_uom"):
            errors["batch_uom"] = "Vui lòng chọn đơn vị tính sản lượng lô."
    elif data.get("batch_uom") is not None:
        errors["batch_size"] = "Vui lòng nhập sản lượng lô chuẩn khi chọn đơn vị tính."
    start, end = data.get("effective_from"), data.get("effective_to")
    if end and not start:
        errors["effective_from"] = "Vui lòng nhập ngày bắt đầu khi có ngày kết thúc hiệu lực."
    elif start and end and end <= start:
        errors["effective_to"] = "Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực."
    if errors:
        raise ValidationError(errors)


def validate_operation(*, data, organization, instance=None, version=None, check_unique=True):
    errors = {}
    sequence = data.get("sequence_no")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 0 < sequence <= 2147483647:
        errors["sequence_no"] = "Thứ tự công đoạn phải lớn hơn 0."
    for field, label in (("operation_code", "mã công đoạn"), ("operation_name", "tên công đoạn")):
        if not data.get(field):
            errors[field] = f"Vui lòng nhập {label}."
    if check_unique:
        version = version or getattr(instance, "routing_version", None)
    if check_unique and version and "sequence_no" not in errors:
        duplicates = RoutingOperation.objects.filter(routing_version=version, sequence_no=sequence)
        if instance and instance.pk:
            duplicates = duplicates.exclude(pk=instance.pk)
        if duplicates.exists():
            errors["sequence_no"] = "Thứ tự công đoạn đã tồn tại trong phiên bản này."
    for field, model, label in (("work_center", WorkCenter, "trung tâm sản xuất"), ("primary_resource", Resource, "nguồn lực")):
        _optional_reference(errors, data, field, model, instance, organization, label)
    center, resource = data.get("work_center"), data.get("primary_resource")
    if center and resource and not any(field in errors for field in ("work_center", "primary_resource")):
        if resource.work_center_id is not None and resource.work_center_id != center.pk:
            errors["primary_resource"] = "Nguồn lực không thuộc trung tâm sản xuất đã chọn."
    if isinstance(resource, Resource) and resource.work_center_id:
        if resource.work_center.organization_id != organization.pk:
            errors["primary_resource"] = "Nguồn lực có trung tâm sản xuất không hợp lệ."
    for field, label in (("setup_time", "Thời gian thiết lập"), ("run_time", "Thời gian chạy")):
        _decimal(errors, data, field, label)
    _optional_reference(errors, data, "time_uom", Uom, instance)
    unit = data.get("time_uom")
    if isinstance(unit, Uom) and unit.category.dimension_code.upper() != "TIME":
        errors["time_uom"] = "Vui lòng chọn đơn vị tính thuộc đại lượng thời gian."
    if any(data.get(field) and field not in errors for field in ("setup_time", "run_time")) and unit is None:
        errors["time_uom"] = "Vui lòng chọn đơn vị thời gian."
    _optional_reference(errors, data, "quantity_uom", Uom, instance)
    if data.get("quantity_basis") is not None:
        _decimal(errors, data, "quantity_basis", "Sản lượng cơ sở", positive=True)
        if not data.get("quantity_uom"):
            errors["quantity_uom"] = "Vui lòng chọn đơn vị tính sản lượng cơ sở."
    elif data.get("quantity_uom") is not None:
        errors["quantity_basis"] = "Vui lòng nhập sản lượng cơ sở khi chọn đơn vị tính."
    if errors:
        raise ValidationError(errors)
