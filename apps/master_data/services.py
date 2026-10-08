"""Mutation boundary: validate, authorize, normalize and persist atomically."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import CostElement, Currency, Item, Supplier, SupplierPrice, Uom, UomCategory, UomConversion
from .access import require_write_access
from .constants import SUPPLIER_FIELDS, SUPPLIER_PRICE_FIELDS
from .constants import CURRENCY_FIELDS, EDITABLE_FIELDS, UOM_CATEGORY_FIELDS, UOM_CONVERSION_FIELDS, UOM_FIELDS
from .validators import (
    normalize_cost_element, normalize_reference_values, validate_cost_element,
    validate_currency, validate_uom, validate_uom_category, validate_uom_conversion,
    normalize_supplier_values, validate_supplier, validate_supplier_price,
)


def save_cost_element(*, workspace, data, instance=None):
    permissions = workspace.permissions
    require_write_access(workspace, resource="cost_element", editing=instance is not None)
    # Field allow-list prevents mass assignment of organization/audit fields.
    values = normalize_cost_element({name: data.get(name) for name in EDITABLE_FIELDS})
    try:
        with transaction.atomic():
            if instance:
                element = CostElement.objects.select_for_update().get(pk=instance.pk, organization=workspace.organization)
            else:
                element = CostElement(organization=workspace.organization, created_by=None)
            if (element.is_sensitive or values["is_sensitive"]) and not permissions.can_manage_sensitive_cost_element:
                raise PermissionDenied("Bạn không có quyền thực hiện thao tác này.")
            validate_cost_element(data=values, organization=workspace.organization, instance=element)
            for field, value in values.items():
                setattr(element, field, value)
            element.updated_by = None
            element.updated_at = timezone.now()
            element.full_clean(validate_unique=False, validate_constraints=False)
            element.save()
            return element
    except IntegrityError as error:
        constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "") or ""
        sqlstate = getattr(error.__cause__, "sqlstate", None)
        if constraint == "uq_cost_element" or sqlstate == "23505":
            raise ValidationError({"code": "Mã phần tử chi phí đã tồn tại trong công ty."}) from None
        field = {
            "ck_cost_element_rounding_scale": "rounding_scale",
            "ck_cost_element_rounding_mode": "rounding_mode",
            "ck_cost_element_value_type": "value_type",
            "ck_cost_element_source_mode": "default_source_mode",
            "ck_cost_element_accounting_scope": "accounting_scope",
            "ck_cost_element_cost_scope": "cost_scope",
            "cost_element_group_id_fkey": "group",
            "cost_element_currency_code_fkey": "currency_code",
            "cost_element_default_uom_id_fkey": "default_uom",
        }.get(constraint)
        message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
        raise ValidationError({field: message} if field else message) from None


def _refresh_reference_values(model, values, workspace):
    """Read authoritative FK values again within the write transaction."""
    if model in (Supplier, SupplierPrice):
        # Price locks Supplier -> Item -> UoM -> Currency. Supplier edits also
        # lock Currency, preventing a stale active choice during deactivation.
        references = (("default_currency_code", Currency),) if model is Supplier else (
            ("supplier", Supplier), ("item", Item), ("price_uom", Uom), ("currency_code", Currency),
        )
        for field, related_model in references:
            reference = values.get(field)
            if reference is None:
                continue
            if not isinstance(reference, related_model):
                raise ValidationError({field: "Danh mục tham chiếu không hợp lệ."})
            queryset = related_model.objects.select_for_update()
            if related_model in (Supplier, Item):
                queryset = queryset.filter(organization=workspace.organization)
            try:
                values[field] = queryset.get(pk=reference.pk)
            except related_model.DoesNotExist:
                raise ValidationError({field: "Danh mục không còn tồn tại hoặc không thuộc công ty hiện tại."}) from None
        return
    # Lock referenced units in stable order to serialize category changes with
    # conversion creation/edit. Caller-supplied Model objects may be stale.
    unit_fields = ("from_uom", "to_uom") if model is UomConversion else ()
    unit_ids = [values[name].pk for name in unit_fields if isinstance(values.get(name), Uom)]
    units = {unit.pk: unit for unit in Uom.objects.filter(pk__in=unit_ids).select_related("category").select_for_update(of=("self",)).order_by("pk")}
    for name, related_model in (("category", UomCategory), ("from_uom", Uom), ("to_uom", Uom), ("item", Item)):
        reference = values.get(name)
        if reference is None:
            continue
        if not isinstance(reference, related_model):
            raise ValidationError({name: "Danh mục tham chiếu không hợp lệ."})
        try:
            if name in unit_fields:
                values[name] = units[reference.pk]
            else:
                queryset = related_model.objects.all()
                if name == "item":
                    queryset = queryset.filter(organization=workspace.organization)
                values[name] = queryset.get(pk=reference.pk)
        except (KeyError, related_model.DoesNotExist):
            raise ValidationError({name: "Danh mục không còn tồn tại hoặc không thuộc công ty hiện tại."}) from None


def _save_reference(*, model, resource, fields, validator, workspace, data, instance=None, uppercase=("code",)):
    require_write_access(workspace, resource=resource, editing=instance is not None)
    if model is Currency and instance is not None:
        uppercase = ()  # Currency identifiers are immutable; normalize new codes only.
    normalizer = normalize_supplier_values if model in (Supplier, SupplierPrice) else normalize_reference_values
    values = normalizer({name: data.get(name) for name in fields}, uppercase=uppercase)
    try:
        with transaction.atomic():
            if instance is not None:
                queryset = model.objects.select_for_update()
                if model in (UomConversion, Supplier, SupplierPrice):
                    queryset = queryset.filter(organization=workspace.organization)
                try:
                    record = queryset.get(pk=instance.pk)
                except model.DoesNotExist:
                    raise ValidationError("Bản ghi không còn tồn tại hoặc không thuộc công ty hiện tại.") from None
            else:
                record = model()
            _refresh_reference_values(model, values, workspace)
            validator(data=values, organization=workspace.organization, instance=record)
            for name, value in values.items():
                setattr(record, name, value)
            if model in (UomConversion, Supplier, SupplierPrice):
                record.organization = workspace.organization
            if model in (Uom, UomCategory, Supplier):
                record.updated_at = timezone.now()
            record.full_clean(validate_unique=False, validate_constraints=False)
            record.save(force_update=instance is not None, force_insert=instance is None)
            return record
    except IntegrityError as error:
        constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "") or ""
        if getattr(error.__cause__, "sqlstate", None) == "23505" and model not in (UomConversion, SupplierPrice):
            message = "Mã nhà cung cấp đã tồn tại." if model is Supplier else "Mã đã tồn tại trong danh mục."
            raise ValidationError({"code": message}) from None
        field = {
            "ck_currency_decimal_places": "decimal_places",
            "ck_uom_precision": "precision",
            "uom_category_id_fkey": "category",
            "ck_uom_conversion_distinct": "to_uom",
            "ck_uom_conversion_factor": "factor",
            "ck_uom_conversion_period": "effective_to",
            "uom_conversion_from_uom_id_fkey": "from_uom",
            "uom_conversion_to_uom_id_fkey": "to_uom",
            "uom_conversion_item_id_fkey": "item",
            "supplier_default_currency_code_fkey": "default_currency_code",
            **{f"supplier_price_{field}_fkey": field.removesuffix("_id") for field in ("supplier_id", "item_id", "price_uom_id", "currency_code")},
            "ck_supplier_price_min_qty": "min_qty",
            "ck_supplier_price_unit_price": "unit_price",
            "ck_supplier_price_tax_rate": "tax_rate",
            "ck_supplier_price_recoverable": "tax_recoverable_ratio",
            "ck_supplier_price_period": "effective_to",
        }.get(constraint)
        message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
        raise ValidationError({field: message} if field else message) from None


def save_currency(*, workspace, data, instance=None):
    return _save_reference(model=Currency, resource="currency", fields=CURRENCY_FIELDS, validator=validate_currency, workspace=workspace, data=data, instance=instance)


def save_uom_category(*, workspace, data, instance=None):
    return _save_reference(model=UomCategory, resource="uom_category", fields=UOM_CATEGORY_FIELDS, validator=validate_uom_category, workspace=workspace, data=data, instance=instance, uppercase=("code", "dimension_code"))


def save_uom(*, workspace, data, instance=None):
    return _save_reference(model=Uom, resource="uom", fields=UOM_FIELDS, validator=validate_uom, workspace=workspace, data=data, instance=instance)


def save_uom_conversion(*, workspace, data, instance=None):
    return _save_reference(model=UomConversion, resource="uom_conversion", fields=UOM_CONVERSION_FIELDS, validator=validate_uom_conversion, workspace=workspace, data=data, instance=instance, uppercase=())


def save_supplier(*, workspace, data, instance=None):
    return _save_reference(model=Supplier, resource="supplier", fields=SUPPLIER_FIELDS, validator=validate_supplier, workspace=workspace, data=data, instance=instance)


def save_supplier_price(*, workspace, data, instance=None):
    # status/created_by/created_at are absent from the allow-list. New prices are
    # DRAFT with a NULL actor; edits preserve the existing record status/history.
    return _save_reference(model=SupplierPrice, resource="supplier_price", fields=SUPPLIER_PRICE_FIELDS, validator=validate_supplier_price, workspace=workspace, data=data, instance=instance, uppercase=())
