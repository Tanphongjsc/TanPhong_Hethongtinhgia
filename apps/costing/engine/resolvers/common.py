from django.db.models import Q
from ..errors import CostingError


def dated(query, day):
    return query.filter(effective_from__lte=day).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))


def bounded(query, maximum=2000):
    rows = list(query[:maximum + 1])
    if len(rows) > maximum:
        raise CostingError("Nguồn dữ liệu vượt giới hạn của một lần tính giá.", code="SOURCE_LIMIT", stage="resolution")
    return rows


def one(query, label):
    rows = list(query[:2])
    if not rows: raise CostingError(f"Không tìm thấy {label} có hiệu lực tại ngày tính giá.", code="MISSING_SOURCE", stage="resolution")
    if len(rows) > 1: raise CostingError(f"Có nhiều {label} phù hợp; chưa có quy tắc chọn nguồn. Vui lòng xử lý dữ liệu mơ hồ.", code="AMBIGUOUS_SOURCE", stage="resolution")
    return rows[0]


def active(ctx, *records):
    for record in records:
        if record is None: continue
        if hasattr(record, "organization_id") and record.organization_id not in (None, ctx.organization.pk):
            raise CostingError("Nguồn dữ liệu không thuộc hệ thống.", stage="resolution")
        if hasattr(record, "is_active") and not record.is_active:
            raise CostingError(f"Nguồn dữ liệu {getattr(record, 'code', '')} đã ngừng hoạt động.", stage="resolution")
    ctx.remember(*records)
