"""Resource vertical slices against isolated PostgreSQL and production checks."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Currency, Organization, Resource, ResourceRate, Uom, UomCategory, WorkCenter
from apps.master_data.access import INTERNAL_ACCESS, Workspace, get_workspace
from . import resource_selectors as selectors, resource_services as services
from .resource_forms import ResourceForm, ResourceRateForm, WorkCenterForm
from .resource_views import work_center_create


class ProductionResourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="INTERNAL", name="Công ty nội bộ")
        cls.other = Organization.objects.create(code="OTHER", name="Dữ liệu khác")
        cls.vnd = Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
        cls.usd = Currency.objects.create(code="USD", name="Đô la Mỹ")
        cls.time = UomCategory.objects.create(code="TIME", name="Thời gian", dimension_code="TIME")
        cls.energy = UomCategory.objects.create(code="ENERGY", name="Năng lượng", dimension_code="ENERGY")
        cls.hour = Uom.objects.create(category=cls.time, code="H", name="Giờ", symbol="h")
        cls.kwh = Uom.objects.create(category=cls.energy, code="KWH", name="Kilowatt giờ", symbol="kWh")
        cls.center = WorkCenter.objects.create(organization=cls.company, code="WC_MIX", name="Khu vực phối trộn", site_code="SITE_A", capacity_value=Decimal("20"), capacity_uom=cls.hour)
        cls.inactive_center = WorkCenter.objects.create(organization=cls.company, code="WC_OLD", name="Khu vực cũ", is_active=False)
        cls.other_center = WorkCenter.objects.create(organization=cls.other, code="SECRET_CENTER", name="Trung tâm khác")
        cls.resource = Resource.objects.create(organization=cls.company, code="MIXER", name="Máy trộn số 1", resource_type="MACHINE", work_center=cls.center, capacity_uom=cls.hour)
        cls.labor = Resource.objects.create(organization=cls.company, code="LABOR", name="Nhân công", resource_type="LABOR", is_active=False)
        cls.other_resource = Resource.objects.create(organization=cls.other, code="SECRET_RESOURCE", name="Nguồn lực khác", resource_type="SERVICE", work_center=cls.other_center)
        cls.today = timezone.localdate()
        cls.rate = ResourceRate.objects.create(organization=cls.company, resource=cls.resource, rate_type="OPERATING", amount=Decimal("120000.12345678"),
            currency_code=cls.vnd, per_uom=cls.hour, effective_from=cls.today - timedelta(days=20), effective_to=cls.today + timedelta(days=20))
        cls.other_rate = ResourceRate.objects.create(organization=cls.other, resource=cls.other_resource, rate_type="PRIVATE", amount=1, currency_code=cls.vnd, per_uom=cls.hour, effective_from=cls.today)
        cls.records = {"work_center": cls.center, "resource": cls.resource, "resource_rate": cls.rate}
        cls.models = {"work_center": WorkCenter, "resource": Resource, "resource_rate": ResourceRate}
        cls.forms = {"work_center": WorkCenterForm, "resource": ResourceForm, "resource_rate": ResourceRateForm}

    def setUp(self):
        settings = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        settings.enable()
        self.addCleanup(settings.disable)

    def url(self, resource, action="list", record=None):
        return reverse(f"bom:{resource}_{action}", args=[record.pk] if record is not None else [])

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url("resource")))

    def payload(self, kind, **changes):
        data = {
            "work_center": dict(code=" wc_new ", name=" Trung tâm mới ", site_code=" SITE_B ", capacity_value="40", normal_capacity_value="30", capacity_uom=str(self.hour.pk), is_active="on"),
            "resource": dict(code=" resource_new ", name=" Nguồn lực mới ", resource_type="SERVICE", work_center=str(self.center.pk), capacity_value="1.12345678", capacity_uom=str(self.kwh.pk), is_active="on"),
            "resource_rate": dict(resource=str(self.resource.pk), rate_type=" OPERATING ", amount="250000.12345678", currency_code="VND", per_uom=str(self.hour.pk),
                effective_from=self.today.isoformat(), effective_to=(self.today + timedelta(days=90)).isoformat(), source_reference=" REF-2026 "),
        }[kind]
        data.update(changes)
        return data

    def values(self, resource, **changes):
        form = self.forms[resource](self.payload(resource, **changes), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def test_anonymous_lists_details_and_active_sidebar(self):
        with CaptureQueriesContext(connection) as queries:
            for resource, record in self.records.items():
                with self.subTest(resource=resource):
                    response = self.client.get(self.url(resource))
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(record, response.context["records"])
                    self.assertContains(response, f'href="{self.url(resource)}" aria-current="page"')
                    self.assertContains(response, 'aria-current="page"', count=1)
                    self.assertNotIn("sessionid", response.cookies)
                    detail = self.client.get(self.url(resource, "detail", record))
                    self.assertEqual(detail.status_code, 200)
                    self.assertTemplateUsed(detail, "bom/resources/detail.html")
                    self.assertContains(detail, record.name if resource != "resource_rate" else "120.000,12345678 VND / Giờ")
        self.assertFalse(any("organization_member" in query["sql"] for query in queries))

    def test_center_search_code_name_site(self):
        for q in ("wc_mix", "Khu vực phối trộn", "site_a"):
            self.assertEqual(list(self.client.get(self.url("work_center"), {"q": q}).context["records"]), [self.center])

    def test_resource_search_code_name(self):
        for q in ("mixer", "Máy trộn số 1"):
            self.assertEqual(list(self.client.get(self.url("resource"), {"q": q}).context["records"]), [self.resource])

    def test_rate_search_resource_and_work_center(self):
        for q in ("mixer", "Máy trộn số 1", "wc_mix", "Khu vực phối trộn"):
            self.assertEqual(list(self.client.get(self.url("resource_rate"), {"q": q}).context["records"]), [self.rate])

    def test_active_type_and_work_center_filters(self):
        cases = (("work_center", {"active": "false"}, self.inactive_center),
            ("resource", {"is_active": "false"}, self.labor), ("resource", {"resource_type": "MACHINE"}, self.resource),
            ("resource", {"work_center": str(self.center.pk)}, self.resource))
        for resource, filters, record in cases:
            self.assertEqual(list(self.client.get(self.url(resource), filters).context["records"]), [record])

    def test_rate_reference_filters(self):
        for key, value in (("resource", self.resource.pk), ("work_center", self.center.pk), ("resource_type", "MACHINE"),
            ("currency", "VND"), ("rate_uom", self.hour.pk), ("rate_type", "OPERATING"), ("status", "DRAFT")):
            self.assertEqual(list(self.client.get(self.url("resource_rate"), {key: value}).context["records"]), [self.rate])
        self.assertFalse(self.client.get(self.url("resource_rate"), {"currency": "USD"}).context["records"])

    def test_effective_date_status_is_separate_from_record_status(self):
        future = ResourceRate.objects.create(organization=self.company, resource=self.resource, rate_type="OPERATING", amount=2,
            currency_code=self.vnd, per_uom=self.hour, effective_from=self.today + timedelta(days=10))
        expired = ResourceRate.objects.create(organization=self.company, resource=self.resource, rate_type="OPERATING", amount=3,
            currency_code=self.vnd, per_uom=self.hour, effective_from=self.today - timedelta(days=30), effective_to=self.today - timedelta(days=1))
        for code, record in (("EFFECTIVE", self.rate), ("FUTURE", future), ("EXPIRED", expired)):
            response = self.client.get(self.url("resource_rate"), {"effective": code})
            self.assertEqual(list(response.context["records"]), [record])
        self.assertContains(self.client.get(self.url("resource_rate")), "Nháp")
        ResourceRate.objects.filter(pk=self.rate.pk).update(effective_to=self.today)
        self.assertEqual(selectors.rate_queryset(organization=self.company).get(pk=self.rate.pk).date_status, "EFFECTIVE")

    def test_sort_whitelists_and_stable_order(self):
        for resource, filters, first in (("work_center", {"sort": "-code"}, self.inactive_center),
            ("resource", {"sort": "name"}, self.resource), ("resource_rate", {"sort": "-rate"}, self.rate)):
            response = self.client.get(self.url(resource), filters)
            self.assertEqual(response.context["records"][0], first)
        for resource in self.records:
            response = self.client.get(self.url(resource), {"sort": "--code", "per_page": "999"})
            self.assertEqual(response.context["current_sort"], "-effective_from" if resource == "resource_rate" else "code")
            self.assertEqual(response.context["per_page"], 25)

    def test_pagination_and_query_state_all_modules(self):
        WorkCenter.objects.bulk_create([WorkCenter(organization=self.company, code=f"TEST_{i:03}", name="Trung tâm thử") for i in range(61)])
        Resource.objects.bulk_create([Resource(organization=self.company, code=f"TEST_{i:03}", name="Nguồn lực thử", resource_type="MACHINE") for i in range(61)])
        ResourceRate.objects.bulk_create([ResourceRate(organization=self.company, resource=self.resource, rate_type="TEST", amount=i,
            currency_code=self.vnd, per_uom=self.hour, effective_from=self.today) for i in range(61)])
        for resource in self.records:
            params = {"q": "test"} if resource != "resource_rate" else {"rate_type": "TEST"}
            for size, count in ((25, 25), (50, 50), (100, 61)):
                response = self.client.get(self.url(resource), {**params, "per_page": size})
                self.assertEqual(len(response.context["records"]), count)
                self.assertEqual(response.context["page_obj"].paginator.count, 61)
            response = self.client.get(self.url(resource), {**params, "page": 2})
            self.assertEqual(len(response.context["records"]), 25)
            self.assertContains(response, "page=3")
            self.assertContains(response, 'hx-push-url="true"')

    def test_create_assigns_company_and_normalizes(self):
        for resource, model in self.models.items():
            response = self.client.post(self.url(resource, "create"), self.payload(resource, organization=self.other.pk, created_by="00000000-0000-0000-0000-000000000001", status="EFFECTIVE"), follow=True)
            self.assertEqual(response.status_code, 200)
            saved = model.objects.order_by("-pk").first()
            self.assertEqual(saved.organization_id, self.company.pk)
            if resource == "resource_rate":
                self.assertEqual(saved.amount, Decimal("250000.12345678"))
                self.assertEqual(saved.rate_type, "OPERATING")
                self.assertEqual(saved.source_reference, "REF-2026")
                self.assertIsNone(saved.created_by)
                self.assertEqual(saved.status, "DRAFT")
                self.assertContains(response, "Đã tạo đơn giá nguồn lực.")
            else:
                self.assertEqual(saved.code, "WC_NEW" if resource == "work_center" else "RESOURCE_NEW")
                self.assertEqual(saved.name, "Trung tâm mới" if resource == "work_center" else "Nguồn lực mới")
                if resource == "resource":
                    self.assertEqual(saved.metadata, {})

    def test_duplicate_codes_rejected(self):
        for resource in ("work_center", "resource"):
            response = self.client.post(self.url(resource, "create"), self.payload(resource, code=f" {self.records[resource].code.lower()} "))
            self.assertContains(response, "đã tồn tại.")
            self.assertIn("code", response.context["form"].errors)

    def test_duplicate_race_uses_database_constraint_message(self):
        for resource, save, validator in (("work_center", services.save_work_center, "validate_work_center"), ("resource", services.save_resource, "validate_resource")):
            values = self.values(resource)
            values["code"] = self.records[resource].code
            with patch(f"apps.bom.resource_services.{validator}"), self.assertRaisesMessage(ValidationError, "đã tồn tại"):
                save(workspace=self.workspace(), data=values)

    def test_invalid_required_fields_keep_input_and_accessible_errors(self):
        for resource, changes, field in (("work_center", {"code": "", "name": ""}, "code"),
            ("resource", {"code": "", "resource_type": ""}, "resource_type"), ("resource_rate", {"resource": ""}, "resource")):
            response = self.client.post(self.url(resource, "create"), self.payload(resource, **changes))
            self.assertEqual(response.status_code, 200)
            self.assertIn(field, response.context["form"].errors)
            self.assertContains(response, f'id_{field}_errors')
            self.assertContains(response, 'aria-invalid="true"')
            self.assertContains(response, "Vui lòng kiểm tra các trường được đánh dấu.")

    def test_resource_type_matches_database_values(self):
        for code in ("MACHINE", "LABOR", "WORK_CENTER", "SERVICE"):
            form = ResourceForm(self.payload("resource", resource_type=code), workspace=self.workspace())
            self.assertTrue(form.is_valid(), form.errors)
        response = self.client.post(self.url("resource", "create"), self.payload("resource", resource_type="ENERGY"))
        self.assertIn("resource_type", response.context["form"].errors)

    def test_work_center_is_optional_for_resource(self):
        response = self.client.post(self.url("resource", "create"), self.payload("resource", work_center=""))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(Resource.objects.get(code="RESOURCE_NEW").work_center_id)

    def test_capacity_nonnegative_and_requires_uom(self):
        for resource in ("work_center", "resource"):
            for field, value in (("capacity_value", "-1"), ("capacity_uom", "")):
                response = self.client.post(self.url(resource, "create"), self.payload(resource, **{field: value}))
                self.assertIn(field, response.context["form"].errors)
            self.assertTrue(self.forms[resource](self.payload(resource, capacity_value="0"), workspace=self.workspace()).is_valid())
        form = WorkCenterForm(self.payload("work_center", normal_capacity_value="-1"), workspace=self.workspace())
        self.assertFalse(form.is_valid())
        self.assertIn("normal_capacity_value", form.errors)

    def test_amount_zero_allowed_negative_and_invalid_rejected(self):
        for amount in ("-1", "NaN", "Infinity", "abc", "1.123456789", "10000000000000000"):
            response = self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate", amount=amount))
            self.assertIn("amount", response.context["form"].errors)
        response = self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate", amount="0"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ResourceRate.objects.filter(organization=self.company, amount=0).exists())

    def test_rate_required_fields(self):
        for field in ("resource", "rate_type", "amount", "currency_code", "per_uom", "effective_from"):
            response = self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate", **{field: ""}))
            self.assertIn(field, response.context["form"].errors)

    def test_end_date_must_be_strictly_after_start(self):
        for end in (self.today, self.today - timedelta(days=1)):
            response = self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate", effective_to=end.isoformat()))
            self.assertContains(response, "Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực.")
        self.assertEqual(self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate", effective_to="")).status_code, 302)

    def test_per_uom_is_not_assumed_to_be_time(self):
        response = self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate", per_uom=self.kwh.pk))
        self.assertEqual(response.status_code, 302)
        saved = ResourceRate.objects.filter(organization=self.company).latest("pk")
        self.assertEqual(saved.per_uom_id, self.kwh.pk)

    def test_edit_all_models_preserves_metadata_actors_and_created_at(self):
        Resource.objects.filter(pk=self.resource.pk).update(metadata={"legacy": "preserve"})
        ResourceRate.objects.filter(pk=self.rate.pk).update(status="EFFECTIVE")
        for resource, record in self.records.items():
            changes = {"code": record.code, "name": "Tên cập nhật"} if resource != "resource_rate" else {"amount": "230000"}
            response = self.client.post(self.url(resource, "edit", record), self.payload(resource, **changes), follow=True)
            self.assertEqual(response.status_code, 200)
            saved = self.models[resource].objects.get(pk=record.pk)
            self.assertEqual(saved.created_at, record.created_at)
            if resource == "resource_rate":
                self.assertEqual(saved.status, "EFFECTIVE")
                self.assertIsNone(saved.created_by)
            elif resource == "resource":
                self.assertEqual(saved.metadata, {"legacy": "preserve"})
            else:
                self.assertGreater(saved.updated_at, record.updated_at)

    def test_new_dated_rate_preserves_historical_row_and_allows_existing_overlap(self):
        original = ResourceRate.objects.get(pk=self.rate.pk)
        response = self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ResourceRate.objects.filter(organization=self.company).count(), 2)
        saved = ResourceRate.objects.get(pk=self.rate.pk)
        for field in ("amount", "effective_from", "effective_to", "rate_type", "created_at"):
            self.assertEqual(getattr(saved, field), getattr(original, field))

    def test_inactive_and_foreign_choices_not_available_on_create(self):
        self.hour.is_active = False
        self.hour.save()
        self.vnd.is_active = False
        self.vnd.save()
        for resource in self.forms:
            form = self.forms[resource](workspace=self.workspace())
            for field, pk in (("work_center", self.inactive_center.pk), ("work_center", self.other_center.pk),
                ("resource", self.labor.pk), ("resource", self.other_resource.pk), ("capacity_uom", self.hour.pk),
                ("per_uom", self.hour.pk), ("currency_code", "VND")):
                if field in form.fields:
                    self.assertFalse(form.fields[field].queryset.filter(pk=pk).exists())

    def test_inactive_existing_references_retained_for_edit_and_history(self):
        WorkCenter.objects.filter(pk=self.center.pk).update(is_active=False)
        Resource.objects.filter(pk=self.resource.pk).update(is_active=False)
        Uom.objects.filter(pk=self.hour.pk).update(is_active=False)
        Currency.objects.filter(pk=self.vnd.pk).update(is_active=False)
        for resource, record in self.records.items():
            response = self.client.get(self.url(resource, "detail", record))
            self.assertEqual(response.status_code, 200)
            form = self.forms[resource](self.payload(resource, **({"code": record.code} if resource != "resource_rate" else {})), workspace=self.workspace(), instance=record)
            # Resource payload changes to a still-active energy UoM; other fields retain originals.
            self.assertTrue(form.is_valid(), form.errors)

    def test_reference_deactivated_after_form_validation_rejected_in_service(self):
        values = self.values("resource_rate")
        Resource.objects.filter(pk=self.resource.pk).update(is_active=False)
        with self.assertRaisesMessage(ValidationError, "ngừng hoạt động"):
            services.save_resource_rate(workspace=self.workspace(), data=values)
        self.assertEqual(ResourceRate.objects.filter(organization=self.company).count(), 1)

    def test_service_refreshes_stale_units_and_maps_integrity_errors(self):
        values = self.values("work_center")
        Uom.objects.filter(pk=self.hour.pk).update(is_active=False)
        with self.assertRaisesMessage(ValidationError, "ngừng hoạt động"):
            services.save_work_center(workspace=self.workspace(), data=values)
        Uom.objects.filter(pk=self.hour.pk).update(is_active=True)
        with patch.object(WorkCenter, "save", side_effect=IntegrityError("raw PostgreSQL details")), self.assertRaisesMessage(ValidationError, "Vui lòng kiểm tra và thử lại"):
            services.save_work_center(workspace=self.workspace(), data=values)

    def test_inconsistent_legacy_resource_reference_cannot_be_used(self):
        Resource.objects.filter(pk=self.resource.pk).update(work_center=self.other_center)
        self.assertEqual(self.client.get(self.url("resource", "detail", self.resource)).status_code, 404)
        form = ResourceRateForm(workspace=self.workspace())
        self.assertFalse(form.fields["resource"].queryset.filter(pk=self.resource.pk).exists())
        values = {
            "resource": self.resource, "rate_type": "TEST", "amount": Decimal(1), "currency_code": self.vnd,
            "per_uom": self.hour, "effective_from": self.today, "effective_to": None,
        }
        with self.assertRaisesMessage(ValidationError, "Danh mục không còn tồn tại"):
            services.save_resource_rate(workspace=self.workspace(), data=values)

    def test_foreign_and_missing_records_do_not_leak(self):
        for resource, record in (("work_center", self.other_center), ("resource", self.other_resource), ("resource_rate", self.other_rate)):
            for action in ("detail", "edit"):
                self.assertEqual(self.client.get(self.url(resource, action, record)).status_code, 404)
            self.assertEqual(self.client.get(reverse(f"bom:{resource}_detail", args=[99999999999999999999])).status_code, 404)
        response = self.client.post(self.url("resource_rate", "create"), self.payload("resource_rate", resource=self.other_resource.pk))
        self.assertIn("resource", response.context["form"].errors)
        response = self.client.post(self.url("resource", "create"), self.payload("resource", work_center=self.other_center.pk))
        self.assertIn("work_center", response.context["form"].errors)

    def test_empty_states_and_htmx_history_restore(self):
        for resource in self.records:
            response = self.client.get(self.url(resource), {"q": "NONE"}, HTTP_HX_REQUEST="true")
            self.assertContains(response, "Không có kết quả phù hợp.")
            self.assertNotContains(response, "<!doctype")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
            full = self.client.get(self.url(resource), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
            self.assertContains(full, "<!doctype")
        ResourceRate.objects.filter(organization=self.company).delete()
        Resource.objects.filter(organization=self.company).delete()
        WorkCenter.objects.filter(organization=self.company).delete()
        for resource, label in (("work_center", "trung tâm sản xuất"), ("resource", "nguồn lực sản xuất"), ("resource_rate", "đơn giá nguồn lực")):
            self.assertContains(self.client.get(self.url(resource)), f"Chưa có {label}.")

    def test_htmx_form_errors_and_success_redirect(self):
        for resource in self.records:
            response = self.client.post(self.url(resource, "create"), {}, HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_form_content.html")
            self.assertNotContains(response, "<!doctype")
            response = self.client.post(self.url(resource, "create"), self.payload(resource), HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertIn("HX-Redirect", response.headers)

    def test_csrf_and_post_only_mutations(self):
        client = Client(enforce_csrf_checks=True)
        for resource in self.records:
            self.assertEqual(client.post(self.url(resource, "create"), self.payload(resource)).status_code, 403)
            response = client.get(self.url(resource, "create"))
            self.assertEqual(response.status_code, 200)
            token = client.cookies["csrftoken"].value
            self.assertEqual(client.post(self.url(resource, "create"), self.payload(resource, csrfmiddlewaretoken=token)).status_code, 302)
            self.assertEqual(self.client.post(self.url(resource)).status_code, 405)

    def test_internal_policy_enforced_centrally(self):
        request = RequestFactory().get(self.url("work_center", "create"))
        request._costing_workspace = Workspace(self.company, replace(INTERNAL_ACCESS, can_create_work_center=False))
        with self.assertRaises(PermissionDenied):
            work_center_create(request)
        with self.assertRaises(PermissionDenied):
            services.save_work_center(workspace=request._costing_workspace, data={})

    def test_detail_resource_history_is_paginated_optimized_and_htmx(self):
        ResourceRate.objects.bulk_create([ResourceRate(organization=self.company, resource=self.resource, rate_type="HISTORY", amount=i,
            currency_code=self.vnd, per_uom=self.hour, effective_from=self.today) for i in range(30)])
        detail_url = self.url("resource", "detail", self.resource)
        response = self.client.get(detail_url)
        self.assertContains(response, "Lịch sử đơn giá")
        self.assertEqual(response.context["rate_history"]["page_obj"].paginator.count, 31)
        self.assertEqual(len(response.context["rate_history"]["records"]), 25)
        partial = self.client.get(detail_url, {"page": 2}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="reference-data-table")
        self.assertEqual(len(partial.context["records"]), 6)
        self.assertNotContains(partial, "<!doctype")
        self.assertContains(partial, "bom/resource-rates/")
        full = self.client.get(detail_url, {"page": 2}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="reference-data-table", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(full, "Lịch sử đơn giá")
        self.assertContains(full, "<!doctype")

    def test_work_center_resources_bounded_and_linked(self):
        Resource.objects.bulk_create([Resource(organization=self.company, code=f"WC_{i}", name="Nguồn lực trung tâm", resource_type="MACHINE", work_center=self.center) for i in range(12)])
        response = self.client.get(self.url("work_center", "detail", self.center))
        self.assertEqual(len(response.context["center_resources"]), 10)
        self.assertContains(response, f'?work_center={self.center.pk}')

    def test_no_n_plus_one_in_selectors(self):
        for selector, references in ((selectors.work_center_queryset, ("capacity_uom",)),
            (selectors.resource_queryset, ("work_center", "capacity_uom")), (selectors.rate_queryset, ("resource", "currency_code", "per_uom"))):
            with self.assertNumQueries(1):
                for record in selector(organization=self.company):
                    for field in references:
                        reference = getattr(record, field)
                        if reference:
                            getattr(reference, "name", None)
                    if isinstance(record, ResourceRate):
                        record.resource.work_center.name

    def test_rendered_query_count_does_not_grow_with_rows(self):
        for resource in self.records:
            with CaptureQueriesContext(connection) as baseline:
                self.client.get(self.url(resource))
            model = self.models[resource]
            if resource == "resource_rate":
                model.objects.bulk_create([model(organization=self.company, resource=self.resource, rate_type="TEST", amount=i,
                    currency_code=self.vnd, per_uom=self.hour, effective_from=self.today) for i in range(25)])
            else:
                extras = {"resource_type": "MACHINE", "work_center": self.center} if resource == "resource" else {}
                model.objects.bulk_create([model(organization=self.company, code=f"QUERY_{i}", name="Kiểm tra truy vấn", capacity_uom=self.hour, **extras) for i in range(25)])
            with CaptureQueriesContext(connection) as populated:
                response = self.client.get(self.url(resource))
            self.assertEqual(len(populated), len(baseline), resource)
            self.assertEqual(len(response.context["records"]), 25)

    def test_database_checks_remain_last_line_of_protection(self):
        for model, record, changes in ((WorkCenter, self.center, {"capacity_value": -1}),
            (Resource, self.resource, {"resource_type": "ENERGY"}), (ResourceRate, self.rate, {"amount": -1}),
            (ResourceRate, self.rate, {"effective_to": self.rate.effective_from}), (ResourceRate, self.rate, {"status": "LOCKED"})):
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.filter(pk=record.pk).update(**changes)

    def test_vietnamese_labels_no_auth_or_organization_fields(self):
        for resource in self.records:
            response = self.client.get(self.url(resource, "create"))
            form = response.context["form"]
            self.assertNotIn("organization", form.fields)
            self.assertNotIn("metadata", form.fields)
            self.assertNotIn("status", form.fields)
            for label in (">Create<", ">Edit<", ">Save<", ">Search<", ">Status<", ">Login<", ">Logout<"):
                self.assertNotContains(response, label)
        self.assertContains(self.client.get(self.url("resource")), "Máy móc")
        self.assertContains(self.client.get(self.url("resource")), "Nhân công")
