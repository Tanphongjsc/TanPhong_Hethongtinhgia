from decimal import Decimal
from apps.core.models import RecipeVersion, RecipeLine, PackagingConfigVersion, PackagingLine, SkuPackagingAssignment, RoutingVersion, RoutingOperation
from ..context import ResolvedValue, step
from ..errors import CostingError
from .common import active, bounded, dated, one


class ManufacturingResolver:
    def __init__(self, ctx, units, prices, rates):
        self.ctx, self.units, self.prices, self.rates = ctx, units, prices, rates

    def output_quantity(self, uom):
        ctx = self.ctx
        if ctx.sku:
            # SKU net quantity is measured per sales unit; its exact master
            # values and both conversions are persisted, never assumed kg.
            count, first = self.units.convert(ctx.quantity, ctx.uom, ctx.sku.sales_uom, item=ctx.sku.sell_item)
            if uom.pk == ctx.sku.sales_uom_id: return count, first
            sale_dimension = ctx.sku.sales_uom.category.dimension_code
            net_dimension = ctx.sku.net_quantity_uom.category.dimension_code
            if uom.category.dimension_code == sale_dimension and sale_dimension != net_dimension:
                quantity, second = self.units.convert(count, ctx.sku.sales_uom, uom, item=ctx.sku.sell_item)
                return quantity, (*first, *second)
            quantity, second = self.units.convert(count * ctx.sku.net_quantity, ctx.sku.net_quantity_uom, uom, item=ctx.product.output_item)
            return quantity, (*first, step("Lượng tịnh của SKU", **{"SKU": ctx.sku.code, "Số đơn vị bán": count, "Lượng tịnh mỗi đơn vị bán": ctx.sku.net_quantity, "Đơn vị lượng tịnh": ctx.sku.net_quantity_uom.name}), *second)
        return self.units.convert(ctx.quantity, ctx.uom, uom, item=ctx.product.output_item)

    def material(self):
        ctx = self.ctx
        version = one(dated(RecipeVersion.objects.filter(recipe__organization=ctx.organization, recipe__product=ctx.product, recipe__is_active=True, status="EFFECTIVE"), ctx.day).select_related("recipe", "output_uom__category"), "định mức nguyên vật liệu")
        active(ctx, version.recipe)
        ctx.remember(version)
        if version.output_qty <= 0 or not Decimal(0) < version.yield_rate <= Decimal(1):
            raise CostingError("Sản lượng hoặc tỷ lệ thu hồi của định mức không hợp lệ.", stage="bom")
        quantity, conversions = self.output_quantity(version.output_uom)
        scale = quantity / version.output_qty
        lines = bounded(RecipeLine.objects.filter(recipe_version=version).select_related("component_item__base_uom__category", "uom__category").order_by("display_order", "pk"))
        if not lines: raise CostingError("Định mức chưa có thành phần.", stage="bom")
        self.prices.preload([row.component_item for row in lines])
        self.units.preload((row.uom_id, price.price_uom_id, row.component_item_id) for row in lines for price in self.prices.candidates[row.component_item_id])
        total, steps = Decimal(0), list(conversions)
        steps.append(step("Quy mô định mức", **{"Định mức": version.recipe.code, "Phiên bản": version.version_no, "Sản lượng chuẩn": version.output_qty, "Sản lượng cần tính": quantity, "Đơn vị": version.output_uom.name, "Hệ số sản lượng": scale, "Tỷ lệ thu hồi": version.yield_rate}))
        for row in lines:
            if row.is_optional or row.substitute_group:
                raise CostingError("Định mức có thành phần tùy chọn/thay thế nhưng chưa có quy tắc chọn thành phần.", code="UNSUPPORTED_SUBSTITUTION", stage="bom")
            if row.qty <= 0 or not Decimal(0) <= row.scrap_rate < Decimal(1): raise CostingError("Số lượng hoặc hao hụt định mức không hợp lệ.", stage="bom")
            active(ctx, row.component_item, row.uom)
            ctx.remember(row)
            adjusted = row.qty * scale / version.yield_rate / (Decimal(1) - row.scrap_rate)
            steps.append(step(f"Nhu cầu vật tư {row.component_item.code}", **{"Số lượng định mức": row.qty, "Hệ số sản lượng": scale, "Tỷ lệ thu hồi": version.yield_rate, "Tỷ lệ hao hụt": row.scrap_rate, "Số lượng sau hao hụt": adjusted, "Đơn vị": row.uom.name}))
            result = self.prices.cost(row.component_item, adjusted, row.uom)
            total += result.value
            steps.extend(result.steps)
        return ResolvedValue(total, tuple(steps))

    def packaging(self):
        ctx = self.ctx
        if not ctx.sku: raise CostingError("Tính bao bì cần chọn SKU.", stage="packaging")
        if ctx.packaging_quantity is None or ctx.packaging_quantity <= 0 or ctx.packaging_uom is None:
            raise CostingError("Vui lòng nhập sản lượng và đơn vị cơ sở đóng gói.", stage="packaging")
        assignment = one(dated(SkuPackagingAssignment.objects.filter(sku=ctx.sku, is_primary=True, packaging_config__organization=ctx.organization, packaging_config__is_active=True, packaging_config__product=ctx.product), ctx.day).select_related("packaging_config"), "cấu hình bao bì chính của SKU")
        config = assignment.packaging_config
        version = one(dated(PackagingConfigVersion.objects.filter(packaging_config=config, status="EFFECTIVE"), ctx.day), "phiên bản bao bì")
        active(ctx, config)
        ctx.remember(assignment, version)
        quantity, conversions = self.units.convert(ctx.quantity, ctx.uom, ctx.packaging_uom, item=ctx.sku.sell_item)
        scale = quantity / ctx.packaging_quantity
        rows = bounded(PackagingLine.objects.filter(packaging_config_version=version).select_related("packaging_item__base_uom__category", "uom__category").order_by("display_order", "pk"))
        if not rows: raise CostingError("Cấu hình chưa có thành phần bao bì.", stage="packaging")
        self.prices.preload([row.packaging_item for row in rows])
        self.units.preload((row.uom_id, price.price_uom_id, row.packaging_item_id) for row in rows for price in self.prices.candidates[row.packaging_item_id])
        total, steps = Decimal(0), list(conversions)
        steps.append(step("Cơ sở đóng gói do người chạy xác định", **{"Cấu hình": config.code, "Phiên bản": version.version_no, "Sản lượng cơ sở": ctx.packaging_quantity, "Đơn vị cơ sở": ctx.packaging_uom.name, "Sản lượng cần tính": quantity, "Hệ số sản lượng": scale}))
        for row in rows:
            active(ctx, row.packaging_item, row.uom)
            if row.qty <= 0: raise CostingError("Số lượng bao bì phải lớn hơn 0.", stage="packaging")
            if row.market_code or row.artwork_code:
                raise CostingError("Bao bì có điều kiện thị trường/mẫu in nhưng Run chưa có bộ chọn điều kiện.", code="UNSUPPORTED_PACKAGING_CONDITION", stage="packaging")
            ctx.remember(row)
            # qty is already the explicit requirement at the provided output
            # basis. Hierarchy is evidence only, not an implicit multiplier.
            required = row.qty * scale
            steps.append(step(f"Nhu cầu bao bì {row.packaging_item.code}", **{"Cấp đóng gói": row.level_code, "Cấp cha": row.parent_level_code, "Số đơn vị mỗi cấp cha": row.units_per_parent, "Số lượng định mức": row.qty, "Số lượng cần dùng": required, "Đơn vị": row.uom.name}))
            result = self.prices.cost(row.packaging_item, required, row.uom)
            total += result.value
            steps.extend(result.steps)
        return ResolvedValue(total, tuple(steps))

    def routing(self):
        ctx = self.ctx
        version = one(dated(RoutingVersion.objects.filter(routing__organization=ctx.organization, routing__product=ctx.product, routing__is_active=True, status="EFFECTIVE"), ctx.day).select_related("routing", "batch_uom__category"), "phiên bản quy trình sản xuất")
        active(ctx, version.routing)
        ctx.remember(version)
        rows = bounded(RoutingOperation.objects.filter(routing_version=version).select_related("primary_resource__work_center", "work_center", "time_uom__category", "quantity_uom__category").order_by("sequence_no", "pk"))
        if not rows: raise CostingError("Quy trình chưa có công đoạn.", stage="routing")
        self.rates.preload([row.primary_resource for row in rows if row.primary_resource])
        self.units.preload((row.time_uom_id, rate.per_uom_id, None) for row in rows if row.primary_resource and row.time_uom_id for rate in self.rates.candidates[row.primary_resource_id])
        total, steps = Decimal(0), []
        for row in rows:
            active(ctx, row.work_center, row.primary_resource, row.time_uom)
            ctx.remember(row)
            if row.setup_time < 0 or row.run_time < 0: raise CostingError("Thời gian công đoạn không được âm.", stage="routing")
            if row.setup_time == 0 and row.run_time == 0:
                steps.append(step(f"Công đoạn {row.operation_code}", **{"Thời gian thiết lập": row.setup_time, "Thời gian chạy": row.run_time, "Lượng sử dụng": Decimal(0)}))
                continue
            if not row.primary_resource or not row.time_uom or row.time_uom.category.dimension_code.upper() != "TIME":
                raise CostingError(f"Công đoạn {row.operation_code} thiếu nguồn lực chính hoặc đơn vị thời gian phù hợp.", stage="routing")
            if row.primary_resource.work_center_id not in (None, row.work_center_id):
                raise CostingError("Nguồn lực không thuộc trung tâm sản xuất của công đoạn.", stage="routing")
            basis, unit = (row.quantity_basis, row.quantity_uom) if row.quantity_basis is not None else (version.batch_size, version.batch_uom)
            quantity, conversion, scale = None, (), Decimal(0)
            if row.run_time > 0:
                if basis is None or basis <= 0 or unit is None:
                    raise CostingError(f"Công đoạn {row.operation_code} thiếu sản lượng cơ sở và đơn vị để tính thời gian.", stage="routing")
                quantity, conversion = self.output_quantity(unit)
                scale = quantity / basis
            usage = row.setup_time + row.run_time * scale
            steps.extend(conversion)
            steps.append(step(f"Công đoạn {row.operation_code} — {row.operation_name}", **{"Trung tâm": row.work_center.name if row.work_center else None, "Thời gian thiết lập một lần": row.setup_time, "Thời gian chạy cơ sở": row.run_time, "Sản lượng cơ sở": basis, "Sản lượng cần tính": quantity, "Hệ số sản lượng": scale, "Thời gian sử dụng": usage, "Đơn vị thời gian": row.time_uom.name}))
            result = self.rates.cost(row.primary_resource, usage, row.time_uom)
            total += result.value
            steps.extend(result.steps)
        return ResolvedValue(total, tuple(steps))
