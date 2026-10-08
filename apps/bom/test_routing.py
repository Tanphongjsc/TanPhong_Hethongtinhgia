"""Routing/version/operation behavior against inspected PostgreSQL fixtures."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Organization, Product, Resource, Routing, RoutingOperation, RoutingVersion, Sku, Uom, UomCategory, WorkCenter
from apps.master_data.access import INTERNAL_ACCESS, Workspace, get_workspace
from . import routing_selectors as selectors, routing_services as services
from .routing_constants import OPERATION_FIELDS, VERSION_FIELDS
from .routing_forms import RoutingForm, RoutingOperationForm, RoutingVersionForm
from .routing_views import routing_create


class RoutingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="ROUTING_INTERNAL", name="Công ty nội bộ")
        cls.other = Organization.objects.create(code="OTHER", name="Dữ liệu khác")
        time = UomCategory.objects.create(code="TIME", name="Thời gian", dimension_code="TIME")
        mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        cls.minute = Uom.objects.create(category=time, code="MIN", name="Phút", symbol="phút")
        cls.hour = Uom.objects.create(category=time, code="H", name="Giờ", symbol="h")
        cls.kg = Uom.objects.create(category=mass, code="KG", name="Kilôgam", symbol="kg")
        cls.product = Product.objects.create(organization=cls.company, code="CAP", name="Cà phê Cappuccino", costing_uom=cls.kg)
        cls.other_product = Product.objects.create(organization=cls.other, code="PRIVATE_PRODUCT", name="Sản phẩm khác", costing_uom=cls.kg)
        cls.sku = Sku.objects.create(organization=cls.company, product=cls.product, code="CAP_20", name="Cappuccino 20 gói", sales_uom=cls.kg, net_quantity=1, net_quantity_uom=cls.kg)
        cls.center = WorkCenter.objects.create(organization=cls.company, code="MIX", name="Khu phối trộn")
        cls.packing = WorkCenter.objects.create(organization=cls.company, code="PACK", name="Khu đóng gói")
        cls.machine = Resource.objects.create(organization=cls.company, work_center=cls.center, code="MIXER", name="Máy trộn", resource_type="MACHINE")
        cls.packer = Resource.objects.create(organization=cls.company, work_center=cls.packing, code="PACKER", name="Máy đóng gói", resource_type="MACHINE")
        cls.shared_resource = Resource.objects.create(organization=cls.company, code="LABOR", name="Nhân công chung", resource_type="LABOR")
        cls.other_center = WorkCenter.objects.create(organization=cls.other, code="PRIVATE_CENTER", name="Trung tâm khác")
        cls.other_resource = Resource.objects.create(organization=cls.other, code="PRIVATE_RESOURCE", name="Nguồn lực khác", resource_type="SERVICE")
        cls.routing = Routing.objects.create(organization=cls.company, product=cls.product, code="RT_CAP", name="Quy trình Cappuccino")
        cls.today = timezone.localdate()
        cls.version = RoutingVersion.objects.create(routing=cls.routing, version_no=1, batch_size=100, batch_uom=cls.kg, effective_from=cls.today)
        cls.operation = RoutingOperation.objects.create(routing_version=cls.version, sequence_no=10, operation_code="MIX", operation_name="Phối trộn", work_center=cls.center,
            primary_resource=cls.machine, setup_time=Decimal("15.12345678"), run_time=Decimal("30"), time_uom=cls.minute, quantity_basis=100, quantity_uom=cls.kg, notes="Ghi chú gốc")
        cls.foreign_routing = Routing.objects.create(organization=cls.other, product=cls.other_product, code="PRIVATE_ROUTING", name="Quy trình riêng")
        cls.foreign_version = RoutingVersion.objects.create(routing=cls.foreign_routing, version_no=1)
        cls.foreign_operation = RoutingOperation.objects.create(routing_version=cls.foreign_version, sequence_no=10, operation_code="PRIVATE", operation_name="Công đoạn riêng")

    def setUp(self):
        settings = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        settings.enable()
        self.addCleanup(settings.disable)

    def url(self, action="list", *, routing=None, version=None, operation=None):
        args = [routing.pk] if routing else []
        if version:
            args.append(version.pk)
        if operation:
            args.append(operation.pk)
        return reverse(f"bom:routing_{action}", args=args)

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url()))

    def version_payload(self, **changes):
        data = dict(batch_size="100.12345678", batch_uom=str(self.kg.pk), effective_from=self.today.isoformat(), effective_to="", change_reason=" Cập nhật quy trình ")
        data.update(changes)
        return data

    def header_payload(self, **changes):
        data = dict(product=str(self.product.pk), code=" rt_new ", name=" Quy trình mới ", is_active="on")
        data.update({f"initial-{key}": value for key, value in self.version_payload().items()})
        data.update(changes)
        return data

    def operation_payload(self, **changes):
        data = dict(sequence_no="20", operation_code=" mix_next ", operation_name=" Phối trộn tiếp ", work_center=str(self.center.pk), primary_resource=str(self.machine.pk),
            setup_time="1.12345678", run_time="1.5", time_uom=str(self.hour.pk), quantity_basis="100.12345678", quantity_uom=str(self.kg.pk), notes=" Ghi chú mới ")
        data.update(changes)
        return data

    def operation_values(self, **changes):
        form = RoutingOperationForm(self.operation_payload(**changes), workspace=self.workspace(), version=self.version)
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def version_values(self, **changes):
        form = RoutingVersionForm(self.version_payload(**changes), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def test_anonymous_list_detail_and_navigation_without_membership(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(list(response.context["records"]), [self.routing])
            self.assertContains(response, "Quy trình sản xuất")
            self.assertContains(response, f'href="{self.url()}" aria-current="page"')
            self.assertNotIn("sessionid", response.cookies)
            detail = self.client.get(self.url("detail", routing=self.routing))
            self.assertContains(detail, "Phối trộn")
            self.assertContains(detail, "15,12345678")
            self.assertContains(detail, 'aria-current="page"', count=1)
        self.assertFalse(any("organization_member" in query["sql"] for query in queries))

    def test_search_routing_product_and_sku(self):
        for keyword in ("rt_cap", "Quy trình Cappuccino", "cap", "Cà phê Cappuccino", "CAP_20", "Cappuccino 20 gói"):
            self.assertEqual(list(self.client.get(self.url(), {"q": keyword}).context["records"]), [self.routing])

    def test_product_sku_status_active_filters(self):
        for key, value in (("product", self.product.pk), ("sku", self.sku.pk), ("status", "DRAFT"), ("effective", "EFFECTIVE"), ("is_active", "true")):
            self.assertEqual(list(self.client.get(self.url(), {key: value}).context["records"]), [self.routing])
        for filters in ({"active": "false"}, {"product": self.other_product.pk}, {"sku": "invalid"}, {"status": "LOCKED"}):
            self.assertFalse(self.client.get(self.url(), filters).context["records"])

    def test_sort_pagination_and_operation_count_no_row_duplication(self):
        records = Routing.objects.bulk_create([Routing(organization=self.company, product=self.product, code=f"TEST_{i:03}", name="Quy trình thử") for i in range(61)])
        RoutingVersion.objects.bulk_create([RoutingVersion(routing=record, version_no=1) for record in records])
        for size, count in ((25, 25), (50, 50), (100, 61)):
            response = self.client.get(self.url(), {"q": "test", "per_page": size, "sort": "-code"})
            self.assertEqual(len(response.context["records"]), count)
            self.assertEqual(response.context["records"][0].code, "TEST_060")
        response = self.client.get(self.url(), {"q": "test", "page": 2, "sort": "name"})
        self.assertEqual(len(response.context["records"]), 25)
        self.assertContains(response, "q=test")
        record = self.client.get(self.url(), {"q": "RT_CAP"}).context["records"][0]
        self.assertEqual(record.latest_operation_count, 1)
        response = self.client.get(self.url(), {"sort": "--code", "per_page": "999"})
        self.assertEqual(response.context["current_sort"], "code")
        self.assertEqual(response.context["per_page"], 25)

    def test_header_create_initial_version_normalization_and_hidden_fields(self):
        response = self.client.post(self.url("create"), self.header_payload(organization=self.other.pk, status="EFFECTIVE", created_by="00000000-0000-0000-0000-000000000001"), follow=True)
        self.assertContains(response, "Đã tạo quy trình sản xuất.")
        saved = Routing.objects.get(code="RT_NEW")
        self.assertEqual(saved.organization_id, self.company.pk)
        self.assertEqual(saved.name, "Quy trình mới")
        version = RoutingVersion.objects.get(routing=saved)
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.status, "DRAFT")
        self.assertEqual(version.batch_size, Decimal("100.12345678"))
        self.assertIsNone(version.created_by)
        self.assertIsNone(version.approved_by)
        self.assertIsNone(version.content_hash)

    def test_header_duplicate_and_invalid_form_retains_inputs(self):
        response = self.client.post(self.url("create"), self.header_payload(code=" rt_cap "))
        self.assertContains(response, "Mã quy trình đã tồn tại.")
        response = self.client.post(self.url("create"), self.header_payload(code="", **{"initial-batch_size": "-1"}))
        self.assertContains(response, "Vui lòng nhập mã quy trình.")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, "Vui lòng kiểm tra các trường được đánh dấu.")
        self.assertEqual(Routing.objects.filter(organization=self.company).count(), 1)

    def test_atomic_header_rolls_back_if_initial_version_fails(self):
        with self.assertRaises(ValidationError):
            services.save_routing(workspace=self.workspace(), data={"product": self.product, "code": "ATOMIC", "name": "Không được lưu", "is_active": True}, initial_version={"batch_size": Decimal(-1)})
        self.assertFalse(Routing.objects.filter(code="ATOMIC").exists())

    def test_header_edit_and_deactivation(self):
        response = self.client.post(self.url("edit", routing=self.routing), self.header_payload(code="rt_cap", name=" Tên cập nhật ", is_active=""), follow=True)
        self.assertContains(response, "Đã cập nhật quy trình sản xuất.")
        saved = Routing.objects.get(pk=self.routing.pk)
        self.assertFalse(saved.is_active)
        self.assertEqual(saved.name, "Tên cập nhật")
        self.assertEqual(saved.created_at, self.routing.created_at)

    def test_empty_states_htmx_and_history_restore(self):
        response = self.client.get(self.url(), {"q": "no_such_record"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Không có kết quả phù hợp.")
        self.assertNotContains(response, "<!doctype")
        restored = self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(restored, "<!doctype")
        RoutingOperation.objects.filter(routing_version=self.version).delete()
        detail = self.client.get(self.url("detail", routing=self.routing))
        self.assertContains(detail, "Quy trình chưa có công đoạn.")
        RoutingVersion.objects.filter(routing=self.routing).delete()
        self.assertContains(self.client.get(self.url("detail", routing=self.routing)), "Quy trình chưa có phiên bản.")
        self.routing.delete()
        self.assertContains(self.client.get(self.url()), "Chưa có quy trình sản xuất.")

    def test_operation_add_decimal_times_quantity_and_resource(self):
        response = self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(), follow=True)
        self.assertContains(response, "Đã thêm công đoạn.")
        saved = RoutingOperation.objects.get(routing_version=self.version, sequence_no=20)
        self.assertEqual(saved.operation_code, "MIX_NEXT")
        self.assertEqual(saved.operation_name, "Phối trộn tiếp")
        self.assertEqual(saved.setup_time, Decimal("1.12345678"))
        self.assertEqual(saved.run_time, Decimal("1.5"))
        self.assertEqual(saved.quantity_basis, Decimal("100.12345678"))
        self.assertEqual(saved.primary_resource_id, self.machine.pk)

    def test_operation_missing_name_code_and_invalid_sequence(self):
        for field, value in (("operation_name", ""), ("operation_code", ""), ("sequence_no", "0"), ("sequence_no", "-1"), ("sequence_no", "2147483648")):
            response = self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(**{field: value}))
            self.assertIn(field, response.context["form"].errors)

    def test_work_center_and_resource_optional_by_schema(self):
        response = self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(work_center="", primary_resource=""))
        self.assertEqual(response.status_code, 302)
        saved = RoutingOperation.objects.get(routing_version=self.version, sequence_no=20)
        self.assertIsNone(saved.work_center_id)
        self.assertIsNone(saved.primary_resource_id)

    def test_negative_times_rejected_zero_times_allowed(self):
        for field in ("setup_time", "run_time"):
            for value in ("-1", "NaN", "Infinity", "0.123456789"):
                form = RoutingOperationForm(self.operation_payload(**{field: value}), workspace=self.workspace(), version=self.version)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
        form = RoutingOperationForm(self.operation_payload(setup_time="0", run_time="0", time_uom=""), workspace=self.workspace(), version=self.version)
        self.assertTrue(form.is_valid(), form.errors)

    def test_time_requires_time_dimension_uom_when_nonzero(self):
        for value in ("", str(self.kg.pk)):
            form = RoutingOperationForm(self.operation_payload(time_uom=value), workspace=self.workspace(), version=self.version)
            self.assertFalse(form.is_valid())
            self.assertIn("time_uom", form.errors)
        self.assertTrue(RoutingOperationForm(self.operation_payload(time_uom=self.minute.pk), workspace=self.workspace(), version=self.version).is_valid())

    def test_quantity_basis_validation_and_unit_pair(self):
        for changes, field in (({"quantity_basis": "0"}, "quantity_basis"), ({"quantity_basis": "-1"}, "quantity_basis"),
            ({"quantity_uom": ""}, "quantity_uom"), ({"quantity_basis": ""}, "quantity_basis")):
            form = RoutingOperationForm(self.operation_payload(**changes), workspace=self.workspace(), version=self.version)
            self.assertFalse(form.is_valid())
            self.assertIn(field, form.errors)
        self.assertTrue(RoutingOperationForm(self.operation_payload(quantity_basis="", quantity_uom=""), workspace=self.workspace(), version=self.version).is_valid())

    def test_duplicate_sequence_rejected_but_code_may_repeat(self):
        response = self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(sequence_no="10"))
        self.assertContains(response, "Thứ tự công đoạn đã tồn tại")
        response = self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(operation_code="MIX"))
        self.assertEqual(response.status_code, 302)

    def test_sequence_defaults_in_steps_of_ten_and_table_order_fixed(self):
        form = RoutingOperationForm(workspace=self.workspace(), version=self.version)
        self.assertEqual(form.initial["sequence_no"], 20)
        RoutingOperation.objects.create(routing_version=self.version, sequence_no=5, operation_code="EARLY", operation_name="Trước")
        response = self.client.get(self.url("version_detail", routing=self.routing, version=self.version), {"sort": "-sequence"})
        self.assertEqual([operation.sequence_no for operation in response.context["operations"]], [5, 10])

    def test_operation_edit_and_remove_confirmation(self):
        edit_url = self.url("operation_edit", routing=self.routing, version=self.version, operation=self.operation)
        response = self.client.post(edit_url, self.operation_payload(sequence_no="10", operation_name="Tên chỉnh sửa"), follow=True)
        self.assertContains(response, "Đã cập nhật công đoạn.")
        self.assertEqual(RoutingOperation.objects.get(pk=self.operation.pk).operation_name, "Tên chỉnh sửa")
        remove_url = self.url("operation_remove", routing=self.routing, version=self.version, operation=self.operation)
        self.assertContains(self.client.get(remove_url), "Bạn có chắc muốn xóa công đoạn này khỏi quy trình?")
        self.assertTrue(RoutingOperation.objects.filter(pk=self.operation.pk).exists())
        self.assertContains(self.client.post(remove_url, follow=True), "Đã xóa công đoạn.")
        self.assertFalse(RoutingOperation.objects.filter(pk=self.operation.pk).exists())

    def test_resource_must_match_center_and_unassigned_resource_allowed(self):
        response = self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(primary_resource=self.packer.pk))
        self.assertIn("primary_resource", response.context["form"].errors)
        values = self.operation_values()
        values["primary_resource"] = self.packer
        with self.assertRaisesMessage(ValidationError, "Nguồn lực không thuộc trung tâm"):
            services.save_operation(workspace=self.workspace(), routing=self.routing, version=self.version, data=values)
        self.assertEqual(self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(primary_resource=self.shared_resource.pk)).status_code, 302)

    def test_dependent_resource_dropdown_filtered_on_server(self):
        url = self.url("operation_resources", routing=self.routing, version=self.version)
        response = self.client.get(url, {"work_center": self.center.pk}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "MIXER")
        self.assertContains(response, "LABOR")
        self.assertNotContains(response, "PACKER")
        self.assertNotContains(response, "PRIVATE_RESOURCE")
        self.assertNotContains(response, "<!doctype")
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_inactive_dropdown_and_existing_reference_retention(self):
        Resource.objects.filter(pk=self.machine.pk).update(is_active=False)
        WorkCenter.objects.filter(pk=self.center.pk).update(is_active=False)
        Uom.objects.filter(pk=self.minute.pk).update(is_active=False)
        form = RoutingOperationForm(workspace=self.workspace(), version=self.version)
        for field, record in (("work_center", self.center), ("primary_resource", self.machine), ("time_uom", self.minute)):
            self.assertFalse(form.fields[field].queryset.filter(pk=record.pk).exists())
        form = RoutingOperationForm(workspace=self.workspace(), version=self.version, instance=self.operation)
        for field, record in (("work_center", self.center), ("primary_resource", self.machine), ("time_uom", self.minute)):
            self.assertTrue(form.fields[field].queryset.filter(pk=record.pk).exists())
        response = self.client.post(self.url("operation_edit", routing=self.routing, version=self.version, operation=self.operation), self.operation_payload(sequence_no="10", time_uom=self.minute.pk))
        self.assertEqual(response.status_code, 302)

    def test_stale_reference_state_revalidated_in_transaction(self):
        values = self.operation_values()
        Resource.objects.filter(pk=self.machine.pk).update(work_center=self.packing)
        with self.assertRaisesMessage(ValidationError, "Nguồn lực không thuộc trung tâm"):
            services.save_operation(workspace=self.workspace(), routing=self.routing, version=self.version, data=values)
        Resource.objects.filter(pk=self.machine.pk).update(work_center=self.center, is_active=False)
        with self.assertRaisesMessage(ValidationError, "ngừng hoạt động"):
            services.save_operation(workspace=self.workspace(), routing=self.routing, version=self.version, data=values)

    def test_htmx_drawer_errors_success_and_delete(self):
        url = self.url("operation_create", routing=self.routing, version=self.version)
        self.assertTemplateUsed(self.client.get(url, HTTP_HX_REQUEST="true"), "bom/routing/partials/operation_editor.html")
        response = self.client.post(url, self.operation_payload(run_time="-1"), HTTP_HX_REQUEST="true")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'value="-1"')
        self.assertNotContains(response, "<!doctype")
        response = self.client.post(url, self.operation_payload(), HTTP_HX_REQUEST="true")
        self.assertEqual(response.headers["HX-Retarget"], "#routing-operations-table")
        self.assertContains(response, 'hx-swap-oob="outerHTML"')
        self.assertContains(response, "Đã thêm công đoạn.")
        saved = RoutingOperation.objects.get(routing_version=self.version, sequence_no=20)
        response = self.client.post(self.url("operation_remove", routing=self.routing, version=self.version, operation=saved), HTTP_HX_REQUEST="true")
        self.assertContains(response, "Đã xóa công đoạn.")

    def test_create_new_version_and_clone_all_operation_fields(self):
        response = self.client.post(self.url("version_create", routing=self.routing) + f"?source={self.version.pk}", self.version_payload(), follow=True)
        self.assertContains(response, "Đã tạo phiên bản quy trình mới.")
        new = RoutingVersion.objects.get(routing=self.routing, version_no=2)
        clone = RoutingOperation.objects.get(routing_version=new)
        for field in OPERATION_FIELDS:
            self.assertEqual(getattr(clone, field), getattr(self.operation, field))
        self.assertEqual(new.status, "DRAFT")
        self.assertIsNone(new.created_by)
        self.assertIsNone(new.approved_by)
        self.assertNotEqual(clone.pk, self.operation.pk)
        self.assertEqual(RoutingOperation.objects.get(pk=self.operation.pk).run_time, Decimal(30))

    def test_version_without_source_has_no_operations(self):
        version = services.create_version(workspace=self.workspace(), routing=self.routing, data=self.version_values())
        self.assertFalse(RoutingOperation.objects.filter(routing_version=version).exists())

    def test_version_batch_and_effective_date_validation(self):
        for changes, field in (({"batch_size": "0"}, "batch_size"), ({"batch_uom": ""}, "batch_uom"),
            ({"effective_to": self.today.isoformat()}, "effective_to"), ({"effective_from": "", "effective_to": self.today.isoformat()}, "effective_from")):
            response = self.client.post(self.url("version_create", routing=self.routing), self.version_payload(**changes))
            self.assertIn(field, response.context["form"].errors)
        form = RoutingVersionForm(self.version_payload(batch_size="", batch_uom="", effective_from=""), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)

    def test_version_edit_and_list_date_status(self):
        response = self.client.post(self.url("version_edit", routing=self.routing, version=self.version), self.version_payload(batch_size="120"), follow=True)
        self.assertContains(response, "Đã cập nhật phiên bản quy trình.")
        self.assertEqual(RoutingVersion.objects.get(pk=self.version.pk).batch_size, Decimal(120))
        response = self.client.get(self.url("version_list", routing=self.routing), {"status": "DRAFT"}, HTTP_HX_REQUEST="true")
        self.assertEqual(list(response.context["records"]), [self.version])
        self.assertNotContains(response, "<!doctype")

    def test_immutable_statuses_enforced_in_service_view_and_database(self):
        for status in ("APPROVED", "EFFECTIVE", "RETIRED"):
            version = RoutingVersion.objects.create(routing=self.routing, version_no=100 + len(status), effective_from=self.today)
            operation = RoutingOperation.objects.create(routing_version=version, sequence_no=10, operation_code="LOCK", operation_name="Đã chốt")
            RoutingVersion.objects.filter(pk=version.pk).update(status=status)
            version.refresh_from_db()
            with self.assertRaisesMessage(ValidationError, "đã được chốt"):
                services.update_version(workspace=self.workspace(), routing=self.routing, instance=version, data=self.version_values())
            with self.assertRaisesMessage(ValidationError, "đã được chốt"):
                services.remove_operation(workspace=self.workspace(), routing=self.routing, version=version, instance=operation)
            response = self.client.post(self.url("operation_edit", routing=self.routing, version=version, operation=operation), self.operation_payload(sequence_no="10"))
            self.assertContains(response, "Không thể chỉnh sửa phiên bản đã được chốt.")
            for mutate in (lambda: RoutingVersion.objects.filter(pk=version.pk).update(batch_size=1),
                lambda: RoutingOperation.objects.filter(pk=operation.pk).update(run_time=1),
                lambda: RoutingOperation.objects.filter(pk=operation.pk).delete()):
                with self.assertRaises(DatabaseError), transaction.atomic():
                    mutate()

    def test_clone_locked_version_keeps_source_unchanged(self):
        RoutingVersion.objects.filter(pk=self.version.pk).update(status="EFFECTIVE")
        self.version.refresh_from_db()
        new = services.create_version(workspace=self.workspace(), routing=self.routing, data=self.version_values(), source=self.version)
        self.assertEqual(new.status, "DRAFT")
        self.assertEqual(RoutingVersion.objects.get(pk=self.version.pk).status, "EFFECTIVE")
        self.assertEqual(RoutingOperation.objects.get(routing_version=new).operation_code, "MIX")

    def test_product_cannot_change_after_locked_version(self):
        another = Product.objects.create(organization=self.company, code="OTHER_PRODUCT", name="Sản phẩm mới", costing_uom=self.kg)
        RoutingVersion.objects.filter(pk=self.version.pk).update(status="APPROVED")
        form = RoutingForm(workspace=self.workspace(), instance=self.routing)
        self.assertTrue(form.fields["product"].disabled)
        with self.assertRaisesMessage(ValidationError, "Không thể đổi sản phẩm"):
            services.save_routing(workspace=self.workspace(), instance=self.routing, data={"product": another, "code": self.routing.code, "name": self.routing.name, "is_active": True})

    def test_clone_rolls_back_when_operation_persistence_fails(self):
        with patch.object(RoutingOperation.objects, "bulk_create", side_effect=RuntimeError("fixture failure")), self.assertRaises(RuntimeError):
            services.create_version(workspace=self.workspace(), routing=self.routing, data=self.version_values(), source=self.version)
        self.assertEqual(RoutingVersion.objects.filter(routing=self.routing).count(), 1)

    def test_foreign_scope_and_wrong_parent_routes_return_404(self):
        for url in (self.url("detail", routing=self.foreign_routing), self.url("edit", routing=self.foreign_routing),
            self.url("version_detail", routing=self.routing, version=self.foreign_version),
            self.url("operation_edit", routing=self.routing, version=self.version, operation=self.foreign_operation), reverse("bom:routing_detail", args=[99999999999999999999])):
            self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.post(self.url("operation_create", routing=self.routing, version=self.version), self.operation_payload(work_center=self.other_center.pk, primary_resource=self.other_resource.pk))
        self.assertIn("work_center", response.context["form"].errors)
        self.assertIn("primary_resource", response.context["form"].errors)

    def test_operations_pagination_and_htmx_canonical_links(self):
        RoutingOperation.objects.bulk_create([RoutingOperation(routing_version=self.version, sequence_no=20+i, operation_code=f"OP_{i}", operation_name="Công đoạn") for i in range(30)])
        url = self.url("version_detail", routing=self.routing, version=self.version)
        response = self.client.get(url, {"page": 2}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="routing-operations-table")
        self.assertEqual(len(response.context["operations"]), 6)
        self.assertNotContains(response, "<!doctype")
        self.assertContains(response, url + "?page=1")
        restored = self.client.get(url, {"page": 2}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="routing-operations-table", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(restored, "<!doctype")

    def test_csrf_and_post_mutation_methods(self):
        client = Client(enforce_csrf_checks=True)
        urls = (self.url("create"), self.url("version_create", routing=self.routing), self.url("operation_create", routing=self.routing, version=self.version), self.url("operation_remove", routing=self.routing, version=self.version, operation=self.operation))
        for url in urls:
            self.assertEqual(client.post(url, {}).status_code, 403)
        self.assertEqual(self.client.post(self.url()).status_code, 405)
        client.get(self.url("operation_create", routing=self.routing, version=self.version))
        token = client.cookies["csrftoken"].value
        response = client.post(urls[2], {**self.operation_payload(), "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 302)

    def test_internal_policy_and_no_organization_form(self):
        request = RequestFactory().get(self.url("create"))
        request._costing_workspace = Workspace(self.company, replace(INTERNAL_ACCESS, can_create_routing=False))
        with self.assertRaises(PermissionDenied):
            routing_create(request)
        with self.assertRaises(PermissionDenied):
            services.save_routing(workspace=request._costing_workspace, data={})
        for form in (RoutingForm(workspace=self.workspace()), RoutingVersionForm(workspace=self.workspace()), RoutingOperationForm(workspace=self.workspace(), version=self.version)):
            for field in ("organization", "status", "created_by", "approved_by", "content_hash"):
                self.assertNotIn(field, form.fields)

    def test_database_checks_and_unique_guard(self):
        for model, record, changes in ((RoutingOperation, self.operation, {"run_time": -1}), (RoutingOperation, self.operation, {"quantity_basis": 0}),
            (RoutingVersion, self.version, {"batch_size": 0}), (RoutingVersion, self.version, {"effective_to": self.today}), (RoutingVersion, self.version, {"status": "LOCKED"})):
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.filter(pk=record.pk).update(**changes)
        with patch("apps.bom.routing_services.validate_operation"), self.assertRaisesMessage(ValidationError, "Thứ tự công đoạn đã tồn tại"):
            values = self.operation_values()
            values["sequence_no"] = 10
            services.save_operation(workspace=self.workspace(), routing=self.routing, version=self.version, data=values)

    def test_selectors_and_rendered_pages_avoid_n_plus_one(self):
        with self.assertNumQueries(1):
            for operation in selectors.operation_queryset(version=self.version, organization=self.company):
                operation.work_center.name
                operation.primary_resource.work_center.name
                operation.time_uom.name
                operation.quantity_uom.name
        with CaptureQueriesContext(connection) as baseline:
            self.client.get(self.url("detail", routing=self.routing))
        RoutingOperation.objects.bulk_create([RoutingOperation(routing_version=self.version, sequence_no=20+i, operation_code=f"QUERY_{i}", operation_name="Công đoạn", work_center=self.center, primary_resource=self.machine, setup_time=1, run_time=1, time_uom=self.minute, quantity_basis=100, quantity_uom=self.kg) for i in range(24)])
        with CaptureQueriesContext(connection) as populated:
            self.client.get(self.url("detail", routing=self.routing))
        self.assertEqual(len(populated), len(baseline))

    def test_clone_query_count_does_not_grow_per_operation(self):
        values = self.version_values()
        workspace = Workspace(self.company)
        with CaptureQueriesContext(connection) as baseline:
            services.create_version(workspace=workspace, routing=self.routing, data=values, source=self.version)
        RoutingOperation.objects.bulk_create([RoutingOperation(routing_version=self.version, sequence_no=20+i, operation_code=f"QUERY_{i}", operation_name="Công đoạn", work_center=self.center, primary_resource=self.machine, setup_time=1, run_time=1, time_uom=self.minute, quantity_basis=100, quantity_uom=self.kg) for i in range(20)])
        with CaptureQueriesContext(connection) as populated:
            services.create_version(workspace=workspace, routing=self.routing, data=values, source=self.version)
        self.assertEqual(len(populated), len(baseline))

    def test_vietnamese_primary_labels(self):
        for url in (self.url(), self.url("create"), self.url("detail", routing=self.routing), self.url("operation_create", routing=self.routing, version=self.version)):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            for label in (">Create<", ">Edit<", ">Save<", ">Search<", ">Login<", ">Logout<"):
                self.assertNotContains(response, label)
