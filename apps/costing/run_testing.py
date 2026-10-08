"""Inspected production Run constraints/triggers, isolated test database only."""
from django.db import models
from apps.core.models import Channel, CostPoolPeriod, CostingRun, CostingRunLine
from apps.master_data.constants import VALUE_TYPES, SOURCE_MODES
from .constants import LINE_TYPES


def install_run_fixtures(editor):
    database = editor.connection.settings_dict
    if (database["NAME"], database["HOST"], database["USER"]) != ("test_costing_slice", "127.0.0.1", "costing_test"):
        raise RuntimeError("Run fixtures require isolated localhost tests.")
    for model in (Channel, CostPoolPeriod, CostingRun, CostingRunLine): editor.create_model(model)
    constraints = (
        (CostPoolPeriod, "ck_cost_pool_period_amount", models.Q(amount__gte=0)),
        (CostPoolPeriod, "ck_cost_pool_period_capacity", models.Q(normal_capacity__isnull=True) | models.Q(normal_capacity__gt=0)),
        (CostPoolPeriod, "ck_cost_pool_period_date", models.Q(period_end__gte=models.F("period_start"))),
        (CostPoolPeriod, "ck_cost_pool_period_status", models.Q(status__in=("DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "CLOSED"))),
        (CostingRun, "ck_costing_run_quantity", models.Q(quantity__gt=0)),
        (CostingRun, "ck_costing_run_status", models.Q(run_status__in=("DRAFT", "CALCULATED", "IN_REVIEW", "APPROVED", "LOCKED", "FAILED", "SUPERSEDED"))),
        (CostingRun, "ck_costing_run_type", models.Q(run_type__in=("PLANNED", "STANDARD", "ACTUAL", "QUOTE", "SCENARIO"))),
        (CostingRunLine, "ck_costing_run_line_type", models.Q(line_type__in=tuple(dict(LINE_TYPES)))),
        (CostingRunLine, "ck_costing_run_line_source", models.Q(source_mode__in=tuple(dict(SOURCE_MODES)))),
        (CostingRunLine, "ck_costing_run_line_value_type", models.Q(value_type__in=tuple(dict(VALUE_TYPES)))),
    )
    for model, name, condition in constraints: editor.add_constraint(model, models.CheckConstraint(condition=condition, name=name))
    protected = ("organization_id", "run_no", "run_type", "scheme_version_id", "product_id", "sku_id", "channel_id", "quantity", "quantity_uom_id", "result_currency_code", "effective_at", "context_jsonb", "version_snapshot_jsonb", "fx_snapshot_jsonb", "manufacturing_cost", "inventory_cost", "landed_cost", "cost_to_serve", "channel_cost", "full_cost", "target_selling_price", "actual_realized_margin")
    differences = " OR ".join(f"NEW.{field} IS DISTINCT FROM OLD.{field}" for field in protected)
    editor.execute("""CREATE FUNCTION public.test_run_header_protect() RETURNS trigger LANGUAGE plpgsql SET search_path TO '' AS $$
        BEGIN
          IF TG_OP='DELETE' AND OLD.run_status IN ('APPROVED','LOCKED','SUPERSEDED') THEN RAISE EXCEPTION 'Immutable run'; END IF;
          IF TG_OP='UPDATE' THEN
            IF OLD.run_status IN ('LOCKED','SUPERSEDED') THEN RAISE EXCEPTION 'Immutable run'; END IF;
            IF OLD.run_status='APPROVED' AND (""" + differences + """) THEN RAISE EXCEPTION 'Immutable approved results'; END IF;
          END IF;
          IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
        END; $$""")
    editor.execute("""CREATE TRIGGER trg_run_header_protect BEFORE UPDATE OR DELETE ON public.costing_run
        FOR EACH ROW EXECUTE FUNCTION public.test_run_header_protect()""")
    editor.execute("""CREATE FUNCTION public.test_run_line_protect() RETURNS trigger LANGUAGE plpgsql SET search_path TO '' AS $$
        DECLARE v_status text; v_run_id bigint;
        BEGIN
          v_run_id := CASE WHEN TG_OP='DELETE' THEN OLD.run_id ELSE NEW.run_id END;
          SELECT run_status INTO v_status FROM public.costing_run WHERE id=v_run_id;
          IF v_status IN ('APPROVED','LOCKED','SUPERSEDED') THEN RAISE EXCEPTION 'Immutable run line'; END IF;
          IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
        END; $$""")
    editor.execute("""CREATE TRIGGER trg_run_line_protect BEFORE INSERT OR UPDATE OR DELETE ON public.costing_run_line
        FOR EACH ROW EXECUTE FUNCTION public.test_run_line_protect()""")
