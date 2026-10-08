"""Idempotent Pricing demo; only READ the existing immutable DEMO Costing Run."""
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.core.models import CostingRun, PriceScenario, Channel, ChannelFeeRule, TaxRule, Currency
from apps.master_data.access import Workspace
from apps.master_data.company_context import get_default_organization
from apps.costing.demo_verification import stored_fingerprint
from .services import save_record
from .scenario_forms import ScenarioForm
from .scenario_services import save_scenario, calculate_scenario
from .engine.context import digest
from .constants import FEE_FIELDS, TAX_FIELDS

EXPECTED = {"unit_cost": "58300", "fees": "5498.62068966", "tax": "8179.31034483", "profit": "17994.48275861", "gross_price": "89972.41379310", "actual_margin": "0.2000000000"}
DAY = date(2026, 10, 8)
FUTURE_EXPECTED = {"unit_cost": "58300", "fees": "6551.56030363", "tax": "9169.24374473", "profit": "18505.20101208", "gross_price": "92526.00506044", "actual_margin": "0.2000000000"}


def compare(snapshot, expected):
    comparisons = []
    for name, value in expected.items():
        actual = Decimal(snapshot["result"][name])
        delta = actual - Decimal(value)
        if delta != 0: raise ValidationError(f"Golden Pricing sai tại {name}: delta={delta}.")
        comparisons.append({"metric": name, "expected": value, "actual": str(actual), "delta": str(delta)})
    return comparisons


def scenario(workspace, run, channel, currency, *, code, day):
    row = PriceScenario.objects.filter(organization=workspace.organization, code=code).first()
    if row is None:
        form = ScenarioForm(dict(code=code, name="Giá bán Cappuccino mẫu", product=run.product_id, sku=run.sku_id, base_run=run.pk,
            channel=channel.pk, pricing_date=day.isoformat(), pricing_method="MARGIN", target_margin="20", currency_code=currency.pk,
            tax_mode="REQUIRED", jurisdiction_code="VN", transaction_type="", fx_rate_type="SPOT"), workspace=workspace)
        if not form.is_valid(): raise ValidationError(form.errors.as_text())
        row = save_scenario(workspace=workspace, data=form.cleaned_data)
    if row.base_run_id != run.pk or row.channel_id != channel.pk or row.currency_code_id != currency.pk or row.target_margin != Decimal("0.2") or row.scenario_context_jsonb.get("pricing_date") != day.isoformat():
        raise ValidationError("Kịch bản mẫu đã đổi đầu vào; không ghi đè dữ liệu.")
    row = calculate_scenario(workspace=workspace, instance=row)
    if row.status != "CALCULATED": raise ValidationError(str(row.output_snapshot_jsonb.get("errors", "Không có kết quả")))
    snapshot = row.output_snapshot_jsonb
    if snapshot.get("hash") != digest({k: v for k, v in snapshot.items() if k != "hash"}): raise ValidationError("Dấu vân tay Pricing không hợp lệ.")
    return row


def ensure(resource, model, workspace, lookup, values):
    rows = list(model.objects.filter(organization=workspace.organization, **lookup)[:2])
    if len(rows) > 1: raise ValidationError("Dữ liệu mẫu có nhiều nguồn trùng tham chiếu; không tự chọn.")
    if rows:
        record = rows[0]
        for name, expected in values.items():
            actual = getattr(record, name)
            if getattr(actual, "pk", actual) != getattr(expected, "pk", expected):
                raise ValidationError(f"Dữ liệu mẫu đã thay đổi tại {name}; không ghi đè lịch sử.")
        return record
    return save_record(resource=resource, workspace=workspace, data=values)


