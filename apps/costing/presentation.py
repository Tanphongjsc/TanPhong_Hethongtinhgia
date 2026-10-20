"""Read-only presentation of saved costing data; no ORM or cost calculations."""
from .run_constants import SOURCE_LABELS


TRACE_LABELS = {
    "Hệ số sản lượng": "Hệ số điều chỉnh theo sản lượng",
    "Số lượng theo đơn vị giá": "Số lượng tính tiền",
    "Số lượng sau hao hụt": "Lượng cần dùng sau thu hồi và hao hụt",
    "Giá trị được sử dụng": "Kết quả sau làm tròn",
    "Số chữ số": "Số chữ số sau dấu phẩy",
    "Đầu vào": "Giá trị đầu vào",
}
OPERATIONS = {
    "+": "Cộng (+)", "-": "Trừ / Đổi dấu (−)", "*": "Nhân (×)", "/": "Chia (÷)",
    "%": "Lấy phần dư (%)", "ROUND": "Làm tròn (ROUND)", "SUM": "Cộng tổng (SUM)",
    "MIN": "Lấy nhỏ nhất (MIN)", "MAX": "Lấy lớn nhất (MAX)", "ABS": "Lấy trị tuyệt đối (ABS)",
    "IF": "Chọn theo điều kiện (IF)", "AND": "Đồng thời (AND)", "OR": "Hoặc (OR)", "NOT": "Phủ định (NOT)",
}


def snapshot_fields(snapshot, table, reference):
    return snapshot.get("sources", {}).get(f"{table}:{reference}", {}).get("fields", {})


def saved_unit(snapshot, reference):
    if reference in (None, ""):
        return ""
    fields = snapshot_fields(snapshot, "uom", reference)
    return fields.get("name") or fields.get("code") or f"Đơn vị #{reference}"


def source_identity(snapshot, source):
    fields, table = source.get("fields", {}), source.get("table", "")
    code, name = fields.get("code", ""), fields.get("name", "")
    parent = {
        "recipe_version": ("recipe", "recipe_id"),
        "packaging_config_version": ("packaging_config", "packaging_config_id"),
        "routing_version": ("routing", "routing_id"),
        "costing_scheme_version": ("costing_scheme", "scheme_id"),
        "formula_version": ("formula", "formula_id"),
        "resource_rate": ("resource", "resource_id"),
        "cost_pool_period": ("cost_pool", "pool_id"),
        "recipe_line": ("item", "component_item_id"),
        "packaging_line": ("item", "packaging_item_id"),
        "supplier_price": ("item", "item_id"),
        "sku_packaging_assignment": ("sku", "sku_id"),
    }.get(table)
    if parent and not name:
        data = snapshot_fields(snapshot, parent[0], fields.get(parent[1]))
        code, name = code or data.get("code", ""), data.get("name", "")
    if table == "routing_operation":
        code, name = fields.get("operation_code", ""), fields.get("operation_name", "")
    detail = ""
    if table == "supplier_price":
        supplier = snapshot_fields(snapshot, "supplier", fields.get("supplier_id"))
        detail = supplier.get("name") or supplier.get("code") or ""
    return code, name or SOURCE_LABELS.get(table, "Nguồn dữ liệu"), detail


def source_groups(snapshot):
    groups = {}
    for source in snapshot.get("sources", {}).values():
        table, fields = source.get("table", ""), source.get("fields", {})
        if table in ("supplier", "supplier_price", "resource_rate", "cost_pool", "cost_pool_period", "allocation_rule"):
            group = "Đơn giá và chi phí phân bổ"
        elif table.startswith(("recipe", "packaging", "routing", "sku_packaging")):
            group = "Định mức, bao bì và công đoạn"
        elif table.startswith(("costing_scheme", "formula")) or table == "cost_element":
            group = "Phương án và công thức"
        else:
            group = "Sản phẩm, vật tư và đơn vị"
        code, name, detail = source_identity(snapshot, source)
        groups.setdefault(group, []).append({"label": SOURCE_LABELS.get(table, "Nguồn dữ liệu"),
            "code": code, "name": name, "detail": detail, "reference": source.get("id"),
            "version": fields.get("version_no"), "from": fields.get("effective_from", fields.get("period_start")),
            "to": fields.get("effective_to", fields.get("period_end"))})
    return [{"title": title, "rows": rows} for title, rows in groups.items()]


