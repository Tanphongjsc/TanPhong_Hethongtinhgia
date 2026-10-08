"""Input validation shared by forms and services, independent of HTTP."""
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator
from apps.core.models import PriceScenario
from .scenario_constants import METHODS
from .scenario_selectors import completed_runs, unit_cost


def validate_input(*, data, organization, instance=None):
    errors = {}
    for name, label, limit in (("code", "mã kịch bản", 120), ("name", "tên kịch bản", 255)):
        value = data.get(name)
        if not isinstance(value, str) or not value.strip(): errors[name] = f"Vui lòng nhập {label}."
        elif len(value) > limit: errors[name] = f"Vui lòng nhập tối đa {limit} ký tự."
    if PriceScenario.objects.filter(organization=organization, code=data.get("code")).exclude(pk=getattr(instance, "pk", None)).exists():
        errors["code"] = "Mã kịch bản đã tồn tại."
    if type(data.get("pricing_date")) is not date: errors["pricing_date"] = "Vui lòng chọn ngày định giá hợp lệ."
    if data.get("tax_mode") not in ("REQUIRED", "NONE"): errors["tax_mode"] = "Vui lòng xác định có áp dụng thuế bán hàng hay không."
    for name, limit in (("jurisdiction_code", 80), ("transaction_type", 100), ("fx_rate_type", 50)):
        if not isinstance(data.get(name, ""), str) or len(data.get(name, "")) > limit: errors[name] = "Mã cấu hình không hợp lệ."
    if data.get("tax_mode") == "REQUIRED" and not data.get("jurisdiction_code"): errors["jurisdiction_code"] = "Vui lòng nhập mã khu vực áp dụng thuế."
    method = data.get("pricing_method")
    if method not in dict(METHODS): errors["pricing_method"] = "Phương pháp định giá chưa được hỗ trợ."
    required = {"MARGIN": "target_margin", "MARKUP": "target_markup", "PROFIT_PER_UNIT": "target_profit_per_unit"}.get(method)
    for name in ("target_margin", "target_markup", "target_profit_per_unit", "minimum_price"):
        value = data.get(name)
        if name == required and value is None: errors[name] = "Vui lòng nhập mục tiêu cho phương pháp định giá đã chọn."
        if value is None: continue
        if not isinstance(value, Decimal) or not value.is_finite():
            errors[name] = "Giá trị không hợp lệ."
            continue
        digits, places = (18, 10) if name in ("target_margin", "target_markup") else (24, 8)
        try: DecimalValidator(digits, places)(value)
        except ValidationError: errors[name] = "Giá trị vượt quá độ chính xác cho phép."
        if name == "target_margin" and not Decimal(-1) <= value < Decimal(1): errors[name] = "Biên lợi nhuận phải từ -100% đến dưới 100%."
        if name == "target_markup" and value < -1: errors[name] = "Tỷ lệ cộng trên giá vốn không được dưới -100%."
        if name == "minimum_price" and value < 0: errors[name] = "Giá tối thiểu không được âm."
        if name not in (required, "minimum_price"): errors[name] = "Chỉ nhập mục tiêu tương ứng với phương pháp định giá đã chọn."
    start, end = data.get("valid_from"), data.get("valid_to")
    if start and end and end < start: errors["valid_to"] = "Ngày hết hiệu lực không được trước ngày bắt đầu hiệu lực."
    run = data.get("base_run")
    if run is None or not completed_runs(organization).filter(pk=run.pk).exists():
        errors["base_run"] = "Vui lòng chọn lần tính giá thành đã hoàn thành và có kết quả đã lưu."
    else:
        try: unit_cost(run)
        except ValidationError as error: errors["base_run"] = error.messages
        product, sku = data.get("product"), data.get("sku")
        if product is None or run.product_id != product.pk: errors["base_run"] = "Lần tính giá thành không thuộc sản phẩm đã chọn."
        if run.sku_id != getattr(sku, "pk", None): errors["base_run"] = "Lần tính giá thành không thuộc SKU đã chọn."
    for name in ("product", "channel", "currency_code"):
        record = data.get(name)
        if record is None: errors[name] = "Vui lòng chọn dữ liệu hợp lệ."
        elif not record.is_active or getattr(record, "organization_id", organization.pk) != organization.pk:
            errors[name] = "Danh mục đã ngừng hoạt động hoặc không thuộc hệ thống."
    sku = data.get("sku")
    if sku and (not sku.is_active or sku.organization_id != organization.pk or sku.product_id != getattr(data.get("product"), "pk", None)):
        errors["sku"] = "SKU không thuộc sản phẩm đang hoạt động đã chọn."
    if errors: raise ValidationError(errors)
