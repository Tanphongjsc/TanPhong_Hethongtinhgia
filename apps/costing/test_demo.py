"""Same command dataset and actual services on the isolated PostgreSQL database."""
from decimal import Decimal
from io import StringIO
import uuid
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from apps.core import models as m
from .demo_data import seed_demo, seed_future_changes, manual_expected
from .demo_verification import verify_demo, create_golden_run, request_data, reconcile, stored_fingerprint
from .run_services import create_run


class DemoIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Organization creation is test-fixture ONLY in guarded localhost DB.
        cls.company = m.Organization.objects.create(code="EXISTING", name="Công ty có sẵn")
        cls.demo = seed_demo()

    def test_commands_seed_twice_preserve_every_record_and_company(self):
        tables = connection.introspection.table_names()
        models = [model for model in vars(m).values() if isinstance(model, type) and hasattr(model, "_meta") and model._meta.db_table in tables]
        before = {model: model.objects.count() for model in models}
        company = m.Organization.objects.values().get(pk=self.company.pk)
        call_command("seed_costing_demo", stdout=StringIO())
        demo = seed_demo()
        self.assertEqual(demo.created, {})
        self.assertEqual(before, {model: model.objects.count() for model in models})
        self.assertEqual(company, m.Organization.objects.values().get(pk=self.company.pk))

    def test_real_golden_future_history_and_all_ui_modules(self):
        report = verify_demo(self.demo)
        self.assertEqual(report["readiness"], "READY FOR PRICING FOUNDATION")
        self.assertEqual(len(report["ui_smoke"]), 22)
        self.assertTrue(report["historical_unchanged"])
        self.assertEqual(report["golden"]["comparisons"]["FULL_COST"]["actual"], "583000.00000000")
        self.assertEqual(report["future"]["comparisons"]["FULL_COST"]["actual"], "647000.00000000")
        self.assertFalse(m.CostingRun.objects.filter(run_status="FAILED").exists())

    def test_seed_refuses_drift_instead_of_overwriting(self):
        m.Item.objects.filter(pk=self.demo.records["coffee"].pk).update(name="Thay đổi có chủ đích")
        before = m.CostElement.objects.count()
        with self.assertRaisesMessage(ValidationError, "Không ghi đè"):
            seed_demo()
        self.assertEqual(m.CostElement.objects.count(), before)
        self.assertEqual(m.Item.objects.get(pk=self.demo.records["coffee"].pk).name, "Thay đổi có chủ đích")

    def test_seed_rolls_back_all_new_records_on_conversion_conflict(self):
        # A collision discovered late in the reference seed rolls back earlier
        # creations. Do not patch the engine or persist corrupt source fixtures.
        before = m.UomConversion.objects.count()
        m.UomConversion.objects.create(organization=self.company, from_uom=self.demo.records["g"],
            to_uom=self.demo.records["kg"], factor=Decimal("0.001"), effective_from=self.demo.records["mass_conversion"].effective_from)
        with self.assertRaisesMessage(ValidationError, "nguồn khác"):
            seed_demo()
        self.assertEqual(m.UomConversion.objects.count(), before + 1)

    def test_idempotent_verification_does_not_duplicate_runs_or_future_sources(self):
        first = verify_demo(self.demo, smoke=False)
        before = (m.CostingRun.objects.count(), m.SupplierPrice.objects.count(), m.ResourceRate.objects.count())
        second = verify_demo(seed_demo(), smoke=False)
        self.assertEqual(first["golden"]["id"], second["golden"]["id"])
        self.assertEqual(before, (m.CostingRun.objects.count(), m.SupplierPrice.objects.count(), m.ResourceRate.objects.count()))

    def test_golden_run_queries_are_batched_and_do_not_query_members(self):
        with CaptureQueriesContext(connection) as queries:
            run = create_golden_run(self.demo)
        reconcile(self.demo, run)
        sql = [row["sql"].lower() for row in queries if row["sql"].lstrip().upper().startswith("SELECT")]
        for table in ("supplier_price", "resource_rate", "recipe_line", "packaging_line", "routing_operation"):
            self.assertLessEqual(sum(f'from "{table}"' in row for row in sql), 2, table)
        self.assertFalse(any("organization_member" in row for row in sql))

    def test_missing_price_fails_without_partial_breakdown(self):
        m.SupplierPrice.objects.filter(pk=self.demo.records["coffee_price"].pk).update(status="RETIRED")
        run = create_run(workspace=self.demo.workspace, data=request_data(self.demo), idempotency_key=uuid.uuid4())
        self.assertEqual(run.run_status, "FAILED")
        self.assertEqual(run.context_jsonb["errors"][0]["code"], "MISSING_PRICE")
        self.assertFalse(m.CostingRunLine.objects.filter(run=run).exists())
        self.assertEqual(run.version_snapshot_jsonb, {})

    def test_missing_rate_fails_without_partial_breakdown(self):
        m.ResourceRate.objects.filter(pk=self.demo.records["mixer_rate"].pk).update(status="RETIRED")
        run = create_run(workspace=self.demo.workspace, data=request_data(self.demo), idempotency_key=uuid.uuid4())
        self.assertEqual(run.run_status, "FAILED")
        self.assertEqual(run.context_jsonb["errors"][0]["code"], "MISSING_RATE")
        self.assertFalse(m.CostingRunLine.objects.filter(run=run).exists())

    def test_old_result_unchanged_and_source_versions_remain_locked(self):
        run = create_golden_run(self.demo)
        before = stored_fingerprint(run)
        seed_future_changes(self.demo)
        self.assertEqual(before, stored_fingerprint(run))
        from apps.bom.services import update_version
        from apps.bom.constants import VERSION_FIELDS
        source = self.demo.records["recipe_version"]
        with self.assertRaisesMessage(ValidationError, "được chốt"):
            update_version(workspace=self.demo.workspace, recipe=self.demo.records["recipe"], instance=source,
                data={field: getattr(source, field) for field in VERSION_FIELDS})

    def test_expected_is_independent_exact_arithmetic(self):
        self.assertEqual(manual_expected()["FULL_COST"], Decimal(583000))
        self.assertEqual(manual_expected(future=True)["FULL_COST"], Decimal(647000))

    def test_effective_end_inclusive_and_next_day_uses_future_sources(self):
        from .demo_data import OLD_END, FUTURE
        seed_future_changes(self.demo)
        old = create_golden_run(self.demo, day=OLD_END)
        new = create_golden_run(self.demo, day=FUTURE)
        reconcile(self.demo, old)
        reconcile(self.demo, new, future=True)

    def test_duplicate_price_is_ambiguous_and_not_silently_selected(self):
        source = self.demo.records["coffee_price"]
        from apps.master_data.services import save_supplier_price
        from apps.master_data.constants import SUPPLIER_PRICE_FIELDS
        duplicate = save_supplier_price(workspace=self.demo.workspace, data={field: getattr(source, field) for field in SUPPLIER_PRICE_FIELDS})
        duplicate.status = "EFFECTIVE"
        duplicate.save(update_fields=["status"])
        run = create_run(workspace=self.demo.workspace, data=request_data(self.demo), idempotency_key=uuid.uuid4())
        self.assertEqual(run.run_status, "FAILED")
        self.assertEqual(run.context_jsonb["errors"][0]["code"], "AMBIGUOUS_PRICE")
        self.assertFalse(m.CostingRunLine.objects.filter(run=run).exists())


