from datetime import date, datetime
from decimal import Decimal as D
from unittest.mock import patch
from django.test import TestCase, Client
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import Organization, PriceScenario, Channel, ChannelFeeRule, TaxRule, FxRate, CostingRun, Product, Sku
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import create_golden_run, stored_fingerprint
from .scenario_forms import ScenarioForm
from .scenario_services import save_scenario, calculate_scenario
from .engine.context import digest


class PricingScenarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        cls.demo = seed_demo()
        cls.workspace = cls.demo.workspace
        cls.costing_run = create_golden_run(cls.demo)
        cls.channel = Channel.objects.create(organization=cls.workspace.organization, code="DIRECT", name="Kênh trực tiếp", channel_type="D2C", market_code="VN", default_currency_code=cls.demo.records["VND"])
        cls.fee = ChannelFeeRule.objects.create(organization=cls.workspace.organization, channel=cls.channel, fee_type="COMMISSION", fee_base="LIST_PRICE", rate=D("0.05"), tax_inclusive=True, effective_from=date(2026, 1, 1), effective_to=date(2026, 11, 1), status="EFFECTIVE")
        cls.fixed = ChannelFeeRule.objects.create(organization=cls.workspace.organization, channel=cls.channel, fee_type="PAYMENT_FEE", fee_base="LIST_PRICE", fixed_amount=D(1000), currency_code=cls.demo.records["VND"], tax_inclusive=True, effective_from=date(2026, 1, 1), status="EFFECTIVE")
        cls.tax = TaxRule.objects.create(organization=cls.workspace.organization, jurisdiction_code="VN", tax_type="VAT", tax_base="SELLING_PRICE", rate=D("0.1"), inclusive=True, effective_from=date(2026, 1, 1), effective_to=date(2026, 11, 1), status="EFFECTIVE")

    @classmethod
    def payload(cls, **overrides):
        return dict(code="TEST_SCENARIO", name="Kịch bản mẫu", product=cls.costing_run.product_id, sku=cls.costing_run.sku_id, base_run=cls.costing_run.pk, channel=cls.channel.pk,
            pricing_date="2026-10-08", pricing_method="MARGIN", target_margin="20", currency_code="VND", tax_mode="REQUIRED", jurisdiction_code="VN", transaction_type="", fx_rate_type="SPOT") | overrides

    def create(self, **overrides):
        form = ScenarioForm(self.payload(**overrides), workspace=self.workspace)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        return save_scenario(workspace=self.workspace, data=form.cleaned_data)

    def calculate(self, record=None):
        return calculate_scenario(workspace=self.workspace, instance=record or self.create())

    def url(self, action="list", pk=None): return reverse(f"pricing:scenario_{action}", args=[pk] if pk else [])

    def test_anonymous_list_empty_full_partial_and_history_restore(self):
        full = self.client.get(self.url())
        self.assertContains(full, "Chưa có kịch bản giá bán.")
        self.assertContains(full, '<html lang="vi"')
        self.assertContains(full, 'href="/pricing/scenarios/compare/"')
        self.assertNotContains(self.client.get(self.url(), HTTP_HX_REQUEST="true"), "<!doctype")
        self.assertContains(self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"), "<!doctype")

    def test_create_normalizes_fraction_and_company(self):
        response = self.client.post(self.url("create"), self.payload(code=" test ", name=" Tên mẫu "))
        self.assertEqual(response.status_code, 302)
        row = PriceScenario.objects.get(code="TEST")
        self.assertEqual((row.name, row.target_margin, row.organization_id, row.status), ("Tên mẫu", D("0.2"), self.workspace.organization.pk, "DRAFT"))
        self.assertIsNone(row.created_by)
        self.assertIsNone(row.approved_by)

    def test_duplicate_code_and_invalid_form_retains_input(self):
        self.create()
        for overrides, field in (({"code": " test_scenario "}, "code"), ({"base_run": ""}, "base_run"), ({"channel": ""}, "channel"), ({"target_margin": "100"}, "target_margin"), ({"pricing_date": "bad"}, "pricing_date"), ({"target_margin": ""}, "target_margin"), ({"target_markup": "20"}, "target_markup"), ({"jurisdiction_code": ""}, "jurisdiction_code")):
            with self.subTest(field=field):
                response = self.client.post(self.url("create"), self.payload(**overrides), HTTP_HX_REQUEST="true")
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertContains(response, "Vui lòng kiểm tra")
                self.assertNotContains(response, "<!doctype")

    def test_edit_draft_and_detail(self):
        row = self.create()
        response = self.client.post(self.url("edit", row.pk), self.payload(name="Tên mới"))
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(self.url("detail", row.pk)), "Tên mới")
        self.assertContains(self.client.get(self.url("edit", row.pk)), 'value="20"')

    def test_date_range_validation(self):
        form = ScenarioForm(self.payload(valid_from="2026-11-01", valid_to="2026-10-31"), workspace=self.workspace)
        self.assertFalse(form.is_valid())
        self.assertIn("valid_to", form.errors)

    def test_search_filters_sort_pagination_and_query_state(self):
        row = self.create()
        PriceScenario.objects.bulk_create(PriceScenario(organization=self.workspace.organization, code=f"Z{i:03}", name=f"Kịch bản {i}", base_run=self.costing_run, channel=self.channel, pricing_method="MARGIN", target_margin=D("0.2"), currency_code_id="VND", scenario_context_jsonb=row.scenario_context_jsonb) for i in range(28))
        for values in ({"q": "TEST_SCENARIO"}, {"q": "Kịch bản mẫu"}, {"q": "CAPPUCCINO_BOX20", "product": self.costing_run.product_id, "sku": self.costing_run.sku_id, "channel": self.channel.pk, "currency_code": "VND", "status": "DRAFT", "date_from": "2026-10-08", "date_to": "2026-10-08"}):
            response = self.client.get(self.url(), values)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["page_obj"].paginator.count, 29 if "product" in values else 1)
        response = self.client.get(self.url(), {"sort": "-code", "page": 2, "per_page": 25, "status": "DRAFT"}, HTTP_HX_REQUEST="true")
        self.assertEqual(len(response.context["records"]), 4)
        self.assertEqual(response.context["records"][0].code, "Z002")
        self.assertContains(response, "status=DRAFT")
        self.assertEqual(self.client.get(self.url(), {"date_from": "bad"}).context["page_obj"].paginator.count, 0)

    def test_dependent_options_scoped_no_global_run_load(self):
        options = self.client.get(self.url("options"), {"product": self.costing_run.product_id, "sku": self.costing_run.sku_id, "channel": self.channel.pk}, HTTP_HX_REQUEST="true")
        self.assertContains(options, "58.300")
        self.assertContains(options, "07/10/2026")
        self.assertNotContains(options, "<!doctype")
        self.assertEqual(options.context["form"]["currency_code"].value(), "VND")
        self.assertEqual(options.context["form"]["jurisdiction_code"].value(), "VN")
        self.assertEqual(self.client.get(self.url("options"), HTTP_HX_REQUEST="true").context["form"].fields["base_run"].queryset.count(), 0)

    def test_incomplete_costing_run_rejected(self):
        import uuid
        values = CostingRun.objects.values().get(pk=self.costing_run.pk)
        for name in ("id", "public_id", "run_no", "idempotency_key", "locked_at"): values.pop(name)
        values["run_status"] = "FAILED"
        failed = CostingRun.objects.create(**values, public_id=uuid.uuid4(), run_no="FAILED_TEST")
        form = ScenarioForm(self.payload(base_run=failed.pk), workspace=self.workspace)
        self.assertFalse(form.is_valid())
        self.assertIn("base_run", form.errors)

    def test_mismatched_product_or_sku_rejected(self):
        form = ScenarioForm(self.payload(sku=""), workspace=self.workspace)
        self.assertFalse(form.is_valid())
        self.assertIn("base_run", form.errors)

    def test_golden_all_metrics_hash_and_costing_unchanged(self):
        before = stored_fingerprint(self.costing_run)
        row = self.calculate()
        self.assertEqual(row.status, "CALCULATED", row.output_snapshot_jsonb)
        expected = {"unit_cost": "58300", "fees": "5498.62068966", "tax": "8179.31034483", "profit": "17994.48275861", "gross_price": "89972.41379310", "actual_margin": "0.2000000000"}
        for key, value in expected.items(): self.assertEqual(D(row.output_snapshot_jsonb["result"][key]), D(value), key)
        self.assertEqual(before, stored_fingerprint(self.costing_run))
        snapshot = row.output_snapshot_jsonb
        self.assertEqual(snapshot["hash"], digest({k: v for k, v in snapshot.items() if k != "hash"}))
        self.assertEqual(len(snapshot["result"]["fee_lines"]), 2)
        self.assertEqual(D(snapshot["result"]["reconciliation"]), 0)

    def test_calculate_is_post_csrf_enforced_and_htmx_partial(self):
        row = self.create()
        self.assertEqual(self.client.get(self.url("calculate", row.pk)).status_code, 405)
        response = Client(enforce_csrf_checks=True).post(self.url("calculate", row.pk))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url("calculate", row.pk), HTTP_HX_REQUEST="true")
        self.assertContains(response, "Cấu thành giá bán")
        self.assertContains(response, "89.972,4137931")
        self.assertContains(response, "Đã lưu kết quả giá bán.")
        self.assertNotContains(response, "<!doctype")

    def test_calculated_immutable_idempotent_and_clone(self):
        row = self.calculate()
        original = row.output_snapshot_jsonb
        self.assertEqual(self.calculate(row).output_snapshot_jsonb, original)
        self.assertEqual(self.client.post(self.url("edit", row.pk), self.payload()).status_code, 409)
        self.assertEqual(self.client.get(self.url("edit", row.pk)).status_code, 302)
        clone = self.client.get(self.url("create"), {"source": row.pk})
        self.assertEqual(clone.context["form"]["code"].value(), "")
        self.assertEqual(clone.context["form"]["target_margin"].value(), D(20))
        row.refresh_from_db()
        self.assertEqual(row.output_snapshot_jsonb, original)

    def test_future_rules_and_history_read_only_persisted_sources(self):
        row = self.calculate()
        original = row.output_snapshot_jsonb
        ChannelFeeRule.objects.create(organization=self.workspace.organization, channel=self.channel, fee_type="COMMISSION", fee_base="LIST_PRICE", rate=D("0.06"), tax_inclusive=True, effective_from=date(2026, 11, 1), status="EFFECTIVE")
        TaxRule.objects.create(organization=self.workspace.organization, jurisdiction_code="VN", tax_type="VAT", tax_base="SELLING_PRICE", rate=D("0.11"), inclusive=True, effective_from=date(2026, 11, 1), status="EFFECTIVE")
        future = self.calculate(self.create(code="FUTURE", pricing_date="2026-11-01"))
        self.assertEqual(future.status, "CALCULATED", future.output_snapshot_jsonb)
        self.assertNotEqual(future.suggested_price, row.suggested_price)
        for day in ("2026-10-08", "2026-10-31"):
            same = self.calculate(self.create(code="DAY_" + day, pricing_date=day))
            self.assertEqual(same.output_snapshot_jsonb["result"], original["result"])
        Channel.objects.filter(pk=self.channel.pk).update(name="Tên đã thay đổi", is_active=False)
        with CaptureQueriesContext(connection) as capture:
            response = self.client.get(self.url("detail", row.pk))
        self.assertContains(response, "Kênh trực tiếp")
        self.assertNotContains(response, "Tên đã thay đổi")
        for table in ("channel_fee_rule", "tax_rule", "fx_rate", "organization_member"):
            self.assertFalse(any(f'FROM "{table}"' in q["sql"] for q in capture.captured_queries), table)
        row.refresh_from_db()
        self.assertEqual(row.output_snapshot_jsonb, original)

    def test_missing_tax_is_controlled_draft_error(self):
        row = self.calculate(self.create(jurisdiction_code="MISSING"))
        self.assertEqual(row.status, "DRAFT")
        self.assertEqual(row.output_snapshot_jsonb["errors"][0]["code"], "MISSING_TAX")
        self.assertIsNone(row.suggested_price)

    def test_missing_fx_and_inverse_only_do_not_fallback(self):
        FxRate.objects.create(organization=self.workspace.organization, rate_type="SPOT", from_currency_code_id="USD", to_currency_code_id="VND", rate=D(26000), effective_at=timezone.make_aware(datetime(2026, 1, 1)), source_name="Nguồn nội bộ")
        row = self.calculate(self.create(currency_code="USD"))
        self.assertEqual(row.output_snapshot_jsonb["errors"][0]["code"], "MISSING_FX")

    def test_cross_currency_exact_direction_effective_instant_snapshot(self):
        fx = FxRate.objects.create(organization=self.workspace.organization, rate_type="SPOT", from_currency_code_id="VND", to_currency_code_id="USD", rate=D("0.00004"), effective_at=timezone.make_aware(datetime(2026, 1, 1)), valid_to=timezone.make_aware(datetime(2026, 11, 1)), source_name="Nguồn nội bộ")
        row = self.calculate(self.create(currency_code="USD"))
        self.assertEqual(row.status, "CALCULATED", row.output_snapshot_jsonb)
        self.assertEqual(D(row.output_snapshot_jsonb["result"]["unit_cost"]), D("2.332"))
        self.assertEqual(row.output_snapshot_jsonb["trace"]["fx"][0]["id"], fx.pk)
        FxRate.objects.create(organization=self.workspace.organization, rate_type="SPOT", from_currency_code_id="VND", to_currency_code_id="USD", rate=D("0.00005"), effective_at=timezone.make_aware(datetime(2026, 11, 1)), source_name="Nguồn kỳ mới")
        self.assertEqual(self.calculate(row).output_snapshot_jsonb, row.output_snapshot_jsonb)

    def test_ambiguous_fx_rejected_and_zero_fx_guarded(self):
        fx = FxRate.objects.create(organization=self.workspace.organization, rate_type="SPOT", from_currency_code_id="VND", to_currency_code_id="USD", rate=D("0.00004"), effective_at=timezone.make_aware(datetime(2026, 1, 1)), source_name="Nguồn nội bộ")
        FxRate.objects.create(organization=self.workspace.organization, rate_type="SPOT", from_currency_code_id="VND", to_currency_code_id="USD", rate=D("0.00005"), effective_at=timezone.make_aware(datetime(2026, 1, 1)), source_name="Nguồn trùng")
        row = self.calculate(self.create(currency_code="USD"))
        self.assertEqual(row.output_snapshot_jsonb["errors"][0]["code"], "AMBIGUOUS_FX")
        fx.rate = D(0)
        with patch("apps.pricing.selectors.get_effective_fx_rate", return_value=fx):
            row = self.calculate(self.create(code="ZERO_FX", currency_code="USD"))
        self.assertEqual(row.output_snapshot_jsonb["errors"][0]["code"], "INVALID_FX")

    def test_tax_exclusive_and_tax_rule_failure_paths(self):
        TaxRule.objects.filter(pk=self.tax.pk).update(inclusive=False)
        row = self.calculate()
        self.assertEqual(row.status, "CALCULATED")
        result = row.output_snapshot_jsonb["result"]
        self.assertEqual(D(result["listed_price"]) + D(result["tax"]), D(result["gross_price"]))
        for changes, code in (({"tax_base": "PRICE_AFTER_FEE"}, "UNSUPPORTED_TAX_BASE"), ({"tax_base": "SELLING_PRICE", "recoverable_ratio": D("0.1")}, "UNSUPPORTED_TAX_RECOVERY")):
            TaxRule.objects.filter(pk=self.tax.pk).update(**changes)
            invalid = self.calculate(self.create(code=code))
            self.assertEqual(invalid.output_snapshot_jsonb["errors"][0]["code"], code)

    def test_inactive_channel_and_invalid_persisted_inputs_rejected(self):
        row = self.create()
        Channel.objects.filter(pk=self.channel.pk).update(is_active=False)
        failed = self.calculate(row)
        self.assertEqual(failed.status, "DRAFT")
        self.assertTrue(failed.output_snapshot_jsonb["errors"])
        self.assertIsNone(failed.suggested_price)

    def test_markup_and_profit_per_unit_through_form(self):
        for method, extra in (("MARKUP", {"target_markup": "20"}), ("PROFIT_PER_UNIT", {"target_profit_per_unit": "12000"})):
            row = self.calculate(self.create(code=method, pricing_method=method, target_margin="", **extra))
            self.assertEqual(row.status, "CALCULATED", row.output_snapshot_jsonb)
            result = row.output_snapshot_jsonb["result"]
            if method == "MARKUP": self.assertEqual(D(result["actual_markup"]), D("0.2"))
            else: self.assertLessEqual(abs(D(result["profit"]) - D(12000)), D("0.00000001"))

    def test_future_fx_boundary_uses_new_rate_without_mutating_old_result(self):
        for rate, start, end in (("0.00004", datetime(2026, 1, 1), datetime(2026, 11, 1)), ("0.00005", datetime(2026, 11, 1), None)):
            FxRate.objects.create(organization=self.workspace.organization, rate_type="SPOT", from_currency_code_id="VND", to_currency_code_id="USD",
                rate=D(rate), effective_at=timezone.make_aware(start), valid_to=timezone.make_aware(end) if end else None, source_name="Nguồn kiểm thử")
        old = self.calculate(self.create(code="OLD_FX", currency_code="USD", tax_mode="NONE", pricing_date="2026-10-31"))
        new = self.calculate(self.create(code="NEW_FX", currency_code="USD", tax_mode="NONE", pricing_date="2026-11-01"))
        self.assertEqual((old.status, new.status), ("CALCULATED", "CALCULATED"))
        self.assertEqual(D(old.output_snapshot_jsonb["result"]["unit_cost"]), D("2.332"))
        self.assertEqual(D(new.output_snapshot_jsonb["result"]["unit_cost"]), D("2.915"))
        old.refresh_from_db()
        self.assertEqual(D(old.output_snapshot_jsonb["result"]["unit_cost"]), D("2.332"))

    def test_multiple_tax_types_parallel_and_same_type_tie_rejected(self):
        second = TaxRule.objects.create(organization=self.workspace.organization, jurisdiction_code="VN", tax_type="SURCHARGE", tax_base="SELLING_PRICE", rate=D("0.05"), inclusive=True, effective_from=date(2026, 1, 1), status="EFFECTIVE")
        row = self.calculate()
        self.assertEqual(row.status, "CALCULATED", row.output_snapshot_jsonb)
        self.assertEqual(len(row.output_snapshot_jsonb["result"]["tax_lines"]), 2)
        TaxRule.objects.create(organization=self.workspace.organization, jurisdiction_code="VN", tax_type=second.tax_type, tax_base="SELLING_PRICE", rate=D("0.02"), inclusive=True, effective_from=date(2026, 1, 1), status="EFFECTIVE")
        failed = self.calculate(self.create(code="TAX_TIE"))
        self.assertEqual(failed.output_snapshot_jsonb["errors"][0]["code"], "AMBIGUOUS_RULE")

    def test_invalid_fee_configuration_is_not_silently_used(self):
        broken = self.fee
        broken.rate = D(-1)
        with patch("apps.pricing.selectors.get_applicable_channel_fee_rules", return_value=[broken]):
            failed = self.calculate()
        self.assertEqual(failed.output_snapshot_jsonb["errors"][0]["code"], "INVALID_RULE")

    def test_demo_command_idempotency_future_and_historical_reconciliation(self):
        # Existing test rules would intentionally conflict with general VN taxes.
        ChannelFeeRule.objects.all().delete()
        TaxRule.objects.all().delete()
        from .demo_scenario import verify_pricing_demo
        report = verify_pricing_demo()
        counts = (PriceScenario.objects.count(), ChannelFeeRule.objects.count(), TaxRule.objects.count())
        again = verify_pricing_demo()
        self.assertEqual(counts, (PriceScenario.objects.count(), ChannelFeeRule.objects.count(), TaxRule.objects.count()))
        self.assertEqual(report, again)
        self.assertTrue(report["historical_unchanged"])
        self.assertEqual(report["costing_fingerprint_before"], report["costing_fingerprint_after"])
        self.assertTrue(all(D(row["delta"]) == 0 for row in report["future_comparisons"]))

    def test_conflicting_fee_is_not_arbitrarily_picked(self):
        ChannelFeeRule.objects.create(organization=self.workspace.organization, channel=self.channel, fee_type="COMMISSION", fee_base="LIST_PRICE", rate=D("0.07"), tax_inclusive=True, effective_from=date(2026, 1, 1), status="EFFECTIVE")
        row = self.calculate()
        self.assertEqual(row.output_snapshot_jsonb["errors"][0]["code"], "AMBIGUOUS_RULE")

    def test_sku_specificity_beats_general_priority(self):
        chosen = ChannelFeeRule.objects.create(organization=self.workspace.organization, channel=self.channel, sku=self.costing_run.sku, fee_type="COMMISSION", fee_base="LIST_PRICE", rate=D("0.04"), priority=-10, tax_inclusive=True, effective_from=date(2026, 1, 1), status="EFFECTIVE")
        row = self.calculate()
        ids = [line["source_id"] for line in row.output_snapshot_jsonb["result"]["fee_lines"]]
        self.assertIn(chosen.pk, ids)
        self.assertNotIn(self.fee.pk, ids)

    def test_unsupported_fee_tax_and_base_fail_closed(self):
        for field, value, code in (("fee_base", "PER_ORDER", "UNSUPPORTED_FEE_BASE"), ("tax_inclusive", False, "UNSUPPORTED_FEE_TAX"), ("refundable_ratio", D("0.5"), "UNSUPPORTED_REFUND")):
            with self.subTest(field=field):
                old = getattr(self.fee, field)
                ChannelFeeRule.objects.filter(pk=self.fee.pk).update(**{field: value})
                row = self.calculate(self.create(code="INVALID_" + field))
                self.assertEqual(row.output_snapshot_jsonb["errors"][0]["code"], code)
                ChannelFeeRule.objects.filter(pk=self.fee.pk).update(**{field: old})

    def test_no_tax_is_explicit_not_missing_rule_fallback(self):
        row = self.calculate(self.create(tax_mode="NONE", jurisdiction_code=""))
        self.assertEqual(row.status, "CALCULATED")
        self.assertEqual(row.output_snapshot_jsonb["result"]["tax"], "0")
        self.assertTrue(row.output_snapshot_jsonb["warnings"])

    def test_no_fee_warning_and_same_currency_does_not_query_fx(self):
        ChannelFeeRule.objects.all().delete()
        with CaptureQueriesContext(connection) as capture: row = self.calculate()
        self.assertEqual(row.status, "CALCULATED")
        self.assertEqual(row.output_snapshot_jsonb["result"]["fees"], "0")
        self.assertFalse(any('FROM "fx_rate"' in q["sql"] for q in capture.captured_queries))

    def test_no_n_plus_one_or_membership_queries_on_list(self):
        row = self.calculate()
        def count():
            with CaptureQueriesContext(connection) as capture: self.client.get(self.url())
            self.assertFalse(any("organization_member" in q["sql"] for q in capture.captured_queries))
            return len(capture)
        before = count()
        PriceScenario.objects.bulk_create(PriceScenario(organization=self.workspace.organization, code=f"COPY_{i}", name="Kịch bản", base_run=self.costing_run, channel=self.channel, pricing_method="MARGIN", currency_code_id="VND", scenario_context_jsonb=row.scenario_context_jsonb, output_snapshot_jsonb=row.output_snapshot_jsonb, status="CALCULATED") for i in range(20))
        self.assertEqual(count(), before)

    def test_unexpected_error_safe_and_logged(self):
        row = self.create()
        with patch("apps.pricing.scenario_services.execute", side_effect=RuntimeError("secret SQL")), self.assertLogs("apps.pricing.scenario_services", level="ERROR"):
            row = self.calculate(row)
        response = self.client.get(self.url("detail", row.pk))
        self.assertNotContains(response, "secret SQL")
        self.assertContains(response, "Mã tham chiếu")
