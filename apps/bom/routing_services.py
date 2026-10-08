"""Atomic routing mutations. Lock Routing -> Version -> Operation -> references."""
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.core.models import Product, Resource, Routing, RoutingOperation, RoutingVersion, Uom, WorkCenter
from apps.master_data.access import require_write_access
from .routing_constants import OPERATION_FIELDS, ROUTING_FIELDS, VERSION_FIELDS
from .routing_validators import ensure_editable, normalize_routing_values, validate_operation, validate_routing, validate_version


def _database_error(error):
    state = getattr(error.__cause__, "sqlstate", None)
    constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "")
    messages = {"uq_routing": {"code": "Mã quy trình đã tồn tại."},
        "uq_routing_operation_sequence": {"sequence_no": "Thứ tự công đoạn đã tồn tại trong phiên bản này."},
        "uq_routing_version": "Số phiên bản đã tồn tại. Vui lòng tải lại và thử lại."}
    if constraint in messages:
        raise ValidationError(messages[constraint]) from None
    if state == "P0001":
        raise ValidationError("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới.") from None
    field = {"ck_routing_batch_size": "batch_size", "ck_routing_version_period": "effective_to",
        "ck_routing_effective_date_required": "effective_from", "ck_routing_operation_time": "run_time",
        "ck_routing_operation_qty": "quantity_basis", "routing_product_id_fkey": "product",
        "routing_version_batch_uom_id_fkey": "batch_uom",
        **{f"routing_operation_{name}_id_fkey": name for name in ("work_center", "primary_resource", "time_uom", "quantity_uom")}}.get(constraint)
    if state in ("23502", "23503", "23505", "23514"):
        message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
        raise ValidationError({field: message} if field else message) from None
    raise error


def _locked_routing(workspace, pk):
    try:
        return Routing.objects.select_for_update(of=("self",)).get(pk=pk, organization=workspace.organization, product__organization=workspace.organization)
    except Routing.DoesNotExist:
        raise ValidationError("Không tìm thấy quy trình của hệ thống.") from None


def _locked_version(routing, pk):
    try:
        return RoutingVersion.objects.select_for_update().get(pk=pk, routing=routing)
    except RoutingVersion.DoesNotExist:
        raise ValidationError("Không tìm thấy phiên bản của quy trình này.") from None


def _assign(record, values):
    for field, value in values.items():
        setattr(record, field, value)
    record.full_clean(validate_unique=False, validate_constraints=False)


def _product(reference, organization):
    if not isinstance(reference, Product):
        raise ValidationError({"product": "Vui lòng chọn sản phẩm hợp lệ."})
    try:
        return Product.objects.select_for_update().get(pk=reference.pk, organization=organization)
    except Product.DoesNotExist:
        raise ValidationError({"product": "Sản phẩm không còn tồn tại hoặc không thuộc dữ liệu hệ thống."}) from None


def _refresh_references(rows, organization):
    """Bounded queries for edits/clones, stable locks compatible with resource CRUD."""
    for model, fields in ((Resource, ("primary_resource",)), (WorkCenter, ("work_center",)), (Uom, ("time_uom", "quantity_uom", "batch_uom"))):
        references = [row.get(field) for row in rows for field in fields if row.get(field) is not None]
        if not references:
            continue
        if any(not isinstance(reference, model) for reference in references):
            raise ValidationError("Danh mục tham chiếu không hợp lệ.")
        query = model.objects.filter(pk__in={reference.pk for reference in references})
        if model in (Resource, WorkCenter):
            query = query.filter(organization=organization)
        if model is Resource:
            query = query.select_related("work_center")
        elif model is Uom:
            query = query.select_related("category")
        lookup = {reference.pk: reference for reference in query.select_for_update(of=("self",)).order_by("pk")}
        for row in rows:
            for field in fields:
                if row.get(field) is None:
                    continue
                try:
                    row[field] = lookup[row[field].pk]
                except KeyError:
                    raise ValidationError({field: "Danh mục không còn tồn tại hoặc không thuộc dữ liệu hệ thống."}) from None


