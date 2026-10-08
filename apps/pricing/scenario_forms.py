from decimal import Decimal
from django import forms
from django.urls import reverse
from django.utils import timezone
from apps.core.models import Product, Sku, CostingRun, Channel, Currency
from apps.master_data.forms import ReferenceChoiceField, CompactNumberInput, FIELD_CLASSES
from apps.master_data.ui_helpers import add_form_error
from .scenario_constants import FIELDS, METHODS
from .scenario_selectors import completed_runs, run_label
from .scenario_validators import validate_input


class RunChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj): return run_label(obj)


def number(label, *, ratio=False):
    return forms.DecimalField(label=label, required=False, max_digits=18 if ratio else 24,
        decimal_places=8, widget=CompactNumberInput(attrs={"step": "any"}))


def selected_id(value):
    value = getattr(value, "pk", value)
    return int(str(value)) if str(value).isascii() and str(value).isdecimal() and len(str(value)) <= 18 else None


class ScenarioForm(forms.Form):
    code = forms.CharField(label="Mã kịch bản", max_length=120)
    name = forms.CharField(label="Tên kịch bản", max_length=255)
    product = ReferenceChoiceField(queryset=Product.objects.none(), label="Sản phẩm")
    sku = ReferenceChoiceField(queryset=Sku.objects.none(), label="SKU", required=False)
    base_run = RunChoiceField(queryset=CostingRun.objects.none(), label="Nguồn giá thành", help_text="Chỉ chọn lần tính đã khóa, có kết quả đã lưu và đúng sản phẩm/SKU. Giá bán tính cho một đơn vị sản lượng của nguồn này.")
    channel = ReferenceChoiceField(queryset=Channel.objects.none(), label="Kênh bán")
    pricing_date = forms.DateField(label="Ngày định giá", initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    pricing_method = forms.ChoiceField(label="Phương pháp định giá", choices=METHODS)
    target_margin = number("Biên lợi nhuận mục tiêu (%)", ratio=True)
    target_markup = number("Tỷ lệ cộng trên giá vốn (%)", ratio=True)
    target_profit_per_unit = number("Lợi nhuận mục tiêu trên một đơn vị")
    minimum_price = number("Giá bán tối thiểu")
    currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), label="Tiền tệ bán")
    tax_mode = forms.ChoiceField(label="Thuế bán hàng", choices=(("REQUIRED", "Áp dụng thuế theo quy tắc"), ("NONE", "Không áp dụng thuế")), initial="REQUIRED")
    jurisdiction_code = forms.CharField(label="Mã khu vực áp dụng thuế", required=False, max_length=80, help_text="Lấy từ mã thị trường của kênh nếu có; cần nhập rõ khi áp dụng thuế.")
    transaction_type = forms.CharField(label="Mã loại giao dịch", required=False, max_length=100)
    fx_rate_type = forms.CharField(label="Mã loại tỷ giá", required=False, max_length=50, help_text="Bắt buộc nếu cần đổi tiền tệ; đúng chiều, tại 00:00 ngày định giá (giờ Việt Nam).")
    valid_from = forms.DateField(label="Hiệu lực từ ngày", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    valid_to = forms.DateField(label="Hiệu lực đến ngày", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    def __init__(self, *args, workspace, instance=None, **kwargs):
        initial = dict(kwargs.pop("initial", {}))
        if instance:
            initial.update({name: getattr(instance, name) for name in FIELDS})
            initial.update(product=instance.base_run.product_id, sku=instance.base_run.sku_id,
                pricing_date=instance.scenario_context_jsonb.get("pricing_date"))
            for name in ("tax_mode", "jurisdiction_code", "transaction_type", "fx_rate_type"):
                initial[name] = instance.scenario_context_jsonb.get(name, "REQUIRED" if name == "tax_mode" else "")
            for name in ("target_margin", "target_markup"):
                if initial[name] is not None: initial[name] = (initial[name] * Decimal(100)).normalize()
        super().__init__(*args, initial=initial, **kwargs)
        self.workspace, self.instance = workspace, instance
        org = workspace.organization
        def selected(name): return self.data.get(name) if self.is_bound else self.initial.get(name)
        self.fields["product"].queryset = Product.objects.filter(organization=org, is_active=True).order_by("code")
        self.fields["sku"].queryset = Sku.objects.filter(organization=org, product__organization=org, is_active=True,
            product__is_active=True, product_id=selected_id(selected("product"))).order_by("code")
        runs = completed_runs(org).filter(product_id=selected_id(selected("product")), sku_id=selected_id(selected("sku")))
        # Bound the dropdown, retaining a chosen older run only within its scope.
        recent = runs.order_by("-created_at", "pk").values("pk")[:100]
        from django.db.models import Q
        self.fields["base_run"].queryset = runs.filter(Q(pk__in=recent) | Q(pk=selected_id(selected("base_run")))).only("id", "context_jsonb", "created_at", "result_currency_code", "run_no", "product", "sku").order_by("-created_at", "pk")
        self.fields["channel"].queryset = Channel.objects.filter(organization=org, is_active=True).order_by("code")
        self.fields["currency_code"].queryset = Currency.objects.filter(is_active=True).order_by("code")
        channel = self.fields["channel"].queryset.filter(pk=selected_id(selected("channel"))).first()
        if channel:
            if not selected("currency_code"): self.initial["currency_code"] = channel.default_currency_code_id
            if not selected("jurisdiction_code"): self.initial["jurisdiction_code"] = channel.market_code
        for name in ("target_margin", "target_markup"):
            self.fields[name].help_text = "Nhập %, ví dụ 20. DB lưu 0,20. Chỉ nhập mục tiêu của phương pháp đã chọn."
        for name, field in self.fields.items():
            field.widget.attrs.update({"class": FIELD_CLASSES, "aria-describedby": f"{self[name].auto_id}_help {self[name].auto_id}_errors"})
        for name in ("product", "sku", "channel"):
            self.fields[name].widget.attrs.update({"hx-get": reverse("pricing:scenario_options"), "hx-trigger": "change", "hx-include": "closest form",
                "hx-params": "product,sku,base_run,channel,currency_code,jurisdiction_code", "hx-target": "#scenario-dependent-fields", "hx-swap": "outerHTML", "hx-sync": "closest form:replace", "hx-push-url": "false"})

    def clean(self):
        values = super().clean()
        values["code"] = values.get("code", "").strip().upper()
        values["name"] = values.get("name", "").strip()
        for name in ("jurisdiction_code", "transaction_type", "fx_rate_type"):
            values[name] = values.get(name, "").strip().upper()
        for name in ("target_margin", "target_markup"):
            if values.get(name) is not None: values[name] /= Decimal(100)
        if self.errors: return values
        try: validate_input(data=values, organization=self.workspace.organization, instance=self.instance)
        except forms.ValidationError as error: add_form_error(self, error)
        return values

    def mark_errors(self):
        for name in self.errors:
            if name in self.fields: self.fields[name].widget.attrs["aria-invalid"] = "true"

    @property
    def sections(self):
        return tuple((title, tuple(self[name] for name in names)) for title, names in (
            ("Thông tin kịch bản", ("code", "name", "product")),
            ("Kênh bán và thời điểm", ("channel", "pricing_date")),
            ("Thuế và tỷ giá", ("tax_mode", "transaction_type", "fx_rate_type")),
            ("Chiến lược giá", ("pricing_method", "target_margin", "target_markup", "target_profit_per_unit", "minimum_price")),
            ("Hiệu lực kịch bản", ("valid_from", "valid_to")),
        ))
