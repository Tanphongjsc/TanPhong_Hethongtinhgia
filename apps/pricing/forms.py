from decimal import Decimal
from django import forms
from django.db.models import Q
from django.utils import timezone
from apps.core.models import Channel, ChannelFeeRule, TaxRule, FxRate, Currency, ProductCategory, Sku
from apps.master_data.forms import ReferenceChoiceField, ReferenceDataForm, CompactNumberInput, FIELD_CLASSES
from .constants import CHANNEL_TYPES, LIFECYCLE, FIELDS
from .validators import normalize_values, validate_values


def percentage(label, *, required=False):
    return forms.DecimalField(label=label, required=required, min_value=0, max_value=100, decimal_places=6, max_digits=9,
        widget=CompactNumberInput(attrs={"step": "any"}), help_text="Nhập theo %. Ví dụ 8 là 8%; dữ liệu lưu là 0,08.")


def tax_inclusion(label):
    return forms.TypedChoiceField(label=label, choices=(("", "Chọn cách thể hiện thuế"), ("True", "Giá đã bao gồm thuế"), ("False", "Giá chưa bao gồm thuế")), coerce=lambda value: value == "True", error_messages={"required": "Vui lòng chọn giá đã hoặc chưa bao gồm thuế."})


class PricingForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    uppercase_fields = ()
    percentage_fields = ()
    groups = ()

    def validate_values(self, **kwargs):
        validate_values(resource=self.resource, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        if not self.instance.pk and "status" in self.fields: self.initial["status"] = "DRAFT"
        for name in self.percentage_fields:
            value = getattr(self.instance, name, None)
            if value is not None: self.initial[name] = value * Decimal(100)
        for name, field in self.fields.items():
            if isinstance(field, forms.DecimalField): field.widget = CompactNumberInput(attrs=field.widget.attrs | {"step": "any"})
            if isinstance(field, forms.ModelChoiceField):
                current = getattr(self.instance, name + "_id")
                query = field.queryset.model.objects.all()
                if field.queryset.model in (Channel, ProductCategory, Sku): query = query.filter(organization=self.workspace.organization)
                field.queryset = query.filter(Q(is_active=True) | Q(pk=current)).order_by("code", "pk")
                if name == "sku": field.queryset = field.queryset.select_related("product")
            if name in ("fee_type", "fee_base", "tax_type", "tax_base", "rate_type", "seller_type", "transaction_type"):
                field.help_text = "Mã nghiệp vụ do công ty quy định."
        if self.instance.pk and self.resource != "channel" and self.instance.status != "DRAFT":
            self.fields["status"].choices = ((self.instance.status, "Bản đã chốt · chỉ đọc"),)
            for field in self.fields.values(): field.disabled = True

    def clean(self):
        # Convert only at the UI boundary. Services accept fractional Decimals.
        data = forms.ModelForm.clean(self)
        for name in self.percentage_fields:
            if data.get(name) is not None: data[name] /= Decimal(100)
        if self.instance.pk and self.resource != "channel" and self.instance.status != "DRAFT":
            self.add_error(None, "Bản đã chốt chỉ được xem. Hãy thêm bản mới cho kỳ áp dụng mới.")
            return data
        return super().clean()

    @property
    def sections(self):
        return tuple((title, tuple(self[name] for name in fields)) for title, fields in self.groups)


class ChannelForm(PricingForm):
    resource = "channel"
    channel_type = forms.ChoiceField(label="Loại kênh bán", choices=(("", "Chọn loại kênh bán"), *CHANNEL_TYPES))
    default_currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), required=False, label="Tiền tệ mặc định")
    groups = (("Thông tin kênh bán", ("code", "name", "channel_type")), ("Thông tin giao dịch", ("platform_code", "market_code", "seller_type", "default_currency_code")), ("Quản lý", ("is_active",)))
    class Meta:
        model = Channel
        fields = FIELDS["channel"]
        labels = {"code": "Mã kênh bán", "name": "Tên kênh bán", "platform_code": "Mã nền tảng", "market_code": "Mã thị trường", "seller_type": "Mã loại người bán", "is_active": "Đang hoạt động"}


class DatedRuleForm(PricingForm):
    rate = percentage("Tỷ lệ (%)")
    currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), required=False, label="Tiền tệ")
    priority = forms.IntegerField(label="Mức ưu tiên", initial=100, min_value=-2147483648, max_value=2147483647, help_text="Số nguyên theo cấu hình; chưa quyết định thứ tự tính phí/thuế.")
    effective_from = forms.DateField(label="Hiệu lực từ ngày", initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    effective_to = forms.DateField(label="Hiệu lực đến ngày", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), help_text="Ngày kết thúc phải sau ngày bắt đầu; để trống nếu không giới hạn.")
    status = forms.ChoiceField(label="Trạng thái", choices=LIFECYCLE, initial="DRAFT", help_text="Chọn Đang hiệu lực để sử dụng trực tiếp sau khi kiểm tra hợp lệ; không có bước phê duyệt.")


