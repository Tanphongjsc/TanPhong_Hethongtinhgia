# Rollout giao diện theo nhóm màn hình

Phạm vi: toàn bộ giao diện hiện có tại baseline `f4e0030`, không thêm module, route hoặc nghiệp vụ. Tất cả màn hình kế thừa shell/tokens/components chung; không cần sửa mỗi full-page wrapper để nhận giao diện mới. Contract và kết quả kiểm thử ở [UI_BASELINE](UI_BASELINE.md) và [REGRESSION_REPORT](REGRESSION_REPORT.md).

## Các đợt triển khai

| Đợt | Phạm vi | Pattern áp dụng | Contract giữ nguyên |
|---|---|---|---|
| 1 | App shell, sidebar, topbar, breadcrumb, page header, shared components | Indigo/Slate, Inter, Lucide, 240/72px navigation, density, controls, feedback | 28 đích/nhãn/thứ tự menu, URLs; không UI tài khoản/công ty |
| 2 | Reference Item list/form, Run/Pricing detail | Table/filter/pagination, sectioned form, metric/metadata/waterfall | Cột, 17 trường Item, labels, nguồn và giá trị kết quả |
| 3 | Danh mục, sản phẩm, nhà cung cấp | Shared reference-data/catalog templates; icon row actions | CRUD, active filters, sorting, pagination, validation, confirmation |
| 4 | BOM, bao bì, trung tâm/nguồn lực/đơn giá, routing, overhead | Data panels, line/operation tables, drawer/modal, history/version badges | Dòng/assignment, effective dates, versioning, editable guards |
| 5 | Công thức và phương án tính giá | Workspace editor/palette/test/validation, source fields và lines | Expression, test inputs/action values, nguồn phụ thuộc, validate/activate |
| 6 | Lần tính giá và truy vết | Metadata, tổng/đơn vị, breakdown, snapshot/trace disclosure | Execution/rerun, Decimal, snapshot/hash/history và Golden |
| 7 | Pricing Foundation, Scenario, Comparison | Metric grid, waterfall, sticky comparison identifier/baseline | Solve/calculate/clone, fee/tax/FX, repeated IDs/query/baseline, delta |

Sau từng nhóm chạy contract audit và các test ứng dụng/browser liên quan; kết thúc chạy full suite. Các lỗi presentation phát hiện được sửa trong CSS/template/UI state, không sửa expected values hay backend.

## 28 đích điều hướng hiện có

Các hàng dùng chung list/form/detail vẫn giữ template và context riêng của backend.

| Nhóm / màn hình | Template/pattern nhận rollout | Luồng kiểm tra |
|---|---|---|
| Lần tính giá thành | `costing/runs/*` | List/create/detail, dependent inputs, trace, snapshot, rerun |
| Phần tử chi phí | `master_data/cost_element_*`, partials chuyên biệt | CRUD/filter/pagination, errors, More/confirmation |
| Nhóm sản phẩm | `product/catalog_*` + reference-data table/form | CRUD/search/active/sort, empty, HTMX |
| Vật tư / Hàng hóa | `product/catalog_*` + reference-data components | Reference list/form, 17 fields, relations, errors |
| Sản phẩm | `product/catalog_*` | CRUD, category/UoM filters, active relations |
| SKU | `product/catalog_*` | CRUD, Product relations, quantity validation |
| Tiền tệ | `master_data/reference_data_*` | CRUD, immutable code editing, decimal places |
| Nhóm đơn vị tính | `master_data/reference_data_*` | CRUD, display mappings, active filters |
| Đơn vị tính | `master_data/reference_data_*` | CRUD/category/base/precision |
| Quy đổi đơn vị tính | `master_data/reference_data_*` | Relations, factor/date validation, HTMX |
| Nhà cung cấp | `master_data/reference_data_*` | CRUD/search/active/duplicate code |
| Giá nhà cung cấp | `master_data/reference_data_*` | Price/date relations, historical display |
| BOM / Công thức sản xuất | `bom/detail`, `line_form`, `version_list`, partials | Header/version/lines, add/edit/remove, clone, immutability |
| Cấu hình bao bì | `bom/packaging/*` | Detail/versions/lines/SKU assignments, drawer |
| Trung tâm sản xuất | Reference-data list/form + resource detail patterns | CRUD, active, related resources |
| Nguồn lực | Reference-data list/form + `bom/resources/detail` | CRUD, work center, type, rate history |
| Đơn giá nguồn lực | Reference-data list/form/detail + rate history | Decimal, effective filters/date validation, history |
| Quy trình sản xuất | `bom/routing/*` | Operations/sequence/assignments, drawer, clone/version |
| Nhóm chi phí chung | Reference-data + `bom/overhead/detail` | CRUD/related allocation history theo schema hiện có |
| Quy tắc phân bổ | Reference-data + `bom/overhead/*` | Driver/target/date configuration, validation |
| Thiết lập công thức | `formula_engine/*` | Editor/palette, validate/test/save/testcase/activate, versions |
| Phương án tính giá thành | `costing/detail`, `line_form`, `validation`, partials | Source selection, lines, validate/activate, versions |
| Kênh bán | `pricing/list`, `form`, `detail` + shared patterns | CRUD/search/active |
| Quy tắc phí kênh | `pricing/list`, `form`, `detail` | Draft/edit/effective/close period và errors |
| Quy tắc thuế | `pricing/list`, `form`, `detail` | Scope/date/percentage/close period |
| Tỷ giá | `pricing/list`, `form`, `detail` | Currency/time/direction, effective validation |
| Kịch bản giá bán | `pricing/scenarios/*` | Run/Product/SKU dependent fields, save/calculate/clone, readonly history |
| So sánh kịch bản | `pricing/comparison/*` | Selection, baseline, repeated query IDs, matrix/snapshot delta |

