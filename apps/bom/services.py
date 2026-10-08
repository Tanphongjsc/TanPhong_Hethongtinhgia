"""Atomic definitions and versions. Always lock Recipe -> Version -> Line."""
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.core.models import Item, Product, Recipe, RecipeLine, RecipeVersion, Uom
from apps.master_data.access import require_write_access
from .constants import LINE_FIELDS, RECIPE_FIELDS, VERSION_FIELDS
from .validators import ensure_editable, normalize_values, validate_conversions, validate_line, validate_recipe, validate_version


def _database_error(error):
    cause = error.__cause__
    state = getattr(cause, "sqlstate", None)
    constraint = getattr(getattr(cause, "diag", None), "constraint_name", "")
    if constraint == "uq_recipe":
        raise ValidationError({"code": "Mã định mức đã tồn tại."}) from None
    if constraint == "uq_recipe_version":
        raise ValidationError("Số phiên bản đã tồn tại. Vui lòng tải lại và thử lại.") from None
    if state == "P0001":
        # Production triggers protect both the version and its lines. Never
        # expose PL/pgSQL messages/SQL; prechecks use the same statuses.
        raise ValidationError("Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới.") from None
    field = {
        "ck_recipe_output_qty": "output_qty", "ck_recipe_yield_rate": "yield_rate",
        "ck_recipe_version_period": "effective_to", "ck_recipe_effective_date_required": "effective_from",
        "ck_recipe_line_qty": "qty", "ck_recipe_line_scrap": "scrap_rate",
        "recipe_product_id_fkey": "product", "recipe_version_output_uom_id_fkey": "output_uom",
        "recipe_line_component_item_id_fkey": "component_item", "recipe_line_uom_id_fkey": "uom",
    }.get(constraint)
    if state in ("23502", "23503", "23505", "23514"):
        message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
        raise ValidationError({field: message} if field else message) from None
    raise error


def _locked_recipe(workspace, pk):
    try:
        return Recipe.objects.select_for_update(of=("self",)).get(pk=pk, organization=workspace.organization,
            product__organization=workspace.organization)
    except Recipe.DoesNotExist:
        raise ValidationError("Không tìm thấy định mức của công ty hiện tại.") from None


def _locked_version(recipe, pk):
    try:
        return RecipeVersion.objects.select_for_update().get(pk=pk, recipe=recipe)
    except RecipeVersion.DoesNotExist:
        raise ValidationError("Không tìm thấy phiên bản của định mức này.") from None


def _reference(model, reference, field, organization):
    if not isinstance(reference, model):
        raise ValidationError({field: "Vui lòng chọn danh mục hợp lệ."})
    queryset = model.objects.select_for_update()
    if model in (Item, Product):
        queryset = queryset.filter(organization=organization)
    try:
        return queryset.get(pk=reference.pk)
    except model.DoesNotExist:
        raise ValidationError({field: "Danh mục không còn tồn tại hoặc không thuộc công ty hiện tại."}) from None


def _assign(record, values):
    for field, value in values.items():
        setattr(record, field, value)
    record.full_clean(validate_unique=False, validate_constraints=False)


def _validate_version_lines(version, organization, date):
    lines = list(RecipeLine.objects.filter(recipe_version=version).select_related("component_item", "uom"))
    if any(line.component_item.organization_id != organization.pk for line in lines):
        raise ValidationError("Phiên bản có thành phần không thuộc công ty hiện tại.")
    validate_conversions(lines=[(line.component_item, line.uom) for line in lines], organization=organization, effective_from=date)
    return lines


def _new_version(*, recipe, workspace, data, source=None):
    values = normalize_values({field: data.get(field) for field in VERSION_FIELDS}, uppercase=())
    values["output_uom"] = _reference(Uom, values["output_uom"], "output_uom", workspace.organization)
    validate_version(data=values, organization=workspace.organization, instance=source)
    number = max(RecipeVersion.objects.filter(recipe=recipe).aggregate(number=Max("version_no"))["number"] or 0, 0) + 1
    if number > 2147483647:
        raise ValidationError("Không thể tăng số phiên bản. Vui lòng kiểm tra cấu hình dữ liệu.")
    lines = _validate_version_lines(source, workspace.organization, values["effective_from"]) if source else []
    version = RecipeVersion(recipe=recipe, version_no=number, status="DRAFT", created_by=None, approved_by=None,
        approved_at=None, content_hash=None)
    _assign(version, values)
    version.save(force_insert=True)
    RecipeLine.objects.bulk_create([RecipeLine(recipe_version=version, **{field: getattr(line, field) for field in LINE_FIELDS}) for line in lines])
    return version


