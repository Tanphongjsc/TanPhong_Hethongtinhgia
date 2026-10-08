"""Pricing configuration validation; no fee/tax/FX calculation."""
from decimal import Decimal
from django.core.exceptions import ValidationError
from .constants import CHANNEL_TYPES, MODELS

CODE_FIELDS = ("code", "channel_type", "platform_code", "market_code", "seller_type", "fee_type", "fee_base", "jurisdiction_code", "tax_type", "tax_class_code", "transaction_type", "tax_base", "rate_type")


def normalize_values(data, *, uppercase=()):
    values = dict(data)
    for name, value in values.items():
        if isinstance(value, str):
            value = value.strip()
            if name in CODE_FIELDS: value = value.upper()
            values[name] = value if value or name in ("code", "name", "source_name") else None
    return values


def validate_values(*, resource, data, organization, instance=None):
    errors = {}
    if resource == "channel":
        for field, label in (("code", "mã kênh bán"), ("name", "tên kênh bán")):
            if not data.get(field): errors[field] = f"Vui lòng nhập {label}."
        if data.get("channel_type") not in dict(CHANNEL_TYPES): errors["channel_type"] = "Vui lòng chọn loại kênh bán hợp lệ."
        query = MODELS[resource].objects.filter(organization=organization, code=data.get("code"))
        if instance and instance.pk: query = query.exclude(pk=instance.pk)
        if query.exists(): errors["code"] = "Mã kênh bán đã tồn tại."
    else:
        required = {"channel_fee_rule": ("channel", "fee_type", "fee_base"), "tax_rule": ("jurisdiction_code", "tax_type", "tax_base"), "fx_rate": ("rate_type", "from_currency_code", "to_currency_code", "source_name", "effective_at")}[resource]
        for name in required:
            if data.get(name) in (None, ""): errors[name] = "Vui lòng nhập hoặc chọn giá trị cho trường này."
        if data.get("status") not in ("DRAFT", "EFFECTIVE"): errors["status"] = "Chỉ lưu Nháp hoặc đưa trực tiếp vào hiệu lực sau khi kiểm tra hợp lệ."
    if resource in ("channel_fee_rule", "tax_rule"):
        if data.get("rate") is None and data.get("fixed_amount") is None:
            errors["rate"] = "Vui lòng nhập tỷ lệ hoặc số tiền cố định."
        for name in ("rate", "refundable_ratio", "recoverable_ratio"):
            value = data.get(name)
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or not 0 <= value <= 1):
                errors[name] = "Tỷ lệ phải từ 0% đến 100%."
        for name in ("fixed_amount", "floor_amount", "cap_amount"):
            value = data.get(name)
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or value < 0): errors[name] = "Số tiền không được âm và phải là số hợp lệ."
        if any(data.get(name) is not None for name in ("fixed_amount", "floor_amount", "cap_amount")) and not data.get("currency_code"):
            errors["currency_code"] = "Vui lòng chọn tiền tệ cho các giá trị tiền."
        if data.get("floor_amount") is not None and data.get("cap_amount") is not None and data["cap_amount"] < data["floor_amount"]:
            errors["cap_amount"] = "Giá trị trần không được nhỏ hơn giá trị sàn."
        start, end = data.get("effective_from"), data.get("effective_to")
        if not start: errors["effective_from"] = "Vui lòng nhập ngày bắt đầu hiệu lực."
        if start and end and end <= start: errors["effective_to"] = "Ngày kết thúc phải sau ngày bắt đầu hiệu lực."
        priority = data.get("priority")
        if type(priority) is not int or not -2147483648 <= priority <= 2147483647: errors["priority"] = "Mức ưu tiên phải là số nguyên trong giới hạn lưu trữ."
    if resource == "fx_rate":
        rate = data.get("rate")
        if not isinstance(rate, Decimal) or not rate.is_finite() or rate <= 0: errors["rate"] = "Tỷ giá phải lớn hơn 0."
        if data.get("from_currency_code") == data.get("to_currency_code"): errors["to_currency_code"] = "Tiền tệ đích phải khác tiền tệ nguồn."
        if data.get("valid_to") and data.get("effective_at") and data["valid_to"] <= data["effective_at"]:
            errors["valid_to"] = "Thời điểm kết thúc phải sau thời điểm bắt đầu hiệu lực."
    if resource == "channel_fee_rule":
        sku, category = data.get("sku"), data.get("product_category")
        if sku and category and sku.product.category_id != category.pk:
            errors["sku"] = "SKU không thuộc nhóm sản phẩm đã chọn."
    if errors: raise ValidationError(errors)
