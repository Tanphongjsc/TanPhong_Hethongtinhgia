"""Vietnamese display vocabulary; persisted codes remain unchanged."""
from decimal import Decimal, InvalidOperation
from django.utils import timezone

ENUM_LABELS = {
    "B2B": "Doanh nghiệp / Đại lý", "RETAIL": "Bán lẻ", "ECOMMERCE": "Thương mại điện tử", "D2C": "Bán trực tiếp",
    "CALCULATED": "Đã tính", "PLANNED": "Kế hoạch", "STANDARD": "Chuẩn", "ACTUAL": "Thực tế", "SCENARIO": "Kịch bản",
    "INPUT": "Dữ liệu đầu vào", "CALCULATION": "Tính toán", "SUBTOTAL": "Tổng phụ", "OUTPUT": "Đầu ra", "INFO": "Thông tin",
    "INTERNAL": "Nội bộ", "SCREEN": "Màn hình", "QUOTE": "Báo giá", "REPORT": "Báo cáo", "ALL": "Tất cả",
    "NOT_VALIDATED": "Chưa kiểm tra", "VALID": "Hợp lệ", "INVALID": "Không hợp lệ",
    "FACTORY_FIXED": "Chi phí cố định nhà máy", "FACTORY_VARIABLE": "Chi phí biến đổi nhà máy",
    "QA": "Đảm bảo chất lượng", "WAREHOUSE": "Kho vận", "EXPORT": "Xuất khẩu", "OTHER": "Khác",
    "NORMAL_CAPACITY": "Công suất bình thường", "MACHINE_HOUR": "Giờ máy", "LABOR_HOUR": "Giờ lao động",
    "KG": "Khối lượng (kg)", "UNIT": "Số đơn vị", "BATCH": "Số lô", "PALLET_DAY": "Ngày lưu pallet",
    "SHIPMENT": "Số chuyến hàng", "VALUE": "Giá trị", "CUSTOM": "Tùy chỉnh",
    "MACHINE": "Máy móc", "LABOR": "Nhân công", "WORK_CENTER": "Trung tâm sản xuất",
    "MONEY": "Tiền tệ", "NUMBER": "Số", "PERCENT": "Tỷ lệ phần trăm",
    "QUANTITY": "Số lượng", "BOOLEAN": "Có / Không", "TEXT": "Văn bản",
    "SYSTEM": "Hệ thống", "MANUAL": "Nhập thủ công", "LOOKUP": "Tra cứu",
    "FORMULA": "Công thức", "EXTERNAL": "Nguồn bên ngoài",
    "INVENTORY_COST": "Chi phí hàng tồn kho", "COMMERCIAL_COST": "Chi phí thương mại",
    "PRICING_ONLY": "Chỉ dùng cho giá bán", "ANALYTICS": "Phân tích",
    "MANUFACTURING": "Sản xuất", "LANDED": "Chi phí đến kho",
    "COST_TO_SERVE": "Chi phí phục vụ", "CHANNEL": "Kênh bán", "PRICING": "Giá bán",
    "HALF_UP": "Làm tròn nửa lên", "HALF_EVEN": "Làm tròn nửa về số chẵn",
    "UP": "Ra xa số 0", "DOWN": "Về phía số 0", "CEILING": "Về phía dương vô cùng",
    "FLOOR": "Về phía âm vô cùng",
    "ACTIVE": "Đang hoạt động", "INACTIVE": "Ngừng hoạt động",
    "DRAFT": "Nháp", "IN_REVIEW": "Chờ duyệt", "APPROVED": "Đã duyệt",
    "EFFECTIVE": "Đang hiệu lực", "RETIRED": "Ngừng hiệu lực", "REJECTED": "Bị từ chối",
    "FAILED": "Thất bại", "LOCKED": "Đã khóa", "SUPERSEDED": "Đã thay thế", "CANCELLED": "Đã hủy", "CALCULATED": "Đã tính",
    "RAW_MATERIAL": "Nguyên liệu", "PACKAGING": "Bao bì",
    "SEMI_FINISHED": "Bán thành phẩm", "FINISHED_GOOD": "Thành phẩm",
    "SERVICE": "Dịch vụ", "BY_PRODUCT": "Phụ phẩm",
    "FUTURE": "Sắp hiệu lực", "EXPIRED": "Hết hiệu lực",
    "UNDATED": "Chưa đặt hiệu lực",
    "PRIMARY": "Cấp 1 · Bao bì trực tiếp", "SECONDARY": "Cấp 2 · Bao bì nhóm",
    "TERTIARY": "Cấp 3 · Bao bì vận chuyển", "PALLET": "Kiện trên pallet", "CONTAINER": "Công-ten-nơ",
}


def display_label(code):
    # Unknown values are business technical codes, never rewritten or stored.
    return ENUM_LABELS.get(code, code)


def format_percent(value):
    if value is None: return "—"
    try: value = Decimal(str(value))
    except (InvalidOperation, ValueError): return "—"
    return f"{format_number(value * Decimal(100))}%" if value.is_finite() else "—"


def format_number(value):
    """Vietnamese separators, no insignificant zeroes; preserve all precision."""
    if value is None or value == "":
        return "—"
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            return "—"
    except (InvalidOperation, ValueError):
        return str(value)
    formatted = format(number, ",f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted.translate(str.maketrans({",": ".", ".": ","}))


def supplier_detail_fields(record):
    currency = record.default_currency_code
    return (("Mã", record.code), ("Tên nhà cung cấp", record.name), ("Mã số thuế", record.tax_code or "—"),
        ("Tiền tệ mặc định", f"{currency.code} — {currency.name}" if currency else "—"),
        ("Điều khoản thanh toán", record.payment_terms or "—"),
        ("Ngày tạo", timezone.localtime(record.created_at).strftime("%d/%m/%Y %H:%M")),
        ("Ngày cập nhật", timezone.localtime(record.updated_at).strftime("%d/%m/%Y %H:%M")))


def supplier_price_detail_fields(record):
    return (
        ("Nhà cung cấp", f"{record.supplier.code} — {record.supplier.name}"),
        ("Vật tư / Hàng hóa", f"{record.item.code} — {record.item.name}"),
        ("Đơn giá", f"{format_number(record.unit_price)} {record.currency_code_id}"),
        ("Tiền tệ", f"{record.currency_code.code} — {record.currency_code.name}"),
        ("Đơn vị tính", f"{record.price_uom.name} ({record.price_uom.symbol})"),
        ("Số lượng tối thiểu", format_number(record.min_qty)),
        ("Đơn giá đã gồm thuế", "Có" if record.tax_inclusive else "Không"),
        ("Tỷ lệ thuế", f"{format_number(record.tax_rate * 100)}%" if record.tax_rate is not None else "—"),
        ("Tỷ lệ thuế được khấu trừ", f"{format_number(record.tax_recoverable_ratio * 100)}%"),
        ("Hiệu lực từ ngày", record.effective_from.strftime("%d/%m/%Y")),
        ("Hiệu lực đến ngày", record.effective_to.strftime("%d/%m/%Y") if record.effective_to else "Không giới hạn"),
        ("Nguồn dữ liệu", record.source_type or "—"), ("Tham chiếu / Số báo giá", record.source_reference or "—"),
        ("Ngày tạo", timezone.localtime(record.created_at).strftime("%d/%m/%Y %H:%M")),
    )
