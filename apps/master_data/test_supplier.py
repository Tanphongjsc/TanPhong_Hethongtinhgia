"""Supplier/price vertical slice on isolated PostgreSQL, including real checks."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Currency, Item, Organization, Supplier, SupplierPrice, Uom, UomCategory
from .access import get_workspace
from .forms import SupplierForm, SupplierPriceForm
from .selectors import supplier_queryset, supplier_price_queryset
from .services import save_supplier, save_supplier_price


class SupplierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="COMPANY", name="Công ty nội bộ")
        cls.other = Organization.objects.create(code="OTHER", name="Công ty khác")
        cls.vnd = Currency.objects.create(code="VND", name="Đồng Việt Nam", decimal_places=0)
        cls.usd = Currency.objects.create(code="USD", name="Đô la Mỹ", decimal_places=2)
        cls.mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        cls.count = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        cls.kg = Uom.objects.create(category=cls.mass, code="KG", name="Kilôgam", symbol="kg")
        cls.pack = Uom.objects.create(category=cls.count, code="PACK", name="Gói", symbol="gói")
        cls.item = Item.objects.create(organization=cls.company, code="COFFEE", name="Cà phê nguyên liệu", item_type="RAW_MATERIAL", base_uom=cls.kg)
        cls.other_item = Item.objects.create(organization=cls.other, code="SECRET_ITEM", name="Vật tư công ty khác", item_type="RAW_MATERIAL", base_uom=cls.kg)
        cls.supplier = Supplier.objects.create(organization=cls.company, code="NCC_A", name="Nhà cung cấp A", tax_code="0101234567", default_currency_code=cls.vnd)
        cls.inactive = Supplier.objects.create(organization=cls.company, code="NCC_B", name="Nhà cung cấp B", is_active=False, default_currency_code=cls.usd)
        cls.other_supplier = Supplier.objects.create(organization=cls.other, code="SECRET_SUPPLIER", name="Nhà cung cấp riêng")
        cls.today = timezone.localdate()
        cls.price = SupplierPrice.objects.create(organization=cls.company, supplier=cls.supplier, item=cls.item,
            price_uom=cls.kg, currency_code=cls.vnd, min_qty=Decimal("100"), unit_price=Decimal("125000.12345678"),
            effective_from=cls.today - timedelta(days=10), effective_to=cls.today + timedelta(days=10))
        cls.records = {"supplier": cls.supplier, "supplier_price": cls.price}

    def setUp(self):
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        company.enable()
        self.addCleanup(company.disable)

    def url(self, resource, action="list", record=None):
        return reverse(f"master_data:{resource}_{action}", args=[record.pk] if record is not None else [])

    def payload(self, resource="supplier_price", **changes):
        data = dict(code=" ncc_new ", name=" Nhà cung cấp mới ", tax_code=" 0100000001 ",
            default_currency_code=self.vnd.pk, payment_terms=" Thanh toán sau 30 ngày ", is_active="on") if resource == "supplier" else dict(
            supplier=str(self.supplier.pk), item=str(self.item.pk), price_uom=str(self.kg.pk), currency_code=self.vnd.pk,
            unit_price="130000.12345678", min_qty="0", tax_inclusive="", tax_rate="0.1", tax_recoverable_ratio="1",
            effective_from="2026-06-01", effective_to="2026-12-31", source_type=" Báo giá ", source_reference=" BG-2026 ")
        data.update(changes)
        return data

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url("supplier")))

    def price_values(self, **changes):
        form = SupplierPriceForm(self.payload(**changes), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def test_anonymous_lists_and_detail_without_membership(self):
        with CaptureQueriesContext(connection) as queries:
            for resource, record in self.records.items():
                response = self.client.get(self.url(resource))
                self.assertEqual(response.status_code, 200)
                self.assertIn(record, response.context["records"])
                self.assertContains(response, f'href="{self.url(resource)}" aria-current="page"')
                self.assertContains(response, 'aria-current="page"', count=1)
                self.assertNotIn("sessionid", response.cookies)
                response = self.client.get(self.url(resource, "detail", record))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "master_data/reference_data_detail.html")
        self.assertFalse(any("organization_member" in query["sql"] for query in queries))

    def test_supplier_search_code_name_and_tax_code(self):
        for query in ("ncc_a", "Nhà cung cấp A", "0101234567"):
            with self.subTest(query=query):
                response = self.client.get(self.url("supplier"), {"q": query})
                self.assertEqual(list(response.context["records"]), [self.supplier])

    def test_supplier_active_and_currency_filters(self):
        for filters, expected in (({"active": "true"}, self.supplier), ({"is_active": "false"}, self.inactive),
            ({"currency": "USD"}, self.inactive)):
            self.assertEqual(list(self.client.get(self.url("supplier"), filters).context["records"]), [expected])

    def test_supplier_create_normalizes_and_assigns_internal_company(self):
        response = self.client.post(self.url("supplier", "create"), self.payload("supplier", organization=self.other.pk), follow=True)
        self.assertEqual(response.status_code, 200)
        saved = Supplier.objects.get(code="NCC_NEW")
        self.assertEqual(saved.organization_id, self.company.pk)
        self.assertEqual(saved.name, "Nhà cung cấp mới")
        self.assertEqual(saved.tax_code, "0100000001")
        self.assertEqual(saved.payment_terms, "Thanh toán sau 30 ngày")
        self.assertContains(response, "Đã tạo nhà cung cấp.")

    def test_duplicate_supplier_code_rejected_after_normalization(self):
        response = self.client.post(self.url("supplier", "create"), self.payload("supplier", code=" ncc_a "))
        self.assertContains(response, "Mã nhà cung cấp đã tồn tại.")
        self.assertEqual(Supplier.objects.filter(organization=self.company).count(), 2)

    def test_supplier_code_can_exist_in_another_company(self):
        response = self.client.post(self.url("supplier", "create"), self.payload("supplier", code=self.other_supplier.code))
        self.assertEqual(response.status_code, 302)

    def test_supplier_invalid_form_keeps_input_and_field_errors(self):
        response = self.client.post(self.url("supplier", "create"), self.payload("supplier", code="", name=""))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vui lòng nhập mã nhà cung cấp.")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, "0100000001")
        self.assertContains(response, "Vui lòng kiểm tra các trường được đánh dấu.")

    def test_supplier_edit_preserves_created_at_and_supports_deactivation(self):
        response = self.client.post(self.url("supplier", "edit", self.supplier),
            self.payload("supplier", code="ncc_a", name=" Nhà cung cấp A cập nhật ", is_active=""), follow=True)
        self.assertContains(response, "Đã cập nhật nhà cung cấp.")
        saved = Supplier.objects.get(pk=self.supplier.pk)
        self.assertEqual(saved.name, "Nhà cung cấp A cập nhật")
        self.assertFalse(saved.is_active)
        self.assertEqual(saved.created_at, self.supplier.created_at)
        self.assertGreater(saved.updated_at, self.supplier.updated_at)

    def test_price_search_supplier_and_item(self):
        for query in ("ncc_a", "Nhà cung cấp A", "coffee", "Cà phê nguyên liệu"):
            self.assertEqual(list(self.client.get(self.url("supplier_price"), {"q": query}).context["records"]), [self.price])

    def test_price_reference_filters(self):
        for parameter, value in (("supplier", self.supplier.pk), ("item", self.item.pk), ("currency", self.vnd.pk), ("uom", self.kg.pk)):
            response = self.client.get(self.url("supplier_price"), {parameter: value})
            self.assertEqual(list(response.context["records"]), [self.price])
            self.assertContains(response, f'value="{value}" selected')
        for filters in ({"currency": self.usd.pk}, {"uom": self.pack.pk}, {"supplier": self.other_supplier.pk}, {"item": self.other_item.pk}):
            self.assertEqual(list(self.client.get(self.url("supplier_price"), filters).context["records"]), [])

    def test_malformed_filter_ids_are_safe(self):
        for parameter in ("supplier", "item", "uom"):
            for value in ("bad", "-1", "9" * 100, "１２"):
                self.assertEqual(list(self.client.get(self.url("supplier_price"), {parameter: value}).context["records"]), [])

    def test_sort_both_directions(self):
        SupplierPrice.objects.create(organization=self.company, supplier=self.inactive, item=self.item, price_uom=self.pack,
            currency_code=self.usd, unit_price=1, effective_from=date(2020, 1, 1))
        mappings = {"supplier": {"code": "code", "name": "name", "created_at": "created_at"},
            "supplier_price": {"supplier": "supplier__code", "item": "item__code", "unit_price": "unit_price", "effective_from": "effective_from"}}
        for resource, fields in mappings.items():
            for parameter, field in fields.items():
                for prefix in ("", "-"):
                    response = self.client.get(self.url(resource), {"sort": prefix + parameter})
                    visible = [record.pk for record in response.context["records"]]
                    expected = self.records[resource].__class__.objects.filter(pk__in=visible).order_by(prefix + field, "pk").values_list("pk", flat=True)
                    self.assertEqual(visible, list(expected))
        for resource, default in (("supplier", "code"), ("supplier_price", "-effective_from")):
            self.assertEqual(self.client.get(self.url(resource), {"sort": "bad", "per_page": 999}).context["current_sort"], default)

    def test_database_pagination_and_query_state(self):
        Supplier.objects.bulk_create([Supplier(organization=self.company, code=f"TEST_{i:03}", name=f"Nhà cung cấp {i}") for i in range(101)])
        SupplierPrice.objects.bulk_create([SupplierPrice(organization=self.company, supplier=self.supplier, item=self.item,
            price_uom=self.kg, currency_code=self.vnd, unit_price=i, effective_from=self.today) for i in range(101)])
        for resource in self.records:
            for size in (25, 50, 100):
                filters = {"per_page": size, "page": 2, "q": "test" if resource == "supplier" else "coffee"}
                response = self.client.get(self.url(resource), filters)
                self.assertEqual(response.context["page_obj"].number, 2)
                self.assertEqual(response.context["per_page"], size)
                self.assertLessEqual(len(response.context["records"]), size)
                self.assertContains(response, f'per_page={size}')
                self.assertContains(response, 'hx-target="#reference-data-table"')

    def test_price_create_valid_preserves_precision_and_null_actor(self):
        response = self.client.post(self.url("supplier_price", "create"), self.payload(organization=self.other.pk,
            created_by="00000000-0000-0000-0000-000000000001", status="EFFECTIVE"), follow=True)
        self.assertContains(response, "Đã tạo giá nhà cung cấp.")
        saved = SupplierPrice.objects.exclude(pk=self.price.pk).get()
        self.assertEqual(saved.organization_id, self.company.pk)
        self.assertEqual(saved.unit_price, Decimal("130000.12345678"))
        self.assertIsNone(saved.created_by)
        self.assertEqual(saved.status, "DRAFT")
        self.assertEqual(saved.source_type, "Báo giá")
        self.assertEqual(saved.source_reference, "BG-2026")
        self.assertContains(response, "130.000,12345678 VND")

    def test_price_edit_preserves_status_creation_and_other_periods(self):
        previous = save_supplier_price(workspace=self.workspace(), data=self.price_values(effective_from="2025-01-01", effective_to="2025-12-31"))
        self.price.status = "APPROVED"
        self.price.save()
        response = self.client.post(self.url("supplier_price", "edit", self.price), self.payload(unit_price="135000", status="RETIRED"), follow=True)
        self.assertContains(response, "Đã cập nhật giá nhà cung cấp.")
        saved = SupplierPrice.objects.get(pk=self.price.pk)
        self.assertEqual(saved.status, "APPROVED")
        self.assertEqual(saved.unit_price, Decimal("135000"))
        self.assertEqual(saved.created_at, self.price.created_at)
        previous.refresh_from_db()
        self.assertEqual(previous.unit_price, Decimal("130000.12345678"))

    def test_zero_price_and_quantity_are_allowed_by_database(self):
        response = self.client.post(self.url("supplier_price", "create"), self.payload(unit_price="0", min_qty="0"))
        self.assertEqual(response.status_code, 302)

    def test_invalid_unit_price_and_quantity_rejected(self):
        for field in ("unit_price", "min_qty"):
            for value in ("-0.00000001", "NaN", "Infinity", "bad", "1.123456789", "1" * 30):
                response = self.client.post(self.url("supplier_price", "create"), self.payload(**{field: value}))
                self.assertIn(field, response.context["form"].errors)
        self.assertEqual(SupplierPrice.objects.count(), 1)

    def test_missing_required_price_fields(self):
        for field in ("supplier", "item", "price_uom", "currency_code", "unit_price", "effective_from"):
            response = self.client.post(self.url("supplier_price", "create"), self.payload(**{field: ""}))
            self.assertIn(field, response.context["form"].errors)
            self.assertContains(response, 'aria-invalid="true"')

    def test_invalid_date_range_including_equal_dates(self):
        for end in ("2026-05-31", "2026-06-01", "bad"):
            response = self.client.post(self.url("supplier_price", "create"), self.payload(effective_to=end))
            self.assertIn("effective_to", response.context["form"].errors)
        response = self.client.post(self.url("supplier_price", "create"), self.payload(effective_to=""))
        self.assertEqual(response.status_code, 302)

    def test_tax_boundaries_and_precision(self):
        for field in ("tax_rate", "tax_recoverable_ratio"):
            for value in ("-0.00000001", "1.00000001", "NaN"):
                response = self.client.post(self.url("supplier_price", "create"), self.payload(**{field: value}))
                self.assertIn(field, response.context["form"].errors)
            for value in ("0", "1"):
                form = SupplierPriceForm(self.payload(**{field: value}), workspace=self.workspace())
                self.assertTrue(form.is_valid(), form.errors)
        response = self.client.post(self.url("supplier_price", "create"), self.payload(tax_rate="", tax_recoverable_ratio="0"))
        self.assertEqual(response.status_code, 302)

    def test_duplicate_and_overlapping_price_periods_follow_existing_schema(self):
        values = self.price_values()
        first = save_supplier_price(workspace=self.workspace(), data=values)
        second = save_supplier_price(workspace=self.workspace(), data=values)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(SupplierPrice.objects.count(), 3)

    def test_different_item_uom_stored_without_conversion(self):
        saved = save_supplier_price(workspace=self.workspace(), data=self.price_values(price_uom=str(self.pack.pk)))
        self.assertEqual(saved.price_uom_id, self.pack.pk)
        self.assertEqual(saved.unit_price, Decimal("130000.12345678"))

    def test_effective_status_boundaries_and_record_status_filter(self):
        cases = ((self.today + timedelta(days=1), None, "FUTURE"),
            (self.today - timedelta(days=5), self.today - timedelta(days=1), "EXPIRED"),
            (self.today, None, "EFFECTIVE"), (self.today - timedelta(days=1), self.today, "EFFECTIVE"))
        for start, end, expected in cases:
            self.price.effective_from, self.price.effective_to = start, end
            self.price.save()
            record = supplier_price_queryset(organization=self.company, today=self.today).get(pk=self.price.pk)
            self.assertEqual(record.date_status, expected)
            with patch("apps.master_data.selectors.timezone.localdate", return_value=self.today):
                response = self.client.get(self.url("supplier_price"), {"effective": expected, "status": "DRAFT"})
                self.assertEqual(list(response.context["records"]), [record])
                self.assertContains(response, "Nháp")
                self.assertEqual(list(self.client.get(self.url("supplier_price"), {"status": "APPROVED"}).context["records"]), [])

    def test_active_choices_and_retained_inactive_history(self):
        for resource, form_class in (("supplier", SupplierForm), ("supplier_price", SupplierPriceForm)):
            record = self.records[resource]
            fields = ("default_currency_code",) if resource == "supplier" else ("supplier", "item", "currency_code", "price_uom")
            for field in fields:
                related = getattr(record, field)
                related.is_active = False
                related.save()
                create = form_class(workspace=self.workspace())
                edit = form_class(workspace=self.workspace(), instance=record)
                self.assertNotIn(related, create.fields[field].queryset)
                self.assertIn(related, edit.fields[field].queryset)
            data = self.payload(resource)
            if resource == "supplier":
                data["code"] = record.code
            form = form_class(data, workspace=self.workspace(), instance=record)
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(self.client.get(self.url(resource, "detail", record)).status_code, 200)

    def test_company_scope_in_lists_forms_detail_and_edits(self):
        foreign_price = SupplierPrice.objects.create(organization=self.other, supplier=self.other_supplier,
            item=self.other_item, price_uom=self.kg, currency_code=self.vnd, unit_price=1, effective_from=self.today)
        inconsistent = SupplierPrice.objects.create(organization=self.company, supplier=self.other_supplier,
            item=self.item, price_uom=self.kg, currency_code=self.vnd, unit_price=1, effective_from=self.today)
        form = SupplierPriceForm(workspace=self.workspace())
        self.assertNotIn(self.other_item, form.fields["item"].queryset)
        self.assertNotIn(self.other_supplier, form.fields["supplier"].queryset)
        for resource, record in (("supplier", self.other_supplier), ("supplier_price", foreign_price), ("supplier_price", inconsistent)):
            self.assertNotIn(record, self.client.get(self.url(resource)).context["records"])
            self.assertEqual(self.client.get(self.url(resource, "detail", record)).status_code, 404)
            self.assertEqual(self.client.post(self.url(resource, "edit", record), self.payload(resource)).status_code, 404)
        for field, value in (("item", self.other_item.pk), ("supplier", self.other_supplier.pk)):
            response = self.client.post(self.url("supplier_price", "create"), self.payload(**{field: value}))
            self.assertIn(field, response.context["form"].errors)

    def test_service_reloads_stale_references_and_scopes(self):
        for field, model, reference in (("supplier", Supplier, self.supplier), ("item", Item, self.item),
            ("price_uom", Uom, self.kg), ("currency_code", Currency, self.vnd)):
            values = self.price_values()
            model.objects.filter(pk=reference.pk).update(is_active=False)
            with self.assertRaises(ValidationError) as error:
                save_supplier_price(workspace=self.workspace(), data=values)
            self.assertIn(field, error.exception.message_dict)
            model.objects.filter(pk=reference.pk).update(is_active=True)
        values = self.price_values()
        values["item"] = self.other_item
        with self.assertRaises(ValidationError) as error:
            save_supplier_price(workspace=self.workspace(), data=values)
        self.assertIn("item", error.exception.message_dict)
        self.assertEqual(SupplierPrice.objects.count(), 1)

    def test_database_uniqueness_race_becomes_friendly_error(self):
        form = SupplierForm(self.payload("supplier"), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        data = {**form.cleaned_data, "code": self.supplier.code}
        with patch("apps.master_data.services.validate_supplier"):
            with self.assertRaises(ValidationError) as error:
                save_supplier(workspace=self.workspace(), data=data)
        self.assertEqual(error.exception.message_dict, {"code": ["Mã nhà cung cấp đã tồn tại."]})
        self.assertEqual(Supplier.objects.count(), 3)

    def test_database_checks_and_safe_service_mapping(self):
        values = self.price_values()
        for field, value in (("unit_price", Decimal("-1")), ("min_qty", Decimal("-1")),
            ("tax_rate", Decimal("2")), ("tax_recoverable_ratio", Decimal("2")), ("effective_to", date(2026, 6, 1))):
            with patch("apps.master_data.services.validate_supplier_price"):
                with self.assertRaises(ValidationError) as error:
                    save_supplier_price(workspace=self.workspace(), data={**values, field: value})
            self.assertIn(field, error.exception.message_dict)
            self.assertNotIn("CHECK", str(error.exception))
        with self.assertRaises(IntegrityError), transaction.atomic():
            SupplierPrice.objects.filter(pk=self.price.pk).update(status="BAD_STATUS")
        self.assertEqual(SupplierPrice.objects.count(), 1)

    def test_empty_states_and_htmx_full_history_restoration(self):
        for resource in self.records:
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
            self.assertNotContains(response, "<!DOCTYPE")
            self.assertContains(response, 'hx-push-url="true"')
            self.assertIn("HX-Request", response.headers["Vary"])
            response = self.client.get(self.url(resource), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/reference_data_list.html")
            self.assertContains(self.client.get(self.url(resource), {"q": "missing"}), "Không có kết quả phù hợp.")
        SupplierPrice.objects.all().delete()
        Supplier.objects.all().delete()
        for resource, label in (("supplier", "nhà cung cấp"), ("supplier_price", "giá nhà cung cấp")):
            self.assertContains(self.client.get(self.url(resource)), f"Chưa có {label}.")

    def test_htmx_forms_and_save_redirect(self):
        for resource, record in self.records.items():
            response = self.client.get(self.url(resource, "detail", record), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_detail_content.html")
            response = self.client.post(self.url(resource, "create"), {}, HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_form_content.html")
            self.assertContains(response, "Vui lòng kiểm tra các trường được đánh dấu.")
            response = self.client.post(self.url(resource, "create"), self.payload(resource), HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertIn("HX-Redirect", response.headers)

    def test_csrf_remains_enforced_and_organization_hidden(self):
        client = Client(enforce_csrf_checks=True)
        for resource in self.records:
            url = self.url(resource, "create")
            page = client.get(url)
            self.assertContains(page, 'name="csrfmiddlewaretoken"')
            self.assertNotContains(page, 'name="organization"')
            self.assertNotContains(page, 'name="created_by"')
            self.assertNotContains(page, 'name="status"')
            self.assertEqual(client.post(url, self.payload(resource)).status_code, 403)
            self.assertEqual(client.post(url, self.payload(resource), HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 302)

    def test_related_queries_do_not_grow_with_rows(self):
        with self.assertNumQueries(1):
            for record in supplier_queryset(organization=self.company):
                _ = record.default_currency_code.name
        SupplierPrice.objects.bulk_create([SupplierPrice(organization=self.company, supplier=self.supplier,
            item=self.item, price_uom=self.kg, currency_code=self.vnd, unit_price=i, effective_from=self.today) for i in range(20)])
        with self.assertNumQueries(1):
            for record in supplier_price_queryset(organization=self.company):
                _ = (record.supplier.name, record.item.name, record.price_uom.symbol, record.currency_code.name, record.date_status)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url("supplier_price"))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 8)
        self.assertEqual(len(response.context["records"]), 21)

    def test_number_date_and_tax_display(self):
        self.price.tax_rate = Decimal("0.1")
        self.price.save()
        response = self.client.get(self.url("supplier_price", "detail", self.price))
        self.assertContains(response, "125.000,12345678 VND")
        self.assertContains(response, self.price.effective_from.strftime("%d/%m/%Y"))
        self.assertContains(response, "10%")
        self.assertContains(response, "100%")
        self.assertContains(response, "Không")
        self.assertContains(response, "Hiệu lực theo ngày:")
        self.assertNotContains(response, "125000.12345678")
        form = self.client.get(self.url("supplier_price", "edit", self.price))
        self.assertContains(form, 'value="125000.12345678"')
        self.assertContains(form, 'value="1"')
        self.assertContains(form, "hãy thêm bản ghi mới")
        self.price.refresh_from_db()
        self.assertEqual(self.price.unit_price, Decimal("125000.12345678"))
