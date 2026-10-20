"""Readable explanations must remain a projection of the saved calculation."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import uuid
from unittest.mock import patch

from django.db import connection
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.models import CostingRun, CostingRunLine, CostElement, Item, SupplierPrice
from apps.master_data.access import Workspace
from apps.master_data.presentation import ui_field_label
from .presentation import source_groups, trace_presentation
from .run_services import create_run
from .run_test_data import golden_data, request_data, seal


class ExplanationFormattingTests(SimpleTestCase):
    def test_nested_values_are_readable_exact_and_html_escaped(self):
        html = render_to_string("costing/runs/partials/trace_value.html", {"value": {
            "arguments": [Decimal("0.08333333"), False, 0, None], "value": "<script>alert(1)</script>"}})
        self.assertIn("Giá trị đầu vào", html)
        self.assertIn("0,08333333", html)
        self.assertIn("Không", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("Decimal(", html)
        self.assertNotIn("False", html)

    def test_glossary_keeps_business_codes_and_established_names(self):
        self.assertEqual(ui_field_label("Nhãn hiển thị"), "Tên hiển thị")
        self.assertEqual(ui_field_label("Độ chính xác ↓"), "Số chữ số thập phân ↓")
        for label in ("Phần tử chi phí", "SKU", "CF_NVL_DUONG", "unit_price", "Hiệu lực từ ngày"):
            self.assertEqual(ui_field_label(label), label)

    def test_unknown_and_legacy_sources_remain_visible_without_mutation(self):
        snapshot = {"sources": {"unknown:1": {"table": "unknown", "id": 1, "fields": {}},
            "recipe_version:7": {"table": "recipe_version", "id": 7, "fields": {"recipe_id": 3, "version_no": 2}}}}
        before = deepcopy(snapshot)
        rows = [row for group in source_groups(snapshot) for row in group["rows"]]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["version"], 2)
        self.assertEqual(snapshot, before)

    def test_mixed_trace_order_values_and_codes_are_not_recomputed(self):
        steps = [{"title": "Công thức TOTAL", "fields": [["Biểu thức", "$A + $B"], ["Kết quả", "12.50000000"]]},
            {"title": "Phép tính", "fields": [["Phép tính", "+"], ["Đầu vào", ["2.5", "10"]], ["Kết quả", "12.5"]]},
            {"title": "Quy tắc", "fields": [["Dòng", "000123"], ["Tỷ lệ hao hụt", "0.02"]]}]
        original = deepcopy(steps)
        line = SimpleNamespace(source_mode="FORMULA", input_snapshot_jsonb={"inputs": {"A": "2.5", "B": "10"}}, value_type="MONEY", amount=Decimal("12.5"), currency_code_id="VND")
        result = trace_presentation(SimpleNamespace(version_snapshot_jsonb={}), line, steps)
        self.assertEqual([section["kind"] for section in result["sections"]], ["facts", "calculations", "facts"])
        self.assertEqual(result["sections"][1]["rows"][0]["value"], "12.5")
        self.assertEqual(result["sections"][2]["fields"][0]["value"], "000123")
        self.assertEqual(result["inputs"][0]["code"], "A")
        self.assertEqual(result["value"], Decimal("12.5"))
        self.assertEqual(steps, original)


class ExplanationHistoryTests(TestCase):
    def setUp(self):
        self.data = golden_data()
        seal(self.data)
        self.run = create_run(workspace=Workspace(self.data.company), data=request_data(self.data), idempotency_key=uuid.uuid4())
        setting = override_settings(DEFAULT_ORGANIZATION_ID=self.data.company.pk)
        setting.enable()
        self.addCleanup(setting.disable)

    def url(self, action, line=None):
        return reverse("costing:run_" + action, args=[self.run.public_id, line.pk] if line else [self.run.public_id])

    def test_formula_trace_has_named_inputs_grouped_math_and_saved_result(self):
        line = CostingRunLine.objects.get(run=self.run, line_code="FULL_COST")
        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            response = self.client.get(self.url("trace", line), **headers)
            self.assertContains(response, "Số liệu đưa vào công thức")
            self.assertContains(response, "Các bước tính và căn cứ chi tiết")
            self.assertContains(response, "60.000")
            self.assertContains(response, "Nguyên vật liệu")
            self.assertContains(response, "MATERIAL_COST")
            self.assertContains(response, "Cộng (+)")
            if headers:
                self.assertContains(response, "max-w-4xl")
                self.assertNotContains(response, "<!DOCTYPE")

    def test_material_trace_is_a_quantity_price_amount_table(self):
        line = CostingRunLine.objects.get(run=self.run, line_code="MATERIAL_COST")
        response = self.client.get(self.url("trace", line))
        for text in ("Vật tư và đơn giá đã dùng", "Số lượng tính tiền", "Đơn giá", "Thành tiền", "40.000", "Nhà cung cấp thử nghiệm"):
            self.assertContains(response, text)
        self.assertNotContains(response, "Số liệu đưa vào công thức")
        self.assertContains(response, "100%")

    def test_presentation_gets_never_read_current_sources_or_mutate_history(self):
        before_run = CostingRun.objects.values().get(pk=self.run.pk)
        before_lines = list(CostingRunLine.objects.filter(run=self.run).order_by("pk").values())
        Item.objects.filter(pk=self.data.items[0].pk).update(name="TÊN HIỆN TẠI KHÁC")
        CostElement.objects.filter(pk=self.data.elements["MATERIAL_COST"].pk).update(name="PHẦN TỬ ĐÃ ĐỔI TÊN")
        SupplierPrice.objects.filter(pk=self.data.prices[0].pk).update(unit_price=999999)
        line = CostingRunLine.objects.get(run=self.run, line_code="FULL_COST")
        with patch("apps.costing.run_services.execute", side_effect=AssertionError("must not recalculate")), CaptureQueriesContext(connection) as queries:
            for action in ("detail", "snapshot", "trace"):
                response = self.client.get(self.url(action, line if action == "trace" else None))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "999.999")
                self.assertNotContains(response, "TÊN HIỆN TẠI KHÁC")
                self.assertNotContains(response, "PHẦN TỬ ĐÃ ĐỔI TÊN")
        for query in queries:
            self.assertTrue(query["sql"].lstrip().upper().startswith("SELECT"), query["sql"])
            for table in ("supplier_price", "item", "cost_element", "recipe", "organization_member"):
                self.assertNotIn('FROM "' + table + '"', query["sql"])
                self.assertNotIn('JOIN "' + table + '"', query["sql"])
        self.assertEqual(CostingRun.objects.values().get(pk=self.run.pk), before_run)
        self.assertEqual(list(CostingRunLine.objects.filter(run=self.run).order_by("pk").values()), before_lines)

    def test_snapshot_sources_have_saved_parent_names_and_units(self):
        response = self.client.get(self.url("snapshot"))
        for text in ("Đơn giá và chi phí phân bổ", "Định mức, bao bì và công đoạn", "Định mức cà phê", "Nhà cung cấp thử nghiệm", "07/10/2026", "Hộp"):
            self.assertContains(response, text)
        self.assertContains(response, "Số thành phẩm theo định mức bao bì")

    def test_new_form_labels_keep_original_input_names_ids_and_rules(self):
        response = self.client.get(reverse("costing:run_create"), {"unused": ""})
        self.assertContains(response, 'for="id_result_currency_code"')
        self.assertContains(response, "Tiền tệ tính giá")
        self.assertEqual(response.context["form"].fields["quantity"].decimal_places, 8)
        self.assertEqual(response.context["form"].fields["quantity"].label, "Sản lượng cần tính")
        response = self.client.get(reverse("costing:run_options"), {"product": self.data.product.pk, "sku": self.data.sku.pk,
            "scheme": self.data.scheme.pk, "costing_date": self.data.day.isoformat()}, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'name="packaging_quantity"')
        self.assertContains(response, 'for="id_packaging_quantity"')
        self.assertContains(response, "Số thành phẩm theo định mức bao bì")
        self.assertContains(response, "1 túi chứa 50 gói")
        self.assertTrue(response.context["form"].fields["packaging_quantity"].required)