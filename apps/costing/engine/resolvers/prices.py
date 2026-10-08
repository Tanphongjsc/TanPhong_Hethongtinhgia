from decimal import Decimal
from apps.core.models import SupplierPrice, ResourceRate
from ..context import ResolvedValue, step
from ..errors import CostingError
from .common import active, bounded, dated


class PriceResolver:
    def __init__(self, ctx, units):
        self.ctx, self.units, self.candidates = ctx, units, {}

    def preload(self, items):
        needed = {item.pk for item in items} - self.candidates.keys()
        if not needed: return
        for pk in needed: self.candidates[pk] = []
        query = dated(SupplierPrice.objects.filter(organization=self.ctx.organization, item_id__in=needed, status="EFFECTIVE", supplier__is_active=True), self.ctx.day)
        for row in bounded(query.select_related("supplier", "item", "price_uom__category", "currency_code").order_by("pk")):
            self.candidates[row.item_id].append(row)

    def cost(self, item, quantity, uom):
        active(self.ctx, item, uom)
        self.preload([item])
        matches, currency_missing = [], False
        for row in self.candidates[item.pk]:
            if row.currency_code_id != self.ctx.currency.pk:
                currency_missing = True
                continue
            amount, conversion = self.units.convert(quantity, uom, row.price_uom, item=item)
            if amount >= row.min_qty: matches.append((row, amount, conversion))
        if len(matches) != 1:
            if not matches and currency_missing:
                raise CostingError(f"Giá vật tư {item.code} khác tiền tệ kết quả; chưa có quy tắc FX được cấu hình.", code="MISSING_FX", stage="supplier_price")
            raise CostingError(f"{'Không tìm thấy' if not matches else 'Có nhiều'} giá nhà cung cấp phù hợp cho vật tư {item.code} tại ngày {self.ctx.day:%d/%m/%Y}. Không tự chọn giá hoặc dùng giá 0.", code="MISSING_PRICE" if not matches else "AMBIGUOUS_PRICE", stage="supplier_price")
        row, amount, conversion = matches[0]
        active(self.ctx, row.supplier, row.price_uom, row.currency_code)
        if row.unit_price < 0: raise CostingError("Đơn giá vật tư không hợp lệ.", stage="supplier_price")
        # Tax treatment has no approved resolver contract yet. Never silently
        # count gross price or recoverable tax as manufacturing cost.
        if row.tax_inclusive or (row.tax_rate not in (None, Decimal(0))):
            raise CostingError(f"Giá vật tư {item.code} có thuế; chưa có quy tắc xử lý thuế mua hàng được xác định.", code="UNSUPPORTED_TAX", stage="supplier_price")
        self.ctx.remember(row)
        cost = amount * row.unit_price
        return ResolvedValue(cost, (*conversion, step(f"Vật tư {item.code} — {item.name}", **{"Giá tham chiếu": row.pk, "Nhà cung cấp": f"{row.supplier.code} — {row.supplier.name}", "Số lượng theo đơn vị giá": amount, "Đơn vị tính giá": row.price_uom.name, "Đơn giá": row.unit_price, "Tiền tệ": row.currency_code_id, "Hiệu lực từ ngày": row.effective_from, "Hiệu lực đến ngày": row.effective_to, "Thành tiền": cost})))


class ResourceRateResolver:
    def __init__(self, ctx, units): self.ctx, self.units, self.candidates = ctx, units, {}

    def preload(self, resources):
        needed = {row.pk for row in resources} - self.candidates.keys()
        if not needed: return
        for pk in needed: self.candidates[pk] = []
        query = dated(ResourceRate.objects.filter(organization=self.ctx.organization, resource_id__in=needed, status="EFFECTIVE"), self.ctx.day)
        for row in bounded(query.select_related("per_uom__category", "currency_code").order_by("pk")): self.candidates[row.resource_id].append(row)

    def cost(self, resource, usage, uom):
        active(self.ctx, resource, resource.work_center)
        self.preload([resource])
        rows = self.candidates[resource.pk]
        if len(rows) != 1:
            raise CostingError(f"{'Không tìm thấy' if not rows else 'Có nhiều'} đơn giá nguồn lực {resource.code} tại ngày tính giá; không có chính sách chọn rate_type.", code="MISSING_RATE" if not rows else "AMBIGUOUS_RATE", stage="resource_rate")
        row = rows[0]
        if row.amount < 0: raise CostingError("Đơn giá nguồn lực không hợp lệ.", stage="resource_rate")
        if row.currency_code_id != self.ctx.currency.pk: raise CostingError("Đơn giá nguồn lực khác tiền tệ kết quả; chưa có quy tắc FX.", code="MISSING_FX", stage="resource_rate")
        active(self.ctx, row.per_uom, row.currency_code)
        quantity, conversion = self.units.convert(usage, uom, row.per_uom)
        self.ctx.remember(row)
        cost = quantity * row.amount
        return ResolvedValue(cost, (*conversion, step(f"Nguồn lực {resource.code} — {resource.name}", **{"Đơn giá tham chiếu": row.pk, "Loại đơn giá": row.rate_type, "Lượng sử dụng": quantity, "Đơn vị tính giá": row.per_uom.name, "Đơn giá": row.amount, "Tiền tệ": row.currency_code_id, "Hiệu lực từ ngày": row.effective_from, "Hiệu lực đến ngày": row.effective_to, "Thành tiền": cost})))
