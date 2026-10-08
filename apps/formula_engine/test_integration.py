"""Real PostgreSQL CRUD/version/security, input persistence and graph behavior."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from apps.core.models import CostElement, Currency, Formula, FormulaDependency, FormulaTestCase, FormulaVersion, Organization, Uom, UomCategory
from apps.master_data.access import get_workspace
from . import selectors, services
from .engine import build_plan
from .errors import FormulaError
from .forms import FormulaForm, TestForm


def element(**values):
    return CostElement.objects.create(default_source_mode="MANUAL", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING", **values)


class FormulaIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="FORMULA", name="Công ty kiểm thử")
        cls.other = Organization.objects.create(code="OTHER", name="Dữ liệu khác")
        cls.currency = Currency.objects.create(code="VND", name="Đồng Việt Nam")
        cls.a = element(organization=cls.company, code="A", name="Nguyên vật liệu", value_type="MONEY", currency_code=cls.currency, dimension_code="MONEY")
        cls.b = element(organization=cls.company, code="B", name="Bao bì", value_type="MONEY", currency_code=cls.currency, dimension_code="MONEY")
        cls.output = element(organization=cls.company, code="TOTAL", name="Tổng chi phí", value_type="MONEY", currency_code=cls.currency, dimension_code="MONEY")
        cls.old = element(organization=cls.company, code="OLD", name="Biến ngừng dùng", value_type="NUMBER", is_active=False)
        cls.today = timezone.localdate()
        cls.formula = Formula.objects.create(organization=cls.company, code="SUM", name="Tổng chi phí", description="Cộng nguyên liệu và bao bì", output_element=cls.output)
        cls.version = FormulaVersion.objects.create(formula=cls.formula, version_no=1, expression="A+B", effective_from=cls.today)
        cls.foreign = Formula.objects.create(organization=cls.other, code="PRIVATE", name="Không thuộc hệ thống")

    def setUp(self):
        config = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        config.enable(); self.addCleanup(config.disable)
        self.workspace = get_workspace(RequestFactory().get("/"))

    def url(self, action="list", formula=None, version=None):
        arguments = [] if action in ("list", "create", "catalogue") else [getattr(formula or self.formula, "pk", formula)]
        if version: arguments.append(version.pk)
        return reverse("formula_engine:formula_" + action, args=arguments)

    def header(self, **changes):
        values = dict(code=" new_formula ", name=" Công thức mới ", description=" Mô tả ", output_element=str(self.output.pk), is_active="on")
        values.update(changes); return values

    def payload(self, **changes):
        values = {**self.header(), "expression": "A + B", "effective_from": self.today.isoformat(), "effective_to": "", "change_reason": "Thêm công thức", "action": "save"}
        values.update(changes); return values

    def plan(self, expression=None, formula=None, **changes):
        return build_plan(organization=self.company, formula=formula or self.formula, expression=expression or self.version.expression, **changes)

    def case(self, expected="120", **changes):
        values = dict(formula=self.formula, name="Chi phí cơ bản", input_context={"A": "100", "B": "20"}, expected_value_numeric=Decimal(expected))
        values.update(changes); return FormulaTestCase.objects.create(**values)

    def test_list_direct_access_no_membership_or_execution_queries(self):
        with CaptureQueriesContext(connection) as queries: response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200); self.assertNotContains(response, "PRIVATE")
        self.assertContains(response, 'aria-current="page"', count=1); self.assertNotIn("sessionid", response.cookies)
        for query in queries:
            for name in ("organization_member", "costing_run", "supplier_price", "resource_rate"):
                self.assertNotIn(f'"{name}"', query["sql"])

    def test_search_code_name_description(self):
        for keyword in ("sum", "Tổng chi phí", "nguyên liệu"):
            with self.subTest(keyword=keyword): self.assertEqual(list(self.client.get(self.url(), {"q": keyword}).context["records"]), [self.formula])

    def test_filters_status_result_type_active_effective_validation(self):
        for filters in ({"status": "DRAFT"}, {"value_type": "MONEY"}, {"active": "true"}, {"effective": "EFFECTIVE"}, {"validation": "NOT_VALIDATED"}):
            with self.subTest(filters=filters): self.assertEqual(list(self.client.get(self.url(), filters).context["records"]), [self.formula])
        self.assertContains(self.client.get(self.url(), {"active": "false"}), "Không có kết quả phù hợp.")

    def test_sort_pagination_and_state(self):
        Formula.objects.bulk_create([Formula(organization=self.company, code=f"F{i:03}", name=f"Công thức {i}") for i in range(30)])
        response = self.client.get(self.url(), {"sort": "-code", "per_page": "25", "page": "2"})
        self.assertEqual(response.context["page_obj"].paginator.count, 31); self.assertEqual(len(response.context["records"]), 6)
        self.assertEqual(response.context["current_sort"], "-code")
        self.assertEqual(len(self.client.get(self.url(), {"per_page": "50"}).context["records"]), 31)

    def test_create_normalizes_and_stores_canonical_ast_hash_dependencies(self):
        response = self.client.post(self.url("create"), self.payload())
        self.assertEqual(response.status_code, 302)
        formula = Formula.objects.get(code="NEW_FORMULA")
        self.assertEqual(formula.organization_id, self.company.pk); self.assertEqual(formula.name, "Công thức mới")
        version = FormulaVersion.objects.get(formula=formula)
        self.assertEqual(version.status, "DRAFT"); self.assertEqual(version.validation_status, "VALID")
        self.assertEqual(len(version.ast_hash), 64); self.assertEqual(version.ast_jsonb["dsl_version"], 1)
        self.assertIsNone(version.created_by); self.assertIsNone(version.approved_by)
        self.assertEqual(set(FormulaDependency.objects.filter(formula_version=version).values_list("dependency_code", flat=True)), {"A", "B"})

    def test_duplicate_code_and_missing_header(self):
        response = self.client.post(self.url("create"), self.payload(code=" sum "))
        self.assertContains(response, "Mã công thức đã tồn tại.")
        self.assertContains(self.client.post(self.url("create"), self.payload(code="", name="")), "Vui lòng nhập mã công thức.")

    def test_invalid_expression_rolls_back_header_and_rejects_unknown(self):
        for expression in ("A+", "UNKNOWN + 1", 'open("x")', "OLD+1"):
            with self.subTest(expression=expression):
                response = self.client.post(self.url("create"), self.payload(expression=expression))
                self.assertEqual(response.status_code, 200); self.assertFalse(Formula.objects.filter(code="NEW_FORMULA").exists())

    def test_detail_edit_header_and_fixed_identity(self):
        self.assertContains(self.client.get(self.url("detail")), "A+B")
        response = self.client.post(self.url("edit"), self.header(code="CHANGED", name="Tên mới", output_element=str(self.a.pk)))
        self.assertEqual(response.status_code, 302); self.formula.refresh_from_db()
        self.assertEqual(self.formula.code, "SUM"); self.assertEqual(self.formula.output_element_id, self.output.pk); self.assertEqual(self.formula.name, "Tên mới")

    def test_edit_version_and_dependency_normalization(self):
        response = self.client.post(self.url("version_edit", version=self.version), self.payload(expression="A + A + $A"))
        self.assertEqual(response.status_code, 302); self.version.refresh_from_db()
        self.assertEqual(self.version.expression, "A + A + $A")
        self.assertEqual(FormulaDependency.objects.filter(formula_version=self.version).count(), 1)

    def test_new_version_clones_expression_and_reuses_identity_tests(self):
        self.case()
        page = self.client.get(self.url("version_create"))
        self.assertEqual(page.context["version_form"].initial["expression"], "A+B")
        response = self.client.post(self.url("version_create"), self.payload(expression="A+B"))
        self.assertEqual(response.status_code, 302)
        version = FormulaVersion.objects.get(formula=self.formula, version_no=2)
        self.assertEqual(version.status, "DRAFT"); self.version.refresh_from_db(); self.assertEqual(self.version.expression, "A+B")
        self.assertEqual(FormulaTestCase.objects.filter(formula=self.formula).count(), 1)

    def test_invalid_period_equal_or_before(self):
        for end in (self.today, self.today-timedelta(days=1)):
            self.assertContains(self.client.post(self.url("version_edit", version=self.version), self.payload(effective_to=end.isoformat())), "Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực.")

    def test_empty_state_and_htmx_full_restore(self):
        FormulaVersion.objects.filter(formula=self.formula).delete(); self.formula.delete()
        self.assertContains(self.client.get(self.url()), "Chưa có công thức tính.")
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html"); self.assertNotContains(response, "<!doctype")
        self.assertContains(self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"), "<!doctype")

    def test_htmx_validation_keeps_input_no_persistence(self):
        response = self.client.post(self.url("create"), self.payload(expression="A+", action="validate"), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "formula_engine/partials/studio_content.html")
        self.assertContains(response, "A+"); self.assertContains(response, "Lỗi cú pháp")
        self.assertContains(response, 'aria-invalid="true"'); self.assertFalse(Formula.objects.filter(code="NEW_FORMULA").exists())

    def test_htmx_create_and_csrf(self):
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(secure.post(self.url("create"), self.payload()).status_code, 403)
        response = self.client.post(self.url("create"), self.payload(), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200); self.assertIn("HX-Redirect", response)

    def test_scope_and_parent_id_are_checked(self):
        self.assertEqual(self.client.get(self.url("detail", self.foreign)).status_code, 404)
        self.assertEqual(self.client.get(self.url("version_detail", self.foreign, self.version)).status_code, 404)

    def test_structured_inputs_runner_trace_and_htmx(self):
        response = self.client.post(self.url("version_detail", version=self.version), {"action": "test", "input_A": "100", "input_B": "20", "expected": "120"}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="formula-test-panel")
        self.assertTemplateUsed(response, "formula_engine/partials/test_panel.html")
        self.assertEqual(response.context["result"].value, Decimal(120)); self.assertTrue(response.context["passed"])
        self.assertContains(response, "Diễn giải phép tính"); self.assertContains(response, "Đạt")

    def test_missing_sample_and_division_error(self):
        self.assertContains(self.client.post(self.url("version_detail", version=self.version), {"action": "test"}), "Vui lòng nhập dữ liệu mẫu.")
        self.version.expression = "A / 0"; self.version.save()
        response = self.client.post(self.url("version_detail", version=self.version), {"action": "test", "input_A": "100"})
        self.assertContains(response, "Không thể chia cho 0.")

    def test_save_test_and_replay_zero_tolerance(self):
        response = self.client.post(self.url("version_detail", version=self.version), {"action": "save_test", "input_A": "100.1", "input_B": "20.2", "expected": "120.3", "test_name": "Chi phí chuẩn"})
        self.assertContains(response, "Đã lưu bộ kiểm thử công thức.")
        case = FormulaTestCase.objects.get(formula=self.formula)
        self.assertEqual(case.input_context, {"A": "100.1", "B": "20.2"}); self.assertEqual(case.tolerance, 0)
        result = self.client.post(self.url("version_detail", version=self.version), {"action": "run_cases"})
        self.assertTrue(result.context["case_results"][0]["passed"])

    def test_expected_and_name_required_for_persistence(self):
        data = {"action": "save_test", "input_A": "100", "input_B": "20", "test_name": ""}
        self.assertContains(self.client.post(self.url("version_detail", version=self.version), data), "Vui lòng nhập tên bộ kiểm thử.")
        data["test_name"] = "Tên"
        self.assertContains(self.client.post(self.url("version_detail", version=self.version), data), "Vui lòng nhập kết quả mong đợi")
        self.assertFalse(FormulaTestCase.objects.exists())

    def test_existing_tolerance_respected_and_bad_context_fails_cleanly(self):
        case = self.case(expected="120.00000001", tolerance=Decimal("0.00000001"))
        self.assertTrue(services.run_cases(self.plan(), [case])[0]["passed"])
        case.input_context = {"A": 1.5, "B": "20"}
        self.assertFalse(services.run_cases(self.plan(), [case])[0]["passed"])

    def test_reference_plan_and_nested_trace_no_db_during_evaluation(self):
        formula = Formula.objects.create(organization=self.company, code="FULL", name="Chi phí đầy đủ", output_element=self.output)
        plan = self.plan("@SUM * 1.05", formula)
        with CaptureQueriesContext(connection) as queries: result = plan.run({"A": Decimal(100), "B": Decimal(20)})
        self.assertEqual(len(queries), 0); self.assertEqual(result.value, Decimal("126"))
        self.assertEqual({step["formula"] for step in result.trace}, {"SUM", "FULL"})

    def test_symbol_collision_requires_explicit_reference(self):
        element(organization=self.company, code="SUM", name="Mã trùng", value_type="MONEY", currency_code=self.currency, dimension_code="MONEY")
        formula = Formula.objects.create(organization=self.company, code="FULL", name="Chi phí đầy đủ", output_element=self.output)
        with self.assertRaisesMessage(FormulaError, "đồng thời"): self.plan("SUM", formula)
        self.assertEqual(self.plan("@SUM", formula).order, ["SUM", "FULL"])
        self.assertEqual(self.plan("$SUM", formula).order, ["FULL"])

    def test_graph_cycles_self_two_three(self):
        second = Formula.objects.create(organization=self.company, code="SECOND", name="B")
        third = Formula.objects.create(organization=self.company, code="THIRD", name="C")
        v2 = FormulaVersion.objects.create(formula=second, version_no=1, expression="@SUM")
        v3 = FormulaVersion.objects.create(formula=third, version_no=1, expression="@SUM")
        for expression in ("@SUM", "@SECOND", "@THIRD"):
            if expression == "@THIRD": v3.expression="@SECOND"; v3.save()
            with self.subTest(expression=expression), self.assertRaisesMessage(FormulaError, "phụ thuộc vòng"): self.plan(expression)

    def test_publish_requires_date_and_passing_active_tests(self):
        with self.assertRaisesMessage(ValidationError, "ít nhất một bộ kiểm thử"): services.activate_version(workspace=self.workspace, formula=self.formula, version=self.version)
        case = self.case(expected="999")
        with self.assertRaisesMessage(ValidationError, "chưa đạt"): services.activate_version(workspace=self.workspace, formula=self.formula, version=self.version)
        self.version.refresh_from_db(); self.assertEqual(self.version.status, "DRAFT")
        case.expected_value_numeric = Decimal(120); case.save()
        self.version.effective_from = None; self.version.save()
        with self.assertRaisesMessage(ValidationError, "ngày bắt đầu"): services.activate_version(workspace=self.workspace, formula=self.formula, version=self.version)

    def test_publish_success_and_database_immutability(self):
        self.case()
        version = services.activate_version(workspace=self.workspace, formula=self.formula, version=self.version)
        self.assertEqual(version.status, "EFFECTIVE"); self.assertEqual(version.validation_status, "VALID")
        self.assertIsNone(version.approved_by)
        with self.assertRaises(ValidationError): services.save_version(workspace=self.workspace, formula=self.formula, instance=version, data={"expression": "A", "effective_from": self.today})
        with self.assertRaises(DatabaseError), transaction.atomic(): FormulaVersion.objects.filter(pk=version.pk).update(expression="A")
        with self.assertRaises(DatabaseError), transaction.atomic(): FormulaDependency.objects.filter(formula_version=version).delete()

    def test_publish_rechecks_modified_syntax_unknown_reference_and_cycle(self):
        self.case()
        for expression in ("A+", "UNKNOWN", "@SUM"):
            self.version.expression=expression; self.version.save()
            with self.subTest(expression=expression), self.assertRaises(ValidationError): services.activate_version(workspace=self.workspace, formula=self.formula, version=self.version)
            self.version.refresh_from_db(); self.assertEqual(self.version.status, "DRAFT")

    def test_publish_requires_effective_dependency_and_rejects_ambiguity(self):
        outer = Formula.objects.create(organization=self.company, code="OUTER", name="Ngoài", output_element=self.output)
        version = FormulaVersion.objects.create(formula=outer, version_no=1, expression="@SUM", effective_from=self.today)
        self.case(formula=outer)
        with self.assertRaisesMessage(ValidationError, "đang hiệu lực"): services.activate_version(workspace=self.workspace, formula=outer, version=version)
        self.case(); services.activate_version(workspace=self.workspace, formula=self.formula, version=self.version)
        FormulaVersion.objects.create(formula=self.formula, version_no=2, expression="A+B", status="EFFECTIVE", effective_from=self.today)
        with self.assertRaisesMessage(ValidationError, "mơ hồ"): services.activate_version(workspace=self.workspace, formula=outer, version=version)

    def test_inactive_and_other_scope_references_rejected(self):
        with self.assertRaises(FormulaError): self.plan("OLD")
        element(organization=self.other, code="PRIVATE_ELEMENT", name="Ngoài", value_type="NUMBER")
        with self.assertRaises(FormulaError): self.plan("PRIVATE_ELEMENT")
        self.formula.is_active=False; self.formula.save()
        outer = Formula.objects.create(organization=self.company, code="OUTER", name="Ngoài")
        with self.assertRaises(FormulaError): self.plan("@SUM", outer)

    def test_catalogue_active_bounded_search_and_vietnamese_labels(self):
        response = self.client.get(self.url("catalogue"), {"q": "bao bì"})
        self.assertContains(response, "$B"); self.assertNotContains(response, "OLD"); self.assertNotContains(response, "PRIVATE")
        self.assertContains(self.client.get(self.url("create")), "Thiết lập công thức")
        for word in (">Create<", ">Edit<", ">Save<", ">Status<", ">Actions<"):
            self.assertNotContains(self.client.get(self.url()), word)

    def test_list_queries_do_not_scale_with_row_count(self):
        def count():
            with CaptureQueriesContext(connection) as captured: self.client.get(self.url())
            return len(captured)
        initial = count()
        Formula.objects.bulk_create([Formula(organization=self.company, code=f"QUERY_{i}", name="Công thức", output_element=self.output) for i in range(20)])
        self.assertEqual(count(), initial)

    def test_plan_batches_shared_references(self):
        expression = " + ".join(["A"] * 20)
        with CaptureQueriesContext(connection) as captured: self.plan(expression)
        self.assertLessEqual(len(captured), 3)

    def test_saved_ast_is_not_executed_or_trusted(self):
        self.version.ast_jsonb={"kind": "python", "value": "malicious"}; self.version.save()
        self.assertEqual(self.plan().run({"A": Decimal(100), "B": Decimal(20)}).value, Decimal(120))

    def test_version_history_and_immutable_ui_path(self):
        self.case(); services.activate_version(workspace=self.workspace, formula=self.formula, version=self.version)
        self.assertContains(self.client.get(self.url("version_edit", version=self.version)), "Không thể chỉnh sửa phiên bản")
        self.assertContains(self.client.get(self.url("version_list")), "Phiên bản 1")
        response=self.client.get(self.url("version_list"), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")

    def test_boolean_and_text_structured_inputs_and_expected_persistence(self):
        for code, kind, expression, sample, expected in (("FLAG", "BOOLEAN", "NOT FLAG", "FALSE", "TRUE"), ("LABEL", "TEXT", "LABEL", "Tên tiếng Việt", "Tên tiếng Việt")):
            with self.subTest(kind=kind):
                element(organization=self.company, code=code, name="Dữ liệu mẫu", value_type=kind)
                formula = Formula.objects.create(organization=self.company, code=f"TEST_{code}", name="Kiểm thử")
                version = FormulaVersion.objects.create(formula=formula, version_no=1, expression=expression)
                response = self.client.post(self.url("version_detail", formula, version), {"action": "save_test", f"input_{code}": sample, "expected": expected, "test_name": "Kiểm thử mẫu"})
                self.assertEqual(response.status_code, 200)
                case = FormulaTestCase.objects.get(formula=formula)
                self.assertEqual(case.expected_value_text, expected)
                self.assertTrue(services.run_cases(self.plan(expression, formula), [case])[0]["passed"])

    def test_saved_test_can_be_deactivated_and_missing_case_is_safe(self):
        case = self.case()
        url = reverse("formula_engine:formula_test_deactivate", args=[self.formula.pk, case.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        case.refresh_from_db(); self.assertFalse(case.is_active)
        self.assertContains(self.client.post(url), "Không tìm thấy bộ kiểm thử đang hoạt động.")

    def test_activation_http_and_clone_from_effective_preserves_history(self):
        self.case()
        url = self.url("version_activate", version=self.version)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        clone = services.save_version(workspace=self.workspace, formula=self.formula, source=self.version, data={"expression": "A+B", "effective_from": self.today+timedelta(days=1)})
        self.assertEqual(clone.status, "DRAFT"); self.version.refresh_from_db(); self.assertEqual(self.version.status, "EFFECTIVE")

    def test_text_result_and_expression_are_html_escaped(self):
        formula = Formula.objects.create(organization=self.company, code="TEXT_OUTPUT", name="Văn bản")
        version = FormulaVersion.objects.create(formula=formula, version_no=1, expression='"<script>alert(1)</script>"')
        response = self.client.post(self.url("version_detail", formula, version), {"action": "test"})
        self.assertContains(response, "&lt;script&gt;"); self.assertNotContains(response, "<script>alert(1)</script>")

    def test_replay_does_not_require_manual_sample_fields(self):
        self.case()
        response = self.client.post(self.url("version_detail", version=self.version), {"action": "run_cases"})
        self.assertTrue(response.context["case_results"][0]["passed"])
        self.assertNotContains(response, "Vui lòng nhập dữ liệu mẫu.")

    def test_legacy_case_resolves_and_ambiguous_case_is_rejected(self):
        legacy = element(organization=self.company, code="legacy", name="Mã cũ", value_type="NUMBER")
        formula = Formula.objects.create(organization=self.company, code="legacy_formula", name="Công thức cũ")
        plan = self.plan("LEGACY", formula)
        self.assertEqual(plan.run({"LEGACY": Decimal(3)}).value, Decimal(3))
        services.save_formula(workspace=self.workspace, instance=formula, data={"code": formula.code, "name": "Tên mới", "description": None, "output_element": None, "is_active": True})
        formula.refresh_from_db(); self.assertEqual(formula.code, "legacy_formula")
        element(organization=self.company, code="LEGACY", name="Mã trùng", value_type="NUMBER")
        with self.assertRaisesMessage(FormulaError, "mơ hồ"): self.plan("LEGACY", formula)

    def test_nested_error_identifies_correct_formula_and_source_location(self):
        outer = Formula.objects.create(organization=self.company, code="OUTER", name="Bên ngoài")
        self.version.expression = "1 +\n ?"; self.version.save()
        with self.assertRaises(FormulaError) as error: self.plan("@SUM", outer)
        self.assertIn('Công thức "SUM" · Phiên bản 1', str(error.exception))
        self.assertIn("Dòng 2, cột 2", str(error.exception))