def trace_presentation(run, line, steps):
    snapshot = run.version_snapshot_jsonb
    elements = {source.get("fields", {}).get("code", "").upper(): source.get("fields", {})
        for source in snapshot.get("sources", {}).values() if source.get("table") == "cost_element"}
    inputs = []
    formula_inputs = line.input_snapshot_jsonb.get("inputs", {}) if line.source_mode == "FORMULA" else {}
    for code, value in formula_inputs.items():
        fields = elements.get(code.upper(), {})
        inputs.append({"code": code, "name": fields.get("name", code), "value": value,
            "kind": fields.get("value_type"), "unit": fields.get("currency_code_id") if fields.get("value_type") == "MONEY" else saved_unit(snapshot, fields.get("default_uom_id"))})
    sections, materials = [], []
    for number, entry in enumerate(steps, 1):
        fields = dict(entry.get("fields", []))
        if {"Phép tính", "Đầu vào", "Kết quả"}.issubset(fields):
            if not sections or sections[-1]["kind"] != "calculations":
                sections.append({"kind": "calculations", "rows": []})
            operation = fields.get("Phép tính", "")
            sections[-1]["rows"].append({"operation": OPERATIONS.get(operation, operation),
                "arguments": fields.get("Đầu vào", []), "value": fields.get("Kết quả"),
                "title": entry.get("title", ""), "metadata": [(label, value) for label, value in entry.get("fields", [])
                    if label not in ("Phép tính", "Đầu vào", "Kết quả")]})
            continue
        facts = [{"label": TRACE_LABELS.get(label, label), "value": value,
            "percent": label in ("Tỷ lệ thu hồi", "Tỷ lệ hao hụt"),
            "code": label in ("Định mức", "Cấu hình", "Dòng", "Biểu thức"), "wide": label == "Biểu thức"}
            for label, value in entry.get("fields", [])]
        sections.append({"kind": "facts", "title": ("Làm tròn kết quả của khoản chi phí" if entry.get("title") == "Làm tròn tại ranh giới phần tử chi phí" else entry.get("title", "Chi tiết")), "number": number, "fields": facts,
            "expanded": entry.get("title") in ("Quy mô định mức", "Cơ sở đóng gói do người chạy xác định") or entry.get("title", "").startswith("Công thức ")})
        if "Giá tham chiếu" in fields and "Thành tiền" in fields:
            price = snapshot_fields(snapshot, "supplier_price", fields["Giá tham chiếu"])
            item = snapshot_fields(snapshot, "item", price.get("item_id"))
            materials.append({"title": item.get("name") or entry.get("title"), "code": item.get("code", ""), "supplier": fields.get("Nhà cung cấp"),
                "quantity": fields.get("Số lượng theo đơn vị giá"), "unit": fields.get("Đơn vị tính giá"),
                "price": fields.get("Đơn giá"), "currency": fields.get("Tiền tệ"), "amount": fields.get("Thành tiền")})
    values = {"MONEY": "amount", "QUANTITY": "quantity", "NUMBER": "number_value", "PERCENT": "percent_value", "BOOLEAN": "boolean_value", "TEXT": "text_value"}
    return {"sections": sections, "materials": materials, "inputs": inputs,
        "value": getattr(line, values.get(line.value_type, "text_value"), None),
        "unit": line.currency_code_id or line.input_snapshot_jsonb.get("unit_label", "")}