from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Item, Organization, PackagingConfig, PackagingConfigVersion, PackagingLine, Product, Sku, SkuPackagingAssignment, Uom, UomCategory, UomConversion
from apps.master_data.access import get_workspace
from apps.master_data.test_vietnamese_ui import VisibleText
from . import packaging_selectors as selectors, packaging_services as services
from .packaging_constants import LINE_FIELDS, VERSION_FIELDS
from .packaging_forms import PackagingAssignmentForm, PackagingConfigForm, PackagingLineForm, PackagingVersionForm


class PackagingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Organization.objects.create(code="PACKAGING", name="Công ty bao bì")
        cls.other = Organization.objects.create(code="OTHER", name="Công ty khác")
        count = UomCategory.objects.create(code="COUNT", name="Số lượng", dimension_code="COUNT")
        mass = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        length = UomCategory.objects.create(code="LENGTH", name="Chiều dài", dimension_code="LENGTH")
        cls.pc = Uom.objects.create(category=count, code="PC", name="Cái", symbol="cái")
        cls.ct = Uom.objects.create(category=count, code="CT", name="Thùng", symbol="thùng")
        cls.kg = Uom.objects.create(category=mass, code="KG", name="Kilôgam", symbol="kg")
        cls.cm = Uom.objects.create(category=length, code="CM", name="Xentimét", symbol="cm")
        cls.item = Item.objects.create(organization=cls.company, code="BOX", name="Hộp Cappuccino", item_type="PACKAGING", base_uom=cls.pc)
        cls.material = Item.objects.create(organization=cls.company, code="CHOCO", name="Chocolate", item_type="RAW_MATERIAL", base_uom=cls.pc)
        cls.other_item = Item.objects.create(organization=cls.other, code="OTHER_BOX", name="Vật tư khác", item_type="PACKAGING", base_uom=cls.pc)
        cls.product = Product.objects.create(organization=cls.company, code="CAP", name="Cà phê Cappuccino", costing_uom=cls.kg)
        cls.other_product = Product.objects.create(organization=cls.other, code="OTHER", name="Sản phẩm khác", costing_uom=cls.kg)
        cls.second_product = Product.objects.create(organization=cls.company, code="CACAO", name="Cacao", costing_uom=cls.kg)
        cls.sku = Sku.objects.create(organization=cls.company, product=cls.product, code="CAP_20", name="Cappuccino hộp 20 gói", sales_uom=cls.pc, net_quantity=500, net_quantity_uom=cls.kg)
        cls.wrong_sku = Sku.objects.create(organization=cls.company, product=cls.second_product, code="CACAO_20", name="Cacao", sales_uom=cls.pc, net_quantity=1, net_quantity_uom=cls.pc)
        cls.config = PackagingConfig.objects.create(organization=cls.company, product=cls.product, code="PACK_CAP", name="Bao bì Cappuccino", description="Hộp giấy")
        cls.foreign = PackagingConfig.objects.create(organization=cls.other, product=cls.other_product, code="FOREIGN", name="Cấu hình khác")
        cls.today = timezone.localdate()
        cls.version = PackagingConfigVersion.objects.create(packaging_config=cls.config, version_no=1, effective_from=cls.today - timedelta(days=1),
            gross_weight=Decimal("0.50000001"), weight_uom=cls.kg, length=20, width=10, height=5, dimension_uom=cls.cm, change_reason="Bản đầu")
        cls.foreign_version = PackagingConfigVersion.objects.create(packaging_config=cls.foreign, version_no=1)
        cls.line = PackagingLine.objects.create(packaging_config_version=cls.version, packaging_item=cls.item, qty=Decimal("0.08333333"), uom=cls.pc,
            level_code="TERTIARY", parent_level_code="PALLET", units_per_parent=12, market_code="VN", artwork_code="CAP_20", display_order=10, notes="Một phần thùng")
        cls.assignment = SkuPackagingAssignment.objects.create(packaging_config=cls.config, sku=cls.sku, effective_from=cls.today)

    def setUp(self):
        override = override_settings(DEFAULT_ORGANIZATION_ID=self.company.pk)
        override.enable()
        self.addCleanup(override.disable)

    def url(self, action="list", *, config=None, version=None, line=None, assignment=None):
        args = [] if action in ("list", "create") else [(config or self.config).pk]
        if action in ("version_detail", "version_edit", "line_create", "line_edit", "line_remove"):
            args.append((version or self.version).pk)
        if action in ("line_edit", "line_remove"):
            args.append((line or self.line).pk)
        if action == "assignment_edit":
            args.append((assignment or self.assignment).pk)
        return reverse(f"bom:packaging_{action}", args=args)

    def workspace(self):
        return get_workspace(RequestFactory().get(self.url()))

    def version_payload(self, **changes):
        data = dict(effective_from=self.today.isoformat(), effective_to=(self.today + timedelta(days=30)).isoformat(),
            gross_weight="0.75000001", weight_uom=str(self.kg.pk), length="21.00000001", width="12", height="6", dimension_uom=str(self.cm.pk), change_reason=" Quy cách mới ")
        data.update(changes)
        return data

    def config_payload(self, **changes):
        data = dict(product=str(self.product.pk), code=" pack_new ", name=" Cấu hình mới ", description=" Ghi chú ", is_active="on",
            **{f"initial-{field}": value for field, value in self.version_payload().items()})
        data.update(changes)
        return data

    def line_payload(self, **changes):
        data = dict(packaging_item=str(self.item.pk), qty="0.08333333", uom=str(self.pc.pk), level_code="TERTIARY", parent_level_code=" PALLET ",
            units_per_parent="12.00000001", market_code=" VN ", artwork_code=" CAP_20 ", display_order="20", notes=" Một phần thùng ")
        data.update(changes)
        return data

    def assignment_payload(self, **changes):
        data = dict(sku=str(self.sku.pk), effective_from=(self.today + timedelta(days=1)).isoformat(), effective_to="", is_primary="on")
        data.update(changes)
        return data

    def version_data(self, **changes):
        form = PackagingVersionForm(self.version_payload(**changes), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def line_data(self, **changes):
        form = PackagingLineForm(self.line_payload(**changes), workspace=self.workspace(), version=self.version)
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def conversion(self, **changes):
        data = dict(organization=self.company, from_uom=self.ct, to_uom=self.pc, factor=Decimal(12), effective_from=self.today - timedelta(days=10))
        data.update(changes)
        return UomConversion.objects.create(**data)

    def test_pages_anonymous_active_menu_no_auth_or_cost_queries(self):
        actions = ("list", "create", "detail", "edit", "version_list", "version_create", "version_detail", "version_edit", "line_create", "line_edit", "line_remove", "assignment_list", "assignment_create", "assignment_edit")
        with CaptureQueriesContext(connection) as queries:
            for action in actions:
                response = self.client.get(self.url(action))
                self.assertEqual(response.status_code, 200, action)
                self.assertContains(response, 'href="/bom/packaging/" aria-current="page"', count=1)
                self.assertContains(response, 'aria-current="page"', count=1)
                self.assertEqual([title for title, items, expanded in response.context["sidebar_sections"] if expanded], ["SẢN XUẤT"])
                self.assertNotIn("sessionid", response.cookies)
        self.assertFalse(any(any(table in q["sql"] for table in ("organization_member", "supplier_price", "costing_run")) for q in queries))

    def test_search_config_product_and_assigned_sku(self):
        SkuPackagingAssignment.objects.create(packaging_config=self.config, sku=self.sku, effective_from=self.today - timedelta(days=20))
        for term in ("pack_cap", "Bao bì Cappuccino", "Hộp giấy", "cap_20", "hộp 20 gói", "Cà phê Cappuccino"):
            self.assertEqual(list(self.client.get(self.url(), {"q": term}).context["records"]), [self.config])
        unassigned = PackagingConfig.objects.create(organization=self.company, product=self.product, code="UNASSIGNED", name="Chưa gán")
        self.assertNotIn(unassigned, self.client.get(self.url(), {"q": self.sku.code}).context["records"])

    def test_filters_and_invalid_foreign_ids(self):
        for filters in ({"product": self.product.pk}, {"sku": self.sku.pk}, {"active": "true"}, {"status": "DRAFT"}, {"effective": "EFFECTIVE"}):
            self.assertEqual(list(self.client.get(self.url(), filters).context["records"]), [self.config])
        for filters in ({"product": self.other_product.pk}, {"sku": self.wrong_sku.pk}, {"active": "false"}, {"status": "APPROVED"}, {"effective": "EXPIRED"}):
            self.assertEqual(list(self.client.get(self.url(), filters).context["records"]), [])
        for parameter in ("product", "sku"):
            for value in ("bad", "9" * 100, "-1", "１２"):
                self.assertEqual(list(self.client.get(self.url(), {parameter: value}).context["records"]), [])

    def test_latest_version_and_date_status_are_separate(self):
        newest = PackagingConfigVersion.objects.create(packaging_config=self.config, version_no=2)
        self.assertEqual(self.client.get(self.url("detail")).context["version"], newest)
        record = self.client.get(self.url()).context["records"][0]
        self.assertEqual(record.latest_version_no, 2)
        self.assertEqual(record.date_status, "UNDATED")
        for start, end, status in ((self.today + timedelta(days=1), None, "FUTURE"), (self.today - timedelta(days=2), self.today - timedelta(days=1), "EXPIRED"), (self.today - timedelta(days=1), self.today, "EFFECTIVE")):
            PackagingConfigVersion.objects.filter(pk=newest.pk).update(effective_from=start, effective_to=end)
            record = self.client.get(self.url()).context["records"][0]
            self.assertEqual((record.date_status, record.latest_status), (status, "DRAFT"))

    def test_sort_and_pagination_whitelist(self):
        PackagingConfig.objects.bulk_create([PackagingConfig(organization=self.company, product=self.product, code=f"PACK_{i:03}", name=f"Bao bì {i}") for i in range(105)])
        for per_page in (25, 50, 100):
            response = self.client.get(self.url(), {"per_page": per_page, "sort": "-code"})
            self.assertEqual(len(response.context["records"]), per_page)
            self.assertEqual(response.context["records"][0].code, "PACK_CAP")
        self.assertEqual(len(self.client.get(self.url(), {"page": 5}).context["records"]), 6)
        for sort in ("code", "name", "created_at", "effective_from", "version", "-name"):
            self.assertEqual(self.client.get(self.url(), {"sort": sort}).context["current_sort"], sort)
        bad = self.client.get(self.url(), {"sort": "--code", "per_page": "9", "page": "bad"})
        self.assertEqual((bad.context["current_sort"], bad.context["per_page"]), ("code", 25))

    def test_create_atomic_normalizes_and_nullable_actors(self):
        response = self.client.post(self.url("create"), self.config_payload())
        self.assertEqual(response.status_code, 302)
        config = PackagingConfig.objects.get(code="PACK_NEW")
        self.assertEqual((config.organization_id, config.name, config.description), (self.company.pk, "Cấu hình mới", "Ghi chú"))
        version = PackagingConfigVersion.objects.get(packaging_config=config)
        self.assertEqual((version.status, version.version_no, version.created_by, version.approved_by), ("DRAFT", 1, None, None))
        self.assertEqual(version.gross_weight, Decimal("0.75000001"))
        self.assertIsNone(version.content_hash)

    def test_duplicate_code_and_database_race_mapped(self):
        response = self.client.post(self.url("create"), self.config_payload(code=" pack_cap "))
        self.assertContains(response, "Mã cấu hình bao bì đã tồn tại.")
        form = PackagingConfigForm(self.config_payload(), workspace=self.workspace())
        self.assertTrue(form.is_valid(), form.errors)
        with patch("apps.bom.packaging_services.validate_config"):
            with self.assertRaises(ValidationError) as caught:
                services.save_config(workspace=self.workspace(), data={**form.cleaned_data, "code": self.config.code}, initial_version=self.version_data())
        self.assertEqual(caught.exception.message_dict, {"code": ["Mã cấu hình bao bì đã tồn tại."]})

    def test_invalid_header_and_prefix_accessibility(self):
        response = self.client.post(self.url("create"), self.config_payload(code="", name="", **{"initial-gross_weight": "-1"}))
        self.assertContains(response, "Vui lòng nhập mã cấu hình bao bì.")
        self.assertContains(response, 'aria-describedby="id_initial-gross_weight_help id_initial-gross_weight_errors"')
        self.assertFalse(PackagingConfig.objects.filter(code="PACK_NEW").exists())
        with patch("apps.bom.packaging_services._new_version", side_effect=ValidationError("Lỗi thử rollback")):
            self.client.post(self.url("create"), self.config_payload())
        self.assertFalse(PackagingConfig.objects.filter(code="PACK_NEW").exists())

    def test_edit_header_deactivate(self):
        response = self.client.post(self.url("edit"), self.config_payload(code=" pack_cap ", name=" Bao bì mới ", is_active=""), follow=True)
        self.assertContains(response, "Đã cập nhật cấu hình bao bì.")
        self.config.refresh_from_db()
        self.assertEqual((self.config.name, self.config.is_active), ("Bao bì mới", False))

    def test_new_version_clones_every_line_and_all_config_fields(self):
        PackagingLine.objects.bulk_create([PackagingLine(packaging_config_version=self.version, packaging_item=self.item, qty=i + 1, uom=self.pc, level_code="PRIMARY") for i in range(30)])
        old = {field: getattr(self.version, field) for field in VERSION_FIELDS}
        response = self.client.post(self.url("version_create") + f"?source={self.version.pk}", self.version_payload())
        self.assertEqual(response.status_code, 302)
        newest = PackagingConfigVersion.objects.get(packaging_config=self.config, version_no=2)
        self.assertEqual((newest.status, newest.created_by, newest.approved_at), ("DRAFT", None, None))
        self.assertEqual(PackagingLine.objects.filter(packaging_config_version=newest).count(), 31)
        cloned = PackagingLine.objects.get(packaging_config_version=newest, display_order=10)
        for field in LINE_FIELDS:
            self.assertEqual(getattr(cloned, field), getattr(self.line, field))
        self.version.refresh_from_db()
        self.assertEqual({field: getattr(self.version, field) for field in VERSION_FIELDS}, old)

    def test_clone_prefill_and_blank_new_version(self):
        form = self.client.get(self.url("version_create"), {"source": self.version.pk}).context["form"]
        self.assertEqual(form["gross_weight"].value(), self.version.gross_weight)
        response = self.client.post(self.url("version_create"), {"status": "EFFECTIVE", "version_no": 100})
        self.assertEqual(response.status_code, 302)
        newest = PackagingConfigVersion.objects.get(packaging_config=self.config, version_no=2)
        self.assertEqual(newest.status, "DRAFT")
        self.assertFalse(PackagingLine.objects.filter(packaging_config_version=newest).exists())

    def test_clone_failure_rolls_back_version_and_lines(self):
        with patch("apps.bom.packaging_services.PackagingLine.objects.bulk_create", side_effect=ValidationError("Lỗi clone")):
            response = self.client.post(self.url("version_create") + f"?source={self.version.pk}", self.version_payload())
        self.assertContains(response, "Lỗi clone")
        self.assertEqual(PackagingConfigVersion.objects.filter(packaging_config=self.config).count(), 1)
        self.assertEqual(PackagingLine.objects.count(), 1)

    def test_version_period_and_measurement_validation(self):
        for data, field in (({"effective_to": self.today.isoformat()}, "effective_to"), ({"effective_from": ""}, "effective_from"),
            ({"gross_weight": "-1"}, "gross_weight"), ({"length": "-1"}, "length"), ({"width": "-1"}, "width"), ({"height": "-1"}, "height"),
            ({"weight_uom": str(self.cm.pk)}, "weight_uom"), ({"dimension_uom": str(self.kg.pk)}, "dimension_uom"), ({"weight_uom": ""}, "weight_uom")):
            form = PackagingVersionForm(self.version_payload(**data), workspace=self.workspace())
            self.assertFalse(form.is_valid(), data)
            self.assertIn(field, form.errors)
        self.assertEqual(self.client.post(self.url("version_edit"), self.version_payload()).status_code, 302)

    def test_no_overlap_rule_invented(self):
        self.assertEqual(self.client.post(self.url("version_create"), self.version_payload()).status_code, 302)
        self.assertEqual(self.client.post(self.url("version_create"), self.version_payload()).status_code, 302)

    def test_add_fractional_line_and_structure_fields(self):
        response = self.client.post(self.url("line_create"), self.line_payload())
        self.assertEqual(response.status_code, 302)
        line = PackagingLine.objects.order_by("-pk").first()
        self.assertEqual(line.qty, Decimal("0.08333333"))
        self.assertEqual(line.units_per_parent, Decimal("12.00000001"))
        self.assertEqual((line.parent_level_code, line.market_code, line.artwork_code, line.notes), ("PALLET", "VN", "CAP_20", "Một phần thùng"))
        # The DB parent code is free text, unlike level_code's CHECK. Preserve
        # legacy/custom codes instead of turning the display dropdown into a rule.
        self.assertEqual(self.client.post(self.url("line_edit"), self.line_payload(parent_level_code="CUSTOM_LEVEL")).status_code, 302)
        form = self.client.get(self.url("line_edit")).context["form"]
        self.assertIn(("CUSTOM_LEVEL", "CUSTOM_LEVEL"), tuple(form.fields["parent_level_code"].widget.choices))

    def test_line_required_positive_precision_and_level(self):
        for field, value in (("packaging_item", ""), ("uom", ""), ("qty", "0"), ("qty", "-1"), ("qty", "0.123456789"), ("units_per_parent", "0"), ("units_per_parent", "-1"), ("level_code", "BAD")):
            response = self.client.post(self.url("line_create"), self.line_payload(**{field: value}))
            self.assertEqual(response.status_code, 200)
            self.assertIn(field, response.context["form"].errors)
        self.assertEqual(PackagingLine.objects.count(), 1)

    def test_edit_line_and_remove_only_on_confirmed_post(self):
        self.assertEqual(self.client.post(self.url("line_edit"), self.line_payload(qty="0.25")).status_code, 302)
        self.line.refresh_from_db()
        self.assertEqual(self.line.qty, Decimal("0.25"))
        self.assertContains(self.client.get(self.url("line_remove")), "Bạn có chắc muốn xóa thành phần bao bì này?")
        self.assertTrue(PackagingLine.objects.filter(pk=self.line.pk).exists())
        self.assertEqual(self.client.post(self.url("line_remove"), {}).status_code, 302)
        self.assertFalse(PackagingLine.objects.filter(pk=self.line.pk).exists())

    def test_duplicate_item_and_all_existing_types_allowed(self):
        self.assertEqual(self.client.post(self.url("line_create"), self.line_payload()).status_code, 302)
        self.assertEqual(self.client.post(self.url("line_create"), self.line_payload(packaging_item=str(self.material.pk))).status_code, 302)
        self.assertEqual(PackagingLine.objects.filter(packaging_item=self.item).count(), 2)
        form = PackagingLineForm(workspace=self.workspace(), version=self.version)
        self.assertEqual(form.fields["packaging_item"].queryset.first(), self.item)

    def test_inactive_master_create_hidden_existing_edit_clone_retained(self):
        Item.objects.filter(pk=self.item.pk).update(is_active=False)
        Uom.objects.filter(pk=self.pc.pk).update(is_active=False)
        form = self.client.get(self.url("line_create")).context["form"]
        self.assertNotIn(self.item, form.fields["packaging_item"].queryset)
        self.assertNotIn(self.pc, form.fields["uom"].queryset)
        self.assertEqual(self.client.post(self.url("line_create"), self.line_payload()).status_code, 200)
        self.assertEqual(self.client.post(self.url("line_edit"), self.line_payload()).status_code, 302)
        self.assertEqual(self.client.post(self.url("version_create") + f"?source={self.version.pk}", self.version_payload()).status_code, 302)

    def test_conversion_needed_and_either_direction_accepted(self):
        response = self.client.post(self.url("line_create"), self.line_payload(uom=str(self.ct.pk)))
        self.assertContains(response, "không tìm thấy quy đổi đơn vị phù hợp")
        self.conversion()
        self.assertEqual(self.client.post(self.url("line_create"), self.line_payload(uom=str(self.ct.pk))).status_code, 302)
        UomConversion.objects.all().delete()
        self.conversion(from_uom=self.pc, to_uom=self.ct, factor=Decimal("0.083333333333"))
        self.assertEqual(self.client.post(self.url("line_create"), self.line_payload(uom=str(self.ct.pk))).status_code, 302)

    def test_conversion_scope_date_and_item_specific_cross_category(self):
        self.conversion(organization=self.other)
        self.assertFalse(PackagingLineForm(self.line_payload(uom=str(self.ct.pk)), workspace=self.workspace(), version=self.version).is_valid())
        UomConversion.objects.all().delete()
        self.conversion(organization=None, effective_from=self.today + timedelta(days=2))
        self.assertFalse(PackagingLineForm(self.line_payload(uom=str(self.ct.pk)), workspace=self.workspace(), version=self.version).is_valid())
        UomConversion.objects.all().delete()
        self.conversion(organization=None, item=self.item, from_uom=self.kg, to_uom=self.pc)
        self.assertTrue(PackagingLineForm(self.line_payload(uom=str(self.kg.pk)), workspace=self.workspace(), version=self.version).is_valid())

    def test_version_date_change_and_clone_revalidate_conversions(self):
        self.conversion(effective_to=self.today + timedelta(days=1))
        self.client.post(self.url("line_edit"), self.line_payload(uom=str(self.ct.pk)))
        response = self.client.post(self.url("version_edit"), self.version_payload(effective_from=(self.today + timedelta(days=2)).isoformat()))
        self.assertContains(response, "không tìm thấy quy đổi đơn vị phù hợp")
        response = self.client.post(self.url("version_create") + f"?source={self.version.pk}", self.version_payload(effective_from=(self.today + timedelta(days=2)).isoformat()))
        self.assertContains(response, "không tìm thấy quy đổi đơn vị phù hợp")

    def test_stale_inactive_reference_cannot_bypass_service(self):
        data = self.line_data()
        Item.objects.filter(pk=self.item.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            services.save_line(workspace=self.workspace(), config=self.config, version=self.version, data=data)

    def test_assignment_create_edit_duplicate_and_product_scope(self):
        self.assertEqual(self.client.post(self.url("assignment_create"), self.assignment_payload()).status_code, 302)
        response = self.client.post(self.url("assignment_create"), self.assignment_payload())
        self.assertContains(response, "SKU đã được gán cấu hình này với cùng ngày bắt đầu.")
        self.assertEqual(self.client.post(self.url("assignment_edit"), self.assignment_payload(effective_from=self.today.isoformat(), is_primary="")).status_code, 302)
        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.is_primary)
        response = self.client.post(self.url("assignment_create"), self.assignment_payload(sku=str(self.wrong_sku.pk)))
        self.assertIn("sku", response.context["form"].errors)

    def test_assignment_dates_search_and_history(self):
        response = self.client.post(self.url("assignment_create"), self.assignment_payload(effective_from=self.today.isoformat(), effective_to=self.today.isoformat()))
        self.assertIn("effective_to", response.context["form"].errors)
        self.assertEqual(list(self.client.get(self.url("assignment_list"), {"q": "cap_20"}).context["records"]), [self.assignment])
        Sku.objects.filter(pk=self.sku.pk).update(is_active=False)
        self.assertNotIn(self.sku, self.client.get(self.url("assignment_create")).context["form"].fields["sku"].queryset)
        self.assertIn(self.sku, self.client.get(self.url("assignment_edit")).context["form"].fields["sku"].queryset)
        self.assertContains(self.client.get(self.url("detail")), self.sku.code)

    def test_assignment_integrity_race_mapped(self):
        form = PackagingAssignmentForm(self.assignment_payload(effective_from=self.today.isoformat()), workspace=self.workspace(), config=self.config)
        data = {"sku": self.sku, "effective_from": self.today, "effective_to": None, "is_primary": True}
        with patch("apps.bom.packaging_services.validate_assignment"):
            with self.assertRaises(ValidationError) as error:
                services.save_assignment(workspace=self.workspace(), config=self.config, data=data)
        self.assertIn("effective_from", error.exception.message_dict)

    def test_product_cannot_change_when_assigned_or_immutable(self):
        with self.assertRaises(ValidationError):
            services.save_config(workspace=self.workspace(), instance=self.config, data={"product": self.second_product, "code": self.config.code, "name": self.config.name, "description": None, "is_active": True})
        self.assertTrue(self.client.get(self.url("edit")).context["form"].fields["product"].disabled)

    def test_deleted_version_race_returns_not_found_instead_of_server_error(self):
        def remove_during_save(**kwargs):
            PackagingLine.objects.filter(packaging_config_version=self.version).delete()
            PackagingConfigVersion.objects.filter(pk=self.version.pk).delete()
            raise ValidationError("Không tìm thấy phiên bản.")
        for action in ("version_edit", "line_create"):
            with self.subTest(action=action), transaction.atomic():
                with patch("apps.bom.packaging_services.update_version" if action == "version_edit" else "apps.bom.packaging_services.save_line", side_effect=remove_during_save):
                    response = self.client.post(self.url(action), self.version_payload() if action == "version_edit" else self.line_payload())
                self.assertEqual(response.status_code, 404)
                transaction.set_rollback(True)

    def test_nested_scope_and_parent_move_blocked(self):
        for action in ("detail", "edit", "version_list", "assignment_list", "assignment_create"):
            self.assertEqual(self.client.get(self.url(action, config=self.foreign)).status_code, 404)
        self.assertEqual(self.client.get(self.url("version_detail", version=self.foreign_version)).status_code, 404)
        self.assertEqual(self.client.get(self.url("version_create"), {"source": self.foreign_version.pk}).status_code, 404)
        for bad in ("bad", "9" * 100):
            self.assertEqual(self.client.get(self.url("version_create"), {"source": bad}).status_code, 404)
        response = self.client.post(self.url("line_edit"), self.line_payload(packaging_config_version=self.foreign_version.pk))
        self.assertEqual(response.status_code, 302)
        self.line.refresh_from_db()
        self.assertEqual(self.line.packaging_config_version_id, self.version.pk)

    def test_immutable_versions_and_lines_every_guarded_status(self):
        for status in ("APPROVED", "EFFECTIVE", "RETIRED"):
            version = PackagingConfigVersion.objects.create(packaging_config=self.config, version_no=10 * (1 + ("APPROVED", "EFFECTIVE", "RETIRED").index(status)), effective_from=self.today)
            line = PackagingLine.objects.create(packaging_config_version=version, packaging_item=self.item, qty=1, uom=self.pc, level_code="PRIMARY")
            PackagingConfigVersion.objects.filter(pk=version.pk).update(status=status)
            for action, payload in (("version_edit", self.version_payload()), ("line_create", self.line_payload()), ("line_edit", self.line_payload()), ("line_remove", {})):
                response = self.client.post(self.url(action, version=version, line=line), payload)
                self.assertContains(response, "Không thể chỉnh sửa phiên bản đã được chốt")
            self.assertEqual(self.client.post(self.url("version_create") + f"?source={version.pk}", self.version_payload()).status_code, 302)
            self.assertNotContains(self.client.get(self.url("version_detail", version=version)), "+ Thêm thành phần")

    def test_database_trigger_is_final_protection(self):
        PackagingConfigVersion.objects.filter(pk=self.version.pk).update(status="EFFECTIVE")
        operations = (lambda: PackagingConfigVersion.objects.filter(pk=self.version.pk).update(gross_weight=2),
            lambda: PackagingLine.objects.filter(pk=self.line.pk).update(qty=2), lambda: PackagingLine.objects.filter(pk=self.line.pk).delete(),
            lambda: PackagingLine.objects.create(packaging_config_version=self.version, packaging_item=self.item, qty=1, uom=self.pc, level_code="PRIMARY"))
        for operation in operations:
            with self.assertRaises(DatabaseError), transaction.atomic():
                operation()
        with patch("apps.bom.packaging_services.ensure_editable"):
            with self.assertRaises(ValidationError) as error:
                services.save_line(workspace=self.workspace(), config=self.config, version=self.version, instance=self.line, data=self.line_data())
        self.assertIn("Không thể chỉnh sửa phiên bản đã được chốt", str(error.exception))

    def test_database_checks_match_inspected_schema(self):
        for field, value in (("gross_weight", -1), ("length", -1), ("width", -1), ("height", -1), ("effective_to", self.version.effective_from), ("status", "BAD")):
            with self.assertRaises(IntegrityError), transaction.atomic():
                PackagingConfigVersion.objects.filter(pk=self.version.pk).update(**{field: value})
        for field, value in (("qty", 0), ("qty", -1), ("units_per_parent", 0), ("level_code", "BAD")):
            with self.assertRaises(IntegrityError), transaction.atomic():
                PackagingLine.objects.filter(pk=self.line.pk).update(**{field: value})

    def test_htmx_drawer_validation_result_and_pagination_targets(self):
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "master_data/partials/reference_data_table.html")
        self.assertNotContains(response, "<!doctype")
        self.assertTemplateUsed(self.client.get(self.url(), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"), "master_data/reference_data_list.html")
        response = self.client.get(self.url("line_create"), HTTP_HX_REQUEST="true")
        self.assertContains(response, 'role="dialog"')
        self.assertContains(response, 'x-data="overlayPanel(true)"')
        invalid = self.client.post(self.url("line_create"), self.line_payload(qty="0"), HTTP_HX_REQUEST="true")
        self.assertContains(invalid, "Số lượng phải lớn hơn 0.")
        PackagingLine.objects.bulk_create([PackagingLine(packaging_config_version=self.version, packaging_item=self.item, qty=i + 1, uom=self.pc, level_code="PRIMARY") for i in range(30)])
        response = self.client.post(self.url("line_create") + "?page=2&per_page=25", self.line_payload(), HTTP_HX_REQUEST="true")
        self.assertEqual(response["HX-Retarget"], "#packaging-lines-table")
        self.assertContains(response, 'hx-swap-oob="outerHTML"')
        self.assertContains(response, self.url("version_detail") + "?page=1&amp;per_page=25")
        self.assertContains(response, "Đã thêm thành phần bao bì.")
        partial = self.client.get(self.url("version_detail"), HTTP_HX_REQUEST="true", HTTP_HX_TARGET="packaging-lines-table")
        self.assertTemplateUsed(partial, "bom/packaging/partials/lines_table.html")
        self.assertNotContains(partial, 'id="packaging-detail"')
        self.assertNotContains(self.client.get(self.url("line_create")), "hx-post=")

    def test_empty_states_and_legacy_config(self):
        self.assertContains(self.client.get(self.url(), {"q": "missing"}), "Không có kết quả phù hợp.")
        PackagingLine.objects.all().delete()
        self.assertContains(self.client.get(self.url("detail")), "Cấu hình chưa có thành phần bao bì.")
        empty = PackagingConfig.objects.create(organization=self.company, product=self.product, code="EMPTY", name="Chưa có bản")
        self.assertContains(self.client.get(self.url("detail", config=empty)), "Cấu hình chưa có phiên bản.")
        SkuPackagingAssignment.objects.all().delete()
        PackagingConfigVersion.objects.all().delete()
        PackagingConfig.objects.all().delete()
        self.assertContains(self.client.get(self.url()), "Chưa có cấu hình bao bì.")

    def test_csrf_and_audit_fields_not_exposed(self):
        client = Client(enforce_csrf_checks=True)
        for action, data in (("create", self.config_payload()), ("version_create", self.version_payload()), ("line_create", self.line_payload()), ("line_remove", {}), ("assignment_create", self.assignment_payload())):
            page = client.get(self.url(action))
            self.assertContains(page, 'name="csrfmiddlewaretoken"')
            for field in ("organization", "created_by", "approved_by", "status", "version_no", "content_hash"):
                self.assertNotContains(page, f'name="{field}"')
            self.assertEqual(client.post(self.url(action), data).status_code, 403)
            self.assertEqual(client.post(self.url(action), data, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 302)

    def test_bounded_queries_lines_and_assignment_preview(self):
        PackagingLine.objects.bulk_create([PackagingLine(packaging_config_version=self.version, packaging_item=self.item, qty=i + 1, uom=self.pc, level_code="PRIMARY") for i in range(40)])
        SkuPackagingAssignment.objects.bulk_create([SkuPackagingAssignment(packaging_config=self.config, sku=self.sku, effective_from=self.today + timedelta(days=i + 1)) for i in range(30)])
        with self.assertNumQueries(1):
            for line in selectors.line_queryset(version=self.version, organization=self.company):
                _ = line.packaging_item.name, line.uom.symbol
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url())
        self.assertLessEqual(len(queries), 7)
        self.assertFalse(any('"packaging_line"' in q["sql"] for q in queries))
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url("detail"))
        self.assertLessEqual(len(queries), 9)
        self.assertEqual(len(response.context["lines"]), 25)
        self.assertEqual(len(response.context["assignments"]), 5)

    def test_vietnamese_display_decimal_date_and_no_fake_output(self):
        import re
        banned = re.compile(r"\b(?:Create|Edit|Save|Cancel|Search|Filter|Status|Actions|Active|Inactive|Name|Description)\b")
        for action in ("list", "create", "detail", "version_list", "version_edit", "line_create", "assignment_create"):
            response = self.client.get(self.url(action))
            parser = VisibleText()
            parser.feed(response.content.decode())
            self.assertIsNone(banned.search(" ".join(parser.text)))
            self.assertContains(response, 'lang="vi"')
            self.assertNotContains(response, "Sản lượng chuẩn")
        response = self.client.get(self.url("detail"))
        self.assertContains(response, "0,08333333")
        self.assertContains(response, "Cấp 3 · Bao bì vận chuyển")
        self.assertContains(response, self.version.effective_from.strftime("%d/%m/%Y"))
