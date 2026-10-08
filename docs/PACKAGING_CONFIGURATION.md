# Packaging Configuration — báo cáo implementation

Ngày: 07/10/2026. Phạm vi: cấu hình bao bì, phiên bản, thành phần và liên kết SKU
bằng bảng có sẵn. Không triển khai Routing/Resource/Costing/Pricing/Workflow.
Single-company/no-auth, UI tiếng Việt, code/database identifiers giữ tiếng Anh.
Không sửa apps/core/models.py, schema/FK/trigger production hoặc tạo business migration.

## Models, relationships và constraint thật

Đã inspect model và metadata Supabase trong transaction READ ONLY; đối chiếu mọi
column/nullability/character length/numeric precision của 4 models: không mismatch.
Models unmanaged, schema costing theo search_path hiện có.

| Model | Fields thực tế |
| --- | --- |
| PackagingConfig | organization, product, code, name, description, is_active, created_at, updated_at |
| PackagingConfigVersion | packaging_config, version_no, status, effective_from, effective_to, gross_weight, weight_uom, length, width, height, dimension_uom, change_reason, content_hash, created_by, approved_by, created_at, approved_at |
| PackagingLine | packaging_config_version, packaging_item, level_code, qty, uom, units_per_parent, parent_level_code, market_code, artwork_code, display_order, notes |
| SkuPackagingAssignment | sku, packaging_config, effective_from, effective_to, is_primary, created_at |

Config bắt buộc thuộc Product. SKU liên kết Config identity qua SkuPackagingAssignment,
không FK trực tiếp lên Config, không assignment tới một version cụ thể. UI gán SKU
cùng Product/công ty; Product bị giữ cố định khi có assignment hoặc phiên bản chốt.
Item là vật tư master đầu vào; không tạo Item/SKU ngầm. Recipe/BOM và Packaging
là các entity/version/line riêng; không di chuyển các line bao bì đã có trong Recipe.

**Không có output quantity, output UoM, yield hoặc scrap rate ở Packaging.**
Form/list không giả các field này hoặc mặc định lượng cho 1 SKU. Quantity từng line
và units_per_parent giữ độc lập; quy mô đầu ra/normalization Costing cần quyết định
business/database riêng trước khi làm resolver/engine.

Unique:

- uq_packaging_config: organization_id + code.
- uq_packaging_config_version: packaging_config_id + version_no.
- uq_sku_packaging_assignment: sku_id + packaging_config_id + effective_from.
- Không unique Item/level trên PackagingLine; cho phép cùng Item nhiều dòng/cấp.

CHECK:

- Status: DRAFT, IN_REVIEW, APPROVED, EFFECTIVE, RETIRED.
- Ngoài DRAFT/IN_REVIEW cần effective_from.
- Version: effective_to NULL hoặc effective_from NULL hoặc effective_to > effective_from.
- Assignment: effective_to NULL hoặc effective_to > effective_from; effective_from bắt buộc.
- Gross weight và dimensions nếu có phải >= 0.
- Qty > 0; units_per_parent NULL hoặc > 0.
- Level: PRIMARY, SECONDARY, TERTIARY, PALLET, CONTAINER.

Quantity/units/measurement đều Decimal(24,8). Parent_level_code là nullable text,
không enum/FK tới line khác. Không parent uniqueness, overlap hoặc cycle constraint.
DB có index lines theo (packaging_config_version_id, display_order); version unique
index hỗ trợ query bản mới nhất. DB version/line FK cascade, assignment → Config
RESTRICT; không xóa Config/Version/Assignment trong UI. Core mappings giữ DO_NOTHING.

## Features và routes

Dùng `/bom/packaging/` để reuse app/namespace/convention hiện có, không thêm namespace
manufacturing mới. URL names có prefix bom:packaging_.