def _new_version(*, routing, workspace, data, source=None):
    values = normalize_routing_values({field: data.get(field) for field in VERSION_FIELDS}, uppercase=())
    operations = list(RoutingOperation.objects.filter(routing_version=source).select_related("work_center", "primary_resource", "time_uom", "quantity_uom").order_by("sequence_no", "pk")) if source else []
    rows = [{field: getattr(operation, field) for field in OPERATION_FIELDS} for operation in operations]
    _refresh_references([values, *rows], workspace.organization)
    validate_version(data=values, organization=workspace.organization, instance=source)
    for operation, row in zip(operations, rows):
        validate_operation(data=row, organization=workspace.organization, instance=operation, check_unique=False)
    number = max(RoutingVersion.objects.filter(routing=routing).aggregate(number=Max("version_no"))["number"] or 0, 0) + 1
    if number > 2147483647:
        raise ValidationError("Không thể tăng số phiên bản. Vui lòng kiểm tra cấu hình dữ liệu.")
    version = RoutingVersion(routing=routing, version_no=number, status="DRAFT", created_by=None, approved_by=None, approved_at=None, content_hash=None)
    _assign(version, values)
    version.save(force_insert=True)
    RoutingOperation.objects.bulk_create([RoutingOperation(routing_version=version, **row) for row in rows])
    return version


def save_routing(*, workspace, data, instance=None, initial_version=None):
    require_write_access(workspace, resource="routing", editing=instance is not None)
    values = normalize_routing_values({field: data.get(field) for field in ROUTING_FIELDS})
    try:
        with transaction.atomic():
            routing = _locked_routing(workspace, instance.pk) if instance else Routing(organization=workspace.organization)
            values["product"] = _product(values["product"], workspace.organization)
            validate_routing(data=values, organization=workspace.organization, instance=routing)
            routing.updated_at = timezone.now()
            _assign(routing, values)
            routing.save(force_insert=instance is None, force_update=instance is not None)
            if instance is None:
                if initial_version is None:
                    raise ValidationError("Vui lòng nhập cấu hình phiên bản đầu tiên.")
                _new_version(routing=routing, workspace=workspace, data=initial_version)
            return routing
    except DatabaseError as error:
        _database_error(error)


def create_version(*, workspace, routing, data, source=None):
    require_write_access(workspace, resource="routing_version")
    try:
        with transaction.atomic():
            routing = _locked_routing(workspace, routing.pk)
            source = _locked_version(routing, source.pk) if source is not None else None
            return _new_version(routing=routing, workspace=workspace, data=data, source=source)
    except DatabaseError as error:
        _database_error(error)


def update_version(*, workspace, routing, instance, data):
    require_write_access(workspace, resource="routing_version", editing=True)
    values = normalize_routing_values({field: data.get(field) for field in VERSION_FIELDS}, uppercase=())
    try:
        with transaction.atomic():
            routing = _locked_routing(workspace, routing.pk)
            version = _locked_version(routing, instance.pk)
            ensure_editable(version)
            _refresh_references([values], workspace.organization)
            validate_version(data=values, organization=workspace.organization, instance=version)
            _assign(version, values)
            version.content_hash = None
            version.save(force_update=True)
            return version
    except DatabaseError as error:
        _database_error(error)


def save_operation(*, workspace, routing, version, data, instance=None):
    require_write_access(workspace, resource="routing_operation", editing=instance is not None)
    values = normalize_routing_values({field: data.get(field) for field in OPERATION_FIELDS}, uppercase=())
    try:
        with transaction.atomic():
            routing = _locked_routing(workspace, routing.pk)
            version = _locked_version(routing, version.pk)
            ensure_editable(version)
            if instance:
                try:
                    operation = RoutingOperation.objects.select_for_update().get(pk=instance.pk, routing_version=version)
                except RoutingOperation.DoesNotExist:
                    raise ValidationError("Không tìm thấy công đoạn của phiên bản này.") from None
            else:
                operation = RoutingOperation(routing_version=version)
            _refresh_references([values], workspace.organization)
            validate_operation(data=values, organization=workspace.organization, instance=operation, version=version)
            _assign(operation, values)
            operation.save(force_insert=instance is None, force_update=instance is not None)
            version.content_hash = None
            version.save(update_fields=["content_hash"])
            return operation
    except DatabaseError as error:
        _database_error(error)


def remove_operation(*, workspace, routing, version, instance):
    require_write_access(workspace, resource="routing_operation", editing=True)
    if not workspace.permissions.can_delete_routing_operation:
        raise ValidationError("Thao tác xóa công đoạn chưa được hệ thống hỗ trợ.")
    try:
        with transaction.atomic():
            routing = _locked_routing(workspace, routing.pk)
            version = _locked_version(routing, version.pk)
            ensure_editable(version)
            deleted, _ = RoutingOperation.objects.filter(pk=instance.pk, routing_version=version).delete()
            if not deleted:
                raise ValidationError("Không tìm thấy công đoạn của phiên bản này.")
            version.content_hash = None
            version.save(update_fields=["content_hash"])
    except DatabaseError as error:
        _database_error(error)
