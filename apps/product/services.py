"""Atomic, scoped mutations with explicit editable field allow-lists."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import Item, Product, ProductCategory, Sku, Uom
from apps.master_data.access import require_write_access
from .constants import CATEGORY_FIELDS, ITEM_FIELDS, PRODUCT_FIELDS, PRODUCT_UNIT_FIELDS, SKU_FIELDS, SKU_UNIT_FIELDS, UNIT_FIELDS
from .validators import normalize_product_values, validate_category, validate_item, validate_product, validate_sku


def _refresh_item_references(values, organization):
    category = values.get("category")
    if category is not None:
        if not isinstance(category, ProductCategory):
            raise ValidationError({"category": "Nhóm sản phẩm không hợp lệ."})
        try:
            values["category"] = ProductCategory.objects.select_for_update().get(pk=category.pk, organization=organization)
        except ProductCategory.DoesNotExist:
            raise ValidationError({"category": "Nhóm sản phẩm không còn tồn tại hoặc không thuộc công ty hiện tại."}) from None
    for field in UNIT_FIELDS:
        if values.get(field) is not None and not isinstance(values[field], Uom):
            raise ValidationError({field: "Đơn vị tính không hợp lệ."})
    ids = {values[field].pk for field in UNIT_FIELDS if values.get(field) is not None}
    # Stable locking order also serializes concurrent UoM edits/deactivation.
    units = {unit.pk: unit for unit in Uom.objects.filter(pk__in=ids).select_related("category").select_for_update(of=("self",)).order_by("pk")}
    for field in UNIT_FIELDS:
        if values.get(field) is not None:
            try:
                values[field] = units[values[field].pk]
            except KeyError:
                raise ValidationError({field: "Đơn vị tính không còn tồn tại."}) from None


def _refresh_product_references(model, values, organization):
    # Lock Product -> Item -> category -> units, consistent with Item updates.
    references = (("output_item", Item), ("category", ProductCategory)) if model is Product else (("product", Product), ("sell_item", Item))
    for field, reference_model in references:
        reference = values.get(field)
        if reference is None:
            continue
        if not isinstance(reference, reference_model):
            raise ValidationError({field: "Danh mục tham chiếu không hợp lệ."})
        try:
            values[field] = reference_model.objects.select_for_update().get(pk=reference.pk, organization=organization)
        except reference_model.DoesNotExist:
            raise ValidationError({field: "Danh mục không còn tồn tại hoặc không thuộc công ty hiện tại."}) from None
    fields = PRODUCT_UNIT_FIELDS if model is Product else SKU_UNIT_FIELDS
    for field in fields:
        if values.get(field) is not None and not isinstance(values[field], Uom):
            raise ValidationError({field: "Đơn vị tính không hợp lệ."})
    ids = {values[field].pk for field in fields if values.get(field) is not None}
    units = {unit.pk: unit for unit in Uom.objects.filter(pk__in=ids).select_for_update().order_by("pk")}
    for field in fields:
        if values.get(field) is not None:
            try:
                values[field] = units[values[field].pk]
            except KeyError:
                raise ValidationError({field: "Đơn vị tính không còn tồn tại."}) from None


def _save_catalog(*, model, resource, fields, validator, workspace, data, instance=None):
    require_write_access(workspace, resource=resource, editing=instance is not None)
    values = normalize_product_values({field: data.get(field) for field in fields})
    try:
        with transaction.atomic():
            if instance is None:
                record = model(organization=workspace.organization)
            else:
                try:
                    record = model.objects.select_for_update().get(pk=instance.pk, organization=workspace.organization)
                except model.DoesNotExist:
                    raise ValidationError("Bản ghi không còn tồn tại hoặc không thuộc công ty hiện tại.") from None
            if model is Item:
                _refresh_item_references(values, workspace.organization)
            elif model in (Product, Sku):
                _refresh_product_references(model, values, workspace.organization)
            validator(data=values, organization=workspace.organization, instance=record)
            for field, value in values.items():
                setattr(record, field, value)
            record.updated_at = timezone.now()
            # Hidden JSON is not editable. Empty {} is valid in PostgreSQL;
            # Django's blank=False field validation would reject that default.
            hidden_fields = {Item: ("metadata",), Sku: ("attributes",)}.get(model, ())
            record.full_clean(exclude=hidden_fields, validate_unique=False, validate_constraints=False)
            record.save(force_insert=instance is None, force_update=instance is not None)
            return record
    except IntegrityError as error:
        constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "") or ""
        if getattr(error.__cause__, "sqlstate", None) == "23505":
            if model is Sku and constraint == "uq_sku_barcode":
                raise ValidationError({"barcode": "Mã vạch đã tồn tại."}) from None
            message = {Product: "Mã sản phẩm đã tồn tại.", Sku: "Mã SKU đã tồn tại."}.get(model, "Mã này đã tồn tại.")
            raise ValidationError({"code": message}) from None
        field = {
            "ck_item_type": "item_type", "ck_item_weight": "net_weight", "ck_item_dimension": "length",
            **{f"item_{name}_id_fkey": name for name in ("category", *UNIT_FIELDS)},
            **{f"product_{name}_id_fkey": name for name in ("category", "output_item", *PRODUCT_UNIT_FIELDS)},
            **{f"sku_{name}_id_fkey": name for name in ("product", "sell_item", *SKU_UNIT_FIELDS)},
            "ck_sku_net_quantity": "net_quantity",
        }.get(constraint)
        message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
        raise ValidationError({field: message} if field else message) from None


def save_category(*, workspace, data, instance=None):
    return _save_catalog(model=ProductCategory, resource="product_category", fields=CATEGORY_FIELDS, validator=validate_category, workspace=workspace, data=data, instance=instance)


def save_item(*, workspace, data, instance=None):
    return _save_catalog(model=Item, resource="item", fields=ITEM_FIELDS, validator=validate_item, workspace=workspace, data=data, instance=instance)


def save_product(*, workspace, data, instance=None):
    return _save_catalog(model=Product, resource="product", fields=PRODUCT_FIELDS, validator=validate_product, workspace=workspace, data=data, instance=instance)


def save_sku(*, workspace, data, instance=None):
    return _save_catalog(model=Sku, resource="sku", fields=SKU_FIELDS, validator=validate_sku, workspace=workspace, data=data, instance=instance)
