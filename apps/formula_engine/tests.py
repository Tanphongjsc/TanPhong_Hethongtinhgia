"""Pure DSL security, precision, typing and bounded execution regression."""
from decimal import Decimal
from django.test import SimpleTestCase, override_settings
from .ast_nodes import Node, fingerprint
from .dependencies import references, topological_order
from .errors import FormulaError
from .evaluator import Budget, evaluate
from .parser import parse
from .validator import ValueType, validate


class DslTests(SimpleTestCase):
    def run_expression(self, expression, inputs=None, types=None):
        inputs = inputs or {}
        root = parse(expression)
        symbols = {(node.kind, node.value): (types or {}).get(node.value, ValueType("NUMBER")) for node in references(root).values()}
        output = validate(root, symbols)
        return evaluate(root, {(node.kind, node.value): inputs[node.value] for node in references(root).values()}, output, symbol_types=symbols)

    def test_precedence_parentheses_unary_and_decimal(self):
        for expression, expected in (("1 + 2 * 3", "7"), ("(1 + 2) * 3", "9"), ("-2 + +5", "3"), ("0.1 + 0.2", "0.3"), ("9 % 4", "1"), ("10 / 4", "2.5"), ("9 - 4 - 2", "3")):
            with self.subTest(expression=expression): self.assertEqual(self.run_expression(expression).value, Decimal(expected))

    def test_functions_and_decimal_rounding(self):
        for expression, expected in (("ROUND(1.005, 2)", "1.01"), ("ROUND(-1.005, 2)", "-1.01"), ("MIN(3, 2, 4)", "2"), ("MAX(3, 2, 4)", "4"), ("ABS(-2.5)", "2.5")):
            with self.subTest(expression=expression): self.assertEqual(self.run_expression(expression).value, Decimal(expected))

    def test_all_comparisons_and_boolean_precedence(self):
        for expression in ("2 > 1", "2 >= 2", "1 < 2", "1 <= 1", "2 == 2", "2 != 3", "NOT 2 == 3", "TRUE OR FALSE AND FALSE"):
            with self.subTest(expression=expression): self.assertIs(self.run_expression(expression).value, True)

    def test_lazy_if_and_boolean_do_not_evaluate_unchosen_division(self):
        self.assertEqual(self.run_expression("IF(TRUE, 7, 1 / 0)").value, Decimal(7))
        self.assertIs(self.run_expression("FALSE AND 1 / 0 > 1").value, False)
        self.assertIs(self.run_expression("TRUE OR 1 / 0 > 1").value, True)

    def test_text_and_boolean_literals(self):
        self.assertEqual(self.run_expression('IF(TRUE, "Có", "Không")').value, "Có")
        self.assertEqual(self.run_expression('IF(TRUE, ")", "(")').value, ")")
        self.assertIs(self.run_expression('"A" == "A"').value, True)

    def test_invalid_syntax_and_arity(self):
        for expression in ("", "A +", "(A+B", "1 2", "1e3", "1..5", "UNKNOWN(A)", "ROUND(1)", "ABS(1,2)", "IF(TRUE, 1)", "MIN()", "1 ** 2", "ROUND(1,2,3)"):
            with self.subTest(expression=expression), self.assertRaises(FormulaError): parse(expression)

    def test_attack_syntax_rejected(self):
        for expression in ('__import__("os")', 'open("file")', 'eval("1")', 'exec("1")', "x.__class__", "globals()", "locals()", "import os", "request.user", "settings.SECRET_KEY", "A[0]", "[x for x in y]", "lambda x: x", "A; DROP TABLE formula", "1 // 2", "getattr(A, 'x')", "__dict__", "A := 1"):
            with self.subTest(expression=expression), self.assertRaises(FormulaError): parse(expression)

    def test_source_error_location(self):
        with self.assertRaises(FormulaError) as error: parse("1 +\n ?")
        self.assertIn("Dòng 2, cột 2", error.exception.describe("1 +\n ?"))

    def test_dependencies_are_normalized_and_explicit(self):
        root = parse("a + A + $A + @B")
        self.assertEqual(set(references(root)), {("symbol", "A"), ("element", "A"), ("formula", "B")})
        self.assertEqual(fingerprint(parse("a+1")), fingerprint(parse(" A + 1 ")))

    def test_unknown_variable_and_type_errors(self):
        with self.assertRaises(FormulaError): validate(parse("UNKNOWN"), {})
        for expression in ('1 + "A"', "IF(1,2,3)", "TRUE + 1", "NOT 1", "TRUE AND 1", 'IF(TRUE,1,"A")', "ROUND(1,2.5)", "ROUND(1,13)", "ROUND(1,A)"):
            with self.subTest(expression=expression), self.assertRaises(FormulaError): self.run_expression(expression, {"A": Decimal(2)})

    def test_units_and_currency_validation(self):
        money = ValueType("MONEY", "MONEY", "VND")
        usd = ValueType("MONEY", "MONEY", "USD")
        mass = ValueType("QUANTITY", "MASS", unit=1)
        for types in ({"A": money, "B": usd}, {"A": money, "B": mass}, {"A": mass, "B": ValueType("QUANTITY", "MASS", unit=2)}):
            with self.subTest(types=types), self.assertRaises(FormulaError): self.run_expression("A+B", {"A": Decimal(1), "B": Decimal(2)}, types)
        result = self.run_expression("A * 1.05", {"A": Decimal(100)}, {"A": money})
        self.assertEqual(result.value, Decimal("105")); self.assertEqual(result.data_type, "MONEY")
        with self.assertRaises(FormulaError): validate(parse("1"), {}, money)

    def test_division_by_zero_and_missing_input(self):
        for expression in ("1/0", "1%0"):
            with self.subTest(expression=expression), self.assertRaisesMessage(FormulaError, "Không thể chia cho 0"): self.run_expression(expression)
        root = parse("A")
        with self.assertRaisesMessage(FormulaError, "Thiếu dữ liệu"): evaluate(root, {}, ValueType("NUMBER"))

    def test_invalid_runtime_type_and_nonfinite(self):
        for value in (1.2, True, "123", Decimal("NaN"), Decimal("Infinity")):
            for expression in ("A", "A + 1"):
                with self.subTest(value=value, expression=expression), self.assertRaises(FormulaError): self.run_expression(expression, {"A": value})

    def test_trace_contains_substituted_values(self):
        result = self.run_expression("A + B", {"A": Decimal(100), "B": Decimal(20)})
        self.assertEqual(result.trace[-1]["arguments"], (Decimal(100), Decimal(20)))
        self.assertEqual(result.trace[-1]["value"], Decimal(120))

    def test_expression_node_depth_and_numeric_limits(self):
        with override_settings(FORMULA_LIMITS={"expression_length": 10}):
            with self.assertRaises(FormulaError): parse("12345 + 12345")
        with override_settings(FORMULA_LIMITS={"nodes": 3}):
            with self.assertRaises(FormulaError): parse("1+2+3")
        with self.assertRaises(FormulaError): parse("(" * 80 + "1" + ")" * 80)
        with self.assertRaises(FormulaError): parse("9" * 1000)
        with self.assertRaises(FormulaError): evaluate(parse("1+2"), {}, ValueType("NUMBER"), budget=Budget(1))

    def test_graph_self_two_three_cycles_and_shared_dag(self):
        for graph in ({"A": ["A"]}, {"A": ["B"], "B": ["A"]}, {"A": ["B"], "B": ["C"], "C": ["A"]}):
            with self.subTest(graph=graph), self.assertRaisesMessage(FormulaError, "phụ thuộc vòng"): topological_order(graph, "A")
        self.assertEqual(topological_order({"A": ["B", "C"], "B": ["D"], "C": ["D"]}, "A"), ["D", "B", "C", "A"])
        with override_settings(FORMULA_LIMITS={"graph_depth": 2}):
            with self.assertRaises(FormulaError): topological_order({"A": ["B"], "B": ["C"]}, "A")

    def test_forged_ast_rejects_unknown_nodes_calls_and_arity(self):
        literal = Node("number", "1")
        for node in (Node("python", "x"), Node("call", "OPEN", (literal,)), Node("binary", "+", (literal,)), Node("binary", "**", (literal, literal))):
            with self.subTest(node=node), self.assertRaises(FormulaError): evaluate(node, {}, ValueType("NUMBER"))
