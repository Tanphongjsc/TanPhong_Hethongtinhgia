"""Configuration vocabulary mirrors inspected costing CHECK constraints."""
from apps.master_data.presentation import display_label
from apps.master_data.constants import COST_SCOPES, SOURCE_MODES
from apps.bom.constants import VERSION_STATUSES, EDITABLE_STATUSES
from apps.bom.routing_constants import DATE_STATUSES

def choices(codes):
    return tuple((code, display_label(code)) for code in codes)

LINE_TYPES = choices(("INPUT", "CALCULATION", "SUBTOTAL", "OUTPUT", "INFO"))
VISIBILITY_SCOPES = choices(("INTERNAL", "SCREEN", "QUOTE", "REPORT", "ALL"))
SCHEME_FIELDS = ("code", "name", "purpose", "context_scope", "description", "is_active")
VERSION_FIELDS = ("effective_from", "effective_to", "change_reason")
LINE_FIELDS = ("line_code", "label", "line_type", "cost_element", "source_mode",
    "system_resolver_code", "rule_table", "formula_version", "external_adapter_code",
    "editable", "min_override_value", "max_override_value", "override_requires_reason",
    "visibility_scope", "cost_scope", "display_order", "rounding_scale", "notes")
# Legacy metadata remains in exact clones/hashes for historical compatibility.
# It is not accepted from forms or used to require user approval.
COPY_FIELDS = (*LINE_FIELDS[:13], "approval_policy_code", *LINE_FIELDS[13:], "condition_jsonb")
