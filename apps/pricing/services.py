"""Atomic configuration writes. Actors stay NULL; no approval or calculation."""
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils import timezone
from apps.master_data.access import require_write_access
from .constants import FIELDS, MODELS
from .validators import normalize_values, validate_values


def save_record(*, resource, workspace, data, instance=None):
    require_write_access(workspace, resource=resource, editing=instance is not None)
    model = MODELS[resource]
    try:
        with transaction.atomic():
            record = model(organization=workspace.organization)
            if instance:
                try: record = model.objects.select_for_update().get(pk=instance.pk, organization=workspace.organization)
                except model.DoesNotExist: raise ValidationError("Không tìm thấy dữ liệu của hệ thống.") from None
                if resource != "channel" and record.status != "DRAFT":
                    raise ValidationError("Bản đã chốt chỉ được xem. Hãy thêm bản mới cho kỳ áp dụng mới.")
            values = normalize_values({name: data.get(name) for name in FIELDS[resource]})
            # Refresh each reference before validating; reject stale/inactive or
            # foreign-company inputs even if a caller bypasses the HTML form.
            for name in FIELDS[resource]:
                field = model._meta.get_field(name)
                ref = values[name]
                if not field.is_relation or ref is None: continue
                related = field.remote_field.model
                if not isinstance(ref, related): raise ValidationError({name: "Tham chiếu không hợp lệ."})
                query = related.objects.select_for_update(of=("self",)).filter(pk=ref.pk)
                if any(f.name == "organization" for f in related._meta.fields): query = query.filter(organization=workspace.organization)
                if name == "sku": query = query.select_related("product")
                ref = query.first()
                if not ref or (not ref.is_active and getattr(record, name + "_id") != ref.pk):
                    raise ValidationError({name: "Tham chiếu đã ngừng hoạt động hoặc không thuộc dữ liệu hệ thống."})
                values[name] = ref
            validate_values(resource=resource, data=values, organization=workspace.organization, instance=record)
            for name, value in values.items(): setattr(record, name, value)
            if hasattr(record, "created_by") and not instance: record.created_by = None
            if resource == "channel": record.updated_at = timezone.now()
            record.full_clean(validate_unique=False, validate_constraints=False)
            record.save(force_insert=instance is None, force_update=instance is not None)
            return record
    except DatabaseError as error:
        state = getattr(error.__cause__, "sqlstate", None)
        constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", "")
        if constraint == "uq_channel": raise ValidationError({"code": "Mã kênh bán đã tồn tại."}) from None
        if state in ("23502", "23503", "23505", "23514", "22003"):
            raise ValidationError("Dữ liệu không còn hợp lệ hoặc vượt giới hạn lưu trữ. Vui lòng kiểm tra và thử lại.") from None
        raise


def save_channel(**kwargs): return save_record(resource="channel", **kwargs)
def save_channel_fee_rule(**kwargs): return save_record(resource="channel_fee_rule", **kwargs)
def save_tax_rule(**kwargs): return save_record(resource="tax_rule", **kwargs)
def save_fx_rate(**kwargs): return save_record(resource="fx_rate", **kwargs)


def close_period(*, resource, workspace, instance, end):
    """Explicit future end only; never alter amount, scope, past dates or status."""
    if resource not in ("channel_fee_rule", "tax_rule", "fx_rate"):
        raise ValidationError("Danh mục này không có khoảng hiệu lực.")
    require_write_access(workspace, resource=resource, editing=True)
    model = MODELS[resource]
    with transaction.atomic():
        try: record = model.objects.select_for_update().get(pk=instance.pk, organization=workspace.organization)
        except model.DoesNotExist: raise ValidationError("Không tìm thấy dữ liệu.") from None
        start_name, end_name, now = ("effective_at", "valid_to", timezone.now()) if resource == "fx_rate" else ("effective_from", "effective_to", timezone.localdate())
        if record.status != "EFFECTIVE" or getattr(record, end_name) is not None:
            raise ValidationError("Chỉ kết thúc bản đang hiệu lực và chưa có mốc kết thúc.")
        if end is None or end <= now or end <= getattr(record, start_name):
            raise ValidationError({end_name: "Mốc kết thúc phải trong tương lai và sau mốc bắt đầu hiệu lực."})
        setattr(record, end_name, end)
        record.save(update_fields=[end_name])
        return record
