"""Explicit supplier-price publication with existing validation and costing."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, IntegrityError
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Currency, Item, Organization, Supplier, SupplierPrice, Uom, UomCategory
from .access import Workspace
from . import services


class SupplierPriceActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="PRICE_ACT", name="Công ty kiểm thử")
        cls.currency = Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
        category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        cls.kg = Uom.objects.create(category=category, code="KG", name="Kilôgam", symbol="kg")
        cls.supplier = Supplier.objects.create(organization=cls.company, code="SUP", name="Nhà cung cấp")
        cls.item = Item.objects.create(organization=cls.company, code="SUGAR", name="Đường", item_type="RAW_MATERIAL", base_uom=cls.kg)
        cls.price = SupplierPrice.objects.create(organization=cls.company, supplier=cls.supplier, item=cls.item,
            price_uom=cls.kg, currency_code=cls.currency, unit_price=Decimal("19200.12345678"),
            effective_from=timezone.localdate(), source_reference="Báo giá gốc")

    def setUp(self):
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        company.enable()
        self.addCleanup(company.disable)
        self.workspace = Workspace(self.company)
        self.url = reverse("master_data:supplier_price_activate", args=[self.price.pk])
        self.detail = reverse("master_data:supplier_price_detail", args=[self.price.pk])

    def activate(self):
        return services.activate_supplier_price(workspace=self.workspace, instance=self.price)

    def test_post_only_and_confirmation_button_on_draft(self):
        page = self.client.get(self.detail)
        self.assertContains(page, 'id="activate-supplier-price-form"')
        self.assertContains(page, 'name="csrfmiddlewaretoken"')
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.price.refresh_from_db()
        self.assertEqual(self.price.status, "DRAFT")

    def test_activation_changes_only_status_and_repeated_submit_is_safe(self):
        before = SupplierPrice.objects.values().get(pk=self.price.pk)
        response = self.client.post(self.url)
        self.assertRedirects(response, self.detail)
        after = SupplierPrice.objects.values().get(pk=self.price.pk)
        self.assertEqual(after.pop("status"), "EFFECTIVE")
        before.pop("status")
        self.assertEqual(before, after)
        self.assertIsNone(self.activate().created_by)
        self.assertContains(self.client.get(self.detail), "Đang hiệu lực")
        self.assertNotContains(self.client.get(self.detail), 'id="activate-supplier-price-form"')
        self.assertEqual(SupplierPrice.objects.count(), 1)

    def test_current_active_references_required_even_with_stale_instance(self):
        for record in (self.supplier, self.item, self.currency, self.kg):
            with self.subTest(reference=type(record).__name__):
                type(record).objects.filter(pk=record.pk).update(is_active=False)
                with self.assertRaisesMessage(ValidationError, "đã ngừng hoạt động"):
                    self.activate()
                self.price.refresh_from_db()
                self.assertEqual(self.price.status, "DRAFT")
                type(record).objects.filter(pk=record.pk).update(is_active=True)

    def test_validation_error_stays_on_detail_full_and_htmx(self):
        Supplier.objects.filter(pk=self.supplier.pk).update(is_active=False)
        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            response = self.client.post(self.url, **headers)
            self.assertContains(response, "Không thể kích hoạt giá nhà cung cấp.")
            self.assertContains(response, "đã ngừng hoạt động")
            self.assertContains(response, 'role="alert"')
            if headers:
                self.assertNotContains(response, "<!DOCTYPE")
            self.price.refresh_from_db()
            self.assertEqual(self.price.status, "DRAFT")

    def test_csrf_required_and_htmx_success_redirect(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url).status_code, 403)
        client.get(self.detail)
        response = client.post(self.url, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], self.detail)

    def test_approved_and_in_review_can_activate_without_user_workflow(self):
        for status in ("APPROVED", "IN_REVIEW"):
            SupplierPrice.objects.filter(pk=self.price.pk).update(status=status)
            self.assertEqual(self.activate().status, "EFFECTIVE")

    def test_retired_price_requires_new_record(self):
        SupplierPrice.objects.filter(pk=self.price.pk).update(status="RETIRED")
        self.assertNotContains(self.client.get(self.detail), 'id="activate-supplier-price-form"')
        response = self.client.post(self.url)
        self.assertContains(response, "Không thể kích hoạt giá đã ngừng hiệu lực")
        self.price.refresh_from_db()
        self.assertEqual(self.price.status, "RETIRED")

    def test_dates_zero_price_and_tax_are_preserved_no_new_costing_policy(self):
        start = timezone.localdate() + timedelta(days=10)
        SupplierPrice.objects.filter(pk=self.price.pk).update(unit_price=0, min_qty=0,
            effective_from=start, effective_to=start + timedelta(days=20), tax_inclusive=True, tax_rate=Decimal("0.1"))
        saved = self.activate()
        self.assertEqual(saved.unit_price, Decimal(0))
        self.assertEqual(saved.effective_from, start)
        self.assertEqual(saved.tax_rate, Decimal("0.1"))
        self.assertTrue(saved.tax_inclusive)
        # Tax resolution remains the costing engine's existing responsibility.

    def test_other_quotes_dates_and_existing_edit_policy_unchanged(self):
        other = SupplierPrice.objects.create(organization=self.company, supplier=self.supplier, item=self.item,
            price_uom=self.kg, currency_code=self.currency, unit_price=18000, status="EFFECTIVE",
            effective_from=self.price.effective_from - timedelta(days=30))
        before = SupplierPrice.objects.values().get(pk=other.pk)
        self.activate()
        self.assertEqual(SupplierPrice.objects.values().get(pk=other.pk), before)
        self.price.refresh_from_db()
        values = {field: getattr(self.price, field) for field in services.SUPPLIER_PRICE_FIELDS}
        values["unit_price"] = Decimal(20000)
        saved = services.save_supplier_price(workspace=self.workspace, data=values, instance=self.price)
        self.assertEqual(saved.status, "EFFECTIVE")
        self.assertEqual(saved.unit_price, Decimal(20000))
        self.assertEqual(SupplierPrice.objects.values().get(pk=other.pk), before)

    def test_scope_and_existing_internal_write_hook_enforced(self):
        other = Organization.objects.create(code="OTHER", name="Khác")
        with self.assertRaisesMessage(ValidationError, "Không tìm thấy"):
            services.activate_supplier_price(workspace=Workspace(other), instance=self.price)
        with patch("apps.master_data.views.require_access", return_value=Workspace(other)):
            self.assertEqual(self.client.post(self.url).status_code, 404)
        denied = Workspace(self.company, replace(self.workspace.permissions, can_edit_supplier_price=False))
        with self.assertRaises(PermissionDenied):
            services.activate_supplier_price(workspace=denied, instance=self.price)
        with patch("apps.master_data.access.get_workspace", return_value=denied):
            self.assertNotContains(self.client.get(self.detail), 'id="activate-supplier-price-form"')
            self.assertEqual(self.client.post(self.url).status_code, 403)

    def test_integrity_error_is_user_friendly_and_rolls_back(self):
        with patch.object(SupplierPrice, "save", side_effect=IntegrityError("raw SQL must not leak")):
            response = self.client.post(self.url)
        self.assertContains(response, "Không thể kích hoạt giá nhà cung cấp")
        self.assertNotContains(response, "raw SQL")
        self.price.refresh_from_db()
        self.assertEqual(self.price.status, "DRAFT")

    def test_no_membership_or_costing_execution_during_activation(self):
        with CaptureQueriesContext(connection) as queries:
            self.activate()
        self.assertFalse(any("organization_member" in row["sql"] or "costing_run" in row["sql"] for row in queries))
        self.assertLess(len(queries), 18)


class SupplierPriceActivationCostingTests(TestCase):
    def test_failed_run_preserved_new_run_uses_activated_prices(self):
        from apps.costing.run_test_data import golden_data, seal, request_data
        from apps.costing.run_services import create_run
        data = golden_data()
        workspace = Workspace(data.company)
        seal(data)
        SupplierPrice.objects.filter(pk__in=[price.pk for price in data.prices]).update(status="DRAFT")
        failed = create_run(workspace=workspace, data=request_data(data), idempotency_key=uuid.uuid4())
        self.assertEqual(failed.run_status, "FAILED")
        self.assertEqual(failed.context_jsonb["errors"][0]["code"], "MISSING_PRICE")
        for price in data.prices:
            services.activate_supplier_price(workspace=workspace, instance=price)
        result = create_run(workspace=workspace, data=request_data(data), idempotency_key=uuid.uuid4())
        self.assertEqual(result.run_status, "LOCKED", result.context_jsonb)
        self.assertEqual(result.full_cost, Decimal(60000))
        failed.refresh_from_db()
        self.assertEqual(failed.run_status, "FAILED")
        self.assertIsNone(failed.full_cost)
