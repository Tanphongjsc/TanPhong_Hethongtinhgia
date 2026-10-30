# Ma trận chức năng xóa

Ngày kiểm tra: 21/10/2026. Dự án: `D:/TANPHONGJSC/HeThongTinhGiaThanh/TanPhong_Hethongtinhgia`.

Đã kiểm kê **51 model core**, **28 đích menu**, **38 loại dữ liệu có quyết định tại lớp xóa** (27 loại cấp menu + 11 loại con/phiên bản). Có **36 loại được xóa có điều kiện**, **2 loại giữ lại** (Run và bộ kiểm thử); FormulaDependency chỉ được xóa theo phiên bản nháp sở hữu. 13 model không có endpoint xóa riêng được liệt kê cuối bảng. Màn hình so sánh chỉ đọc, không phải một entity mới.

Chính sách chung: mọi FK, tham chiếu mã và bằng chứng lịch sử được kiểm tra lại khi POST. Bảng dưới không có nghĩa bản ghi đang sử dụng được phép xóa. Xem [DELETE_POLICY](DELETE_POLICY.md).

## Màn hình/entity đang triển khai

URL xóa chung: `GET/POST /master-data/delete/<resource>/<identifier>/`, tên `master_data:record_delete`, view `apps/master_data/deletion_views.py:record_delete`. GET xác nhận chỉ đọc; POST có CSRF. Các URL cũ giữ nguyên.

Tất cả thao tác mới dùng `components/delete_action.html` → `master_data/partials/delete_confirm_content.html` + `delete_form.html`; không HTMX dùng `master_data/delete_confirm.html`. Header dùng chung `layouts/page_header.html`.

