from dataclasses import replace
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.models import Item, Organization, OrganizationMember, Product, ProductCategory, Sku, Uom, UomCategory
from apps.master_data.access import get_workspace
from .constants import PRODUCT_FIELDS, SKU_FIELDS
from .forms import ProductForm, SkuForm
from .selectors import product_queryset, sku_queryset
from .services import save_product, save_sku


class ProductSkuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="PRODUCT_TEST", name="Công ty sản phẩm")
        cls.other = Organization.objects.create(code="OTHER", name="Công ty khác")
        cls.category = ProductCategory.objects.create(organization=cls.company, code="CAFE", name="Cà phê")
        cls.cocoa = ProductCategory.objects.create(organization=cls.company, code="CACAO", name="Cacao")
        cls.inactive_category = ProductCategory.objects.create(organization=cls.company, code="OLD", name="Nhóm cũ", is_active=False)
        cls.foreign_category = ProductCategory.objects.create(organization=cls.other, code="PRIVATE", name="Nhóm riêng")
        mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        count = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        cls.kg = Uom.objects.create(category=mass, code="KG", name="Kilôgam", symbol="kg")
        cls.g = Uom.objects.create(category=mass, code="G", name="Gam", symbol="g")
        cls.pack = Uom.objects.create(category=count, code="PACK", name="Gói", symbol="gói")
        cls.inactive_unit = Uom.objects.create(category=mass, code="MG", name="Miligam", symbol="mg", is_active=False)
        cls.output = Item.objects.create(organization=cls.company, code="COFFEE_ITEM", name="Hàng hóa cà phê", item_type="FINISHED_GOOD", base_uom=cls.kg)
        cls.inactive_item = Item.objects.create(organization=cls.company, code="OLD_ITEM", name="Hàng hóa cũ", item_type="FINISHED_GOOD", base_uom=cls.kg, is_active=False)
        cls.foreign_item = Item.objects.create(organization=cls.other, code="PRIVATE_ITEM", name="Hàng hóa riêng", item_type="FINISHED_GOOD", base_uom=cls.kg)
        cls.product = Product.objects.create(organization=cls.company, category=cls.category, code="CAPPUCCINO", name="Cà phê Cappuccino", description="Công thức cà phê hòa tan", costing_uom=cls.kg, output_item=cls.output)
        cls.other_product = Product.objects.create(organization=cls.company, category=cls.cocoa, code="CACAO", name="Cacao hòa tan", costing_uom=cls.pack, is_active=False)
        cls.foreign_product = Product.objects.create(organization=cls.other, category=cls.foreign_category, code="PRIVATE_PRODUCT", name="Sản phẩm riêng", costing_uom=cls.kg)
        cls.sku = Sku.objects.create(organization=cls.company, product=cls.product, code="CAP_25G", name="Cappuccino 25g", sales_uom=cls.pack, net_quantity=Decimal("25"), net_quantity_uom=cls.g, sell_item=cls.output, barcode="8930001", attributes={"legacy_variant": "CHOCO"})
        cls.inactive_sku = Sku.objects.create(organization=cls.company, product=cls.other_product, code="CACAO_PACK", name="Cacao đóng gói", sales_uom=cls.pack, net_quantity=Decimal("1"), net_quantity_uom=cls.pack, is_active=False)
        cls.foreign_sku = Sku.objects.create(organization=cls.other, product=cls.foreign_product, code="PRIVATE_SKU", name="SKU riêng", sales_uom=cls.pack, net_quantity=Decimal("10"), net_quantity_uom=cls.g)

    def setUp(self):
        setting = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        setting.enable()
        self.addCleanup(setting.disable)

    def url(self, resource, action="list", record=None):
        return reverse(f"product:{resource}_{action}", args=[record.pk] if record else [])

    def product_data(self, **changes):
        data = dict(category=str(self.category.pk), code=" new_product ", name=" Sản phẩm mới ", description=" Mô tả sản phẩm ", costing_uom=str(self.kg.pk), output_item=str(self.output.pk), tax_class_code=" VAT ", is_active="on")
        data.update(changes)
        return data

    def sku_data(self, **changes):
        data = dict(product=str(self.product.pk), code=" new_sku ", name=" SKU mới ", barcode=" 8930002 ", sales_uom=str(self.pack.pk), net_quantity="25.125", net_quantity_uom=str(self.g.pk), sell_item=str(self.output.pk), is_active="on")
        data.update(changes)
        return data

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url("product")))

    def test_product_list_200_and_search_code_name_description(self):
        response = self.client.get(self.url("product"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Danh mục sản phẩm")
        self.assertNotContains(response, self.foreign_product.name)
        for query in ("cappuccino", "Cà phê", "Công thức"):
            self.assertEqual(list(self.client.get(self.url("product"), {"q": query}).context["records"]), [self.product])

    def test_product_category_uom_and_active_filters(self):
        for filters in ({"category": self.category.pk}, {"costing_uom": self.kg.pk}, {"active": "true"}):
            self.assertEqual(list(self.client.get(self.url("product"), filters).context["records"]), [self.product])
        for parameter in ("active", "is_active"):
            self.assertEqual(list(self.client.get(self.url("product"), {parameter: "false"}).context["records"]), [self.other_product])

    def test_product_create_normalizes_sets_company_and_keeps_entities_separate(self):
        response = self.client.post(self.url("product", "create"), self.product_data(organization=str(self.other.pk), created_at="2000-01-01", metadata='{"fake":1}'))
        record = Product.objects.get(organization=self.company, code="NEW_PRODUCT")
        self.assertRedirects(response, self.url("product", "detail", record), fetch_redirect_response=False)
        self.assertEqual(record.name, "Sản phẩm mới")
        self.assertEqual(record.description, "Mô tả sản phẩm")
        self.assertEqual(record.tax_class_code, "VAT")
        self.assertEqual(record.output_item, self.output)
        self.assertEqual(record.costing_uom, self.kg)
        self.assertNotEqual(record.created_at.year, 2000)
        self.assertEqual(Item.objects.filter(organization=self.company).count(), 2)
        self.assertContains(self.client.get(self.url("product", "detail", record)), "Đã tạo sản phẩm.")

    def test_product_duplicate_code_rejected_and_company_uniqueness(self):
        response = self.client.post(self.url("product", "create"), self.product_data(code=" cappuccino "))
        self.assertContains(response, "Mã sản phẩm đã tồn tại.")
        self.assertEqual(self.client.post(self.url("product", "create"), self.product_data(code="PRIVATE_PRODUCT")).status_code, 302)

    def test_product_invalid_form_retains_inputs_and_field_errors(self):
        for field in ("code", "name", "costing_uom"):
            response = self.client.post(self.url("product", "create"), self.product_data(**{field: ""}))
            self.assertContains(response, "Không thể lưu sản phẩm.")
            self.assertIn(field, response.context["form"].errors)
            self.assertContains(response, 'aria-invalid="true"')

    def test_product_edit_and_detail_preserve_created_at(self):
        created_at = self.product.created_at
        response = self.client.post(self.url("product", "edit", self.product), self.product_data(code="CAPPUCCINO", name="Cà phê đã sửa", is_active=""))
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Cà phê đã sửa")
        self.assertFalse(self.product.is_active)
        self.assertEqual(self.product.created_at, created_at)
        detail = self.client.get(self.url("product", "detail", self.product))
        self.assertContains(detail, "Đã cập nhật sản phẩm.")
        self.assertContains(detail, "Ngừng hoạt động")
        self.assertContains(detail, "Hàng hóa cà phê")
        self.assertContains(detail, "Đơn vị tính giá thành")

    def test_product_allows_nullable_category_item_and_tax(self):
        response = self.client.post(self.url("product", "create"), self.product_data(category="", output_item="", tax_class_code="", description=""))
        self.assertEqual(response.status_code, 302)
        record = Product.objects.get(organization=self.company, code="NEW_PRODUCT")
        self.assertIsNone(record.category_id)
        self.assertIsNone(record.output_item_id)
        self.assertIsNone(record.tax_class_code)
        self.assertIsNone(record.description)

    def test_product_choices_are_active_friendly_and_company_scoped(self):
        form = ProductForm(workspace=self.workspace())
        self.assertNotIn(self.inactive_category, form.fields["category"].queryset)
        self.assertNotIn(self.foreign_category, form.fields["category"].queryset)
        self.assertEqual(list(form.fields["output_item"].queryset), [self.output])
        self.assertNotIn(self.inactive_unit, form.fields["costing_uom"].queryset)
        self.assertEqual(form.fields["category"].label_from_instance(self.category), "CAFE — Cà phê")
        self.assertEqual(form.fields["costing_uom"].label_from_instance(self.kg), "Kilôgam (kg)")

    def test_product_rejects_inactive_and_foreign_new_references(self):
        for changes, field in (({"category": self.inactive_category.pk}, "category"), ({"category": self.foreign_category.pk}, "category"), ({"output_item": self.inactive_item.pk}, "output_item"), ({"output_item": self.foreign_item.pk}, "output_item"), ({"costing_uom": self.inactive_unit.pk}, "costing_uom")):
            response = self.client.post(self.url("product", "create"), self.product_data(**changes))
            self.assertIn(field, response.context["form"].errors)

    def test_product_can_retain_inactive_references_when_editing(self):
        self.product.category = self.inactive_category
        self.product.output_item = self.inactive_item
        self.product.costing_uom = self.inactive_unit
        self.product.save()
        response = self.client.post(self.url("product", "edit", self.product), self.product_data(code="CAPPUCCINO", category=self.inactive_category.pk, output_item=self.inactive_item.pk, costing_uom=self.inactive_unit.pk))
        self.assertEqual(response.status_code, 302)

    def test_sku_list_200_and_search_own_and_product_fields(self):
        response = self.client.get(self.url("sku"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Danh mục SKU")
        self.assertNotContains(response, self.foreign_sku.name)
        for query in ("cap_25g", "Cappuccino 25g", "CAPPUCCINO", "Cà phê Cappuccino"):
            self.assertEqual(list(self.client.get(self.url("sku"), {"q": query}).context["records"]), [self.sku])

    def test_sku_product_category_active_filters_include_history(self):
        for filters in ({"product": self.product.pk}, {"category": self.category.pk}, {"active": "true"}):
            self.assertEqual(list(self.client.get(self.url("sku"), filters).context["records"]), [self.sku])
        self.assertEqual(list(self.client.get(self.url("sku"), {"is_active": "false"}).context["records"]), [self.inactive_sku])
        self.assertEqual(list(self.client.get(self.url("sku"), {"product": self.other_product.pk}).context["records"]), [self.inactive_sku])

    def test_sku_create_valid_normalizes_without_changing_quantity(self):
        response = self.client.post(self.url("sku", "create"), self.sku_data(organization=self.other.pk, attributes='{"override":true}'))
        record = Sku.objects.get(organization=self.company, code="NEW_SKU")
        self.assertRedirects(response, self.url("sku", "detail", record), fetch_redirect_response=False)
        self.assertEqual(record.name, "SKU mới")
        self.assertEqual(record.barcode, "8930002")
        self.assertEqual(record.net_quantity, Decimal("25.125"))
        self.assertEqual(record.net_quantity_uom, self.g)
        self.assertEqual(record.sales_uom, self.pack)
        self.assertEqual(record.sell_item, self.output)
        self.assertEqual(record.product, self.product)
        self.assertEqual(record.attributes, {})
        self.assertContains(self.client.get(self.url("sku", "detail", record)), "Đã tạo SKU.")

    def test_sku_duplicate_code_rejected_and_company_uniqueness(self):
        response = self.client.post(self.url("sku", "create"), self.sku_data(code=" cap_25g "))
        self.assertContains(response, "Mã SKU đã tồn tại.")
        self.assertEqual(self.client.post(self.url("sku", "create"), self.sku_data(code="PRIVATE_SKU")).status_code, 302)

    def test_barcode_unique_after_trim_and_edit_own_barcode_allowed(self):
        form = SkuForm(data=self.sku_data(barcode=" 8930001 "), workspace=self.workspace())
        self.assertFalse(form.is_valid())
        self.assertIn("barcode", form.errors)
        response = self.client.post(self.url("sku", "create"), self.sku_data(barcode="8930001"))
        self.assertContains(response, "Mã vạch đã tồn tại.")
        self.assertEqual(self.client.post(self.url("sku", "edit", self.sku), self.sku_data(code="CAP_25G", barcode="8930001")).status_code, 302)

    def test_blank_barcodes_normalize_to_null_and_can_be_reused(self):
        for index in range(2):
            response = self.client.post(self.url("sku", "create"), self.sku_data(code=f"NO_BARCODE_{index}", barcode="   ", sell_item=""))
            self.assertEqual(response.status_code, 302)
            record = Sku.objects.get(organization=self.company, code=f"NO_BARCODE_{index}")
            self.assertIsNone(record.barcode)
            self.assertIsNone(record.sell_item_id)

    def test_barcode_case_preserved_and_unique_only_within_company(self):
        self.foreign_sku.barcode = "BARCode"
        self.foreign_sku.save()
        response = self.client.post(self.url("sku", "create"), self.sku_data(barcode=" BARCode "))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Sku.objects.get(organization=self.company, code="NEW_SKU").barcode, "BARCode")

    def test_sku_missing_product_and_other_required_fields(self):
        for field in ("product", "code", "name", "sales_uom", "net_quantity", "net_quantity_uom"):
            response = self.client.post(self.url("sku", "create"), self.sku_data(**{field: ""}))
            self.assertContains(response, "Không thể lưu SKU.")
            self.assertIn(field, response.context["form"].errors)
        self.assertContains(self.client.post(self.url("sku", "create"), self.sku_data(product="")), "Vui lòng chọn sản phẩm.")

    def test_invalid_weights_quantities_precision_and_non_finite_values(self):
        for value in ("0", "-1", "NaN", "Infinity", "0.123456789", "9" * 30):
            response = self.client.post(self.url("sku", "create"), self.sku_data(net_quantity=value))
            self.assertIn("net_quantity", response.context["form"].errors)
        self.assertContains(self.client.post(self.url("sku", "create"), self.sku_data(net_quantity="0")), "Lượng tịnh phải lớn hơn 0.")

    def test_non_mass_net_quantity_and_small_positive_quantity_supported(self):
        for unit, quantity, code in ((self.pack, "2", "COUNT_SKU"), (self.g, "0.00000001", "MIN_QUANTITY")):
            response = self.client.post(self.url("sku", "create"), self.sku_data(code=code, barcode="", net_quantity=quantity, net_quantity_uom=unit.pk))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(Sku.objects.get(organization=self.company, code=code).net_quantity, Decimal(quantity))

    def test_sku_edit_preserves_attributes_and_created_at(self):
        created_at = self.sku.created_at
        response = self.client.post(self.url("sku", "edit", self.sku), self.sku_data(code="CAP_25G", name="Quy cách đã sửa", barcode="8930001", attributes="{}", is_active=""))
        self.assertEqual(response.status_code, 302)
        self.sku.refresh_from_db()
        self.assertEqual(self.sku.name, "Quy cách đã sửa")
        self.assertEqual(self.sku.attributes, {"legacy_variant": "CHOCO"})
        self.assertEqual(self.sku.created_at, created_at)
        self.assertFalse(self.sku.is_active)
        self.assertContains(self.client.get(self.url("sku", "detail", self.sku)), "Đã cập nhật SKU.")

    def test_sku_detail_numeric_and_date_formatting(self):
        self.sku.net_quantity = Decimal("1250.50000000")
        self.sku.created_at = datetime(2026, 10, 7, 5, 15, tzinfo=dt_timezone.utc)
        self.sku.save()
        detail = self.client.get(self.url("sku", "detail", self.sku))
        for text in ("1.250,5", "Gam (g)", "Gói (gói)", "07/10/2026 12:15", "Cà phê Cappuccino"):
            self.assertContains(detail, text)
        self.assertNotContains(detail, "legacy_variant")
        edit = self.client.get(self.url("sku", "edit", self.sku))
        self.assertContains(edit, 'value="1250.5"')
        self.assertNotContains(edit, "1250.50000000")

    def test_inactive_product_hidden_for_create_but_existing_sku_editable(self):
        self.product.is_active = False
        self.product.save()
        form = SkuForm(workspace=self.workspace())
        self.assertNotIn(self.product, form.fields["product"].queryset)
        response = self.client.post(self.url("sku", "create"), self.sku_data())
        self.assertIn("product", response.context["form"].errors)
        self.assertEqual(self.client.get(self.url("sku", "detail", self.sku)).status_code, 200)
        response = self.client.post(self.url("sku", "edit", self.sku), self.sku_data(code="CAP_25G", barcode="8930001"))
        self.assertEqual(response.status_code, 302)

    def test_sku_inactive_and_foreign_references_rejected_for_create(self):
        for changes, field in (({"product": self.foreign_product.pk}, "product"), ({"product": self.other_product.pk}, "product"), ({"sell_item": self.inactive_item.pk}, "sell_item"), ({"sell_item": self.foreign_item.pk}, "sell_item"), ({"sales_uom": self.inactive_unit.pk}, "sales_uom"), ({"net_quantity_uom": self.inactive_unit.pk}, "net_quantity_uom")):
            response = self.client.post(self.url("sku", "create"), self.sku_data(**changes))
            self.assertIn(field, response.context["form"].errors)

    def test_sku_retained_inactive_units_and_item_allowed_on_edit(self):
        self.sku.sales_uom = self.inactive_unit
        self.sku.net_quantity_uom = self.inactive_unit
        self.sku.sell_item = self.inactive_item
        self.sku.save()
        response = self.client.post(self.url("sku", "edit", self.sku), self.sku_data(code="CAP_25G", barcode="8930001", sales_uom=self.inactive_unit.pk, net_quantity_uom=self.inactive_unit.pk, sell_item=self.inactive_item.pk))
        self.assertEqual(response.status_code, 302)

    def test_sku_dropdowns_friendly_scoped_and_exclude_json_audit_fields(self):
        for form, fields in ((ProductForm(workspace=self.workspace()), PRODUCT_FIELDS), (SkuForm(workspace=self.workspace()), SKU_FIELDS)):
            self.assertEqual(tuple(form.fields), fields)
            for field in ("organization", "id", "created_at", "updated_at", "attributes", "metadata"):
                self.assertNotIn(field, form.fields)
        form = SkuForm(workspace=self.workspace())
        self.assertEqual(list(form.fields["product"].queryset), [self.product])
        self.assertEqual(form.fields["product"].label_from_instance(self.product), "CAPPUCCINO — Cà phê Cappuccino")
        self.assertEqual(form.fields["net_quantity_uom"].label_from_instance(self.g), "Gam (g)")

    def test_sort_both_directions_and_invalid_sort_whitelist(self):
        for resource, model, mapping in (("product", Product, {"code": "code", "name": "name", "category": "category__code", "created_at": "created_at"}), ("sku", Sku, {"code": "code", "name": "name", "product": "product__code", "created_at": "created_at"})):
            for parameter, field in mapping.items():
                for prefix in ("", "-"):
                    response = self.client.get(self.url(resource), {"sort": prefix + parameter})
                    self.assertEqual([row.pk for row in response.context["records"]], list(model.objects.filter(organization=self.company).order_by(prefix + field, "pk").values_list("pk", flat=True)))
            for invalid in ("--code", "organization_id", "product__organization__name"):
                self.assertEqual(self.client.get(self.url(resource), {"sort": invalid}).context["current_sort"], "code")

    def test_pagination_options_and_query_state_for_both_modules(self):
        Product.objects.bulk_create([Product(organization=self.company, code=f"PAGE_{i:03}", name=f"Sản phẩm {i}", costing_uom=self.kg) for i in range(101)])
        Sku.objects.bulk_create([Sku(organization=self.company, product=self.product, code=f"PAGE_{i:03}", name=f"SKU {i}", sales_uom=self.pack, net_quantity=1, net_quantity_uom=self.pack) for i in range(101)])
        for resource in ("product", "sku"):
            for size in (25, 50, 100):
                response = self.client.get(self.url(resource), {"q": "PAGE", "sort": "-code", "per_page": size, "page": 2})
                self.assertEqual(response.context["page_obj"].number, 2)
                self.assertEqual(len(response.context["records"]), min(size, 101 - size))
                self.assertEqual(response.context["per_page"], size)
                self.assertContains(response, "q=PAGE&amp;sort=-code")
            self.assertEqual(self.client.get(self.url(resource), {"per_page": "999"}).context["per_page"], 25)

    def test_invalid_and_foreign_filter_ids_return_empty_results(self):
        for resource, field in (("product", "category"), ("product", "costing_uom"), ("sku", "product"), ("sku", "category")):
            for value in ("bad", "9" * 100, "-1", "１２"):
                self.assertEqual(list(self.client.get(self.url(resource), {field: value}).context["records"]), [])
        self.assertEqual(list(self.client.get(self.url("sku"), {"product": self.foreign_product.pk}).context["records"]), [])

    def test_empty_states_without_and_with_filters(self):
        for resource in ("product", "sku"):
            self.assertContains(self.client.get(self.url(resource), {"q": "no-results"}), "Không có kết quả phù hợp.")
        Sku.objects.filter(organization=self.company).delete()
        Product.objects.filter(organization=self.company).delete()
        self.assertContains(self.client.get(self.url("sku")), "Chưa có SKU.")
        self.assertContains(self.client.get(self.url("product")), "Chưa có sản phẩm.")

    def test_htmx_partials_restore_validation_and_success_redirect(self):
        for resource, record, payload in (("product", self.product, self.product_data()), ("sku", self.sku, self.sku_data())):
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
            self.assertTemplateUsed(response, f"product/partials/{resource}_rows.html")
            self.assertNotContains(response, "<!doctype")
            self.assertIn("HX-Request", response["Vary"])
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
            self.assertTemplateUsed(response, "product/catalog_list.html")
            self.assertContains(response, "<!doctype")
            response = self.client.get(self.url(resource, "detail", record), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "product/partials/catalog_detail_content.html")
            response = self.client.post(self.url(resource, "create"), {}, HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_form_content.html")
            self.assertNotIn("HX-Redirect", response)
            response = self.client.post(self.url(resource, "create"), payload, HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertIn(f"/product/{'products' if resource == 'product' else 'skus'}/", response["HX-Redirect"])

    def test_company_boundaries_for_detail_edit_and_bad_legacy_sku_product(self):
        for resource, record in (("product", self.foreign_product), ("sku", self.foreign_sku)):
            for action in ("detail", "edit"):
                self.assertEqual(self.client.get(self.url(resource, action, record)).status_code, 404)
            self.assertEqual(self.client.post(self.url(resource, "edit", record), {}).status_code, 404)
            oversized = reverse(f"product:{resource}_detail", args=[10 ** 100])
            self.assertEqual(self.client.get(oversized).status_code, 404)
        self.sku.product = self.foreign_product
        self.sku.save()
        self.assertNotContains(self.client.get(self.url("sku")), self.sku.name)
        self.assertEqual(self.client.get(self.url("sku", "detail", self.sku)).status_code, 404)

    def test_anonymous_no_auth_no_membership_queries_and_navigation_active(self):
        with patch.object(OrganizationMember.objects, "filter", side_effect=AssertionError("Membership query")), CaptureQueriesContext(connection) as queries:
            for resource, record in (("product", self.product), ("sku", self.sku)):
                for action in ("list", "detail", "create", "edit"):
                    response = self.client.get(self.url(resource, action, record if action in ("detail", "edit") else None))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, f'href="{self.url(resource)}" aria-current="page"')
                    self.assertContains(response, 'aria-current="page"', count=1)
                    self.assertNotIn("sessionid", response.cookies)
                    for text in ("Đăng nhập", "Đăng xuất", "organization-switch"):
                        self.assertNotContains(response, text)
        self.assertFalse(any("organization_member" in query["sql"] for query in queries))

    def test_csrf_enforced_for_create_and_edit(self):
        client = Client(enforce_csrf_checks=True)
        for resource, record, payload in (("product", self.product, self.product_data(code="CAPPUCCINO")), ("sku", self.sku, self.sku_data(code="CAP_25G", barcode="8930001"))):
            for action in ("create", "edit"):
                self.assertEqual(client.post(self.url(resource, action, record if action == "edit" else None), payload).status_code, 403)
            client.get(self.url(resource, "edit", record))
            self.assertEqual(client.post(self.url(resource, "edit", record), payload, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 302)

    def test_optimized_querysets_have_no_n_plus_one(self):
        Product.objects.bulk_create([Product(organization=self.company, category=self.category, output_item=self.output, code=f"Q{i}", name="Sản phẩm", costing_uom=self.kg) for i in range(8)])
        Sku.objects.bulk_create([Sku(organization=self.company, product=self.product, sell_item=self.output, code=f"Q{i}", name="SKU", sales_uom=self.pack, net_quantity=25, net_quantity_uom=self.g) for i in range(8)])
        with self.assertNumQueries(1):
            for record in product_queryset(organization=self.company):
                _ = record.category.name if record.category else None
                _ = record.output_item.name if record.output_item else None
                _ = record.costing_uom.name
        with self.assertNumQueries(1):
            for record in sku_queryset(organization=self.company):
                _ = record.product.name, record.sales_uom.name, record.net_quantity_uom.name
                _ = record.product.category.name if record.product.category else None
                _ = record.sell_item.name if record.sell_item else None

    def test_dropdown_rendering_query_count_independent_of_option_count(self):
        form = SkuForm(workspace=self.workspace())
        with CaptureQueriesContext(connection) as before:
            str(form["product"])
        Product.objects.bulk_create([Product(organization=self.company, code=f"OPTION_{i}", name="Sản phẩm", costing_uom=self.kg) for i in range(10)])
        form = SkuForm(workspace=self.workspace())
        with CaptureQueriesContext(connection) as after:
            str(form["product"])
        self.assertEqual(len(before), len(after))
        self.assertEqual(len(after), 1)

    def test_service_refreshes_product_item_and_unit_state_inside_transaction(self):
        for model, field, form_class, data, service, target in (
            (Product, "product", SkuForm, self.sku_data(), save_sku, self.product),
            (Item, "sell_item", SkuForm, self.sku_data(), save_sku, self.output),
            (Uom, "sales_uom", SkuForm, self.sku_data(), save_sku, self.pack),
            (Uom, "costing_uom", ProductForm, self.product_data(), save_product, self.kg),
        ):
            form = form_class(data=data, workspace=self.workspace())
            self.assertTrue(form.is_valid(), form.errors)
            model.objects.filter(pk=target.pk).update(is_active=False)
            with self.assertRaises(ValidationError) as error:
                service(workspace=self.workspace(), data=form.cleaned_data)
            self.assertIn(field, error.exception.message_dict)
            model.objects.filter(pk=target.pk).update(is_active=True)

    def test_services_enforce_scope_without_view_and_reject_foreign_references(self):
        for form_class, data, service, resource, foreign in ((ProductForm, self.product_data(), save_product, "product", self.foreign_product), (SkuForm, self.sku_data(), save_sku, "sku", self.foreign_sku)):
            form = form_class(data=data, workspace=self.workspace())
            self.assertTrue(form.is_valid(), form.errors)
            denied = replace(self.workspace(), permissions=replace(self.workspace().permissions, **{f"can_create_{resource}": False}))
            with self.assertRaises(PermissionDenied):
                service(workspace=denied, data=form.cleaned_data)
            with self.assertRaises(ValidationError):
                service(workspace=self.workspace(), data=form.cleaned_data, instance=foreign)
        form = SkuForm(data=self.sku_data(), workspace=self.workspace())
        self.assertTrue(form.is_valid())
        form.cleaned_data["product"] = self.foreign_product
        with self.assertRaises(ValidationError) as error:
            save_sku(workspace=self.workspace(), data=form.cleaned_data)
        self.assertIn("product", error.exception.message_dict)

    def test_unique_races_map_to_friendly_product_sku_and_barcode_errors(self):
        for form_class, data, service, validator, model, message in ((ProductForm, self.product_data(), save_product, "validate_product", Product, "Mã sản phẩm đã tồn tại."), (SkuForm, self.sku_data(), save_sku, "validate_sku", Sku, "Mã SKU đã tồn tại.")):
            form = form_class(data=data, workspace=self.workspace())
            self.assertTrue(form.is_valid(), form.errors)
            values = dict(form.cleaned_data)
            model.objects.create(organization=self.company, **values)
            with patch(f"apps.product.services.{validator}"), self.assertRaisesMessage(ValidationError, message):
                service(workspace=self.workspace(), data=form.cleaned_data)
        form = SkuForm(data=self.sku_data(code="BARCODE_RACE", barcode="RACE_BAR"), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        Sku.objects.create(organization=self.company, product=self.product, code="OTHER_CODE", name="Concurrent", barcode="RACE_BAR", sales_uom=self.pack, net_quantity=1, net_quantity_uom=self.pack)
        with patch("apps.product.services.validate_sku"), self.assertRaises(ValidationError) as error:
            save_sku(workspace=self.workspace(), data=form.cleaned_data)
        self.assertEqual(error.exception.message_dict, {"barcode": ["Mã vạch đã tồn tại."]})

    def test_net_quantity_database_check_and_service_error_are_sanitized(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Sku.objects.create(organization=self.company, product=self.product, code="INVALID", name="Invalid", sales_uom=self.pack, net_quantity=0, net_quantity_uom=self.g)
        form = SkuForm(data=self.sku_data(), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        form.cleaned_data["net_quantity"] = Decimal("0")
        with patch("apps.product.services.validate_sku"), self.assertRaises(ValidationError) as error:
            save_sku(workspace=self.workspace(), data=form.cleaned_data)
        self.assertIn("net_quantity", error.exception.message_dict)
        self.assertNotIn("CHECK", str(error.exception))
