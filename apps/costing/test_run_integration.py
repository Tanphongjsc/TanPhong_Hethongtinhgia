"""Dated end-to-end costing on isolated PostgreSQL, including stored history."""
from datetime import timedelta
from decimal import Decimal
import uuid
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.db import connection, transaction, DatabaseError
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from apps.core.models import (
    CostingRun, CostingRunLine, CostingSchemeLine, CostElement, Formula, FormulaVersion,
    SupplierPrice, ResourceRate, Recipe, RecipeVersion, RecipeLine, PackagingConfigVersion, PackagingLine,
    RoutingOperation, Uom, UomConversion, Product, Sku, Currency, Organization,
)
from apps.master_data.access import Workspace
from .engine.context import ExecutionContext, digest, json_data
from .engine.errors import CostingError
from .engine.runner import execute
from .run_services import create_run
from .run_forms import RunForm
from .run_test_data import golden_data, seal, request_data


class RunIntegrationTests(TestCase):
    def setUp(self):
        self.data = golden_data()
        self.workspace = Workspace(self.data.company)
        setting = override_settings(DEFAULT_ORGANIZATION_ID=self.data.company.pk)
        setting.enable(); self.addCleanup(setting.disable)

    def run_costing(self, **changes):
        seal(self.data)
        return create_run(workspace=self.workspace, data=request_data(self.data, **changes), idempotency_key=uuid.uuid4())

    def url(self, action="list", run=None, line=None):
        args = [run.public_id] if run else []
        if line: args.append(line.pk)
        return reverse("costing:run_" + action, args=args)

    def post_data(self, **changes):
        data = request_data(self.data)
        data.pop("manual")
        values = {key: getattr(value, "pk", value) for key, value in data.items()}
        values["costing_date"] = self.data.day.isoformat()
        values["idempotency_key"] = str(uuid.uuid4())
        values.update(changes)
        return values

    def line(self, run, code): return CostingRunLine.objects.get(run=run, line_code=code)

    def assert_failed(self, run, code=None):
        self.assertEqual(run.run_status, "FAILED", run.context_jsonb)
        self.assertFalse(CostingRunLine.objects.filter(run=run).exists())
        self.assertEqual(run.version_snapshot_jsonb, {})
        self.assertIsNone(run.full_cost)
        self.assertTrue(run.context_jsonb["errors"][0]["message"])
        if code: self.assertEqual(run.context_jsonb["errors"][0]["code"], code)

    def test_golden_full_pipeline_amounts_trace_and_snapshot(self):
        run = self.run_costing()
        self.assertEqual(run.run_status, "LOCKED", run.context_jsonb)
        self.assertEqual(run.manufacturing_cost, Decimal("60000"))
        self.assertEqual(run.full_cost, Decimal("60000"))
        self.assertEqual({line.line_code: line.amount for line in CostingRunLine.objects.filter(run=run)}, {
            "MATERIAL_COST": Decimal(40000), "PACKAGING_COST": Decimal(5000), "RESOURCE_COST": Decimal(10000), "OVERHEAD_COST": Decimal(5000), "FULL_COST": Decimal(60000)})
        self.assertIsNone(run.created_by); self.assertIsNone(run.approved_by)
        self.assertEqual(run.quantity, Decimal(1)); self.assertIsNotNone(run.locked_at)
        self.assertEqual(run.context_jsonb["per_unit"], "60000.000000")
        sources = run.version_snapshot_jsonb["sources"]
        for record in (self.data.recipe_version, self.data.packaging_version, self.data.routing_version, self.data.prices[0], self.data.rate, self.data.rule, self.data.period, self.data.formula_version):
            self.assertIn(f"{record._meta.db_table}:{record.pk}", sources)
        snapshot = dict(run.version_snapshot_jsonb); fingerprint = snapshot.pop("sha256")
        self.assertEqual(digest(snapshot), fingerprint)
        self.assertEqual(snapshot["order"][-1], "FULL_COST")
        result = self.line(run, "FULL_COST")
        self.assertEqual(result.input_snapshot_jsonb["inputs"]["MATERIAL_COST"], "40000.000000")
        self.assertNotIn("FULL_COST", result.input_snapshot_jsonb["inputs"])
        self.assertTrue(result.source_trace_jsonb["steps"])
        self.assertIn("5000", str(self.line(run, "PACKAGING_COST").source_trace_jsonb))

    def test_deterministic_same_inputs_new_runs_same_snapshots(self):
        first, second = self.run_costing(), self.run_costing()
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.version_snapshot_jsonb, second.version_snapshot_jsonb)
        self.assertEqual(first.full_cost, second.full_cost)
        self.assertEqual(list(CostingRunLine.objects.filter(run=first).order_by("display_order").values_list("source_trace_jsonb", flat=True)),
            list(CostingRunLine.objects.filter(run=second).order_by("display_order").values_list("source_trace_jsonb", flat=True)))

    def test_scaling_and_packaging_explicit_basis(self):
        run = self.run_costing(quantity=Decimal(12), packaging_quantity=Decimal(12))
        self.assertEqual(self.line(run, "MATERIAL_COST").amount, 480000)
        self.assertEqual(self.line(run, "PACKAGING_COST").amount, 5000)
        self.assertEqual(self.line(run, "RESOURCE_COST").amount, 120000)
        self.assertEqual(self.line(run, "OVERHEAD_COST").amount, 60000)
        self.assertEqual(run.full_cost, 665000)
        self.assertEqual(run.context_jsonb["request"]["packaging_quantity"], "12")

    def test_fractional_packaging_not_integer_or_parent_multiplied(self):
        PackagingLine.objects.filter(pk=self.data.packaging_line.pk).update(qty=Decimal("0.08333333"), units_per_parent=12, parent_level_code="SECONDARY")
        run = self.run_costing()
        self.assertEqual(self.line(run, "PACKAGING_COST").amount, Decimal("416.666650"))

    def test_yield_and_scrap_confirmed_formula(self):
        RecipeVersion.objects.filter(pk=self.data.recipe_version.pk).update(yield_rate=Decimal("0.8"))
        RecipeLine.objects.filter(pk=self.data.recipe_lines[0].pk).update(scrap_rate=Decimal("0.2"))
        run = self.run_costing()
        self.assertEqual(self.line(run, "MATERIAL_COST").amount, Decimal("56250"))
        self.assertIn("3.125", str(self.line(run, "MATERIAL_COST").source_trace_jsonb))

    def test_setup_once_and_operation_basis_precedes_batch(self):
        RoutingOperation.objects.filter(pk=self.data.operation.pk).update(setup_time=Decimal("0.25"), quantity_basis=2, quantity_uom=self.data.kg)
        run = self.run_costing(quantity=Decimal(4))
        self.assertEqual(self.line(run, "RESOURCE_COST").amount, Decimal("22500"))

    def test_setup_only_does_not_require_run_quantity_basis(self):
        RoutingOperation.objects.filter(pk=self.data.operation.pk).update(run_time=0, setup_time=Decimal("0.25"))
        type(self.data.routing_version).objects.filter(pk=self.data.routing_version.pk).update(batch_size=None, batch_uom=None)
        run = self.run_costing(quantity=Decimal(4))
        self.assertEqual(self.line(run, "RESOURCE_COST").amount, Decimal(2500))

    def test_time_conversion_from_master_inverse_no_hour_constant(self):
        minute = Uom.objects.create(category=self.data.h.category, code="MIN", name="Phút", symbol="phút")
        UomConversion.objects.create(from_uom=self.data.h, to_uom=minute, factor=60, effective_from=self.data.day-timedelta(days=1))
        RoutingOperation.objects.filter(pk=self.data.operation.pk).update(run_time=90, time_uom=minute)
        run = self.run_costing()
        self.assertEqual(self.line(run, "RESOURCE_COST").amount, Decimal(15000))
        self.assertIn("uom_conversion", str(run.version_snapshot_jsonb))

    def test_routing_basis_other_sales_unit_not_net_mass(self):
        carton = Uom.objects.create(category=self.data.box.category, code="CARTON", name="Thùng", symbol="thùng")
        UomConversion.objects.create(from_uom=carton, to_uom=self.data.box, factor=12, effective_from=self.data.day)
        RoutingOperation.objects.filter(pk=self.data.operation.pk).update(quantity_basis=1, quantity_uom=carton)
        run = self.run_costing(quantity=Decimal(12))
        self.assertEqual(run.run_status, "LOCKED", run.context_jsonb)
        self.assertEqual(self.line(run, "RESOURCE_COST").amount, Decimal(10000))

    def test_material_conversion_decimal_from_master(self):
        gram = Uom.objects.create(category=self.data.kg.category, code="G", name="Gram", symbol="g")
        UomConversion.objects.create(from_uom=gram, to_uom=self.data.kg, factor=Decimal("0.001"), effective_from=self.data.day)
        RecipeLine.objects.filter(pk=self.data.recipe_lines[0].pk).update(qty=500, uom=gram)
        run = self.run_costing()
        self.assertEqual(self.line(run, "MATERIAL_COST").amount, Decimal(25000))

    def test_missing_conversion_failed_no_identity_fallback(self):
        gram = Uom.objects.create(category=self.data.kg.category, code="G", name="Gram", symbol="g")
        RecipeLine.objects.filter(pk=self.data.recipe_lines[0].pk).update(uom=gram)
        self.assert_failed(self.run_costing(), "MISSING_CONVERSION")

    def test_competing_conversions_fail_without_guessed_specificity(self):
        gram = Uom.objects.create(category=self.data.kg.category, code="G", name="Gram", symbol="g")
        for item in (None, self.data.items[0]):
            UomConversion.objects.create(from_uom=gram, to_uom=self.data.kg, factor=Decimal("0.001"), item=item, effective_from=self.data.day)
        RecipeLine.objects.filter(pk=self.data.recipe_lines[0].pk).update(uom=gram)
        self.assert_failed(self.run_costing(), "AMBIGUOUS_CONVERSION")

    def test_costing_date_price_end_inclusive_and_future_not_selected(self):
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(effective_to=self.data.day)
        SupplierPrice.objects.create(organization=self.data.company, supplier=self.data.supplier, item=self.data.items[0], price_uom=self.data.kg,
            currency_code=self.data.currency, unit_price=20000, status="EFFECTIVE", effective_from=self.data.day+timedelta(days=1))
        self.assertEqual(self.run_costing().full_cost, Decimal(60000))
        self.assertEqual(self.run_costing(costing_date=self.data.day+timedelta(days=1)).full_cost, Decimal(80000))

    def test_missing_price_failed_not_zero(self):
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(status="DRAFT")
        self.assert_failed(self.run_costing(), "MISSING_PRICE")

    def test_ambiguous_price_failed_not_latest_cheapest(self):
        SupplierPrice.objects.create(organization=self.data.company, supplier=self.data.supplier, item=self.data.items[0], price_uom=self.data.kg,
            currency_code=self.data.currency, unit_price=1, status="EFFECTIVE", effective_from=self.data.day)
        self.assert_failed(self.run_costing(), "AMBIGUOUS_PRICE")

    def test_quantity_tier_unmet_is_missing_price(self):
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(min_qty=100)
        self.assert_failed(self.run_costing(), "MISSING_PRICE")

    def test_missing_fx_failed(self):
        usd = Currency.objects.create(code="USD", name="Đô la Mỹ")
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(currency_code=usd)
        self.assert_failed(self.run_costing(), "MISSING_FX")

    def test_undefined_tax_treatment_fail_closed(self):
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(tax_inclusive=True, tax_rate=Decimal("0.1"))
        self.assert_failed(self.run_costing(), "UNSUPPORTED_TAX")

    def test_missing_resource_rate_failed(self):
        ResourceRate.objects.filter(pk=self.data.rate.pk).update(effective_to=self.data.day-timedelta(days=1))
        self.assert_failed(self.run_costing(), "MISSING_RATE")

    def test_ambiguous_resource_rate_type_failed(self):
        ResourceRate.objects.create(organization=self.data.company, resource=self.data.resource, rate_type="OTHER", amount=1,
            currency_code=self.data.currency, per_uom=self.data.h, status="EFFECTIVE", effective_from=self.data.day)
        self.assert_failed(self.run_costing(), "AMBIGUOUS_RATE")

    def test_overlapping_bom_fail(self):
        RecipeVersion.objects.create(recipe=self.data.recipe, version_no=2, output_qty=1, output_uom=self.data.kg, status="EFFECTIVE", effective_from=self.data.day)
        self.assert_failed(self.run_costing(), "AMBIGUOUS_SOURCE")

    def test_no_bom_active_at_date_fails(self):
        RecipeVersion.objects.filter(pk=self.data.recipe_version.pk).update(effective_from=self.data.day+timedelta(days=1))
        self.assert_failed(self.run_costing(), "MISSING_SOURCE")

    def test_missing_packaging_basis_fails(self):
        self.assert_failed(self.run_costing(packaging_quantity=None, packaging_uom=None))

    def test_missing_packaging_assignment_fails(self):
        self.data.assignment.delete()
        self.assert_failed(self.run_costing(), "MISSING_SOURCE")

    def test_routing_missing_quantity_basis_fails(self):
        type(self.data.routing_version).objects.filter(pk=self.data.routing_version.pk).update(batch_size=None)
        self.assert_failed(self.run_costing())

    def test_allocation_missing_denominator_fails(self):
        type(self.data.period).objects.filter(pk=self.data.period.pk).update(normal_capacity=None)
        self.assert_failed(self.run_costing(), "MISSING_DENOMINATOR")

    def test_unsupported_allocation_driver_not_fake_denominator(self):
        type(self.data.rule).objects.filter(pk=self.data.rule.pk).update(basis_type="MACHINE_HOUR")
        self.assert_failed(self.run_costing())

    def test_formula_division_by_zero_failed_safe_error(self):
        formula = Formula.objects.create(organization=self.data.company, code="BROKEN", name="Chia cho không", output_element=self.data.elements["FULL_COST"])
        version = FormulaVersion.objects.create(formula=formula, version_no=1, expression="$MATERIAL_COST / 0", status="EFFECTIVE", validation_status="VALID", effective_from=self.data.day)
        CostingSchemeLine.objects.filter(pk=self.data.scheme_lines["FULL_COST"].pk).update(formula_version=version)
        self.assert_failed(self.run_costing(), "FORMULA_ERROR")

    def test_persistence_failure_rolls_back_all_lines_and_snapshots(self):
        seal(self.data)
        real_bulk = CostingRunLine.objects.bulk_create
        def fail_after_insert(rows, **kwargs):
            real_bulk(rows[:1], **kwargs)
            raise RuntimeError("internal confidential exception")
        with patch("apps.costing.run_services.CostingRunLine.objects.bulk_create", side_effect=fail_after_insert), self.assertLogs("apps.costing.run_services", level="ERROR"):
            run = self.run_costing()
        self.assert_failed(run, "SYSTEM_ERROR")
        self.assertNotIn("confidential", str(run.context_jsonb))
        self.assertContains(self.client.get(self.url("detail", run)), "Mã tham chiếu")

    def test_idempotency_same_request_and_mismatched_request(self):
        seal(self.data); token = uuid.uuid4()
        data = request_data(self.data)
        first = create_run(workspace=self.workspace, data=data, idempotency_key=token)
        self.assertEqual(create_run(workspace=self.workspace, data=data, idempotency_key=token).pk, first.pk)
        with self.assertRaisesMessage(ValidationError, "dữ liệu khác"):
            create_run(workspace=self.workspace, data=request_data(self.data, quantity=Decimal(2)), idempotency_key=token)
        self.assertEqual(CostingRun.objects.count(), 1)

    def test_history_only_stored_results_after_source_changes(self):
        run = self.run_costing(); before = run.version_snapshot_jsonb
        Product.objects.filter(pk=self.data.product.pk).update(name="Tên mới")
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(unit_price=999999)
        ResourceRate.objects.filter(pk=self.data.rate.pk).update(amount=999999)
        self.data.currency.name = "Tên tiền tệ mới"; self.data.currency.save()
        line = self.line(run, "MATERIAL_COST")
        with patch("apps.costing.run_services.execute", side_effect=AssertionError("must not recalculate")), CaptureQueriesContext(connection) as queries:
            for action in ("detail", "snapshot", "trace"):
                response = self.client.get(self.url(action, run, line if action == "trace" else None))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "999.999")
        for query in queries:
            for table in ("supplier_price", "resource_rate", "recipe", "formula_version", "organization_member", "product", "sku"):
                self.assertNotIn('FROM "'+table+'"', query["sql"])
                self.assertNotIn('JOIN "'+table+'"', query["sql"])
        run.refresh_from_db(); self.assertEqual(run.version_snapshot_jsonb, before); self.assertEqual(run.full_cost, 60000)
        self.assertContains(self.client.get(self.url("detail", run)), "CAP — Cà phê")

    def test_completed_header_and_lines_database_immutable(self):
        run = self.run_costing(); line = self.line(run, "MATERIAL_COST")
        for action in (lambda: CostingRun.objects.filter(pk=run.pk).update(full_cost=1), lambda: CostingRunLine.objects.filter(pk=line.pk).update(amount=1), lambda: CostingRunLine.objects.filter(pk=line.pk).delete()):
            with self.assertRaises(DatabaseError), transaction.atomic(): action()

    def test_rerun_new_record_old_result_unchanged(self):
        first = self.run_costing()
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(unit_price=20000)
        response = self.client.post(self.url("rerun", first), self.post_data())
        self.assertEqual(response.status_code, 302)
        second = CostingRun.objects.exclude(pk=first.pk).get()
        self.assertEqual(second.supersedes_run_id, first.pk); self.assertEqual(second.full_cost, 80000)
        first.refresh_from_db(); self.assertEqual(first.full_cost, 60000); self.assertEqual(first.run_status, "LOCKED")

    def test_anonymous_list_create_detail_without_membership(self):
        seal(self.data)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(self.url("create"), self.post_data())
            self.assertEqual(response.status_code, 302)
            run = CostingRun.objects.get()
            for action in ("list", "create", "detail", "snapshot", "rerun"):
                self.assertEqual(self.client.get(self.url(action, run if action not in ("list", "create") else None)).status_code, 200)
        self.assertFalse(any('"organization_member"' in q["sql"] for q in queries))
        self.assertNotIn("sessionid", response.cookies)

    def test_csrf_enforced_and_no_auth_redirect(self):
        seal(self.data)
        client = Client(enforce_csrf_checks=True)
        response = client.get(self.url("create"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.post(self.url("create"), self.post_data()).status_code, 403)
        self.assertEqual(client.post(self.url("create"), self.post_data(), HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 302)

    def test_invalid_form_keeps_input_and_does_not_create_run(self):
        seal(self.data)
        for changes in ({"quantity": "0"}, {"product": ""}, {"costing_date": "bad"}, {"packaging_quantity": ""}):
            response = self.client.post(self.url("create"), self.post_data(**changes), HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
            self.assertNotContains(response, "<!doctype")
        self.assertFalse(CostingRun.objects.exists())

    def test_search_filters_sort_pagination_query_state(self):
        run = self.run_costing()
        for q in (run.run_no, "Cà phê", "CAP_BOX", "Giá thành sản xuất"):
            self.assertEqual(self.client.get(self.url(), {"q": q}).context["page_obj"].paginator.count, 1)
        for query in ({"product": self.data.product.pk}, {"sku": self.data.sku.pk}, {"scheme": self.data.scheme.pk}, {"status": "LOCKED"}, {"date_from": self.data.day.isoformat(), "date_to": self.data.day.isoformat()}):
            self.assertEqual(self.client.get(self.url(), query).context["page_obj"].paginator.count, 1)
        self.assertContains(self.client.get(self.url(), {"status": "FAILED"}), "Không có kết quả phù hợp.")
        self.assertEqual(self.client.get(self.url(), {"date_to": "bad"}).context["page_obj"].paginator.count, 0)
        for i in range(26):
            self.run_costing(quantity=Decimal(i+2))
        response = self.client.get(self.url(), {"sort": "-total_cost", "per_page": 25, "page": 2, "date_from": self.data.day.isoformat()})
        self.assertEqual(len(response.context["records"]), 2)
        self.assertEqual(response.context["current_sort"], "-total_cost")
        self.assertContains(response, "date_from=2026-10-07")
        self.assertEqual(self.client.get(self.url(), {"per_page": 50}).context["page_obj"].paginator.count, 27)

    def test_empty_state_htmx_and_history_restore(self):
        self.assertContains(self.client.get(self.url()), "Chưa có lần tính giá thành.")
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertNotContains(response, "<!doctype"); self.assertContains(response, 'id="reference-data-table"')
        self.assertContains(self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"), "<!doctype")

    def test_dependent_sku_scheme_and_packaging_inputs_htmx(self):
        seal(self.data)
        response = self.client.get(self.url("options"), {"product": self.data.product.pk, "scheme": self.data.scheme.pk, "costing_date": self.data.day.isoformat()}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Cà phê đóng hộp"); self.assertContains(response, "Sản lượng cơ sở đóng gói")
        self.assertNotContains(response, "<!doctype")
        self.assertNotContains(self.client.get(self.url("options"), {"product": "bad"}, HTTP_HX_REQUEST="true"), "Cà phê đóng hộp")

    def test_inactive_dropdowns_and_sku_product_mismatch(self):
        seal(self.data)
        other = Product.objects.create(organization=self.data.company, code="OTHER", name="Khác", costing_uom=self.data.kg)
        form = RunForm(self.post_data(product=other.pk), workspace=self.workspace)
        self.assertFalse(form.is_valid()); self.assertIn("sku", form.errors)
        Sku.objects.filter(pk=self.data.sku.pk).update(is_active=False)
        form = RunForm(workspace=self.workspace, initial={"product": self.data.product.pk, "costing_date": self.data.day})
        self.assertFalse(form.fields["sku"].queryset.exists())

    def test_detail_trace_snapshot_partials_and_pagination(self):
        run = self.run_costing(); line = self.line(run, "MATERIAL_COST")
        for action in ("detail", "snapshot", "trace"):
            response = self.client.get(self.url(action, run, line if action == "trace" else None), HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200); self.assertNotContains(response, "<!doctype")
        response = self.client.get(self.url("detail", run), HTTP_HX_REQUEST="true", HTTP_HX_TARGET="run-lines-table")
        self.assertContains(response, 'id="run-lines-table"'); self.assertNotContains(response, 'id="run-detail"')
        self.assertContains(self.client.get(self.url("snapshot", run)), "07/10/2026")
        self.assertNotContains(self.client.get(self.url("snapshot", run)), "07/10/2026 00:00")

    def test_foreign_run_and_line_references_are_not_exposed(self):
        run = self.run_costing(); line = self.line(run, "MATERIAL_COST")
        second = self.run_costing()
        self.assertEqual(self.client.get(self.url("trace", second, line)).status_code, 404)
        self.assertEqual(self.client.get(reverse("costing:run_detail", args=[uuid.uuid4()])).status_code, 404)
        other = Organization.objects.create(code="OTHER", name="Khác")
        with override_settings(DEFAULT_ORGANIZATION_ID=other.pk):
            self.assertEqual(self.client.get(self.url("detail", run)).status_code, 404)

    def test_float_input_rejected_and_decimal_json_lossless(self):
        with self.assertRaises(CostingError): json_data(0.1)
        self.assertEqual(json_data(Decimal("0.123456789123456789")), "0.123456789123456789")
        seal(self.data)
        with self.assertRaises(ValidationError): create_run(workspace=self.workspace, data=request_data(self.data, quantity=1.5), idempotency_key=uuid.uuid4())

    def test_all_source_queries_batched_as_material_lines_grow(self):
        def measure():
            with CaptureQueriesContext(connection) as queries: self.run_costing()
            return len(queries), sum('FROM "supplier_price"' in q["sql"] for q in queries)
        baseline, initial_prices = measure()
        Recipe.objects.filter(pk=self.data.recipe.pk).update(is_active=False)
        self.data.recipe = Recipe.objects.create(organization=self.data.company, product=self.data.product, code="MANY", name="Nhiều thành phần")
        self.data.recipe_version = RecipeVersion.objects.create(recipe=self.data.recipe, version_no=1, output_qty=1, output_uom=self.data.kg, effective_from=self.data.day)
        for row in self.data.recipe_lines:
            RecipeLine.objects.create(recipe_version=self.data.recipe_version, component_item=row.component_item, qty=row.qty, uom=row.uom, display_order=row.display_order)
        for i in range(15):
            RecipeLine.objects.create(recipe_version=self.data.recipe_version, component_item=self.data.items[0], qty=1, uom=self.data.kg, display_order=100+i)
        count, prices = measure()
        self.assertEqual(prices, 2)  # one material batch and one packaging batch
        self.assertEqual(prices, initial_prices)
        self.assertEqual(count, baseline)
        self.assertLess(count, 65)

    def test_vietnamese_pages_display_and_numeric_formats(self):
        run = self.run_costing()
        response = self.client.get(self.url("detail", run))
        self.assertContains(response, "60.000 VND")
        self.assertContains(response, "07/10/2026")
        self.assertContains(response, "66,67%")
        self.assertNotContains(response, "66,666666")
        for action in ("list", "create", "detail", "snapshot"):
            text = self.client.get(self.url(action, run if action in ("detail", "snapshot") else None)).content.decode()
            for english in (">Create<", ">Save<", ">Cancel<", ">Status<", ">Actions<", ">True<", ">False<"):
                self.assertNotIn(english, text)

    def test_zero_cost_has_zero_summary_and_safe_percentage(self):
        SupplierPrice.objects.all().update(unit_price=0)
        ResourceRate.objects.all().update(amount=0)
        type(self.data.period).objects.all().update(amount=0)
        run = self.run_costing()
        self.assertEqual(run.run_status, "LOCKED", run.context_jsonb)
        self.assertEqual(run.full_cost, Decimal(0))
        response = self.client.get(self.url("detail", run))
        self.assertContains(response, "0 VND")
        self.assertTrue(all(line.share is None for line in response.context["lines"]))

    def test_manual_inputs_typed_stored_bounded_and_used_by_formula(self):
        row = self.data.scheme_lines["MATERIAL_COST"]
        CostingSchemeLine.objects.filter(pk=row.pk).update(source_mode="MANUAL", system_resolver_code=None, min_override_value=10, max_override_value=100)
        run = self.run_costing(manual={"MATERIAL_COST": Decimal(50)})
        self.assertEqual(run.full_cost, 20050)
        self.assertEqual(self.line(run, "MATERIAL_COST").input_snapshot_jsonb["raw_value"], "50")
        self.assertEqual(run.context_jsonb["request"]["manual"], {"MATERIAL_COST": "50"})
        self.assert_failed(self.run_costing(manual={"MATERIAL_COST": Decimal(101)}))

    def test_manual_keys_and_missing_formula_provider_rejected(self):
        self.assert_failed(self.run_costing(manual={"arbitrary": Decimal(1)}), "INVALID_INPUT")

    def test_formula_missing_variable_controlled_failed_run(self):
        self.data.scheme_lines["MATERIAL_COST"].delete()
        self.assert_failed(self.run_costing())

    def test_invalid_formula_version_controlled_failed_run(self):
        # Referencing an unvalidated version may exist in legacy DRAFT config.
        formula = Formula.objects.create(organization=self.data.company, code="INVALID", name="Chưa hợp lệ", output_element=self.data.elements["FULL_COST"])
        version = FormulaVersion.objects.create(formula=formula, version_no=1, expression="1")
        CostingSchemeLine.objects.filter(pk=self.data.scheme_lines["FULL_COST"].pk).update(formula_version=version)
        self.assert_failed(self.run_costing())

    def test_resource_rate_effective_dates_end_inclusive(self):
        ResourceRate.objects.filter(pk=self.data.rate.pk).update(effective_to=self.data.day)
        ResourceRate.objects.create(organization=self.data.company, resource=self.data.resource, rate_type="STANDARD", amount=20000,
            currency_code=self.data.currency, per_uom=self.data.h, status="EFFECTIVE", effective_from=self.data.day+timedelta(days=1))
        self.assertEqual(self.run_costing().full_cost, 60000)
        self.assertEqual(self.run_costing(costing_date=self.data.day+timedelta(days=1)).full_cost, 70000)

    def test_quantity_resolvers_cache_each_target_unit(self):
        for i, unit in enumerate((self.data.kg, self.data.box)):
            element = CostElement.objects.create(organization=self.data.company, code=f"Q{i}", name="Sản lượng", value_type="QUANTITY", dimension_code=unit.category.dimension_code,
                default_uom=unit, default_source_mode="SYSTEM", accounting_scope="ANALYTICS", cost_scope="ANALYTICS")
            CostingSchemeLine.objects.create(scheme_version=self.data.scheme_version, line_code=f"Q{i}", label="Sản lượng", line_type="INFO", source_mode="SYSTEM", system_resolver_code="RUN_QUANTITY",
                cost_element=element, display_order=70+i, cost_scope="ANALYTICS")
        Sku.objects.filter(pk=self.data.sku.pk).update(net_quantity=2)
        run = self.run_costing()
        self.assertEqual(self.line(run, "Q0").quantity, 2)
        self.assertEqual(self.line(run, "Q1").quantity, 1)

    def test_formula_without_element_preserves_inferred_money_type(self):
        CostingSchemeLine.objects.create(scheme_version=self.data.scheme_version, line_code="INFO", label="Thông tin", line_type="INFO", source_mode="FORMULA",
            formula_version=self.data.formula_version, display_order=90, cost_scope="ANALYTICS")
        run = self.run_costing()
        self.assertEqual(run.run_status, "LOCKED", run.context_jsonb)
        self.assertEqual(self.line(run, "INFO").value_type, "MONEY")
        self.assertEqual(self.line(run, "INFO").amount, 60000)

    def test_rounding_at_line_boundary_and_storage_overflow_fail(self):
        CostingSchemeLine.objects.filter(pk=self.data.scheme_lines["MATERIAL_COST"].pk).update(rounding_scale=0)
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(unit_price=Decimal("10000.255"))
        run = self.run_costing()
        self.assertEqual(self.line(run, "MATERIAL_COST").amount, 40001)
        self.assertEqual(Decimal(self.line(run, "MATERIAL_COST").input_snapshot_jsonb["raw_value"]), Decimal("40000.51"))
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(unit_price=Decimal("9999999999999999"))
        self.assert_failed(self.run_costing(), "PRECISION_OVERFLOW")
