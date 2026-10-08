from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from apps.core.models import Item, PackagingConfig, PackagingConfigVersion, PackagingLine, Product, Sku, SkuPackagingAssignment, Uom
from apps.master_data.forms import CompactNumberInput, ReferenceChoiceField, ReferenceDataForm, UnitChoiceField
from apps.master_data.presentation import display_label
from .constants import IMMUTABLE_STATUSES
from .packaging_constants import ASSIGNMENT_FIELDS, CONFIG_FIELDS, LEVELS, LINE_FIELDS, MEASUREMENTS, VERSION_FIELDS
from .packaging_validators import normalize_values, validate_assignment, validate_config, validate_conversions, validate_line, validate_version


class PackagingConfigForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    validate_values = staticmethod(validate_config)
    product = ReferenceChoiceField(queryset=Product.objects.none(), label="Sản phẩm", error_messages={"required": "Vui lòng chọn sản phẩm."})

    class Meta:
        model = PackagingConfig
        fields = CONFIG_FIELDS
        labels = {"code": "Mã cấu hình", "name": "Tên cấu hình", "description": "Mô tả", "is_active": "Đang hoạt động"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        error_messages = {"code": {"required": "Vui lòng nhập mã cấu hình bao bì."}, "name": {"required": "Vui lòng nhập tên cấu hình bao bì."}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["product"].queryset = Product.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.product_id)).order_by("code")
        if self.instance.pk and (self.instance.packagingconfigversion_set.filter(status__in=IMMUTABLE_STATUSES).exists() or self.instance.skupackagingassignment_set.exists()):
            self.fields["product"].disabled = True
            self.fields["product"].help_text = "Sản phẩm được giữ cố định vì cấu hình đã được gán SKU hoặc có phiên bản được chốt."

    @property
    def sections(self):
        return (("Thông tin chung", tuple(self[name] for name in ("product", "code", "name", "description"))), ("Quản lý", (self["is_active"],)))


class PackagingVersionForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    uppercase_fields = ()
    weight_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị trọng lượng")
    dimension_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị kích thước")
    effective_from = forms.DateField(required=False, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    class Meta:
        model = PackagingConfigVersion
        fields = VERSION_FIELDS
        labels = {"gross_weight": "Khối lượng tổng", "length": "Chiều dài", "width": "Chiều rộng", "height": "Chiều cao", "change_reason": "Lý do thay đổi"}
        widgets = {**{field: CompactNumberInput(attrs={"min": "0", "step": "any"}) for field in MEASUREMENTS}, "change_reason": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, source=None, **kwargs):
        self.source = source
        if source and "instance" not in kwargs:
            kwargs.setdefault("initial", {field: getattr(source, field) for field in VERSION_FIELDS})
        super().__init__(*args, **kwargs)
        reference = source or self.instance
        for field, dimension in (("weight_uom", "MASS"), ("dimension_uom", "LENGTH")):
            self.fields[field].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=getattr(reference, f"{field}_id"))).filter(category__dimension_code=dimension).select_related("category").order_by("name", "code")

    def validate_values(self, *, data, organization, instance):
        validate_version(data=data, organization=organization, instance=self.source or instance)

    @property
    def sections(self):
        return (("Quy cách bao bì", tuple(self[name] for name in ("gross_weight", "weight_uom", "length", "width", "height", "dimension_uom"))),
            ("Hiệu lực và thay đổi", tuple(self[name] for name in ("effective_from", "effective_to", "change_reason"))))


class PackagingItemChoiceField(ReferenceChoiceField):
    def label_from_instance(self, instance):
        return f"{super().label_from_instance(instance)} · {display_label(instance.item_type)}"


class PackagingLineForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    validate_values = staticmethod(validate_line)
    uppercase_fields = ()
    packaging_item = PackagingItemChoiceField(queryset=Item.objects.none(), label="Vật tư bao bì", error_messages={"required": "Vui lòng chọn vật tư bao bì."}, help_text="Ưu tiên vật tư loại Bao bì; có thể chọn thành phần khác trong danh mục đang hoạt động.")
    uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị tính", error_messages={"required": "Vui lòng chọn đơn vị tính."})
    level_code = forms.ChoiceField(choices=LEVELS, label="Cấp đóng gói")

    class Meta:
        model = PackagingLine
        fields = LINE_FIELDS
        labels = {"qty": "Số lượng", "units_per_parent": "Số đơn vị trong cấp cha", "parent_level_code": "Cấp cha", "market_code": "Mã thị trường", "artwork_code": "Mã mẫu thiết kế", "display_order": "Thứ tự", "notes": "Ghi chú"}
        help_texts = {"qty": "Chấp nhận số lẻ, tối đa 8 chữ số thập phân. Nhập dấu chấm cho phần thập phân.", "parent_level_code": "Để trống nếu không có cấp cha. Cấu trúc được lưu theo cấp đóng gói.", "units_per_parent": "Để trống nếu chưa xác định. Không tự quy đổi số lượng giữa các cấp."}
        widgets = {"parent_level_code": forms.Select(choices=(("", "Không có cấp cha"), *LEVELS)), "qty": CompactNumberInput(attrs={"min": "0", "step": "any"}), "units_per_parent": CompactNumberInput(attrs={"min": "0", "step": "any"}), "notes": forms.Textarea(attrs={"rows": 2})}
        error_messages = {"qty": {"required": "Vui lòng nhập số lượng."}}

    def __init__(self, *args, version, **kwargs):
        self.version = version
        super().__init__(*args, **kwargs)
        self.instance.packaging_config_version = version
        # parent_level_code is free text in DB. Offer known levels, but preserve
        # legacy/custom values and failed POST input without inventing a CHECK.
        parent = self.data.get(self.add_prefix("parent_level_code")) if self.is_bound else self.initial.get("parent_level_code")
        choices = tuple(self.fields["parent_level_code"].widget.choices)
        if parent and parent not in dict(choices):
            self.fields["parent_level_code"].widget.choices = (*choices, (parent, display_label(parent.strip())))
        self.fields["packaging_item"].queryset = Item.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.packaging_item_id)).annotate(
            packaging_priority=Case(When(item_type="PACKAGING", then=Value(0)), default=Value(1), output_field=IntegerField())).order_by("packaging_priority", "code")
        self.fields["uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=self.instance.uom_id)).order_by("name", "code")

    def clean(self):
        data = super().clean()
        if not self.errors:
            try:
                validate_conversions(lines=[(data["packaging_item"], data["uom"])], organization=self.workspace.organization, effective_from=self.version.effective_from)
            except ValidationError as error:
                self.add_error("uom", error)
        return data

    @property
    def sections(self):
        return (("Thành phần bao bì", tuple(self[name] for name in ("packaging_item", "qty", "uom", "level_code"))),
            ("Cấu trúc đóng gói", tuple(self[name] for name in ("parent_level_code", "units_per_parent"))),
            ("Thông tin bổ sung", tuple(self[name] for name in ("market_code", "artwork_code", "display_order", "notes"))))


class PackagingAssignmentForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    validate_values = staticmethod(validate_assignment)
    uppercase_fields = ()
    sku = ReferenceChoiceField(queryset=Sku.objects.none(), label="SKU", error_messages={"required": "Vui lòng chọn SKU."})
    effective_from = forms.DateField(initial=timezone.localdate, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    class Meta:
        model = SkuPackagingAssignment
        fields = ASSIGNMENT_FIELDS
        labels = {"is_primary": "Cấu hình chính"}

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.packaging_config = config
        self.fields["sku"].queryset = Sku.objects.filter(organization=self.workspace.organization, product=config.product, product__organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.sku_id)).select_related("product").order_by("code")

    @property
    def sections(self):
        return (("SKU sử dụng cấu hình", (self["sku"], self["is_primary"])), ("Hiệu lực áp dụng", (self["effective_from"], self["effective_to"])))
