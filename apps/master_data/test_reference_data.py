from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Currency, Item, Organization, Uom, UomCategory, UomConversion
from .access import get_workspace
from .forms import CurrencyForm, UomForm, UomConversionForm
from .selectors import uom_queryset, uom_conversion_queryset
from .services import save_currency, save_uom, save_uom_conversion


class ReferenceDataTests(TestCase):
    resources = ("currency", "uom_category", "uom", "uom_conversion")

    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(code="ORG_A", name="Tổ chức A")
        cls.other_org = Organization.objects.create(code="ORG_B", name="Tổ chức B")
        cls.currency = Currency.objects.create(code="VND", name="Việt Nam đồng", decimal_places=0)
        cls.usd = Currency.objects.create(code="USD", name="US Dollar", decimal_places=2, is_active=False)
        cls.mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        cls.volume = UomCategory.objects.create(code="VOLUME", name="Thể tích", dimension_code="VOLUME")
        cls.kg = Uom.objects.create(category=cls.mass, code="KG", name="Kilogram", symbol="kg", precision=6, is_base=True)
        cls.gram = Uom.objects.create(category=cls.mass, code="G", name="Gram", symbol="g", precision=3)
        cls.litre = Uom.objects.create(category=cls.volume, code="L", name="Litre", symbol="l", precision=4)
        cls.item = Item.objects.create(organization=cls.organization, code="MATERIAL_A", name="Nguyên liệu A", item_type="RAW_MATERIAL", base_uom=cls.kg)
        cls.other_item = Item.objects.create(organization=cls.other_org, code="SECRET_ITEM", name="Mặt hàng riêng B", item_type="RAW_MATERIAL", base_uom=cls.kg)
        cls.conversion = UomConversion.objects.create(organization=cls.organization, from_uom=cls.kg, to_uom=cls.gram, factor=Decimal("1000"), effective_from=date(2026, 1, 1))
        cls.shared = UomConversion.objects.create(from_uom=cls.gram, to_uom=cls.kg, factor=Decimal("0.001"), effective_from=date(2025, 1, 1))
        cls.foreign = UomConversion.objects.create(organization=cls.other_org, from_uom=cls.kg, to_uom=cls.litre, item=cls.other_item, factor=Decimal("2"), effective_from=date(2026, 1, 1))
        cls.records = {"currency": cls.currency, "uom_category": cls.mass, "uom": cls.kg, "uom_conversion": cls.conversion}

    def setUp(self):
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.organization.pk)
        company.enable()
        self.addCleanup(company.disable)

    def url(self, resource, action="list", record=None):
        return reverse(f"master_data:{resource}_{action}", args=[record.pk] if record else [])

    def payload(self, resource, **overrides):
        data = {
            "currency": dict(code=" eur ", name=" Euro ", decimal_places="2", is_active="on"),
            "uom_category": dict(code=" length ", name=" Chiều dài ", dimension_code=" length ", description=" Mô tả ", is_active="on"),
            "uom": dict(category=str(self.mass.pk), code=" mg ", name=" Milligram ", symbol=" mg ", precision="9", is_base="", is_active="on"),
            "uom_conversion": dict(from_uom=str(self.kg.pk), to_uom=str(self.gram.pk), factor="1000.000000000001", item="", effective_from="2026-02-01", effective_to="", source_reference=" Tài liệu A "),
        }[resource]
        data.update(overrides)
        return data

    def workspace(self):
        request = RequestFactory().get(self.url("currency"))
        return get_workspace(request)

    def test_all_list_and_detail_pages(self):
        for resource, record in self.records.items():
            with self.subTest(resource=resource):
                response = self.client.get(self.url(resource))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "master_data/reference_data_list.html")
                self.assertIn(record, response.context["records"])
                self.assertContains(response, 'id="reference-data-table"')
                self.assertContains(response, f'href="{self.url(resource)}" aria-current="page"')
                self.assertContains(response, 'aria-current="page"', count=1)
                response = self.client.get(self.url(resource, "detail", record))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "master_data/reference_data_detail.html")

    def test_search_all_supported_fields(self):
        cases = (("currency", "vnd", self.currency), ("currency", "Việt Nam", self.currency),
            ("uom_category", "mass", self.mass), ("uom_category", "Khối lượng", self.mass),
            ("uom", "kilogram", self.kg), ("uom", "kg", self.kg),
            ("uom_conversion", "Kilogram", self.conversion))
        for resource, term, record in cases:
            with self.subTest(resource=resource, term=term):
                self.assertIn(record, self.client.get(self.url(resource), {"q": term}).context["records"])
        self.mass.dimension_code = "WEIGHT"
        self.mass.save()
        self.assertEqual(list(self.client.get(self.url("uom_category"), {"q": "weight"}).context["records"]), [self.mass])
        self.conversion.item = self.item
        self.conversion.save()
        for term in ("material_a", "Nguyên liệu A"):
            self.assertEqual(list(self.client.get(self.url("uom_conversion"), {"q": term}).context["records"]), [self.conversion])

    def test_active_filter_for_shared_reference_tables(self):
        for resource in ("currency", "uom_category", "uom"):
            model = self.records[resource].__class__
            self.records[resource].is_active = False
            self.records[resource].save()
            for parameter in ("active", "is_active"):
                response = self.client.get(self.url(resource), {parameter: "false"})
                self.assertEqual(list(response.context["records"]), list(model.objects.filter(is_active=False).order_by("code")))

    def test_uom_category_and_base_filters(self):
        response = self.client.get(self.url("uom"), {"category": self.mass.pk, "is_base": "true"})
        self.assertEqual(list(response.context["records"]), [self.kg])
        self.assertContains(response, f'value="{self.mass.pk}" selected')
        self.assertEqual(list(self.client.get(self.url("uom"), {"is_base": "false"}).context["records"]), [self.gram, self.litre])

    def test_conversion_filters(self):
        self.conversion.item = self.item
        self.conversion.save()
        for parameters in ({"from_uom": self.kg.pk}, {"to_uom": self.gram.pk}, {"item": self.item.pk}):
            self.assertEqual(list(self.client.get(self.url("uom_conversion"), parameters).context["records"]), [self.conversion])

    def test_invalid_filter_ids_do_not_raise_or_widen_results(self):
        for resource, parameter in (("uom", "category"), ("uom_conversion", "from_uom"), ("uom_conversion", "to_uom"), ("uom_conversion", "item")):
            for value in ("bad", "9" * 100, "１２", "-1"):
                with self.subTest(resource=resource, parameter=parameter, value=value):
                    response = self.client.get(self.url(resource), {parameter: value})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(list(response.context["records"]), [])

    def test_sorting_both_directions_for_every_module(self):
        fields = {"currency": {"code": "code", "name": "name", "decimal_places": "decimal_places"},
            "uom_category": {"code": "code", "name": "name", "dimension_code": "dimension_code"},
            "uom": {"code": "code", "name": "name", "category": "category__code", "precision": "precision"},
            "uom_conversion": {"effective_from": "effective_from", "from_uom": "from_uom__code", "to_uom": "to_uom__code"}}
        for resource, mapping in fields.items():
            for parameter, field in mapping.items():
                for prefix in ("", "-"):
                    with self.subTest(resource=resource, sort=prefix + parameter):
                        response = self.client.get(self.url(resource), {"sort": prefix + parameter})
                        visible = [record.pk for record in response.context["records"]]
                        model = self.records[resource].__class__
                        self.assertEqual(visible, list(model.objects.filter(pk__in=visible).order_by(prefix + field, "pk").values_list("pk", flat=True)))
            response = self.client.get(self.url(resource), {"sort": "--bad", "per_page": "999"})
            self.assertEqual(response.context["per_page"], 25)
            self.assertEqual(response.context["current_sort"], "-effective_from" if resource == "uom_conversion" else "code")

    def test_pagination_preserves_query_and_options(self):
        Uom.objects.bulk_create([Uom(category=self.mass, code=f"TEST_{i:03}", name=f"Test {i}", symbol="t") for i in range(102)])
        for size in (25, 50, 100):
            response = self.client.get(self.url("uom"), {"q": "test", "per_page": size, "sort": "-code", "page": 2})
            self.assertEqual(response.context["per_page"], size)
            self.assertEqual(response.context["page_obj"].number, 2)
            self.assertContains(response, "q=test&amp;per_page=")
            self.assertContains(response, 'hx-target="#reference-data-table"')
        self.assertEqual(len(self.client.get(self.url("uom"), {"per_page": "bad"}).context["records"]), 25)

    def test_create_all_modules_and_normalization(self):
        for resource in self.resources:
            with self.subTest(resource=resource):
                response = self.client.post(self.url(resource, "create"), self.payload(resource), follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f"Đã tạo {response.context['resource_label']}.")
        currency = Currency.objects.get(pk="EUR")
        self.assertEqual(currency.name, "Euro")
        category = UomCategory.objects.get(code="LENGTH")
        self.assertEqual((category.dimension_code, category.description), ("LENGTH", "Mô tả"))
        unit = Uom.objects.get(code="MG")
        self.assertEqual((unit.name, unit.symbol, unit.precision), ("Milligram", "mg", 9))
        conversion = UomConversion.objects.get(effective_from=date(2026, 2, 1))
        self.assertEqual(conversion.organization, self.organization)
        self.assertEqual(conversion.factor, Decimal("1000.000000000001"))
        self.assertEqual(conversion.source_reference, "Tài liệu A")

    def test_duplicate_codes_rejected_in_all_coded_modules(self):
        for resource in ("currency", "uom_category", "uom"):
            with self.subTest(resource=resource):
                response = self.client.post(self.url(resource, "create"), self.payload(resource, code=self.records[resource].code.lower()))
                self.assertEqual(response.status_code, 200)
                self.assertIn("code", response.context["form"].errors)
                self.assertContains(response, 'aria-invalid="true"')

    def test_currency_length_and_decimal_places_validation(self):
        for overrides, field in (({"code": "VN"}, "code"), ({"code": "VNDD"}, "code"), ({"decimal_places": "-1"}, "decimal_places"), ({"decimal_places": "9"}, "decimal_places")):
            response = self.client.post(self.url("currency", "create"), self.payload("currency", **overrides))
            self.assertIn(field, response.context["form"].errors)

    def test_invalid_uom_precision_and_required_category(self):
        for overrides, field in (({"precision": "-1"}, "precision"), ({"precision": "13"}, "precision"), ({"category": ""}, "category")):
            response = self.client.post(self.url("uom", "create"), self.payload("uom", **overrides))
            self.assertIn(field, response.context["form"].errors)

    def test_edit_all_modules(self):
        for resource, record in self.records.items():
            data = self.payload(resource, code=getattr(record, "code", ""), name=" Đã cập nhật ")
            if resource == "uom":
                data["symbol"] = "kg"
            if resource == "uom_conversion":
                data["factor"] = "123.456"
            response = self.client.post(self.url(resource, "edit", record), data, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f"Đã cập nhật {response.context['resource_label']}.")
            record.refresh_from_db()
            if resource == "uom_conversion":
                self.assertEqual(record.factor, Decimal("123.456"))
            else:
                self.assertEqual(record.name, "Đã cập nhật")

    def test_currency_primary_key_is_immutable_even_when_posted(self):
        response = self.client.get(self.url("currency", "edit", self.currency))
        self.assertTrue(response.context["form"].fields["code"].disabled)
        response = self.client.post(self.url("currency", "edit", self.currency), self.payload("currency", code="EUR"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Currency.objects.filter(pk="EUR").exists())
        self.currency.refresh_from_db()
        self.assertEqual(self.currency.code, "VND")
        with self.assertRaises(ValidationError):
            save_currency(workspace=self.workspace(), data=dict(code="EUR", name="Euro", decimal_places=2, is_active=True), instance=self.currency)

    def test_legacy_currency_primary_key_keeps_its_original_case(self):
        legacy = Currency.objects.create(code="gbp", name="Legacy pound")
        response = self.client.post(self.url("currency", "edit", legacy), self.payload("currency", name="Pound"))
        self.assertEqual(response.status_code, 302)
        legacy.refresh_from_db()
        self.assertEqual((legacy.pk, legacy.name), ("gbp", "Pound"))
        self.assertFalse(Currency.objects.filter(pk="GBP").exists())

    def test_currency_code_routes_preserve_all_three_character_identifiers(self):
        # The specification requires length 3, without adding an ISO-only rule.
        response = self.client.post(self.url("currency", "create"), self.payload("currency", code="a/b"), follow=True)
        self.assertEqual(response.status_code, 200)
        record = Currency.objects.get(pk="A/B")
        self.assertEqual(self.client.get(self.url("currency", "edit", record)).status_code, 200)

    def test_deactivation_without_delete(self):
        for resource in ("currency", "uom_category", "uom"):
            record = self.records[resource]
            data = self.payload(resource, code=record.code, is_active="")
            self.assertEqual(self.client.post(self.url(resource, "edit", record), data).status_code, 302)
            record.refresh_from_db()
            self.assertFalse(record.is_active)
            self.assertNotContains(self.client.get(self.url(resource, "detail", record)), "Delete")

    def test_conversion_rejects_invalid_factor_units_dates_and_precision(self):
        cases = (({"factor": "0"}, "factor"), ({"factor": "-2"}, "factor"), ({"factor": "NaN"}, "factor"),
            ({"factor": "1.1234567890123"}, "factor"), ({"to_uom": self.kg.pk}, "to_uom"),
            ({"effective_to": "2026-02-01"}, "effective_to"), ({"effective_to": "2025-01-01"}, "effective_to"),
            ({"effective_from": ""}, "effective_from"), ({"to_uom": self.litre.pk}, "to_uom"))
        for overrides, field in cases:
            with self.subTest(overrides=overrides):
                response = self.client.post(self.url("uom_conversion", "create"), self.payload("uom_conversion", **overrides))
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertContains(response, "Không thể lưu quy đổi đơn vị tính.")

    def test_item_specific_conversion_and_organization_injection(self):
        data = self.payload("uom_conversion", item=self.item.pk, to_uom=self.litre.pk, organization=self.other_org.pk, id=999999)
        self.assertEqual(self.client.post(self.url("uom_conversion", "create"), data).status_code, 302)
        conversion = UomConversion.objects.get(item=self.item)
        self.assertEqual(conversion.organization, self.organization)
        self.assertNotEqual(conversion.pk, 999999)
        response = self.client.post(self.url("uom_conversion", "create"), self.payload("uom_conversion", item=self.other_item.pk))
        self.assertIn("item", response.context["form"].errors)

    def test_cross_organization_conversion_hidden_and_shared_read_only(self):
        response = self.client.get(self.url("uom_conversion"))
        self.assertEqual(set(response.context["records"]), {self.conversion, self.shared})
        for action in ("detail", "edit"):
            self.assertEqual(self.client.get(self.url("uom_conversion", action, self.foreign)).status_code, 404)
        detail = self.client.get(self.url("uom_conversion", "detail", self.shared))
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.context["primary_action_url"])
        self.assertEqual(self.client.get(self.url("uom_conversion", "edit", self.shared)).status_code, 403)
        self.assertEqual(self.client.post(self.url("uom_conversion", "edit", self.shared), self.payload("uom_conversion")).status_code, 403)
        self.shared.organization = None
        self.shared.item = self.other_item
        self.shared.save()
        self.assertEqual(self.client.get(self.url("uom_conversion", "detail", self.shared)).status_code, 404)

    def test_inactive_references_rejected_but_retained_values_can_be_edited(self):
        self.kg.is_active = False
        self.kg.save()
        response = self.client.post(self.url("uom_conversion", "create"), self.payload("uom_conversion"))
        self.assertIn("from_uom", response.context["form"].errors)
        response = self.client.post(self.url("uom_conversion", "edit", self.conversion), self.payload("uom_conversion"))
        self.assertEqual(response.status_code, 302)
        self.mass.is_active = False
        self.mass.save()
        response = self.client.post(self.url("uom", "create"), self.payload("uom"))
        self.assertIn("category", response.context["form"].errors)
        self.assertEqual(self.client.post(self.url("uom", "edit", self.kg), self.payload("uom", code="KG")).status_code, 302)

    def test_no_speculative_base_unit_or_overlap_policy(self):
        self.assertEqual(self.client.post(self.url("uom", "create"), self.payload("uom", is_base="on")).status_code, 302)
        self.assertEqual(Uom.objects.filter(category=self.mass, is_base=True).count(), 2)
        data = self.payload("uom_conversion", effective_from="2026-01-01", factor="1000")
        self.assertEqual(self.client.post(self.url("uom_conversion", "create"), data).status_code, 302)
        self.assertEqual(UomConversion.objects.filter(organization=self.organization, from_uom=self.kg, to_uom=self.gram, effective_from=date(2026, 1, 1)).count(), 2)

    def test_category_change_cannot_break_general_conversion(self):
        response = self.client.post(self.url("uom", "edit", self.kg), self.payload("uom", code="KG", category=self.volume.pk))
        self.assertIn("category", response.context["form"].errors)
        self.kg.refresh_from_db()
        self.assertEqual(self.kg.category, self.mass)

    def test_htmx_partials_and_history_restores(self):
        for resource, record in self.records.items():
            for action, partial in (("list", "table"), ("detail", "detail_content"), ("create", "form_content")):
                with self.subTest(resource=resource, action=action):
                    url = self.url(resource, action, record if action == "detail" else None)
                    response = self.client.get(url, HTTP_HX_REQUEST="true")
                    self.assertTemplateUsed(response, f"master_data/partials/reference_data_{partial}.html")
                    self.assertNotContains(response, "<!doctype")
                    restored = self.client.get(url, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
                    self.assertContains(restored, "<!doctype")
            response = self.client.post(self.url(resource, "create"), self.payload(resource, **({"factor": "0"} if resource == "uom_conversion" else {"code": ""})), HTTP_HX_REQUEST="true")
            self.assertTemplateUsed(response, "master_data/partials/reference_data_form_content.html")
            response = self.client.post(self.url(resource, "create"), self.payload(resource), HTTP_HX_REQUEST="true")
            self.assertEqual(response.status_code, 200)
            self.assertIn("HX-Redirect", response)

    def test_empty_search_and_empty_table(self):
        for resource in self.resources:
            response = self.client.get(self.url(resource), {"q": "definitely-no-results"})
            self.assertContains(response, "Không có kết quả phù hợp.")
        UomConversion.objects.all().delete()
        Item.objects.all().delete()
        Uom.objects.all().delete()
        UomCategory.objects.all().delete()
        Currency.objects.all().delete()
        for resource, label in (("currency", "tiền tệ"), ("uom_category", "nhóm đơn vị tính"), ("uom", "đơn vị tính"), ("uom_conversion", "quy đổi đơn vị tính")):
            self.assertContains(self.client.get(self.url(resource)), f"Chưa có {label}.")

    def test_not_found_names_correct_resource(self):
        for resource, label in (("currency", "tiền tệ"), ("uom_category", "nhóm đơn vị tính"), ("uom", "đơn vị tính"), ("uom_conversion", "quy đổi đơn vị tính")):
            record = SimpleNamespace(pk="ZZZ" if resource == "currency" else 999999)
            response = self.client.get(self.url(resource, "detail", record))
            self.assertContains(response, f"Không tìm thấy {label}.", status_code=404)
        record = SimpleNamespace(pk=10 ** 100)
        self.assertEqual(self.client.get(self.url("uom", "detail", record)).status_code, 404)

    def test_related_data_has_no_n_plus_one(self):
        with self.assertNumQueries(1):
            for unit in uom_queryset():
                _ = unit.category.name
        with self.assertNumQueries(1):
            for record in uom_conversion_queryset(organization=self.organization):
                _ = record.from_uom.name, record.to_uom.name
                _ = record.organization.name if record.organization else None
                _ = record.item.name if record.item else None


    def test_services_authorize_without_view(self):
        workspace = self.workspace()
        for resource, form_class, service in (("currency", CurrencyForm, save_currency), ("uom", UomForm, save_uom), ("uom_conversion", UomConversionForm, save_uom_conversion)):
            form = form_class(self.payload(resource), workspace=workspace)
            self.assertTrue(form.is_valid(), form.errors)
            denied = replace(workspace, permissions=replace(workspace.permissions, **{f"can_create_{resource}": False}))
            with self.assertRaises(PermissionDenied):
                service(workspace=denied, data=form.cleaned_data)

    def test_conversion_service_rejects_foreign_item_and_global_update(self):
        workspace = self.workspace()
        form = UomConversionForm(self.payload("uom_conversion"), workspace=workspace)
        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaises(ValidationError):
            save_uom_conversion(workspace=workspace, data=dict(form.cleaned_data, item=self.other_item))
        with self.assertRaises(ValidationError):
            save_uom_conversion(workspace=workspace, data=form.cleaned_data, instance=self.shared)

    def test_database_race_and_unknown_integrity_error_are_friendly(self):
        workspace = self.workspace()
        data = dict(code="VND", name="Duplicate", decimal_places=2, is_active=True)
        with patch("apps.master_data.services.validate_currency"):
            with self.assertRaises(ValidationError) as caught:
                save_currency(workspace=workspace, data=data)
        self.assertIn("code", caught.exception.message_dict)
        self.assertNotIn("duplicate key", str(caught.exception))
        with patch.object(Currency, "save", side_effect=IntegrityError("private SQL details")):
            with self.assertRaises(ValidationError) as caught:
                save_currency(workspace=workspace, data=dict(data, code="EUR"))
        self.assertNotIn("private SQL", str(caught.exception))
        self.assertFalse(Currency.objects.filter(pk="EUR").exists())

    def test_postgresql_constraints_are_final_protection(self):
        for model, pk, values in ((Currency, self.currency.pk, {"decimal_places": 9}), (Uom, self.kg.pk, {"precision": 13}),
            (UomConversion, self.conversion.pk, {"factor": 0}), (UomConversion, self.conversion.pk, {"to_uom": self.kg}),
            (UomConversion, self.conversion.pk, {"effective_to": self.conversion.effective_from})):
            with self.subTest(model=model.__name__, values=values):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    model.objects.filter(pk=pk).update(**values)

    def test_csrf_enforced_on_all_create_endpoints(self):
        client = Client(enforce_csrf_checks=True)
        for resource in self.resources:
            self.assertEqual(client.post(self.url(resource, "create"), self.payload(resource)).status_code, 403)
        client.get(self.url("currency", "create"))
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.url("currency", "create"), self.payload("currency"), HTTP_X_CSRFTOKEN=token).status_code, 302)

    def test_production_unexpected_error_hides_traceback(self):
        with self.assertLogs("apps.master_data.middleware", level="ERROR"):
            with patch("apps.master_data.selectors.currency_list", side_effect=RuntimeError("private error")):
                response = self.client.get(self.url("currency"))
        self.assertContains(response, "Mã tham chiếu:", status_code=500)
        self.assertNotContains(response, "private error", status_code=500)
