"""Vietnamese forms for existing pool/rule configuration only."""
from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.core.models import AllocationRule, CostPool, Uom
from apps.master_data.forms import ReferenceChoiceField, ReferenceDataForm, UnitChoiceField
from .overhead_constants import ALLOCATION_BASES, ALLOCATION_RULE_FIELDS, COST_POOL_FIELDS, POOL_TYPES
from .overhead_validators import normalize_overhead_values, validate_allocation_rule, validate_cost_pool


class CostPoolForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_overhead_values)
    validate_values = staticmethod(validate_cost_pool)
    pool_type = forms.ChoiceField(choices=(("", "Chọn loại nhóm chi phí"), *POOL_TYPES), label="Loại nhóm chi phí", error_messages={"required": "Vui lòng chọn loại nhóm chi phí."})

    class Meta:
        model = CostPool
        fields = COST_POOL_FIELDS
        labels = {"code": "Mã nhóm chi phí", "name": "Tên nhóm chi phí", "description": "Mô tả", "is_active": "Đang hoạt động"}
        error_messages = {"code": {"required": "Vui lòng nhập mã nhóm chi phí."}, "name": {"required": "Vui lòng nhập tên nhóm chi phí."}}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    @property
    def sections(self):
        return (("Thông tin chung", tuple(self[name] for name in ("code", "name", "pool_type", "description"))), ("Quản lý", (self["is_active"],)))


class AllocationRuleForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_overhead_values)
    validate_values = staticmethod(validate_allocation_rule)
    pool = ReferenceChoiceField(queryset=CostPool.objects.none(), label="Nhóm chi phí", error_messages={"required": "Vui lòng chọn nhóm chi phí."})
    basis_type = forms.ChoiceField(choices=(("", "Chọn tiêu thức phân bổ"), *ALLOCATION_BASES), label="Tiêu thức phân bổ", error_messages={"required": "Vui lòng chọn tiêu thức phân bổ."})
    basis_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị tiêu thức")
    priority = forms.IntegerField(min_value=-2147483648, max_value=2147483647, initial=100, label="Mức ưu tiên", help_text="Số nguyên. Thứ tự áp dụng sẽ được xác định khi tính giá.")
    effective_from = forms.DateField(initial=timezone.localdate, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), error_messages={"required": "Vui lòng nhập ngày bắt đầu hiệu lực."})
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), help_text="Để trống nếu không giới hạn. Ngày kết thúc phải sau ngày bắt đầu.")

    class Meta:
        model = AllocationRule
        fields = ALLOCATION_RULE_FIELDS
        labels = {"code": "Mã quy tắc", "name": "Tên quy tắc", "formula_code": "Mã công thức tham chiếu"}
        error_messages = {"code": {"required": "Vui lòng nhập mã quy tắc phân bổ."}, "name": {"required": "Vui lòng nhập tên quy tắc phân bổ."}}
        help_texts = {"formula_code": "Không bắt buộc. Chỉ lưu mã tham chiếu; không thực thi công thức tại màn hình này."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pool"].queryset = CostPool.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.pool_id)).order_by("code", "pk")
        self.fields["basis_uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=self.instance.basis_uom_id)).order_by("name", "pk")

    @property
    def sections(self):
        return (("Thông tin chung", tuple(self[name] for name in ("code", "name", "pool"))),
            ("Cơ sở phân bổ", tuple(self[name] for name in ("basis_type", "basis_uom", "formula_code", "priority"))),
            ("Hiệu lực", tuple(self[name] for name in ("effective_from", "effective_to"))))
