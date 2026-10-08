"""Lexer + bounded precedence parser for the project's restricted DSL."""
from dataclasses import dataclass
import re
from .ast_nodes import Node
from .errors import FormulaError
from .functions import FUNCTIONS
from .limits import limits

IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)")
PRECEDENCE = {"OR": 1, "AND": 2, "==": 3, "!=": 3, ">": 3, ">=": 3, "<": 3, "<=": 3,
    "+": 4, "-": 4, "*": 5, "/": 5, "%": 5}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    position: int


def tokenize(expression):
    budget = limits()
    if not isinstance(expression, str) or not expression.strip():
        raise FormulaError("Biểu thức công thức không được để trống.", category="syntax", position=0)
    if len(expression) > budget.expression_length:
        raise FormulaError("Biểu thức vượt giới hạn độ dài.", category="syntax")
    if "\x00" in expression:
        raise FormulaError("Biểu thức chứa ký tự không hợp lệ.", category="syntax")
    tokens, pos = [], 0
    while pos < len(expression):
        character = expression[pos]
        if character.isspace():
            pos += 1
            continue
        start = pos
        if character in "\"'":
            quote = character
            pos += 1
            value = []
            while pos < len(expression) and expression[pos] != quote:
                if expression[pos] == "\\":
                    pos += 1
                    if pos >= len(expression) or expression[pos] not in (quote, "\\"):
                        raise FormulaError("Ký tự thoát trong văn bản không hợp lệ.", position=pos, category="syntax")
                value.append(expression[pos])
                pos += 1
            if pos >= len(expression):
                raise FormulaError("Thiếu dấu đóng văn bản.", position=start, category="syntax")
            pos += 1
            tokens.append(Token("text", "".join(value), start))
        elif character in "@$":
            match = IDENTIFIER.match(expression, pos+1)
            if not match:
                raise FormulaError("Mã tham chiếu không hợp lệ.", position=pos, category="syntax")
            tokens.append(Token("formula" if character == "@" else "element", match[0].upper(), pos))
            pos = match.end()
        elif (match := NUMBER.match(expression, pos)):
            if len(match[0].replace(".", "")) > budget.numeric_digits:
                raise FormulaError("Giá trị số vượt giới hạn chữ số.", position=pos, category="syntax")
            tokens.append(Token("number", match[0], pos))
            pos = match.end()
        elif (match := IDENTIFIER.match(expression, pos)):
            value = match[0].upper()
            tokens.append(Token("operator" if value in ("AND", "OR", "NOT") else "identifier", value, pos))
            pos = match.end()
        else:
            pair = expression[pos:pos+2]
            if pair in (">=", "<=", "==", "!="):
                tokens.append(Token("operator", pair, pos)); pos += 2
            elif character in "+-*/%><(),":
                tokens.append(Token("operator", character, pos)); pos += 1
            else:
                raise FormulaError("Ký tự không được phép trong biểu thức.", position=pos, category="syntax")
        if len(tokens) > budget.nodes * 4:
            raise FormulaError("Biểu thức vượt giới hạn số thành phần.", category="syntax")
    tokens.append(Token("end", "", len(expression)))
    return tokens


class Parser:
    def __init__(self, expression):
        self.tokens = tokenize(expression)
        self.index = 0
        self.count = 0
        self.budget = limits()

    @property
    def token(self):
        return self.tokens[self.index]

    def consume(self, expected=None):
        token = self.token
        if expected is not None and (token.value != expected or token.kind != "operator"):
            raise FormulaError(f"Cần ký hiệu {expected}.", position=token.position, category="syntax")
        self.index += 1
        return token

    def node(self, kind, value, children, position):
        self.count += 1
        if self.count > self.budget.nodes:
            raise FormulaError("Biểu thức vượt giới hạn số nút.", category="syntax")
        return Node(kind, value, tuple(children), position)

    def expression(self, minimum=1, depth=1):
        if depth > self.budget.depth:
            raise FormulaError("Biểu thức lồng quá sâu.", category="syntax", position=self.token.position)
        token = self.consume()
        if token.value in ("+", "-", "NOT") and token.kind == "operator":
            child = self.expression(3 if token.value == "NOT" else 6, depth+1)
            left = self.node("unary", token.value, [child], token.position)
        elif token.value == "(" and token.kind == "operator":
            left = self.expression(1, depth+1)
            self.consume(")")
        elif token.kind in ("number", "text", "element", "formula"):
            left = self.node(token.kind, token.value, [], token.position)
        elif token.kind == "identifier":
            if self.token.value == "(" and self.token.kind == "operator":
                function = FUNCTIONS.get(token.value)
                if function is None:
                    raise FormulaError(f'Không hỗ trợ hàm "{token.value}".', position=token.position, category="syntax")
                self.consume("(")
                children = []
                if self.token.value != ")" or self.token.kind != "operator":
                    while True:
                        children.append(self.expression(1, depth+1))
                        if len(children) > function.maximum:
                            raise FormulaError(f"Hàm {token.value} có quá nhiều tham số.", category="syntax", position=token.position)
                        if self.token.value != "," or self.token.kind != "operator":
                            break
                        self.consume(",")
                self.consume(")")
                if not function.minimum <= len(children) <= function.maximum:
                    raise FormulaError(f"Hàm {token.value} yêu cầu {function.minimum} đến {function.maximum} tham số.", category="syntax", position=token.position)
                left = self.node("call", token.value, children, token.position)
            else:
                left = self.node("boolean" if token.value in ("TRUE", "FALSE") else "symbol", token.value, [], token.position)
        else:
            raise FormulaError("Cần giá trị, biến hoặc dấu ngoặc mở.", position=token.position, category="syntax")
        while self.token.kind == "operator" and PRECEDENCE.get(self.token.value, 0) >= minimum:
            operator = self.consume()
            right = self.expression(PRECEDENCE[operator.value]+1, depth+1)
            left = self.node("binary", operator.value, [left, right], operator.position)
        return left


def parse(expression):
    parser = Parser(expression)
    root = parser.expression()
    if parser.token.kind != "end":
        raise FormulaError("Ký hiệu hoặc giá trị dư trong biểu thức.", position=parser.token.position, category="syntax")
    pending = [(root, 1)]
    while pending:
        node, depth = pending.pop()
        if depth > parser.budget.depth:
            raise FormulaError("Cây biểu thức lồng quá sâu.", position=node.position, category="syntax")
        pending.extend((child, depth+1) for child in node.children)
    return root
