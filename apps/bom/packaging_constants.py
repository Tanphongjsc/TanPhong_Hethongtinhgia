from apps.master_data.presentation import display_label

CONFIG_FIELDS = ("product", "code", "name", "description", "is_active")
VERSION_FIELDS = ("effective_from", "effective_to", "gross_weight", "weight_uom", "length", "width", "height", "dimension_uom", "change_reason")
LINE_FIELDS = ("packaging_item", "level_code", "qty", "uom", "units_per_parent", "parent_level_code", "market_code", "artwork_code", "display_order", "notes")
ASSIGNMENT_FIELDS = ("sku", "effective_from", "effective_to", "is_primary")
MEASUREMENTS = ("gross_weight", "length", "width", "height")
LEVELS = tuple((code, display_label(code)) for code in ("PRIMARY", "SECONDARY", "TERTIARY", "PALLET", "CONTAINER"))
