"""Existing pool/rule constraints, CRUD, history and presentation integration."""
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AllocationRule, CostPool, Organization, Uom, UomCategory
from apps.master_data.access import INTERNAL_ACCESS, Workspace, get_workspace
from . import overhead_selectors as selectors, overhead_services as services
from .overhead_constants import ALLOCATION_BASES, RULE_STATUSES
from .overhead_forms import AllocationRuleForm, CostPoolForm
from .overhead_views import cost_pool_create


class OverheadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="OVERHEAD", name="Công ty nội bộ")
        cls.other = Organization.objects.create(code="OTHER", name="Dữ liệu khác")
        time = UomCategory.objects.create(code="TIME", name="Thời gian", dimension_code="TIME")
        cls.hour = Uom.objects.create(category=time, code="H", name="Giờ", symbol="h")
        cls.inactive_unit = Uom.objects.create(category=time, code="OLD", name="Phút cũ", symbol="phút", is_active=False)
        cls.pool = CostPool.objects.create(organization=cls.company, code="FACTORY", name="Nhà máy", pool_type="FACTORY_FIXED", description="Chi phí thuê nhà xưởng")
        cls.variable = CostPool.objects.create(organization=cls.company, code="VARIABLE", name="Biến đổi", pool_type="FACTORY_VARIABLE")
        cls.inactive = CostPool.objects.create(organization=cls.company, code="OLD", name="Nhóm cũ", pool_type="OTHER", is_active=False)
        cls.foreign = CostPool.objects.create(organization=cls.other, code="PRIVATE", name="Nhóm khác", pool_type="QA")
        cls.today = timezone.localdate()
        cls.rule = AllocationRule.objects.create(organization=cls.company, pool=cls.pool, code="MACHINE", name="Phân bổ giờ máy",
            basis_type="MACHINE_HOUR", basis_uom=cls.hour, priority=10, effective_from=cls.today)
        cls.future = AllocationRule.objects.create(organization=cls.company, pool=cls.variable, code="FUTURE", name="Phân bổ tương lai",
            basis_type="UNIT", priority=20, effective_from=cls.today+timedelta(days=10))
        cls.expired = AllocationRule.objects.create(organization=cls.company, pool=cls.pool, code="EXPIRED", name="Quy tắc cũ",
            basis_type="NORMAL_CAPACITY", priority=100, effective_from=cls.today-timedelta(days=30), effective_to=cls.today-timedelta(days=1), status="RETIRED")
        cls.foreign_rule = AllocationRule.objects.create(organization=cls.other, pool=cls.foreign, code="PRIVATE_RULE", name="Quy tắc khác",
            basis_type="CUSTOM", effective_from=cls.today)

    def setUp(self):
        config = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        config.enable()
        self.addCleanup(config.disable)

    def url(self, resource="cost_pool", action="list", record=None):
        return reverse(f"bom:{resource}_{action}", args=[record.pk] if record else [])

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url()))

    def pool_payload(self, **changes):
        values = dict(code=" new_pool ", name=" Nhóm chi phí mới ", pool_type="OTHER", description=" Mô tả mới ", is_active="on")
        values.update(changes)
        return values

    def rule_payload(self, **changes):
        values = dict(pool=str(self.pool.pk), code=" new_rule ", name=" Quy tắc mới ", basis_type="LABOR_HOUR", basis_uom=str(self.hour.pk),
            formula_code=" ref_Case ", priority="100", effective_from=self.today.isoformat(), effective_to="")
        values.update(changes)
        return values

    def rule_values(self, **changes):
        form = AllocationRuleForm(self.rule_payload(**changes), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def pool_values(self, **changes):
        form = CostPoolForm(self.pool_payload(**changes), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def test_lists_direct_access_and_no_membership_or_calculation_queries(self):
        with CaptureQueriesContext(connection) as queries:
            for resource in ("cost_pool", "allocation_rule"):
                response = self.client.get(self.url(resource))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-current="page"', count=1)
                self.assertNotContains(response, "PRIVATE")
                self.assertNotIn("sessionid", response.cookies)
        for query in queries:
            for table in ("organization_member", "cost_pool_period", "cost_element", "resource_rate", "costing_run"):
                self.assertNotIn(f'"{table}"', query["sql"])

    def test_pool_search_code_name_description(self):
        for keyword in ("factory", "Nhà máy", "thuê nhà xưởng"):
            response = self.client.get(self.url(), {"q": keyword})
            self.assertEqual(list(response.context["records"]), [self.pool])

    def test_pool_type_and_active_filters(self):
        for filters, expected in (({"pool_type": "FACTORY_VARIABLE"}, [self.variable]), ({"active": "false"}, [self.inactive]),
            ({"is_active": "true", "pool_type": "FACTORY_FIXED"}, [self.pool])):
            self.assertEqual(list(self.client.get(self.url(), filters).context["records"]), expected)

    def test_pool_sort_and_invalid_sort_fallback(self):
        for sort in ("code", "-code", "name", "-name", "created_at", "-created_at", "--code", "unknown"):
            response = self.client.get(self.url(), {"sort": sort})
            self.assertEqual(response.status_code, 200)
            expected = sort if sort not in ("--code", "unknown") else "code"
            self.assertEqual(response.context["current_sort"], expected)

    def test_pool_pagination_and_rule_count(self):
        CostPool.objects.bulk_create([CostPool(organization=self.company, code=f"POOL_{i:03}", name="Nhóm", pool_type="OTHER") for i in range(60)])
        for per_page in (25, 50, 100):
            response = self.client.get(self.url(), {"per_page": per_page})
            self.assertEqual(len(response.context["records"]), min(per_page, 63))
        self.assertEqual(self.client.get(self.url(), {"page": 3}).context["page_obj"].number, 3)
        self.assertEqual(selectors.overhead_detail(resource="cost_pool", organization=self.company, pk=self.pool.pk).rule_count, 2)

    def test_pool_create_normalizes_and_ignores_internal_fields(self):
        response = self.client.post(self.url(action="create"), self.pool_payload(organization=self.other.pk, status="EFFECTIVE", created_at="2000-01-01"))
        record = CostPool.objects.get(code="NEW_POOL")
        self.assertRedirects(response, self.url(action="detail", record=record), fetch_redirect_response=False)
        self.assertEqual(record.organization, self.company)
        self.assertEqual(record.name, "Nhóm chi phí mới")
        self.assertEqual(record.description, "Mô tả mới")
        self.assertContains(self.client.get(response.url), "Đã tạo nhóm chi phí chung.")

    def test_pool_duplicate_and_required_values(self):
        for changes, field in (({"code": " factory "}, "code"), ({"code": " "}, "code"), ({"name": " "}, "name"),
            ({"pool_type": ""}, "pool_type"), ({"pool_type": "FAKE"}, "pool_type")):
            response = self.client.post(self.url(action="create"), self.pool_payload(**changes))
            self.assertEqual(response.status_code, 200)
            self.assertIn(field, response.context["form"].errors)
            self.assertContains(response, 'aria-invalid="true"')

    def test_pool_edit_and_confirmation_hook(self):
        url = self.url(action="edit", record=self.pool)
        self.assertContains(self.client.get(url), "deactivate-reference")
        response = self.client.post(url, self.pool_payload(code=" factory ", name="Tên cập nhật", is_active=""))
        self.assertRedirects(response, self.url(action="detail", record=self.pool))
        self.pool.refresh_from_db()
        self.assertEqual(self.pool.name, "Tên cập nhật")
        self.assertFalse(self.pool.is_active)
        self.assertContains(self.client.get(response.url), "Ngừng hoạt động")

    def test_pool_detail_and_paginated_rule_history(self):
        url = self.url(action="detail", record=self.pool)
        response = self.client.get(url)
        self.assertContains(response, "Quy tắc phân bổ của nhóm")
        self.assertEqual(response.context["rule_history"]["page_obj"].paginator.count, 2)
        self.assertContains(response, self.url("allocation_rule", "create")+f"?pool={self.pool.pk}")
        self.assertContains(response, 'id="reference-data-filters"')
        AllocationRule.objects.bulk_create([AllocationRule(organization=self.company, pool=self.pool, code=f"RULE_{i:03}", name="Quy tắc", basis_type="UNIT", effective_from=self.today) for i in range(28)])
        response = self.client.get(url, {"page": 2}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="reference-data-table")
        self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
        self.assertEqual(len(response.context["records"]), 5)
        self.assertNotContains(response, "<!doctype")
        response = self.client.get(url, {"q": "machine", "status": "DRAFT"})
        self.assertEqual(response.context["rule_history"]["page_obj"].paginator.count, 1)

    def test_pool_empty_and_htmx_full_history_restore(self):
        for resource in ("cost_pool", "allocation_rule"):
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
            self.assertNotContains(response, "<!doctype")
            restore = self.client.get(self.url(resource), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
            self.assertContains(restore, "<!doctype")
        AllocationRule.objects.filter(organization=self.company).delete()
        CostPool.objects.filter(organization=self.company).delete()
        self.assertContains(self.client.get(self.url()), "Chưa có nhóm chi phí chung.")
        self.assertContains(self.client.get(self.url("allocation_rule")), "Chưa có quy tắc phân bổ.")

    def test_rule_search_code_name_pool_code_name(self):
        for keyword, expected in (("machine", [self.rule]), ("Phân bổ giờ máy", [self.rule]), ("factory", [self.expired, self.rule]), ("Nhà máy", [self.expired, self.rule])):
            response = self.client.get(self.url("allocation_rule"), {"q": keyword})
            self.assertEqual(list(response.context["records"]), expected)

    def test_rule_pool_basis_unit_status_filters(self):
        for filters, expected in (({"pool": str(self.variable.pk)}, [self.future]), ({"basis_type": "MACHINE_HOUR"}, [self.rule]),
            ({"basis_uom": str(self.hour.pk)}, [self.rule]), ({"status": "RETIRED"}, [self.expired])):
            self.assertEqual(list(self.client.get(self.url("allocation_rule"), filters).context["records"]), expected)

    def test_rule_effective_status_filters_include_end_date(self):
        for status, expected in (("EFFECTIVE", [self.rule]), ("FUTURE", [self.future]), ("EXPIRED", [self.expired])):
            self.assertEqual(list(self.client.get(self.url("allocation_rule"), {"effective": status}).context["records"]), expected)
        AllocationRule.objects.filter(pk=self.expired.pk).update(effective_to=self.today)
        self.assertIn(self.expired.pk, self.client.get(self.url("allocation_rule"), {"effective": "EFFECTIVE"}).context["records"].values_list("pk", flat=True))

    def test_rule_sort_and_pagination(self):
        for sort, expected in (("priority", [self.rule, self.future, self.expired]), ("-priority", [self.expired, self.future, self.rule]),
            ("effective_from", [self.expired, self.rule, self.future]), ("-effective_from", [self.future, self.rule, self.expired])):
            self.assertEqual(list(self.client.get(self.url("allocation_rule"), {"sort": sort}).context["records"]), expected)
        AllocationRule.objects.bulk_create([AllocationRule(organization=self.company, pool=self.pool, code=f"RULE_{i:03}", name="Quy tắc", basis_type="UNIT", effective_from=self.today) for i in range(60)])
        for per_page in (25, 50, 100):
            response = self.client.get(self.url("allocation_rule"), {"per_page": per_page})
            self.assertEqual(len(response.context["records"]), min(per_page, 63))
        self.assertEqual(self.client.get(self.url("allocation_rule"), {"page": 3}).context["page_obj"].number, 3)

    def test_rule_create_normalized_draft_null_actor_and_empty_conditions(self):
        response = self.client.post(self.url("allocation_rule", "create"), self.rule_payload(organization=self.other.pk, status="EFFECTIVE", condition_jsonb='{"target_type":"SKU"}', created_by="bad"))
        record = AllocationRule.objects.get(code="NEW_RULE")
        self.assertRedirects(response, self.url("allocation_rule", "detail", record), fetch_redirect_response=False)
        self.assertEqual((record.organization, record.pool, record.basis_uom), (self.company, self.pool, self.hour))
        self.assertEqual((record.name, record.formula_code, record.status, record.condition_jsonb, record.created_by), ("Quy tắc mới", "ref_Case", "DRAFT", {}, None))
        self.assertContains(self.client.get(response.url), "Đã tạo quy tắc phân bổ.")

    def test_rule_duplicate_required_pool_basis_code_name(self):
        for changes, field in (({"code": " machine "}, "code"), ({"code": " "}, "code"), ({"name": " "}, "name"),
            ({"pool": ""}, "pool"), ({"basis_type": ""}, "basis_type"), ({"basis_type": "MACHINE_HOURS"}, "basis_type")):
            response = self.client.post(self.url("allocation_rule", "create"), self.rule_payload(**changes))
            self.assertEqual(response.status_code, 200)
            self.assertIn(field, response.context["form"].errors)

    def test_rule_invalid_priority_and_signed_integer_range(self):
        for priority in ("", "1.5", "bad", "2147483648", "-2147483649"):
            form = AllocationRuleForm(self.rule_payload(priority=priority), workspace=self.workspace())
            self.assertFalse(form.is_valid())
            self.assertIn("priority", form.errors)
        for priority in ("0", "-1", "2147483647", "-2147483648"):
            self.assertTrue(AllocationRuleForm(self.rule_payload(priority=priority), workspace=self.workspace()).is_valid())

    def test_rule_invalid_effective_dates(self):
        for changes, field in (({"effective_from": ""}, "effective_from"), ({"effective_to": self.today.isoformat()}, "effective_to"),
            ({"effective_to": (self.today-timedelta(days=1)).isoformat()}, "effective_to"), ({"effective_to": "bad"}, "effective_to")):
            response = self.client.post(self.url("allocation_rule", "create"), self.rule_payload(**changes))
            self.assertIn(field, response.context["form"].errors)

    def test_all_stored_bases_and_optional_unit_formula(self):
        for basis, _ in ALLOCATION_BASES:
            with self.subTest(basis=basis):
                form = AllocationRuleForm(self.rule_payload(basis_type=basis, basis_uom="", formula_code=""), workspace=self.workspace())
                self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("FIXED_PERCENTAGE", dict(ALLOCATION_BASES))

    def test_rule_edit_preserves_status_conditions_actor_and_created_at(self):
        conditions = {"legacy_scope": ["SKU", 19], "nested": {"threshold": "0.125"}}
        AllocationRule.objects.filter(pk=self.rule.pk).update(status="EFFECTIVE", condition_jsonb=conditions)
        before = AllocationRule.objects.get(pk=self.rule.pk)
        response = self.client.post(self.url("allocation_rule", "edit", self.rule), self.rule_payload(code=" machine ", name="Cập nhật", status="DRAFT", condition_jsonb="{}"))
        self.assertRedirects(response, self.url("allocation_rule", "detail", self.rule), fetch_redirect_response=False)
        self.rule.refresh_from_db()
        self.assertEqual((self.rule.status, self.rule.condition_jsonb, self.rule.created_at, self.rule.created_by), ("EFFECTIVE", conditions, before.created_at, None))
        self.assertEqual(self.rule.name, "Cập nhật")
        self.assertContains(self.client.get(response.url), "Đã cập nhật quy tắc phân bổ.")
        detail = self.client.get(response.url)
        self.assertContains(detail, "Có điều kiện áp dụng bổ sung")
        self.assertNotContains(detail, "legacy_scope")

    def test_new_dated_rule_keeps_old_history_and_overlap_has_no_invented_policy(self):
        before = AllocationRule.objects.get(pk=self.rule.pk)
        created = services.save_allocation_rule(workspace=self.workspace(), data=self.rule_values())
        self.rule.refresh_from_db()
        for field in ("code", "name", "effective_from", "effective_to", "basis_type", "priority"):
            self.assertEqual(getattr(self.rule, field), getattr(before, field))
        self.assertEqual(created.effective_from, self.rule.effective_from)
        self.assertNotEqual(created.pk, self.rule.pk)

    def test_rule_detail_and_preselected_pool(self):
        response = self.client.get(self.url("allocation_rule", "detail", self.rule))
        for label in ("Giờ máy", "Nhóm chi phí", "Hiệu lực theo ngày", "Mức ưu tiên"):
            self.assertContains(response, label)
        self.assertContains(response, self.today.strftime("%d/%m/%Y"))
        response = self.client.get(self.url("allocation_rule", "create"), {"pool": self.variable.pk})
        self.assertEqual(response.context["form"].initial["pool"], self.variable.pk)
        self.assertEqual(self.client.get(self.url("allocation_rule", "create"), {"pool": "bad"}).status_code, 404)

    def test_inactive_catalogs_hidden_for_create_and_kept_for_edit(self):
        create = AllocationRuleForm(workspace=self.workspace())
        self.assertNotIn(self.inactive, create.fields["pool"].queryset)
        self.assertNotIn(self.inactive_unit, create.fields["basis_uom"].queryset)
        AllocationRule.objects.filter(pk=self.rule.pk).update(pool=self.inactive, basis_uom=self.inactive_unit)
        self.rule.refresh_from_db()
        edit = AllocationRuleForm(workspace=self.workspace(), instance=self.rule)
        self.assertIn(self.inactive, edit.fields["pool"].queryset)
        self.assertIn(self.inactive_unit, edit.fields["basis_uom"].queryset)
        values = self.rule_payload(code="machine", pool=str(self.inactive.pk), basis_uom=str(self.inactive_unit.pk))
        self.assertTrue(AllocationRuleForm(values, workspace=self.workspace(), instance=self.rule).is_valid())

    def test_stale_pool_and_unit_checks_in_service(self):
        values = self.rule_values()
        CostPool.objects.filter(pk=self.pool.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            services.save_allocation_rule(workspace=self.workspace(), data=values)
        CostPool.objects.filter(pk=self.pool.pk).update(is_active=True)
        Uom.objects.filter(pk=self.hour.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            services.save_allocation_rule(workspace=self.workspace(), data=values)

    def test_scope_and_corrupt_cross_scope_references_rejected(self):
        for resource, record in (("cost_pool", self.foreign), ("allocation_rule", self.foreign_rule)):
            for action in ("detail", "edit"):
                self.assertEqual(self.client.get(self.url(resource, action, record)).status_code, 404)
        form = AllocationRuleForm(self.rule_payload(pool=str(self.foreign.pk)), workspace=self.workspace())
        self.assertFalse(form.is_valid())
        values = self.rule_values()
        values["pool"] = self.foreign
        with self.assertRaises(ValidationError):
            services.save_allocation_rule(workspace=self.workspace(), data=values)
        with self.assertRaises(ValidationError):
            services.save_cost_pool(workspace=self.workspace(), instance=self.foreign, data=self.pool_payload())
        AllocationRule.objects.filter(pk=self.rule.pk).update(pool=self.foreign)
        self.assertEqual(self.client.get(self.url("allocation_rule", "detail", self.rule)).status_code, 404)

    def test_service_mass_assignment_ignored_and_invalid_values_rejected(self):
        values = self.rule_values()
        values.update(status="EFFECTIVE", condition_jsonb={"target_id": 1}, created_by="fake", organization=self.other)
        saved = services.save_allocation_rule(workspace=self.workspace(), data=values)
        self.assertEqual((saved.organization, saved.status, saved.condition_jsonb, saved.created_by), (self.company, "DRAFT", {}, None))
        for changes in ({"pool": "bad"}, {"basis_uom": "bad"}, {"priority": True}, {"basis_type": "FAKE"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                services.save_allocation_rule(workspace=self.workspace(), data={**self.rule_values(code="ANOTHER"), **changes})

    def test_no_fake_fields_or_hard_delete_routes(self):
        pool_form = CostPoolForm(workspace=self.workspace())
        rule_form = AllocationRuleForm(workspace=self.workspace())
        for name in ("organization", "status", "created_by", "target_type", "target_id", "percentage", "weight", "factor", "condition_jsonb", "version_no"):
            self.assertNotIn(name, rule_form.fields)
        for name in ("cost_element", "members", "effective_from", "status", "version_no"):
            self.assertNotIn(name, pool_form.fields)
        for path in (f"/bom/cost-pools/{self.pool.pk}/delete/", f"/bom/allocation-rules/{self.rule.pk}/delete/"):
            self.assertEqual(self.client.post(path).status_code, 404)

    def test_htmx_form_errors_redirect_and_detail_partial(self):
        for resource, record, payload in (("cost_pool", self.pool, self.pool_payload), ("allocation_rule", self.rule, self.rule_payload)):
            response = self.client.post(self.url(resource, "create"), payload(code=""), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_form_content.html")
            self.assertIn("code", response.context["form"].errors)
            response = self.client.post(self.url(resource, "create"), payload(), HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertIn("HX-Redirect", response)
            detail = self.client.get(self.url(resource, "detail", record), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(detail, "bom/overhead/partials/detail_content.html")
            restore = self.client.get(self.url(resource, "detail", record), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
            self.assertContains(restore, "<!doctype")

    def test_csrf_enforced_without_user_session(self):
        client = Client(enforce_csrf_checks=True)
        url = self.url(action="create")
        self.assertEqual(client.get(url).status_code, 200)
        self.assertEqual(client.post(url, self.pool_payload()).status_code, 403)
        self.assertEqual(client.post(url, self.pool_payload(), HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 302)
        self.assertNotIn("sessionid", client.cookies)

    def test_internal_access_hook_used_by_view_and_service(self):
        denied = replace(INTERNAL_ACCESS, can_create_cost_pool=False)
        request = RequestFactory().get(self.url(action="create"))
        request._costing_workspace = Workspace(self.company, denied)
        with self.assertRaises(PermissionDenied):
            cost_pool_create(request)
        with self.assertRaises(PermissionDenied):
            services.save_cost_pool(workspace=request._costing_workspace, data=self.pool_payload())

    def test_database_constraints_and_duplicate_race_mapping(self):
        for model, pk, values in ((CostPool, self.pool.pk, {"pool_type": "FAKE"}), (AllocationRule, self.rule.pk, {"basis_type": "FAKE"}),
            (AllocationRule, self.rule.pk, {"status": "LOCKED"}), (AllocationRule, self.rule.pk, {"effective_to": self.today})):
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.filter(pk=pk).update(**values)
        with patch("apps.bom.overhead_services.validate_cost_pool"), self.assertRaisesMessage(ValidationError, "Mã nhóm chi phí đã tồn tại"):
            services.save_cost_pool(workspace=self.workspace(), data={**self.pool_values(), "code": "FACTORY"})
        with patch("apps.bom.overhead_services.validate_allocation_rule"), self.assertRaisesMessage(ValidationError, "Mã quy tắc phân bổ đã tồn tại"):
            services.save_allocation_rule(workspace=self.workspace(), data={**self.rule_values(), "code": "MACHINE"})

    def test_service_failure_rolls_back(self):
        values = self.rule_values()
        with patch.object(AllocationRule, "save", side_effect=IntegrityError("do not expose raw database error")), self.assertRaisesMessage(ValidationError, "Dữ liệu không còn hợp lệ"):
            services.save_allocation_rule(workspace=self.workspace(), data=values)
        self.assertFalse(AllocationRule.objects.filter(code="NEW_RULE").exists())

    def test_rule_list_and_pool_history_avoid_n_plus_one(self):
        with self.assertNumQueries(1):
            for rule in selectors.rule_queryset(organization=self.company):
                rule.pool.name
                if rule.basis_uom:
                    rule.basis_uom.name
        urls = (self.url("allocation_rule"), self.url(action="detail", record=self.pool), self.url())
        counts = []
        for url in urls:
            with CaptureQueriesContext(connection) as queries:
                self.client.get(url)
            counts.append(len(queries))
        AllocationRule.objects.bulk_create([AllocationRule(organization=self.company, pool=self.pool, code=f"QUERY_{i:03}", name="Quy tắc", basis_type="UNIT", basis_uom=self.hour, effective_from=self.today) for i in range(22)])
        for url, count in zip(urls, counts):
            with CaptureQueriesContext(connection) as queries:
                self.client.get(url)
            self.assertEqual(len(queries), count)

    def test_vietnamese_mappings_and_main_pages(self):
        for resource, record in (("cost_pool", self.pool), ("allocation_rule", self.rule)):
            for action, instance in (("list", None), ("create", None), ("detail", record), ("edit", record)):
                response = self.client.get(self.url(resource, action, instance))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-label="Điều hướng trang"')
                for label in (">Create<", ">Edit<", ">Save<", ">Search<", ">Status<", ">Active<", ">Login<"):
                    self.assertNotContains(response, label)
        self.assertContains(self.client.get(self.url()), "Chi phí cố định nhà máy")
        self.assertContains(self.client.get(self.url("allocation_rule")), "Giờ máy")
