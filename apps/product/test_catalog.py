from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.models import Item, Organization, OrganizationMember, ProductCategory, Uom, UomCategory
from apps.master_data.access import get_workspace
from .constants import ITEM_TYPES
from .forms import ItemForm
from .selectors import item_queryset
from .services import save_category, save_item


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(code="CATALOG", name="Công ty danh mục")
        cls.other = Organization.objects.create(code="OTHER", name="Công ty khác")
        cls.category = ProductCategory.objects.create(organization=cls.organization, code="NL", name="Nguyên liệu", description="Dùng cho sản xuất")
        cls.inactive = ProductCategory.objects.create(organization=cls.organization, code="OLD", name="Nhóm cũ", is_active=False)
        cls.foreign_category = ProductCategory.objects.create(organization=cls.other, code="FOREIGN", name="Nhóm riêng")
        cls.mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        cls.length = UomCategory.objects.create(code="LENGTH", name="Chiều dài", dimension_code="LENGTH")
        cls.kg = Uom.objects.create(category=cls.mass, code="KG", name="Kilôgam", symbol="kg")
        cls.m = Uom.objects.create(category=cls.length, code="M", name="Mét", symbol="m")
        cls.inactive_unit = Uom.objects.create(category=cls.mass, code="G", name="Gam", symbol="g", is_active=False)
        cls.item = Item.objects.create(organization=cls.organization, category=cls.category, code="BOT", name="Bột nguyên liệu", item_type="RAW_MATERIAL", base_uom=cls.kg, purchase_uom=cls.kg, production_uom=cls.kg, metadata={"legacy": True})
        cls.service = Item.objects.create(organization=cls.organization, code="SERVICE", name="Gia công", item_type="SERVICE", base_uom=cls.kg, is_stock_item=False, is_active=False)
        cls.foreign_item = Item.objects.create(organization=cls.other, category=cls.foreign_category, code="PRIVATE", name="Vật tư riêng", item_type="PACKAGING", base_uom=cls.kg)

    def setUp(self):
        setting = override_settings(DEFAULT_ORGANIZATION_ID=self.organization.pk)
        setting.enable()
        self.addCleanup(setting.disable)

    def url(self, resource, action="list", record=None):
        return reverse(f"product:{resource}_{action}", args=[record.pk] if record else [])

    def category_data(self, **changes):
        data = dict(code=" tp ", name=" Thành phẩm ", description=" Mô tả ", is_active="on")
        data.update(changes)
        return data

    def item_data(self, **changes):
        data = dict(category=str(self.category.pk), code=" new_item ", name=" Vật tư mới ", item_type="RAW_MATERIAL",
            base_uom=str(self.kg.pk), purchase_uom=str(self.kg.pk), production_uom=str(self.kg.pk),
            tax_class_code=" VAT ", net_weight="1.125", gross_weight="1.5", weight_uom=str(self.kg.pk),
            length="2.5", width="0", height="1", dimension_uom=str(self.m.pk), is_stock_item="on", is_active="on")
        data.update(changes)
        return data

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url("item")))

    def test_category_list_search_code_name_description(self):
        response = self.client.get(self.url("category"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Danh mục nhóm sản phẩm")
        self.assertNotContains(response, self.foreign_category.name)
        for keyword in ("nl", "Nguyên liệu", "sản xuất"):
            self.assertEqual(list(self.client.get(self.url("category"), {"q": keyword}).context["records"]), [self.category])

    def test_category_active_filter(self):
        for parameter in ("active", "is_active"):
            response = self.client.get(self.url("category"), {parameter: "false"})
            self.assertEqual(list(response.context["records"]), [self.inactive])

    def test_sorting_and_pagination_for_both_modules(self):
        for resource, model, fields in (("category", ProductCategory, ("code", "name", "created_at")), ("item", Item, ("code", "name", "item_type", "created_at"))):
            for field in fields:
                for prefix in ("", "-"):
                    response = self.client.get(self.url(resource), {"sort": prefix + field})
                    self.assertEqual([row.pk for row in response.context["records"]], list(model.objects.filter(organization=self.organization).order_by(prefix + field, "pk").values_list("pk", flat=True)))
            self.assertEqual(self.client.get(self.url(resource), {"sort": "--bad", "per_page": "bad"}).context["current_sort"], "code")
        Item.objects.bulk_create([Item(organization=self.organization, code=f"PAGE_{i:03}", name=f"Vật tư {i}", item_type="PACKAGING", base_uom=self.kg) for i in range(101)])
        for size in (25, 50, 100):
            response = self.client.get(self.url("item"), {"q": "PAGE", "page": 2, "per_page": size})
            self.assertEqual(response.context["page_obj"].number, 2)
            self.assertEqual(response.context["per_page"], size)
            self.assertContains(response, 'hx-push-url="true"')
        self.assertEqual(self.client.get(self.url("item"), {"per_page": 999}).context["per_page"], 25)

    def test_create_category_normalizes_and_sets_company(self):
        response = self.client.post(self.url("category", "create"), self.category_data(organization=str(self.other.pk), parent=str(self.foreign_category.pk)))
        record = ProductCategory.objects.get(code="TP", organization=self.organization)
        self.assertRedirects(response, self.url("category", "detail", record), fetch_redirect_response=False)
        self.assertEqual(record.name, "Thành phẩm")
        self.assertEqual(record.description, "Mô tả")
        self.assertIsNone(record.parent_id)
        self.assertContains(self.client.get(self.url("category", "detail", record)), "Đã tạo nhóm sản phẩm.")

    def test_duplicate_category_code_rejected_but_other_company_allowed(self):
        response = self.client.post(self.url("category", "create"), self.category_data(code=" nl "))
        self.assertContains(response, "Mã này đã tồn tại.")
        self.assertEqual(ProductCategory.objects.filter(organization=self.organization, code="NL").count(), 1)
        self.assertEqual(self.client.post(self.url("category", "create"), self.category_data(code="FOREIGN")).status_code, 302)

    def test_category_invalid_form_keeps_inputs_and_accessible_errors(self):
        response = self.client.post(self.url("category", "create"), self.category_data(code="", name="Giữ nội dung"))
        self.assertContains(response, "Không thể lưu nhóm sản phẩm.")
        self.assertContains(response, 'value="Giữ nội dung"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertIn("code", response.context["form"].errors)

    def test_edit_category_preserves_parent_and_deactivates(self):
        self.category.parent = self.inactive
        self.category.save()
        response = self.client.post(self.url("category", "edit", self.category), self.category_data(code="NL", name="Nhóm đã sửa", is_active=""))
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Nhóm đã sửa")
        self.assertEqual(self.category.parent_id, self.inactive.pk)
        self.assertFalse(self.category.is_active)
        self.assertContains(self.client.get(self.url("category", "detail", self.category)), "Đã cập nhật nhóm sản phẩm.")

    def test_category_detail_and_empty_states(self):
        self.assertContains(self.client.get(self.url("category", "detail", self.category)), "Dùng cho sản xuất")
        self.assertContains(self.client.get(self.url("category"), {"q": "no-results"}), "Không có kết quả phù hợp.")
        Item.objects.filter(organization=self.organization).update(category=None)
        ProductCategory.objects.filter(organization=self.organization).delete()
        self.assertContains(self.client.get(self.url("category")), "Chưa có nhóm sản phẩm.")

    def test_item_list_search_and_all_filters(self):
        response = self.client.get(self.url("item"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Danh mục vật tư / hàng hóa")
        self.assertContains(response, "Nguyên liệu")
        self.assertNotContains(response, self.foreign_item.name)
        for params in ({"q": "bot"}, {"q": "Bột nguyên"}, {"category": self.category.pk}, {"item_type": "RAW_MATERIAL"}, {"active": "true"}, {"is_stock_item": "true"}):
            self.assertEqual(list(self.client.get(self.url("item"), params).context["records"]), [self.item])
        self.assertEqual(list(self.client.get(self.url("item"), {"base_uom": self.kg.pk}).context["records"]), [self.item, self.service])
        self.assertEqual(list(self.client.get(self.url("item"), {"is_active": "false"}).context["records"]), [self.service])

    def test_invalid_or_foreign_filters_do_not_widen_results(self):
        for field in ("category", "base_uom"):
            for value in ("bad", "-1", "9" * 100, "１２"):
                self.assertEqual(list(self.client.get(self.url("item"), {field: value}).context["records"]), [])
        self.assertEqual(list(self.client.get(self.url("item"), {"category": self.foreign_category.pk}).context["records"]), [])
        self.assertEqual(list(self.client.get(self.url("item"), {"item_type": "MATERIAL"}).context["records"]), [])

    def test_create_item_normalizes_and_persists_units_without_conversion(self):
        response = self.client.post(self.url("item", "create"), self.item_data(organization=str(self.other.pk), metadata='{"fake":1}'))
        record = Item.objects.get(organization=self.organization, code="NEW_ITEM")
        self.assertRedirects(response, self.url("item", "detail", record), fetch_redirect_response=False)
        self.assertEqual(record.name, "Vật tư mới")
        self.assertEqual(record.tax_class_code, "VAT")
        self.assertEqual(record.metadata, {})
        self.assertEqual(record.base_uom, self.kg)
        self.assertEqual(record.purchase_uom, self.kg)
        self.assertEqual(record.production_uom, self.kg)
        self.assertEqual(record.dimension_uom, self.m)
        self.assertEqual(record.net_weight, Decimal("1.125"))
        self.assertContains(self.client.get(self.url("item", "detail", record)), "Đã tạo vật tư / hàng hóa.")

    def test_all_actual_item_types_are_supported(self):
        for item_type, label in ITEM_TYPES:
            response = self.client.post(self.url("item", "create"), self.item_data(code="TYPE_" + item_type, item_type=item_type))
            self.assertEqual(response.status_code, 302, response.context)
            record = Item.objects.get(organization=self.organization, code="TYPE_" + item_type)
            self.assertContains(self.client.get(self.url("item", "detail", record)), label)

    def test_duplicate_item_code_rejected(self):
        response = self.client.post(self.url("item", "create"), self.item_data(code=" bot "))
        self.assertContains(response, "Mã này đã tồn tại.")
        self.assertEqual(Item.objects.filter(organization=self.organization, code="BOT").count(), 1)

    def test_edit_item_preserves_metadata_and_updates(self):
        response = self.client.post(self.url("item", "edit", self.item), self.item_data(code="BOT", name="Bột đã sửa", metadata="{}", is_active=""))
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "Bột đã sửa")
        self.assertEqual(self.item.metadata, {"legacy": True})
        self.assertFalse(self.item.is_active)
        self.assertContains(self.client.get(self.url("item", "detail", self.item)), "Đã cập nhật vật tư / hàng hóa.")

    def test_item_detail_dates_numbers_and_friendly_unit_labels(self):
        self.item.net_weight = Decimal("1250.50000000")
        self.item.weight_uom = self.kg
        self.item.save()
        response = self.client.get(self.url("item", "detail", self.item))
        self.assertContains(response, "1.250,5")
        self.assertContains(response, "Kilôgam (kg)")
        self.assertContains(response, self.item.created_at.strftime("%d/%m/%Y"))
        self.assertNotContains(response, "1250.50000000")
        self.assertNotContains(response, "legacy")
        form = self.client.get(self.url("item", "edit", self.item))
        self.assertContains(form, 'value="1250.5"')
        self.assertNotContains(form, 'value="1250.50000000"')

    def test_negative_weights_and_dimensions_are_rejected(self):
        for field in ("net_weight", "gross_weight", "length", "width", "height"):
            response = self.client.post(self.url("item", "create"), self.item_data(**{field: "-0.1"}))
            self.assertIn(field, response.context["form"].errors)
            self.assertContains(response, "Giá trị phải lớn hơn hoặc bằng 0.")

    def test_gross_weight_must_not_be_less_than_net(self):
        response = self.client.post(self.url("item", "create"), self.item_data(net_weight="2", gross_weight="1"))
        self.assertContains(response, "Khối lượng tổng không được nhỏ hơn khối lượng tịnh.")

    def test_measurements_require_correct_dimension_units_including_zero(self):
        for changes, field in (({"weight_uom": ""}, "weight_uom"), ({"weight_uom": str(self.m.pk)}, "weight_uom"), ({"dimension_uom": ""}, "dimension_uom"), ({"dimension_uom": str(self.kg.pk)}, "dimension_uom"), ({"net_weight": "0", "gross_weight": "0", "weight_uom": ""}, "weight_uom")):
            response = self.client.post(self.url("item", "create"), self.item_data(**changes))
            self.assertIn(field, response.context["form"].errors)

    def test_optional_measurements_category_and_purchase_units(self):
        response = self.client.post(self.url("item", "create"), self.item_data(category="", purchase_uom="", production_uom="", net_weight="", gross_weight="", weight_uom="", length="", width="", height="", dimension_uom=""))
        self.assertEqual(response.status_code, 302)
        record = Item.objects.get(code="NEW_ITEM", organization=self.organization)
        self.assertIsNone(record.category_id)
        self.assertIsNone(record.net_weight)

    def test_required_base_unit_and_invalid_type_or_numeric_precision(self):
        for changes, field in (({"base_uom": ""}, "base_uom"), ({"item_type": "MATERIAL"}, "item_type"), ({"net_weight": "NaN"}, "net_weight"), ({"length": "0.123456789"}, "length"), ({"gross_weight": "9" * 30}, "gross_weight")):
            response = self.client.post(self.url("item", "create"), self.item_data(**changes))
            self.assertIn(field, response.context["form"].errors)

    def test_form_choices_are_active_scoped_and_friendly(self):
        form = ItemForm(workspace=self.workspace())
        self.assertEqual(list(form.fields["category"].queryset), [self.category])
        self.assertNotIn(self.inactive_unit, list(form.fields["base_uom"].queryset))
        self.assertEqual(form.fields["base_uom"].label_from_instance(self.kg), "Kilôgam (kg)")
        self.assertEqual(form.fields["category"].label_from_instance(self.category), "NL — Nguyên liệu")
        self.assertEqual(list(form.fields["weight_uom"].queryset), [self.kg])
        self.assertEqual(list(form.fields["dimension_uom"].queryset), [self.m])
        for field in ("organization", "metadata", "created_at", "updated_at", "id"):
            self.assertNotIn(field, form.fields)

    def test_new_inactive_or_foreign_references_rejected_and_retained_edit_allowed(self):
        for changes, field in (({"category": str(self.foreign_category.pk)}, "category"), ({"category": str(self.inactive.pk)}, "category"), ({"base_uom": str(self.inactive_unit.pk)}, "base_uom")):
            response = self.client.post(self.url("item", "create"), self.item_data(**changes))
            self.assertIn(field, response.context["form"].errors)
        self.item.category = self.inactive
        self.item.base_uom = self.inactive_unit
        self.item.save()
        response = self.client.post(self.url("item", "edit", self.item), self.item_data(code="BOT", category=str(self.inactive.pk), base_uom=str(self.inactive_unit.pk)))
        self.assertEqual(response.status_code, 302)

    def test_company_boundaries_enforced_on_detail_edit_and_direct_service(self):
        for resource, record in (("category", self.foreign_category), ("item", self.foreign_item)):
            for action in ("detail", "edit"):
                self.assertEqual(self.client.get(self.url(resource, action, record)).status_code, 404)
            self.assertEqual(self.client.post(self.url(resource, "edit", record), {}).status_code, 404)
        with self.assertRaises(ValidationError):
            save_category(workspace=self.workspace(), data={"code": "FOREIGN", "name": "Tamper", "description": None, "is_active": True}, instance=self.foreign_category)

    def test_item_queryset_has_no_n_plus_one(self):
        Item.objects.bulk_create([Item(organization=self.organization, code=f"Q{i}", name="Vật tư", item_type="PACKAGING", category=self.category, base_uom=self.kg, purchase_uom=self.kg, production_uom=self.kg, weight_uom=self.kg, dimension_uom=self.m) for i in range(10)])
        with self.assertNumQueries(1):
            for record in item_queryset(organization=self.organization):
                for field in ("category", "base_uom", "purchase_uom", "production_uom", "weight_uom", "dimension_uom"):
                    reference = getattr(record, field)
                    if reference:
                        self.assertTrue(reference.name)

    def test_anonymous_pages_never_query_membership_or_create_user_session(self):
        with patch.object(OrganizationMember.objects, "filter", side_effect=AssertionError("Membership query")), CaptureQueriesContext(connection) as queries:
            for resource in ("category", "item"):
                response = self.client.get(self.url(resource))
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("sessionid", response.cookies)
                self.assertNotContains(response, "Đăng nhập")
                self.assertNotContains(response, "Đăng xuất")
        self.assertFalse(any("organization_member" in query["sql"] for query in queries))

    def test_htmx_partial_history_restore_and_validation(self):
        for resource, record in (("category", self.category), ("item", self.item)):
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
            self.assertNotContains(response, "<!doctype html>")
            self.assertIn("HX-Request", response["Vary"])
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
            self.assertTemplateUsed(response, "product/catalog_list.html")
            response = self.client.get(self.url(resource, "detail", record), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "product/partials/catalog_detail_content.html")
            response = self.client.post(self.url(resource, "create"), {}, HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_form_content.html")
            self.assertNotIn("HX-Redirect", response)
        response = self.client.post(self.url("item", "create"), self.item_data(), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], self.url("item", "detail", Item.objects.get(code="NEW_ITEM", organization=self.organization)))

    def test_csrf_is_enforced_and_valid_token_works(self):
        client = Client(enforce_csrf_checks=True)
        for resource, payload in (("category", self.category_data()), ("item", self.item_data())):
            self.assertEqual(client.post(self.url(resource, "create"), payload).status_code, 403)
            client.get(self.url(resource, "create"))
            self.assertEqual(client.post(self.url(resource, "create"), payload, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 302)

    def test_item_empty_states_and_navigation(self):
        self.assertContains(self.client.get(self.url("item"), {"q": "no-results"}), "Không có kết quả phù hợp.")
        Item.objects.filter(organization=self.organization).delete()
        response = self.client.get(self.url("item"))
        self.assertContains(response, "Chưa có vật tư / hàng hóa.")
        self.assertContains(response, f'href="{self.url("item")}" aria-current="page"')
        self.assertContains(response, 'aria-current="page"', count=1)

    def test_service_rechecks_stale_inactive_unit_and_category(self):
        form = ItemForm(data=self.item_data(), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        Uom.objects.filter(pk=self.kg.pk).update(is_active=False)
        with self.assertRaises(ValidationError) as error:
            save_item(workspace=self.workspace(), data=form.cleaned_data)
        self.assertIn("base_uom", error.exception.message_dict)
        Uom.objects.filter(pk=self.kg.pk).update(is_active=True)
        ProductCategory.objects.filter(pk=self.category.pk).update(is_active=False)
        with self.assertRaises(ValidationError) as error:
            save_item(workspace=self.workspace(), data=form.cleaned_data)
        self.assertIn("category", error.exception.message_dict)

    def test_database_constraints_and_unique_race_are_sanitized(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Item.objects.create(organization=self.organization, code="INVALID", name="Test", item_type="MATERIAL", base_uom=self.kg)
        form = ItemForm(data=self.item_data(), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        Item.objects.create(organization=self.organization, code="NEW_ITEM", name="Concurrent", item_type="SERVICE", base_uom=self.kg)
        with patch("apps.product.services.validate_item"), self.assertRaisesMessage(ValidationError, "Mã này đã tồn tại."):
            save_item(workspace=self.workspace(), data=form.cleaned_data)
        data = {"code": self.category.code, "name": "Duplicate", "description": None, "is_active": True}
        with patch("apps.product.services.validate_category"), self.assertRaisesMessage(ValidationError, "Mã này đã tồn tại."):
            save_category(workspace=self.workspace(), data=data)
