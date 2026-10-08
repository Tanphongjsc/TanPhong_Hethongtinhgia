"""Scoped atomic persistence; no rates resolution or production costing."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Currency, Resource, ResourceRate, Uom, WorkCenter
from apps.master_data.access import require_write_access
from .resource_constants import RATE_FIELDS, RESOURCE_FIELDS, WORK_CENTER_FIELDS
from .resource_validators import normalize_resource_values, validate_resource, validate_resource_rate, validate_work_center


def _refresh_references(model, values, organization):
    references = {WorkCenter: (("capacity_uom", Uom),), Resource: (("work_center", WorkCenter), ("capacity_uom", Uom)),
        ResourceRate: (("resource", Resource), ("per_uom", Uom), ("currency_code", Currency))}[model]
    # Lock dependency order: Rate -> Resource -> WorkCenter -> UoM -> Currency.
    # Readers still see inactive historical references; validation preserves the
    # existing reference but refuses newly selecting an inactive catalog entry.
    for field, reference_model in references:
        reference = values.get(field)
        if reference is None:
            continue
        if not isinstance(reference, reference_model):
            raise ValidationError({field: "Danh mục tham chiếu không hợp lệ."})
        query = reference_model.objects.select_for_update()
        if reference_model in (WorkCenter, Resource):
            query = query.filter(organization=organization)
        if reference_model is Resource:
            query = query.filter(Q(work_center__isnull=True) | Q(work_center__organization=organization))
            query = query.select_for_update(of=("self",))
        try:
            values[field] = query.get(pk=reference.pk)
        except reference_model.DoesNotExist:
            raise ValidationError({field: "Danh mục không còn tồn tại hoặc không thuộc dữ liệu hệ thống."}) from None


def _save(*, model, resource, fields, validator, workspace, data, instance=None):
    require_write_access(workspace, resource=resource, editing=instance is not None)
    values = normalize_resource_values({name: data.get(name) for name in fields}, uppercase=() if model is ResourceRate else ("code",))
    try:
        with transaction.atomic():
            if instance is None:
                record = model(organization=workspace.organization)
            else:
                try:
                    record = model.objects.select_for_update().get(pk=instance.pk, organization=workspace.organization)
                except model.DoesNotExist:
                    raise ValidationError("Bản ghi không còn tồn tại hoặc không thuộc dữ liệu hệ thống.") from None
            _refresh_references(model, values, workspace.organization)
            validator(data=values, organization=workspace.organization, instance=record)
            for field, value in values.items():
                setattr(record, field, value)
            if model is not ResourceRate:
                record.updated_at = timezone.now()
            # Metadata, status and actors never enter the editable allow-list.
            record.full_clean(exclude=("metadata",) if model is Resource else (), validate_unique=False, validate_constraints=False)
            record.save(force_insert=instance is None, force_update=instance is not None)
            return record
    except IntegrityError as error:
        constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "") or ""
        duplicate = {"uq_work_center": "Mã trung tâm sản xuất đã tồn tại.", "uq_resource": "Mã nguồn lực đã tồn tại."}
        if constraint in duplicate:
            raise ValidationError({"code": duplicate[constraint]}) from None
        field = {"ck_work_center_capacity": "capacity_value", "ck_resource_type": "resource_type",
            "ck_resource_rate_amount": "amount", "ck_resource_rate_period": "effective_to",
            "resource_work_center_id_fkey": "work_center", "resource_capacity_uom_id_fkey": "capacity_uom",
            "work_center_capacity_uom_id_fkey": "capacity_uom", "resource_rate_resource_id_fkey": "resource",
            "resource_rate_per_uom_id_fkey": "per_uom", "resource_rate_currency_code_fkey": "currency_code"}.get(constraint)
        message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
        raise ValidationError({field: message} if field else message) from None


def save_work_center(*, workspace, data, instance=None):
    return _save(model=WorkCenter, resource="work_center", fields=WORK_CENTER_FIELDS, validator=validate_work_center, workspace=workspace, data=data, instance=instance)


def save_resource(*, workspace, data, instance=None):
    return _save(model=Resource, resource="resource", fields=RESOURCE_FIELDS, validator=validate_resource, workspace=workspace, data=data, instance=instance)


def save_resource_rate(*, workspace, data, instance=None):
    # New rates are DRAFT/NULL actor; adding a new dated row preserves history.
    return _save(model=ResourceRate, resource="resource_rate", fields=RATE_FIELDS, validator=validate_resource_rate, workspace=workspace, data=data, instance=instance)
