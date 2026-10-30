"""Explicit deletion scope; existing business mappings remain in core."""
from dataclasses import dataclass
from apps.core import models as m

@dataclass(frozen=True)
class DeleteSpec:
    model: type
    label: str
    list_name: str
    context_key: str = 'record'
    parent: str = ''

SPECS = {
    'cost_element': DeleteSpec(m.CostElement, 'phần tử chi phí', 'master_data:cost_element_list', 'element'),
    'currency': DeleteSpec(m.Currency, 'tiền tệ', 'master_data:currency_list'),
    'uom_category': DeleteSpec(m.UomCategory, 'nhóm đơn vị tính', 'master_data:uom_category_list'),
    'uom': DeleteSpec(m.Uom, 'đơn vị tính', 'master_data:uom_list'),
    'uom_conversion': DeleteSpec(m.UomConversion, 'quy đổi đơn vị tính', 'master_data:uom_conversion_list'),
    'supplier': DeleteSpec(m.Supplier, 'nhà cung cấp', 'master_data:supplier_list'),
    'supplier_price': DeleteSpec(m.SupplierPrice, 'giá nhà cung cấp', 'master_data:supplier_price_list'),
    'product_category': DeleteSpec(m.ProductCategory, 'nhóm sản phẩm', 'product:category_list'),
    'item': DeleteSpec(m.Item, 'vật tư / hàng hóa', 'product:item_list'),
    'product': DeleteSpec(m.Product, 'sản phẩm', 'product:product_list'),
    'sku': DeleteSpec(m.Sku, 'SKU', 'product:sku_list'),
    'bom': DeleteSpec(m.Recipe, 'định mức nguyên vật liệu', 'bom:bom_list', 'recipe'),
    'bom_version': DeleteSpec(m.RecipeVersion, 'phiên bản định mức', 'bom:bom_list', 'version', 'recipe'),
    'bom_line': DeleteSpec(m.RecipeLine, 'thành phần định mức', 'bom:bom_list', 'line', 'recipe_version'),
    'packaging': DeleteSpec(m.PackagingConfig, 'cấu hình bao bì', 'bom:packaging_list', 'config'),
    'packaging_version': DeleteSpec(m.PackagingConfigVersion, 'phiên bản bao bì', 'bom:packaging_list', 'version', 'packaging_config'),
    'packaging_line': DeleteSpec(m.PackagingLine, 'thành phần bao bì', 'bom:packaging_list', 'line', 'packaging_config_version'),
    'packaging_assignment': DeleteSpec(m.SkuPackagingAssignment, 'liên kết SKU với bao bì', 'bom:packaging_list', 'record', 'packaging_config'),
    'work_center': DeleteSpec(m.WorkCenter, 'trung tâm sản xuất', 'bom:work_center_list'),
    'resource': DeleteSpec(m.Resource, 'nguồn lực', 'bom:resource_list'),
    'resource_rate': DeleteSpec(m.ResourceRate, 'đơn giá nguồn lực', 'bom:resource_rate_list'),
    'routing': DeleteSpec(m.Routing, 'quy trình sản xuất', 'bom:routing_list', 'routing'),
    'routing_version': DeleteSpec(m.RoutingVersion, 'phiên bản quy trình', 'bom:routing_list', 'version', 'routing'),
    'routing_operation': DeleteSpec(m.RoutingOperation, 'công đoạn', 'bom:routing_list', 'operation', 'routing_version'),
    'cost_pool': DeleteSpec(m.CostPool, 'nhóm chi phí chung', 'bom:cost_pool_list'),
    'allocation_rule': DeleteSpec(m.AllocationRule, 'quy tắc phân bổ', 'bom:allocation_rule_list'),
    'formula': DeleteSpec(m.Formula, 'công thức', 'formula_engine:formula_list', 'formula'),
    'formula_version': DeleteSpec(m.FormulaVersion, 'phiên bản công thức', 'formula_engine:formula_list', 'version', 'formula'),
    'formula_test': DeleteSpec(m.FormulaTestCase, 'bộ kiểm thử công thức', 'formula_engine:formula_list', 'case', 'formula'),
    'scheme': DeleteSpec(m.CostingScheme, 'phương án tính giá thành', 'costing:scheme_list', 'scheme'),
    'scheme_version': DeleteSpec(m.CostingSchemeVersion, 'phiên bản phương án', 'costing:scheme_list', 'version', 'scheme'),
    'scheme_line': DeleteSpec(m.CostingSchemeLine, 'dòng phương án', 'costing:scheme_list', 'line', 'scheme_version'),
    'run': DeleteSpec(m.CostingRun, 'lần tính giá thành', 'costing:run_list', 'run'),
    'channel': DeleteSpec(m.Channel, 'kênh bán', 'pricing:channel_list'),
    'channel_fee_rule': DeleteSpec(m.ChannelFeeRule, 'quy tắc phí kênh', 'pricing:channel_fee_rule_list'),
    'tax_rule': DeleteSpec(m.TaxRule, 'quy tắc thuế', 'pricing:tax_rule_list'),
    'fx_rate': DeleteSpec(m.FxRate, 'tỷ giá', 'pricing:fx_rate_list'),
    'scenario': DeleteSpec(m.PriceScenario, 'kịch bản giá bán', 'pricing:scenario_list'),
}
MODEL_SPECS = {spec.model: (key, spec) for key, spec in SPECS.items()}
LABELS = {spec.model: spec.label for spec in SPECS.values()}
LABELS.update({m.FormulaDependency: 'quan hệ phụ thuộc công thức', m.CostingRunLine: 'dòng kết quả tính giá',
    m.CostingOverride: 'dữ liệu điều chỉnh lần tính', m.CostPoolPeriod: 'số liệu kỳ chi phí chung',
    m.RuleRow: 'dòng bảng quy tắc', m.RuleTableVersion: 'phiên bản bảng quy tắc',
    m.RuleTable: 'bảng quy tắc', m.CostElementGroup: 'nhóm phần tử chi phí'})
