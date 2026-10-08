"""Vietnamese configuration display; database values and precision stay intact."""
from django.utils import timezone
from apps.master_data.presentation import display_label, format_number, format_percent
from .constants import code_label

FIELD_LABELS = {
    "code": "Mã kênh bán", "name": "Tên kênh bán", "channel_type": "Loại kênh", "platform_code": "Mã nền tảng", "market_code": "Mã thị trường", "seller_type": "Mã loại người bán", "default_currency_code": "Tiền tệ mặc định",
    "channel": "Kênh bán", "product_category": "Nhóm sản phẩm", "sku": "SKU", "fee_type": "Loại phí", "fee_base": "Cơ sở tính phí", "rate": "Tỷ lệ (%)", "fixed_amount": "Số tiền cố định", "currency_code": "Tiền tệ", "floor_amount": "Giá trị sàn", "cap_amount": "Giá trị trần", "refundable_ratio": "Tỷ lệ được hoàn (%)", "tax_inclusive": "Thuế trong phí", "priority": "Mức ưu tiên",
    "effective_from": "Hiệu lực từ ngày", "effective_to": "Hiệu lực đến ngày", "source_reference": "Nguồn tham chiếu", "status": "Trạng thái", "jurisdiction_code": "Mã khu vực áp dụng", "tax_type": "Loại thuế", "tax_class_code": "Mã nhóm thuế", "transaction_type": "Mã loại giao dịch", "tax_base": "Cơ sở tính thuế", "recoverable_ratio": "Tỷ lệ được khấu trừ (%)", "inclusive": "Thuế trong giá",
    "rate_type": "Loại tỷ giá", "from_currency_code": "Tiền tệ nguồn", "to_currency_code": "Tiền tệ đích", "effective_at": "Hiệu lực từ thời điểm", "valid_to": "Hiệu lực đến thời điểm", "source_name": "Tên nguồn dữ liệu", "is_active": "Trạng thái", "created_at": "Ngày tạo", "updated_at": "Ngày cập nhật", "date_status": "Hiệu lực theo thời gian",
}
PAGE_COLUMNS = {
    "channel": (("code", "Mã", False), ("name", "Tên kênh", False), ("channel_type", "Loại kênh", False), (None, "Thị trường", False), (None, "Tiền tệ mặc định", False), (None, "Trạng thái", False)),
    "channel_fee_rule": (("channel", "Kênh bán", False), ("fee_type", "Loại phí", False), (None, "Cơ sở tính phí", False), ("rate", "Tỷ lệ (%)", True), (None, "Số tiền cố định", True), (None, "Tiền tệ", False), (None, "Phạm vi", False), ("priority", "Ưu tiên", True), ("effective_from", "Hiệu lực từ", False), (None, "Hiệu lực đến", False), (None, "Trạng thái", False)),
    "tax_rule": (("jurisdiction_code", "Khu vực", False), ("tax_type", "Loại thuế", False), (None, "Cơ sở tính thuế", False), ("rate", "Thuế suất (%)", True), (None, "Số tiền cố định", True), (None, "Tiền tệ", False), (None, "Nhóm thuế", False), (None, "Thuế trong giá", False), ("priority", "Ưu tiên", True), ("effective_from", "Hiệu lực từ", False), (None, "Hiệu lực đến", False), (None, "Trạng thái", False)),
    "fx_rate": (("from_currency_code", "Tiền tệ nguồn", False), ("to_currency_code", "Tiền tệ đích", False), ("rate", "Tỷ giá", True), (None, "Chiều quy đổi", False), ("rate_type", "Loại tỷ giá", False), (None, "Nguồn", False), ("effective_at", "Hiệu lực từ", False), (None, "Hiệu lực đến", False), (None, "Trạng thái", False)),
}
ROW_FIELDS = {
    "channel": ("code", "name", "channel_type", "market_code", "default_currency_code", "is_active"),
    "channel_fee_rule": ("channel", "fee_type", "fee_base", "rate", "fixed_amount", "currency_code", "scope", "priority", "effective_from", "effective_to", "status"),
    "tax_rule": ("jurisdiction_code", "tax_type", "tax_base", "rate", "fixed_amount", "currency_code", "tax_class_code", "inclusive", "priority", "effective_from", "effective_to", "status"),
    "fx_rate": ("from_currency_code", "to_currency_code", "rate", "direction", "rate_type", "source_name", "effective_at", "valid_to", "status"),
}


def field_value(record, name, resource):
    if name == "direction": return f"1 {record.from_currency_code_id} = {format_number(record.rate)} {record.to_currency_code_id}"
    if name == "scope": return " · ".join(f"{ref.code} — {ref.name}" for ref in (record.product_category, record.sku) if ref) or "Mọi SKU trong kênh"
    value = getattr(record, name, None)
    if name in ("inclusive", "tax_inclusive"): return "Giá đã bao gồm thuế" if value else "Giá chưa bao gồm thuế"
    if name == "is_active": return display_label("ACTIVE" if value else "INACTIVE")
    if (name == "rate" and resource != "fx_rate") or name in ("refundable_ratio", "recoverable_ratio"): return format_percent(value)
    if name in ("rate", "fixed_amount", "cap_amount", "floor_amount", "priority"): return format_number(value)
    if name in ("effective_from", "effective_to"): return value.strftime("%d/%m/%Y") if value else "—"
    if name in ("effective_at", "valid_to", "created_at", "updated_at"): return timezone.localtime(value).strftime("%d/%m/%Y %H:%M:%S") if value else "—"
    if name in ("fee_type", "fee_base", "tax_type", "tax_base", "rate_type"): return code_label(value)
    if name in ("status", "date_status", "channel_type"): return display_label(value)
    if hasattr(value, "code"): return f"{value.code} — {value.name}"
    return value or "—"


def decorate(record, resource):
    record.cells = [{"value": field_value(record, name, resource), "numeric": PAGE_COLUMNS[resource][index][2], "technical": name in ("code", "jurisdiction_code", "market_code", "tax_class_code"), "status": ("ACTIVE" if record.is_active else "INACTIVE") if name == "is_active" else record.status if name == "status" else None, "date_status": getattr(record, "date_status", None) if name == "status" else None} for index, name in enumerate(ROW_FIELDS[resource])]
    record.pricing_editable = resource == "channel" or record.status == "DRAFT"
    return record