def save_recipe(*, workspace, data, instance=None, initial_version=None):
    require_write_access(workspace, resource="bom", editing=instance is not None)
    values = normalize_values({field: data.get(field) for field in RECIPE_FIELDS})
    try:
        with transaction.atomic():
            recipe = _locked_recipe(workspace, instance.pk) if instance else Recipe(organization=workspace.organization)
            values["product"] = _reference(Product, values["product"], "product", workspace.organization)
            validate_recipe(data=values, organization=workspace.organization, instance=recipe)
            recipe.updated_at = timezone.now()
            _assign(recipe, values)
            recipe.save(force_insert=instance is None, force_update=instance is not None)
            if instance is None:
                if initial_version is None:
                    raise ValidationError("Vui lòng nhập cấu hình phiên bản đầu tiên.")
                _new_version(recipe=recipe, workspace=workspace, data=initial_version)
            return recipe
    except DatabaseError as error:
        _database_error(error)


def create_version(*, workspace, recipe, data, source=None):
    require_write_access(workspace, resource="bom_version")
    try:
        with transaction.atomic():
            recipe = _locked_recipe(workspace, recipe.pk)
            source = _locked_version(recipe, source.pk) if source is not None else None
            return _new_version(recipe=recipe, workspace=workspace, data=data, source=source)
    except DatabaseError as error:
        _database_error(error)


def update_version(*, workspace, recipe, instance, data):
    require_write_access(workspace, resource="bom_version", editing=True)
    values = normalize_values({field: data.get(field) for field in VERSION_FIELDS}, uppercase=())
    try:
        with transaction.atomic():
            recipe = _locked_recipe(workspace, recipe.pk)
            version = _locked_version(recipe, instance.pk)
            ensure_editable(version)
            values["output_uom"] = _reference(Uom, values["output_uom"], "output_uom", workspace.organization)
            validate_version(data=values, organization=workspace.organization, instance=version)
            if values["effective_from"] != version.effective_from:
                _validate_version_lines(version, workspace.organization, values["effective_from"])
            _assign(version, values)
            version.content_hash = None
            version.save(force_update=True)
            return version
    except DatabaseError as error:
        _database_error(error)


def save_line(*, workspace, recipe, version, data, instance=None):
    require_write_access(workspace, resource="bom_line", editing=instance is not None)
    values = normalize_values({field: data.get(field) for field in LINE_FIELDS}, uppercase=())
    try:
        with transaction.atomic():
            recipe = _locked_recipe(workspace, recipe.pk)
            version = _locked_version(recipe, version.pk)
            ensure_editable(version)
            if instance:
                try:
                    line = RecipeLine.objects.select_for_update().get(pk=instance.pk, recipe_version=version)
                except RecipeLine.DoesNotExist:
                    raise ValidationError("Không tìm thấy thành phần của phiên bản này.") from None
            else:
                line = RecipeLine(recipe_version=version)
            values["component_item"] = _reference(Item, values["component_item"], "component_item", workspace.organization)
            values["uom"] = _reference(Uom, values["uom"], "uom", workspace.organization)
            validate_line(data=values, organization=workspace.organization, instance=line)
            validate_conversions(lines=[(values["component_item"], values["uom"])], organization=workspace.organization, effective_from=version.effective_from)
            _assign(line, values)
            line.save(force_insert=instance is None, force_update=instance is not None)
            version.content_hash = None
            version.save(update_fields=["content_hash"])
            return line
    except DatabaseError as error:
        _database_error(error)


def remove_line(*, workspace, recipe, version, instance):
    require_write_access(workspace, resource="bom_line", editing=True)
    if not workspace.permissions.can_delete_bom_line:
        raise ValidationError("Thao tác xóa thành phần chưa được hệ thống hỗ trợ.")
    try:
        with transaction.atomic():
            recipe = _locked_recipe(workspace, recipe.pk)
            version = _locked_version(recipe, version.pk)
            ensure_editable(version)
            deleted, _ = RecipeLine.objects.filter(pk=instance.pk, recipe_version=version).delete()
            if not deleted:
                raise ValidationError("Không tìm thấy thành phần của phiên bản này.")
            version.content_hash = None
            version.save(update_fields=["content_hash"])
    except DatabaseError as error:
        _database_error(error)
