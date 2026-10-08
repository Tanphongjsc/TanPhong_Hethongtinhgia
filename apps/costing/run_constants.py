from apps.master_data.presentation import display_label

RUN_STATUSES = tuple((code, display_label(code)) for code in ("DRAFT", "CALCULATED", "IN_REVIEW", "APPROVED", "LOCKED", "FAILED", "SUPERSEDED"))
RUN_TYPES = (("STANDARD", "Giá thành chuẩn"), ("PLANNED", "Giá thành kế hoạch"))
REQUEST_FIELDS = ("product", "sku", "scheme", "costing_date", "quantity", "quantity_uom", "result_currency_code", "run_type", "packaging_quantity", "packaging_uom", "notes")

SOURCE_LABELS = {
    "product": "Sản phẩm", "sku": "SKU", "uom": "Đơn vị tính", "uom_category": "Nhóm đơn vị tính", "currency": "Tiền tệ",
    "costing_scheme": "Phương án tính giá thành", "costing_scheme_version": "Phiên bản phương án", "costing_scheme_line": "Thành phần tính giá",
    "cost_element": "Phần tử chi phí", "formula": "Công thức", "formula_version": "Phiên bản công thức",
    "recipe": "Định mức nguyên vật liệu", "recipe_version": "Phiên bản định mức", "recipe_line": "Thành phần định mức",
    "packaging_config": "Cấu hình bao bì", "packaging_config_version": "Phiên bản bao bì", "packaging_line": "Thành phần bao bì", "sku_packaging_assignment": "Gán bao bì cho SKU",
    "routing": "Quy trình sản xuất", "routing_version": "Phiên bản quy trình", "routing_operation": "Công đoạn",
    "resource": "Nguồn lực", "resource_rate": "Đơn giá nguồn lực", "work_center": "Trung tâm sản xuất",
    "supplier": "Nhà cung cấp", "supplier_price": "Giá nhà cung cấp", "item": "Vật tư / Hàng hóa", "uom_conversion": "Quy đổi đơn vị",
    "cost_pool": "Nhóm chi phí chung", "cost_pool_period": "Số liệu kỳ chi phí", "allocation_rule": "Quy tắc phân bổ",
}
