"""Production resource fields and inspected database codes."""
from apps.master_data.presentation import display_label

RESOURCE_TYPES = tuple((code, display_label(code)) for code in (
    "MACHINE", "LABOR", "WORK_CENTER", "SERVICE",
))
RATE_STATUSES = tuple((code, display_label(code)) for code in (
    "DRAFT", "IN_REVIEW", "APPROVED", "EFFECTIVE", "RETIRED",
))
DATE_STATUSES = tuple((code, display_label(code)) for code in ("EFFECTIVE", "FUTURE", "EXPIRED"))
WORK_CENTER_FIELDS = ("code", "name", "site_code", "capacity_value", "capacity_uom", "normal_capacity_value", "is_active")
RESOURCE_FIELDS = ("code", "name", "resource_type", "work_center", "capacity_value", "capacity_uom", "is_active")
RATE_FIELDS = ("resource", "rate_type", "amount", "currency_code", "per_uom", "effective_from", "effective_to", "source_reference")
