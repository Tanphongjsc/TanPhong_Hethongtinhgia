"""Vietnamese forms, structured sample inputs and simple editor presentation."""
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from apps.core.models import CostElement, Formula
from apps.master_data.forms import FIELD_CLASSES, ReferenceChoiceField, ReferenceDataForm, CompactNumberInput
from .constants import HEADER_FIELDS
from .engine import build_plan
from .errors import FormulaError
from .services import validate_header, validate_period
from .validator import NUMERIC


def style_fields(form):
    for name, field in form.fields.items():
        field.widget.attrs.setdefault("class", "h-4 w-4 rounded border-slate-300 accent-brand-600" if isinstance(field.widget, forms.CheckboxInput) else FIELD_CLASSES)
        field.widget.attrs["aria-describedby"] = f"{form[name].auto_id}_help {form[name].auto_id}_errors"
        if form.is_bound and name in form.errors: field.widget.attrs["aria-invalid"] = "true"


class FormulaForm(ReferenceDataForm):
    output_element = ReferenceChoiceField(queryset=CostElement.objects.none(), required=False, label="Phần tử chi phí kết quả")
    validate_values = staticmethod(validate_header)

    class Meta:
        model = Formula
        fields = HEADER_FIELDS
        labels = {"code": "Mã công thức", "name": "Tên công thức", "description": "Mô tả", "is_active": "Đang hoạt động"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        error_messages = {"code": {"required": "Vui lòng nhập mã công thức."}, "name": {"required": "Vui lòng nhập tên công thức."}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["output_element"].queryset = CostElement.objects.filter(organization=self.workspace.organization).filter(
            Q(is_active=True) | Q(pk=self.instance.output_element_id)).order_by("code")
        if not self.instance._state.adding:
            self.uppercase_fields = ()
            for name in ("code", "output_element"):
                self.fields[name].disabled = True
                self.fields[name].help_text = "Định danh ổn định; không thay đổi khi chỉnh sửa."


class VersionForm(forms.Form):
    expression = forms.CharField(label="Biểu thức", strip=True, widget=forms.Textarea(attrs={"rows": 10, "class": FIELD_CLASSES + " font-mono", "spellcheck": "false", "x-ref": "expression"}),
        error_messages={"required": "Biểu thức công thức không được để trống."})
    effective_from = forms.DateField(required=False, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), help_text="Ngày kết thúc phải sau ngày bắt đầu; để trống nếu không giới hạn.")
    change_reason = forms.CharField(required=False, label="Lý do thay đổi", widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, workspace, formula, **kwargs):
        self.workspace, self.formula = workspace, formula
        self.plan = None
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean(self):
        values = super().clean()
        if self.errors: return values
        try:
            validate_period(values)
            self.plan = build_plan(organization=self.workspace.organization, formula=self.formula, expression=values["expression"])
        except ValidationError as error:
            from apps.master_data.ui_helpers import add_form_error
            add_form_error(self, error)
        except FormulaError as error:
            self.add_error("expression", error.describe(values["expression"]))
        return values

    @property
    def sections(self):
        return (("Hiệu lực và thay đổi", tuple(self[name] for name in ("effective_from", "effective_to", "change_reason"))),)


class TestForm(forms.Form):
    test_name = forms.CharField(required=False, max_length=255, label="Tên bộ kiểm thử", help_text="Nhập khi muốn lưu dữ liệu mẫu và kết quả mong đợi.")

    def __init__(self, *args, plan, **kwargs):
        self.plan = plan
        super().__init__(*args, **kwargs)
        self.input_names = {}
        for code, element in sorted(plan.inputs.items()):
            name = f"input_{code}"
            self.input_names[code] = name
            self.fields[name] = self.value_field(element.value_type, label=f"{element.name} · {code}", required=True)
            unit = element.default_uom
            self.fields[name].help_text = " · ".join(filter(None, (element.currency_code_id, f"{unit.name} ({unit.symbol})" if unit else None,
                "Nhập tỷ lệ thập phân; 0.1 tương ứng 10%." if element.value_type == "PERCENT" else None)))
        kind = plan.types[plan.root_code].kind
        self.fields["expected"] = self.value_field(kind, label="Kết quả mong đợi", required=False)
        self.fields["expected"].help_text = "So sánh chính xác. Bộ kiểm thử mới có sai số cho phép bằng 0."
        style_fields(self)

    @staticmethod
    def value_field(kind, *, label, required):
        if kind in NUMERIC:
            return forms.DecimalField(label=label, required=required, max_digits=64, widget=CompactNumberInput(attrs={"step": "any"}),
                error_messages={"required": "Vui lòng nhập dữ liệu mẫu.", "invalid": "Vui lòng nhập số hợp lệ."})
        if kind == "BOOLEAN":
            return forms.TypedChoiceField(label=label, required=required, choices=(("", "Chọn giá trị"), ("TRUE", "Có"), ("FALSE", "Không")),
                coerce=lambda value: value == "TRUE", empty_value=None)
        return forms.CharField(label=label, required=required, max_length=8000, strip=False)

    def clean(self):
        values = super().clean()
        if self.errors: return values
        values["inputs"] = {code: values[name] for code, name in self.input_names.items()}
        try: self.plan.run(values["inputs"])
        except FormulaError as error: self.add_error(None, error.describe())
        expected = values.get("expected")
        if self.plan.types[self.plan.root_code].kind == "TEXT" and expected == "":
            values["expected"] = None
        if isinstance(expected, Decimal) and (len(expected.as_tuple().digits) > 24 or -expected.as_tuple().exponent > 8):
            self.add_error("expected", "Kết quả mong đợi lưu tối đa 24 chữ số, trong đó 8 chữ số thập phân.")
        return values

    @property
    def input_fields(self):
        return tuple(self[name] for name in self.input_names.values())
