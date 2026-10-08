"""Atomic overhead configuration persistence, no calculation or target resolution."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import AllocationRule, CostPool, Uom
from apps.master_data.access import require_write_access
from .overhead_constants import ALLOCATION_RULE_FIELDS, COST_POOL_FIELDS
from .overhead_validators import normalize_overhead_values, validate_allocation_rule, validate_cost_pool


def _database_error(error):
    constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "")
    duplicate = {"uq_cost_pool": "Mã nhóm chi phí đã tồn tại.", "uq_allocation_rule": "Mã quy tắc phân bổ đã tồn tại."}
    if constraint in duplicate:
        raise ValidationError({"code": duplicate[constraint]}) from None
    field = {"ck_cost_pool_type": "pool_type", "ck_allocation_basis": "basis_type",
        "ck_allocation_rule_period": "effective_to", "allocation_rule_pool_id_fkey": "pool",
        "allocation_rule_basis_uom_id_fkey": "basis_uom"}.get(constraint)
    message = "Dữ liệu không còn hợp lệ. Vui lòng kiểm tra và thử lại."
    raise ValidationError({field: message} if field else message) from None


def _locked_record(model, instance, organization):
    if instance is None:
        return model(organization=organization)
    try:
        return model.objects.select_for_update().get(pk=instance.pk, organization=organization)
    except model.DoesNotExist:
        raise ValidationError("Không tìm thấy dữ liệu của hệ thống.") from None


def _assign(record, values):
    for field, value in values.items():
        setattr(record, field, value)
    record.full_clean(exclude=("condition_jsonb",) if isinstance(record, AllocationRule) else (), validate_unique=False, validate_constraints=False)


def save_cost_pool(*, workspace, data, instance=None):
    require_write_access(workspace, resource="cost_pool", editing=instance is not None)
    values = normalize_overhead_values({field: data.get(field) for field in COST_POOL_FIELDS})
    try:
        with transaction.atomic():
            record = _locked_record(CostPool, instance, workspace.organization)
            validate_cost_pool(data=values, organization=workspace.organization, instance=record)
            _assign(record, values)
            record.updated_at = timezone.now()
            record.save(force_insert=instance is None, force_update=instance is not None)
            return record
    except IntegrityError as error:
        _database_error(error)


def save_allocation_rule(*, workspace, data, instance=None):
    require_write_access(workspace, resource="allocation_rule", editing=instance is not None)
    values = normalize_overhead_values({field: data.get(field) for field in ALLOCATION_RULE_FIELDS})
    try:
        with transaction.atomic():
            record = _locked_record(AllocationRule, instance, workspace.organization)
            # Refresh references inside the transaction, avoiding stale active/scope checks.
            for field, model in (("pool", CostPool), ("basis_uom", Uom)):
                reference = values.get(field)
                if reference is None:
                    continue
                if not isinstance(reference, model):
                    raise ValidationError({field: "Danh mục tham chiếu không hợp lệ."})
                query = model.objects.select_for_update()
                if model is CostPool:
                    query = query.filter(organization=workspace.organization)
                try:
                    values[field] = query.get(pk=reference.pk)
                except model.DoesNotExist:
                    raise ValidationError({field: "Danh mục không còn tồn tại hoặc không thuộc dữ liệu hệ thống."}) from None
            validate_allocation_rule(data=values, organization=workspace.organization, instance=record)
            _assign(record, values)
            # New rules use model defaults DRAFT/{}/NULL actor; edits preserve them.
            record.save(force_insert=instance is None, force_update=instance is not None)
            return record
    except IntegrityError as error:
        _database_error(error)
