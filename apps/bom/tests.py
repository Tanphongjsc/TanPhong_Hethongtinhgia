from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Item, Organization, Product, Recipe, RecipeLine, RecipeVersion, Sku, Uom, UomCategory, UomConversion
from apps.master_data.access import get_workspace
from apps.master_data.test_vietnamese_ui import VisibleText
from . import selectors, services
from .constants import LINE_FIELDS, VERSION_FIELDS
from .forms import RecipeForm, RecipeLineForm, RecipeVersionForm


class BomTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="BOM_COMPANY", name="Công ty nội bộ")
        cls.other = Organization.objects.create(code="OTHER", name="Công ty khác")
        mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        count = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        cls.kg = Uom.objects.create(category=mass, code="KG", name="Kilôgam", symbol="kg")
        cls.g = Uom.objects.create(category=mass, code="G", name="Gam", symbol="g")
        cls.pack = Uom.objects.create(category=count, code="PACK", name="Gói", symbol="gói")
        cls.item = Item.objects.create(organization=cls.company, code="COFFEE", name="Cà phê nguyên liệu", item_type="RAW_MATERIAL", base_uom=cls.kg)
        cls.other_item = Item.objects.create(organization=cls.other, code="SECRET", name="Vật tư công ty khác", item_type="RAW_MATERIAL", base_uom=cls.kg)
        cls.product = Product.objects.create(organization=cls.company, code="CAPPUCCINO", name="Cà phê Cappuccino", costing_uom=cls.kg)
        cls.other_product = Product.objects.create(organization=cls.other, code="OTHER_PRODUCT", name="Sản phẩm khác", costing_uom=cls.kg)
        cls.sku = Sku.objects.create(organization=cls.company, product=cls.product, code="CAP_25G", name="Cappuccino quy cách 25g", sales_uom=cls.pack, net_quantity=25, net_quantity_uom=cls.g)
        cls.recipe = Recipe.objects.create(organization=cls.company, product=cls.product, code="BOM_CAP", name="Định mức Cappuccino", description="Mô tả định mức")
        cls.foreign = Recipe.objects.create(organization=cls.other, product=cls.other_product, code="SECRET_BOM", name="Định mức khác")
        cls.today = timezone.localdate()
        cls.version = RecipeVersion.objects.create(recipe=cls.recipe, version_no=1, output_qty=Decimal("100"), output_uom=cls.kg,
            yield_rate=Decimal("0.98"), effective_from=cls.today - timedelta(days=1), effective_to=cls.today + timedelta(days=20))
        cls.foreign_version = RecipeVersion.objects.create(recipe=cls.foreign, version_no=1, output_qty=1, output_uom=cls.kg)
        cls.line = RecipeLine.objects.create(recipe_version=cls.version, component_item=cls.item, qty=Decimal("0.40000001"), uom=cls.kg,
            scrap_rate=Decimal("0.02"), operation_code="MIX_1", substitute_group="A", is_optional=True, display_order=10, notes="Ghi chú nguồn")

    def setUp(self):
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        company.enable()
        self.addCleanup(company.disable)

    def url(self, action="list", *, recipe=None, version=None, line=None):
        args = [] if action in ("list", "create") else [(recipe or self.recipe).pk]
        if action in ("version_detail", "version_edit", "line_create", "line_edit", "line_remove"):
            args.append((version or self.version).pk)
        if action in ("line_edit", "line_remove"):
            args.append((line or self.line).pk)
        return reverse(f"bom:bom_{action}", args=args)

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url()))

    def recipe_payload(self, **changes):
        data = dict(product=str(self.product.pk), code=" bom_new ", name=" Định mức mới ", description=" Mô tả mới ", is_active="on",
            **{f"initial-{field}": value for field, value in self.version_payload().items()})
        data.update(changes)
        return data

    def version_payload(self, **changes):
        data = dict(output_qty="100.00000001", output_uom=str(self.kg.pk), yield_rate="98.123456",
            effective_from=self.today.isoformat(), effective_to=(self.today + timedelta(days=90)).isoformat(), change_reason=" Thay đổi định mức ")
        data.update(changes)
        return data

    def line_payload(self, **changes):
        data = dict(component_item=str(self.item.pk), qty="0.50000001", uom=str(self.kg.pk), scrap_rate="2.123456",
            operation_code=" MIX_2 ", substitute_group=" B ", is_optional="on", display_order="20", notes=" Thành phần mới ")
        data.update(changes)
        return data

    def version_data(self, **changes):
        form = RecipeVersionForm(self.version_payload(**changes), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def line_data(self, **changes):
        form = RecipeLineForm(self.line_payload(**changes), workspace=self.workspace(), version=self.version)
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def conversion(self, **changes):
        data = dict(organization=self.company, from_uom=self.g, to_uom=self.kg, factor=Decimal("0.001"), effective_from=self.today - timedelta(days=100))
        data.update(changes)
        return UomConversion.objects.create(**data)

    def test_anonymous_list_detail_without_auth_or_costing_queries(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(list(response.context["records"]), [self.recipe])
            self.assertContains(response, 'href="/bom/" aria-current="page"')
            self.assertContains(response, 'aria-current="page"', count=1)
            for action in ("detail", "edit", "version_list", "version_create", "version_detail", "version_edit", "line_create", "line_edit", "line_remove"):
                page = self.client.get(self.url(action))
                self.assertEqual(page.status_code, 200)
                self.assertContains(page, 'href="/bom/" aria-current="page"', count=1)
                current_sections = [title for title, items, expanded in page.context["sidebar_sections"] if expanded]
                self.assertEqual(current_sections, ["SẢN XUẤT"])
        self.assertFalse(any("organization_member" in query["sql"] or "supplier_price" in query["sql"] for query in queries))
        self.assertNotIn("sessionid", response.cookies)

    def test_search_recipe_product_and_sku_without_duplicate_rows(self):
        Sku.objects.create(organization=self.company, product=self.product, code="CAP_OTHER", name="Cappuccino khác", sales_uom=self.pack, net_quantity=1, net_quantity_uom=self.kg)
        for term in ("bom_cap", "Định mức Cappuccino", "cappuccino", "Cà phê Cappuccino", "cap_25g", "quy cách 25g"):
            with self.subTest(term=term):
                response = self.client.get(self.url(), {"q": term})
                self.assertEqual(list(response.context["records"]), [self.recipe])

    def test_filters_product_sku_latest_status_date_active(self):
        for filters in ({"product": self.product.pk}, {"sku": self.sku.pk}, {"status": "DRAFT"}, {"effective": "EFFECTIVE"}, {"active": "true"}):
            self.assertEqual(list(self.client.get(self.url(), filters).context["records"]), [self.recipe])
        for filters in ({"product": self.other_product.pk}, {"status": "APPROVED"}, {"effective": "EXPIRED"}, {"active": "false"}):
            self.assertEqual(list(self.client.get(self.url(), filters).context["records"]), [])
        for parameter in ("product", "sku"):
            for value in ("bad", "9" * 100, "-1", "１２"):
                self.assertEqual(list(self.client.get(self.url(), {parameter: value}).context["records"]), [])
        inconsistent = Sku.objects.create(organization=self.other, product=self.product, code="BAD_SKU", name="SKU không đúng công ty", sales_uom=self.pack, net_quantity=1, net_quantity_uom=self.kg)
        self.assertEqual(list(self.client.get(self.url(), {"sku": inconsistent.pk}).context["records"]), [])

    def test_latest_version_is_displayed_not_implicitly_effective(self):
        RecipeVersion.objects.create(recipe=self.recipe, version_no=2, output_qty=200, output_uom=self.pack, yield_rate=1)
        response = self.client.get(self.url())
        record = response.context["records"][0]
        self.assertEqual(record.latest_version_no, 2)
        self.assertEqual(record.latest_output_qty, Decimal(200))
        self.assertContains(response, "Phiên bản mới nhất")
        self.assertEqual(self.client.get(self.url("detail")).context["version"].version_no, 2)
        self.assertEqual(self.client.get(self.url("version_detail")).context["version"].version_no, 1)

    def test_sort_all_supported_fields_both_directions(self):
        second = Recipe.objects.create(organization=self.company, product=self.product, code="AAA", name="Định mức A")
        RecipeVersion.objects.create(recipe=second, version_no=3, output_qty=1, output_uom=self.kg, effective_from=self.today - timedelta(days=100))
        mappings = {"code": "code", "name": "name", "created_at": "created_at", "version": "latest_version_no", "effective_from": "latest_effective_from"}
        for field, attr in mappings.items():
            for prefix in ("", "-"):
                records = list(self.client.get(self.url(), {"sort": prefix + field}).context["records"])
                values = [getattr(record, attr) for record in records]
                self.assertEqual(values, sorted(values, reverse=bool(prefix)))
        self.assertEqual(self.client.get(self.url(), {"sort": "bad"}).context["current_sort"], "code")

    def test_pagination_recipe_version_and_lines(self):
        Recipe.objects.bulk_create([Recipe(organization=self.company, product=self.product, code=f"TEST_{i:03}", name=f"Định mức {i}") for i in range(101)])
        RecipeVersion.objects.bulk_create([RecipeVersion(recipe=self.recipe, version_no=i + 2, output_qty=1, output_uom=self.kg) for i in range(101)])
        RecipeLine.objects.bulk_create([RecipeLine(recipe_version=self.version, component_item=self.item, qty=1, uom=self.kg, display_order=i) for i in range(101)])
        for url in (self.url(), self.url("version_list"), self.url("version_detail")):
            for size in (25, 50, 100):
                response = self.client.get(url, {"per_page": size, "page": 2})
                self.assertEqual(response.context["page_obj"].number, 2)
                self.assertEqual(response.context["per_page"], size)
                self.assertLessEqual(len(response.context["page_obj"].object_list), size)
                self.assertContains(response, f"per_page={size}")
        self.assertEqual(self.client.get(self.url(), {"per_page": 999}).context["per_page"], 25)

    def test_create_recipe_and_first_version_atomically(self):
        response = self.client.post(self.url("create"), self.recipe_payload(organization=self.other.pk), follow=True)
        self.assertContains(response, "Đã tạo định mức nguyên vật liệu.")
        recipe = Recipe.objects.get(code="BOM_NEW")
        self.assertEqual(recipe.name, "Định mức mới")
        self.assertEqual(recipe.organization_id, self.company.pk)
        version = recipe.recipeversion_set.get()
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.output_qty, Decimal("100.00000001"))
        self.assertEqual(version.yield_rate, Decimal("0.98123456"))
        self.assertEqual(version.status, "DRAFT")
        self.assertIsNone(version.created_by)
        self.assertIsNone(version.approved_by)

    def test_duplicate_code_rejected_after_normalization(self):
        response = self.client.post(self.url("create"), self.recipe_payload(code=" bom_cap "))
        self.assertContains(response, "Mã định mức đã tồn tại.")
        self.assertEqual(Recipe.objects.count(), 2)

    def test_invalid_initial_version_leaves_no_half_created_recipe(self):
        for field, value in (("initial-output_qty", "0"), ("initial-output_uom", ""), ("initial-yield_rate", "0")):
            response = self.client.post(self.url("create"), self.recipe_payload(**{field: value}))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["version_form"].errors)
            self.assertFalse(Recipe.objects.filter(code="BOM_NEW").exists())
        with patch("apps.bom.services._new_version", side_effect=ValidationError("Không thể lưu phiên bản.")):
            response = self.client.post(self.url("create"), self.recipe_payload())
        self.assertContains(response, "Không thể lưu phiên bản.")
        self.assertFalse(Recipe.objects.filter(code="BOM_NEW").exists())

    def test_invalid_forms_and_prefixed_accessible_errors(self):
        response = self.client.post(self.url("create"), self.recipe_payload(name="", **{"initial-output_qty": "0"}))
        self.assertContains(response, "Vui lòng nhập tên định mức.")
        self.assertContains(response, 'id="id_initial-output_qty_errors"')
        self.assertContains(response, 'aria-describedby="id_initial-output_qty_help id_initial-output_qty_errors"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, "Vui lòng kiểm tra các trường được đánh dấu.")
        self.assertEqual(Recipe.objects.count(), 2)

    def test_header_edit_and_deactivate(self):
        response = self.client.post(self.url("edit"), self.recipe_payload(code="bom_cap", name=" Định mức cập nhật ", is_active=""), follow=True)
        self.assertContains(response, "Đã cập nhật định mức nguyên vật liệu.")
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.name, "Định mức cập nhật")
        self.assertFalse(self.recipe.is_active)

    def test_new_version_and_hidden_audit_status_identifiers(self):
        response = self.client.post(self.url("version_create"), self.version_payload(status="EFFECTIVE", version_no=99,
            created_by="00000000-0000-0000-0000-000000000001", approved_at="2026-01-01"), follow=True)
        self.assertContains(response, "Đã tạo phiên bản định mức mới.")
        version = RecipeVersion.objects.get(recipe=self.recipe, version_no=2)
        self.assertEqual(version.status, "DRAFT")
        self.assertIsNone(version.content_hash)
        self.assertIsNone(version.created_by)
        self.assertIsNone(version.approved_at)

    def test_clone_all_configuration_and_lines_old_unchanged(self):
        old = {field: getattr(self.version, field) for field in VERSION_FIELDS}
        values = {field: getattr(self.line, field) for field in LINE_FIELDS}
        source = self.url("version_create") + f"?source={self.version.pk}"
        page = self.client.get(source)
        self.assertContains(page, 'value="98"')
        self.assertContains(page, f'action="{source}"')
        payload = self.version_payload(output_qty="100", yield_rate="98", effective_from=self.version.effective_from.isoformat(), effective_to=self.version.effective_to.isoformat(), change_reason="Bản sao")
        response = self.client.post(source, payload, follow=True)
        self.assertContains(response, "Đã tạo phiên bản định mức mới.")
        new = RecipeVersion.objects.get(recipe=self.recipe, version_no=2)
        line = new.recipeline_set.get()
        for field, value in values.items():
            self.assertEqual(getattr(line, field), value)
        self.assertNotEqual(line.pk, self.line.pk)
        self.assertEqual(new.status, "DRAFT")
        self.version.refresh_from_db()
        self.assertEqual({field: getattr(self.version, field) for field in VERSION_FIELDS}, old)

    def test_clone_failure_rolls_back_version_and_lines(self):
        with patch("apps.bom.services.RecipeLine.objects.bulk_create", side_effect=ValidationError("Lỗi sao chép thành phần.")):
            with self.assertRaises(ValidationError):
                services.create_version(workspace=self.workspace(), recipe=self.recipe, data=self.version_data(), source=self.version)
        self.assertEqual(RecipeVersion.objects.filter(recipe=self.recipe).count(), 1)
        self.assertEqual(RecipeLine.objects.count(), 1)

    def test_version_edit_only_changes_selected_draft(self):
        second = services.create_version(workspace=self.workspace(), recipe=self.recipe, data=self.version_data())
        response = self.client.post(self.url("version_edit"), self.version_payload(output_qty="250", change_reason=" Sửa sản lượng "), follow=True)
        self.assertContains(response, "Đã cập nhật phiên bản định mức.")
        self.version.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.version.output_qty, Decimal(250))
        self.assertEqual(self.version.change_reason, "Sửa sản lượng")
        self.assertEqual(second.output_qty, Decimal("100.00000001"))

    def test_version_quantity_yield_dates_boundaries(self):
        for field, value in (("output_qty", "0"), ("output_qty", "-1"), ("output_qty", "NaN"),
            ("yield_rate", "0"), ("yield_rate", "100.000001"), ("yield_rate", "-1"), ("yield_rate", "98.1234567")):
            response = self.client.post(self.url("version_create"), self.version_payload(**{field: value}))
            self.assertIn(field, response.context["form"].errors)
        for end in (self.today.isoformat(), (self.today - timedelta(days=1)).isoformat()):
            response = self.client.post(self.url("version_create"), self.version_payload(effective_to=end))
            self.assertIn("effective_to", response.context["form"].errors)
        response = self.client.post(self.url("version_create"), self.version_payload(effective_from="", effective_to=""))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(self.url("version_create"), self.version_payload(effective_from=""))
        self.assertIn("effective_from", response.context["form"].errors)

    def test_status_and_effective_filters_on_version_history(self):
        future = services.create_version(workspace=self.workspace(), recipe=self.recipe, data=self.version_data(effective_from=(self.today + timedelta(days=1)).isoformat()))
        response = self.client.get(self.url("version_list"), {"status": "DRAFT", "effective": "FUTURE"})
        self.assertEqual(list(response.context["records"]), [future])
        self.assertContains(response, "Sắp hiệu lực")
        self.assertContains(response, "Nháp")

    def test_overlapping_version_dates_allowed_by_existing_schema(self):
        first = services.create_version(workspace=self.workspace(), recipe=self.recipe, data=self.version_data())
        second = services.create_version(workspace=self.workspace(), recipe=self.recipe, data=self.version_data())
        self.assertNotEqual(first.pk, second.pk)

    def test_add_and_edit_line_normalizes_exact_decimal(self):
        response = self.client.post(self.url("line_create"), self.line_payload(), follow=True)
        self.assertContains(response, "Đã thêm thành phần.")
        saved = RecipeLine.objects.exclude(pk=self.line.pk).get()
        self.assertEqual(saved.qty, Decimal("0.50000001"))
        self.assertEqual(saved.scrap_rate, Decimal("0.02123456"))
        self.assertEqual(saved.operation_code, "MIX_2")
        self.assertEqual(saved.notes, "Thành phần mới")
        response = self.client.post(self.url("line_edit", line=saved), self.line_payload(qty="1.5", scrap_rate="0", notes="Đã sửa"), follow=True)
        self.assertContains(response, "Đã cập nhật thành phần.")
        saved.refresh_from_db()
        self.assertEqual(saved.qty, Decimal("1.5"))
        self.assertEqual(saved.scrap_rate, 0)

    def test_missing_item_and_uom_invalid_qty_and_scrap(self):
        for field, values in (("component_item", ("",)), ("uom", ("",)), ("qty", ("0", "-1", "NaN", "1.123456789")),
            ("scrap_rate", ("-1", "100", "100.000001", "NaN"))):
            for value in values:
                response = self.client.post(self.url("line_create"), self.line_payload(**{field: value}))
                self.assertIn(field, response.context["form"].errors)
                self.assertContains(response, 'aria-invalid="true"')
        self.assertEqual(RecipeLine.objects.count(), 1)

    def test_repeat_item_and_all_item_types_are_allowed(self):
        from apps.product.constants import ITEM_TYPES
        for item_type, label in ITEM_TYPES:
            item = Item.objects.create(organization=self.company, code=item_type, name=label, item_type=item_type, base_uom=self.kg)
            response = self.client.post(self.url("line_create"), self.line_payload(component_item=str(item.pk)))
            self.assertEqual(response.status_code, 302)
        response = self.client.post(self.url("line_create"), self.line_payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecipeLine.objects.filter(component_item=self.item).count(), 2)

    def test_delete_requires_post_and_explicit_confirmation(self):
        response = self.client.get(self.url("line_remove"))
        self.assertContains(response, "Bạn có chắc muốn xóa thành phần này khỏi định mức?")
        self.assertTrue(RecipeLine.objects.filter(pk=self.line.pk).exists())
        response = self.client.post(self.url("line_remove"), {}, follow=True)
        self.assertContains(response, "Đã xóa thành phần.")
        self.assertFalse(RecipeLine.objects.filter(pk=self.line.pk).exists())
        self.assertContains(response, "Định mức chưa có thành phần.")

    def test_inactive_choices_are_hidden_but_existing_refs_retained(self):
        self.item.is_active = self.kg.is_active = self.product.is_active = False
        self.item.save()
        self.kg.save()
        self.product.save()
        create = RecipeLineForm(workspace=self.workspace(), version=self.version)
        edit = RecipeLineForm(workspace=self.workspace(), version=self.version, instance=self.line)
        self.assertNotIn(self.item, create.fields["component_item"].queryset)
        self.assertNotIn(self.kg, create.fields["uom"].queryset)
        self.assertIn(self.item, edit.fields["component_item"].queryset)
        self.assertIn(self.kg, edit.fields["uom"].queryset)
        self.assertNotIn(self.product, RecipeForm(workspace=self.workspace()).fields["product"].queryset)
        response = self.client.post(self.url("line_edit"), self.line_payload())
        self.assertEqual(response.status_code, 302)
        copied = services.create_version(workspace=self.workspace(), recipe=self.recipe,
            data={field: getattr(self.version, field) for field in VERSION_FIELDS}, source=self.version)
        self.assertEqual(copied.recipeline_set.count(), 1)
        self.assertEqual(self.client.get(self.url("detail")).status_code, 200)

    def test_uom_difference_requires_effective_direct_conversion(self):
        response = self.client.post(self.url("line_create"), self.line_payload(uom=str(self.g.pk)))
        self.assertContains(response, "không tìm thấy quy đổi đơn vị phù hợp")
        self.assertIn("uom", response.context["form"].errors)
        self.conversion()
        response = self.client.post(self.url("line_create"), self.line_payload(uom=str(self.g.pk)))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecipeLine.objects.exclude(pk=self.line.pk).get().qty, Decimal("0.50000001"))

    def test_conversion_inverse_shared_and_item_specific_scope(self):
        self.conversion(organization=None, from_uom=self.kg, to_uom=self.g, factor=Decimal(1000))
        form = RecipeLineForm(self.line_payload(uom=str(self.g.pk)), workspace=self.workspace(), version=self.version)
        self.assertTrue(form.is_valid(), form.errors)
        UomConversion.objects.all().delete()
        self.conversion(from_uom=self.pack, to_uom=self.kg, factor=Decimal("0.25"), item=self.item)
        form = RecipeLineForm(self.line_payload(uom=str(self.pack.pk)), workspace=self.workspace(), version=self.version)
        self.assertTrue(form.is_valid(), form.errors)

    def test_conversion_wrong_item_company_expired_or_future_is_rejected(self):
        cases = ({"organization": self.other}, {"item": self.other_item},
            {"effective_to": self.today - timedelta(days=2)}, {"effective_from": self.today + timedelta(days=1)})
        for changes in cases:
            conversion = self.conversion(**changes)
            form = RecipeLineForm(self.line_payload(uom=str(self.g.pk)), workspace=self.workspace(), version=self.version)
            self.assertFalse(form.is_valid())
            self.assertIn("uom", form.errors)
            conversion.delete()

    def test_version_date_change_revalidates_all_conversion_pairs(self):
        conversion = self.conversion(effective_to=self.today + timedelta(days=5))
        self.line.uom = self.g
        self.line.save()
        response = self.client.post(self.url("version_edit"), self.version_payload(effective_from=(self.today + timedelta(days=6)).isoformat()))
        self.assertContains(response, "không tìm thấy quy đổi đơn vị phù hợp")
        self.version.refresh_from_db()
        self.assertEqual(self.version.effective_from, self.today - timedelta(days=1))

    def test_service_reloads_stale_references_and_conversions(self):
        values = self.line_data()
        Item.objects.filter(pk=self.item.pk).update(is_active=False)
        with self.assertRaises(ValidationError) as error:
            services.save_line(workspace=self.workspace(), recipe=self.recipe, version=self.version, data=values)
        self.assertIn("component_item", error.exception.message_dict)
        Item.objects.filter(pk=self.item.pk).update(is_active=True)
        conversion = self.conversion()
        values = self.line_data(uom=str(self.g.pk))
        conversion.delete()
        with self.assertRaises(ValidationError):
            services.save_line(workspace=self.workspace(), recipe=self.recipe, version=self.version, data=values)

    def test_company_and_nested_url_scope(self):
        for url in (self.url("detail", recipe=self.foreign), self.url("edit", recipe=self.foreign),
            self.url("version_detail", version=self.foreign_version), self.url("line_edit", version=self.foreign_version),
            self.url("version_create") + f"?source={self.foreign_version.pk}"):
            self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.post(self.url("create"), self.recipe_payload(product=str(self.other_product.pk)))
        self.assertIn("product", response.context["form"].errors)
        response = self.client.post(self.url("line_create"), self.line_payload(component_item=str(self.other_item.pk)))
        self.assertIn("component_item", response.context["form"].errors)
        response = self.client.get(self.url("version_create") + "?source=bad")
        self.assertEqual(response.status_code, 404)

    def test_locked_versions_and_lines_cannot_be_mutated_in_service_or_ui(self):
        for status in ("APPROVED", "EFFECTIVE", "RETIRED"):
            version = services.create_version(workspace=self.workspace(), recipe=self.recipe, data=self.version_data(), source=self.version)
            RecipeVersion.objects.filter(pk=version.pk).update(status=status)
            line = version.recipeline_set.get()
            detail = self.client.get(self.url("version_detail", version=version))
            self.assertNotContains(detail, "+ Thêm thành phần")
            self.assertContains(detail, "Phiên bản đã được chốt.")
            for url, data in ((self.url("version_edit", version=version), self.version_payload()),
                (self.url("line_create", version=version), self.line_payload()),
                (self.url("line_edit", version=version, line=line), self.line_payload()),
                (self.url("line_remove", version=version, line=line), {})):
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Không thể chỉnh sửa phiên bản đã được chốt.")
            version.refresh_from_db()
            self.assertEqual(version.recipeline_set.count(), 1)
            self.assertEqual(version.output_qty, Decimal("100.00000001"))
            copied = services.create_version(workspace=self.workspace(), recipe=self.recipe,
                data={field: getattr(version, field) for field in VERSION_FIELDS}, source=version)
            self.assertEqual(copied.status, "DRAFT")
            self.assertEqual(copied.recipeline_set.count(), 1)

    def test_locked_header_product_cannot_change_or_line_move_between_versions(self):
        RecipeVersion.objects.filter(pk=self.version.pk).update(status="APPROVED")
        product = Product.objects.create(organization=self.company, code="NEW_PRODUCT", name="Sản phẩm mới", costing_uom=self.kg)
        form = self.client.get(self.url("edit")).context["form"]
        self.assertTrue(form.fields["product"].disabled)
        data = {field: getattr(self.recipe, field) for field in ("product", "code", "name", "description", "is_active")}
        with self.assertRaises(ValidationError):
            services.save_recipe(workspace=self.workspace(), data={**data, "product": product}, instance=self.recipe)
        second = services.create_version(workspace=self.workspace(), recipe=self.recipe, data=self.version_data())
        response = self.client.post(self.url("line_edit", version=second, line=self.line), self.line_payload())
        self.assertEqual(response.status_code, 404)

    def test_database_immutable_triggers_are_last_protection(self):
        RecipeVersion.objects.filter(pk=self.version.pk).update(status="APPROVED")
        operations = (
            lambda: RecipeVersion.objects.filter(pk=self.version.pk).update(output_qty=200),
            lambda: RecipeVersion.objects.filter(pk=self.version.pk).delete(),
            lambda: RecipeLine.objects.filter(pk=self.line.pk).update(qty=2),
            lambda: RecipeLine.objects.filter(pk=self.line.pk).delete(),
            lambda: RecipeLine.objects.create(recipe_version=self.version, component_item=self.item, qty=1, uom=self.kg),
        )
        for operation in operations:
            with self.assertRaises(DatabaseError), transaction.atomic():
                operation()

    def test_trigger_exception_becomes_friendly_error_and_rolls_back(self):
        def concurrent_status_change(version):
            RecipeVersion.objects.filter(pk=version.pk).update(status="APPROVED")
        with patch("apps.bom.services.ensure_editable", side_effect=concurrent_status_change):
            with self.assertRaises(ValidationError) as error:
                services.save_line(workspace=self.workspace(), recipe=self.recipe, version=self.version, data=self.line_data())
        self.assertIn("Không thể chỉnh sửa phiên bản đã được chốt", str(error.exception))
        self.version.refresh_from_db()
        self.assertEqual(self.version.status, "DRAFT")
        self.assertEqual(RecipeLine.objects.count(), 1)

    def test_uniqueness_race_maps_database_error(self):
        form = RecipeForm(self.recipe_payload(), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        with patch("apps.bom.services.validate_recipe"):
            with self.assertRaises(ValidationError) as error:
                services.save_recipe(workspace=self.workspace(), data={**form.cleaned_data, "code": self.recipe.code}, initial_version=self.version_data())
        self.assertEqual(error.exception.message_dict, {"code": ["Mã định mức đã tồn tại."]})

    def test_real_database_quantity_rate_period_and_status_checks(self):
        for field, value in (("output_qty", 0), ("yield_rate", 0), ("yield_rate", 2), ("effective_to", self.version.effective_from), ("status", "BAD")):
            with self.assertRaises(IntegrityError), transaction.atomic():
                RecipeVersion.objects.filter(pk=self.version.pk).update(**{field: value})
        for field, value in (("qty", 0), ("qty", -1), ("scrap_rate", -1), ("scrap_rate", 1)):
            with self.assertRaises(IntegrityError), transaction.atomic():
                RecipeLine.objects.filter(pk=self.line.pk).update(**{field: value})

    def test_htmx_list_history_detail_version_and_line_partial(self):
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
        self.assertNotContains(response, "<!doctype", html=False)
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/reference_data_list.html")
        self.assertTemplateUsed(self.client.get(self.url("detail"), HTTP_HX_REQUEST="true"), "bom/partials/detail_content.html")
        self.assertTemplateUsed(self.client.get(self.url("version_list"), HTTP_HX_REQUEST="true"), "master_data/partials/reference_data_table.html")
        self.assertTemplateUsed(self.client.get(self.url("line_create"), HTTP_HX_REQUEST="true"), "bom/partials/line_editor.html")
        response = self.client.post(self.url("line_create"), self.line_payload(qty="0"), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "bom/partials/line_editor.html")
        self.assertContains(response, "Số lượng phải lớn hơn 0.")
        response = self.client.post(self.url("line_create"), self.line_payload(), HTTP_HX_REQUEST="true")
        self.assertEqual(response["HX-Retarget"], "#bom-lines-table")
        self.assertEqual(response["HX-Reswap"], "outerHTML")
        self.assertContains(response, 'hx-swap-oob="outerHTML"')
        self.assertContains(response, "Đã thêm thành phần.")
        response = self.client.get(self.url("version_detail"), HTTP_HX_REQUEST="true", HTTP_HX_TARGET="bom-lines-table")
        self.assertTemplateUsed(response, "bom/partials/lines_table.html")
        self.assertNotContains(response, 'id="bom-detail"')
        normal = self.client.get(self.url("line_create"))
        self.assertNotContains(normal, "hx-post=")

    def test_line_result_pagination_links_target_detail_not_post_endpoint(self):
        RecipeLine.objects.bulk_create([RecipeLine(recipe_version=self.version, component_item=self.item, qty=1, uom=self.kg) for _ in range(30)])
        response = self.client.post(self.url("line_create") + "?page=2&per_page=25", self.line_payload(), HTTP_HX_REQUEST="true")
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertContains(response, self.url("version_detail") + "?page=1&amp;per_page=25")
        self.assertNotContains(response, self.url("line_create") + "?page=1")

    def test_csrf_still_required_and_audit_organization_hidden(self):
        client = Client(enforce_csrf_checks=True)
        for url, data in ((self.url("create"), self.recipe_payload()), (self.url("version_create"), self.version_payload()),
            (self.url("line_create"), self.line_payload()), (self.url("line_remove"), {})):
            page = client.get(url)
            self.assertContains(page, 'name="csrfmiddlewaretoken"')
            for field in ("organization", "created_by", "approved_by", "status", "content_hash"):
                self.assertNotContains(page, f'name="{field}"')
            self.assertEqual(client.post(url, data).status_code, 403)
            response = client.post(url, data, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
            self.assertEqual(response.status_code, 302)

    def test_empty_states_and_legacy_recipe_without_version(self):
        self.assertContains(self.client.get(self.url(), {"q": "missing"}), "Không có kết quả phù hợp.")
        RecipeLine.objects.all().delete()
        self.assertContains(self.client.get(self.url("version_detail")), "Định mức chưa có thành phần.")
        empty = Recipe.objects.create(organization=self.company, product=self.product, code="EMPTY", name="Định mức chưa có phiên bản")
        self.assertContains(self.client.get(self.url("detail", recipe=empty)), "Định mức chưa có phiên bản.")
        RecipeVersion.objects.all().delete()
        Recipe.objects.all().delete()
        self.assertContains(self.client.get(self.url()), "Chưa có định mức nguyên vật liệu.")

    def test_query_counts_are_bounded_and_list_does_not_load_lines(self):
        RecipeLine.objects.bulk_create([RecipeLine(recipe_version=self.version, component_item=self.item, qty=i + 1, uom=self.kg) for i in range(40)])
        with self.assertNumQueries(1):
            for line in selectors.line_queryset(version=self.version, organization=self.company):
                _ = line.component_item.name, line.uom.symbol
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 7)
        self.assertFalse(any('"recipe_line"' in query["sql"] for query in queries))
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url("version_detail"))
        self.assertLessEqual(len(queries), 7)
        self.assertEqual(len(response.context["lines"]), 25)

    def test_percent_date_precision_and_vietnamese_labels(self):
        import re
        banned = re.compile(r"\b(?:Create|Edit|Save|Cancel|Search|Filter|Status|Actions|Active|Inactive|Name|Description)\b")
        for action in ("list", "detail", "create", "edit", "version_list", "version_create", "version_detail", "version_edit", "line_create", "line_edit", "line_remove"):
            page = self.client.get(self.url(action))
            self.assertEqual(page.status_code, 200)
            parser = VisibleText()
            parser.feed(page.content.decode())
            self.assertIsNone(banned.search(" ".join(parser.text)))
            self.assertContains(page, 'lang="vi"')
        page = self.client.get(self.url("version_detail"))
        self.assertContains(page, "0,40000001")
        self.assertContains(page, "2%")
        self.assertContains(page, "98%")
        self.assertContains(page, self.version.effective_from.strftime("%d/%m/%Y"))
        self.assertContains(page, "Nguyên liệu")
        self.assertNotContains(page, ">True<")
        self.line.refresh_from_db()
        self.assertEqual(self.line.qty, Decimal("0.40000001"))
