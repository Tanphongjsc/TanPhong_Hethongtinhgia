from decimal import Decimal, localcontext
from .context import PricingError, POLICY, json_data, digest
from .resolvers import Resolver, source
from .solver import solve
from apps.pricing.scenario_selectors import unit_cost


def execute(context):
    with localcontext() as precision:
        precision.prec = 50
        scenario, run = context.scenario, context.run
        resolver = Resolver(context)
        if run.run_status != "LOCKED": raise PricingError("INVALID_COSTING_RUN", "Lần tính giá thành chưa hoàn thành.")
        cost = resolver.convert(unit_cost(run), run.result_currency_code_id)
        fees, taxes = resolver.fees(), resolver.taxes()
        target = getattr(scenario, {"MARGIN": "target_margin", "MARKUP": "target_markup", "PROFIT_PER_UNIT": "target_profit_per_unit"}[scenario.pricing_method])
        result = solve(cost=cost, method=scenario.pricing_method, target=target, fees=fees, taxes=taxes, minimum=scenario.minimum_price)
        result["listed_price"] = result["gross_price"] if taxes and taxes[0]["inclusive"] else result["pre_tax_revenue"]
        result["listed_price_includes_tax"] = bool(taxes and taxes[0]["inclusive"])
        snapshot = json_data({"schema": 1, "policy": POLICY, "inputs": {"method": scenario.pricing_method, "target": target,
            "pricing_date": context.pricing_date, "currency": scenario.currency_code_id, "minimum_price": scenario.minimum_price,
            "tax_mode": context.tax_mode, "jurisdiction": context.jurisdiction, "transaction_type": context.transaction_type,
            "fx_rate_type": context.fx_rate_type, "quantity": Decimal(1), "uom_id": run.quantity_uom_id},
            "costing": {"id": run.pk, "public_id": str(run.public_id), "unit_cost": unit_cost(run), "currency": run.result_currency_code_id,
                "quantity": run.quantity, "full_cost": run.full_cost, "effective_at": run.effective_at,
                "context": run.context_jsonb, "snapshot_hash": digest(run.version_snapshot_jsonb)},
            "sources": [source(scenario.channel), source(scenario.currency_code), source(run.product), *resolver.sources],
            "display": scenario.scenario_context_jsonb["display"], "result": result,
            "trace": {"fx": resolver.fx, "rejected_rules": resolver.rejected,
                "equation": "P - sum(fees(P)) - sum(taxes(P)) - C = profit; margin = profit/P; markup = profit/C",
                "fee_lines": result["fee_lines"], "tax_lines": result["tax_lines"]}, "warnings": resolver.warnings})
        snapshot["hash"] = digest(snapshot)
        return snapshot
