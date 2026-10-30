"""Configured conversion dependencies only; no calculation or rate selection."""
from django.db.models import F, Q
from apps.core import models as m


def _pair(left, right, units):
    return Q(**{left+'__in':units,right+'__in':units}) & ~Q(**{left:F(right)})


def _output_uses(query, product, target, conversion):
    """Declared product/SKU output units, matching the existing resolver branches."""
    units=(conversion.from_uom_id,conversion.to_uom_id)
    prefix=product+'__' if product else ''
    plain=query.filter(_pair(prefix+'costing_uom_id',target+'_id',units))
    if conversion.item_id: plain=plain.filter(**{prefix+'output_item_id':conversion.item_id})
    if plain.exists(): return True
    sku=prefix+'sku__'
    sale,net=sku+'sales_uom',sku+'net_quantity_uom'
    sale_branch=Q(**{target+'__category__dimension_code':F(sale+'__category__dimension_code')}) & ~Q(**{sale+'__category__dimension_code':F(net+'__category__dimension_code')})
    sale_rows=query.filter(sale_branch & _pair(sale+'_id',target+'_id',units))
    net_rows=query.filter(~sale_branch & ~Q(**{target+'_id':F(sale+'_id')}) & _pair(net+'_id',target+'_id',units))
    if conversion.item_id:
        sale_rows=sale_rows.filter(**{sku+'sell_item_id':conversion.item_id})
        net_rows=net_rows.filter(**{prefix+'output_item_id':conversion.item_id})
    return sale_rows.exists() or net_rows.exists()


def _declared_output_uses(unit, conversion):
    """Global scheme/period targets can apply to any product in this company."""
    units=(conversion.from_uom_id,conversion.to_uom_id)
    opposite=units[1] if unit.pk == units[0] else units[0]
    products=m.Product.objects.filter(organization_id=conversion.organization_id,costing_uom_id=opposite)
    skus=m.Sku.objects.filter(organization_id=conversion.organization_id).exclude(sales_uom=unit)
    sale_branch=Q(sales_uom__category__dimension_code=unit.category.dimension_code) & ~Q(sales_uom__category__dimension_code=F('net_quantity_uom__category__dimension_code'))
    sale_rows=skus.filter(sale_branch,sales_uom_id=opposite)
    net_rows=skus.filter(~sale_branch,net_quantity_uom_id=opposite)
    if conversion.item_id:
        products=products.filter(output_item_id=conversion.item_id)
        sale_rows=sale_rows.filter(sell_item_id=conversion.item_id)
        net_rows=net_rows.filter(product__output_item_id=conversion.item_id)
    return products.exists() or sale_rows.exists() or net_rows.exists()


def used_conversion_reason(record):
    units=(record.from_uom_id,record.to_uom_id)
    for model,item,owner in ((m.RecipeLine,'component_item','recipe_version__recipe'),(m.PackagingLine,'packaging_item','packaging_config_version__packaging_config')):
        rows=model.objects.filter(**{owner+'__organization_id':record.organization_id})
        if record.item_id: rows=rows.filter(**{item+'_id':record.item_id})
        if rows.filter(_pair('uom_id',item+'__base_uom_id',units)).exists():
            return 'Không thể xóa quy đổi vì định mức hoặc bao bì đang dùng cặp đơn vị này với đơn vị cơ sở của vật tư.'
        prices=rows.filter(**{item+'__supplierprice__organization_id':record.organization_id})
        if prices.filter(_pair('uom_id',item+'__supplierprice__price_uom_id',units)).exists():
            return 'Không thể xóa quy đổi vì định mức hoặc bao bì cần quy đổi sang đơn vị của giá nhà cung cấp.'
    operations=m.RoutingOperation.objects.filter(routing_version__routing__organization_id=record.organization_id)
    if record.item_id is None and operations.filter(_pair('time_uom_id','primary_resource__resourcerate__per_uom_id',units)).exists():
        return 'Không thể xóa quy đổi đơn vị thời gian đang được công đoạn và đơn giá nguồn lực sử dụng.'
    targets=(
        (m.RecipeVersion.objects.filter(recipe__organization_id=record.organization_id),'recipe__product','output_uom'),
        (m.RoutingVersion.objects.filter(routing__organization_id=record.organization_id,routingoperation__quantity_basis__isnull=True),'routing__product','batch_uom'),
        (operations.filter(quantity_basis__isnull=False),'routing_version__routing__product','quantity_uom'),
    )
    for rows,product,target in targets:
        if _output_uses(rows,product,target,record):
            return 'Không thể xóa quy đổi vì đơn vị sản lượng của sản phẩm/SKU và định mức hoặc công đoạn còn cần cặp đơn vị này.'
    periods=m.CostPoolPeriod.objects.filter(pool__organization_id=record.organization_id,capacity_uom_id__in=units,pool__allocationrule__isnull=False)
    quantities=m.CostingSchemeLine.objects.filter(scheme_version__scheme__organization_id=record.organization_id,source_mode='SYSTEM',system_resolver_code='RUN_QUANTITY',cost_element__default_uom_id__in=units)
    for unit in m.Uom.objects.filter(pk__in=units).select_related('category'):
        if (periods.filter(capacity_uom=unit).exists() or quantities.filter(cost_element__default_uom=unit).exists()) and _declared_output_uses(unit,record):
            return 'Không thể xóa quy đổi vì đơn vị sản lượng còn được phương án tính giá hoặc cơ sở phân bổ sử dụng.'
    return ''