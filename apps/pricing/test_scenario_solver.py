"""Independent arithmetic expectations, including piecewise fee bounds."""
from decimal import Decimal as D
from django.test import SimpleTestCase
from .engine.solver import solve
from .engine.context import PricingError


def fee(rate="0", fixed="0", floor=None, cap=None):
    return {"id": 1, "label": "Phí", "rate": D(rate), "fixed": D(fixed), "floor": D(floor) if floor else None, "cap": D(cap) if cap else None}


def tax(rate="0.1", inclusive=False, fixed="0"):
    return {"id": 1, "label": "Thuế", "rate": D(rate), "fixed": D(fixed), "inclusive": inclusive}


class PricingSolverTests(SimpleTestCase):
    def test_margin_without_deductions(self):
        r = solve(cost=D(60), method="MARGIN", target=D("0.2"))
        self.assertEqual((r["gross_price"], r["profit"], r["actual_margin"]), (D(75), D(15), D("0.2")))

    def test_markup_differs_from_margin(self):
        r = solve(cost=D(60), method="MARKUP", target=D("0.2"))
        self.assertEqual((r["gross_price"], r["profit"], r["actual_markup"]), (D(72), D(12), D("0.2")))
        self.assertEqual(r["actual_margin"], D("0.1666666667"))

    def test_percentage_fee_inversion(self):
        self.assertEqual(solve(cost=D(60), method="MARGIN", target=D("0.2"), fees=[fee("0.05")])["gross_price"], D(80))

    def test_fixed_fee_and_profit_target(self):
        r = solve(cost=D(60), method="PROFIT_PER_UNIT", target=D(20), fees=[fee(fixed="5")])
        self.assertEqual((r["gross_price"], r["profit"]), (D(85), D(20)))

    def test_multiple_fees_each_have_a_component(self):
        r = solve(cost=D(60), method="MARGIN", target=D("0.2"), fees=[fee("0.1"), fee(fixed="10")])
        self.assertEqual(r["gross_price"], D(100))
        self.assertEqual(len(r["fee_lines"]), 2)

    def test_inclusive_tax_reverse_and_exclusive_tax_addition(self):
        for inclusive in (True, False):
            r = solve(cost=D(60), method="PROFIT_PER_UNIT", target=D(20), taxes=[tax(inclusive=inclusive)])
            self.assertEqual((r["gross_price"], r["tax"], r["profit"]), (D(88), D(8), D(20)))
            self.assertEqual(r["tax_lines"][0]["basis"], D(80))

    def test_multiple_parallel_taxes(self):
        r = solve(cost=D(60), method="PROFIT_PER_UNIT", target=D(20), taxes=[tax("0.1"), tax("0.05")])
        self.assertEqual((r["gross_price"], r["tax"]), (D(92), D(12)))

    def test_fixed_tax_is_not_percentage(self):
        r = solve(cost=D(60), method="PROFIT_PER_UNIT", target=D(20), taxes=[tax("0.1", fixed="2")])
        self.assertEqual((r["gross_price"], r["tax"]), (D(90), D(10)))

    def test_fee_floor_and_cap_cross_piecewise_boundaries(self):
        for item, expected, deducted in ((fee("0.1", floor="20"), D(100), D(20)), (fee("0.5", cap="5"), D("81.25"), D(5))):
            r = solve(cost=D(60), method="MARGIN", target=D("0.2"), fees=[item])
            self.assertEqual((r["gross_price"], r["fees"]), (expected, deducted))

    def test_minimum_price_recomputes_actual_margin(self):
        r = solve(cost=D(60), method="MARGIN", target=D("0.2"), minimum=D(100))
        self.assertEqual((r["gross_price"], r["actual_margin"], r["minimum_applied"]), (D(100), D("0.4"), True))

    def test_invalid_denominator_does_not_return_negative_price(self):
        with self.assertRaisesMessage(PricingError, "mẫu số"):
            solve(cost=D(60), method="MARGIN", target=D("0.8"), fees=[fee("0.2")])

    def test_invalid_margin_markup_and_zero_price(self):
        for method, target, cost in (("MARGIN", D(1), D(60)), ("MARKUP", D(-2), D(60)), ("MARKUP", D(1), D(0)), ("PROFIT_PER_UNIT", D(0), D(0))):
            with self.subTest(method=method, target=target), self.assertRaises(PricingError): solve(cost=cost, method=method, target=target)

    def test_negative_margin_allowed_by_database(self):
        r = solve(cost=D(60), method="MARGIN", target=D("-0.2"))
        self.assertEqual((r["gross_price"], r["profit"]), (D(50), D(-10)))

    def test_golden_independent_constants_and_waterfall(self):
        r = solve(cost=D(58300), method="MARGIN", target=D("0.2"), fees=[fee("0.05"), fee(fixed="1000")], taxes=[tax(inclusive=True)])
        expected = {"unit_cost": "58300", "fees": "5498.62068966", "tax": "8179.31034483", "profit": "17994.48275861", "gross_price": "89972.41379310", "actual_margin": "0.2000000000"}
        for key, value in expected.items(): self.assertEqual(r[key], D(value), key)
        self.assertEqual(r["reconciliation"], D(0))
        self.assertEqual(r["gross_price"] - r["fees"] - r["tax"] - r["unit_cost"], r["profit"])
