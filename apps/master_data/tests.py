from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.core.models import CostElement, CostElementGroup, Currency, Organization, Uom, UomCategory
from .access import INTERNAL_ACCESS, get_workspace
from .forms import CostElementForm
from .selectors import cost_element_queryset
from .services import save_cost_element


class CostElementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(code="ORG_A", name="Tổ chức A")
        cls.other_org = Organization.objects.create(code="ORG_B", name="Tổ chức B")
        cls.currency = Currency.objects.create(code="VND", name="Việt Nam đồng")
        cls.category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        cls.uom = Uom.objects.create(category=cls.category, code="KG", name="Kilogram", symbol="kg")
        cls.group = CostElementGroup.objects.create(organization=cls.organization, code="MATERIAL", name="Nguyên liệu", category_code="MATERIAL")
        cls.other_group = CostElementGroup.objects.create(organization=cls.other_org, code="OTHER", name="Nhóm khác", category_code="OTHER")
        cls.element = cls.make_element(code="MATERIAL_COST", name="Chi phí nguyên liệu", description="Giá đầu vào", group=cls.group, currency_code=cls.currency, default_uom=cls.uom)
        cls.inactive = cls.make_element(code="Z_OLD", name="Ngừng dùng", value_type="NUMBER", default_source_mode="SYSTEM", cost_scope="LANDED", is_active=False)
        cls.secret = cls.make_element(code="SECRET_MARGIN", name="Margin nhạy cảm", is_sensitive=True)
        cls.foreign = cls.make_element(code="FOREIGN_CODE", name="Không được thấy", organization=cls.other_org)

    @classmethod
    def make_element(cls, **overrides):
        data = dict(organization=cls.organization, code="TEST", name="Test", value_type="MONEY", default_source_mode="MANUAL", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING", currency_code=cls.currency)
        data.update(overrides)
        return CostElement.objects.create(**data)

    def setUp(self):
        company = override_settings(DEFAULT_ORGANIZATION_ID=self.organization.pk)
        company.enable()
        self.addCleanup(company.disable)
        self.list_url = reverse("master_data:cost_element_list")
        self.create_url = reverse("master_data:cost_element_create")
        self.detail_url = reverse("master_data:cost_element_detail", args=[self.element.pk])
        self.edit_url = reverse("master_data:cost_element_edit", args=[self.element.pk])

    def payload(self, **overrides):
        data = dict(group=str(self.group.pk), code="new_cost", name="New Cost", description="Mô tả", value_type="MONEY", dimension_code="MASS", default_source_mode="MANUAL", currency_code="VND", default_uom=str(self.uom.pk), rounding_scale="6", rounding_mode="HALF_UP", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING", is_active="on")
        data.update(overrides)
        return data

    def workspace(self):
        request = RequestFactory().get(self.list_url)
        return get_workspace(request)

    def test_list_returns_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "master_data/cost_element_list.html")
        self.assertContains(response, "MATERIAL_COST")
        self.assertNotContains(response, "FOREIGN_CODE")
        self.assertContains(response, "SECRET_MARGIN")

    def test_search_code_name_description(self):
        for term in ("material_cost", "nguyên liệu", "đầu vào"):
            with self.subTest(term=term):
                response = self.client.get(self.list_url, {"q": term})
                self.assertEqual(list(response.context["elements"]), [self.element])

    def test_each_filter(self):
        filters = ({"group": str(self.group.pk)}, {"value_type": "MONEY"}, {"source_mode": "MANUAL"}, {"cost_scope": "MANUFACTURING"}, {"active": "true"})
        for parameters in filters:
            with self.subTest(parameters=parameters):
                self.assertEqual(list(self.client.get(self.list_url, parameters).context["elements"]), [self.element] if "group" in parameters else [self.element, self.secret])
        self.assertEqual(list(self.client.get(self.list_url, {"active": "false"}).context["elements"]), [self.inactive])

    def test_sort_all_allowed_columns_both_directions(self):
        for field in ("code", "name", "value_type", "created_at"):
            for prefix in ("", "-"):
                sort = prefix + field
                with self.subTest(sort=sort):
                    response = self.client.get(self.list_url, {"sort": sort})
                    expected = list(CostElement.objects.filter(pk__in=[self.element.pk, self.inactive.pk, self.secret.pk]).order_by(sort, "pk"))
                    self.assertEqual(list(response.context["elements"]), expected)

    def test_bad_sort_page_size_and_group_are_safe(self):
        response = self.client.get(self.list_url, {"sort": "organization__name", "per_page": "oops", "page": "oops"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_sort"], "code")
        self.assertEqual(response.context["per_page"], 25)
        self.assertEqual(self.client.get(self.list_url, {"sort": "--code"}).context["current_sort"], "code")
        for invalid in ("garbage", "9" * 50, "１２"):
            response = self.client.get(self.list_url, {"group": invalid})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_pagination_25_50_100(self):
        CostElement.objects.bulk_create([CostElement(organization=self.organization, code=f"EXTRA_{i:03}", name="Extra", value_type="NUMBER", default_source_mode="MANUAL", accounting_scope="ANALYTICS", cost_scope="ANALYTICS") for i in range(101)])
        for size in (25, 50, 100):
            response = self.client.get(self.list_url, {"per_page": size})
            self.assertEqual(len(response.context["elements"]), size)
        response = self.client.get(self.list_url, {"page": 2, "per_page": 25})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["elements"]), 25)

    def test_detail(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nguyên liệu")
        self.assertContains(response, "VND")
        self.assertContains(response, "KG")

    def test_create_normalizes_and_sets_audit_context(self):
        response = self.client.post(self.create_url, self.payload(code="  new_cost  ", name="  New Cost  ", organization=str(self.other_org.pk), created_by=str(uuid4())))
        element = CostElement.objects.get(code="NEW_COST", organization=self.organization)
        self.assertRedirects(response, reverse("master_data:cost_element_detail", args=[element.pk]), fetch_redirect_response=False)
        self.assertEqual(element.name, "New Cost")
        self.assertIsNone(element.created_by)
        self.assertIsNone(element.updated_by)
        self.assertContains(self.client.get(reverse("master_data:cost_element_detail", args=[element.pk])), "Đã tạo phần tử chi phí.")

    def test_duplicate_code_rejected_case_insensitively(self):
        response = self.client.post(self.create_url, self.payload(code="  material_cost "))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mã phần tử chi phí đã tồn tại trong công ty.")
        self.assertEqual(CostElement.objects.filter(organization=self.organization, code="MATERIAL_COST").count(), 1)

    def test_same_code_allowed_in_another_organization(self):
        response = self.client.post(self.create_url, self.payload(code=self.foreign.code))
        self.assertEqual(response.status_code, 302)

    def test_edit_preserves_created_fields(self):
        old_created_at = self.element.created_at
        response = self.client.post(self.edit_url, self.payload(code=self.element.code, name=" Updated ", is_active=""))
        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)
        self.element.refresh_from_db()
        self.assertEqual(self.element.name, "Updated")
        self.assertFalse(self.element.is_active)
        self.assertEqual(self.element.created_at, old_created_at)
        self.assertIsNone(self.element.updated_by)
        self.assertContains(self.client.get(self.detail_url), "Đã cập nhật phần tử chi phí.")

    def test_invalid_form_preserves_input_and_links_errors(self):
        response = self.client.post(self.create_url, self.payload(code="", name="Giữ nội dung", rounding_scale="13"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Không thể lưu phần tử chi phí.")
        self.assertContains(response, 'value="Giữ nội dung"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'id_rounding_scale_errors')
        self.assertFalse(CostElement.objects.filter(name="Giữ nội dung").exists())

    def test_rounding_boundaries(self):
        for scale in (-1, 0, 12, 13):
            form = CostElementForm(self.payload(rounding_scale=str(scale)), organization=self.organization, permissions=INTERNAL_ACCESS)
            self.assertEqual(form.is_valid(), scale in (0, 12))

    def test_money_quantity_and_dimension_validation(self):
        for overrides, error_field in (
            ({"currency_code": ""}, "currency_code"),
            ({"value_type": "QUANTITY", "default_uom": ""}, "default_uom"),
            ({"dimension_code": "TIME"}, "dimension_code"),
            ({"value_type": "INVALID"}, "value_type"),
        ):
            with self.subTest(overrides=overrides):
                form = CostElementForm(self.payload(**overrides), organization=self.organization, permissions=INTERNAL_ACCESS)
                self.assertFalse(form.is_valid())
                self.assertIn(error_field, form.errors)

    def test_cross_organization_group_is_rejected(self):
        response = self.client.post(self.create_url, self.payload(group=str(self.other_group.pk)))
        self.assertIn("group", response.context["form"].errors)
        self.assertFalse(CostElement.objects.filter(code="NEW_COST").exists())

    def test_inactive_reference_can_be_retained_but_not_newly_selected(self):
        self.currency.is_active = False
        self.currency.save()
        permissions = INTERNAL_ACCESS
        create_form = CostElementForm(self.payload(), organization=self.organization, permissions=permissions)
        self.assertFalse(create_form.is_valid())
        edit_form = CostElementForm(self.payload(code=self.element.code), instance=self.element, organization=self.organization, permissions=permissions)
        self.assertTrue(edit_form.is_valid(), edit_form.errors)

    def test_htmx_list_partial_and_history_restore_full_page(self):
        response = self.client.get(self.list_url, {"q": "material"}, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/cost_element_table.html")
        self.assertNotContains(response, "<!doctype html>")
        self.assertContains(response, 'id="cost-element-table"')
        self.assertIn("HX-Request", response["Vary"])
        restored = self.client.get(self.list_url, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(restored, "<!doctype html>")

    def test_htmx_detail_and_invalid_form_partials(self):
        response = self.client.get(self.detail_url, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/cost_element_detail_content.html")
        response = self.client.post(self.create_url, self.payload(code=""), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/cost_element_form_content.html")
        self.assertContains(response, "Không thể lưu phần tử chi phí.")

    def test_htmx_create_redirects_to_saved_detail(self):
        response = self.client.post(self.create_url, self.payload(), HTTP_HX_REQUEST="true")
        element = CostElement.objects.get(code="NEW_COST")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], reverse("master_data:cost_element_detail", args=[element.pk]))

    def test_empty_search_and_empty_organization(self):
        response = self.client.get(self.list_url, {"q": "no-result"})
        self.assertContains(response, "Không có kết quả phù hợp.")
        CostElement.objects.filter(organization=self.organization).delete()
        self.assertContains(self.client.get(self.list_url), "Chưa có phần tử chi phí.")

    def test_query_parameters_are_preserved_in_sort_and_pagination(self):
        response = self.client.get(self.list_url, {"q": "cost", "active": "true", "per_page": 50})
        self.assertContains(response, "q=cost&amp;active=true&amp;per_page=50&amp;sort=-code")
        self.assertContains(response, 'hx-push-url="true"')
        self.assertContains(response, 'input changed delay:400ms')

    def test_list_related_objects_have_no_n_plus_one(self):
        with self.assertNumQueries(1):
            elements = list(cost_element_queryset(organization=self.organization, permissions=INTERNAL_ACCESS))
            for element in elements:
                _ = element.organization.name
                _ = element.group.name if element.group else None
                _ = element.currency_code.name if element.currency_code else None
                _ = element.default_uom.code if element.default_uom else None


    def test_cross_organization_detail_and_edit_not_found(self):
        for name in ("cost_element_detail", "cost_element_edit"):
            response = self.client.get(reverse(f"master_data:{name}", args=[self.foreign.pk]))
            self.assertEqual(response.status_code, 404)
            self.assertContains(response, "Không tìm thấy phần tử chi phí.", status_code=404)


    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.create_url, self.payload()).status_code, 403)
        response = client.get(self.create_url)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.create_url, self.payload(), HTTP_X_CSRFTOKEN=token).status_code, 302)

    def test_service_authorizes_independently_of_view(self):
        workspace = self.workspace()
        form = CostElementForm(self.payload(), organization=self.organization, permissions=workspace.permissions)
        self.assertTrue(form.is_valid())
        denied = replace(workspace, permissions=replace(workspace.permissions, can_create_cost_element=False))
        with self.assertRaises(PermissionDenied):
            save_cost_element(workspace=denied, data=form.cleaned_data)

    def test_database_duplicate_race_becomes_field_error(self):
        workspace = self.workspace()
        form = CostElementForm(self.payload(), organization=self.organization, permissions=workspace.permissions)
        self.assertTrue(form.is_valid())
        values = dict(form.cleaned_data, code=self.element.code)
        with patch("apps.master_data.services.validate_cost_element"):
            with self.assertRaises(ValidationError) as caught:
                save_cost_element(workspace=workspace, data=values)
        self.assertIn("code", caught.exception.message_dict)
        self.assertNotIn("duplicate key", str(caught.exception))
        self.assertEqual(CostElement.objects.filter(code=self.element.code).count(), 1)

    def test_unexpected_integrity_error_is_user_friendly_and_rolls_back(self):
        workspace = self.workspace()
        form = CostElementForm(self.payload(code=self.element.code, name="Changed"), instance=self.element, organization=self.organization, permissions=workspace.permissions)
        self.assertTrue(form.is_valid())
        with patch.object(CostElement, "save", side_effect=IntegrityError("private database details")):
            with self.assertRaises(ValidationError) as caught:
                save_cost_element(workspace=workspace, data=form.cleaned_data, instance=self.element)
        self.assertNotIn("private database details", str(caught.exception))
        self.element.refresh_from_db()
        self.assertNotEqual(self.element.name, "Changed")

    def test_postgresql_checks_reject_invalid_rounding(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CostElement.objects.filter(pk=self.element.pk).update(rounding_scale=13)

    def test_production_errors_hide_details_and_include_reference(self):
        with self.assertLogs("apps.master_data.middleware", level="ERROR"):
            with patch("apps.master_data.views.get_list", side_effect=RuntimeError("private traceback detail")):
                response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Mã tham chiếu:", status_code=500)
        self.assertNotContains(response, "private traceback detail", status_code=500)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_database_outage_can_render_error_without_retrying_context(self):
        with self.assertLogs("apps.master_data.middleware", level="ERROR"):
            with patch("apps.master_data.company_context.Organization.objects.filter", side_effect=OperationalError("database unavailable")):
                response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Đã xảy ra lỗi khi xử lý yêu cầu.", status_code=500)

