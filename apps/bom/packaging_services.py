"""Atomic packaging writes; lock Config -> Version -> Line/Assignment."""
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.core.models import Item, PackagingConfig, PackagingConfigVersion, PackagingLine, Product, Sku, SkuPackagingAssignment, Uom
from apps.master_data.access import require_write_access
from .packaging_constants import ASSIGNMENT_FIELDS, CONFIG_FIELDS, LINE_FIELDS, VERSION_FIELDS
from .packaging_validators import normalize_values, validate_assignment, validate_config, validate_conversions, validate_line, validate_version
from .validators import ensure_editable


def _database_error(error):
    cause = error.__cause__
    state = getattr(cause, "sqlstate", None)
    constraint = getattr(getattr(cause, "diag", None), "constraint_name", "")
    if constraint == "uq_packaging_config":
        raise ValidationError({"code": "Mã cấu hình bao bì đã tồn tại."}) from None
    if constraint == "uq_packaging_config_version":
        raise ValidationError("Số phiên bản đã tồn tại. Vui lòng tải lại và thử lại.") from None
    if constraint == "uq_sku_packaging_assignment":
        raise ValidationError({"effective_from": "SKU đã được gán cấu hình này với cùng ngày bắt đầu."}) from None
    if state == "P0001":
        raise ValidationError("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới.") from None
    field = {"ck_packaging_config_period": "effective_to", "ck_packaging_effective_date_required": "effective_from",
        "ck_packaging_weight": "gross_weight", "ck_packaging_line_qty": "qty", "ck_packaging_units_parent": "units_per_parent",
        "ck_packaging_line_level": "level_code", "ck_sku_packaging_period": "effective_to",
        "packaging_config_product_id_fkey": "product", "packaging_line_packaging_item_id_fkey": "packaging_item",
        "packaging_line_uom_id_fkey": "uom", "sku_packaging_assignment_sku_id_fkey": "sku"}.get(constraint)
    if state in ("23502", "23503", "23505", "23514"):
        message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
        raise ValidationError({field: message} if field else message) from None
    raise error


def _locked_config(workspace, pk):
    try:
        return PackagingConfig.objects.select_for_update(of=("self",)).get(pk=pk, organization=workspace.organization, product__organization=workspace.organization)
    except PackagingConfig.DoesNotExist:
        raise ValidationError("Không tìm thấy cấu hình bao bì của công ty hiện tại.") from None


def _locked_version(config, pk):
    try:
        return PackagingConfigVersion.objects.select_for_update().get(pk=pk, packaging_config=config)
    except PackagingConfigVersion.DoesNotExist:
        raise ValidationError("Không tìm thấy phiên bản của cấu hình bao bì này.") from None


def _reference(model, reference, field, organization):
    if reference is None and model is Uom:
        return None
    if not isinstance(reference, model):
        raise ValidationError({field: "Vui lòng chọn danh mục hợp lệ."})
    queryset = model.objects.select_for_update()
    if model in (Item, Product, Sku):
        queryset = queryset.filter(organization=organization)
    try:
        return queryset.get(pk=reference.pk)
    except model.DoesNotExist:
        raise ValidationError({field: "Danh mục không còn tồn tại hoặc không thuộc công ty hiện tại."}) from None


def _assign(record, values):
    for field, value in values.items():
        setattr(record, field, value)
    record.full_clean(validate_unique=False, validate_constraints=False)


def _validate_lines(version, organization, date):
    lines = list(PackagingLine.objects.filter(packaging_config_version=version).select_related("packaging_item", "uom"))
    if any(line.packaging_item.organization_id != organization.pk for line in lines):
        raise ValidationError("Phiên bản có vật tư không thuộc công ty hiện tại.")
    validate_conversions(lines=[(line.packaging_item, line.uom) for line in lines], organization=organization, effective_from=date)
    return lines


def _new_version(*, config, workspace, data, source=None):
    values = normalize_values({field: data.get(field) for field in VERSION_FIELDS}, uppercase=())
    for field in ("weight_uom", "dimension_uom"):
        values[field] = _reference(Uom, values[field], field, workspace.organization)
    validate_version(data=values, organization=workspace.organization, instance=source)
    number = max(PackagingConfigVersion.objects.filter(packaging_config=config).aggregate(number=Max("version_no"))["number"] or 0, 0) + 1
    if number > 2147483647:
        raise ValidationError("Không thể tăng số phiên bản. Vui lòng kiểm tra cấu hình dữ liệu.")
    lines = _validate_lines(source, workspace.organization, values["effective_from"]) if source else []
    version = PackagingConfigVersion(packaging_config=config, version_no=number, status="DRAFT", created_by=None, approved_by=None, approved_at=None, content_hash=None)
    _assign(version, values)
    version.save(force_insert=True)
    PackagingLine.objects.bulk_create([PackagingLine(packaging_config_version=version, **{field: getattr(line, field) for field in LINE_FIELDS}) for line in lines])
    return version


