"""Inspected constraints/triggers; DDL is restricted to isolated localhost tests."""
from django.db import models
from apps.core.models import CostingScheme, CostingSchemeVersion, CostingSchemeLine, RuleTable
from .constants import LINE_TYPES, VISIBILITY_SCOPES, COST_SCOPES, SOURCE_MODES, VERSION_STATUSES


def install_scheme_fixtures(editor):
    database = editor.connection.settings_dict
    if database["NAME"] != "test_costing_slice" or database["HOST"] != "127.0.0.1":
        raise RuntimeError("Scheme fixtures require isolated localhost tests.")
    for model in (RuleTable, CostingScheme, CostingSchemeVersion, CostingSchemeLine): editor.create_model(model)
    constraints = (
        (CostingSchemeVersion, "ck_costing_scheme_version_status", models.Q(status__in=tuple(dict(VERSION_STATUSES)))),
        (CostingSchemeVersion, "ck_costing_scheme_version_period", models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gt=models.F("effective_from"))),
        (CostingSchemeVersion, "ck_costing_scheme_effective_date_required", models.Q(status__in=("DRAFT", "IN_REVIEW")) | models.Q(effective_from__isnull=False)),
        (CostingSchemeLine, "ck_costing_scheme_line_type", models.Q(line_type__in=tuple(dict(LINE_TYPES)))),
        (CostingSchemeLine, "ck_costing_scheme_line_source_mode", models.Q(source_mode__in=tuple(dict(SOURCE_MODES)))),
        (CostingSchemeLine, "ck_costing_scheme_line_visibility", models.Q(visibility_scope__in=tuple(dict(VISIBILITY_SCOPES)))),
        (CostingSchemeLine, "ck_costing_scheme_line_cost_scope", models.Q(cost_scope__in=tuple(dict(COST_SCOPES)))),
        (CostingSchemeLine, "ck_costing_scheme_line_rounding", models.Q(rounding_scale__isnull=True) | models.Q(rounding_scale__gte=0, rounding_scale__lte=12)),
        (CostingSchemeLine, "ck_costing_scheme_line_override_range", models.Q(min_override_value__isnull=True) | models.Q(max_override_value__isnull=True) | models.Q(min_override_value__lte=models.F("max_override_value"))),
        (CostingSchemeLine, "ck_costing_scheme_line_source_reference", models.Q(source_mode="SYSTEM", system_resolver_code__isnull=False) | models.Q(source_mode="MANUAL") | models.Q(source_mode="LOOKUP", rule_table__isnull=False) | models.Q(source_mode="FORMULA", formula_version__isnull=False) | models.Q(source_mode="EXTERNAL", external_adapter_code__isnull=False)),
    )
    for model, name, condition in constraints: editor.add_constraint(model, models.CheckConstraint(condition=condition, name=name))
    editor.execute("""CREATE TRIGGER trg_costing_scheme_version_immutable BEFORE UPDATE OR DELETE
        ON public.costing_scheme_version FOR EACH ROW EXECUTE FUNCTION public.test_recipe_version_immutable()""")
    editor.execute("""CREATE FUNCTION public.test_scheme_line_protect() RETURNS trigger LANGUAGE plpgsql SET search_path TO '' AS $$
        DECLARE v_status text; v_parent_id bigint;
        BEGIN
          v_parent_id := CASE WHEN TG_OP='DELETE' THEN OLD.scheme_version_id ELSE NEW.scheme_version_id END;
          SELECT status INTO v_status FROM public.costing_scheme_version WHERE id=v_parent_id;
          IF v_status IN ('APPROVED','EFFECTIVE','RETIRED') THEN RAISE EXCEPTION 'Immutable scheme line'; END IF;
          IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
        END; $$""")
    editor.execute("""CREATE TRIGGER trg_scheme_line_protect BEFORE INSERT OR UPDATE OR DELETE
        ON public.costing_scheme_line FOR EACH ROW EXECUTE FUNCTION public.test_scheme_line_protect()""")
    # unique_together is deferred until the outer schema_editor exits. The shared
    # runner renames constraints afterwards, matching actual production names.
