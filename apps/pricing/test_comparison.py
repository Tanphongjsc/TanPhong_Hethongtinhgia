"""Independent stored matrix fixtures: comparison must never run an engine."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal as D
import uuid
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from apps.core.models import Organization, PriceScenario, Currency, Channel, ChannelFeeRule, TaxRule, FxRate, CostingRun, Sku
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import create_golden_run, stored_fingerprint
from .comparison import load_selection, validate_compatibility, difference
from .comparison_presentation import matrix
from .comparison_selectors import candidates
from .engine.context import POLICY, digest


EXPECTED = (
    {"unit_cost": "58300", "fees": "5498.62068966", "tax": "8179.31034483", "gross_price": "89972.41379310", "pre_tax_revenue": "81793.10344827", "net_revenue": "76294.48275861", "profit": "17994.48275861", "actual_margin": "0.2", "actual_markup": "0.3086532206"},
    {"unit_cost": "58300", "fees": "6551.56030363", "tax": "9169.24374473", "gross_price": "92526.00506044", "pre_tax_revenue": "83356.76131571", "net_revenue": "76805.20101208", "profit": "18505.20101208", "actual_margin": "0.2", "actual_markup": "0.3174133964"},
    {"unit_cost": "58300", "fees": "6000", "tax": "9090.90909091", "gross_price": "100000", "pre_tax_revenue": "90909.09090909", "net_revenue": "84909.09090909", "profit": "26609.09090909", "actual_margin": "0.2660909091", "actual_markup": "0.4564166537"},
)


class ComparisonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        cls.demo = seed_demo()
        cls.organization = cls.demo.workspace.organization
        cls.costing_run = create_golden_run(cls.demo)
        cls.channel = Channel.objects.create(organization=cls.organization, code="DIRECT_COMPARE", name="Kênh mẫu", channel_type="D2C")
        cls.rows = []
        for index, values in enumerate(EXPECTED):
            snapshot = {"schema": 1, "policy": POLICY, "inputs": {"method": "MARGIN", "target": values["actual_margin"], "pricing_date": "2026-10-08" if index != 1 else "2026-11-01", "quantity": "1", "uom_id": cls.costing_run.quantity_uom_id, "currency": "VND"},
                "costing": {"id": cls.costing_run.pk, "public_id": str(cls.costing_run.public_id), "unit_cost": "58300", "currency": "VND", "effective_at": cls.costing_run.effective_at.isoformat(), "context": cls.costing_run.context_jsonb},
                "display": dict(cls.costing_run.context_jsonb["display"], channel="Kênh mẫu"), "result": dict(values,
                    fee_lines=[{"label": "Phí theo cấu hình đã lưu", "amount": values["fees"], "basis": values["gross_price"], "rate": "0.06" if index == 1 else "0.05", "fixed": "1000", "floor": None, "cap": None}],
                    tax_lines=[{"label": "Thuế đã lưu", "amount": values["tax"], "basis": values["pre_tax_revenue"], "rate": "0.11" if index == 1 else "0.1", "fixed": "0", "inclusive": True}]),
                "trace": {"fx": []}, "trace_id": f"TRACE-{index}", "sources": []}
            snapshot["hash"] = digest(snapshot)
            cls.rows.append(PriceScenario.objects.create(organization=cls.organization, code=chr(65 + index), name=f"Kịch bản {chr(65 + index)}", base_run=cls.costing_run, channel=cls.channel, pricing_method="MARGIN", currency_code_id="VND", target_margin=D(values["actual_margin"]), status="CALCULATED", output_snapshot_jsonb=snapshot))

    def url(self):
        return reverse("pricing:scenario_compare")

    def selection(self, rows=None):
        return load_selection(organization=self.organization, values=[str(r.pk) for r in (rows or self.rows)], required=True)

    def get(self, **values):
        return self.client.get(self.url(), {"scenario": [r.pk for r in self.rows], "compare": "1"} | values)

    def clone(self, row=None, **overrides):
        values = PriceScenario.objects.values().get(pk=(row or self.rows[0]).pk)
        values.pop("id")
        values["code"] = "EXTRA"
        for key, value in overrides.items():
            values[PriceScenario._meta.get_field(key).attname] = getattr(value, "pk", value)
        return PriceScenario.objects.create(**values)

    def change_snapshot(self, row, mutate):
        snap = deepcopy(row.output_snapshot_jsonb)
        mutate(snap)
        snap["hash"] = digest({k: v for k, v in snap.items() if k != "hash"})
        PriceScenario.objects.filter(pk=row.pk).update(output_snapshot_jsonb=snap)

    def run_copy(self, **overrides):
        values = CostingRun.objects.values().get(pk=self.costing_run.pk)
        for name in ("id", "public_id", "run_no", "idempotency_key"):
            values.pop(name)
        values.update(overrides)
        return CostingRun.objects.create(**values, public_id=uuid.uuid4(), run_no=str(uuid.uuid4()))

    def scenario_for_run(self, run, code):
        snapshot = deepcopy(self.rows[0].output_snapshot_jsonb)
        snapshot["inputs"]["uom_id"] = run.quantity_uom_id
        snapshot["costing"].update(id=run.pk, public_id=str(run.public_id))
        snapshot["costing"]["context"]["request"].update(product=run.product_id, sku=run.sku_id)
        snapshot["hash"] = digest({k: v for k, v in snapshot.items() if k != "hash"})
        return self.clone(code=code, base_run=run, output_snapshot_jsonb=snapshot)

    def test_empty_selection_page_200_without_auth(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chưa có kịch bản phù hợp")
        self.assertEqual(response.context["candidates"], [])
        self.assertNotContains(response, "Đăng nhập")

    def test_only_comparison_navigation_active(self):
        response = self.client.get(self.url())
        items = [item for _, group, _ in response.context["sidebar_sections"] for item in group if item["active"]]
        self.assertEqual([i["label"] for i in items], ["So sánh kịch bản"])

    def test_zero_one_six_selected_rejected(self):
        for values in ([], [str(self.rows[0].pk)], [str(i) for i in range(1, 7)]):
            with self.subTest(values=values):
                with self.assertRaisesMessage(ValidationError, "2 đến 5"):
                    load_selection(organization=self.organization, values=values, required=True)
                response = self.client.get(self.url(), {"compare": "1", "scenario": values})
                self.assertContains(response, "2 đến 5")
                self.assertIsNone(response.context["comparison"])

    def test_two_and_five_selected_valid(self):
        for i in range(2):
            self.rows.append(self.clone(code=f"EXTRA{i}"))
        for amount in (2, 5):
            selected = self.selection(self.rows[:amount])
            validate_compatibility(selected)
            response = self.get(scenario=[r.pk for r in self.rows[:amount]])
            self.assertEqual(len(response.context["selected"]), amount)
            self.assertContains(response, "Kết quả so sánh đã lưu")

    def test_duplicate_invalid_and_missing_ids_rejected(self):
        for values in (["1", "01"], ["-1", "2"], ["abc", "2"], ["1e2", "2"], ["9223372036854775808", "2"], ["1" * 50, "2"], ["999999999", str(self.rows[0].pk)]):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                load_selection(organization=self.organization, values=values, required=True)

    def test_other_internal_company_id_cannot_be_selected(self):
        other = Organization.objects.create(code="OTHER", name="Dữ liệu khác", is_active=False)
        row = self.clone(organization=other)
        with self.assertRaisesMessage(ValidationError, "Không tìm thấy"):
            self.selection([self.rows[0], row])

    def test_draft_failed_attempt_and_missing_result_rejected(self):
        for status, snapshot in (("DRAFT", {}), ("DRAFT", {"errors": [{"code": "ERROR"}]}), ("CALCULATED", {})):
            row = self.clone(status=status, output_snapshot_jsonb=snapshot)
            with self.assertRaisesMessage(ValidationError, "kết quả đã lưu hợp lệ"):
                self.selection([self.rows[0], row])
            row.delete()

    def test_corrupted_hash_rejected(self):
        snapshot = deepcopy(self.rows[1].output_snapshot_jsonb)
        snapshot["result"]["profit"] = "0"
        row = self.clone(output_snapshot_jsonb=snapshot)
        with self.assertRaises(ValidationError):
            self.selection([self.rows[0], row])

    def test_nonfinite_float_and_malformed_values_rejected(self):
        for value in ("NaN", "Infinity", "1e99999", "bad", 1.25, None):
            snap = deepcopy(self.rows[1].output_snapshot_jsonb)
            snap["result"]["gross_price"] = value
            if not isinstance(value, float):
                snap["hash"] = digest({k: v for k, v in snap.items() if k != "hash"})
            row = self.clone(output_snapshot_jsonb=snap)
            with self.assertRaises(ValidationError):
                self.selection([self.rows[0], row])
            row.delete()

    def test_different_sku_rejected(self):
        values = Sku.objects.values().get(pk=self.costing_run.sku_id)
        values.pop("id")
        values.update(code="OTHER_SKU", name="SKU khác")
        other = Sku.objects.create(**values)
        run = self.run_copy(sku_id=other.pk)
        scenario = self.scenario_for_run(run, "OTHER_SKU")
        selected = self.selection([self.rows[0], scenario])
        with self.assertRaisesMessage(ValidationError, "cùng một SKU"):
            validate_compatibility(selected)
        response = self.get(scenario=[self.rows[0].pk, scenario.pk])
        self.assertContains(response, "cùng một SKU")
        self.assertIsNone(response.context["comparison"])

    def test_product_level_supported_but_not_mixed_with_sku(self):
        run = self.run_copy(sku_id=None)
        rows = [self.scenario_for_run(run, "PRODUCT_A"), self.scenario_for_run(run, "PRODUCT_B")]
        validate_compatibility(self.selection(rows))
        with self.assertRaises(ValidationError):
            validate_compatibility(self.selection([self.rows[0], rows[1]]))
        self.assertIsNotNone(self.get(scenario=[r.pk for r in rows]).context["comparison"])

    def test_different_output_uom_rejected(self):
        run = self.run_copy(quantity_uom_id=self.demo.records["piece"].pk)
        scenario = self.scenario_for_run(run, "OTHER_UOM")
        selected = self.selection([self.rows[0], scenario])
        with self.assertRaisesMessage(ValidationError, "đơn vị đầu ra"):
            validate_compatibility(selected)

    def test_golden_three_column_matrix_exact_persisted_values(self):
        selected = self.selection()
        result = matrix(selected, self.rows[0].pk)
        metrics = {row["key"]: row for group in result["groups"] for row in group["rows"]}
        from apps.master_data.presentation import format_number, format_percent
        for index, expected in enumerate(EXPECTED):
            for key, value in expected.items():
                self.assertEqual(selected[index].values[key], D(value))
                displayed = format_percent(D(value)) if key.startswith("actual_") else format_number(value) + " VND"
                self.assertEqual(metrics[key]["cells"][index]["value"], displayed)
        response = self.get()
        for value in ("89.972,4137931 VND", "92.526,00506044 VND", "100.000 VND", "26.609,09090909 VND", "20%"):
            self.assertContains(response, value)

    def test_exact_decimal_absolute_relative_and_percentage_point_deltas(self):
        absolute, relative = difference(D("92526.00506044"), D("89972.41379310"))
        self.assertEqual(absolute, D("2553.59126734"))
        self.assertAlmostEqual(relative, D("2.83819357476862"), places=10)
        response = self.get()
        self.assertContains(response, "+2.553,59126734 VND")
        self.assertContains(response, "+510,71825347 VND")
        self.assertContains(response, "+6,60909091 điểm %")

    def test_zero_baseline_safe(self):
        self.assertEqual(difference(D(20), D(0)), (D(20), None))
        self.change_snapshot(self.rows[0], lambda s: s["result"].update(fees="0", actual_markup=None))
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "—")

    def test_explicit_baseline_and_invalid_baseline(self):
        response = self.get(baseline=self.rows[1].pk)
        self.assertEqual(response.context["comparison"]["baseline_id"], self.rows[1].pk)
        self.assertContains(response, "-2.553,59126734 VND")
        response = self.get(baseline="999999")
        self.assertContains(response, "Kịch bản mốc phải thuộc")
        self.assertIsNone(response.context["comparison"])

    def test_different_currency_never_subtracts_money(self):
        Currency.objects.get_or_create(code="USD", defaults={"name": "Đô la Mỹ"})
        self.change_snapshot(self.rows[1], lambda s: s["inputs"].update(currency="USD"))
        response = self.get()
        self.assertContains(response, "92.526,00506044 USD")
        self.assertContains(response, "Không tính chênh lệch tiền")
        rows = {r["key"]: r for group in response.context["comparison"]["groups"] for r in group["rows"]}
        self.assertFalse(rows["profit"]["cells"][1]["comparable"])
        self.assertEqual(rows["profit"]["cells"][1]["delta"], "—")
        self.assertTrue(rows["actual_margin"]["cells"][1]["comparable"])

    def test_persisted_fx_only(self):
        self.change_snapshot(self.rows[1], lambda s: s["trace"].update(fx=[{"from": "USD", "to": "VND", "rate": "25000", "at": "2026-10-08T00:00:00+07:00", "direction": "MULTIPLY"}]))
        response = self.get()
        self.assertContains(response, "1 USD = 25.000 VND")
        self.assertContains(response, "08/10/2026 00:00")

    def test_selector_product_sku_search_channel_currency_date_and_only_calculated(self):
        self.clone(status="DRAFT")
        defaults = {"product": str(self.costing_run.product_id)}
        for values, count in (({}, 3), ({"sku": str(self.costing_run.sku_id)}, 3), ({"q": "Kịch bản B"}, 1), ({"q": "C"}, 3), ({"channel": str(self.channel.pk)}, 3), ({"channel": "9999"}, 0), ({"currency_code": "USD"}, 0), ({"date_from": "2026-11-01"}, 1), ({"date_to": "2026-10-08"}, 2), ({"date_from": "bad"}, 0), ({"sku": "bad"}, 0)):
            with self.subTest(values=values):
                page, _, _ = candidates(organization=self.organization, filters=defaults | values)
                self.assertEqual(page.paginator.count, count)

    def test_selector_requires_product(self):
        self.assertEqual(candidates(organization=self.organization, filters={})[0].paginator.count, 0)

    def test_sort_and_pagination_preserve_repeated_ids(self):
        for index in range(27):
            self.clone(code=f"Z{index:02}")
        response = self.get(product=self.costing_run.product_id, sort="-code", page=2)
        self.assertEqual(len(response.context["candidates"]), 5)
        self.assertEqual(response.context["candidates"][0]["code"], "Z01")
        for row in self.rows:
            self.assertContains(response, f'name="scenario" value="{row.pk}"')
        self.assertContains(response, "scenario=")
        self.assertContains(response, "hx-push-url=\"true\"")

    def test_htmx_partial_and_history_restore_full(self):
        response = self.client.get(self.url(), {"scenario": [r.pk for r in self.rows], "compare": "1"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'id="comparison-results"')
        self.assertNotContains(response, "<!doctype")
        full = self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(full, "<!doctype")

    def test_insufficient_sku_empty_state(self):
        PriceScenario.objects.exclude(pk=self.rows[0].pk).delete()
        response = self.client.get(self.url(), {"product": self.costing_run.product_id, "sku": self.costing_run.sku_id})
        self.assertContains(response, "SKU này chưa có đủ kịch bản để so sánh.")

    def test_vietnamese_labels_and_no_workflow_controls(self):
        response = self.get()
        for label in (">Create<", ">Edit<", ">Search<", ">Status<", ">Actions<", ">Baseline<", "Đăng nhập", "Phê duyệt", "Nhật ký hệ thống"):
            self.assertNotContains(response, label)
        for label in ("Kịch bản mốc", "Chênh lệch", "Doanh thu thuần", "Lợi nhuận", "Đã tính"):
            self.assertContains(response, label)

    def test_comparison_get_is_read_only_no_engine_or_current_sources(self):
        before = list(PriceScenario.objects.values())
        run_before = stored_fingerprint(self.costing_run)
        with patch("apps.pricing.scenario_services.execute", side_effect=AssertionError("Pricing called")), patch("apps.costing.run_services.execute", side_effect=AssertionError("Costing called")), CaptureQueriesContext(connection) as queries:
            response = self.get()
        self.assertEqual(response.status_code, 200)
        sql = " ".join(q["sql"].lower() for q in queries)
        for forbidden in ("channel_fee_rule", "tax_rule", "fx_rate", "organization_member", "costing_run_line", "update ", "insert ", "delete "):
            self.assertNotIn(forbidden, sql)
        self.assertEqual(list(PriceScenario.objects.values()), before)
        self.assertEqual(stored_fingerprint(self.costing_run), run_before)
        self.assertEqual(self.client.post(self.url()).status_code, 405)

    def test_current_master_fee_tax_fx_changes_do_not_change_history(self):
        Currency.objects.get_or_create(code="USD", defaults={"name": "Đô la Mỹ"})
        ChannelFeeRule.objects.create(organization=self.organization, channel=self.channel, fee_type="COMMISSION", fee_base="LIST_PRICE", rate=D("0.05"), effective_from=date(2026, 1, 1))
        TaxRule.objects.create(organization=self.organization, jurisdiction_code="VN", tax_type="VAT", tax_base="SELLING_PRICE", rate=D("0.1"), effective_from=date(2026, 1, 1))
        FxRate.objects.create(organization=self.organization, from_currency_code_id="VND", to_currency_code_id="USD", rate_type="SPOT", rate=D("0.00004"), effective_at=timezone.make_aware(datetime(2026, 1, 1)))
        before = self.get().context["comparison"]
        Channel.objects.filter(pk=self.channel.pk).update(name="Kênh đã đổi tên")
        self.assertEqual(ChannelFeeRule.objects.filter(organization=self.organization).update(rate=D("0.9")), 1)
        self.assertEqual(TaxRule.objects.filter(organization=self.organization).update(rate=D("0.5")), 1)
        self.assertEqual(FxRate.objects.filter(organization=self.organization).update(rate=D("99999")), 1)
        after = self.get()
        self.assertEqual(after.context["comparison"], before)
        self.assertContains(after, "Kênh mẫu")
        self.assertContains(after, "89.972,4137931 VND")

    def test_selection_query_count_constant_two_to_five(self):
        rows = self.rows + [self.clone(code="D"), self.clone(code="E")]
        counts = []
        for amount in (2, 5):
            with CaptureQueriesContext(connection) as queries:
                selected = self.selection(rows[:amount])
                matrix(selected, rows[0].pk)
            counts.append(len(queries))
        self.assertEqual(counts, [1, 1])