| Entity / UI | resource | URL màn hình / điểm thao tác | Template hiện có (dưới templates/) | Chính sách / trạng thái |
|---|---|---|---|---|
| `CostElement` — phần tử chi phí | `cost_element` | `/master-data/cost-elements/<id>/` | `master_data/cost_element_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `Currency` — tiền tệ | `currency` | `/master-data/currencies/<code>/` | `master_data/reference_data_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `UomCategory` — nhóm đơn vị tính | `uom_category` | `/master-data/uom-categories/<id>/` | `master_data/reference_data_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `Uom` — đơn vị tính | `uom` | `/master-data/uoms/<id>/` | `master_data/reference_data_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `UomConversion` — quy đổi đơn vị tính | `uom_conversion` | `/master-data/uom-conversions/<id>/` | `master_data/reference_data_detail.html` | ĐÃ CÓ: không bị cấu hình/quy đổi đang dùng hoặc lịch sử tham chiếu; bản dùng chung chỉ xem. |
| `Supplier` — nhà cung cấp | `supplier` | `/master-data/suppliers/<id>/` | `master_data/reference_data_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `SupplierPrice` — giá nhà cung cấp | `supplier_price` | `/master-data/supplier-prices/<id>/` | `master_data/reference_data_detail.html` | ĐÃ CÓ: chỉ Nháp không bị tham chiếu. |
| `ProductCategory` — nhóm sản phẩm | `product_category` | `/product/categories/<id>/` | `product/catalog_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `Item` — vật tư / hàng hóa | `item` | `/product/items/<id>/` | `product/catalog_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `Product` — sản phẩm | `product` | `/product/products/<id>/` | `product/catalog_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `Sku` — SKU | `sku` | `/product/skus/<id>/` | `product/catalog_detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `Recipe` — định mức nguyên vật liệu | `bom` | `/bom/<id>/` | `bom/partials/detail_content.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `RecipeVersion` — phiên bản định mức | `bom_version` | `/bom/<id>/versions/<version_id>/` | `bom/partials/detail_content.html` | ĐÃ CÓ: Nháp/Chờ duyệt không bị tham chiếu; xóa các dòng sở hữu cùng transaction, giữ hồ sơ cha. |
| `RecipeLine` — thành phần định mức | `bom_line` | `/bom/<id>/versions/<version_id>/lines/<line_id>/remove/` | `bom/partials/detail_content.html` | ĐÃ CÓ: dòng thuộc phiên bản còn được chỉnh sửa; nút xóa dòng cũ và endpoint mới đều kiểm tra ràng buộc. |
| `PackagingConfig` — cấu hình bao bì | `packaging` | `/bom/packaging/<id>/` | `bom/packaging/partials/detail_content.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `PackagingConfigVersion` — phiên bản bao bì | `packaging_version` | `/bom/packaging/<id>/versions/<version_id>/` | `bom/packaging/partials/detail_content.html` | ĐÃ CÓ: Nháp/Chờ duyệt không bị tham chiếu; xóa các dòng sở hữu cùng transaction, giữ hồ sơ cha. |
| `PackagingLine` — thành phần bao bì | `packaging_line` | `/bom/packaging/<id>/versions/<version_id>/lines/<line_id>/remove/` | `bom/packaging/partials/detail_content.html` | ĐÃ CÓ: dòng thuộc phiên bản còn được chỉnh sửa; nút xóa dòng cũ và endpoint mới đều kiểm tra ràng buộc. |
| `SkuPackagingAssignment` — liên kết SKU với bao bì | `packaging_assignment` | `/bom/packaging/<id>/skus/` | `bom/packaging/partials/assignment_rows.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `WorkCenter` — trung tâm sản xuất | `work_center` | `/bom/work-centers/<id>/` | `bom/resources/detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `Resource` — nguồn lực | `resource` | `/bom/resources/<id>/` | `bom/resources/detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `ResourceRate` — đơn giá nguồn lực | `resource_rate` | `/bom/resource-rates/<id>/` | `bom/resources/detail.html` | ĐÃ CÓ: chỉ Nháp không bị tham chiếu. |
| `Routing` — quy trình sản xuất | `routing` | `/bom/routings/<id>/` | `bom/routing/partials/detail_content.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `RoutingVersion` — phiên bản quy trình | `routing_version` | `/bom/routings/<id>/versions/<version_id>/` | `bom/routing/partials/detail_content.html` | ĐÃ CÓ: Nháp/Chờ duyệt không bị tham chiếu; xóa các dòng sở hữu cùng transaction, giữ hồ sơ cha. |
| `RoutingOperation` — công đoạn | `routing_operation` | `/bom/routings/<id>/versions/<version_id>/operations/<line_id>/remove/` | `bom/routing/partials/detail_content.html` | ĐÃ CÓ: dòng thuộc phiên bản còn được chỉnh sửa; nút xóa dòng cũ và endpoint mới đều kiểm tra ràng buộc. |
| `CostPool` — nhóm chi phí chung | `cost_pool` | `/bom/cost-pools/<id>/` | `bom/overhead/detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `AllocationRule` — quy tắc phân bổ | `allocation_rule` | `/bom/allocation-rules/<id>/` | `bom/overhead/detail.html` | ĐÃ CÓ: chỉ Nháp không bị tham chiếu. |
| `Formula` — công thức | `formula` | `/formula-engine/formulas/<id>/` | `formula_engine/partials/detail_content.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `FormulaVersion` — phiên bản công thức | `formula_version` | `/formula-engine/formulas/<id>/versions/<version_id>/` | `formula_engine/partials/detail_content.html` | ĐÃ CÓ: Nháp/Chờ duyệt không bị tham chiếu; xóa các dòng sở hữu cùng transaction, giữ hồ sơ cha. |
| `FormulaTestCase` — bộ kiểm thử công thức | `formula_test` | `/formula-engine/formulas/<id>/test/` | `formula_engine/partials/detail_content.html` | GIỮ LẠI: dùng chung giữa phiên bản; dùng Ngừng sử dụng hiện có. |
| `CostingScheme` — phương án tính giá thành | `scheme` | `/costing/schemes/<id>/` | `costing/partials/detail_content.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `CostingSchemeVersion` — phiên bản phương án | `scheme_version` | `/costing/schemes/<id>/versions/<version_id>/` | `costing/partials/detail_content.html` | ĐÃ CÓ: Nháp/Chờ duyệt không bị tham chiếu; xóa các dòng sở hữu cùng transaction, giữ hồ sơ cha. |
| `CostingSchemeLine` — dòng phương án | `scheme_line` | `/costing/schemes/<id>/versions/<version_id>/lines/<line_id>/remove/` | `costing/partials/detail_content.html` | ĐÃ CÓ: dòng thuộc phiên bản còn được chỉnh sửa; nút xóa dòng cũ và endpoint mới đều kiểm tra ràng buộc. |
| `CostingRun` — lần tính giá thành | `run` | `/costing/runs/<public_id>/` | `costing/runs/detail.html` | GIỮ LẠI: kết quả/khóa chống gửi lặp; backend chặn cả nháp/thất bại. |
| `Channel` — kênh bán | `channel` | `/pricing/channels/<id>/` | `pricing/detail.html` | ĐÃ CÓ: độc lập, không còn dữ liệu con/tham chiếu gây ảnh hưởng; không xóa cascade hồ sơ khác. |
| `ChannelFeeRule` — quy tắc phí kênh | `channel_fee_rule` | `/pricing/channel-fee-rules/<id>/` | `pricing/detail.html` | ĐÃ CÓ: chỉ Nháp không bị tham chiếu. |
| `TaxRule` — quy tắc thuế | `tax_rule` | `/pricing/tax-rules/<id>/` | `pricing/detail.html` | ĐÃ CÓ: chỉ Nháp không bị tham chiếu. |
| `FxRate` — tỷ giá | `fx_rate` | `/pricing/fx-rates/<id>/` | `pricing/detail.html` | ĐÃ CÓ: chỉ Nháp không bị tham chiếu. |
| `PriceScenario` — kịch bản giá bán | `scenario` | `/pricing/scenarios/<id>/` | `pricing/scenarios/detail.html` | ĐÃ CÓ: chỉ Nháp không bị tham chiếu; kịch bản còn phải chưa có kết quả thành công. |

