from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal

from apps.core.models import CostElement, CostElementGroup, Currency, Item, Supplier, SupplierPrice, Uom, UomCategory, UomConversion
from .constants import ACCOUNTING_SCOPES, COST_SCOPES, CURRENCY_FIELDS, EDITABLE_FIELDS, ROUNDING_MODES, SOURCE_MODES, UOM_CATEGORY_FIELDS, UOM_CONVERSION_FIELDS, UOM_FIELDS, VALUE_TYPES
from .validators import (
    normalize_cost_element, normalize_reference_values, validate_cost_element,
    validate_currency, validate_uom_category, validate_uom, validate_uom_conversion,
    normalize_supplier_values, validate_supplier, validate_supplier_price,
)
from .constants import SUPPLIER_FIELDS, SUPPLIER_PRICE_FIELDS

FIELD_CLASSES = "w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 disabled:bg-slate-100"


class CompactNumberInput(forms.NumberInput):
    """Trim insignificant zeroes on initial values, preserve submitted input."""
    def format_value(self, value):
        if isinstance(value, Decimal):
            text = format(value, "f")
            return text.rstrip("0").rstrip(".") if "." in text else text
        return super().format_value(value)


class ReferenceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, instance):
        suffix = " (ngừng hoạt động)" if not instance.is_active else ""
        return f"{instance.code} — {instance.name}{suffix}"


class UnitChoiceField(ReferenceChoiceField):
    def label_from_instance(self, instance):
        suffix = " (ngừng hoạt động)" if not instance.is_active else ""
        return f"{instance.name} ({instance.symbol}){suffix}"


