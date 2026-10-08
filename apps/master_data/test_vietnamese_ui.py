"""Presentation checks on representative pages, without HTML snapshots."""
import re
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser

from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from apps.core.models import CostElement, Currency, Item, Organization, Product, ProductCategory, Sku, Supplier, SupplierPrice, Uom, UomCategory, UomConversion
from .presentation import ENUM_LABELS, format_number


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if not self.skip:
            self.text.extend(value for key, value in attrs if key in ("aria-label", "placeholder", "title") and value)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


class VietnameseUITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        organization = Organization.objects.create(code="VI", name="Công ty")
        cls.currency = Currency.objects.create(code="VND", name="Việt Nam đồng")
        cls.uom_category = UomCategory.objects.create(code="MASS", name="Khối lượng", dimension_code="MASS")
        cls.uom = Uom.objects.create(category=cls.uom_category, code="KG", name="Kilôgam", symbol="kg")
        gram = Uom.objects.create(category=cls.uom_category, code="G", name="Gam", symbol="g")
        cls.uom_conversion = UomConversion.objects.create(organization=organization, from_uom=cls.uom, to_uom=gram, factor=Decimal("1000.500000000000"), effective_from=date(2026, 10, 7))
        cls.cost_element = CostElement.objects.create(organization=organization, code="MATERIAL_COST", name="Chi phí nguyên liệu", value_type="MONEY", currency_code=cls.currency, default_source_mode="MANUAL", accounting_scope="INVENTORY_COST", cost_scope="MANUFACTURING")
        cls.category = ProductCategory.objects.create(organization=organization, code="NL", name="Nguyên liệu")
        cls.item = Item.objects.create(organization=organization, category=cls.category, code="ITEM_VI", name="Vật tư", item_type="RAW_MATERIAL", base_uom=cls.uom)
        cls.product = Product.objects.create(organization=organization, category=cls.category, code="PRODUCT_VI", name="Sản phẩm", costing_uom=cls.uom)
        cls.sku = Sku.objects.create(organization=organization, product=cls.product, code="SKU_VI", name="Quy cách bán", sales_uom=cls.uom, net_quantity=Decimal("1"), net_quantity_uom=cls.uom)
        cls.supplier = Supplier.objects.create(organization=organization, code="NCC_VI", name="Nhà cung cấp Việt", default_currency_code=cls.currency)
        cls.supplier_price = SupplierPrice.objects.create(organization=organization, supplier=cls.supplier, item=cls.item, price_uom=cls.uom, currency_code=cls.currency, unit_price=Decimal("125000"), effective_from=date(2026, 10, 7))

    def test_main_list_detail_create_edit_labels_are_vietnamese(self):
        banned = re.compile(r"\b(?:Create|Edit|Save|Cancel|Search|Filter|Status|Actions|Active|Inactive|Name|Description|Reset|More)\b")
        pages = (("master_data", "cost_element", self.cost_element), ("master_data", "currency", self.currency),
            ("master_data", "uom_category", self.uom_category), ("master_data", "uom", self.uom),
            ("master_data", "uom_conversion", self.uom_conversion), ("product", "category", self.category), ("product", "item", self.item),
            ("product", "product", self.product), ("product", "sku", self.sku),
            ("master_data", "supplier", self.supplier), ("master_data", "supplier_price", self.supplier_price))
        for namespace, resource, record in pages:
            for action in ("list", "detail", "create", "edit"):
                with self.subTest(resource=resource, action=action):
                    response = self.client.get(reverse(f"{namespace}:{resource}_{action}", args=[record.pk] if action in ("detail", "edit") else []))
                    self.assertEqual(response.status_code, 200)
                    parser = VisibleText()
                    parser.feed(response.content.decode())
                    self.assertIsNone(banned.search(" ".join(parser.text)))
                    self.assertContains(response, 'lang="vi"')
                    self.assertNotContains(response, "Costing &amp; Pricing")
                    self.assertNotContains(response, "OrganizationMember")

    def test_cost_element_enum_labels_keep_stored_codes(self):
        response = self.client.get(reverse("master_data:cost_element_list"))
        self.assertContains(response, "Tiền tệ")
        self.assertContains(response, "Nhập thủ công")
        self.assertContains(response, "Chi phí hàng tồn kho")
        self.assertContains(response, "Sản xuất")
        form = self.client.get(reverse("master_data:cost_element_create"))
        self.assertContains(form, 'value="MONEY"')
        self.assertContains(form, 'value="MANUAL"')
        self.cost_element.refresh_from_db()
        self.assertEqual(self.cost_element.code, "MATERIAL_COST")
        self.assertEqual(self.cost_element.value_type, "MONEY")

    def test_status_badges_have_translated_text(self):
        for code in ("ACTIVE", "INACTIVE", "DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "RETIRED", "REJECTED", "FAILED", "LOCKED", "SUPERSEDED", "FUTURE", "EXPIRED"):
            html = render_to_string("components/status_badge.html", {"status": code})
            self.assertIn(ENUM_LABELS[code], html)
            self.assertNotIn(f">{code}<", html)

    def test_number_and_date_display_preserves_database_precision(self):
        self.assertEqual(format_number(Decimal("125000.00000000")), "125.000")
        self.assertEqual(format_number(Decimal("1000.000000000001")), "1.000,000000000001")
        self.assertEqual(format_number(Decimal("0.00000001")), "0,00000001")
        self.assertEqual(format_number(Decimal("0")), "0")
        self.assertEqual(format_number(None), "—")
        response = self.client.get(reverse("master_data:uom_conversion_list"))
        self.assertContains(response, "07/10/2026")
        self.assertContains(response, "1.000,5")
        detail = self.client.get(reverse("master_data:uom_conversion_detail", args=[self.uom_conversion.pk]))
        self.assertContains(detail, "07/10/2026")
        self.assertContains(detail, "1.000,5")
        self.uom_conversion.refresh_from_db()
        self.assertEqual(self.uom_conversion.factor, Decimal("1000.500000000000"))

    def test_invalid_forms_have_vietnamese_feedback(self):
        for namespace, resource in (("master_data", "cost_element"), ("master_data", "currency"), ("master_data", "uom"), ("master_data", "uom_conversion"), ("product", "category"), ("product", "item"), ("product", "product"), ("product", "sku"), ("master_data", "supplier"), ("master_data", "supplier_price")):
            response = self.client.post(reverse(f"{namespace}:{resource}_create"), {})
            self.assertContains(response, "Vui lòng kiểm tra các trường được đánh dấu.")
            self.assertContains(response, 'aria-invalid="true"')
            self.assertNotContains(response, "This field is required")
            self.assertNotContains(response, "IntegrityError")
