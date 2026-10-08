from django import forms
from django.db.models import Max, Q

from apps.core.models import Product, Resource, Routing, RoutingOperation, RoutingVersion, Uom, WorkCenter
from apps.master_data.forms import CompactNumberInput, ReferenceChoiceField, ReferenceDataForm, UnitChoiceField
from .routing_constants import IMMUTABLE_STATUSES, OPERATION_FIELDS, ROUTING_FIELDS, VERSION_FIELDS
from .routing_validators import normalize_routing_values, validate_operation, validate_routing, validate_version


class RoutingForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_routing_values)
    validate_values = staticmethod(validate_routing)
    product = ReferenceChoiceField(queryset=Product.objects.none(), label="Sản phẩm", error_messages={"required": "Vui lòng chọn sản phẩm."})

    class Meta:
        model = Routing
        fields = ROUTING_FIELDS
        labels = {"code": "Mã quy trình", "name": "Tên quy trình", "is_active": "Đang hoạt động"}
        error_messages = {"code": {"required": "Vui lòng nhập mã quy trình."}, "name": {"required": "Vui lòng nhập tên quy trình."}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.organization = self.workspace.organization
        self.fields["product"].queryset = Product.objects.filter(organization=self.workspace.organization).filter(Q(is_active=True) | Q(pk=self.instance.product_id)).order_by("code")
        if self.instance.pk and self.instance.routingversion_set.filter(status__in=IMMUTABLE_STATUSES).exists():
            self.fields["product"].disabled = True
            self.fields["product"].help_text = "Sản phẩm được giữ cố định vì quy trình đã có phiên bản được chốt."

    @property
    def sections(self):
        return (("Thông tin chung", tuple(self[name] for name in ("product", "code", "name"))), ("Quản lý", (self["is_active"],)))


class RoutingVersionForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_routing_values)
    uppercase_fields = ()
    batch_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị tính sản lượng lô")
    effective_from = forms.DateField(required=False, label="Hiệu lực từ ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    effective_to = forms.DateField(required=False, label="Hiệu lực đến ngày", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    class Meta:
        model = RoutingVersion
        fields = VERSION_FIELDS
        labels = {"batch_size": "Sản lượng lô chuẩn", "change_reason": "Lý do thay đổi"}
        widgets = {"batch_size": CompactNumberInput(attrs={"min": "0", "step": "any"}), "change_reason": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"batch_size": "Lớn hơn 0 nếu nhập. Không mặc định quy trình cho một đơn vị sản phẩm."}

    def __init__(self, *args, source=None, **kwargs):
        self.source = source
        if source and "instance" not in kwargs:
            kwargs.setdefault("initial", {field: getattr(source, field) for field in VERSION_FIELDS})
        super().__init__(*args, **kwargs)
        reference = source or self.instance
        self.fields["batch_uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=reference.batch_uom_id)).order_by("name")

    def validate_values(self, *, data, organization, instance):
        validate_version(data=data, organization=organization, instance=self.source or instance)

    @property
    def sections(self):
        return (("Cơ sở sản xuất", tuple(self[name] for name in ("batch_size", "batch_uom"))),
            ("Hiệu lực và thay đổi", tuple(self[name] for name in ("effective_from", "effective_to", "change_reason"))))


class RoutingOperationForm(ReferenceDataForm):
    normalize_values = staticmethod(normalize_routing_values)
    uppercase_fields = ()
    sequence_no = forms.IntegerField(min_value=1, max_value=2147483647, label="Thứ tự công đoạn", error_messages={"min_value": "Thứ tự công đoạn phải lớn hơn 0."})
    work_center = ReferenceChoiceField(queryset=WorkCenter.objects.none(), required=False, label="Trung tâm sản xuất")
    primary_resource = ReferenceChoiceField(queryset=Resource.objects.none(), required=False, label="Nguồn lực chính", help_text="Chọn nguồn lực thuộc trung tâm đã chọn hoặc nguồn lực dùng chung.")
    time_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị thời gian")
    quantity_uom = UnitChoiceField(queryset=Uom.objects.none(), required=False, label="Đơn vị tính sản lượng cơ sở")

    class Meta:
        model = RoutingOperation
        fields = OPERATION_FIELDS
        labels = {"operation_code": "Mã công đoạn", "operation_name": "Tên công đoạn", "setup_time": "Thời gian thiết lập", "run_time": "Thời gian chạy", "quantity_basis": "Sản lượng cơ sở", "notes": "Ghi chú"}
        error_messages = {"operation_code": {"required": "Vui lòng nhập mã công đoạn."}, "operation_name": {"required": "Vui lòng nhập tên công đoạn."}}
        widgets = {**{name: CompactNumberInput(attrs={"min": "0", "step": "any"}) for name in ("setup_time", "run_time", "quantity_basis")}, "notes": forms.Textarea(attrs={"rows": 2})}
        help_texts = {"run_time": "Thời gian chạy ứng với sản lượng cơ sở bên dưới; không tự cộng với thời gian thiết lập.", "quantity_basis": "Ví dụ 30 phút chạy cho 100 kg. Lớn hơn 0 nếu nhập."}

    def __init__(self, *args, version, resource_options_url=None, **kwargs):
        self.version = version
        super().__init__(*args, **kwargs)
        self.instance.routing_version = version
        organization = self.workspace.organization
        self.fields["work_center"].queryset = WorkCenter.objects.filter(organization=organization).filter(Q(is_active=True) | Q(pk=self.instance.work_center_id)).order_by("code")
        resources = Resource.objects.filter(organization=organization).filter(Q(work_center__isnull=True) | Q(work_center__organization=organization))
        if self.is_bound:
            center = self.data.get(self.add_prefix("work_center"), "")
        else:
            center = str(self.initial.get("work_center") or self.instance.work_center_id or "")
        if center:
            if center.isascii() and center.isdecimal() and len(center) <= 18:
                resources = resources.filter(Q(work_center_id=center) | Q(work_center__isnull=True))
            else:
                resources = resources.none()
        self.fields["primary_resource"].queryset = resources.filter(Q(is_active=True) | Q(pk=self.instance.primary_resource_id)).select_related("work_center").order_by("code")
        self.fields["time_uom"].queryset = Uom.objects.filter(category__dimension_code__iexact="TIME").filter(Q(is_active=True) | Q(pk=self.instance.time_uom_id)).select_related("category").order_by("name")
        self.fields["quantity_uom"].queryset = Uom.objects.filter(Q(is_active=True) | Q(pk=self.instance.quantity_uom_id)).order_by("name")
        if not self.is_bound and not self.instance.pk:
            number = RoutingOperation.objects.filter(routing_version=version).aggregate(number=Max("sequence_no"))["number"] or 0
            if number < 2147483638:
                self.initial.setdefault("sequence_no", max(number, 0) + 10)
        if resource_options_url:
            self.fields["work_center"].widget.attrs.update({"hx-get": resource_options_url, "hx-trigger": "change",
                "hx-include": "closest form", "hx-target": "#operation-resource-field", "hx-swap": "outerHTML",
                "hx-push-url": "false", "hx-sync": "#routing-operation-editor:replace"})

    def validate_values(self, *, data, organization, instance):
        validate_operation(data=data, organization=organization, instance=instance, version=self.version)

    @property
    def sections(self):
        return (("Thông tin công đoạn", tuple(self[name] for name in ("sequence_no", "operation_code", "operation_name", "work_center"))),
            ("Thời gian", tuple(self[name] for name in ("setup_time", "run_time", "time_uom"))),
            ("Cơ sở sản xuất", tuple(self[name] for name in ("quantity_basis", "quantity_uom"))), ("Ghi chú", (self["notes"],)))
