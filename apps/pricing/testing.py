"""Mirror inspected CHECKs only in the guarded, disposable localhost database."""
from django.db import models
from apps.core.models import Channel, ChannelFeeRule, TaxRule, FxRate, PriceScenario
from .constants import CHANNEL_TYPES


def install_pricing_fixtures(editor):
    db = editor.connection.settings_dict
    if (db["NAME"], db["HOST"], db["USER"]) != ("test_costing_slice", "127.0.0.1", "costing_test"):
        raise RuntimeError("Pricing fixture DDL requires the isolated localhost test database.")
    # Channel is already installed by Costing Run's fixture, never create twice.
    for model in (ChannelFeeRule, TaxRule, FxRate, PriceScenario): editor.create_model(model)
    for suffix, condition in (
        ("margin", models.Q(target_margin__isnull=True) | models.Q(target_margin__gte=-1, target_margin__lt=1)),
        ("markup", models.Q(target_markup__isnull=True) | models.Q(target_markup__gte=-1)),
        ("method", models.Q(pricing_method__in=("MARGIN", "MARKUP", "PROFIT_PER_UNIT", "RULE_BASED", "MANUAL_APPROVED"))),
        ("period", models.Q(valid_to__isnull=True) | models.Q(valid_from__isnull=True) | models.Q(valid_to__gte=models.F("valid_from"))),
        ("status", models.Q(status__in=("DRAFT", "CALCULATED", "IN_REVIEW", "APPROVED", "EXPIRED", "CANCELLED"))),
    ): editor.add_constraint(PriceScenario, models.CheckConstraint(condition=condition, name=f"ck_price_scenario_{suffix}"))
    editor.add_constraint(Channel, models.CheckConstraint(condition=models.Q(channel_type__in=tuple(dict(CHANNEL_TYPES))), name="ck_channel_type"))
    for model, prefix, ratio in ((ChannelFeeRule, "channel_fee", "refundable_ratio"), (TaxRule, "tax_rule", "recoverable_ratio")):
        for suffix, condition in (
            ("rate", models.Q(rate__isnull=True) | models.Q(rate__gte=0, rate__lte=1)),
            ("refundable" if model is ChannelFeeRule else "recoverable", models.Q(**{ratio + "__gte": 0, ratio + "__lte": 1})),
            ("value", models.Q(rate__isnull=False) | models.Q(fixed_amount__isnull=False)),
            ("period", models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=models.F("effective_from"))),
            ("status", models.Q(status__in=("DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "RETIRED"))),
        ): editor.add_constraint(model, models.CheckConstraint(condition=condition, name=f"ck_{prefix}_{suffix}"))
    editor.add_constraint(ChannelFeeRule, models.CheckConstraint(condition=models.Q(cap_amount__isnull=True) | models.Q(floor_amount__isnull=True) | models.Q(cap_amount__gte=models.F("floor_amount")), name="ck_channel_fee_cap_floor"))
    for suffix, condition in (
        ("pair", ~models.Q(from_currency_code=models.F("to_currency_code"))),
        ("period", models.Q(valid_to__isnull=True) | models.Q(valid_to__gt=models.F("effective_at"))),
        ("positive", models.Q(rate__gt=0)),
        ("status", models.Q(status__in=("DRAFT", "APPROVED", "EFFECTIVE", "RETIRED"))),
    ): editor.add_constraint(FxRate, models.CheckConstraint(condition=condition, name=f"ck_fx_rate_{suffix}"))
