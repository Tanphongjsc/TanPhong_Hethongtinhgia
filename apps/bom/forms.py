from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.core.models import Item, Product, Recipe, RecipeLine, RecipeVersion, Uom
from apps.master_data.forms import CompactNumberInput, ReferenceChoiceField, ReferenceDataForm, UnitChoiceField
from .constants import IMMUTABLE_STATUSES, LINE_FIELDS, RECIPE_FIELDS, VERSION_FIELDS
from .validators import normalize_values, validate_conversions, validate_line, validate_recipe, validate_version


class PercentageField(forms.DecimalField):
    """Display/input percent, persist the exact Decimal ratio expected by DB."""
    def __init__(self, **kwargs):
        super().__init__(max_digits=9, decimal_places=6, min_value=0, max_value=100,
            widget=CompactNumberInput(attrs={"min": "0", "max": "100", "step": "any"}), **kwargs)

    def clean(self, value):
        value = super().clean(value)
        return value / Decimal(100) if value is not None else None

    def prepare_value(self, value):
        return Decimal(value) * Decimal(100) if isinstance(value, (int, Decimal)) else value


class RecipeForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    validate_values = staticmethod(validate_recipe)
    product = ReferenceChoiceField(queryset=Product.objects.none(), label="Sản phẩm", error_messages={"required": "Vui lòng chọn sản phẩm."})

    class Meta:
        model = Recipe
        fields = RECIPE_FIELDS
        labels = {"code": "Mã định mức", "name": "Tên định mức", "description": "Mô tả", "is_active": "Đang hoạt động"}
        error_messages = {"code": {"required": "Vui lòng nhập mã định mức."}, "name": {"required": "Vui lòng nhập tên định mức."}}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["product"].queryset = Product.objects.filter(organization=self.workspace.organization).filter(
            Q(is_active=True) | Q(pk=self.instance.product_id)).order_by("code")
        if self.instance.pk and self.instance.recipeversion_set.filter(status__in=IMMUTABLE_STATUSES).exists():
            self.fields["product"].disabled = True
            self.fields["product"].help_text = "Sản phẩm được giữ cố định vì định mức đã có phiên bản được chốt."

    @property
    def sections(self):
        return (("Thông tin chung", tuple(self[name] for name in ("product", "code", "name", "description"))),
            ("Quản lý", (self["is_active"],)))


class RecipeVersionForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    uppercase_fields = ()
    output_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị tính đầu ra", error_messages={"required": "Vui lòng chọn đơn vị tính đầu ra."})
    yield_rate = PercentageField(label="Tỷ lệ thu hồi (%)", initial=Decimal("1"), help_text="Lớn hơn 0 và không vượt quá 100%. Không tự điều chỉnh số lượng thành phần.")
    effective_from = forms.DateField(required=False, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    class Meta:
        model = RecipeVersion
        fields = VERSION_FIELDS
        labels = {"output_qty": "Sản lượng chuẩn", "change_reason": "Lý do thay đổi"}
        widgets = {"output_qty": CompactNumberInput(attrs={"min": "0", "step": "any"}), "change_reason": forms.Textarea(attrs={"rows": 3})}
        error_messages = {"output_qty": {"required": "Vui lòng nhập sản lượng chuẩn."}}

    def __init__(self, *args, source=None, **kwargs):
        self.source = source
        if source and "instance" not in kwargs:
            kwargs.setdefault("initial", {field: getattr(source, field) for field in VERSION_FIELDS})
        super().__init__(*args, **kwargs)
        reference = source or self.instance
        self.fields["output_uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=reference.output_uom_id)).order_by("code")

    def validate_values(self, *, data, organization, instance):
        validate_version(data=data, organization=organization, instance=self.source or instance)

    @property
    def sections(self):
        return (("Đầu ra sản xuất", tuple(self[name] for name in ("output_qty", "output_uom", "yield_rate"))),
            ("Hiệu lực và thay đổi", tuple(self[name] for name in ("effective_from", "effective_to", "change_reason"))))


class RecipeLineForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    validate_values = staticmethod(validate_line)
    uppercase_fields = ()
    component_item = ReferenceChoiceField(queryset=Item.objects.none(), label="Vật tư / Hàng hóa", error_messages={"required": "Vui lòng chọn vật tư / hàng hóa."})
    uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị tính", error_messages={"required": "Vui lòng chọn đơn vị tính."})
    scrap_rate = PercentageField(label="Tỷ lệ hao hụt (%)", initial=Decimal("0"), help_text="Từ 0 đến dưới 100%. Hao hụt được lưu riêng với số lượng.")

    class Meta:
        model = RecipeLine
        fields = LINE_FIELDS
        labels = {"qty": "Số lượng", "operation_code": "Mã công đoạn", "substitute_group": "Nhóm thay thế", "is_optional": "Thành phần tùy chọn", "display_order": "Thứ tự", "notes": "Ghi chú"}
        widgets = {"qty": CompactNumberInput(attrs={"min": "0", "step": "any"}), "notes": forms.Textarea(attrs={"rows": 2})}
        error_messages = {"qty": {"required": "Vui lòng nhập số lượng."}}

    def __init__(self, *args, version, **kwargs):
        self.version = version
        super().__init__(*args, **kwargs)
        self.instance.recipe_version = version
        self.fields["component_item"].queryset = Item.objects.filter(organization=self.workspace.organization).filter(
            Q(is_active=True) | Q(pk=self.instance.component_item_id)).order_by("code")
        self.fields["uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=self.instance.uom_id)).order_by("code")

    def clean(self):
        data = super().clean()
        if not self.errors:
            try:
                validate_conversions(lines=[(data["component_item"], data["uom"])], organization=self.workspace.organization,
                    effective_from=self.version.effective_from)
            except ValidationError as error:
                self.add_error("uom", error)
        return data

    @property
    def sections(self):
        return (("Thành phần định mức", tuple(self[name] for name in ("component_item", "qty", "uom", "scrap_rate"))),
            ("Thông tin bổ sung", tuple(self[name] for name in ("operation_code", "substitute_group", "is_optional", "display_order", "notes"))))
