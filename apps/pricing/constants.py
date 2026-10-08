"""Fields and the single inspected Channel enum; free business codes stay free."""
from apps.core.models import Channel, ChannelFeeRule, TaxRule, FxRate
from apps.master_data.presentation import display_label

CHANNEL_TYPES = tuple((code, display_label(code)) for code in ("B2B", "RETAIL", "ECOMMERCE", "EXPORT", "D2C", "OTHER"))
LIFECYCLE = (("DRAFT", "Nháp"), ("EFFECTIVE", "Đang hiệu lực"))
LEGACY_STATUSES = (*LIFECYCLE, ("RETIRED", "Ngừng hiệu lực"), ("IN_REVIEW", "Chờ duyệt (dữ liệu cũ)"), ("APPROVED", "Đã duyệt (dữ liệu cũ)"))
CHANNEL_FIELDS = ("code", "name", "channel_type", "platform_code", "market_code", "seller_type", "default_currency_code", "is_active")
FEE_FIELDS = ("channel", "product_category", "sku", "fee_type", "fee_base", "rate", "fixed_amount", "currency_code", "cap_amount", "floor_amount", "refundable_ratio", "tax_inclusive", "priority", "effective_from", "effective_to", "source_reference", "status")
TAX_FIELDS = ("jurisdiction_code", "tax_type", "tax_class_code", "seller_type", "transaction_type", "rate", "fixed_amount", "currency_code", "tax_base", "recoverable_ratio", "inclusive", "priority", "effective_from", "effective_to", "source_reference", "status")
FX_FIELDS = ("rate_type", "from_currency_code", "to_currency_code", "rate", "effective_at", "valid_to", "source_name", "source_reference", "status")
MODELS = {"channel": Channel, "channel_fee_rule": ChannelFeeRule, "tax_rule": TaxRule, "fx_rate": FxRate}
FIELDS = dict(zip(MODELS, (CHANNEL_FIELDS, FEE_FIELDS, TAX_FIELDS, FX_FIELDS)))
LABELS = {"channel": "kênh bán", "channel_fee_rule": "quy tắc phí kênh", "tax_rule": "quy tắc thuế", "fx_rate": "tỷ giá"}
TITLES = {"channel": "Kênh bán", "channel_fee_rule": "Quy tắc phí kênh", "tax_rule": "Quy tắc thuế", "fx_rate": "Tỷ giá"}

# Display only, not a list of permitted values or calculation implementations.
CODE_LABELS = {
    "COMMISSION": "Hoa hồng", "PAYMENT_FEE": "Phí thanh toán", "FULFILLMENT": "Phí xử lý đơn",
    "PERCENTAGE": "Theo tỷ lệ %", "FIXED": "Số tiền cố định", "PER_UNIT": "Theo đơn vị",
    "PER_ORDER": "Theo đơn hàng", "TIERED": "Theo bậc", "LIST_PRICE": "Giá niêm yết",
    "ACTUAL_PAID": "Số tiền thực trả", "PAYMENT_BASE": "Cơ sở thanh toán", "PAYOUT": "Tiền đối soát",
    "SELLING_PRICE": "Giá bán", "NET_PRICE": "Giá thuần", "PRICE_AFTER_FEE": "Giá sau phí",
    "ORDER_VALUE": "Giá trị đơn hàng", "QUANTITY": "Số lượng", "WEIGHT": "Khối lượng",
    "VAT": "Thuế giá trị gia tăng (VAT)", "SPOT": "Giao ngay", "REFERENCE": "Tham chiếu",
    "ACCOUNTING": "Kế toán", "NEGOTIATED": "Thỏa thuận", "SETTLEMENT": "Thanh toán",
}


def code_label(value):
    return CODE_LABELS.get(value, value or "—")
