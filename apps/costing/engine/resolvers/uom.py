from decimal import Decimal
from django.db.models import Q
from apps.core.models import UomConversion
from ..context import step
from ..errors import CostingError
from .common import active, bounded, dated


class UomResolver:
    def __init__(self, ctx):
        self.ctx = ctx
        self.candidates = {}

    @staticmethod
    def key(source_id, target_id, item_id):
        return (*sorted((source_id, target_id)), item_id)

    def preload(self, requests):
        """Batch only required pairs and item scopes; never scan the whole table."""
        needed = {self.key(source, target, item) for source, target, item in requests if source != target} - self.candidates.keys()
        if not needed: return
        condition = Q(pk__in=[])
        for source, target, item in sorted(needed, key=str):
            pair = Q(from_uom_id=source, to_uom_id=target) | Q(from_uom_id=target, to_uom_id=source)
            scope = Q(item__isnull=True) | Q(item_id=item) if item is not None else Q(item__isnull=True)
            condition |= pair & scope
        rows = bounded(dated(UomConversion.objects.filter(condition).filter(Q(organization=self.ctx.organization) | Q(organization__isnull=True)), self.ctx.day).order_by("pk"))
        for source, target, item in needed:
            self.candidates[(source, target, item)] = [row for row in rows if row.item_id in (None, item) and {row.from_uom_id, row.to_uom_id} == {source, target}]

    def convert(self, quantity, source, target, *, item=None):
        if source is None or target is None: raise CostingError("Thiếu đơn vị tính để quy đổi.", code="MISSING_CONVERSION", stage="conversion")
        active(self.ctx, source, target, source.category, target.category)
        if source.pk == target.pk: return quantity, ()
        item_id = getattr(item, "pk", None)
        self.preload(((source.pk, target.pk, item_id),))
        # No guessed specificity/fallback or chain. Competing global, item or
        # inverse records are ambiguous until an explicit policy exists.
        candidates = self.candidates[self.key(source.pk, target.pk, item_id)]
        if len(candidates) != 1:
            text = "Không tìm thấy" if not candidates else "Có nhiều"
            raise CostingError(f"{text} quy đổi đơn vị từ {source.name} sang {target.name}" + (f" cho vật tư {item.code}." if item else "."), code="MISSING_CONVERSION" if not candidates else "AMBIGUOUS_CONVERSION", stage="conversion")
        row = candidates[0]
        if row.factor <= 0: raise CostingError("Hệ số quy đổi không hợp lệ.", stage="conversion")
        if source.category.dimension_code != target.category.dimension_code and row.item_id is None:
            raise CostingError("Quy đổi khác đại lượng cần cấu hình riêng theo vật tư.", stage="conversion")
        factor = row.factor if row.from_uom_id == source.pk else Decimal(1) / row.factor
        self.ctx.remember(row)
        return quantity * factor, (step("Quy đổi đơn vị", **{"Mã tham chiếu": row.pk, "Đơn vị nguồn": source.name, "Đơn vị đích": target.name, "Hệ số đã sử dụng": factor, "Số lượng đầu vào": quantity, "Số lượng quy đổi": quantity * factor}),)