def verify_pricing_demo():
    workspace = Workspace(get_default_organization())
    run = CostingRun.objects.filter(organization=workspace.organization, run_status="LOCKED", sku__code="DEMO_CAPPUCCINO_BOX20",
        context_jsonb__request__costing_date="2026-10-07", full_cost=Decimal(583000), quantity=Decimal(10)).order_by("created_at", "pk").first()
    if not run: raise ValidationError("Chưa có lần tính DEMO đã khóa ngày 07/10/2026. Hãy chạy verify_costing_demo trước; Pricing không tự chạy lại Costing.")
    before = stored_fingerprint(run)
    with transaction.atomic():
        currency = Currency.objects.get(code=run.result_currency_code_id)
        channel = ensure("channel", Channel, workspace, {"code": "DEMO_DIRECT"}, {"code": "DEMO_DIRECT", "name": "Kênh bán trực tiếp mẫu", "channel_type": "D2C", "market_code": "VN", "seller_type": None, "platform_code": None, "default_currency_code": currency, "is_active": True})
        # Serialize same-demo creation without adding a business DB constraint.
        Channel.objects.select_for_update().get(pk=channel.pk)
        for fee_type, rate, fixed in (("COMMISSION", Decimal("0.05"), None), ("PAYMENT_FEE", None, Decimal(1000))):
            reference = "DEMO_PRICING_V1:" + fee_type
            ensure("channel_fee_rule", ChannelFeeRule, workspace, {"source_reference": reference}, dict(channel=channel, product_category=None, sku=None,
                fee_type=fee_type, fee_base="LIST_PRICE", rate=rate, fixed_amount=fixed, currency_code=currency if fixed is not None else None,
                cap_amount=None, floor_amount=None, refundable_ratio=Decimal(0), tax_inclusive=True, priority=100, effective_from=date(2026, 1, 1), effective_to=date(2026, 11, 1), status="EFFECTIVE", source_reference=reference))
        ensure("tax_rule", TaxRule, workspace, {"source_reference": "DEMO_PRICING_V1:VAT"}, dict(jurisdiction_code="VN", tax_type="VAT",
            tax_class_code=None, seller_type=None, transaction_type=None, rate=Decimal("0.1"), fixed_amount=None, currency_code=None, tax_base="SELLING_PRICE", recoverable_ratio=Decimal(0), inclusive=True,
            priority=100, effective_from=date(2026, 1, 1), effective_to=date(2026, 11, 1), status="EFFECTIVE", source_reference="DEMO_PRICING_V1:VAT"))
        row = scenario(workspace, run, channel, currency, code="DEMO_PRICING_GOLDEN", day=DAY)
        snapshot = row.output_snapshot_jsonb
        comparisons = compare(snapshot, EXPECTED)
        # Add future periods; never edit a historical rule or golden snapshot.
        for model, resource, field_names in ((ChannelFeeRule, "channel_fee_rule", FEE_FIELDS), (TaxRule, "tax_rule", TAX_FIELDS)):
            old_rows = model.objects.filter(organization=workspace.organization, source_reference__startswith="DEMO_PRICING_V1:")
            for old in old_rows:
                values = {name: getattr(old, name) for name in field_names}
                values.update(source_reference=old.source_reference.replace("V1:", "V2:"), effective_from=date(2026, 11, 1), effective_to=None)
                if old.source_reference.endswith(":COMMISSION"): values["rate"] = Decimal("0.06")
                if resource == "tax_rule": values["rate"] = Decimal("0.11")
                ensure(resource, model, workspace, {"source_reference": values["source_reference"]}, values)
        future = scenario(workspace, run, channel, currency, code="DEMO_PRICING_FUTURE", day=date(2026, 11, 1))
        future_comparisons = compare(future.output_snapshot_jsonb, FUTURE_EXPECTED)
        stored = PriceScenario.objects.get(pk=row.pk).output_snapshot_jsonb
        if stored != snapshot: raise ValidationError("Kịch bản lịch sử đã thay đổi sau khi bổ sung quy tắc tương lai.")
        after = stored_fingerprint(run)
        if before != after: raise ValidationError("Pricing đã làm thay đổi Costing Run.")
    return {"scenario_id": row.pk, "scenario_code": row.code, "status": row.status, "pricing_date": DAY.isoformat(),
        "costing_run": str(run.public_id), "costing_fingerprint_before": before, "costing_fingerprint_after": after,
        "snapshot_hash": snapshot["hash"], "comparisons": comparisons, "reconciliation": snapshot["result"]["reconciliation"],
        "future_scenario_id": future.pk, "future_comparisons": future_comparisons, "historical_unchanged": stored == snapshot}