class ChannelFeeRuleForm(DatedRuleForm):
    resource = "channel_fee_rule"
    channel = ReferenceChoiceField(queryset=Channel.objects.none(), label="Kênh bán")
    product_category = ReferenceChoiceField(queryset=ProductCategory.objects.none(), required=False, label="Nhóm sản phẩm", help_text="Để trống để áp dụng mọi nhóm.")
    sku = ReferenceChoiceField(queryset=Sku.objects.none(), required=False, label="SKU", help_text="Để trống để áp dụng mọi SKU trong phạm vi đã chọn.")
    refundable_ratio = percentage("Tỷ lệ được hoàn (%)", required=True)
    tax_inclusive = tax_inclusion("Thuế trong phí")
    percentage_fields = ("rate", "refundable_ratio")
    groups = (("Thông tin quy tắc", ("channel", "fee_type", "fee_base")), ("Cách tính phí", ("rate", "fixed_amount", "currency_code", "floor_amount", "cap_amount", "refundable_ratio", "tax_inclusive", "priority")), ("Phạm vi áp dụng", ("product_category", "sku")), ("Hiệu lực và tham chiếu", ("effective_from", "effective_to", "source_reference", "status")))
    class Meta:
        model = ChannelFeeRule
        fields = FIELDS["channel_fee_rule"]
        labels = {"fee_type": "Mã loại phí", "fee_base": "Mã cơ sở tính phí", "fixed_amount": "Số tiền cố định", "floor_amount": "Giá trị sàn", "cap_amount": "Giá trị trần", "source_reference": "Nguồn tham chiếu"}
        widgets = {"source_reference": forms.Textarea(attrs={"rows": 3})}


class TaxRuleForm(DatedRuleForm):
    resource = "tax_rule"
    rate = percentage("Thuế suất (%)")
    recoverable_ratio = percentage("Tỷ lệ được khấu trừ (%)", required=True)
    inclusive = tax_inclusion("Thuế trong giá")
    percentage_fields = ("rate", "recoverable_ratio")
    groups = (("Thông tin thuế", ("jurisdiction_code", "tax_type", "tax_base")), ("Cách tính thuế", ("rate", "fixed_amount", "currency_code", "recoverable_ratio", "inclusive", "priority")), ("Phạm vi áp dụng", ("tax_class_code", "seller_type", "transaction_type")), ("Hiệu lực và tham chiếu", ("effective_from", "effective_to", "source_reference", "status")))
    class Meta:
        model = TaxRule
        fields = FIELDS["tax_rule"]
        labels = {"jurisdiction_code": "Mã khu vực áp dụng", "tax_type": "Mã loại thuế", "tax_base": "Mã cơ sở tính thuế", "tax_class_code": "Mã nhóm thuế", "seller_type": "Mã loại người bán", "transaction_type": "Mã loại giao dịch", "fixed_amount": "Số tiền cố định", "source_reference": "Nguồn tham chiếu"}
        widgets = {"source_reference": forms.Textarea(attrs={"rows": 3})}


class FxRateForm(PricingForm):
    resource = "fx_rate"
    from_currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), label="Tiền tệ nguồn")
    to_currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), label="Tiền tệ đích")
    effective_at = forms.DateTimeField(label="Hiệu lực từ thời điểm", initial=timezone.now, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M:%S"))
    valid_to = forms.DateTimeField(label="Hiệu lực đến thời điểm", required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M:%S"))
    status = forms.ChoiceField(label="Trạng thái", choices=LIFECYCLE, initial="DRAFT")
    groups = (("Chiều quy đổi", ("from_currency_code", "to_currency_code", "rate", "rate_type")), ("Hiệu lực", ("effective_at", "valid_to", "status")), ("Nguồn tham chiếu", ("source_name", "source_reference")))
    class Meta:
        model = FxRate
        fields = FIELDS["fx_rate"]
        labels = {"rate_type": "Mã loại tỷ giá", "rate": "Tỷ giá", "source_name": "Tên nguồn dữ liệu", "source_reference": "Nguồn tham chiếu"}
        help_texts = {"rate": "1 đơn vị tiền tệ nguồn = tỷ giá × đơn vị tiền tệ đích. Tối đa 12 chữ số thập phân; không tự đảo chiều."}
        widgets = {"source_reference": forms.Textarea(attrs={"rows": 3})}


class ClosePeriodForm(forms.Form):
    def __init__(self, *args, resource, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "valid_to" if resource == "fx_rate" else "effective_to"
        if resource == "fx_rate":
            field = forms.DateTimeField(label="Thời điểm kết thúc hiệu lực", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M:%S"))
        else:
            field = forms.DateField(label="Ngày kết thúc hiệu lực", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
        field.widget.attrs.update({"class": FIELD_CLASSES, "aria-describedby": f"id_{self.name}_errors"})
        self.fields[self.name] = field

    @property
    def sections(self): return (("Kết thúc hiệu lực", tuple(self)),)

    def mark_errors(self):
        for name in self.errors:
            if name in self.fields: self.fields[name].widget.attrs["aria-invalid"] = "true"