class DemoAtomicSeedTests(TestCase):
    def test_partial_reference_seed_is_rolled_back_and_existing_company_untouched(self):
        company = m.Organization.objects.create(code="EXISTING", name="Công ty có sẵn")
        time = m.UomCategory.objects.create(code="TIME", name="Thời gian", dimension_code="TIME")
        hour = m.Uom.objects.create(code="HOUR", name="Giờ", symbol="h", category=time)
        minute = m.Uom.objects.create(code="MINUTE", name="Phút", symbol="phút", category=time)
        m.UomConversion.objects.create(organization=company, from_uom=hour, to_uom=minute,
            factor=Decimal(60), effective_from=self._day())
        before = m.Organization.objects.values().get(pk=company.pk)
        with self.assertRaisesMessage(ValidationError, "nguồn khác"):
            seed_demo()
        self.assertEqual(m.Currency.objects.count(), 0)
        self.assertEqual(m.Uom.objects.count(), 2)
        self.assertEqual(m.UomCategory.objects.count(), 1)
        self.assertEqual(m.UomConversion.objects.count(), 1)
        self.assertFalse(m.Item.objects.exists())
        self.assertEqual(before, m.Organization.objects.values().get(pk=company.pk))

    @staticmethod
    def _day():
        from .demo_data import START
        return START