OWNED = {m.RecipeVersion: (m.RecipeLine,), m.PackagingConfigVersion: (m.PackagingLine,),
    m.RoutingVersion: (m.RoutingOperation,), m.FormulaVersion: (m.FormulaDependency,),
    m.CostingSchemeVersion: (m.CostingSchemeLine,)}
EDITABLE = frozenset(('DRAFT', 'IN_REVIEW'))
PARENT_STATUS = {m.RecipeLine: 'recipe_version', m.PackagingLine: 'packaging_config_version',
    m.RoutingOperation: 'routing_version', m.CostingSchemeLine: 'scheme_version'}
DRAFT_ONLY = (m.SupplierPrice, m.ResourceRate, m.AllocationRule, m.ChannelFeeRule, m.TaxRule, m.FxRate, m.PriceScenario)
DETAIL_RESOURCES = {spec.list_name.removesuffix('_list') + '_detail': key
    for key, spec in SPECS.items() if key not in ('bom_line','packaging_line','routing_operation','scheme_line','packaging_assignment','formula_test') and not key.endswith('_version')}
DETAIL_RESOURCES.update({'bom:bom_version_detail':'bom_version','bom:packaging_version_detail':'packaging_version',
    'bom:routing_version_detail':'routing_version','formula_engine:formula_version_detail':'formula_version',
    'costing:scheme_version_detail':'scheme_version'})

def state_blocker(record):
    if isinstance(record, m.CostingRun):
        return 'Không thể xóa lần tính giá thành đã lưu. Kết quả và khóa chống gửi lặp cần được bảo toàn, kể cả lần tính thất bại.'
    if isinstance(record, m.FormulaTestCase):
        return 'Bộ kiểm thử dùng chung cho các phiên bản công thức. Hãy dùng thao tác Ngừng sử dụng để giữ lịch sử.'
    if type(record) in OWNED and record.status not in EDITABLE:
        return 'Không thể xóa phiên bản đã chốt. Hãy giữ lịch sử và tạo phiên bản mới khi cần thay đổi.'
    if isinstance(record, DRAFT_ONLY) and record.status != 'DRAFT':
        return 'Không thể xóa dữ liệu đã chốt hoặc đã có kết quả tính toán.'
    parent = PARENT_STATUS.get(type(record))
    if parent and getattr(record, parent).status not in EDITABLE:
        return 'Không thể xóa thành phần của phiên bản đã chốt.'
    if isinstance(record, m.PriceScenario) and isinstance(record.output_snapshot_jsonb, dict) and record.output_snapshot_jsonb.get('result'):
        return 'Không thể xóa kịch bản đã có kết quả tính giá bán được lưu.'
    if isinstance(record,m.PriceScenario) and record.output_snapshot_jsonb:
        output=record.output_snapshot_jsonb
        if not isinstance(output,dict) or output.get('schema') != 1 or not isinstance(output.get('errors'),list):
            return 'Không thể xóa vì dữ liệu kết quả cũ chưa đủ thông tin để xác định an toàn.'
    return ''