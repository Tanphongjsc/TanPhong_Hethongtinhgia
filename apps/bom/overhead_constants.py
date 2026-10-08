"""Allow-lists and choices matching the inspected unmanaged overhead tables."""
from apps.master_data.presentation import display_label
from .constants import DATE_STATUSES

COST_POOL_FIELDS = ("code", "name", "pool_type", "description", "is_active")
ALLOCATION_RULE_FIELDS = ("pool", "code", "name", "basis_type", "basis_uom", "formula_code", "priority", "effective_from", "effective_to")
POOL_TYPES = tuple((code, display_label(code)) for code in ("FACTORY_FIXED", "FACTORY_VARIABLE", "QA", "WAREHOUSE", "EXPORT", "OTHER"))
ALLOCATION_BASES = tuple((code, display_label(code)) for code in ("NORMAL_CAPACITY", "MACHINE_HOUR", "LABOR_HOUR", "KG", "UNIT", "BATCH", "PALLET_DAY", "SHIPMENT", "VALUE", "CUSTOM"))
RULE_STATUSES = tuple((code, display_label(code)) for code in ("DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "RETIRED"))
