from django import forms
from django.db.models import Q

from apps.core.models import Item, Product, ProductCategory, Sku, Uom
from apps.master_data.forms import CompactNumberInput, ReferenceChoiceField, ReferenceDataForm, UnitChoiceField
from .constants import CATEGORY_FIELDS, ITEM_FIELDS, ITEM_TYPES, MEASUREMENT_FIELDS, PRODUCT_FIELDS, SKU_FIELDS, SKU_UNIT_FIELDS, UNIT_FIELDS
from .validators import normalize_product_values, validate_category, validate_item, validate_product, validate_sku


class ProductCategoryForm(ReferenceDataForm):
    validate_values = staticmethod(validate_category)

    class Meta:
        model = ProductCategory
        fields = CATEGORY_FIELDS
        labels = {"code": "Mã", "name": "Tên nhóm sản phẩm", "description": "Mô tả", "is_active": "Đang hoạt động"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization


class ItemForm(ReferenceDataForm):
    validate_values = staticmethod(validate_item)
    category = ReferenceChoiceField(queryset=ProductCategory.objects.none(), required=False, label="Nhóm sản phẩm")
    item_type = forms.ChoiceField(choices=ITEM_TYPES, label="Loại vật tư / hàng hóa")
    base_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị cơ sở")
    purchase_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị mua")
    production_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị sản xuất")
    weight_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị trọng lượng")
    dimension_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị kích thước")

    class Meta:
        model = Item
        fields = ITEM_FIELDS
        labels = {
            "code": "Mã", "name": "Tên", "tax_class_code": "Mã nhóm thuế",
            "net_weight": "Khối lượng tịnh", "gross_weight": "Khối lượng tổng",
            "length": "Chiều dài", "width": "Chiều rộng", "height": "Chiều cao",
            "is_stock_item": "Theo dõi tồn kho", "is_active": "Đang hoạt động",
        }
        help_texts = {"code": "Mã được chuẩn hóa thành chữ hoa.", "tax_class_code": "Để trống nếu chưa phân loại thuế."}
        widgets = {field: CompactNumberInput(attrs={"min": "0", "step": "any"}) for field in MEASUREMENT_FIELDS}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["category"].queryset = ProductCategory.objects.filter(organization=self.workspace.organization).filter(
            Q(is_active=True) | Q(pk=self.instance.category_id)
        ).order_by("code")
        for field in UNIT_FIELDS:
            queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=getattr(self.instance, f"{field}_id"))).select_related("category")
            if field in ("weight_uom", "dimension_uom"):
                dimension = "MASS" if field == "weight_uom" else "LENGTH"
                queryset = queryset.filter(category__dimension_code=dimension)
            self.fields[field].queryset = queryset.order_by("name", "code")

    def clean(self):
        return normalize_product_values(super().clean())

    @property
    def sections(self):
        return tuple((title, tuple(self[name] for name in fields)) for title, fields in (
            ("Thông tin chung", ("category", "code", "name", "item_type")),
            ("Đơn vị tính", ("base_uom", "purchase_uom", "production_uom")),
            ("Thuế", ("tax_class_code",)),
            ("Trọng lượng", ("net_weight", "gross_weight", "weight_uom")),
            ("Kích thước", ("length", "width", "height", "dimension_uom")),
            ("Quản lý", ("is_stock_item", "is_active")),
        ))


class ProductForm(ReferenceDataForm):
    validate_values = staticmethod(validate_product)
    normalize_values = staticmethod(normalize_product_values)
    category = ReferenceChoiceField(queryset=ProductCategory.objects.none(), required=False, label="Nhóm sản phẩm")
    costing_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị tính giá thành", help_text="Đơn vị cơ sở dùng để tính giá thành của sản phẩm.", error_messages={"required": "Vui lòng chọn đơn vị tính giá thành."})
    output_item = ReferenceChoiceField(queryset=Item.objects.none(), required=False, label="Vật tư / Hàng hóa đầu ra",
        help_text="Liên kết danh mục vật tư / hàng hóa đầu ra nếu đã có. Sản phẩm vẫn được quản lý riêng.")

    class Meta:
        model = Product
        fields = PRODUCT_FIELDS
        labels = {"code": "Mã sản phẩm", "name": "Tên sản phẩm", "description": "Mô tả", "tax_class_code": "Mã nhóm thuế", "is_active": "Đang hoạt động"}
        error_messages = {"code": {"required": "Vui lòng nhập mã sản phẩm."}, "name": {"required": "Vui lòng nhập tên sản phẩm."}}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"code": "Mã được chuẩn hóa thành chữ hoa.", "costing_uom": "Đơn vị cơ sở dùng để tính giá thành của sản phẩm."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["category"].queryset = ProductCategory.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.category_id)).order_by("code")
        self.fields["output_item"].queryset = Item.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.output_item_id)).order_by("code")
        self.fields["costing_uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=self.instance.costing_uom_id)).order_by("name", "code")

    @property
    def sections(self):
        return tuple((title, tuple(self[field] for field in fields)) for title, fields in (
            ("Thông tin chung", ("category", "code", "name", "description")),
            ("Đơn vị tính", ("costing_uom",)),
            ("Liên kết và thuế", ("output_item", "tax_class_code")),
            ("Quản lý", ("is_active",)),
        ))


class SkuForm(ReferenceDataForm):
    validate_values = staticmethod(validate_sku)
    normalize_values = staticmethod(normalize_product_values)
    product = ReferenceChoiceField(queryset=Product.objects.none(), label="Sản phẩm", error_messages={"required": "Vui lòng chọn sản phẩm."})
    sales_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị bán", error_messages={"required": "Vui lòng chọn đơn vị bán."})
    net_quantity_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị lượng tịnh", error_messages={"required": "Vui lòng chọn đơn vị lượng tịnh."})
    sell_item = ReferenceChoiceField(queryset=Item.objects.none(), required=False, label="Vật tư / Hàng hóa bán",
        help_text="Liên kết hàng hóa bán nếu đã có trong danh mục vật tư / hàng hóa.")

    class Meta:
        model = Sku
        fields = SKU_FIELDS
        labels = {"code": "Mã SKU", "name": "Tên SKU", "barcode": "Mã vạch", "net_quantity": "Lượng tịnh", "is_active": "Đang hoạt động"}
        error_messages = {
            "code": {"required": "Vui lòng nhập mã SKU."}, "name": {"required": "Vui lòng nhập tên SKU."},
            "net_quantity": {"required": "Vui lòng nhập lượng tịnh."},
        }
        widgets = {"net_quantity": CompactNumberInput(attrs={"min": "0.00000001", "step": "any"})}
        help_texts = {
            "code": "Mã được chuẩn hóa thành chữ hoa.", "barcode": "Không bắt buộc; mã vạch phải duy nhất trong công ty.",
            "net_quantity": "Lượng tịnh trên một đơn vị bán: khối lượng, thể tích hoặc số lượng theo đơn vị đã chọn. Phải lớn hơn 0.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["product"].queryset = Product.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.product_id)).order_by("code")
        self.fields["sell_item"].queryset = Item.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.sell_item_id)).order_by("code")
        for field in SKU_UNIT_FIELDS:
            self.fields[field].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=getattr(self.instance, f"{field}_id"))).order_by("name", "code")

    @property
    def sections(self):
        return tuple((title, tuple(self[field] for field in fields)) for title, fields in (
            ("Thông tin chung", ("product", "code", "name", "barcode")),
            ("Quy cách", ("sales_uom", "net_quantity", "net_quantity_uom")),
            ("Liên kết hàng hóa", ("sell_item",)),
            ("Quản lý", ("is_active",)),
        ))
