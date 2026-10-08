"""Inspected CHECK/trigger fixtures only for isolated local PostgreSQL."""
from django.db import models
from apps.core.models import Formula, FormulaVersion, FormulaDependency, FormulaTestCase


def install_formula_fixtures(editor):
    database = editor.connection.settings_dict
    if database["NAME"] != "test_costing_slice" or database["HOST"] != "127.0.0.1":
        raise RuntimeError("Formula fixtures require isolated localhost tests.")
    for model in (Formula, FormulaVersion, FormulaDependency, FormulaTestCase): editor.create_model(model)
    constraints = (
        (FormulaVersion, "ck_formula_version_status", models.Q(status__in=("DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "RETIRED"))),
        (FormulaVersion, "ck_formula_validation_status", models.Q(validation_status__in=("NOT_VALIDATED", "VALID", "INVALID"))),
        (FormulaVersion, "ck_formula_version_period", models.Q(effective_to__isnull=True) | models.Q(effective_from__isnull=True) | models.Q(effective_to__gt=models.F("effective_from"))),
        (FormulaVersion, "ck_formula_effective_date_required", models.Q(status__in=("DRAFT", "IN_REVIEW")) | models.Q(effective_from__isnull=False)),
        (FormulaDependency, "ck_formula_dependency_kind", models.Q(dependency_kind__in=("ELEMENT", "FORMULA", "SYSTEM_FIELD", "RULE_TABLE", "RESOLVER"))),
        (FormulaDependency, "ck_formula_dependency_target", models.Q(dependency_kind="ELEMENT", depends_on_element__isnull=False) | models.Q(dependency_kind="FORMULA", depends_on_formula__isnull=False) | models.Q(dependency_kind__in=("SYSTEM_FIELD", "RULE_TABLE", "RESOLVER"))),
        (FormulaTestCase, "ck_formula_test_tolerance", models.Q(tolerance__gte=0)),
    )
    for model, name, condition in constraints:
        editor.add_constraint(model, models.CheckConstraint(condition=condition, name=name))
    # Production uses prevent_approved_version_mutation with this same OLD status guard.
    editor.execute("""CREATE TRIGGER trg_formula_version_immutable BEFORE UPDATE OR DELETE
        ON public.formula_version FOR EACH ROW EXECUTE FUNCTION public.test_recipe_version_immutable()""")
    editor.execute("""CREATE FUNCTION public.test_formula_dependency_protect() RETURNS trigger
        LANGUAGE plpgsql SET search_path TO '' AS $$
        DECLARE v_status text; v_parent_id bigint;
        BEGIN
          v_parent_id := CASE WHEN TG_OP='DELETE' THEN OLD.formula_version_id ELSE NEW.formula_version_id END;
          SELECT status INTO v_status FROM public.formula_version WHERE id=v_parent_id;
          IF v_status IN ('APPROVED','EFFECTIVE','RETIRED') THEN RAISE EXCEPTION 'Immutable formula dependency'; END IF;
          IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
        END; $$""")
    editor.execute("""CREATE TRIGGER trg_formula_dependency_protect BEFORE INSERT OR UPDATE OR DELETE
        ON public.formula_dependency FOR EACH ROW EXECUTE FUNCTION public.test_formula_dependency_protect()""")
    with editor.connection.cursor() as cursor:
        for model, columns, target in ((Formula, ("organization_id", "code"), "uq_formula"), (FormulaVersion, ("formula_id", "version_no"), "uq_formula_version")):
            for name, constraint in editor.connection.introspection.get_constraints(cursor, model._meta.db_table).items():
                if constraint["unique"] and tuple(constraint["columns"]) == columns and name != target:
                    editor.execute("ALTER TABLE %s RENAME CONSTRAINT %s TO %s" % tuple(editor.quote_name(value) for value in (model._meta.db_table, name, target)))