| Feature | Path | URL name |
| --- | --- | --- |
| List | /bom/packaging/ | bom:packaging_list |
| Tạo Config + phiên bản đầu | /bom/packaging/create/ | bom:packaging_create |
| Detail bản mới nhất | /bom/packaging/&lt;id&gt;/ | bom:packaging_detail |
| Edit header | /bom/packaging/&lt;id&gt;/edit/ | bom:packaging_edit |
| Lịch sử phiên bản | /bom/packaging/&lt;id&gt;/versions/ | bom:packaging_version_list |
| Tạo/clone | /bom/packaging/&lt;id&gt;/versions/create/ | bom:packaging_version_create |
| Version detail | /bom/packaging/&lt;id&gt;/versions/&lt;version_id&gt;/ | bom:packaging_version_detail |
| Version edit | /bom/packaging/&lt;id&gt;/versions/&lt;version_id&gt;/edit/ | bom:packaging_version_edit |
| Add line | …/versions/&lt;version_id&gt;/lines/create/ | bom:packaging_line_create |
| Edit line | …/versions/&lt;version_id&gt;/lines/&lt;line_id&gt;/edit/ | bom:packaging_line_edit |
| Confirm/remove line | …/versions/&lt;version_id&gt;/lines/&lt;line_id&gt;/remove/ | bom:packaging_line_remove |
| Liên kết SKU | /bom/packaging/&lt;id&gt;/skus/ | bom:packaging_assignment_list |
| Gán SKU | /bom/packaging/&lt;id&gt;/skus/create/ | bom:packaging_assignment_create |
| Edit liên kết | /bom/packaging/&lt;id&gt;/skus/&lt;assignment_id&gt;/edit/ | bom:packaging_assignment_edit |

List columns mã/tên/Product/số liên kết SKU/bản mới nhất/status/start/is_active;
không tải lines. Search Config code/name/description, Product code/name và **SKU
đã gán** code/name, dùng EXISTS tránh nhân dòng. Filters Product/SKU/active/status
bản mới nhất/hiệu lực theo ngày. Sort code/name/created_at/effective_from/version.
Pagination 25/50/100 tại DB; search 400ms, hx-push-url, stable PK và whitelist sort.
Lịch sử version phân trang, lọc status/date; assignment list tìm SKU/lọc date/sort/page.
Detail hiển thị 5 liên kết gần nhất, link xem toàn bộ, metadata version và lines phân trang.
Inactive header giữ lịch sử; no hard delete, deactivation qua is_active và xác nhận.

## Versioning, date và transaction

Tạo Config + initial Draft trong transaction. Clone `?source=<version_id>` prefill
toàn bộ VERSION_FIELDS, user có thể đổi metadata/ngày/lý do; clone toàn bộ LINE_FIELDS
cho mọi line, không chỉ trang đang xem. Nguồn cùng Config/công ty; nguồn không đổi.
Config/SKU assignments là identity/relationship chung, không nhân bản identity khi clone.
Version mới luôn DRAFT, created_by/approved_by/approved_at/content_hash NULL.
Chưa có approval/publish/status transitions trong UI.

Khóa Config trước cấp MAX(version_no)+1, serialize create đồng thời. Lock order Config
→ Version → Line/Assignment. Lỗi create/clone rollback toàn bộ. Reload references
trước ghi để không chấp nhận master data vừa inactive/stale. Database unique/FK/CHECK/
P0001 trigger error được map thành thông báo tiếng Việt. Không show SQL/traceback.
Version mất giữa POST xử lý như 404; unexpected dùng middleware trace_id hiện có.

Trigger prevent_approved_version_mutation và protect_packaging_line khóa APPROVED/
EFFECTIVE/RETIRED; service kiểm tra status dưới lock, UI hide submit/line actions.
DRAFT/IN_REVIEW sửa được, edit giữ status gốc. Update quy cách phiên bản/lines clear stale hash
của version còn sửa được, chưa tính/chốt hash. Không sửa Product khi đã gán SKU hoặc
có version chốt; mã/tên/mô tả/is_active header còn chỉnh sửa được.

Date end phải **sau** start (cùng ngày bị DB cấm); form yêu cầu start khi end đã nhập.
Date status computed riêng: Chưa đặt hiệu lực/Sắp hiệu lực/Đang hiệu lực/Hết hiệu lực,
bao gồm ngày kết thúc. Phiên bản mới nhất hiển thị không phải resolver bản áp dụng
cho Costing; assignment có date riêng, gán Config chứ không chọn version.
Chưa có overlap/primary uniqueness policy; không tự cấm nhiều bản hoặc liên kết trùng kỳ.

## Line, Item, hierarchy, UoM

- Qty > 0 dùng Decimal 8 chữ số lẻ, chấp nhận 0.08333333; không ép integer hoặc float.
- Units_per_parent optional, nếu nhập > 0, chấp nhận Decimal; không nhân/chia qty ngầm.
- Dropdown Item cùng công ty/active, ưu tiên PACKAGING đúng enum DB, nhãn code—name—type
  tiếng Việt. Các type khác vẫn chọn được vì không có CHECK business cấm (ví dụ Chocolate).
- UoM mới chỉ active; giữ reference inactive đang gắn khi edit/clone lịch sử, không cho
  chọn một reference inactive khác. Không auto-create UoM/conversion/Item.
