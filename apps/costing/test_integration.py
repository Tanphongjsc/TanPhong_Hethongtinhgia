"""Scheme configuration/lifecycle on real isolated PostgreSQL, no runtime costing."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.db import connection, transaction, DatabaseError
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from apps.core.models import CostElement, CostingScheme, CostingSchemeVersion, CostingSchemeLine, Currency, Formula, FormulaVersion, Organization, RuleTable, Uom, UomCategory
from apps.master_data.access import Workspace
from . import services
from .configuration import validate_costing_scheme
from .forms import SchemeLineForm


class SchemeIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="SCHEME", name="Công ty kiểm thử")
        cls.other = Organization.objects.create(code="OTHER", name="Dữ liệu khác")
        cls.today = timezone.localdate()
        cls.currency = Currency.objects.create(code="VND", name="Đồng Việt Nam")
        def element(code, **extra):
            return CostElement.objects.create(organization=cls.company, code=code, name=code, value_type="MONEY", currency_code=cls.currency,
                dimension_code="MONEY", default_source_mode="MANUAL", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING", **extra)
        cls.a, cls.b, cls.output = element("MATERIAL_COST"), element("PACKAGING_COST"), element("FULL_COST")
        cls.old = element("OLD", is_active=False)
        cls.formula = Formula.objects.create(organization=cls.company, code="TOTAL", name="Tổng chi phí", output_element=cls.output)
        cls.formula_version = FormulaVersion.objects.create(formula=cls.formula, version_no=1, expression="$MATERIAL_COST + $PACKAGING_COST", status="EFFECTIVE", validation_status="VALID", effective_from=cls.today-timedelta(days=10))
        cls.draft_formula = FormulaVersion.objects.create(formula=cls.formula, version_no=2, expression="1")
        cls.scheme = CostingScheme.objects.create(organization=cls.company, code="STANDARD", name="Giá thành chuẩn", purpose="STANDARD_COST", context_scope="GENERAL", description="Nguyên liệu và bao bì")
        cls.version = CostingSchemeVersion.objects.create(scheme=cls.scheme, version_no=1, effective_from=cls.today)
        cls.foreign = CostingScheme.objects.create(organization=cls.other, code="PRIVATE", name="Khác", purpose="OTHER")
        cls.rule = RuleTable.objects.create(organization=cls.company, code="RULE", name="Bảng quy tắc", purpose="COST", result_value_type="MONEY")

    def setUp(self):
        config = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        config.enable(); self.addCleanup(config.disable)
        self.workspace = Workspace(self.company)

    def url(self, action="list", *, scheme=None, version=None, line=None):
        args = [] if action in ("list", "create") else [getattr(scheme or self.scheme, "pk", scheme)]
        if action.startswith("version_") and action not in ("version_list", "version_create"): args.append((version or self.version).pk)
        if action.startswith("line_"): args.append((version or self.version).pk)
        if line: args.append(line.pk)
        return reverse("costing:scheme_"+action, args=args)

    def header(self, **changes):
        data = dict(code=" new_scheme ", name=" Phương án mới ", purpose="STANDARD_COST", context_scope="GENERAL", description=" Mô tả ", is_active="on",
            **{"initial-effective_from": self.today.isoformat(), "initial-effective_to": "", "initial-change_reason": "Ban đầu"})
        data.update(changes); return data

    def payload(self, **changes):
        data = dict(line_code=" material ", label=" Nguyên vật liệu ", line_type="INPUT", source_mode="MANUAL", cost_element=str(self.a.pk), display_order="10",
            cost_scope="MANUFACTURING", visibility_scope="INTERNAL", rounding_scale="", min_override_value="", max_override_value="", override_requires_reason="on")
        data.update(changes); return data

    def line(self, **changes):
        data = dict(scheme_version=self.version, line_code="A", label="Nguyên liệu", line_type="INPUT", source_mode="MANUAL", cost_element=self.a, display_order=10, cost_scope="MANUFACTURING")
        data.update(changes); return CostingSchemeLine.objects.create(**data)

    def complete(self):
        self.line()
        self.line(line_code="B", cost_element=self.b, display_order=20)
        return self.line(line_code="TOTAL", line_type="OUTPUT", source_mode="FORMULA", cost_element=self.output, formula_version=self.formula_version, display_order=1)

    def report(self):
        return validate_costing_scheme(organization=self.company, scheme=self.scheme, version=self.version)

    def service_values(self, line=None, **changes):
        from .constants import LINE_FIELDS
        line = line or self.line()
        data = {name: getattr(line, name) for name in LINE_FIELDS}
        data.update(changes); return data

    def test_direct_list_without_membership_or_runtime_queries(self):
        with CaptureQueriesContext(connection) as queries: response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "STANDARD"); self.assertNotContains(response, "PRIVATE")
        self.assertContains(response, 'aria-current="page"', count=1); self.assertNotIn("sessionid", response.cookies)
        self.forbid_runtime(queries)

    def forbid_runtime(self, queries):
        for query in queries:
            for table in ("organization_member", "supplier_price", "resource_rate", "costing_run", "costing_run_line", "cost_pool_period"):
                self.assertNotIn('"'+table+'"', query["sql"])

    def test_search_code_name_description_purpose(self):
        for q in ("standard", "Giá thành", "bao bì", "STANDARD_COST"):
            self.assertEqual(list(self.client.get(self.url(), {"q": q}).context["records"]), [self.scheme])

    def test_filters_status_effective_purpose_scope_active(self):
        for query in ({"status": "DRAFT"}, {"effective": "EFFECTIVE"}, {"purpose": "STANDARD_COST"}, {"context_scope": "GENERAL"}, {"active": "true"}):
            self.assertEqual(list(self.client.get(self.url(), query).context["records"]), [self.scheme])
        self.assertContains(self.client.get(self.url(), {"active": "false"}), "Không có kết quả phù hợp.")

    def test_sort_pagination_and_query_state(self):
        CostingScheme.objects.bulk_create([CostingScheme(organization=self.company, code=f"S{i:03}", name=f"Phương án {i}", purpose="STANDARD") for i in range(30)])
        response = self.client.get(self.url(), {"sort": "-code", "per_page": "25", "page": "2"})
        self.assertEqual(response.context["page_obj"].paginator.count, 31); self.assertEqual(len(response.context["records"]), 6)
        self.assertEqual(response.context["current_sort"], "-code")
        self.assertContains(response, "sort=-code")
        self.assertEqual(len(self.client.get(self.url(), {"per_page": 50}).context["records"]), 31)
        self.assertEqual(self.client.get(self.url(), {"sort": "--code", "per_page": 999}).context["per_page"], 25)

    def test_create_initial_version_and_internal_scope_normalized(self):
        response = self.client.post(self.url("create"), self.header())
        self.assertEqual(response.status_code, 302)
        scheme = CostingScheme.objects.get(code="NEW_SCHEME")
        self.assertEqual(scheme.organization_id, self.company.pk); self.assertEqual(scheme.name, "Phương án mới")
        version = CostingSchemeVersion.objects.get(scheme=scheme)
        self.assertEqual(version.version_no, 1); self.assertEqual(version.status, "DRAFT"); self.assertIsNone(version.created_by)

    def test_duplicate_code_rejected(self):
        self.assertContains(self.client.post(self.url("create"), self.header(code=" standard ")), "Mã phương án đã tồn tại.")

    def test_invalid_header_and_dates_roll_back_all_records(self):
        for data in (self.header(code=""), self.header(**{"initial-effective_to": self.today.isoformat()})):
            response = self.client.post(self.url("create"), data)
            self.assertEqual(response.status_code, 200); self.assertTrue(response.context["form"].errors or response.context["version_form"].errors)
        self.assertFalse(CostingScheme.objects.filter(code="NEW_SCHEME").exists())

    def test_detail_header_edit_and_deactivate(self):
        self.assertContains(self.client.get(self.url("detail")), "Phiên bản 1")
        self.assertEqual(self.client.post(self.url("edit"), self.header(code="STANDARD", name=" Đã sửa ", is_active="")).status_code, 302)
        self.scheme.refresh_from_db(); self.assertEqual(self.scheme.name, "Đã sửa"); self.assertFalse(self.scheme.is_active)

    def test_empty_state_and_htmx_list_history_restore(self):
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html"); self.assertNotContains(response, "<!DOCTYPE")
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/reference_data_list.html")
        CostingSchemeVersion.objects.filter(scheme=self.scheme).delete(); self.scheme.delete()
        self.assertContains(self.client.get(self.url()), "Chưa có phương án tính giá thành.")

    def test_scope_and_nested_id_404(self):
        for url in (self.url("detail", scheme=self.foreign), self.url("detail", scheme=10**30), self.url("version_detail", scheme=self.foreign), self.url("version_create")+"?source=invalid"):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_add_manual_line_decimal_override_and_normalization(self):
        response = self.client.post(self.url("line_create"), self.payload(min_override_value="0.08333333", max_override_value="1.12345678"))
        self.assertEqual(response.status_code, 302)
        line = CostingSchemeLine.objects.get(scheme_version=self.version)
        self.assertEqual(line.line_code, "MATERIAL"); self.assertEqual(line.label, "Nguyên vật liệu")
        self.assertEqual(line.min_override_value, Decimal("0.08333333")); self.assertEqual(line.condition_jsonb, {})

    def test_line_missing_source_rounding_range_and_duplicate_errors(self):
        self.line(line_code="MATERIAL")
        for data, message in ((self.payload(), "Mã dòng đã tồn tại"), (self.payload(line_code="B"), "Thứ tự đã tồn tại"),
            (self.payload(line_code="B", display_order=20, rounding_scale=13), "12"),
            (self.payload(line_code="B", display_order=20, min_override_value=2, max_override_value=1), "tối đa"),
            (self.payload(line_code="B", display_order=20, source_mode="FORMULA"), "nguồn dữ liệu")):
            self.assertContains(self.client.post(self.url("line_create"), data), message)

    def test_formula_line_assignment_and_correct_output(self):
        response = self.client.post(self.url("line_create"), self.payload(source_mode="FORMULA", cost_element=self.output.pk, formula_version=self.formula_version.pk))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CostingSchemeLine.objects.get(scheme_version=self.version).formula_version_id, self.formula_version.pk)

    def test_formula_wrong_output_and_draft_rejected(self):
        for data in (self.payload(source_mode="FORMULA", formula_version=self.formula_version.pk), self.payload(source_mode="FORMULA", formula_version=self.draft_formula.pk, cost_element=self.output.pk)):
            self.assertTrue(self.client.post(self.url("line_create"), data).context["form"].errors)
        self.assertFalse(CostingSchemeLine.objects.filter(scheme_version=self.version).exists())

    def test_formula_wrong_type_when_no_declared_output(self):
        formula = Formula.objects.create(organization=self.company, code="TEXT", name="Văn bản")
        version = FormulaVersion.objects.create(formula=formula, version_no=1, expression='"abc"', status="EFFECTIVE", validation_status="VALID", effective_from=self.today)
        self.assertContains(self.client.post(self.url("line_create"), self.payload(source_mode="FORMULA", formula_version=version.pk)), "Kiểu hoặc đơn vị")

    def test_inactive_and_foreign_references_not_selectable(self):
        form = SchemeLineForm(workspace=self.workspace, version=self.version)
        self.assertNotIn(self.old, form.fields["cost_element"].queryset)
        foreign_element = CostElement.objects.create(organization=self.other, code="OTHER", name="Khác", value_type="NUMBER", default_source_mode="MANUAL", cost_scope="MANUFACTURING", accounting_scope="INVENTORY_COST")
        for target in (self.old, foreign_element):
            self.assertTrue(self.client.post(self.url("line_create"), self.payload(cost_element=target.pk)).context["form"].errors)

    def test_dependent_formula_dropdown_filters_output(self):
        response = self.client.get(self.url("line_sources"), {"source_mode": "FORMULA", "cost_element": self.a.pk}, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'id="scheme-source-fields"'); self.assertNotContains(response, "Tổng chi phí")
        self.assertContains(self.client.get(self.url("line_sources"), {"source_mode": "FORMULA", "cost_element": self.output.pk}, HTTP_HX_REQUEST="true"), "Phiên bản 1")

    def test_line_edit_remove_confirmation_and_condition_preserved(self):
        line = self.line(line_code="MATERIAL", condition_jsonb={"legacy": ["KEEP"]})
        self.assertEqual(self.client.get(self.url("line_remove", line=line)).status_code, 200)
        self.assertTrue(CostingSchemeLine.objects.filter(pk=line.pk).exists())
        self.assertEqual(self.client.post(self.url("line_edit", line=line), self.payload(label="Đã sửa")).status_code, 302)
        line.refresh_from_db(); self.assertEqual(line.condition_jsonb, {"legacy": ["KEEP"]})
        self.assertEqual(self.client.post(self.url("line_remove", line=line)).status_code, 302)
        self.assertFalse(CostingSchemeLine.objects.filter(pk=line.pk).exists())

    def test_line_htmx_save_invalid_remove_and_no_reload(self):
        response = self.client.post(self.url("line_create"), self.payload(), HTTP_HX_REQUEST="true")
        self.assertEqual(response["HX-Retarget"], "#scheme-lines-table"); self.assertContains(response, "hx-swap-oob")
        self.assertContains(response, "Đã thêm thành phần tính giá.")
        line = CostingSchemeLine.objects.get(scheme_version=self.version)
        response = self.client.post(self.url("line_edit", line=line), self.payload(label=""), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "costing/partials/line_editor.html"); self.assertContains(response, 'aria-invalid="true"')
        self.assertNotContains(response, "<!DOCTYPE")
        self.assertContains(self.client.post(self.url("line_remove", line=line), HTTP_HX_REQUEST="true"), "Đã xóa thành phần tính giá.")

    def test_lines_paginated_ordered_and_empty(self):
        self.assertContains(self.client.get(self.url("detail")), "Phương án chưa có thành phần tính giá.")
        CostingSchemeLine.objects.bulk_create([CostingSchemeLine(scheme_version=self.version, line_code=f"L{i}", label="Dòng", line_type="INFO", source_mode="MANUAL", cost_scope="MANUFACTURING", display_order=i) for i in range(30)])
        response = self.client.get(self.url("version_detail"), {"page": 2, "per_page": 25}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="scheme-lines-table")
        self.assertEqual(len(response.context["lines"]), 5); self.assertEqual(response.context["lines"][0].display_order, 25)
        self.assertTemplateUsed(response, "costing/partials/lines_table.html")

    def test_configuration_valid_dependencies_without_evaluation(self):
        self.complete()
        with patch("apps.formula_engine.engine.Plan.run", side_effect=AssertionError("No costing execution")), CaptureQueriesContext(connection) as queries:
            report = self.report()
        self.assertEqual(report.errors, []); self.assertEqual(report.order, ["A", "B", "TOTAL"])
        self.assertEqual({row["element"] for row in report.dependencies}, {"MATERIAL_COST", "PACKAGING_COST"})
        self.forbid_runtime(queries)

    def test_dependency_missing_and_ambiguous(self):
        self.line(line_code="TOTAL", source_mode="FORMULA", formula_version=self.formula_version, cost_element=self.output)
        self.assertIn("Phương án chưa cung cấp dữ liệu cho phần tử chi phí PACKAGING_COST.", self.report().errors)
        self.line(line_code="X", display_order=20)
        self.line(line_code="Y", display_order=30)
        self.assertTrue(any("nhiều nguồn" in error for error in self.report().errors))

    def test_scheme_cross_line_cycle(self):
        fa = Formula.objects.create(organization=self.company, code="FA", name="A", output_element=self.a)
        fb = Formula.objects.create(organization=self.company, code="FB", name="B", output_element=self.b)
        va = FormulaVersion.objects.create(formula=fa, version_no=1, expression="$PACKAGING_COST", status="EFFECTIVE", validation_status="VALID", effective_from=self.today)
        vb = FormulaVersion.objects.create(formula=fb, version_no=1, expression="$MATERIAL_COST", status="EFFECTIVE", validation_status="VALID", effective_from=self.today)
        self.line(source_mode="FORMULA", formula_version=va)
        self.line(line_code="B", display_order=20, cost_element=self.b, source_mode="FORMULA", formula_version=vb)
        self.assertTrue(any("phụ thuộc vòng" in message for message in self.report().errors))

    def test_formula_parser_cycle_and_missing_version_reused(self):
        formula = Formula.objects.create(organization=self.company, code="CYCLE", name="Vòng")
        version = FormulaVersion.objects.create(formula=formula, version_no=1, expression="@CYCLE", status="EFFECTIVE", validation_status="VALID", effective_from=self.today)
        self.line(source_mode="FORMULA", formula_version=version)
        self.assertTrue(any("phụ thuộc vòng" in error for error in self.report().errors))

    def test_invalid_formula_legacy_status_diagnosed(self):
        self.line(source_mode="FORMULA", formula_version=self.draft_formula)
        self.assertTrue(any("chưa được kích hoạt" in error for error in self.report().errors))

    def test_unsupported_sources_and_condition_block_activation(self):
        for mode, reference in (("SYSTEM", {"system_resolver_code": "RECIPE_COST"}), ("LOOKUP", {"rule_table": self.rule}), ("EXTERNAL", {"external_adapter_code": "ERP"})):
            line = self.line(source_mode=mode, **reference)
            self.assertTrue(any("chưa có bộ kiểm tra" in error for error in self.report().errors))
            line.delete()
        self.line(condition_jsonb={"old": True})
        self.assertTrue(any("Điều kiện nâng cao" in error for error in self.report().errors))

    def test_inactive_currency_unit_and_source_diagnosed(self):
        self.complete(); self.currency.is_active = False; self.currency.save()
        self.assertTrue(any("Tiền tệ hoặc đơn vị tính" in error for error in self.report().errors))
        self.a.is_active = False; self.a.save()
        self.assertTrue(any("ngừng hoạt động" in error for error in self.report().errors))

    def test_formula_period_must_cover_scheme_end(self):
        formula = Formula.objects.create(organization=self.company, code="FINITE", name="Có kỳ", output_element=self.output)
        version = FormulaVersion.objects.create(formula=formula, version_no=1, expression="$MATERIAL_COST", status="EFFECTIVE", validation_status="VALID", effective_from=self.today, effective_to=self.today+timedelta(days=5))
        self.line(line_code="TOTAL", source_mode="FORMULA", formula_version=version, cost_element=self.output)
        self.assertTrue(any("kết thúc trước" in error for error in self.report().errors))

    def test_validate_endpoint_full_partial_and_trace(self):
        self.complete()
        response = self.client.get(self.url("version_validate"), HTTP_HX_REQUEST="true")
        self.assertContains(response, "Phụ thuộc dữ liệu"); self.assertContains(response, "Đã cung cấp")
        self.assertNotContains(response, "<!DOCTYPE"); self.assertTemplateUsed(response, "costing/partials/validation.html")
        self.assertTemplateUsed(self.client.get(self.url("version_validate")), "costing/validation.html")

    def test_clone_all_fields_json_references_and_old_unchanged(self):
        old = self.complete()
        CostingSchemeLine.objects.filter(pk=old.pk).update(condition_jsonb={"legacy": [1, "KEEP"]}, editable=True, min_override_value=Decimal("0.12345678"), notes="Ghi chú")
        fields = ("line_code", "cost_element_id", "formula_version_id", "condition_jsonb", "editable", "min_override_value", "notes", "display_order")
        before = list(CostingSchemeLine.objects.filter(scheme_version=self.version).order_by("display_order").values(*fields))
        response = self.client.post(self.url("version_create")+f"?source={self.version.pk}", {"effective_from": self.today.isoformat(), "effective_to": "", "change_reason": "Bản sao"})
        self.assertEqual(response.status_code, 302)
        cloned = CostingSchemeVersion.objects.get(scheme=self.scheme, version_no=2)
        self.assertEqual(cloned.status, "DRAFT"); self.assertIsNone(cloned.content_hash)
        self.assertEqual(list(CostingSchemeLine.objects.filter(scheme_version=cloned).order_by("display_order").values(*fields)), before)
        self.assertEqual(list(CostingSchemeLine.objects.filter(scheme_version=self.version).order_by("display_order").values(*fields)), before)

    def test_clone_form_prefills_source_dates_and_reason(self):
        self.version.effective_to = self.today + timedelta(days=30)
        self.version.change_reason = "Phiên bản gốc"
        self.version.save()
        response = self.client.get(self.url("version_create")+f"?source={self.version.pk}")
        form = response.context["form"]
        self.assertEqual(form.initial["effective_from"], self.today)
        self.assertEqual(form.initial["effective_to"], self.version.effective_to)
        self.assertEqual(form.initial["change_reason"], "Phiên bản gốc")

    def test_formula_dropdown_excludes_expired_and_future_at_check_date(self):
        formula = Formula.objects.create(organization=self.company, code="DATED", name="Theo kỳ")
        for number, start, end in ((1, self.today-timedelta(days=10), self.today-timedelta(days=1)), (2, self.today+timedelta(days=1), None)):
            FormulaVersion.objects.create(formula=formula, version_no=number, expression="1", status="EFFECTIVE", validation_status="VALID", effective_from=start, effective_to=end)
        form = SchemeLineForm(workspace=self.workspace, version=self.version)
        self.assertFalse(form.fields["formula_version"].queryset.filter(formula=formula).exists())

    def test_version_edit_history_and_invalid_period(self):
        self.assertContains(self.client.get(self.url("version_list")), "Phiên bản")
        payload = {"effective_from": self.today.isoformat(), "effective_to": self.today.isoformat(), "change_reason": "Đổi"}
        self.assertContains(self.client.post(self.url("version_edit"), payload), "phải sau")
        payload["effective_to"] = (self.today+timedelta(days=30)).isoformat()
        self.assertEqual(self.client.post(self.url("version_edit"), payload).status_code, 302)

    def test_activate_configuration_then_immutable_backend_and_database(self):
        total = self.complete()
        response = self.client.post(self.url("version_activate"))
        self.assertEqual(response.status_code, 302); self.version.refresh_from_db()
        self.assertEqual(self.version.status, "EFFECTIVE"); self.assertEqual(len(self.version.content_hash), 64); self.assertIsNone(self.version.approved_by)
        self.assertContains(self.client.get(self.url("detail")), "Đã chốt")
        with self.assertRaises(ValidationError): services.remove_line(workspace=self.workspace, scheme=self.scheme, version=self.version, instance=total)
        with self.assertRaises(DatabaseError), transaction.atomic(): CostingSchemeLine.objects.filter(pk=total.pk).update(label="Không được")
        with self.assertRaises(DatabaseError), transaction.atomic(): CostingSchemeVersion.objects.filter(pk=self.version.pk).update(change_reason="Không được")
        self.assertContains(self.client.post(self.url("line_create"), self.payload()), "đã được chốt")

    def test_failed_activation_is_atomic_no_date_or_missing_inputs(self):
        response = self.client.post(self.url("version_activate"))
        self.assertContains(response, "Không thể kích hoạt")
        self.version.refresh_from_db(); self.assertEqual(self.version.status, "DRAFT"); self.assertIsNone(self.version.content_hash)
        self.complete(); self.version.effective_from = None; self.version.save()
        self.assertContains(self.client.post(self.url("version_activate")), "ngày bắt đầu")

    def test_locked_header_identity_stable_and_clone_from_effective(self):
        self.complete(); services.activate_version(workspace=self.workspace, scheme=self.scheme, version=self.version)
        form_response = self.client.get(self.url("edit"))
        self.assertTrue(form_response.context["form"].fields["context_scope"].disabled)
        self.assertEqual(self.client.post(self.url("edit"), self.header(code="FORGED", purpose="CHANGED", context_scope="CHANGED")).status_code, 302)
        self.scheme.refresh_from_db(); self.assertEqual(self.scheme.code, "STANDARD"); self.assertEqual(self.scheme.purpose, "STANDARD_COST")
        cloned = services.save_version(workspace=self.workspace, scheme=self.scheme, data={"effective_from": self.today, "effective_to": None, "change_reason": "Clone"}, source=self.version)
        self.assertEqual(cloned.status, "DRAFT"); self.assertEqual(cloned.costingschemeline_set.count(), 3)

    def test_csrf_required_and_no_get_activation(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(self.url("create"), self.header()).status_code, 403)
        self.assertEqual(self.client.get(self.url("version_activate")).status_code, 405)

    def test_service_revalidates_stale_reference(self):
        line = self.line()
        values = self.service_values(line, line_code="NEW", display_order=20)
        other_element = CostElement.objects.create(organization=self.company, code="TEMP", name="Tạm", value_type="NUMBER", default_source_mode="MANUAL", cost_scope="MANUFACTURING", accounting_scope="INVENTORY_COST")
        values["cost_element"] = other_element
        CostElement.objects.filter(pk=other_element.pk).update(is_active=False)
        with self.assertRaises(ValidationError): services.save_line(workspace=self.workspace, scheme=self.scheme, version=self.version, data=values)

    def test_query_counts_detail(self):
        self.complete()
        with CaptureQueriesContext(connection) as before: self.client.get(self.url("version_detail"))
        CostingSchemeLine.objects.bulk_create([CostingSchemeLine(scheme_version=self.version, line_code=f"L{i}", label="Dòng", line_type="INFO", source_mode="MANUAL", cost_scope="MANUFACTURING", display_order=100+i) for i in range(20)])
        with CaptureQueriesContext(connection) as after: self.client.get(self.url("version_detail"))
        self.assertEqual(len(before), len(after)); self.forbid_runtime(after)

    def test_query_counts_list_independent_of_records(self):
        with CaptureQueriesContext(connection) as before: self.client.get(self.url())
        schemes = CostingScheme.objects.bulk_create([CostingScheme(organization=self.company, code=f"N{i}", name="Phương án", purpose="COST") for i in range(15)])
        CostingSchemeVersion.objects.bulk_create([CostingSchemeVersion(scheme=scheme, version_no=1) for scheme in schemes])
        with CaptureQueriesContext(connection) as after: self.client.get(self.url())
        self.assertEqual(len(before), len(after))

    def test_identical_formula_plan_cached_for_repeated_lines(self):
        from .configuration import analyze_formula
        self.complete()
        self.line(line_code="TOTAL_AGAIN", source_mode="FORMULA", cost_element=self.output, formula_version=self.formula_version, display_order=30)
        with patch("apps.costing.configuration.analyze_formula", wraps=analyze_formula) as analyzer:
            self.assertEqual(self.report().errors, [])
        self.assertEqual(analyzer.call_count, 1)

    def test_integrity_error_maps_duplicate_code_and_order(self):
        line = self.line()
        for values, message in ((self.service_values(line), "Mã dòng đã tồn tại"),
            (self.service_values(line, line_code="DIFFERENT"), "Thứ tự đã tồn tại")):
            with patch("apps.costing.services.validate_line"), self.assertRaisesMessage(ValidationError, message):
                services.save_line(workspace=self.workspace, scheme=self.scheme, version=self.version, data=values)
        self.assertEqual(CostingSchemeLine.objects.filter(scheme_version=self.version).count(), 1)

    def test_clone_failure_rolls_back_version_and_partial_data(self):
        self.complete()
        with patch("django.db.models.query.QuerySet.bulk_create", side_effect=RuntimeError("test failure")), self.assertRaises(RuntimeError):
            services.save_version(workspace=self.workspace, scheme=self.scheme, source=self.version,
                data={"effective_from": self.today, "effective_to": None, "change_reason": "Clone"})
        self.assertEqual(CostingSchemeVersion.objects.filter(scheme=self.scheme).count(), 1)
        self.assertEqual(CostingSchemeLine.objects.filter(scheme_version=self.version).count(), 3)

    def test_valid_non_hour_uom_quantity_mapping(self):
        category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        unit = Uom.objects.create(category=category, code="KG", name="Kilôgam", symbol="kg")
        element = CostElement.objects.create(organization=self.company, code="MASS", name="Khối lượng", value_type="QUANTITY", dimension_code="MASS", default_uom=unit,
            default_source_mode="MANUAL", cost_scope="MANUFACTURING", accounting_scope="INVENTORY_COST")
        self.line(cost_element=element)
        self.assertEqual(self.report().errors, [])
        unit.is_active = False; unit.save()
        self.assertTrue(any("đơn vị tính" in error for error in self.report().errors))

    def test_formula_dependency_requires_effective_version_and_no_ambiguity(self):
        dependency = Formula.objects.create(organization=self.company, code="CHILD", name="Công thức con", output_element=self.output)
        dependent = Formula.objects.create(organization=self.company, code="PARENT", name="Công thức cha", output_element=self.output)
        parent = FormulaVersion.objects.create(formula=dependent, version_no=1, expression="@CHILD", status="EFFECTIVE", validation_status="VALID", effective_from=self.today)
        self.line(source_mode="FORMULA", formula_version=parent, cost_element=self.output)
        self.assertTrue(any("chưa có phiên bản phù hợp" in error for error in self.report().errors))
        for number in (1, 2):
            FormulaVersion.objects.create(formula=dependency, version_no=number, expression="$MATERIAL_COST", status="EFFECTIVE", validation_status="VALID", effective_from=self.today)
        self.assertTrue(any("nhiều phiên bản hiệu lực" in error for error in self.report().errors))

    def test_legacy_formula_invalid_expression_revalidated(self):
        formula = Formula.objects.create(organization=self.company, code="INVALID", name="Sai cú pháp")
        version = FormulaVersion.objects.create(formula=formula, version_no=1, expression="open(1)", status="EFFECTIVE", validation_status="VALID", effective_from=self.today)
        self.line(source_mode="FORMULA", formula_version=version)
        self.assertTrue(self.report().errors)

    def test_nested_line_ownership_and_locked_header_forgery_service(self):
        other_version = CostingSchemeVersion.objects.create(scheme=self.scheme, version_no=2)
        line = self.line(scheme_version=other_version)
        self.assertEqual(self.client.get(self.url("line_edit", line=line)).status_code, 404)
        self.version.status = "APPROVED"; self.version.save()
        values = {"code": "CHANGED", "name": "Tên", "purpose": "CHANGED", "context_scope": "GENERAL", "description": None, "is_active": True}
        with self.assertRaises(ValidationError): services.save_scheme(workspace=self.workspace, instance=self.scheme, data=values)

    def test_vietnamese_labels_no_auth_or_organization_controls(self):
        for action in ("list", "create", "detail", "line_create", "version_list"):
            response = self.client.get(self.url(action))
            self.assertEqual(response.status_code, 200)
            for text in (">Create<", ">Edit<", ">Save<", ">Cancel<", ">Search<", ">Status<", ">Actions<", ">Active<", ">Organization<", ">Login<"):
                self.assertNotContains(response, text)