class CostElementForm(forms.ModelForm):
    group = ReferenceChoiceField(queryset=CostElementGroup.objects.none(), required=False, label="Nhóm chi phí")
    currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), required=False, label="Tiền tệ")
    default_uom = ReferenceChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị tính mặc định")
    value_type = forms.ChoiceField(choices=VALUE_TYPES, label="Loại giá trị")
    default_source_mode = forms.ChoiceField(choices=SOURCE_MODES, label="Nguồn dữ liệu")
    accounting_scope = forms.ChoiceField(choices=ACCOUNTING_SCOPES, label="Phạm vi kế toán")
    cost_scope = forms.ChoiceField(choices=COST_SCOPES, label="Phạm vi chi phí")
    rounding_mode = forms.ChoiceField(choices=ROUNDING_MODES, label="Phương pháp làm tròn")
    rounding_scale = forms.IntegerField(min_value=0, max_value=12, initial=6, label="Số chữ số làm tròn", help_text="Từ 0 đến 12 chữ số thập phân.")

    class Meta:
        model = CostElement
        fields = EDITABLE_FIELDS
        labels = {
            "code": "Mã", "name": "Tên", "description": "Mô tả", "dimension_code": "Đại lượng",
            "is_sensitive": "Dữ liệu nhạy cảm", "is_active": "Đang hoạt động",
        }
        help_texts = {
            "code": "Mã được chuẩn hóa thành chữ hoa, không có khoảng trắng ở đầu/cuối.",
            "is_sensitive": "Đánh dấu dữ liệu cần thận trọng khi sử dụng hoặc chia sẻ.",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, organization, permissions, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.instance.organization = organization
        self.fields["group"].queryset = CostElementGroup.objects.filter(organization=organization).filter(Q(is_active=True) | Q(pk=self.instance.group_id)).order_by("display_order", "code")
        self.fields["currency_code"].queryset = Currency.objects.filter(Q(is_active=True) | Q(pk=self.instance.currency_code_id)).order_by("code")
        self.fields["default_uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=self.instance.default_uom_id)).select_related("category").order_by("code")
        self.fields["is_sensitive"].disabled = not permissions.can_manage_sensitive_cost_element
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "h-4 w-4 rounded border-slate-300 accent-brand-600" if isinstance(field.widget, forms.CheckboxInput) else FIELD_CLASSES
            field.widget.attrs["aria-describedby"] = f"{self[name].auto_id}_help {self[name].auto_id}_errors"
        if self.is_bound:
            self.mark_errors()

    def mark_errors(self):
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["aria-invalid"] = "true"

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        data = normalize_cost_element(data)
        try:
            validate_cost_element(data=data, organization=self.organization, instance=self.instance)
        except ValidationError as error:
            for name, errors in error.message_dict.items():
                self.add_error(name, errors)
        return data

    @property
    def sections(self):
        return (
            ("Thông tin chung", tuple(self[name] for name in ("group", "code", "name", "description"))),
            ("Cấu hình giá trị", tuple(self[name] for name in ("value_type", "dimension_code", "default_source_mode", "currency_code", "default_uom", "rounding_scale", "rounding_mode"))),
            ("Phạm vi", tuple(self[name] for name in ("accounting_scope", "cost_scope"))),
            ("Bảo mật & trạng thái", tuple(self[name] for name in ("is_sensitive", "is_active"))),
        )


class ReferenceDataForm(forms.ModelForm):
    """Shared field presentation and validation plumbing for reference forms."""
    uppercase_fields = ("code",)
    normalize_values = staticmethod(normalize_reference_values)

    def __init__(self, *args, workspace, **kwargs):
        self.workspace = workspace
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "h-4 w-4 rounded border-slate-300 accent-brand-600" if isinstance(field.widget, forms.CheckboxInput) else FIELD_CLASSES
            field.widget.attrs["aria-describedby"] = f"{self[name].auto_id}_help {self[name].auto_id}_errors"

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        data = self.normalize_values(data, uppercase=self.uppercase_fields)
        try:
            self.validate_values(data=data, organization=self.workspace.organization, instance=self.instance)
        except ValidationError as error:
            for name, errors in error.message_dict.items():
                self.add_error(name, errors)
        return data

    def mark_errors(self):
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["aria-invalid"] = "true"

    @property
    def sections(self):
        return (("Thông tin danh mục", tuple(self)),)


class CurrencyForm(ReferenceDataForm):
    validate_values = staticmethod(validate_currency)
    decimal_places = forms.IntegerField(min_value=0, max_value=8, initial=2, label="Số chữ số thập phân", help_text="Từ 0 đến 8.")

    class Meta:
        model = Currency
        fields = CURRENCY_FIELDS
        labels = {"code": "Mã tiền tệ", "name": "Tên", "is_active": "Đang hoạt động"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.uppercase_fields = ()  # Preserve existing primary keys, including legacy casing.
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "Mã tiền tệ là định danh cố định; không thay đổi khi chỉnh sửa."


class UomCategoryForm(ReferenceDataForm):
    validate_values = staticmethod(validate_uom_category)
    uppercase_fields = ("code", "dimension_code")

    class Meta:
        model = UomCategory
        fields = UOM_CATEGORY_FIELDS
        labels = {"code": "Mã nhóm", "name": "Tên", "dimension_code": "Mã đại lượng", "description": "Mô tả", "is_active": "Đang hoạt động"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class UomForm(ReferenceDataForm):
    validate_values = staticmethod(validate_uom)
    category = ReferenceChoiceField(queryset=UomCategory.objects.none(), label="Nhóm đơn vị tính")
    precision = forms.IntegerField(min_value=0, max_value=12, initial=6, label="Độ chính xác", help_text="Từ 0 đến 12 chữ số thập phân.")

    class Meta:
        model = Uom
        fields = UOM_FIELDS
        labels = {"code": "Mã đơn vị", "name": "Tên", "symbol": "Ký hiệu", "is_base": "Đơn vị cơ sở", "is_active": "Đang hoạt động"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = UomCategory.objects.filter(Q(is_active=True) | Q(pk=self.instance.category_id)).order_by("code")


class UomConversionForm(ReferenceDataForm):
    validate_values = staticmethod(validate_uom_conversion)
    uppercase_fields = ()
    from_uom = ReferenceChoiceField(queryset=Uom.objects.none(), label="Đơn vị nguồn")
    to_uom = ReferenceChoiceField(queryset=Uom.objects.none(), label="Đơn vị đích")
    item = ReferenceChoiceField(queryset=Item.objects.none(), required=False, label="Vật tư / Hàng hóa", help_text="Để trống cho quy đổi chung cùng nhóm đơn vị tính. Chỉ chọn vật tư / hàng hóa của công ty.")
    effective_from = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Hiệu lực từ ngày")
    effective_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Hiệu lực đến ngày")

    class Meta:
        model = UomConversion
        fields = UOM_CONVERSION_FIELDS
        labels = {"factor": "Hệ số quy đổi", "source_reference": "Nguồn tham chiếu"}
        help_texts = {"factor": "Giá trị đích = giá trị nguồn × hệ số. Tối đa 12 chữ số thập phân."}
        widgets = {"source_reference": forms.Textarea(attrs={"rows": 3}), "factor": CompactNumberInput(attrs={"step": "any"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        for name in ("from_uom", "to_uom"):
            self.fields[name].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=getattr(self.instance, f"{name}_id"))).select_related("category").order_by("code")
        self.fields["item"].queryset = Item.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.item_id)).order_by("code")


class SupplierForm(ReferenceDataForm):
    validate_values = staticmethod(validate_supplier)
    normalize_values = staticmethod(normalize_supplier_values)
    default_currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), required=False, label="Tiền tệ mặc định")

    class Meta:
        model = Supplier
        fields = SUPPLIER_FIELDS
        labels = {"code": "Mã nhà cung cấp", "name": "Tên nhà cung cấp", "tax_code": "Mã số thuế", "payment_terms": "Điều khoản thanh toán", "is_active": "Đang hoạt động"}
        error_messages = {"code": {"required": "Vui lòng nhập mã nhà cung cấp."}, "name": {"required": "Vui lòng nhập tên nhà cung cấp."}}
        widgets = {"payment_terms": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"code": "Mã được chuẩn hóa thành chữ hoa."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["default_currency_code"].queryset = Currency.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.default_currency_code_id)
        ).order_by("code")

    @property
    def sections(self):
        return tuple((title, tuple(self[name] for name in fields)) for title, fields in (
            ("Thông tin chung", ("code", "name", "tax_code")),
            ("Thông tin giao dịch", ("default_currency_code", "payment_terms")),
            ("Quản lý", ("is_active",)),
        ))


class SupplierPriceForm(ReferenceDataForm):
    validate_values = staticmethod(validate_supplier_price)
    normalize_values = staticmethod(normalize_supplier_values)
    uppercase_fields = ()
    supplier = ReferenceChoiceField(queryset=Supplier.objects.none(), label="Nhà cung cấp", error_messages={"required": "Vui lòng chọn nhà cung cấp."})
    item = ReferenceChoiceField(queryset=Item.objects.none(), label="Vật tư / Hàng hóa", error_messages={"required": "Vui lòng chọn vật tư / hàng hóa."})
    price_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị tính", error_messages={"required": "Vui lòng chọn đơn vị tính."}, help_text="Lưu đơn vị tính trên báo giá; không tự quy đổi sang đơn vị của vật tư / hàng hóa.")
    currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), label="Tiền tệ", error_messages={"required": "Vui lòng chọn tiền tệ."})
    effective_from = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Hiệu lực từ ngày", error_messages={"required": "Vui lòng nhập ngày bắt đầu hiệu lực."})
    effective_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), label="Hiệu lực đến ngày", help_text="Để trống nếu không giới hạn. Ngày kết thúc phải sau ngày bắt đầu.")

    class Meta:
        model = SupplierPrice
        fields = SUPPLIER_PRICE_FIELDS
        labels = {
            "unit_price": "Đơn giá", "min_qty": "Số lượng tối thiểu", "tax_inclusive": "Đơn giá đã gồm thuế",
            "tax_rate": "Tỷ lệ thuế", "tax_recoverable_ratio": "Tỷ lệ thuế được khấu trừ",
            "source_type": "Nguồn dữ liệu", "source_reference": "Tham chiếu / Số báo giá",
        }
        error_messages = {"unit_price": {"required": "Vui lòng nhập đơn giá."}}
        help_texts = {
            "min_qty": "Số lượng theo đơn vị tính của báo giá. Giá trị tối thiểu là 0.",
            "tax_rate": "Nhập tỷ lệ từ 0 đến 1; ví dụ 0.1 tương ứng 10% (dùng dấu chấm khi nhập).",
            "tax_recoverable_ratio": "Nhập tỷ lệ từ 0 đến 1; 1 tương ứng khấu trừ toàn bộ thuế.",
        }
        widgets = {
            **{field: CompactNumberInput(attrs={"min": "0", "step": "any"}) for field in ("unit_price", "min_qty")},
            **{field: CompactNumberInput(attrs={"min": "0", "max": "1", "step": "any"}) for field in ("tax_rate", "tax_recoverable_ratio")},
            "source_reference": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        for name, model in (("supplier", Supplier), ("item", Item), ("price_uom", Uom), ("currency_code", Currency)):
            queryset = model.objects.all()
            if model in (Supplier, Item):
                queryset = queryset.filter(organization=self.workspace.organization)
            self.fields[name].queryset = queryset.filter(
                Q(is_active=True) | Q(pk=getattr(self.instance, f"{name}_id"))
            ).order_by("name" if name == "price_uom" else "code", "pk")

    @property
    def sections(self):
        return tuple((title, tuple(self[name] for name in fields)) for title, fields in (
            ("Thông tin giá", ("supplier", "item", "unit_price", "currency_code", "price_uom")),
            ("Điều kiện áp dụng", ("min_qty",)),
            ("Thuế", ("tax_inclusive", "tax_rate", "tax_recoverable_ratio")),
            ("Thời gian hiệu lực", ("effective_from", "effective_to")),
            ("Thông tin tham chiếu", ("source_type", "source_reference")),
        ))