- Level code theo CHECK; display mapping chung. Parent dropdown gợi ý các cấp đã biết,
  giữ custom/legacy value theo text field DB; không áp enum constraint mới lên parent.
- Có thể ghi/xem cấp, cấp cha và số đơn vị cấp cha, nhưng không có parent-line FK;
  không dựng cây/recursion/cycle engine, không tự yêu cầu parent phải có line tương ứng.
- Measurement >= 0; weight UoM đại lượng MASS, dimension UoM LENGTH theo pattern Item.
  Khi nhập measurement phải có UoM phù hợp. Không tự thêm conversion dimensions.
- No duplicate Item rule. Thứ tự integer theo DB, không tự cấm âm/trùng.

UoM khác Item.base_uom kiểm tra qua validation dùng chung với Recipe: conversion trực
tiếp hai chiều tại ngày đầu version hoặc hôm nay; company/default hoặc shared, cùng
Item hoặc general cùng category. Item-specific có thể khác category theo thiết kế
UoM hiện có. Một query lookup cho các cặp khi clone; kiểm tra lại khi add/edit line,
đổi ngày đầu version và clone. Không chọn factor/priority/chain hoặc Supplier Price.

## Frontend, reuse và queries

Reuse app shell/page header/breadcrumb/sidebar, ReferenceDataForm/choice/number widgets,
shared table/actions/search/filter/pagination/empty/errors/toasts/status/loading,
form_sections, company_context/InternalAccess, query_helpers/ui_helpers và presentation.
`definition_helpers.py` chứa date annotation/safe PK lookup/table metadata dùng thật
cho cả Recipe và Packaging; không tạo generic CRUD framework.

Line form HTMX dùng reusable drawer: role dialog/aria-modal, focus trap, inert/scroll
lock, Close/Hủy/Escape và restore focus. Invalid POST giữ input/errors/aria; success
retarget table, clear drawer bằng OOB, append toast. Remove là GET confirm + POST
CSRF, editable-only backend/frontend. Full GET/POST fallback có form riêng, không
retarget tới table không tồn tại. Canonical pagination links luôn trỏ version detail.
Normal/history restore full shell; HTMX partial; không đổi convention hiện có.

UI tiếng Việt; numeric căn phải, date dd/mm/yyyy, timestamp dd/mm/yyyy HH:mm; code
font-mono; status text có ý nghĩa ngoài màu. SKU/BOM, pallet và các technical code
giữ theo nghiệp vụ, không đổi identifiers/stored enum. Menu Sản xuất active đúng
Config/version/line/assignment; BOM vẫn active riêng. Mobile table cuộn ngang cục bộ;
drawer không làm tràn viewport, hỗ trợ 1440/1100/800/390px.

Selectors select_related Product, version weight_uom/dimension_uom, line Item/Uom,
assignment SKU/Product. List dùng Subquery latest version/assignment count và EXISTS;
không tải toàn bộ versions/lines/assignments. Tests list <= 7 queries, detail <= 9,
chỉ load 25 lines/5 assignment preview; line references truy cập bằng 1 query.
Không raw SQL runtime, không query membership/auth, không Supplier Price/Costing.

## Files created

- apps/bom/packaging_constants.py, packaging_forms.py, packaging_selectors.py,
  packaging_services.py, packaging_validators.py, packaging_views.py, packaging_urls.py.
- apps/bom/definition_helpers.py.
- apps/bom/test_packaging.py, test_packaging_concurrency.py, test_packaging_browser.py.
- templates/bom/packaging/detail.html, line_form.html.
- templates/bom/packaging/partials/config_rows.html, version_rows.html, assignment_rows.html,
  detail_content.html, lines_table.html, line_editor.html, line_form_content.html, line_saved.html.
- docs/PACKAGING_CONFIGURATION.md.

## Files modified

- apps/bom/urls.py, views.py, selectors.py, testing.py (mount/reuse/test fixture).
- apps/master_data/access.py, context_processors.py, navigation.py, presentation.py, testing.py.
- templates/components/drawer.html (optional initial open), static/js/alpine-components.js.
- static/css/app.css được rebuild qua Tailwind, không chỉnh generated CSS bằng tay.
- docs/00_AI_CONTEXT.md, 03_SYSTEM_ARCHITECTURE.md, FRONTEND_IMPLEMENTATION_SPEC.md,
  PRODUCT_SKU.md, README.md.

Không cài dependencies mới; giữ Django/HTMX/Alpine/Tailwind versions hiện có.
Không sửa config/settings.py hoặc root URL; route Packaging được bổ sung vào app bom
đã mount. Không đổi model/table/migration/credentials. Không xóa file iteration trước.

