"""Field allow-lists and existing PostgreSQL item type vocabulary."""
from apps.master_data.presentation import display_label

# Read from costing.ck_item_type; do not add unrecognized database values.
ITEM_TYPES = tuple((code, display_label(code)) for code in (
    "RAW_MATERIAL", "PACKAGING", "SEMI_FINISHED", "FINISHED_GOOD", "SERVICE", "BY_PRODUCT",
))
CATEGORY_FIELDS = ("code", "name", "description", "is_active")
ITEM_FIELDS = (
    "category", "code", "name", "item_type", "base_uom", "purchase_uom",
    "production_uom", "tax_class_code", "net_weight", "gross_weight", "weight_uom",
    "length", "width", "height", "dimension_uom", "is_stock_item", "is_active",
)
UNIT_FIELDS = ("base_uom", "purchase_uom", "production_uom", "weight_uom", "dimension_uom")
MEASUREMENT_FIELDS = ("net_weight", "gross_weight", "length", "width", "height")
PRODUCT_FIELDS = ("category", "code", "name", "description", "costing_uom", "output_item", "tax_class_code", "is_active")
SKU_FIELDS = ("product", "code", "name", "barcode", "sales_uom", "net_quantity", "net_quantity_uom", "sell_item", "is_active")
PRODUCT_UNIT_FIELDS = ("costing_uom",)
SKU_UNIT_FIELDS = ("sales_uom", "net_quantity_uom")
