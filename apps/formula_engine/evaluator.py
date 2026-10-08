"""Iterative AST interpreter. No ORM, I/O, Python source execution or recursion."""
from dataclasses import dataclass
from decimal import Decimal, DecimalException, localcontext
import operator
from .errors import FormulaError
from .functions import FUNCTIONS
from .limits import limits
from .validator import NUMERIC

OPERATORS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv,
    "%": operator.mod, ">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le,
    "==": operator.eq, "!=": operator.ne}


@dataclass
class Budget:
    remaining: int

    def spend(self):
        self.remaining -= 1
        if self.remaining < 0:
            raise FormulaError("Kiểm thử vượt giới hạn thực thi.", category="evaluation")


@dataclass(frozen=True)
class EvaluationResult:
    value: object
    data_type: str
    trace: tuple
    warnings: tuple = ()


def checked_value(value, spec):
    if spec.kind in NUMERIC:
        # Deliberately reject bool/float; all numeric input must preserve Decimal.
        if not isinstance(value, Decimal) or not value.is_finite():
            raise FormulaError("Dữ liệu số không hợp lệ; yêu cầu Decimal hữu hạn.", category="evaluation")
        config = limits()
        if len(value.as_tuple().digits) > config.numeric_digits or (value and abs(value.adjusted()) > config.magnitude):
            raise FormulaError("Giá trị số vượt giới hạn cho phép.", category="evaluation")
    elif spec.kind == "BOOLEAN":
        if type(value) is not bool:
            raise FormulaError("Dữ liệu phải là Có / Không.", category="evaluation")
    elif spec.kind == "TEXT":
        if type(value) is not str or len(value) > limits().expression_length:
            raise FormulaError("Dữ liệu văn bản không hợp lệ.", category="evaluation")
    else:
        raise FormulaError("Kiểu dữ liệu chưa được hỗ trợ.", category="evaluation")
    return value


def evaluate(root, context, result_type, *, budget=None, symbol_types=None):
    from .dependencies import references
    from .validator import ValueType, validate
    for key in references(root):
        if key not in context:
            raise FormulaError(f'Thiếu dữ liệu cho biến "{key[1]}".', category="evaluation")
    if symbol_types is None:
        symbol_types = {key: ValueType("NUMBER" if isinstance(value, Decimal) else "BOOLEAN" if type(value) is bool else "TEXT")
            for key, value in context.items()}
    validate(root, symbol_types, result_type)
    for key, value in context.items():
        if key in symbol_types: checked_value(value, symbol_types[key])
    budget = budget or Budget(limits().steps)
    values, trace = {}, []
    stack = [(root, 0)]
    with localcontext() as decimal_context:
        decimal_context.prec = limits().precision
        decimal_context.Emax = limits().magnitude
        decimal_context.Emin = -limits().magnitude
        while stack:
            node, stage = stack.pop()
            budget.spend()
            if stage == 0:
                if node.kind in ("number", "text", "boolean", "symbol", "element", "formula"):
                    if node.children:
                        raise FormulaError("Cấu trúc nút không hợp lệ.", category="evaluation")
                    if node.kind == "number": value = Decimal(node.value)
                    elif node.kind == "text": value = node.value
                    elif node.kind == "boolean": value = node.value == "TRUE"
                    else:
                        try: value = context[(node.kind, node.value)]
                        except KeyError: raise FormulaError(f'Thiếu dữ liệu cho biến "{node.value}".', category="evaluation") from None
                    values[id(node)] = value
                    trace.append({"expression": node.value, "arguments": (), "value": value})
                    continue
                if node.kind == "call" and node.value == "IF":
                    stack.extend(((node, 1), (node.children[0], 0)))
                elif node.kind == "binary" and node.value in ("AND", "OR"):
                    stack.extend(((node, 1), (node.children[0], 0)))
                elif node.kind in ("binary", "unary", "call"):
                    stack.append((node, 3))
                    stack.extend((child, 0) for child in reversed(node.children))
                else:
                    raise FormulaError("Loại nút không được phép.", category="evaluation")
                continue
            if stage == 1:
                condition = values[id(node.children[0])]
                if type(condition) is not bool:
                    raise FormulaError("Điều kiện phải là Có / Không.", category="evaluation")
                if node.value == "IF":
                    chosen = node.children[1 if condition else 2]
                    stack.extend(((node, 2), (chosen, 0)))
                elif (node.value == "AND" and not condition) or (node.value == "OR" and condition):
                    values[id(node)] = condition
                    trace.append({"expression": node.value, "arguments": (condition,), "value": condition})
                else:
                    stack.extend(((node, 2), (node.children[1], 0)))
                continue
            args = [values[id(child)] for child in node.children if id(child) in values]
            try:
                if stage == 2:
                    value = args[-1]
                    if node.value in ("AND", "OR") and type(value) is not bool:
                        raise FormulaError("Điều kiện phải là Có / Không.", category="evaluation")
                elif node.kind == "binary":
                    if node.value in ("/", "%") and args[1] == 0:
                        raise FormulaError("Không thể chia cho 0.", category="evaluation", position=node.position)
                    function = OPERATORS.get(node.value)
                    if function is None:
                        raise FormulaError("Toán tử không được phép.", category="evaluation")
                    value = function(*args)
                elif node.kind == "unary":
                    if node.value == "NOT": value = not args[0]
                    elif node.value == "+": value = +args[0]
                    elif node.value == "-": value = -args[0]
                    else: raise FormulaError("Toán tử không được phép.", category="evaluation")
                else:
                    function = FUNCTIONS.get(node.value)
                    if function is None or function.implementation is None or not function.minimum <= len(args) <= function.maximum:
                        raise FormulaError("Hàm không được phép hoặc số tham số không hợp lệ.", category="evaluation")
                    value = function.implementation(*args) if node.value in ("ROUND", "ABS") else function.implementation(args)
            except (DecimalException, TypeError, ValueError, OverflowError) as error:
                if isinstance(error, FormulaError): raise
                raise FormulaError("Không thể tính giá trị số hoặc dữ liệu vượt giới hạn.", category="evaluation", position=node.position) from None
            if isinstance(value, Decimal):
                checked_value(value, ValueType("NUMBER"))
            values[id(node)] = value
            trace.append({"expression": node.value, "arguments": tuple(args), "value": value})
    checked_value(values[id(root)], result_type)
    return EvaluationResult(values[id(root)], result_type.kind, tuple(trace))
