"""Developer-owned allow-list, arity and help. No dynamic function lookup."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class Function:
    minimum: int
    maximum: int
    signature: str
    description: str
    implementation: object = None


def round_decimal(value, scale):
    return value.quantize(Decimal(1).scaleb(-int(scale)), rounding=ROUND_HALF_UP)


FUNCTIONS = {
    "ROUND": Function(2, 2, "ROUND(value, scale)", "Làm tròn nửa lên bằng Decimal; số chữ số từ 0 đến 12.", round_decimal),
    "MIN": Function(2, 20, "MIN(a, b, …)", "Lấy giá trị nhỏ nhất trong các giá trị cùng kiểu và đơn vị.", min),
    "MAX": Function(2, 20, "MAX(a, b, …)", "Lấy giá trị lớn nhất trong các giá trị cùng kiểu và đơn vị.", max),
    "ABS": Function(1, 1, "ABS(value)", "Lấy giá trị tuyệt đối.", abs),
    "IF": Function(3, 3, "IF(condition, a, b)", "Chọn một nhánh theo điều kiện Có / Không; chỉ tính nhánh được chọn."),
}