## Quan hệ FK được bảo vệ

Kiểm tra toàn bộ reverse FK từ model core, không chỉ các bảng có màn hình, không lọc bỏ bản ghi inactive/expired. Ngoại lệ sở hữu chỉ áp dụng năm loại version trong OWNED. PostgreSQL vẫn từ chối nếu có ràng buộc phát sinh sau khi kiểm tra.

| Bản ghi cần xóa | Các bảng/trường đang tham chiếu sẽ chặn (hoặc dòng sở hữu được công bố) |
|---|---|
| `CostElement` | `CostingRunLine.cost_element`; `CostingSchemeLine.cost_element`; `Formula.output_element`; `FormulaDependency.depends_on_element` |
| `Currency` | `Channel.default_currency_code`; `ChannelFeeRule.currency_code`; `CostElement.currency_code`; `CostPoolPeriod.currency_code`; `CostingRun.result_currency_code`; `CostingRunLine.currency_code`; `FxRate.from_currency_code`; `FxRate.to_currency_code`; `PriceScenario.currency_code`; `ResourceRate.currency_code`; `RuleRow.currency_code`; `Supplier.default_currency_code`; `SupplierPrice.currency_code`; `TaxRule.currency_code` |
| `UomCategory` | `Uom.category` |
| `Uom` | `AllocationRule.basis_uom`; `CostElement.default_uom`; `CostPoolPeriod.capacity_uom`; `CostingRun.quantity_uom`; `CostingRunLine.quantity_uom`; `Item.base_uom`; `Item.purchase_uom`; `Item.production_uom`; `Item.weight_uom`; `Item.dimension_uom`; `PackagingConfigVersion.weight_uom`; `PackagingConfigVersion.dimension_uom`; `PackagingLine.uom`; `Product.costing_uom`; `RecipeLine.uom`; `RecipeVersion.output_uom`; `Resource.capacity_uom`; `ResourceRate.per_uom`; `RoutingOperation.time_uom`; `RoutingOperation.quantity_uom`; `RoutingVersion.batch_uom`; `RuleRow.uom`; `Sku.sales_uom`; `Sku.net_quantity_uom`; `SupplierPrice.price_uom`; `UomConversion.from_uom`; `UomConversion.to_uom`; `WorkCenter.capacity_uom` |
| `UomConversion` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `Supplier` | `SupplierPrice.supplier` |
| `SupplierPrice` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `ProductCategory` | `ChannelFeeRule.product_category`; `Item.category`; `Product.category`; `ProductCategory.parent` |
| `Item` | `PackagingLine.packaging_item`; `Product.output_item`; `RecipeLine.component_item`; `Sku.sell_item`; `SupplierPrice.item`; `UomConversion.item` |
| `Product` | `CostingRun.product`; `PackagingConfig.product`; `Recipe.product`; `Routing.product`; `Sku.product` |
| `Sku` | `ChannelFeeRule.sku`; `CostingRun.sku`; `SkuPackagingAssignment.sku` |
| `Recipe` | `RecipeVersion.recipe` |
| `RecipeVersion` | `RecipeLine.recipe_version` [dòng sở hữu bản nháp] |
| `RecipeLine` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `PackagingConfig` | `PackagingConfigVersion.packaging_config`; `SkuPackagingAssignment.packaging_config` |
| `PackagingConfigVersion` | `PackagingLine.packaging_config_version` [dòng sở hữu bản nháp] |
| `PackagingLine` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `SkuPackagingAssignment` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `WorkCenter` | `Resource.work_center`; `RoutingOperation.work_center` |
| `Resource` | `ResourceRate.resource`; `RoutingOperation.primary_resource` |
| `ResourceRate` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `Routing` | `RoutingVersion.routing` |
| `RoutingVersion` | `RoutingOperation.routing_version` [dòng sở hữu bản nháp] |
| `RoutingOperation` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `CostPool` | `AllocationRule.pool`; `CostPoolPeriod.pool` |
| `AllocationRule` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `Formula` | `FormulaDependency.depends_on_formula`; `FormulaTestCase.formula`; `FormulaVersion.formula` |
| `FormulaVersion` | `CostingRunLine.formula_version`; `CostingSchemeLine.formula_version`; `FormulaDependency.formula_version` [dòng sở hữu bản nháp]; `RuleRow.formula_version` |
| `FormulaTestCase` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `CostingScheme` | `CostingSchemeVersion.scheme` |
| `CostingSchemeVersion` | `CostingRun.scheme_version`; `CostingSchemeLine.scheme_version` [dòng sở hữu bản nháp] |
| `CostingSchemeLine` | `CostingOverride.scheme_line`; `CostingRunLine.scheme_line` |
| `CostingRun` | `CostingOverride.run`; `CostingRun.supersedes_run`; `CostingRun.compares_to_run`; `CostingRunLine.run`; `PriceScenario.base_run` |
| `Channel` | `ChannelFeeRule.channel`; `CostingRun.channel`; `PriceScenario.channel` |
| `ChannelFeeRule` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `TaxRule` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `FxRate` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |
| `PriceScenario` | Không có reverse FK; vẫn kiểm tra mã/lịch sử/trạng thái. |

