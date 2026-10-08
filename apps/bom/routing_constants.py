"""Field allow-lists for the existing routing schema."""
from .constants import DATE_STATUSES, EDITABLE_STATUSES, IMMUTABLE_STATUSES, VERSION_STATUSES

ROUTING_FIELDS = ("product", "code", "name", "is_active")
VERSION_FIELDS = ("batch_size", "batch_uom", "effective_from", "effective_to", "change_reason")
OPERATION_FIELDS = ("sequence_no", "operation_code", "operation_name", "work_center", "primary_resource",
    "setup_time", "run_time", "time_uom", "quantity_basis", "quantity_uom", "notes")