Không thêm global History/Import/Settings placeholders, user menu hoặc organization selector.

## Phủ full-page templates

Baseline có 38 template dùng `extends` (kể cả shell và error wrapper). Tất cả nhận font/tokens/assets từ base; các wrapper không có nội dung riêng được giữ nguyên.

- Base/layout: `base/error.html`, `layouts/app_shell.html`.
- Master data: ba `cost_element_*` và ba `reference_data_*` list/form/detail.
- Product: `catalog_list.html`, `catalog_form.html`, `catalog_detail.html`.
- BOM: `detail.html`, `line_form.html`, `version_list.html`.
- Packaging: `detail.html`, `line_form.html`.
- Resources/overhead: `resources/detail.html`, `overhead/detail.html`.
- Routing: `detail.html`, `operation_form.html`.
- Formula: `studio.html`, `detail.html`, `versions.html`.
- Scheme: `costing/detail.html`, `line_form.html`, `validation.html`.
- Run: `list.html`, `form.html`, `detail.html`, `trace.html`, `snapshot.html`.
- Pricing Foundation: `list.html`, `form.html`, `detail.html`.
- Scenario: `list.html`, `form.html`, `detail.html`.
- Comparison: `comparison/page.html`.

90 partials giữ nguyên cấu trúc request/response; 16 components cũ được chuẩn hóa, thêm hai include trình bày `icon.html` và `metric.html`.

## Responsive và interaction

| Kích thước | Hành vi |
|---|---|
| 1440 / 1280 | Workspace đầy đủ, bảng scroll riêng nếu nhiều cột, form nhiều cột |
| 992–1279 | Sidebar thu gọn mặc định theo state cũ; rail giữ các liên kết và tooltip |
| 768 | Mobile overlay navigation; form/list/detail dùng chiều rộng sẵn có |
| 390 | Form một cột, toolbar wrap, bảng scroll ngang; không ẩn cột hoặc trường nghiệp vụ |

Gọn/Thoáng chỉ đổi row height/padding và lưu localStorage. Pagination/query không đổi. Sidebar animation chỉ chạy khi người dùng chủ động toggle, tránh che nội dung khi trang vừa render hoặc đổi breakpoint. Hover/focus/tooltip/modal có reduced-motion support.

Validation native và sau HTMX swap giữ dữ liệu, hiển thị lỗi cũ và focus ô `aria-invalid` đầu tiên. Tooltip hoạt động bằng chuột/keyboard và Escape; modal/mobile navigation giữ focus trap/inert. Loading chỉ phản ánh request có sẵn, không sửa payload hoặc endpoint.

## Bằng chứng hình ảnh và phạm vi smoke

`artifacts/ui-redesign/before/` là bản sao screenshot trước rollout; chỉ những ảnh tương ứng các test baseline chạy lại mới là bằng chứng so sánh hiện hành. Các ảnh auth/deployment cũ còn trong kho screenshot không đại diện cho runtime hiện tại và không được dùng để nghiệm thu redesign.

`artifacts/ui-redesign/after/`: Item list, nhóm sản phẩm, Item form, Run detail/snapshot và Pricing detail ở 1440/1280/768/390; collapsed navigation ở 1440. Browser tests cũ tiếp tục xuất ảnh BOM, bao bì, routing, resources, Formula, Scheme, Comparison vào `artifacts/screenshots/`.

Smoke mới duyệt cả 28 đích ở bốn kích thước và các route tạo mới cấp trang ở 1440/390; các luồng cập nhật/chốt/clone/calculation được kiểm tra bởi regression suite hiện có. Đây không phải tuyên bố mọi tổ hợp dữ liệu đều đã được kiểm tra trực quan thủ công.
