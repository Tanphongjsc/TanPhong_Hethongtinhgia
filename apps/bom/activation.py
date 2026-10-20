"""Small publication checks shared by Recipe and Packaging definitions."""
from hashlib import sha256
import json

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.core.models import Uom


def require_active(*records):
    for record in records:
        if record is None:
            continue
        if not record.is_active:
            raise ValidationError("Danh mục tham chiếu đã ngừng hoạt động. Vui lòng kiểm tra trước khi kích hoạt.")
        if isinstance(record, Uom) and not record.category.is_active:
            raise ValidationError("Nhóm đơn vị tính đã ngừng hoạt động.")


def validate_activation_period(version, peers):
    start, end = version.effective_from, version.effective_to
    if not start:
        raise ValidationError("Vui lòng nhập ngày bắt đầu hiệu lực trước khi kích hoạt.")
    if end and end <= start:
        raise ValidationError("Ngày kết thúc hiệu lực phải sau ngày bắt đầu hiệu lực.")
    overlaps = peers.exclude(pk=version.pk).filter(
        status="EFFECTIVE", effective_from__isnull=False,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=start))
    if end:
        overlaps = overlaps.filter(effective_from__lte=end)
    if overlaps.exists():
        raise ValidationError(
            "Đã có phiên bản đang hiệu lực chồng khoảng ngày áp dụng. "
            "Vui lòng kiểm tra lịch sử phiên bản; hệ thống không tự thay thế nguồn đã chốt."
        )


def definition_hash(version, version_fields, lines, line_fields):
    def values(record, fields):
        return {name: getattr(record, record._meta.get_field(name).attname) for name in fields}
    content = {"version": values(version, version_fields),
               "lines": [values(line, line_fields) for line in lines]}
    return sha256(json.dumps(content, sort_keys=True, default=str,
                             separators=(",", ":")).encode("utf-8")).hexdigest()
