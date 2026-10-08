"""Type/unit checks without implicit currency/UoM conversion."""
from dataclasses import dataclass
from decimal import Decimal
from .ast_nodes import Node, walk
from .errors import FormulaError
from .functions import FUNCTIONS
from .limits import limits
from .parser import PRECEDENCE

NUMERIC = frozenset(("MONEY", "NUMBER", "PERCENT", "QUANTITY"))


@dataclass(frozen=True)
class ValueType:
    kind: str
    dimension: str = ""
    currency: str = ""
    unit: object = None

    @property
    def scalar(self):
        return self.kind in ("NUMBER", "PERCENT") and not (self.dimension or self.currency or self.unit)

    def compatible(self, other):
        return self == other or (self.scalar and other.scalar)


def element_type(element):
    if element is None:
        return None
    dimension = (element.dimension_code or "").upper()
    if not dimension and element.default_uom:
        dimension = element.default_uom.category.dimension_code.upper()
    if element.value_type == "MONEY" and not dimension:
        dimension = "MONEY"
    if element.value_type in ("BOOLEAN", "TEXT") or (element.value_type in ("NUMBER", "PERCENT") and dimension in ("", "NUMBER", "PERCENT", "RATIO", "DIMENSIONLESS")):
        dimension = ""
    return ValueType(element.value_type, dimension, element.currency_code_id or "", element.default_uom_id)


def same_type(a, b, node):
    if not a.compatible(b):
        raise FormulaError("Kiểu dữ liệu hoặc đơn vị của các thành phần không tương thích; không tự quy đổi.", position=node.position)
    return a


def validate(root, symbols, output=None):
    pending, count = [(root, 1)], 0
    config = limits()
    while pending:
        node, depth = pending.pop()
        count += 1
        if not isinstance(node, Node) or count > config.nodes or depth > config.depth:
            raise FormulaError("Cấu trúc AST không hợp lệ hoặc vượt giới hạn.")
        arity = {"number": 0, "text": 0, "boolean": 0, "symbol": 0, "element": 0, "formula": 0, "unary": 1, "binary": 2}.get(node.kind)
        if arity is not None and len(node.children) != arity:
            raise FormulaError("Số thành phần của nút AST không hợp lệ.")
        if node.kind == "call":
            function = FUNCTIONS.get(node.value)
            if function is None or not function.minimum <= len(node.children) <= function.maximum:
                raise FormulaError("Hàm hoặc số tham số không được phép.")
        if node.kind == "binary" and node.value not in PRECEDENCE:
            raise FormulaError("Toán tử không được phép.")
        if node.kind == "unary" and node.value not in ("+", "-", "NOT"):
            raise FormulaError("Toán tử không được phép.")
        pending.extend((child, depth+1) for child in node.children)
    types = {}
    for node in reversed(list(walk(root))):
        args = [types[id(child)] for child in node.children]
        def numeric():
            if any(argument.kind not in NUMERIC for argument in args):
                raise FormulaError("Phép tính yêu cầu giá trị số.", position=node.position)
        if node.kind == "number":
            result = ValueType("NUMBER")
        elif node.kind == "text":
            result = ValueType("TEXT")
        elif node.kind == "boolean":
            result = ValueType("BOOLEAN")
        elif node.kind in ("symbol", "element", "formula"):
            result = symbols.get((node.kind, node.value))
            if result is None:
                raise FormulaError(f'Không tìm thấy biến hoặc công thức "{node.value}".', position=node.position)
        elif node.kind == "unary":
            if node.value == "NOT":
                if args[0].kind != "BOOLEAN":
                    raise FormulaError("NOT yêu cầu điều kiện Có / Không.", position=node.position)
                result = ValueType("BOOLEAN")
            else:
                numeric(); result = args[0]
        elif node.kind == "binary":
            a, b = args
            if node.value in ("AND", "OR"):
                if any(argument.kind != "BOOLEAN" for argument in args):
                    raise FormulaError("AND / OR yêu cầu điều kiện Có / Không.", position=node.position)
                result = ValueType("BOOLEAN")
            elif node.value in (">", ">=", "<", "<=", "==", "!="):
                same_type(a, b, node)
                if node.value not in ("==", "!=") and a.kind not in NUMERIC:
                    raise FormulaError("So sánh thứ tự chỉ hỗ trợ giá trị số.", position=node.position)
                result = ValueType("BOOLEAN")
            else:
                numeric()
                if node.value in ("+", "-", "%"):
                    result = same_type(a, b, node)
                elif node.value == "*":
                    if a.scalar: result = b
                    elif b.scalar: result = a
                    else: raise FormulaError("Chưa hỗ trợ nhân hai đại lượng có đơn vị.", position=node.position)
                else:
                    if b.scalar: result = a
                    elif a.compatible(b): result = ValueType("NUMBER")
                    else: raise FormulaError("Chưa hỗ trợ phép chia tạo đại lượng phái sinh.", position=node.position)
        elif node.kind == "call":
            if node.value == "IF":
                if args[0].kind != "BOOLEAN":
                    raise FormulaError("Điều kiện IF phải có kiểu Có / Không.", position=node.position)
                result = same_type(args[1], args[2], node)
            elif node.value == "ROUND":
                if args[0].kind not in NUMERIC or node.children[1].kind != "number":
                    raise FormulaError("ROUND yêu cầu giá trị số và số chữ số là hằng số nguyên từ 0 đến 12.", position=node.position)
                scale = Decimal(node.children[1].value)
                if scale != scale.to_integral_value() or not 0 <= scale <= 12:
                    raise FormulaError("Số chữ số làm tròn phải là số nguyên từ 0 đến 12.", position=node.position)
                result = args[0]
            else:
                numeric(); result = args[0]
                for argument in args[1:]: same_type(result, argument, node)
        else:
            raise FormulaError("Loại nút biểu thức không được phép.")
        types[id(node)] = result
    result = types[id(root)]
    if output and not output.compatible(result):
        raise FormulaError("Kiểu hoặc đơn vị kết quả không khớp phần tử chi phí đầu ra.")
    return result
