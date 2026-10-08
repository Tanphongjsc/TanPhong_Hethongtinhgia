"""Single-company behavior with no authentication, session or membership."""
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.models import CostElement, Organization, OrganizationMember
from .access import INTERNAL_ACCESS, get_workspace, require_access
from .company_context import ConfigurationError, get_default_organization


class CompanyContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="COMPANY", name="Công ty nội bộ")
        cls.element = CostElement.objects.create(organization=cls.company, code="INTERNAL", name="Chi phí nội bộ", value_type="NUMBER", default_source_mode="MANUAL", accounting_scope="ANALYTICS", cost_scope="ANALYTICS")

    def setUp(self):
        self.list_url = reverse("master_data:cost_element_list")

    def payload(self, **overrides):
        values = dict(code=" new_cost ", name=" Chi phí mới ", value_type="NUMBER", default_source_mode="MANUAL", rounding_scale="0", rounding_mode="HALF_UP", accounting_scope="ANALYTICS", cost_scope="ANALYTICS", is_active="on")
        return {**values, **overrides}

    def test_root_redirects_directly_to_cost_elements(self):
        self.assertRedirects(self.client.get("/"), self.list_url, fetch_redirect_response=False)

    def test_direct_access_has_no_user_session_or_membership_query(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("organization_member", " ".join(query["sql"] for query in queries))
        self.assertFalse(hasattr(response.wsgi_request, "user"))
        self.assertFalse(hasattr(response.wsgi_request, "session"))
        self.assertNotIn("sessionid", response.cookies)
        self.assertContains(response, "+ Thêm mới")

    def test_workspace_requires_no_user_attributes_and_is_cached_per_request(self):
        request = RequestFactory().get(self.list_url)
        with self.assertNumQueries(1):
            workspace = require_access(request)
            self.assertIs(get_workspace(request), workspace)
        self.assertEqual(workspace.organization, self.company)
        self.assertIs(workspace.permissions, INTERNAL_ACCESS)
        self.assertTrue(all(vars(INTERNAL_ACCESS).values()))

    def test_create_assigns_company_and_null_audit_ignoring_posted_ids(self):
        response = self.client.post(reverse("master_data:cost_element_create"), self.payload(organization="999999", created_by=str(uuid4()), updated_by=str(uuid4())))
        self.assertEqual(response.status_code, 302)
        element = CostElement.objects.get(code="NEW_COST")
        self.assertEqual(element.organization, self.company)
        self.assertIsNone(element.created_by)
        self.assertIsNone(element.updated_by)
        self.assertContains(self.client.get(response.url), "Đã tạo phần tử chi phí.")
        self.assertNotIn("sessionid", self.client.cookies)

    def test_edit_works_without_user_and_does_not_accept_audit_assignment(self):
        response = self.client.post(reverse("master_data:cost_element_edit", args=[self.element.pk]), self.payload(code=self.element.code, name="Đã sửa", updated_by=str(uuid4())))
        self.assertEqual(response.status_code, 302)
        self.element.refresh_from_db()
        self.assertEqual(self.element.name, "Đã sửa")
        self.assertIsNone(self.element.updated_by)

    def test_htmx_anonymous_returns_table_partial_without_login_redirect(self):
        response = self.client.get(self.list_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "master_data/partials/cost_element_table.html")
        self.assertNotIn("HX-Redirect", response)

    def test_one_active_company_auto_resolves_despite_inactive_records(self):
        Organization.objects.create(code="INACTIVE", name="Ngừng dùng", is_active=False)
        self.assertEqual(get_default_organization(), self.company)

    def test_no_active_company_is_an_actionable_configuration_error(self):
        self.company.is_active = False
        self.company.save()
        with self.assertRaisesMessage(ConfigurationError, "Chưa có công ty hoạt động"):
            get_default_organization()
        for debug in (False, True):
            with override_settings(DEBUG=debug), self.assertNumQueries(1):
                response = self.client.get(self.list_url)
            self.assertContains(response, "Chưa có công ty hoạt động", status_code=503)
            self.assertNotContains(response, "Traceback", status_code=503)

    def test_missing_company_partial_does_not_redirect_or_retry_context(self):
        Organization.objects.all().update(is_active=False)
        with self.assertNumQueries(1):
            response = self.client.get(self.list_url, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "partials/error.html")
        self.assertContains(response, "Chưa có công ty hoạt động", status_code=503)

    def test_multiple_active_companies_require_configuration(self):
        Organization.objects.create(code="OTHER", name="Công ty khác")
        with self.assertRaisesMessage(ConfigurationError, "DEFAULT_ORGANIZATION_ID"):
            get_default_organization()
        self.assertContains(self.client.get(self.list_url), "Có nhiều công ty hoạt động", status_code=503)

    def test_explicit_id_selects_correct_active_company(self):
        other = Organization.objects.create(code="OTHER", name="Công ty khác")
        with override_settings(DEFAULT_ORGANIZATION_ID=str(other.pk)):
            self.assertEqual(get_default_organization(), other)
            response = self.client.get(self.list_url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "Chi phí nội bộ")

    def test_invalid_or_inactive_configured_id_fails_without_fallback(self):
        inactive = Organization.objects.create(code="INACTIVE", name="Ngừng dùng", is_active=False)
        for identifier in ("bad", "-1", "0", "9" * 30, "999999", str(inactive.pk)):
            with self.subTest(identifier=identifier), override_settings(DEFAULT_ORGANIZATION_ID=identifier):
                with self.assertRaises(ConfigurationError):
                    get_default_organization()
                self.assertContains(self.client.get(self.list_url), "DEFAULT_ORGANIZATION_ID", status_code=503)

    def test_other_modes_report_configuration_error(self):
        with override_settings(APP_MODE="multi_tenant"):
            with self.assertRaisesMessage(ConfigurationError, "single_company"):
                get_default_organization()

    def test_cookie_query_and_headers_cannot_switch_company(self):
        other = Organization.objects.create(code="OTHER", name="Công ty khác")
        foreign = CostElement.objects.create(organization=other, code="FOREIGN", name="Chi phí công ty khác", value_type="NUMBER", default_source_mode="MANUAL", accounting_scope="ANALYTICS", cost_scope="ANALYTICS")
        self.client.cookies["sessionid"] = "old-or-forged-auth-cookie"
        with override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk):
            response = self.client.get(self.list_url, {"organization": other.pk, "user_id": str(uuid4())}, HTTP_X_ORGANIZATION_ID=str(other.pk))
            self.assertContains(response, self.element.name)
            self.assertNotContains(response, foreign.name)
            for route in ("cost_element_detail", "cost_element_edit"):
                self.assertEqual(self.client.get(reverse(f"master_data:{route}", args=[foreign.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse("master_data:cost_element_edit", args=[foreign.pk]), self.payload()).status_code, 404)

    def test_membership_is_retained_but_never_needed(self):
        self.assertFalse(OrganizationMember._meta.managed)
        with patch.object(OrganizationMember.objects, "filter", side_effect=AssertionError("Membership must not be queried")):
            self.assertEqual(self.client.get(self.list_url).status_code, 200)
            self.assertEqual(self.client.get(reverse("master_data:cost_element_create")).status_code, 200)
            self.assertEqual(self.client.post(reverse("master_data:cost_element_create"), self.payload()).status_code, 302)

    def test_sensitive_data_is_available_under_internal_policy(self):
        self.element.is_sensitive = True
        self.element.save()
        self.assertContains(self.client.get(self.list_url), self.element.code)
        self.assertEqual(self.client.get(reverse("master_data:cost_element_edit", args=[self.element.pk])).status_code, 200)

    def test_auth_and_switching_routes_are_removed(self):
        for path in ("/accounts/login/", "/accounts/logout/", "/accounts/session/", "/accounts/organizations/", "/admin/", "/master-data/context/organization/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
        self.assertFalse(any(name in settings.INSTALLED_APPS for name in ("apps.accounts", "django.contrib.auth", "django.contrib.sessions", "django.contrib.admin")))

    def test_ui_does_not_expose_organization_or_user_controls(self):
        response = self.client.get(self.list_url)
        for text in ("Đăng nhập", "Đăng xuất", "organization-switch", "Users &amp; Roles", "Organization Scope", ">Organization<"):
            self.assertNotContains(response, text)
        self.assertNotContains(self.client.get(reverse("master_data:uom_conversion_list")), "Organization Scope")

    def test_unknown_url_remains_404_when_company_config_is_missing(self):
        Organization.objects.all().update(is_active=False)
        self.assertEqual(self.client.get("/unknown/route/").status_code, 404)
