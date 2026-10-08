"""Read-only integrity report for implemented tables; never repairs or deletes data.

Run with env/Scripts/python.exe scripts/audit_demo_integrity.py --report artifacts/hardening-integrity.json.
"""
import argparse
import json
from pathlib import Path
import sys

from django.db import connection, transaction
from django.db.models import Count, F, Subquery


MODEL_NAMES = """Currency UomCategory Uom UomConversion CostElementGroup CostElement
ProductCategory Item Product Sku Supplier SupplierPrice Recipe RecipeVersion RecipeLine
PackagingConfig PackagingConfigVersion PackagingLine SkuPackagingAssignment WorkCenter
Resource ResourceRate Routing RoutingVersion RoutingOperation CostPool CostPoolPeriod
AllocationRule Formula FormulaVersion FormulaDependency FormulaTestCase CostingScheme
CostingSchemeVersion CostingSchemeLine CostingRun CostingRunLine Channel ChannelFeeRule
TaxRule FxRate PriceScenario""".split()


def audit_integrity():
    from apps.core import models as m
    from apps.master_data.company_context import get_default_organization
    from apps.costing.engine.context import digest as costing_digest
    from apps.pricing.engine.context import digest as pricing_digest
    report = {"read_only": True, "counts": {}, "errors": [], "warnings": [], "checks": 0}
    def check(query, code, table, **extra):
        report["checks"] += 1
        count = query.count()
        if count:
            report["errors"].append({"code": code, "table": table, "count": count, **extra})
    # On PostgreSQL this protects against accidental future writes in this tool.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
        company = get_default_organization()
        report["company_count"] = m.Organization.objects.count()
        report["active_company_count"] = m.Organization.objects.filter(is_active=True).count()
        report["company_context_valid"] = company is not None
        tables = set(connection.introspection.table_names())
        for name in MODEL_NAMES:
            model = getattr(m, name)
            table = model._meta.db_table
            if table not in tables:
                report["errors"].append({"code": "MISSING_TABLE", "table": table})
                continue
            report["counts"][table] = model.objects.count()
            fields = {field.name: field for field in model._meta.concrete_fields}
            for unique in model._meta.unique_together:
                query = model.objects.all()
                # PostgreSQL unique constraints permit multiple NULLs.
                for field in unique:
                    query = query.filter(**{field + "__isnull": False})
                check(query.values(*unique).annotate(n=Count("pk")).filter(n__gt=1), "DUPLICATE_KEY", table, fields=list(unique))
            for field in fields.values():
                if not field.many_to_one or field.related_model._meta.db_table not in tables:
                    continue
                query = model.objects.filter(**{field.attname + "__isnull": False}).exclude(
                    **{field.attname + "__in": Subquery(field.related_model.objects.values("pk"))})
                check(query, "ORPHAN_REFERENCE", table, field=field.name)
                target_fields = {f.name for f in field.related_model._meta.concrete_fields}
                if "is_active" in target_fields and field.name != "organization":
                    count = model.objects.filter(**{field.name + "__is_active": False}).count()
                    if count:
                        report["warnings"].append({"code": "INACTIVE_REFERENCE_REVIEW", "table": table, "field": field.name, "count": count})
                if "organization" in fields and "organization" in target_fields:
                    check(model.objects.exclude(**{field.attname + "__isnull": True}).exclude(
                        **{field.name + "__organization_id": F("organization_id")}), "INCONSISTENT_INTERNAL_SCOPE", table, field=field.name)
            for start, end in (("effective_from", "effective_to"), ("period_start", "period_end"), ("valid_from", "valid_to"), ("effective_at", "valid_to")):
                if start in fields and end in fields:
                    check(model.objects.filter(**{end + "__lt": F(start)}), "INVALID_PERIOD", table)
        check(m.SkuPackagingAssignment.objects.exclude(sku__product_id=F("packaging_config__product_id")), "SKU_PRODUCT_MISMATCH", "sku_packaging_assignment")
        check(m.CostingRun.objects.filter(sku__isnull=False).exclude(product_id=F("sku__product_id")), "SKU_PRODUCT_MISMATCH", "costing_run")
        check(m.PriceScenario.objects.exclude(organization_id=F("base_run__organization_id")), "SCENARIO_RUN_SCOPE_MISMATCH", "price_scenario")
        for run in m.CostingRun.objects.all().iterator(chunk_size=100):
            report["checks"] += 1
            snapshot = run.version_snapshot_jsonb
            if run.run_status == "LOCKED":
                valid = isinstance(snapshot, dict) and snapshot.get("schema") == 1 and snapshot.get("sha256") == costing_digest({k: v for k, v in snapshot.items() if k != "sha256"})
                valid = valid and bool(run.context_jsonb.get("per_unit")) and m.CostingRunLine.objects.filter(run=run).exists()
                if not valid: report["errors"].append({"code": "INCOMPLETE_LOCKED_RUN", "id": run.pk})
            elif run.run_status == "FAILED" and (snapshot or m.CostingRunLine.objects.filter(run=run).exists()):
                report["errors"].append({"code": "PARTIAL_FAILED_RUN", "id": run.pk})
            elif run.run_status in ("DRAFT", "CALCULATED"):
                report["warnings"].append({"code": "UNFINISHED_RUN_REVIEW", "id": run.pk, "status": run.run_status})
        for scenario in m.PriceScenario.objects.filter(status="CALCULATED").iterator(chunk_size=100):
            report["checks"] += 1
            snapshot = scenario.output_snapshot_jsonb
            valid = isinstance(snapshot, dict) and snapshot.get("schema") == 1 and snapshot.get("hash") == pricing_digest({k: v for k, v in snapshot.items() if k != "hash"})
            if not valid: report["errors"].append({"code": "INCOMPLETE_CALCULATED_SCENARIO", "id": scenario.pk})
        report["status"] = "PASS" if not report["errors"] else "FAIL"
    return report


def main():
    import os
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="artifacts/hardening-integrity.json")
    args = parser.parse_args()
    path = (root / args.report).resolve()
    if not path.is_relative_to(root): parser.error("Report must be inside the workspace")
    report = audit_integrity()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "checks", "errors", "warnings")}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
