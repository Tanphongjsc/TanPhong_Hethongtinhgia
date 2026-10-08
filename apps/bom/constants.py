from apps.master_data.presentation import display_label

RECIPE_FIELDS = ("product", "code", "name", "description", "is_active")
VERSION_FIELDS = ("output_qty", "output_uom", "yield_rate", "effective_from", "effective_to", "change_reason")
LINE_FIELDS = ("component_item", "qty", "uom", "scrap_rate", "operation_code", "substitute_group", "is_optional", "display_order", "notes")
EDITABLE_STATUSES = ("DRAFT", "IN_REVIEW")
IMMUTABLE_STATUSES = ("APPROVED", "EFFECTIVE", "RETIRED")
VERSION_STATUSES = tuple((code, display_label(code)) for code in (*EDITABLE_STATUSES, *IMMUTABLE_STATUSES))
DATE_STATUSES = tuple((code, display_label(code)) for code in ("UNDATED", "FUTURE", "EFFECTIVE", "EXPIRED"))