def save_config(*, workspace, data, instance=None, initial_version=None):
    require_write_access(workspace, resource="packaging", editing=instance is not None)
    values = normalize_values({field: data.get(field) for field in CONFIG_FIELDS})
    try:
        with transaction.atomic():
            config = _locked_config(workspace, instance.pk) if instance else PackagingConfig(organization=workspace.organization)
            values["product"] = _reference(Product, values["product"], "product", workspace.organization)
            validate_config(data=values, organization=workspace.organization, instance=config)
            config.updated_at = timezone.now()
            _assign(config, values)
            config.save(force_insert=instance is None, force_update=instance is not None)
            if instance is None:
                if initial_version is None:
                    raise ValidationError("Vui lòng nhập cấu hình phiên bản đầu tiên.")
                _new_version(config=config, workspace=workspace, data=initial_version)
            return config
    except DatabaseError as error:
        _database_error(error)


def create_version(*, workspace, config, data, source=None):
    require_write_access(workspace, resource="packaging_version")
    try:
        with transaction.atomic():
            config = _locked_config(workspace, config.pk)
            source = _locked_version(config, source.pk) if source else None
            return _new_version(config=config, workspace=workspace, data=data, source=source)
    except DatabaseError as error:
        _database_error(error)


def update_version(*, workspace, config, instance, data):
    require_write_access(workspace, resource="packaging_version", editing=True)
    values = normalize_values({field: data.get(field) for field in VERSION_FIELDS}, uppercase=())
    try:
        with transaction.atomic():
            config = _locked_config(workspace, config.pk)
            version = _locked_version(config, instance.pk)
            ensure_editable(version)
            for field in ("weight_uom", "dimension_uom"):
                values[field] = _reference(Uom, values[field], field, workspace.organization)
            validate_version(data=values, organization=workspace.organization, instance=version)
            if values["effective_from"] != version.effective_from:
                _validate_lines(version, workspace.organization, values["effective_from"])
            _assign(version, values)
            version.content_hash = None
            version.save(force_update=True)
            return version
    except DatabaseError as error:
        _database_error(error)


def save_line(*, workspace, config, version, data, instance=None):
    require_write_access(workspace, resource="packaging_line", editing=instance is not None)
    values = normalize_values({field: data.get(field) for field in LINE_FIELDS}, uppercase=())
    try:
        with transaction.atomic():
            config = _locked_config(workspace, config.pk)
            version = _locked_version(config, version.pk)
            ensure_editable(version)
            if instance:
                try:
                    line = PackagingLine.objects.select_for_update().get(pk=instance.pk, packaging_config_version=version)
                except PackagingLine.DoesNotExist:
                    raise ValidationError("Không tìm thấy thành phần của phiên bản này.") from None
            else:
                line = PackagingLine(packaging_config_version=version)
            values["packaging_item"] = _reference(Item, values["packaging_item"], "packaging_item", workspace.organization)
            values["uom"] = _reference(Uom, values["uom"], "uom", workspace.organization)
            validate_line(data=values, organization=workspace.organization, instance=line)
            validate_conversions(lines=[(values["packaging_item"], values["uom"])], organization=workspace.organization, effective_from=version.effective_from)
            _assign(line, values)
            line.save(force_insert=instance is None, force_update=instance is not None)
            version.content_hash = None
            version.save(update_fields=["content_hash"])
            return line
    except DatabaseError as error:
        _database_error(error)


def remove_line(*, workspace, config, version, instance):
    require_write_access(workspace, resource="packaging_line", editing=True)
    if not workspace.permissions.can_delete_packaging_line:
        raise ValidationError("Thao tác xóa thành phần chưa được hệ thống hỗ trợ.")
    try:
        with transaction.atomic():
            config = _locked_config(workspace, config.pk)
            version = _locked_version(config, version.pk)
            ensure_editable(version)
            deleted, _ = PackagingLine.objects.filter(pk=instance.pk, packaging_config_version=version).delete()
            if not deleted:
                raise ValidationError("Không tìm thấy thành phần của phiên bản này.")
            version.content_hash = None
            version.save(update_fields=["content_hash"])
    except DatabaseError as error:
        _database_error(error)


def save_assignment(*, workspace, config, data, instance=None):
    require_write_access(workspace, resource="packaging_assignment", editing=instance is not None)
    values = normalize_values({field: data.get(field) for field in ASSIGNMENT_FIELDS}, uppercase=())
    try:
        with transaction.atomic():
            config = _locked_config(workspace, config.pk)
            if instance:
                try:
                    assignment = SkuPackagingAssignment.objects.select_for_update().get(pk=instance.pk, packaging_config=config)
                except SkuPackagingAssignment.DoesNotExist:
                    raise ValidationError("Không tìm thấy liên kết SKU của cấu hình này.") from None
            else:
                assignment = SkuPackagingAssignment(packaging_config=config)
            values["sku"] = _reference(Sku, values["sku"], "sku", workspace.organization)
            validate_assignment(data=values, organization=workspace.organization, instance=assignment)
            _assign(assignment, values)
            assignment.save(force_insert=instance is None, force_update=instance is not None)
            return assignment
    except DatabaseError as error:
        _database_error(error)
