"""PriceScenario's inspected database contract; no synthetic lifecycle values."""
METHODS = (("MARGIN", "Biên lợi nhuận mục tiêu"), ("MARKUP", "Tỷ lệ cộng trên giá vốn"), ("PROFIT_PER_UNIT", "Lợi nhuận trên một đơn vị"))
STATUSES = (("DRAFT", "Nháp"), ("CALCULATED", "Đã tính"), ("IN_REVIEW", "Chờ duyệt (dữ liệu cũ)"), ("APPROVED", "Đã duyệt (dữ liệu cũ)"), ("EXPIRED", "Hết hiệu lực"), ("CANCELLED", "Đã hủy"))
FIELDS = ("code", "name", "base_run", "channel", "pricing_method", "target_margin", "target_markup", "target_profit_per_unit", "minimum_price", "currency_code", "valid_from", "valid_to")
