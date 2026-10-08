"""Developer-defined resolver codes, not new database enums or executable config."""
from .errors import CostingError
from .resolvers.allocation import allocation_rule

RESOLVERS = {"MATERIAL_COST": ("material", "MONEY"), "PACKAGING_COST": ("packaging", "MONEY"), "RESOURCE_COST": ("routing", "MONEY"), "RUN_QUANTITY": ("quantity", "QUANTITY")}


def check_source(row, organization, day):
    code = row.system_resolver_code or ""
    if code.startswith("ALLOCATION:") and code[11:]:
        rule = allocation_rule(organization, code[11:], day)
        if rule.basis_type != "NORMAL_CAPACITY" or rule.formula_code or rule.condition_jsonb:
            raise CostingError("Tiêu thức phân bổ chưa có hợp đồng thực thi được hỗ trợ.")
        kind = "MONEY"
    elif code in RESOLVERS: kind = RESOLVERS[code][1]
    else: raise CostingError("Mã bộ lấy dữ liệu chưa được đăng ký, chưa có bộ kiểm tra cấu hình hoặc thực thi; không thể kích hoạt hoặc chạy phương án.")
    element = row.cost_element
    if not element or element.value_type != kind:
        raise CostingError("Bộ lấy dữ liệu cần phần tử chi phí có kiểu kết quả phù hợp.")
    if kind == "MONEY" and element.default_uom_id:
        raise CostingError("Bộ lấy chi phí trả tổng tiền, không trả đơn giá theo đơn vị.")
    return kind