## Validation evidence

Tests dùng PostgreSQL 17 localhost/test_costing_slice, fixture unmanaged bổ sung 4
models và CHECK/unique/triggers theo metadata thật. DDL có guard host/database, không
thực hiện ở Supabase. Version trigger cùng behavior Recipe, line trigger theo Packaging.
Fixture FK vẫn tạo từ DO_NOTHING, không chứng minh production ON DELETE CASCADE.

- Targeted cuối: 39 tests — 37 form/view/service/DB/query tests, 1 concurrency, 1 browser.
  Tất cả đạt. Full regression cuối: 277 tests trong 92.052s, gồm 7 browser flows,
  tất cả đạt. PostgreSQL test server được dừng sau kiểm thử.
- python manage.py check: đạt, không issue. npm run build:css: đạt (Tailwind 4.3.3).
  AST/UTF-8/conflict markers/trailing whitespace và git diff --check: đạt.
- Coverage: header/list/search/filters/sort/paging/duplicate race/atomic rollback,
  version create/clone toàn bộ lines/nguồn không đổi/invalid date/measurements,
  3 immutable statuses/DB trigger, Decimal fraction, quantities/levels/units,
  inactive create/edit/clone, UoM 2 chiều/date/scope/item-specific/stale references,
  assignment same Product/duplicate/date/inactive/history, cross-company/nested URL,
  CSRF/no auth/audit hidden, HTMX/OOB/fallback/canonical pagination, legacy parent,
  deleted-version race, Vietnamese display/precision/query counts/empty state.
- Browser thật: create/error/assign SKU, drawer add/edit/cancel/remove, focus/Escape/
  restore/inert, clone/history, search/filter/sort/pagination/URL persistence, normal
  POST fallback, responsive widths, no JS error và không session auth.
- Read-only Supabase smoke: / → 302 Cost Element; /bom/packaging/, create, HTMX list,
  BOM, SKU, Supplier Price → 200, không session cookie. DB hiện có 0 Config/Version/
  Line/Assignment; không tạo dữ liệu giả ở DB thật. Writes chỉ kiểm thử local.

Logs: artifacts/packaging-targeted-tests.log, packaging-full-tests.log.
Screenshots: artifacts/screenshots/packaging-detail-desktop.png,
packaging-list-desktop.png, packaging-drawer-mobile.png (gitignored/test data).

## Known limitations / issues cần task riêng

1. Không có quy mô đầu ra/output UoM trong schema Packaging; không giả định 1 SKU.
   Costing normalization sau này cần đặc tả/quyết định riêng, không sửa schema task này.
2. Parent theo level text, không FK tới line; chưa có full hierarchy/cycle/expansion
   engine. Fields chỉ mô tả cấu trúc, không nhân quantity từ units_per_parent.
3. Chưa overlap/primary uniqueness/effective-version resolver hoặc usage lock trên
   SKU assignments; assignment edit có thể đổi lịch sử ngày. Thêm bản ghi mới khi đổi kỳ.
4. New versions Draft, chưa approval/publish/status transition/hash finalization UI.
5. Conversion xác nhận cặp trực tiếp tại một ngày, chưa chain/factor priority/full-period
   coverage. Không tính cost, hao hụt hoặc tích hợp Supplier Price.
6. Trigger DB protect_packaging_line kiểm tra NEW parent khi UPDATE, có thể bị SQL
   ngoài ứng dụng chuyển line từ bản khóa sang Draft mà không xét OLD parent. Service
   không expose parent assignment và luôn khóa/validate version nguồn. Giữ nguyên
   schema/trigger; hardening cần task DB riêng được phép, tương tự phát hiện Recipe.
7. Không chốt/khóa SKU assignment bằng usage Costing vì chưa có engine/usage resolver.

Recommended next slice: Work Center + Resource/Resource Rate theo schema hiện có,
chọn phạm vi cụ thể trước khi implement; chưa triển khai trong iteration này.

## Chạy

```powershell
.\env\Scripts\Activate.ps1
python manage.py check
npm run build:css
python manage.py runserver
```

Mở http://127.0.0.1:8000/bom/packaging/ trực tiếp; terminal thứ hai `npm run dev:css`.
Product/SKU/Item/UoM/conversion cần có sẵn. APP_MODE=single_company và company context
giữ nguyên, DEFAULT_ORGANIZATION_ID chỉ cần khi có nhiều organization active.

```powershell
$env:COSTING_BROWSER_TESTS = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.bom.test_packaging apps.bom.test_packaging_concurrency apps.bom.test_packaging_browser
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```