## Model không tạo màn hình xóa riêng

| Model | Quyết định |
|---|---|
| FormulaDependency | Chỉ xóa cùng FormulaVersion nháp sở hữu; công thức/phần tử được tham chiếu không bị xóa theo. |
| CostingRunLine, CostingOverride | Giữ cùng Run; không endpoint xóa riêng. Override còn FK đến dòng phương án thì chặn xóa dòng đó. |
| CostElementGroup, CostPoolPeriod | Chưa có màn hình quản lý độc lập; FK từ các bảng này vẫn bảo vệ danh mục/nhóm liên quan. |
| RuleTable, RuleTableVersion, RuleRow | Chưa có CRUD đang chạy. Không mở tính năng mới; quan hệ FK đến Formula/Currency/UoM nếu có vẫn chặn. |
| Organization, OrganizationMember | Mappings tương thích DB, ngoài business flow. Không thêm UI/quyền/xóa hay membership query. |
| ApprovalRequest, ApprovalAction, AuditEvent | Workflow/audit nghiệp vụ đã gỡ. Giữ mappings, không khôi phục runtime hoặc thêm chức năng xóa. |

## Màn hình chỉ đọc và các trường hợp không tạo entity

- So sánh kịch bản: `/pricing/scenarios/compare/`, không persist đối tượng so sánh, không nút Xóa.
- Danh mục tham chiếu công thức: `/formula-engine/catalogue/` theo URL thực tế ở resolver; màn hình chỉ tra cứu, không xóa các mục hệ thống từ đây.
- Lịch sử phiên bản, nguồn dữ liệu, trace và snapshot của Run: chỉ đọc; nút xóa nằm ở chi tiết phiên bản đủ điều kiện, không ở bảng kết quả lịch sử.
- Schema không có OperationResource, CostPoolMember, AllocationTarget/RuleLine riêng. Không dựng entity hoặc ràng buộc giả. RoutingOperation dùng primary_resource; AllocationRule dùng pool, basis_type và formula_code.

## Bằng chứng

Chi tiết kiểm thử, Golden, giới hạn audit baseline và danh sách file trong [DELETE_IMPLEMENTATION_REPORT](DELETE_IMPLEMENTATION_REPORT.md). Không chạy DML hay migration trên Supabase thật.
