from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json


class PricingError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def json_data(value):
    if isinstance(value, Decimal):
        if not value.is_finite(): raise PricingError("INVALID_NUMBER", "Giá trị số không hợp lệ.")
        return str(value)
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, dict): return {str(k): json_data(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [json_data(v) for v in value]
    if isinstance(value, float): raise PricingError("INVALID_NUMBER", "Không hỗ trợ số thực thiếu độ chính xác.")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(json_data(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class PricingContext:
    organization: object
    scenario: object
    run: object
    pricing_date: date
    jurisdiction: str
    transaction_type: str
    tax_mode: str
    fx_rate_type: str


POLICY = {"version": 1, "margin_denominator": "CUSTOMER_GROSS_PRICE", "markup_denominator": "UNIT_COST",
    "fee_basis": "CUSTOMER_GROSS_PRICE", "fixed_fee_basis": "ONE_COSTING_OUTPUT_UNIT",
    "fee_resolution": "FEE_TYPE:SKU>CATEGORY>CHANNEL,PRIORITY_DESC,TIE_ERROR",
    "tax_basis": "COMMON_PRE_TAX_PRICE", "tax_order": "PARALLEL", "tax_resolution": "TAX_TYPE:SCOPE_COUNT,PRIORITY_DESC,TIE_ERROR",
    "fx_instant": "PRICING_DATE_00:00_ASIA_HO_CHI_MINH", "fx_direction": "DIRECT_ONLY",
    "money_scale": 8, "rounding": "HALF_EVEN", "commercial_rounding": False}
