"""CRUD and temporal/Decimal contracts against real isolated PostgreSQL."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction, IntegrityError
from django.test import TestCase, Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from apps.core.models import Channel, ChannelFeeRule, TaxRule, FxRate, Organization, OrganizationMember, CostingSchemeLine
from apps.costing.demo_data import seed_demo
from apps.costing.demo_verification import verify_demo, create_golden_run, stored_fingerprint
from apps.master_data.access import Workspace
from apps.master_data.navigation import SECTIONS, DESTINATIONS
from .forms import ChannelForm, ChannelFeeRuleForm, TaxRuleForm, FxRateForm
from . import services, selectors
from .constants import FIELDS, MODELS


class PricingFoundationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="TEST", name="Công ty mẫu")
        cls.demo = seed_demo()
        cls.workspace = Workspace(cls.company)
        cls.channel = cls.save("channel", cls.payload("channel"))
        cls.fee = cls.save("channel_fee_rule", cls.payload("channel_fee_rule"))
        cls.tax = cls.save("tax_rule", cls.payload("tax_rule"))
        cls.fx = cls.save("fx_rate", cls.payload("fx_rate"))

    @classmethod
    def payload(cls, resource, **overrides):
        data = {
            "channel": {"code": "DIRECT", "name": "Kênh trực tiếp", "channel_type": "D2C", "market_code": "VN", "default_currency_code": "VND", "is_active": "on"},
            "channel_fee_rule": {"channel": getattr(cls, "channel", None).pk if hasattr(cls, "channel") else "", "fee_type": "COMMISSION", "fee_base": "LIST_PRICE", "rate": "8", "refundable_ratio": "0", "tax_inclusive": "False", "priority": "100", "effective_from": "2026-01-01", "effective_to": "2026-07-01", "status": "DRAFT"},
            "tax_rule": {"jurisdiction_code": "VN", "tax_type": "VAT", "tax_base": "LIST_PRICE", "rate": "10", "recoverable_ratio": "0", "inclusive": "False", "priority": "100", "effective_from": "2026-01-01", "effective_to": "2026-07-01", "status": "DRAFT"},
            "fx_rate": {"rate_type": "SPOT", "from_currency_code": "USD", "to_currency_code": "VND", "rate": "26000.123456789012", "effective_at": "2026-01-01T00:00:00", "valid_to": "2026-07-01T00:00:00", "source_name": "Nguồn nội bộ", "status": "DRAFT"},
        }[resource]
        return data | overrides

    @classmethod
    def save(cls, resource, data, instance=None):
        form = {"channel": ChannelForm, "channel_fee_rule": ChannelFeeRuleForm, "tax_rule": TaxRuleForm, "fx_rate": FxRateForm}[resource](data, workspace=cls.workspace, instance=instance)
        if not form.is_valid(): raise AssertionError(form.errors.as_json())
        return services.save_record(resource=resource, workspace=cls.workspace, data=form.cleaned_data, instance=instance)

    def url(self, resource, action="list", record=None):
        return reverse(f"pricing:{resource}_{action}", args=[record.pk] if record else [])

    def test_anonymous_all_lists_create_detail_edit_full_and_partial(self):
        for resource, record in (("channel", self.channel), ("channel_fee_rule", self.fee), ("tax_rule", self.tax), ("fx_rate", self.fx)):
            for action in ("list", "create", "detail", "edit"):
                with self.subTest(resource=resource, action=action):
                    response = self.client.get(self.url(resource, action, record if action in ("detail", "edit") else None))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, '<html lang="vi"')
                    partial = self.client.get(response.request["PATH_INFO"], HTTP_HX_REQUEST="true")
                    self.assertEqual(partial.status_code, 200)
                    self.assertNotContains(partial, "<!doctype")
                    self.assertNotContains(response, "Chờ phê duyệt</span>")
                    for text in ("Login", "Logout", "Create", "Actions", "Search", "True", "False"):
                        # Inspect visible text, not boolean option values/JS identifiers.
                        self.assertNotContains(response, f">{text}<")

    def test_channel_create_normalizes_and_is_unique(self):
        response = self.client.post(self.url("channel", "create"), self.payload("channel", code=" new ", name=" Tên mới "))
        self.assertEqual(response.status_code, 302)
        record = Channel.objects.get(code="NEW")
        self.assertEqual((record.name, record.organization_id), ("Tên mới", self.company.pk))
        duplicate = self.client.post(self.url("channel", "create"), self.payload("channel", code=" direct "))
        self.assertContains(duplicate, "Mã kênh bán đã tồn tại.")

    def test_channel_search_filters_sort_and_pagination(self):
        Channel.objects.bulk_create(Channel(organization=self.company, code=f"Z{i:03}", name=f"Kênh {i}", channel_type="B2B", is_active=False) for i in range(30))
        response = self.client.get(self.url("channel"), {"q": "trực tiếp"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        response = self.client.get(self.url("channel"), {"active": "false", "channel_type": "B2B", "sort": "-code", "page": "2", "per_page": "25"})
        self.assertEqual(response.context["page_obj"].paginator.count, 30)
        self.assertEqual(len(response.context["records"]), 5)
        self.assertEqual(response.context["records"][0].code, "Z004")
        self.assertContains(response, "active=false")

    def test_channel_invalid_required_fields_and_type(self):
        for overrides, field in (({"code": ""}, "code"), ({"name": ""}, "name"), ({"channel_type": "INVENTED"}, "channel_type")):
            response = self.client.post(self.url("channel", "create"), self.payload("channel", **overrides))
            self.assertIn(field, response.context["form"].errors)

    def test_channel_edit_and_deactivate(self):
        response = self.client.post(self.url("channel", "edit", self.channel), self.payload("channel", name="Tên sửa", is_active=""))
        self.assertEqual(response.status_code, 302)
        self.channel.refresh_from_db()
        self.assertFalse(self.channel.is_active)
        self.assertEqual(self.channel.name, "Tên sửa")

    def test_fee_percentage_boundary_round_trip_and_edit(self):
        self.assertEqual(self.fee.rate, Decimal("0.08"))
        response = self.client.get(self.url("channel_fee_rule", "edit", self.fee))
        self.assertEqual(response.context["form"]["rate"].value(), Decimal(8))
        response = self.client.post(self.url("channel_fee_rule", "edit", self.fee), self.payload("channel_fee_rule", rate="8.123456"))
        self.assertEqual(response.status_code, 302)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.rate, Decimal("0.08123456"))
        self.assertIsNone(self.fee.created_by)

    def test_fee_fixed_amount_and_currency(self):
        record = self.save("channel_fee_rule", self.payload("channel_fee_rule", rate="", fixed_amount="3000.12345678", currency_code="VND"))
        self.assertEqual(record.fixed_amount, Decimal("3000.12345678"))
        self.assertIsNone(record.rate)
        response = self.client.post(self.url("channel_fee_rule", "create"), self.payload("channel_fee_rule", rate="", fixed_amount="3000"))
        self.assertIn("currency_code", response.context["form"].errors)

    def test_fee_invalid_rates_amounts_limits_dates_and_required_inputs(self):
        cases = (({"rate": "-1"}, "rate"), ({"rate": "100.000001"}, "rate"), ({"rate": "0.0000001"}, "rate"), ({"rate": "", "fixed_amount": ""}, "rate"), ({"fixed_amount": "-1"}, "fixed_amount"), ({"cap_amount": "9", "floor_amount": "10", "currency_code": "VND"}, "cap_amount"), ({"refundable_ratio": "101"}, "refundable_ratio"), ({"channel": ""}, "channel"), ({"fee_base": ""}, "fee_base"), ({"tax_inclusive": ""}, "tax_inclusive"), ({"effective_to": "2025-12-31"}, "effective_to"), ({"effective_to": "2026-01-01"}, "effective_to"))
        for overrides, field in cases:
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url("channel_fee_rule", "create"), self.payload("channel_fee_rule", **overrides))
                self.assertIn(field, response.context["form"].errors)

    def test_fee_scope_validation_and_filter(self):
        r = self.demo.records
        self.save("channel_fee_rule", self.payload("channel_fee_rule", sku=r["sku"].pk, product_category=r["category"].pk))
        response = self.client.get(self.url("channel_fee_rule"), {"sku": r["sku"].pk, "channel": self.channel.pk, "product_category": r["category"].pk})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        other_category = type(r["category"]).objects.create(organization=self.company, code="OTHER", name="Khác")
        response = self.client.post(self.url("channel_fee_rule", "create"), self.payload("channel_fee_rule", sku=r["sku"].pk, product_category=other_category.pk))
        self.assertIn("sku", response.context["form"].errors)

    def test_tax_create_inclusive_and_fractional_storage(self):
        for inclusion in ("True", "False"):
            record = self.save("tax_rule", self.payload("tax_rule", inclusive=inclusion, rate="8.5", recoverable_ratio="75"))
            self.assertEqual((record.rate, record.recoverable_ratio, record.inclusive), (Decimal("0.085"), Decimal("0.75"), inclusion == "True"))
            response = self.client.get(self.url("tax_rule", "detail", record))
            self.assertContains(response, "Giá đã bao gồm thuế" if record.inclusive else "Giá chưa bao gồm thuế")

    def test_tax_fixed_amount(self):
        record = self.save("tax_rule", self.payload("tax_rule", rate="", fixed_amount="10", currency_code="VND"))
        self.assertEqual(record.fixed_amount, Decimal(10))

    def test_tax_invalid_rates_dates_amount_and_inclusion(self):
        for overrides, field in (({"rate": "101"}, "rate"), ({"recoverable_ratio": "-1"}, "recoverable_ratio"), ({"fixed_amount": "-1"}, "fixed_amount"), ({"rate": ""}, "rate"), ({"effective_to": "2025-01-01"}, "effective_to"), ({"inclusive": ""}, "inclusive"), ({"jurisdiction_code": ""}, "jurisdiction_code")):
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url("tax_rule", "create"), self.payload("tax_rule", **overrides))
                self.assertIn(field, response.context["form"].errors)

    def test_tax_edit_keeps_fraction(self):
        response = self.client.post(self.url("tax_rule", "edit", self.tax), self.payload("tax_rule", rate="5"))
        self.assertEqual(response.status_code, 302)
        self.tax.refresh_from_db()
        self.assertEqual(self.tax.rate, Decimal("0.05"))

    def test_tax_search_and_scope_filters(self):
        for parameter, value in (("q", "VAT"), ("jurisdiction_code", "VN"), ("tax_type", "VAT")):
            response = self.client.get(self.url("tax_rule"), {parameter: value})
            self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertEqual(self.client.get(self.url("tax_rule"), {"tax_class_code": "MISSING"}).context["page_obj"].paginator.count, 0)

    def test_fx_decimal_precision_and_direction(self):
        self.fx.refresh_from_db()
        self.assertEqual(self.fx.rate, Decimal("26000.123456789012"))
        response = self.client.get(self.url("fx_rate", "detail", self.fx))
        self.assertContains(response, "1 USD = 26.000,123456789012 VND")

    def test_fx_invalid_pair_rate_dates_precision_and_nonfinite(self):
        for overrides, field in (({"to_currency_code": "USD"}, "to_currency_code"), ({"rate": "0"}, "rate"), ({"rate": "-1"}, "rate"), ({"rate": "NaN"}, "rate"), ({"rate": "0.1234567890123"}, "rate"), ({"valid_to": "2025-01-01T00:00"}, "valid_to"), ({"source_name": ""}, "source_name")):
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url("fx_rate", "create"), self.payload("fx_rate", **overrides))
                self.assertIn(field, response.context["form"].errors)

    def test_fx_edit_draft(self):
        response = self.client.post(self.url("fx_rate", "edit", self.fx), self.payload("fx_rate", rate="25555"))
        self.assertEqual(response.status_code, 302)
        self.fx.refresh_from_db()
        self.assertEqual(self.fx.rate, Decimal(25555))

    def test_all_empty_states_and_history_restore(self):
        for resource in MODELS:
            response = self.client.get(self.url(resource), {"q": "NOT_FOUND"}, HTTP_HX_REQUEST="true")
            self.assertContains(response, "Không có kết quả phù hợp.")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
            self.assertContains(response, "<!doctype")
        ChannelFeeRule.objects.all().delete()
        self.assertContains(self.client.get(self.url("channel_fee_rule")), "Chưa có quy tắc phí kênh")

    def test_all_post_successes_have_toasts_and_htmx_redirect(self):
        for resource in MODELS:
            data = self.payload(resource, **({"code": "SECOND"} if resource == "channel" else {}))
            response = self.client.post(self.url(resource, "create"), data, HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertIn("HX-Redirect", response)
            destination = self.client.get(response["HX-Redirect"])
            self.assertContains(destination, "Đã tạo")

    def test_invalid_htmx_retains_input_and_accessible_errors(self):
        response = self.client.post(self.url("channel_fee_rule", "create"), self.payload("channel_fee_rule", rate="101"), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/reference_data_form_content.html")
        self.assertContains(response, 'value="101"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'for="id_rate"')

    def test_no_auth_membership_approval_audit_queries(self):
        with patch.object(OrganizationMember.objects, "filter", side_effect=AssertionError("Membership must not be queried")), CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.client.get(self.url("channel")).status_code, 200)
        for row in queries:
            for table in ("organization_member", "approval_request", "approval_action", "audit_event", "auth_user"):
                self.assertNotIn(table, row["sql"].lower())
        self.assertNotIn("apps.audit", settings.INSTALLED_APPS)
        self.assertNotIn("apps.workflow", settings.INSTALLED_APPS)

    def test_sidebar_only_implemented_destinations_without_approval_audit(self):
        names = [name for section, items in SECTIONS for name in items]
        self.assertEqual(set(names), set(DESTINATIONS))
        self.assertEqual(len(names), len(set(names)))
        for name in ("Approval Inbox", "My Requests", "Audit Log", "Workflow"): self.assertNotIn(name, names)
        for name in ("Channels", "Channel Fee Rules", "Tax Rules", "FX Rates"):
            self.assertTrue(reverse(DESTINATIONS[name][1]).startswith("/pricing/"))
        for resource in MODELS:
            response = self.client.get(self.url(resource))
            self.assertContains(response, f'href="{self.url(resource)}" aria-current="page"')

    def test_hidden_fields_cannot_be_forged_and_company_is_scoped(self):
        other = Organization.objects.create(code="OTHER", name="Công ty khác")
        foreign = Channel.objects.create(organization=other, code="FOREIGN", name="Khác", channel_type="OTHER")
        with override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk):
            self.assertEqual(self.client.get(self.url("channel", "detail", foreign)).status_code, 404)
            response = self.client.post(self.url("channel_fee_rule", "create"), self.payload("channel_fee_rule", channel=foreign.pk))
            self.assertIn("channel", response.context["form"].errors)
            response = self.client.post(self.url("channel_fee_rule", "create"), self.payload("channel_fee_rule", organization=other.pk, created_by="00000000-0000-0000-0000-000000000001"))
            self.assertEqual(response.status_code, 302)
            created = ChannelFeeRule.objects.latest("pk")
            self.assertEqual(created.organization_id, self.company.pk)
            self.assertIsNone(created.created_by)

    def test_inactive_new_references_rejected_but_history_preserved(self):
        Channel.objects.filter(pk=self.channel.pk).update(is_active=False)
        form = ChannelFeeRuleForm(workspace=self.workspace)
        self.assertNotIn(self.channel.pk, form.fields["channel"].queryset.values_list("pk", flat=True))
        form = ChannelFeeRuleForm(workspace=self.workspace, instance=self.fee)
        self.assertIn(self.channel.pk, form.fields["channel"].queryset.values_list("pk", flat=True))
        self.assertEqual(self.client.get(self.url("channel_fee_rule", "detail", self.fee)).status_code, 200)

    def test_direct_activation_and_effective_definitions_readonly(self):
        for resource, record in (("channel_fee_rule", self.fee), ("tax_rule", self.tax), ("fx_rate", self.fx)):
            self.save(resource, self.payload(resource, status="EFFECTIVE"), record)
            record.refresh_from_db()
            before = MODELS[resource].objects.values().get(pk=record.pk)
            response = self.client.post(self.url(resource, "edit", record), self.payload(resource, rate="1"))
            self.assertContains(response, "Bản đã chốt chỉ được xem.")
            self.assertEqual(before, MODELS[resource].objects.values().get(pk=record.pk))
            with self.assertRaisesMessage(ValidationError, "Bản đã chốt"):
                services.save_record(resource=resource, workspace=self.workspace, data={}, instance=record)

    def test_legacy_statuses_still_render_and_do_not_enable_editing(self):
        for status in ("IN_REVIEW", "APPROVED", "RETIRED"):
            ChannelFeeRule.objects.filter(pk=self.fee.pk).update(status=status)
            self.assertEqual(self.client.get(self.url("channel_fee_rule", "detail", self.fee)).status_code, 200)
            response = self.client.get(self.url("channel_fee_rule", "edit", self.fee))
            self.assertTrue(response.context["form_readonly"])

    def test_business_codes_are_not_invented_enums(self):
        record = self.save("channel_fee_rule", self.payload("channel_fee_rule", fee_type=" custom_fee ", fee_base=" custom_base "))
        self.assertEqual((record.fee_type, record.fee_base), ("CUSTOM_FEE", "CUSTOM_BASE"))

    def test_all_csrf_and_method_protection(self):
        client = Client(enforce_csrf_checks=True)
        for resource in MODELS:
            self.assertEqual(client.post(self.url(resource, "create"), self.payload(resource)).status_code, 403)
            self.assertEqual(self.client.post(self.url(resource)).status_code, 405)

    def test_fee_tax_fx_lists_search_sort_filter_pagination(self):
        for resource, record in (("channel_fee_rule", self.fee), ("tax_rule", self.tax), ("fx_rate", self.fx)):
            copies = []
            for i in range(29):
                clone = MODELS[resource](**{name: getattr(record, name) for name in FIELDS[resource]}, organization=self.company)
                copies.append(clone)
            MODELS[resource].objects.bulk_create(copies)
            search = {"channel_fee_rule": "trực tiếp", "tax_rule": "VAT", "fx_rate": "USD"}[resource]
            params = {"q": search, "status": "DRAFT", "sort": "-rate", "per_page": "25", "page": "2"}
            if resource == "channel_fee_rule": params["channel"] = self.channel.pk
            if resource == "fx_rate": params.update(from_currency_code="USD", to_currency_code="VND", rate_type="SPOT")
            response = self.client.get(self.url(resource), params, HTTP_HX_REQUEST="true")
            self.assertEqual(response.context["page_obj"].paginator.count, 30)
            self.assertEqual(len(response.context["records"]), 5)

    def test_invalid_sort_page_size_and_filter_are_safe(self):
        for resource in MODELS:
            response = self.client.get(self.url(resource), {"sort": "--DROP", "page": "oops", "per_page": "999"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["per_page"], 25)
        self.assertEqual(self.client.get(self.url("channel_fee_rule"), {"channel": "invalid"}).context["page_obj"].paginator.count, 0)

    def test_queryset_relations_do_not_grow_with_number_of_rows(self):
        for resource, record in (("channel", self.channel), ("channel_fee_rule", self.fee), ("tax_rule", self.tax), ("fx_rate", self.fx)):
            with CaptureQueriesContext(connection) as first: self.client.get(self.url(resource))
            clone_data = {name: getattr(record, name) for name in FIELDS[resource]}
            if resource == "channel": clone_data["code"] = "SECOND"
            MODELS[resource].objects.create(organization=self.company, **clone_data)
            with CaptureQueriesContext(connection) as second: self.client.get(self.url(resource))
            self.assertEqual(len(first), len(second), resource)
            self.assertTrue(any("LIMIT" in query["sql"] for query in second))

    def test_database_constraints_are_final_guard(self):
        for model, pk, changes in ((ChannelFeeRule, self.fee.pk, {"rate": Decimal(2)}), (TaxRule, self.tax.pk, {"recoverable_ratio": Decimal(-1)}), (FxRate, self.fx.pk, {"rate": Decimal(0)})):
            with self.assertRaises(IntegrityError), transaction.atomic(): model.objects.filter(pk=pk).update(**changes)

    def test_integrity_errors_are_friendly(self):
        from types import SimpleNamespace
        from django.db import IntegrityError
        error = IntegrityError("PRIVATE SQL")
        error.__cause__ = Exception("PRIVATE DETAIL")
        error.__cause__.sqlstate = "23505"
        error.__cause__.diag = SimpleNamespace(constraint_name="uq_channel")
        with patch.object(Channel, "save", side_effect=error):
            response = self.client.post(self.url("channel", "create"), self.payload("channel", code="NEW"))
        self.assertContains(response, "Mã kênh bán đã tồn tại.")
        self.assertNotContains(response, "PRIVATE")

    def test_cleanup_keeps_exact_scheme_clone_metadata_and_manual_input(self):
        from apps.costing.forms import SchemeLineForm
        from apps.costing.services import save_version
        from apps.costing.constants import COPY_FIELDS, VERSION_FIELDS
        source = self.demo.records["scheme_version"]
        form = SchemeLineForm(workspace=self.workspace, version=source)
        self.assertNotIn("approval_policy_code", form.fields)
        for name in ("editable", "override_requires_reason", "min_override_value", "max_override_value"): self.assertIn(name, form.fields)
        self.assertIn("approval_policy_code", COPY_FIELDS)
        before = list(CostingSchemeLine.objects.filter(scheme_version=source).order_by("display_order").values(*COPY_FIELDS))
        cloned = save_version(workspace=self.workspace, scheme=self.demo.records["scheme"], data={name: getattr(source, name) for name in VERSION_FIELDS}, source=source)
        self.assertEqual(before, list(CostingSchemeLine.objects.filter(scheme_version=cloned).order_by("display_order").values(*COPY_FIELDS)))
    def test_fee_selector_scope_currency_dates_and_all_applicable_rules(self):
        r = self.demo.records
        global_fee = self.save("channel_fee_rule", self.payload("channel_fee_rule", status="EFFECTIVE"))
        specific = self.save("channel_fee_rule", self.payload("channel_fee_rule", status="EFFECTIVE", sku=r["sku"].pk, product_category=r["category"].pk, priority="200"))
        self.save("channel_fee_rule", self.payload("channel_fee_rule", status="EFFECTIVE", currency_code="USD"))
        kwargs = dict(organization=self.company, channel=self.channel, on_date=date(2026, 1, 1), sku=r["sku"], currency="VND")
        rows = list(selectors.get_applicable_channel_fee_rules(**kwargs))
        self.assertEqual([row.pk for row in rows], [specific.pk, global_fee.pk])
        self.assertEqual(list(selectors.get_applicable_channel_fee_rules(**(kwargs | {"on_date": date(2026, 7, 1)}))), [])
        self.assertEqual(list(selectors.get_applicable_channel_fee_rules(**(kwargs | {"on_date": date(2025, 12, 31)}))), [])
        rows = list(selectors.get_applicable_channel_fee_rules(**(kwargs | {"sku": None})))
        self.assertEqual([row.pk for row in rows], [global_fee.pk])

    def test_tax_selector_explicit_scope_and_wildcards(self):
        generic = self.save("tax_rule", self.payload("tax_rule", status="EFFECTIVE"))
        specific = self.save("tax_rule", self.payload("tax_rule", status="EFFECTIVE", tax_class_code="FOOD", seller_type="COMPANY", transaction_type="SALE", priority="200"))
        kwargs = dict(organization=self.company, jurisdiction_code="VN", on_date=date(2026, 1, 1), tax_type="VAT", tax_class_code="FOOD", seller_type="COMPANY", transaction_type="SALE")
        self.assertEqual([row.pk for row in selectors.get_applicable_tax_rules(**kwargs)], [specific.pk, generic.pk])
        self.assertEqual([row.pk for row in selectors.get_applicable_tax_rules(**(kwargs | {"tax_class_code": None}))], [generic.pk])
        self.assertEqual(list(selectors.get_applicable_tax_rules(**(kwargs | {"jurisdiction_code": "OTHER"}))), [])
        self.assertEqual(list(selectors.get_applicable_tax_rules(**(kwargs | {"on_date": date(2026, 7, 1)}))), [])

    def test_fx_selector_historical_pair_type_and_exact_boundaries(self):
        old = self.save("fx_rate", self.payload("fx_rate", status="EFFECTIVE"))
        new = self.save("fx_rate", self.payload("fx_rate", status="EFFECTIVE", effective_at="2026-07-01T00:00:00", valid_to="", rate="27000"))
        kwargs = dict(organization=self.company, from_currency="USD", to_currency="VND", rate_type="SPOT")
        self.assertEqual(selectors.get_effective_fx_rate(**kwargs, effective_at=old.effective_at).pk, old.pk)
        self.assertEqual(selectors.get_effective_fx_rate(**kwargs, effective_at=new.effective_at).pk, new.pk)
        self.assertEqual(old.rate, Decimal("26000.123456789012"))
        for overrides in ({"from_currency": "VND", "to_currency": "USD"}, {"rate_type": "OTHER"}):
            with self.assertRaises(selectors.PricingResolutionError) as caught:
                selectors.get_effective_fx_rate(**(kwargs | overrides), effective_at=new.effective_at)
            self.assertEqual(caught.exception.code, "MISSING_FX")

    def test_fx_selector_ambiguity_fails_instead_of_latest_or_inverse(self):
        self.save("fx_rate", self.payload("fx_rate", status="EFFECTIVE"))
        overlap = self.save("fx_rate", self.payload("fx_rate", status="EFFECTIVE", rate="27000"))
        with self.assertRaises(selectors.PricingResolutionError) as caught:
            selectors.get_effective_fx_rate(organization=self.company, from_currency="USD", to_currency="VND", rate_type="SPOT", effective_at=overlap.effective_at)
        self.assertEqual(caught.exception.code, "AMBIGUOUS_FX")

    def test_resolvers_require_explicit_date_and_aware_time(self):
        with self.assertRaises(selectors.PricingResolutionError):
            selectors.get_applicable_tax_rules(organization=self.company, jurisdiction_code="", on_date=date(2026, 1, 1))
        with self.assertRaises(selectors.PricingResolutionError):
            selectors.get_applicable_tax_rules(organization=self.company, jurisdiction_code="VN", on_date=timezone.now())
        with self.assertRaises(selectors.PricingResolutionError):
            selectors.get_effective_fx_rate(organization=self.company, from_currency="USD", to_currency="VND", rate_type="SPOT", effective_at=datetime(2026, 1, 1))

    def test_pricing_data_and_cleanup_do_not_change_golden_or_history(self):
        run = create_golden_run(self.demo)
        before = stored_fingerprint(run)
        for resource in ("channel_fee_rule", "tax_rule", "fx_rate"):
            self.save(resource, self.payload(resource, status="EFFECTIVE"))
        report = verify_demo(self.demo, smoke=False)
        self.assertEqual(report["golden"]["comparisons"]["FULL_COST"]["actual"], "583000.00000000")
        self.assertEqual(report["future"]["comparisons"]["FULL_COST"]["actual"], "647000.00000000")
        self.assertEqual(before, stored_fingerprint(run))

    def test_close_period_only_changes_future_end_and_preserves_definition(self):
        from datetime import timedelta
        for resource in ("channel_fee_rule", "tax_rule", "fx_rate"):
            field = "valid_to" if resource == "fx_rate" else "effective_to"
            record = self.save(resource, self.payload(resource, status="EFFECTIVE", **{field: ""}))
            before = MODELS[resource].objects.values().get(pk=record.pk)
            end = timezone.now() + timedelta(days=60) if resource == "fx_rate" else timezone.localdate() + timedelta(days=60)
            services.close_period(resource=resource, workspace=self.workspace, instance=record, end=end)
            after = MODELS[resource].objects.values().get(pk=record.pk)
            self.assertEqual(after.pop(field), end)
            before.pop(field)
            self.assertEqual(before, after)
            with self.assertRaises(ValidationError): services.close_period(resource=resource, workspace=self.workspace, instance=record, end=end + timedelta(days=1))

    def test_close_period_rejects_past_and_has_htmx_fallback(self):
        from datetime import timedelta
        record = self.save("channel_fee_rule", self.payload("channel_fee_rule", status="EFFECTIVE", effective_to=""))
        url = self.url("channel_fee_rule", "close", record)
        response = self.client.post(url, {"effective_to": "2020-01-01"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Mốc kết thúc phải trong tương lai")
        response = self.client.post(url, {"effective_to": (timezone.localdate() + timedelta(days=60)).isoformat()}, HTTP_HX_REQUEST="true")
        self.assertIn("HX-Redirect", response)
