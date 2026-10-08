from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Max, Q
from django.utils import timezone
from apps.core.models import CostElement, CostingScheme, CostingSchemeLine, CostingSchemeVersion, FormulaVersion, RuleTable
from apps.master_data.forms import ReferenceChoiceField, ReferenceDataForm, CompactNumberInput
from apps.formula_engine.engine import FORMULA_RELATIONS, ELEMENT_RELATIONS
from apps.formula_engine.errors import FormulaError
from .constants import SCHEME_FIELDS, VERSION_FIELDS, LINE_FIELDS, LINE_TYPES, SOURCE_MODES, VISIBILITY_SCOPES, COST_SCOPES, EDITABLE_STATUSES
from .validators import normalize_values, validate_scheme, validate_version, validate_line
from .configuration import analyze_formula


class SchemeForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    validate_values = staticmethod(validate_scheme)
    class Meta:
        model = CostingScheme
        fields = SCHEME_FIELDS
        labels = {"code": "Mã phương án", "name": "Tên phương án", "purpose": "Mã mục đích", "context_scope": "Mã phạm vi áp dụng", "description": "Mô tả", "is_active": "Đang hoạt động"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"purpose": "Mã nghiệp vụ do công ty quy định; không phải phương pháp tính được hệ thống tự thực thi.",
            "context_scope": "Mã phạm vi nghiệp vụ; phương án hiện không gán trực tiếp sản phẩm hoặc SKU."}
        error_messages = {"code": {"required": "Vui lòng nhập mã phương án."}, "name": {"required": "Vui lòng nhập tên phương án."}}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        if self.instance.pk and self.instance.costingschemeversion_set.exclude(status__in=EDITABLE_STATUSES).exists():
            for name in ("code", "purpose", "context_scope"):
                self.fields[name].disabled = True
            self.uppercase_fields = ()
    @property
    def sections(self):
        return (("Thông tin chung", tuple(self[name] for name in SCHEME_FIELDS[:-1])), ("Quản lý", (self["is_active"],)))


class SchemeVersionForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    uppercase_fields = ()
    validate_values = staticmethod(validate_version)
    effective_from = forms.DateField(required=False, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    class Meta:
        model = CostingSchemeVersion
        fields = VERSION_FIELDS
        labels = {"change_reason": "Lý do thay đổi"}
        widgets = {"change_reason": forms.Textarea(attrs={"rows": 3})}
    def __init__(self, *args, source=None, **kwargs):
        if source and kwargs.get("instance") is None:
            kwargs.setdefault("initial", {name: getattr(source, name) for name in VERSION_FIELDS})
        super().__init__(*args, **kwargs)
    @property
    def sections(self): return (("Hiệu lực và thay đổi", tuple(self)),)


class FormulaVersionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, instance):
        from apps.master_data.presentation import display_label
        return f"{instance.formula.code} — {instance.formula.name} — Phiên bản {instance.version_no} — {display_label(instance.status)}"


class SchemeLineForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_values)
    uppercase_fields = ("line_code",)
    cost_element = ReferenceChoiceField(queryset=CostElement.objects.none(), required=False, label="Phần tử chi phí")
    formula_version = FormulaVersionChoiceField(queryset=FormulaVersion.objects.none(), required=False, label="Phiên bản công thức")
    rule_table = ReferenceChoiceField(queryset=RuleTable.objects.none(), required=False, label="Bảng quy tắc")
    line_type = forms.ChoiceField(choices=LINE_TYPES, label="Loại dòng")
    source_mode = forms.ChoiceField(choices=SOURCE_MODES, label="Nguồn dữ liệu")
    cost_scope = forms.ChoiceField(choices=COST_SCOPES, label="Phạm vi chi phí")
    visibility_scope = forms.ChoiceField(choices=VISIBILITY_SCOPES, label="Phạm vi hiển thị")
    display_order = forms.IntegerField(min_value=-2147483648, max_value=2147483647, label="Thứ tự hiển thị")
    rounding_scale = forms.IntegerField(required=False, min_value=0, max_value=12, label="Số chữ số làm tròn", help_text="Để trống để dùng cấu hình phần tử chi phí.")
    class Meta:
        model = CostingSchemeLine
        fields = LINE_FIELDS
        labels = {"line_code": "Mã dòng", "label": "Nhãn hiển thị", "system_resolver_code": "Mã bộ lấy dữ liệu hệ thống",
            "external_adapter_code": "Mã kết nối dữ liệu bên ngoài", "editable": "Cho phép điều chỉnh giá trị",
            "min_override_value": "Giá trị điều chỉnh tối thiểu", "max_override_value": "Giá trị điều chỉnh tối đa",
            "override_requires_reason": "Điều chỉnh cần lý do", "notes": "Ghi chú"}
        widgets = {"notes": forms.Textarea(attrs={"rows": 2}), **{name: CompactNumberInput(attrs={"step": "any"}) for name in ("min_override_value", "max_override_value")}}
        help_texts = {"display_order": "Thứ tự trình bày; phụ thuộc công thức quyết định thứ tự tính sau này.",
            "system_resolver_code": "Mã được hỗ trợ: MATERIAL_COST (nguyên liệu), PACKAGING_COST (bao bì), RESOURCE_COST (nguồn lực), RUN_QUANTITY (sản lượng), ALLOCATION:<mã quy tắc> (công suất bình thường)."}
    def __init__(self, *args, version, options_url=None, **kwargs):
        self.version = version
        super().__init__(*args, **kwargs)
        organization = self.workspace.organization
        self.fields["cost_element"].queryset = CostElement.objects.filter(organization=organization).filter(Q(is_active=True) | Q(pk=self.instance.cost_element_id)).select_related(*ELEMENT_RELATIONS).order_by("code")
        self.fields["rule_table"].queryset = RuleTable.objects.filter(organization=organization).filter(Q(is_active=True) | Q(pk=self.instance.rule_table_id)).order_by("code")
        formulas = FormulaVersion.objects.filter(formula__organization=organization)
        selected = self.data.get(self.add_prefix("cost_element")) if self.is_bound else self.initial.get("cost_element", self.instance.cost_element_id)
        selectable = formulas.filter(status="EFFECTIVE", validation_status="VALID", formula__is_active=True)
        day = version.effective_from or timezone.localdate()
        selectable = selectable.filter(effective_from__lte=day).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))
        if selected:
            selected = getattr(selected, "pk", selected)
            if str(selected).isascii() and str(selected).isdecimal() and len(str(selected)) <= 18:
                selectable = selectable.filter(Q(formula__output_element_id=selected) | Q(formula__output_element__isnull=True))
            else: selectable = selectable.none()
        query = formulas.filter(Q(pk__in=selectable.values("pk")) | Q(pk=self.instance.formula_version_id))
        self.fields["formula_version"].queryset = query.select_related("formula", *("formula__" + name for name in FORMULA_RELATIONS)).order_by("formula__code", "-version_no")
        if not self.is_bound and not self.instance.pk:
            maximum = CostingSchemeLine.objects.filter(scheme_version=version).aggregate(number=Max("display_order"))["number"] or 0
            self.initial.setdefault("display_order", min(max(maximum, 0) + 10, 2147483647))
            self.initial.setdefault("line_type", "INPUT")
            self.initial.setdefault("source_mode", "MANUAL")
            self.initial.setdefault("cost_scope", "MANUFACTURING")
        if options_url:
            for name in ("cost_element", "source_mode"):
                self.fields[name].widget.attrs.update({"hx-get": options_url, "hx-trigger": "change", "hx-include": "closest form", "hx-target": "#scheme-source-fields", "hx-swap": "outerHTML", "hx-push-url": "false", "hx-sync": "#scheme-line-editor:replace"})
    def validate_values(self, *, data, organization, instance):
        validate_line(data=data, organization=organization, instance=instance, version=self.version)
        if data.get("source_mode") == "FORMULA" and data.get("formula_version"):
            try: analyze_formula(organization=organization, version=data["formula_version"], target=data.get("cost_element"), effective_date=self.version.effective_from)
            except FormulaError as error: raise ValidationError({"formula_version": error.describe(data["formula_version"].expression)}) from None
    @property
    def source_fields(self):
        mode = self.data.get(self.add_prefix("source_mode")) if self.is_bound else self.initial.get("source_mode", self.instance.source_mode)
        field = {"SYSTEM": "system_resolver_code", "LOOKUP": "rule_table", "FORMULA": "formula_version", "EXTERNAL": "external_adapter_code"}.get(mode)
        return (self[field],) if field else ()
    @property
    def sections(self):
        return (
            ("Dòng cấu hình", tuple(self[name] for name in ("line_code", "label", "line_type", "display_order", "cost_element", "source_mode"))),
            ("Phạm vi và làm tròn", tuple(self[name] for name in ("cost_scope", "visibility_scope", "rounding_scale"))),
            ("Chính sách điều chỉnh", tuple(self[name] for name in ("editable", "min_override_value", "max_override_value", "override_requires_reason"))),
            ("Ghi chú", (self["notes"],)))
