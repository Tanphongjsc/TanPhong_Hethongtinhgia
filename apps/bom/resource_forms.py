"""Vietnamese forms backed by the existing unmanaged resource models."""
from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Currency, Resource, ResourceRate, Uom, WorkCenter
from apps.master_data.forms import CompactNumberInput, ReferenceChoiceField, ReferenceDataForm, UnitChoiceField
from .resource_constants import RATE_FIELDS, RESOURCE_FIELDS, RESOURCE_TYPES, WORK_CENTER_FIELDS
from .resource_validators import normalize_resource_values, validate_resource, validate_resource_rate, validate_work_center


class ProductionReferenceForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_resource_values)
    section_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        for name, model in (("work_center", WorkCenter), ("resource", Resource), ("capacity_uom", Uom), ("per_uom", Uom), ("currency_code", Currency)):
            if name not in self.fields:
                continue
            query = model.objects.all()
            if model in (WorkCenter, Resource):
                query = query.filter(organization=self.workspace.organization)
            if model is Resource:
                query = query.filter(Q(work_center__isnull=True) | Q(work_center__organization=self.workspace.organization))
            self.fields[name].queryset = query.filter(Q(is_active=True) | Q(pk=getattr(self.instance, f"{name}_id"))).order_by("name" if model is Uom else "code", "pk")

    @property
    def sections(self):
        return tuple((title, tuple(self[name] for name in fields)) for title, fields in self.section_fields)


class WorkCenterForm(ProductionReferenceForm):
    validate_values = staticmethod(validate_work_center)
    capacity_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị công suất")
    section_fields = (("Thông tin chung", ("code", "name", "site_code")),
        ("Công suất", ("capacity_value", "normal_capacity_value", "capacity_uom")), ("Quản lý", ("is_active",)))

    class Meta:
        model = WorkCenter
        fields = WORK_CENTER_FIELDS
        labels = {"code": "Mã trung tâm sản xuất", "name": "Tên trung tâm", "site_code": "Mã địa điểm",
            "capacity_value": "Công suất", "normal_capacity_value": "Công suất bình thường", "is_active": "Đang hoạt động"}
        error_messages = {"code": {"required": "Vui lòng nhập mã trung tâm sản xuất."}, "name": {"required": "Vui lòng nhập tên trung tâm sản xuất."}}
        widgets = {field: CompactNumberInput(attrs={"min": "0", "step": "any"}) for field in ("capacity_value", "normal_capacity_value")}
        help_texts = {"capacity_value": "Không âm. Chọn đơn vị công suất khi nhập giá trị.", "code": "Mã được chuẩn hóa thành chữ hoa."}


class ResourceForm(ProductionReferenceForm):
    validate_values = staticmethod(validate_resource)
    resource_type = forms.ChoiceField(choices=RESOURCE_TYPES, label="Loại nguồn lực", error_messages={"required": "Vui lòng chọn loại nguồn lực."})
    work_center = ReferenceChoiceField(queryset=WorkCenter.objects.none(), required=False, label="Trung tâm sản xuất")
    capacity_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị công suất")
    section_fields = (("Thông tin chung", ("code", "name", "resource_type", "work_center")),
        ("Năng lực", ("capacity_value", "capacity_uom")), ("Quản lý", ("is_active",)))

    class Meta:
        model = Resource
        fields = RESOURCE_FIELDS
        labels = {"code": "Mã nguồn lực", "name": "Tên nguồn lực", "capacity_value": "Công suất", "is_active": "Đang hoạt động"}
        error_messages = {"code": {"required": "Vui lòng nhập mã nguồn lực."}, "name": {"required": "Vui lòng nhập tên nguồn lực."}}
        widgets = {"capacity_value": CompactNumberInput(attrs={"min": "0", "step": "any"})}
        help_texts = {"code": "Mã được chuẩn hóa thành chữ hoa.", "capacity_value": "Không âm. Chọn đơn vị công suất khi nhập giá trị."}


class ResourceRateForm(ProductionReferenceForm):
    validate_values = staticmethod(validate_resource_rate)
    uppercase_fields = ()
    resource = ReferenceChoiceField(queryset=Resource.objects.none(), label="Nguồn lực", error_messages={"required": "Vui lòng chọn nguồn lực."})
    currency_code = ReferenceChoiceField(queryset=Currency.objects.none(), label="Tiền tệ", error_messages={"required": "Vui lòng chọn tiền tệ."})
    per_uom = UnitChoiceField(queryset=Uom.objects.none(), label="Đơn vị tính giá", error_messages={"required": "Vui lòng chọn đơn vị tính giá."})
    effective_from = forms.DateField(initial=timezone.localdate, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), error_messages={"required": "Vui lòng nhập ngày bắt đầu hiệu lực."})
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), help_text="Để trống nếu không giới hạn. Ngày kết thúc phải sau ngày bắt đầu.")
    section_fields = (("Nguồn lực", ("resource", "rate_type")), ("Đơn giá", ("amount", "currency_code", "per_uom")),
        ("Hiệu lực", ("effective_from", "effective_to")), ("Tham chiếu", ("source_reference",)))

    class Meta:
        model = ResourceRate
        fields = RATE_FIELDS
        labels = {"rate_type": "Mã loại đơn giá", "amount": "Đơn giá", "source_reference": "Nguồn dữ liệu / Tham chiếu"}
        error_messages = {"rate_type": {"required": "Vui lòng nhập mã loại đơn giá."}, "amount": {"required": "Vui lòng nhập đơn giá."}}
        widgets = {"amount": CompactNumberInput(attrs={"min": "0", "step": "any"}), "source_reference": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"rate_type": "Mã nghiệp vụ do công ty quy định; giữ nguyên mã hiện có khi chỉnh sửa.",
            "amount": "Đơn giá không âm theo cấu hình dữ liệu hiện tại; tối đa 8 chữ số thập phân."}
