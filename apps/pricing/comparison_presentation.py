"""Vietnamese presentation of stored results. All financial arithmetic is Decimal."""
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from django.urls import reverse
from apps.master_data.presentation import format_number, format_percent
from .comparison import difference, number
from .scenario_constants import METHODS
from .scenario_presentation import display_date, trace_rows


def signed(value, suffix=""):
    if value is None:
        return "—"
    return ("+" if value > 0 else "") + format_number(value) + suffix


def column(scenario):
    snapshot = scenario.snapshot
    inputs, costing, display = snapshot["inputs"], snapshot["costing"], snapshot["display"]
    target = number(inputs["target"])
    return {"id": scenario.record.pk, "code": scenario.record.code, "name": scenario.record.name,
        "date": display_date(inputs["pricing_date"]), "channel": display.get("channel") or "Không có kênh bán",
        "product": display.get("product") or "—", "sku": display.get("sku") or "Không có SKU",
        "currency": scenario.currency, "uom": display.get("uom") or "—", "status": "CALCULATED",
        "costing_url": reverse("costing:run_detail", args=[costing["public_id"]]),
        "costing_label": scenario.record.base_run.run_no, "costing_date": display_date(costing["effective_at"]),
        "source_cost": f"{format_number(costing['unit_cost'])} {costing['currency']}",
        "method": dict(METHODS)[inputs["method"]],
        "target_margin": format_percent(target) if inputs["method"] == "MARGIN" else "—",
        "target_markup": format_percent(target) if inputs["method"] == "MARKUP" else "—",
        "target_profit": f"{format_number(target)} {scenario.currency}" if inputs["method"] == "PROFIT_PER_UNIT" else "—",
        "price": format_number(scenario.values["gross_price"]), "margin": format_percent(scenario.values["actual_margin"]),
        "detail_url": reverse("pricing:scenario_detail", args=[scenario.record.pk]),
        "fees": list(trace_rows(snapshot, "fee_lines")), "taxes": list(trace_rows(snapshot, "tax_lines")),
        "fx": [dict(fx, display_at=display_date(fx.get("at"))) for fx in snapshot["trace"].get("fx", [])], "hash": snapshot["hash"], "trace_id": snapshot.get("trace_id", "—")}


def matrix(scenarios, baseline_id):
    baseline = next(s for s in scenarios if s.record.pk == baseline_id)
    same_currency = len({s.currency for s in scenarios}) == 1
    groups = []
    definitions = (("Giá thành và cấu thành giá", (("unit_cost", "Giá vốn", False), ("fees", "Tổng phí kênh bán", False), ("tax", "Tổng thuế", False))),
        ("Kết quả giá bán", (("gross_price", "Giá khách trả (gồm thuế)", False), ("pre_tax_revenue", "Doanh thu trước phí, chưa thuế", False),
            ("net_revenue", "Doanh thu thuần sau phí và thuế", False), ("profit", "Lợi nhuận", False),
            ("actual_margin", "Biên lợi nhuận thực tế / giá khách trả", True), ("actual_markup", "Tỷ lệ cộng thực tế / giá vốn", True))))
    for title, metrics in definitions:
        rows = []
        for key, label, ratio in metrics:
            cells = []
            for s in scenarios:
                value = s.values[key]
                absolute, relative = difference(value, baseline.values[key]) if ratio or same_currency else (None, None)
                if ratio and absolute is not None:
                    absolute *= Decimal(100)
                if relative is not None:
                    with localcontext() as precision:
                        precision.prec = 80
                        relative = relative.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
                cells.append({"id": s.record.pk, "value": format_percent(value) if ratio else f"{format_number(value)} {s.currency}",
                    "baseline": s.record.pk == baseline_id,
                    "delta": signed(absolute, " điểm %" if ratio else f" {s.currency}"), "relative": signed(relative, "%"),
                    "comparable": ratio or same_currency})
            rows.append({"key": key, "label": label, "cells": cells})
        groups.append({"title": title, "rows": rows})
    return {"groups": groups, "same_currency": same_currency, "baseline_id": baseline_id}
