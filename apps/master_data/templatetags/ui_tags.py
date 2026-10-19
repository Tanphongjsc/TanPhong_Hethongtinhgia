"""Presentation-only icon mapping; no ORM, permissions or business decisions."""
from django import template

register = template.Library()
SIDEBAR_ICONS = {
    "Lần tính giá thành": "calculator", "Phần tử chi phí": "variable",
    "Nhóm sản phẩm": "folder-tree", "Vật tư / Hàng hóa": "boxes",
    "Sản phẩm": "package", "SKU": "square-stack", "Tiền tệ": "coins",
    "Nhóm đơn vị tính": "layers", "Đơn vị tính": "ruler",
    "Quy đổi đơn vị tính": "arrow-left-right", "Nhà cung cấp": "truck",
    "Giá nhà cung cấp": "receipt", "BOM / Công thức sản xuất": "flask-conical",
    "Cấu hình bao bì": "package", "Trung tâm sản xuất": "factory",
    "Nguồn lực": "cpu", "Đơn giá nguồn lực": "banknote",
    "Quy trình sản xuất": "route", "Nhóm chi phí chung": "layers",
    "Quy tắc phân bổ": "arrow-left-right", "Thiết lập công thức": "code-xml",
    "Phương án tính giá thành": "square-stack", "Kênh bán": "store",
    "Quy tắc phí kênh": "percent", "Quy tắc thuế": "landmark",
    "Tỷ giá": "arrow-left-right", "Kịch bản giá bán": "circle-dollar-sign",
    "So sánh kịch bản": "chart-column",
}


@register.filter
def sidebar_icon(label):
    return SIDEBAR_ICONS.get(str(label), "layers")
