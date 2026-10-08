"""Cost Element vocabulary from existing costing PostgreSQL CHECK constraints."""
from .presentation import display_label

SUPPLIER_FIELDS = ("code", "name", "tax_code", "default_currency_code", "payment_terms", "is_active")
SUPPLIER_PRICE_FIELDS = (
    "supplier", "item", "price_uom", "currency_code", "min_qty", "unit_price",
    "tax_inclusive", "tax_rate", "tax_recoverable_ratio", "effective_from",
    "effective_to", "source_type", "source_reference",
)
SUPPLIER_PRICE_STATUSES = tuple((code, display_label(code)) for code in (
    "DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "RETIRED",
))
PRICE_DATE_STATUSES = tuple((code, display_label(code)) for code in ("EFFECTIVE", "FUTURE", "EXPIRED"))

VALUE_TYPES = tuple((value, display_label(value)) for value in (
    "MONEY", "NUMBER", "PERCENT", "QUANTITY", "BOOLEAN", "TEXT"
))
SOURCE_MODES = tuple((value, display_label(value)) for value in (
    "SYSTEM", "MANUAL", "LOOKUP", "FORMULA", "EXTERNAL"
))
ACCOUNTING_SCOPES = tuple((value, display_label(value)) for value in (
    "INVENTORY_COST", "COMMERCIAL_COST", "PRICING_ONLY", "ANALYTICS"
))
COST_SCOPES = tuple((value, display_label(value)) for value in (
    "MANUFACTURING", "LANDED", "COST_TO_SERVE", "CHANNEL", "PRICING", "ANALYTICS"
))
ROUNDING_MODES = tuple((value, display_label(value)) for value in (
    "HALF_UP", "HALF_EVEN", "UP", "DOWN", "CEILING", "FLOOR"
))
ROUNDING_MIN = 0
ROUNDING_MAX = 12
PAGE_SIZES = (25, 50, 100)
SORT_FIELDS = ("code", "name", "value_type", "created_at")
EDITABLE_FIELDS = (
    "group", "code", "name", "description", "value_type", "dimension_code",
    "default_source_mode", "currency_code", "default_uom", "rounding_scale",
    "rounding_mode", "accounting_scope", "cost_scope", "is_sensitive", "is_active",
)
CURRENCY_FIELDS = ("code", "name", "decimal_places", "is_active")
UOM_CATEGORY_FIELDS = ("code", "name", "dimension_code", "description", "is_active")
UOM_FIELDS = ("category", "code", "name", "symbol", "precision", "is_base", "is_active")
UOM_CONVERSION_FIELDS = ("from_uom", "to_uom", "factor", "item", "effective_from", "effective_to", "source_reference")
