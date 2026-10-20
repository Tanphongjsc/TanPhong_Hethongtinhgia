"""Publish existing BOM/packaging definitions without changing costing rules."""
from datetime import timedelta
from decimal import Decimal
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import (
    Item, Organization, PackagingConfig, PackagingConfigVersion, PackagingLine,
    Product, Recipe, RecipeVersion, RecipeLine, Uom, UomCategory, UomConversion,
)
from apps.master_data.access import Workspace
from . import services, packaging_services


class DefinitionActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="ACTIVATION", name="Công ty kiểm thử")
        cls.day = timezone.localdate()
        cls.category = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        cls.unit = Uom.objects.create(category=cls.category, code="PC", name="Cái", symbol="cái")
        cls.other_unit = Uom.objects.create(category=cls.category, code="BOX", name="Hộp", symbol="hộp")
        cls.product = Product.objects.create(organization=cls.company, code="COFFEE", name="Cà phê", costing_uom=cls.unit)
        cls.material = Item.objects.create(organization=cls.company, code="BEAN", name="Nguyên liệu", item_type="RAW_MATERIAL", base_uom=cls.unit)
        cls.packaging_item = Item.objects.create(organization=cls.company, code="BAG", name="Bao bì", item_type="PACKAGING", base_uom=cls.unit)
        cls.recipe = Recipe.objects.create(organization=cls.company, product=cls.product, code="BOM", name="Định mức")
        cls.bom_version = RecipeVersion.objects.create(recipe=cls.recipe, version_no=1, output_qty=Decimal(1), output_uom=cls.unit,
            effective_from=cls.day, effective_to=cls.day + timedelta(days=30))
        cls.bom_line = RecipeLine.objects.create(recipe_version=cls.bom_version, component_item=cls.material, qty=Decimal("0.018"), uom=cls.unit)
        cls.config = PackagingConfig.objects.create(organization=cls.company, product=cls.product, code="PACK", name="Cấu hình bao bì")
        cls.pack_version = PackagingConfigVersion.objects.create(packaging_config=cls.config, version_no=1,
            effective_from=cls.day, effective_to=cls.day + timedelta(days=30))
        cls.pack_line = PackagingLine.objects.create(packaging_config_version=cls.pack_version, packaging_item=cls.packaging_item,
            level_code="PRIMARY", qty=Decimal("0.08333333"), uom=cls.unit)

    def setUp(self):
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        company.enable()
        self.addCleanup(company.disable)
        self.workspace = Workspace(self.company)
        self.definitions = (
            SimpleNamespace(name="bom", parent=self.recipe, version=self.bom_version, line=self.bom_line, module=services, parent_arg="recipe"),
            SimpleNamespace(name="packaging", parent=self.config, version=self.pack_version, line=self.pack_line, module=packaging_services, parent_arg="config"),
        )

    def url(self, definition, action="version_activate"):
        return reverse(f"bom:{definition.name}_{action}", args=[definition.parent.pk, definition.version.pk])

    def activate(self, definition):
        return definition.module.activate_version(workspace=self.workspace, version=definition.version, **{definition.parent_arg: definition.parent})

    def assert_draft(self, definition):
        definition.version.refresh_from_db()
        self.assertEqual(definition.version.status, "DRAFT")
        self.assertIsNone(definition.version.content_hash)

    def test_post_activates_only_status_and_hash_and_is_idempotent(self):
        for definition in self.definitions:
            with self.subTest(module=definition.name):
                before = type(definition.version).objects.values().get(pk=definition.version.pk)
                line_before = type(definition.line).objects.values().get(pk=definition.line.pk)
                self.assertEqual(self.client.get(self.url(definition)).status_code, 405)
                response = self.client.post(self.url(definition))
                self.assertRedirects(response, self.url(definition, "version_detail"))
                definition.version.refresh_from_db()
                self.assertEqual(definition.version.status, "EFFECTIVE")
                self.assertEqual(len(definition.version.content_hash), 64)
                after = type(definition.version).objects.values().get(pk=definition.version.pk)
                self.assertEqual({k: v for k, v in after.items() if k not in ("status", "content_hash")},
                                 {k: v for k, v in before.items() if k not in ("status", "content_hash")})
                self.assertEqual(type(definition.line).objects.values().get(pk=definition.line.pk), line_before)
                self.assertEqual(self.activate(definition).content_hash, definition.version.content_hash)
                self.assertIsNone(definition.version.approved_by)

    def test_draft_button_and_effective_version_immutable_but_clone_allowed(self):
        for definition in self.definitions:
            page = self.client.get(self.url(definition, "version_detail"))
            self.assertContains(page, 'id="activate-' + definition.name + '-form"')
            self.activate(definition)
            definition.version.refresh_from_db()
            page = self.client.get(self.url(definition, "version_detail"))
            self.assertNotContains(page, 'id="activate-' + definition.name + '-form"')
            with self.assertRaisesMessage(ValidationError, "Không thể chỉnh sửa"):
                definition.module.remove_line(workspace=self.workspace, version=definition.version, instance=definition.line,
                                              **{definition.parent_arg: definition.parent})
            fields = ("output_qty", "output_uom", "yield_rate", "effective_from", "effective_to", "change_reason") if definition.name == "bom" else (
                "effective_from", "effective_to", "gross_weight", "weight_uom", "length", "width", "height", "dimension_uom", "change_reason")
            clone = definition.module.create_version(workspace=self.workspace, source=definition.version,
                data={field: getattr(definition.version, field) for field in fields}, **{definition.parent_arg: definition.parent})
            self.assertEqual(clone.status, "DRAFT")
            self.assertEqual(clone.version_no, 2)
            relation = "recipeline_set" if definition.name == "bom" else "packagingline_set"
            self.assertEqual(getattr(clone, relation).get().qty, definition.line.qty)
            self.assertEqual(getattr(definition.version, relation).get().pk, definition.line.pk)

    def test_missing_effective_date_returns_readable_error_full_and_htmx(self):
        for definition in self.definitions:
            type(definition.version).objects.filter(pk=definition.version.pk).update(effective_from=None, effective_to=None)
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                response = self.client.post(self.url(definition), **headers)
                self.assertContains(response, "Vui lòng nhập ngày bắt đầu hiệu lực")
                self.assertContains(response, 'role="alert"')
                if headers:
                    self.assertNotContains(response, "<!DOCTYPE")
                self.assert_draft(definition)

    def test_empty_definition_not_published(self):
        for definition in self.definitions:
            definition.line.delete()
            with self.assertRaisesMessage(ValidationError, "chưa có thành phần"):
                self.activate(definition)
            self.assert_draft(definition)

    def test_inactive_items_units_categories_parent_and_product_rejected(self):
        for definition in self.definitions:
            item = self.material if definition.name == "bom" else self.packaging_item
            for record in (item, self.unit, self.category, definition.parent, self.product):
                type(record).objects.filter(pk=record.pk).update(is_active=False)
                with self.subTest(module=definition.name, model=type(record).__name__):
                    with self.assertRaises(ValidationError):
                        self.activate(definition)
                    self.assert_draft(definition)
                type(record).objects.filter(pk=record.pk).update(is_active=True)

    def test_conversion_rechecked_at_effective_date(self):
        for definition in self.definitions:
            type(definition.line).objects.filter(pk=definition.line.pk).update(uom=self.other_unit)
            with self.assertRaisesMessage(ValidationError, "không tìm thấy quy đổi"):
                self.activate(definition)
            self.assert_draft(definition)
        UomConversion.objects.create(organization=self.company, from_uom=self.other_unit, to_uom=self.unit,
            factor=Decimal(12), effective_from=self.day)
        for definition in self.definitions:
            self.assertEqual(self.activate(definition).status, "EFFECTIVE")
    def test_overlap_same_product_even_different_recipe_and_inclusive_boundary(self):
        for definition in self.definitions:
            self.activate(definition)
            fields = {field: getattr(definition.version, field) for field in (
                ("output_qty", "output_uom", "yield_rate") if definition.name == "bom" else ())}
            # A different Recipe for the same Product is also a competing source.
            parent = (Recipe.objects.create(organization=self.company, product=self.product, code="OTHER_BOM", name="Định mức khác")
                      if definition.name == "bom" else definition.parent)
            next_version = type(definition.version).objects.create(**{definition.parent_arg if definition.name == "bom" else "packaging_config": parent},
                version_no=2, effective_from=definition.version.effective_to, **fields)
            line_values = {f.attname: getattr(definition.line, f.attname) for f in definition.line._meta.fields if not f.primary_key}
            line_values["recipe_version_id" if definition.name == "bom" else "packaging_config_version_id"] = next_version.pk
            type(definition.line).objects.create(**line_values)
            candidate = SimpleNamespace(**{**definition.__dict__, "parent": parent, "version": next_version})
            with self.assertRaisesMessage(ValidationError, "chồng khoảng ngày"):
                self.activate(candidate)
            self.assert_draft(candidate)
            type(next_version).objects.filter(pk=next_version.pk).update(effective_from=definition.version.effective_to + timedelta(days=1))
            self.assertEqual(self.activate(candidate).status, "EFFECTIVE")
            definition.version.refresh_from_db()
            self.assertEqual(definition.version.status, "EFFECTIVE")
            self.assertEqual(definition.version.effective_to, self.day + timedelta(days=30))

    def test_approved_version_not_silently_rewritten(self):
        for definition in self.definitions:
            type(definition.version).objects.filter(pk=definition.version.pk).update(status="APPROVED")
            with self.assertRaisesMessage(ValidationError, "đã được chốt"):
                self.activate(definition)
            definition.version.refresh_from_db()
            self.assertEqual(definition.version.status, "APPROVED")

    def test_csrf_required_then_htmx_redirect(self):
        client = Client(enforce_csrf_checks=True)
        for definition in self.definitions:
            self.assertEqual(client.post(self.url(definition)).status_code, 403)
            client.get(self.url(definition, "version_detail"))
            response = client.post(self.url(definition), HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value, HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["HX-Redirect"], self.url(definition, "version_detail"))

    def test_mismatched_parent_or_workspace_rejected(self):
        other = Organization.objects.create(code="OTHER", name="Công ty khác")
        for definition in self.definitions:
            with self.assertRaises(ValidationError):
                definition.module.activate_version(workspace=Workspace(other), version=definition.version, **{definition.parent_arg: definition.parent})
            foreign_parent = type(definition.parent).objects.create(organization=self.company, product=self.product, code="MISMATCH", name="Khác")
            url = reverse(f"bom:{definition.name}_version_activate", args=[foreign_parent.pk, definition.version.pk])
            self.assertEqual(self.client.post(url).status_code, 404)
            self.assert_draft(definition)

    def test_existing_write_hook_enforced(self):
        for definition in self.definitions:
            with patch.object(definition.module, "require_write_access", side_effect=PermissionDenied):
                self.assertEqual(self.client.post(self.url(definition)).status_code, 403)
            self.assert_draft(definition)

    def test_activation_queries_do_not_grow_per_line_or_read_prices_memberships(self):
        counts = []
        for definition in self.definitions:
            extra = {f.attname: getattr(definition.line, f.attname) for f in definition.line._meta.fields if not f.primary_key}
            type(definition.line).objects.bulk_create([type(definition.line)(**extra) for _ in range(20)])
            with CaptureQueriesContext(connection) as queries:
                self.activate(definition)
            counts.append(len(queries))
            self.assertFalse(any("supplier_price" in q["sql"] or "organization_member" in q["sql"] for q in queries))
            self.assertLess(len(queries), 30)
        self.assertLess(abs(counts[0] - counts[1]), 8)

    def test_packaging_actions_inside_last_table_cell(self):
        class Rows(HTMLParser):
            def __init__(self):
                super().__init__()
                self.cells = None
                self.rows = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "tr": self.cells = []
                elif tag == "td" and self.cells is not None: self.cells.append([])
                elif tag == "a" and self.cells:
                    self.cells[-1].append(attrs.get("href"))
            def handle_endtag(self, tag):
                if tag == "tr" and self.cells:
                    self.rows.append(self.cells)
                    self.cells = None
        response = self.client.get(reverse("bom:packaging_list"), HTTP_HX_REQUEST="true")
        parser = Rows()
        parser.feed(response.content.decode())
        row = parser.rows[0]
        self.assertEqual(len(row), 9)
        self.assertIn(reverse("bom:packaging_detail", args=[self.config.pk]), row[-1])
        self.assertIn(reverse("bom:packaging_edit", args=[self.config.pk]), row[-1])
        self.assertNotIn(reverse("bom:packaging_edit", args=[self.config.pk]), row[0])


class ActivationCostingIntegrationTests(TestCase):
    def test_published_definitions_work_with_existing_costing_resolver(self):
        from apps.costing.run_test_data import golden_data, request_data
        from apps.costing.run_services import create_run
        data = golden_data()
        workspace = Workspace(data.company)
        # Only the other source fixtures are sealed here. BOM and packaging use
        # the actual newly exposed services, never a test-only status update.
        for record in (data.routing_version, data.scheme_version):
            type(record).objects.filter(pk=record.pk).update(status="EFFECTIVE")
        services.activate_version(workspace=workspace, recipe=data.recipe, version=data.recipe_version)
        packaging_services.activate_version(workspace=workspace, config=data.packaging, version=data.packaging_version)
        run = create_run(workspace=workspace, data=request_data(data), idempotency_key=uuid.uuid4())
        self.assertEqual(run.run_status, "LOCKED", run.context_jsonb)
        self.assertEqual(run.full_cost, Decimal("60000"))
        for record in (data.recipe_version, data.packaging_version):
            self.assertIn(f"{record._meta.db_table}:{record.pk}", run.version_snapshot_jsonb["sources"])