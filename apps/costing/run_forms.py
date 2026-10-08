import uuid
from django import forms
from django.db.models import Exists, OuterRef
from django.utils import timezone
from apps.core.models import Product, Sku, Uom, Currency, CostingScheme, CostingSchemeVersion, CostingSchemeLine
from apps.master_data.forms import ReferenceChoiceField, UnitChoiceField, CompactNumberInput, FIELD_CLASSES
from .run_constants import RUN_TYPES
from .engine.resolvers.common import dated


class RunForm(forms.Form):
    product = ReferenceChoiceField(queryset=Product.objects.none(), label="Sản phẩm")
    sku = ReferenceChoiceField(queryset=Sku.objects.none(), required=False, label="SKU")
    scheme = ReferenceChoiceField(queryset=CostingScheme.objects.none(), label="Phương án tính giá thành", help_text="Phương án chưa được gán sẵn cho sản phẩm/SKU. Vui lòng chọn phương án phù hợp; danh sách chỉ gồm phương án có phiên bản hiệu lực tại ngày tính giá.")
    costing_date = forms.DateField(label="Ngày tính giá", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), initial=timezone.localdate)
    quantity = forms.DecimalField(label="Sản lượng cần tính", max_digits=24, decimal_places=8, widget=CompactNumberInput(attrs={"step": "any"}), initial=1)
    quantity_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị sản lượng")
    result_currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), label="Tiền tệ kết quả")
    run_type = forms.ChoiceField(label="Loại lần tính", choices=RUN_TYPES, initial="STANDARD")
    packaging_quantity = forms.DecimalField(required=False, label="Sản lượng cơ sở đóng gói", max_digits=24, decimal_places=8, widget=CompactNumberInput(attrs={"step": "any"}), help_text="Sản lượng mà các số lượng thành phần bao bì đáp ứng. Không tự nhân số lượng theo cấp cha.")
    packaging_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị cơ sở đóng gói")
    notes = forms.CharField(required=False, label="Ghi chú", max_length=3000, widget=forms.Textarea(attrs={"rows": 2}))
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, workspace, options_url=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace, self.manual_rows, self.configuration_message = workspace, [], ""
        organization = workspace.organization
        self.initial.setdefault("idempotency_key", uuid.uuid4())
        def selected(name):
            value = self.data.get(name) if self.is_bound else self.initial.get(name)
            return getattr(value, "pk", value)
        def pk(value): return int(str(value)) if str(value).isascii() and str(value).isdecimal() and len(str(value)) <= 18 else None
        self.fields["product"].queryset = Product.objects.filter(organization=organization, is_active=True).order_by("code")
        self.fields["sku"].queryset = Sku.objects.filter(organization=organization, product__organization=organization, product_id=pk(selected("product")), is_active=True).order_by("code")
        units = Uom.objects.filter(is_active=True, category__is_active=True).select_related("category").order_by("name")
        for name in ("quantity_uom", "packaging_uom"): self.fields[name].queryset = units
        self.fields["result_currency_code"].queryset = Currency.objects.filter(is_active=True).order_by("code")
        try: day = self.fields["costing_date"].clean(selected("costing_date")) if selected("costing_date") else timezone.localdate()
        except forms.ValidationError: day = None
        versions = dated(CostingSchemeVersion.objects.filter(scheme__organization=organization, scheme__is_active=True, status="EFFECTIVE"), day) if day else CostingSchemeVersion.objects.none()
        self.fields["scheme"].queryset = CostingScheme.objects.filter(organization=organization, is_active=True).filter(Exists(versions.filter(scheme_id=OuterRef("pk")))).order_by("code")
        candidates = list(versions.filter(scheme_id=pk(selected("scheme")))[:2])
        self.version = candidates[0] if len(candidates) == 1 else None
        if selected("scheme") and self.version is None: self.configuration_message = "Phương án chưa có đúng một phiên bản hiệu lực tại ngày tính giá."
        rows = list(CostingSchemeLine.objects.filter(scheme_version=self.version).select_related("cost_element").order_by("display_order", "pk")[:201]) if self.version else []
        self.has_packaging = any(row.source_mode == "SYSTEM" and row.system_resolver_code == "PACKAGING_COST" for row in rows)
        for name in ("packaging_quantity", "packaging_uom"): self.fields[name].required = self.has_packaging
        for row in rows:
            if row.source_mode != "MANUAL": continue
            name = f"manual_{row.pk}"
            kind = row.cost_element.value_type if row.cost_element else "TEXT" if row.line_type == "INFO" else "NUMBER"
            if kind == "BOOLEAN": field = forms.ChoiceField(choices=(("true", "Có"), ("false", "Không")))
            elif kind == "TEXT": field = forms.CharField(max_length=4000)
            else: field = forms.DecimalField(max_digits=24 if kind != "PERCENT" else 18, decimal_places=8 if kind != "PERCENT" else 10, min_value=row.min_override_value, max_value=row.max_override_value, widget=CompactNumberInput(attrs={"step": "any"}))
            field.label = f"{row.label} ({row.line_code})"
            field.help_text = "Dữ liệu đầu vào thủ công, không phải điều chỉnh kết quả đã tính." + (" Nhập tỷ lệ dạng thập phân (ví dụ 0,1 tương ứng 10%)." if kind == "PERCENT" else "")
            self.fields[name] = field
            self.manual_rows.append((row, name, kind))
        if options_url:
            for name in ("product", "sku", "scheme", "costing_date"):
                self.fields[name].widget.attrs.update({"hx-get": options_url, "hx-trigger": "change", "hx-include": "closest form", "hx-params": "not csrfmiddlewaretoken,idempotency_key,notes", "hx-target": "#run-dependent-fields", "hx-swap": "outerHTML", "hx-sync": "closest form:replace", "hx-push-url": "false"})
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", FIELD_CLASSES)
            field.widget.attrs["aria-describedby"] = f"{self[name].auto_id}_help {self[name].auto_id}_errors"

    def clean(self):
        values = super().clean()
        for name in ("quantity", "packaging_quantity"):
            if values.get(name) is not None and values[name] <= 0: self.add_error(name, "Sản lượng phải lớn hơn 0.")
        if values.get("sku") and values.get("product") and values["sku"].product_id != values["product"].pk:
            self.add_error("sku", "SKU không thuộc sản phẩm đã chọn.")
        if self.configuration_message: self.add_error("scheme", self.configuration_message)
        values["manual"] = {row.line_code: values[name] == "true" if kind == "BOOLEAN" else values[name] for row, name, kind in self.manual_rows if name in values}
        return values

    def mark_errors(self):
        for name in self.errors:
            if name in self.fields: self.fields[name].widget.attrs["aria-invalid"] = "true"

    @property
    def manual_fields(self): return tuple(self[name] for _, name, _ in self.manual_rows)

    @property
    def sections(self): return (("Sản lượng và thời điểm", tuple(self[name] for name in ("product", "costing_date", "quantity", "quantity_uom", "result_currency_code", "run_type"))),)

    @property
    def dependent_fields(self): return (self["sku"], self["scheme"])

    @property
    def packaging_fields(self): return tuple(self[name] for name in ("packaging_quantity", "packaging_uom"))
