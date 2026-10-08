"""Deterministic piecewise linear inversion, including per-fee floors/caps."""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from .context import PricingError

ZERO, ONE, SCALE = Decimal(0), Decimal(1), Decimal("0.00000001")


def money(value):
    if not value.is_finite() or abs(value) >= Decimal("1e16"):
        raise PricingError("MONEY_RANGE", "Số tiền vượt quá phạm vi lưu trữ cho phép.")
    return value.quantize(SCALE, rounding=ROUND_HALF_EVEN)


def fee_amount(price, fee):
    raw = price * fee["rate"] + fee["fixed"]
    bounded = max(raw, fee["floor"]) if fee["floor"] is not None else raw
    if fee["cap"] is not None: bounded = min(bounded, fee["cap"])
    return raw, bounded


def solve(*, cost, method, target, fees=(), taxes=(), minimum=None):
    with localcontext() as ctx:
        ctx.prec = 50
        if not cost.is_finite() or cost < 0: raise PricingError("INVALID_COST", "Giá vốn không hợp lệ.")
        if method not in ("MARGIN", "MARKUP", "PROFIT_PER_UNIT") or not target.is_finite(): raise PricingError("INVALID_METHOD", "Mục tiêu định giá không hợp lệ.")
        if method == "MARGIN" and not -ONE <= target < ONE: raise PricingError("INVALID_MARGIN", "Biên lợi nhuận mục tiêu phải từ -100% đến dưới 100%.")
        if method == "MARKUP" and (target < -ONE or cost == 0): raise PricingError("INVALID_MARKUP", "Tỷ lệ cộng trên giá vốn không hợp lệ hoặc giá vốn bằng 0.")
        tax_rate = sum((tax["rate"] for tax in taxes), ZERO)
        tax_fixed = sum((tax["fixed"] for tax in taxes), ZERO)
        breaks = {ZERO, tax_fixed}
        for fee in fees:
            if fee["rate"] <= 0: continue
            for bound in (fee["floor"], fee["cap"]):
                if bound is not None and (point := (bound - fee["fixed"]) / fee["rate"]) > 0: breaks.add(point)
        points = sorted(breaks)
        candidates = []
        for low, high in zip(points, (*points[1:], None)):
            sample = (low + high) / 2 if high is not None else low + ONE
            a, b = ZERO, ZERO
            for fee in fees:
                raw, bounded = fee_amount(sample, fee)
                if raw == bounded: a, b = a + fee["rate"], b + fee["fixed"]
                else: b += bounded
            denominator = ONE / (ONE + tax_rate) - a - (target if method == "MARGIN" else ZERO)
            if denominator <= 0: continue
            profit_target = target * cost if method == "MARKUP" else target if method == "PROFIT_PER_UNIT" else ZERO
            price = (cost + b + tax_fixed / (ONE + tax_rate) + profit_target) / denominator
            if price >= max(low, tax_fixed) and (high is None or price <= high): candidates.append(price)
        if not candidates: raise PricingError("INVALID_DENOMINATOR", "Không thể tính giá bán: mẫu số không dương hoặc mục tiêu không khả thi.")
        unrounded = max(min(candidates), minimum if minimum is not None else ZERO)
        price = money(unrounded)
        if price <= 0: raise PricingError("INVALID_PRICE", "Giá bán phải lớn hơn 0 để tính biên lợi nhuận.")
        base = (price - tax_fixed) / (ONE + tax_rate)
        fee_rows = []
        for fee in fees:
            raw, bounded = fee_amount(price, fee)
            fee_rows.append({"kind": "FEE", "label": fee["label"], "source_id": fee["id"], "basis": price,
                "rate": fee["rate"], "fixed": fee["fixed"], "raw": raw, "floor": fee["floor"], "cap": fee["cap"], "amount": money(bounded)})
        tax_rows = [{"kind": "TAX", "label": tax["label"], "source_id": tax["id"], "basis": base,
            "rate": tax["rate"], "fixed": tax["fixed"], "inclusive": tax["inclusive"], "amount": money(base * tax["rate"] + tax["fixed"])} for tax in taxes]
        fee_total = sum((r["amount"] for r in fee_rows), ZERO)
        tax_total = sum((r["amount"] for r in tax_rows), ZERO)
        cost = money(cost)
        net = price - tax_total - fee_total
        profit = net - cost
        ratio_scale = Decimal("0.0000000001")
        margin = (profit / price).quantize(ratio_scale, rounding=ROUND_HALF_EVEN)
        markup = (profit / cost).quantize(ratio_scale, rounding=ROUND_HALF_EVEN) if cost else None
        waterfall = [{"kind": "PRICE", "label": "Giá khách trả", "amount": price}, *fee_rows, *tax_rows,
            {"kind": "NET", "label": "Doanh thu thuần sau phí và thuế", "amount": net},
            {"kind": "COST", "label": "Giá vốn", "amount": cost}, {"kind": "PROFIT", "label": "Lợi nhuận", "amount": profit}]
        return {"gross_price": price, "pre_tax_revenue": price - tax_total, "net_revenue": net, "unit_cost": cost,
            "fees": fee_total, "tax": tax_total, "profit": profit, "actual_margin": margin, "actual_markup": markup,
            "unrounded_price": unrounded, "minimum_applied": minimum is not None and minimum > min(candidates),
            "waterfall": waterfall, "fee_lines": fee_rows, "tax_lines": tax_rows,
            "reconciliation": price - fee_total - tax_total - cost - profit}
