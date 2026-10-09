# AI_CONTEXT.md
## Costing & Pricing Platform — Hướng dẫn tài liệu cho AI/Codex

Tài liệu này là entry point bắt buộc cho AI/Codex trước khi làm việc trên repository.

## 1. Current Architecture — nguồn sự thật hiện tại

Hệ thống Costing là **phần mềm độc lập**.

- **Render deployment preparation 08/10/2026:** target mới là **Render Web Service**,
  Supabase giữ Session pooler/SSL/search_path `costing,public`; `DATABASE_URL` ưu tiên
  toàn bộ legacy `DB_*`, không thay schema/engine/models. Build `bash build.sh`, start
  `gunicorn -c config/gunicorn.py config.wsgi:application`, health `/health/`. Python
  3.11.5/Node 24.11.0 pin trong version files. WhiteNoise/manifest reuse, Render
  managed HTTPS transport riêng với exact hostname/CSRF, không wildcard. Waitress
  giữ cho Windows/portable. Chủ dự án xác nhận chưa có service; chỉ chuẩn bị repo và
  Dashboard, không kết luận đã LIVE. Yêu cầu mới **supersedes** phần "bỏ qua giới hạn
  truy cập" của phase trước: Web Service public + không Auth cần báo access risk,
  kiểm tra plan/hạn chế IP trước dữ liệu nhạy cảm; không tự thêm Auth/Organization.
  Runbook và manifest: [DEPLOYMENT_RENDER.md](DEPLOYMENT_RENDER.md).

- **Deployment preparation 08/10/2026 (phase trước, target mới ở mục trên):** thêm `config.production` (process env,
  DEBUG=False, SSL/search_path costing,public, safe hosts), Waitress + WhiteNoise
  local assets/manifest, `/health/` và `/ready/`, JSON technical logging và guards
  DEMO/migration/test commands. Entry point portable `python -m config.serve`;
  không engine/schema/Golden changes. Khi hoàn thành phase đó chưa có production
  target nên chưa deploy; nội dung bỏ qua giới hạn truy cập của phase đó đã được
  superseded bởi yêu cầu Render mới ở trên.
  Không thêm Auth hoặc organization workflow. Runbook hiện hành ở đầu
  [06_DEPLOYMENT_DEVOPS.md](06_DEPLOYMENT_DEVOPS.md), evidence/gates trong
  [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md). Các mô tả “chưa có app server/
  health/static production” của iteration cũ được superseded; backup/restore thực tế
  và reboot/restart/rollback trên server đích chưa được xác minh.

- **System hardening 08/10/2026:** chỉ sửa lỗi/hồi quy/hiệu năng, không thêm module
  hoặc triển khai hạ tầng. Sidebar chỉ hiện các module đã có route; global History,
  Overrides và Import/Settings placeholders cũ đã bỏ. Version/history và manual
  inputs trong màn hình nghiệp vụ vẫn giữ. CSRF/400/404 có thông báo tiếng Việt;
  danh sách Run không tải snapshot nguồn lớn. Audit dữ liệu chỉ đọc và regression
  toàn hệ thống: [SYSTEM_HARDENING.md](SYSTEM_HARDENING.md).

- **08/10/2026 — kiến trúc hiện tại:** không Approval Workflow/Maker-Checker hoặc
  business Audit Log. `apps/workflow` và `apps/audit` đã gỡ khỏi source/runtime;
  menu phê duyệt/nhật ký thao tác và field chính sách duyệt trong UI phương án đã bỏ.
  Mọi yêu cầu cũ về approver/reviewer/approval/audit nhân sự bên dưới và trong SDLC
  được **superseded**. Core mappings/bảng/actor nullable giữ tương thích DB.
  Versioning, lịch sử, kích hoạt Formula/Scheme, dữ liệu nhập điều chỉnh, effective
  resolution, snapshot/hash/source/explain/trace_id và logging kỹ thuật vẫn giữ.
- **Pricing Foundation** đã triển khai trong `apps/pricing`, namespace `pricing:`,
  `/pricing/channels/`, `/pricing/channel-fee-rules/`, `/pricing/tax-rules/`,
  `/pricing/fx-rates/`: CRUD/HTMX/validation/Decimal và selectors cấu hình.
  Models hiện có Channel/ChannelFeeRule/TaxRule/FxRate, không rule lines/version table.
  Phí/thuế không code/name/UoM; loại phí/cơ sở/thuế/tỷ giá là text tự do, không invent enum.
  UI nhập %, DB giữ phần số. Chỉ sửa Nháp, đưa vào hiệu lực trực tiếp qua validation;
  definition đã chốt chỉ đọc, có thao tác riêng đóng kỳ tương lai cho bản chưa có end.
  Pricing dùng khoảng [start,end); không đổi quy ước Costing upstream cũ.
  Fee/tax selectors trả candidates phù hợp, không tính/chọn winner; FX đúng chiều,
  aware timestamp, thiếu/mơ hồ báo rõ. Không Pricing logic trong Costing Engine.
  Pricing Scenario và Compare đã triển khai. Xem [PRICING_FOUNDATION.md](PRICING_FOUNDATION.md).
- **Scenario Comparison 08/10/2026:** `/pricing/scenarios/compare/`, query GET không
  session/persistence mới. Chọn 2–5 PriceScenario CALCULATED có snapshot schema 1/hash
  hợp lệ; cùng SKU hoặc cùng Product khi tất cả không SKU, cùng output UoM/cơ sở giá.
  Giá trị/fee/tax/FX/trace đọc snapshot, không gọi engine hoặc resolve current rules.
  Decimal delta theo mốc; tiền khác currency chỉ hiển thị, không trừ/quy đổi tự động.
  Product → SKU, search/filter/sort/pagination HTMX giữ repeated scenario IDs trong URL.
  [SCENARIO_COMPARISON.md](SCENARIO_COMPARISON.md) là contract, manifest và test evidence.
- **Pricing Scenario 08/10/2026:** `/pricing/scenarios/`, dùng PriceScenario hiện có,
  base_run → persisted CostingRun LOCKED; không tính lại Costing. Product/SKU qua Run,
  pricing_date/context trong JSON; kết quả/waterfall/sources/trace/hash trong output JSON.
  DRAFT → CALCULATED; lỗi giữ Nháp + diagnostics, không invent FAILED hoặc version table.
  CALCULATED chỉ đọc, calculate lặp lại trả snapshot cũ; nhân bản tạo kịch bản mới.
  Margin = lợi nhuận / giá khách trả, markup = lợi nhuận / giá vốn. Phí cùng type chọn
  SKU > category > general rồi priority DESC, hòa báo lỗi; các type cộng, fixed theo
  một đơn vị Costing output; sàn/trần riêng từng phí. Chỉ LIST_PRICE và phí đã gồm thuế.
  Thuế song song trên giá trước thuế chung; inclusive tách ngược, exclusive cộng vào
  giá niêm yết; mode thuế NONE phải chọn rõ. Missing/unknown basis không fallback 0.
  FX direct, loại nhập rõ, 00:00 ngày định giá giờ Việt Nam; thiếu/trùng báo lỗi.
  Solver Decimal piecewise, tiền 8dp HALF_EVEN; không commercial rounding tự đặt.
  verify_pricing_demo reuse Run DEMO đã khóa, Golden/future delta 0, history/fingerprint
  không đổi. [PRICING_SCENARIO.md](PRICING_SCENARIO.md) là contract hiện tại, supersedes
  các câu “Scenario chưa triển khai” hoặc ví dụ Fee/Tax giản lược cũ.

- Backend: Django
- UI hiện tại sử dụng tiếng Việt; code identifiers, URL names, enum/currency/UoM
  và business technical codes giữ tiếng Anh hoặc mã gốc. Mapping dùng chung tại
  `apps/master_data/presentation.py` và `navigation.py`.
- Đã triển khai Product Category và Item Master tại `apps/product/`, routes
  `/product/categories/` và `/product/items/`. Models vẫn ở `apps/core/models.py`.
  Xem [PRODUCT_CATEGORY_ITEM_VI.md](PRODUCT_CATEGORY_ITEM_VI.md) cho scope/rules/tests.
- Đã triển khai Product và SKU tại `/product/products/`, `/product/skus/`, reuse
  luồng `apps/product/` và UI danh mục. Product dùng `costing_uom`; SKU dùng
  `sales_uom`, `net_quantity`, `net_quantity_uom` (không mặc định lượng là khối lượng).
  `net_quantity > 0` theo CHECK hiện có. Xem [PRODUCT_SKU.md](PRODUCT_SKU.md).
- Database: Supabase PostgreSQL
- Business schema: `costing`
- Frontend: Django Templates + HTMX + Alpine.js + Tailwind CSS
- Business database models: `apps/core/models.py`
- Bộ mẫu và audit tích hợp: `seed_costing_demo` seed atomic một dataset `DEMO_`
  trong công ty hiện có, không ghi đè dữ liệu khác định nghĩa/không reset lịch sử.
  `verify_costing_demo` chạy engine thật, Golden độc lập, giá/rate tương lai,
  persisted history và UI smoke 22 module. Golden 10 hộp ngày 07/10/2026:
  583.000 VND, 58.300 VND/hộp; overhead NORMAL_CAPACITY 530.000 VND / 100 hộp.
  MACHINE/LABOR được đối soát từ trace RESOURCE_COST, không có resolver riêng.
  Công thức/scheme kích hoạt qua service và regression gates; nguồn manufacturing
  mẫu được chốt sau validation trong command, không thêm approval workflow.
  Xem [COSTING_DEMO_AUDIT.md](COSTING_DEMO_AUDIT.md). Task audit không triển khai Pricing.
- Đã triển khai Lần tính giá thành ở `/costing/runs/`, app `costing`: synchronous
  Decimal execution, list/create/detail/trace/snapshot/rerun. Dùng CostingRun và
  CostingRunLine hiện có; DRAFT → CALCULATED → LOCKED hoặc FAILED. Historical detail
  chỉ đọc kết quả/trace/snapshot đã lưu, không resolve current sources. Rerun tạo
  record mới. SYSTEM registry: MATERIAL_COST, PACKAGING_COST, RESOURCE_COST,
  RUN_QUANTITY, ALLOCATION:<rule_code>. NORMAL_CAPACITY cần số liệu kỳ/công suất/
  đơn vị đầu ra rõ ràng; các driver thiếu mẫu số, FX/thuế mua hàng, LOOKUP/EXTERNAL
  hoặc nguồn mơ hồ bị chặn, không đoán hoặc thay 0. Cơ sở bao bì do người chạy nhập;
  qty nguyên liệu × scale / yield / (1 − scrap); setup một lần mỗi Run, run_time theo
  operation.quantity_basis hoặc batch_size. Các câu «chưa resolve/chưa tính Costing»
  trong mô tả iteration upstream bên dưới chỉ nói phạm vi CRUD của iteration đó,
  được superseded ở execution layer này. Xem [COSTING_RUN.md](COSTING_RUN.md).
- Đã triển khai Phương án tính giá thành ở `/costing/schemes/`, app/namespace costing.
  Models hiện có: CostingScheme → CostingSchemeVersion → CostingSchemeLine; dòng
  gán CostElement/FormulaVersion/RuleTable hoặc mã resolver/adapter. Không có Product/
  SKU/BOM/Packaging/Routing/Pool/Allocation assignments, base currency/UoM/quantity
  hoặc selection policy. Không dựng giả. CRUD/HTMX, clone atomic, config validation
  reuse Formula Engine (không evaluate), dependency completeness/cycle và guarded
  activation; APPROVED/EFFECTIVE/RETIRED bất biến theo DB. SYSTEM dùng registry của
  Costing Run; mã chưa đăng ký và LOOKUP/EXTERNAL bị chặn activation. condition_jsonb
  giữ nguyên, không expose. App cấu hình không evaluate hoặc query prices/rates. Xem
  [COSTING_SCHEME.md](COSTING_SCHEME.md) cho scope và giới hạn kiểm tra tại ngày đầu.
- Đã triển khai Formula Engine tại `/formula-engine/formulas/`, app
  `apps/formula_engine/`: Formula/FormulaVersion/FormulaDependency/FormulaTestCase
  unmanaged hiện có. DSL allow-list, AST/hash, type/unit, dependency/cycle,
  iterative Decimal evaluator và Studio/test/trace tiếng Việt. Phiên bản Nháp tạo/clone
  atomic; kích hoạt revalidate và chạy tests, dependency phải EFFECTIVE đúng ngày.
  APPROVED/EFFECTIVE/RETIRED bất biến theo DB. Không RuleTable/LOOKUP hoặc Costing,
  auth/company workflow mới. Xem [FORMULA_ENGINE.md](FORMULA_ENGINE.md) cho DSL,
  giới hạn, lifecycle và khác biệt preview mới nhất so với execution snapshot tương lai.
- Đã triển khai CostPool / AllocationRule tại `/bom/cost-pools/` và
  `/bom/allocation-rules/`, trong `apps/bom/overhead_*`, namespace bom hiện có.
  Pool có pool_type/is_active; rule gắn pool, basis_type + basis_uom tùy chọn,
  formula_code text tùy chọn, priority integer và effective dates/status.
  Không có CostPoolMember/CostElement relation, rule lines, target FK hoặc version
  table; không dựng giả. condition_jsonb giữ nguyên khi edit, không expose raw JSON.
  New rule DRAFT/NULL actor; edit giữ status cũ, DB không có immutable trigger.
  Code unique theo DB, end > start; priority dùng signed integer range hiện có.
  Không overlap policy/resolver, formula execution, CostPoolPeriod amount UI hoặc
  tính phân bổ. Xem [COST_POOL_ALLOCATION_RULE.md](COST_POOL_ALLOCATION_RULE.md).
- Đã triển khai Routing tại `/bom/routings/` trong `apps/bom/routing_*`, reuse
  namespace `bom:`. `Routing → Product`, `RoutingVersion → Routing`,
  `RoutingOperation → RoutingVersion + WorkCenter/primary_resource/Uom`.
  Không có SKU FK hoặc bảng OperationResource; mỗi công đoạn có một nguồn lực
  chính tùy chọn. Version có batch_size/batch_uom và effective dates.
  Thời gian thiết lập/chạy Decimal được lưu riêng, >= 0 theo DB; thời gian khác 0
  cần UoM đại lượng TIME. Sản lượng lô/cơ sở > 0 nếu nhập, kèm đơn vị.
  Thứ tự > 0, unique theo version, gợi ý max + 10. Tạo/clone atomic, clone toàn bộ
  công đoạn sang Nháp; APPROVED/EFFECTIVE/RETIRED bất biến theo trigger hiện có.
  Không duyệt, resolver, overlap policy, snapshot đơn giá hoặc tính production cost.
  Xem [ROUTING.md](ROUTING.md) cho schema, hành vi, kiểm thử và giới hạn.
- Đã triển khai WorkCenter / Resource / ResourceRate tại `/bom/work-centers/`,
  `/bom/resources/`, `/bom/resource-rates/` trong `apps/bom/resource_*`.
  Resource có WorkCenter tùy chọn; loại MACHINE/LABOR/WORK_CENTER/SERVICE theo CHECK.
  Rate dùng amount/currency_code/per_uom/rate_type và effective dates, không có
  version table; amount >= 0, end > start theo DB. Bản mới Nháp/actor NULL.
  Lịch sử đơn giá phân trang ở Resource Detail; chưa có overlap/usage lock/resolver.
  Không auth hoặc organization workflow mới. Xem [WORK_CENTER_RESOURCE_RATE.md](WORK_CENTER_RESOURCE_RATE.md).
- Đã triển khai Supplier và Supplier Price tại `/master-data/suppliers/`,
  `/master-data/supplier-prices/`, reuse CRUD/HTMX danh mục hiện có. Giá mua dùng
  `price_uom`, `currency_code`, `min_qty`, các trường thuế và ngày hiệu lực thực tế.
  Giá mới là `DRAFT`, actor NULL; trạng thái bản ghi và khoảng hiệu lực theo ngày
  hiển thị riêng. DB yêu cầu `effective_to > effective_from`; chưa có policy overlap
  hoặc kiểm tra usage/khóa lịch sử Costing. Xem [SUPPLIER_PRICE.md](SUPPLIER_PRICE.md).
- Đã triển khai Recipe / BOM tại `/bom/` trong `apps/bom/`, dùng các model hiện có
  `Recipe`, `RecipeVersion`, `RecipeLine`. Recipe gắn Product, không có SKU/output
  Item FK riêng; tìm/lọc SKU chỉ tìm định mức của Product tương ứng. Phiên bản mới
  và bản sao là `DRAFT`, actor NULL; clone nguyên cấu hình/thành phần trong transaction.
  `APPROVED`, `EFFECTIVE`, `RETIRED` bất biến theo trigger DB, chỉ tạo bản mới để sửa.
  `DRAFT` và `IN_REVIEW` sửa được; không có thao tác chuyển trạng thái/duyệt trong UI.
  Quy đổi đơn vị khác Item.base_uom kiểm tra cặp trực tiếp ở ngày bắt đầu phiên bản
  hoặc hôm nay, không tính giá/chọn hệ số/resolve chuỗi. Phiên bản mới nhất hiển thị
  không phải resolver phiên bản hiệu lực cho Costing. Xem [RECIPE_BOM.md](RECIPE_BOM.md).
- Database-first; business models dùng `managed = False`
- Đã triển khai Packaging tại `/bom/packaging/` trong `apps/bom/packaging_*`, dùng
  `PackagingConfig`, `PackagingConfigVersion`, `PackagingLine` và `SkuPackagingAssignment`.
  Config gắn Product; SKU gán qua bảng riêng có hiệu lực, không thêm SKU FK lên header.
  Version giữ khối lượng/kích thước/ngày hiệu lực; không có output_qty/output_uom hoặc
  scrap_rate. Lines giữ quantity Decimal, cấp/cấp cha/units_per_parent và Item + Uom.
  Bản mới/clone Nháp; APPROVED/EFFECTIVE/RETIRED khóa theo trigger như Recipe.
  Item PACKAGING được ưu tiên, không tự cấm các loại khác nếu DB không cấm.
  Không tự tính quy mô đầu ra, mở rộng cây, chọn version hay Packaging Cost.
  Xem [PACKAGING_CONFIGURATION.md](PACKAGING_CONFIGURATION.md) cho schema/giới hạn/tests.
- Chế độ hiện tại: **single-company, no authentication** (`APP_MODE=single_company`).
- Không login/logout, Supabase Auth, user session, user permissions hoặc organization UI.
- Company context dùng duy nhất `apps/master_data/company_context.py:get_default_organization`.
  Một organization active được dùng tự động; nhiều organization active cần
  `DEFAULT_ORGANIZATION_ID`; không có/ID không hợp lệ thì báo ConfigurationError.
- `Organization` và `organization_id` chỉ là database compatibility layer;
  `OrganizationMember` được giữ nguyên model/table nhưng không tham gia runtime.
- Access policy nội bộ tập trung trong `apps/master_data/access.py:InternalAccess`.
  Các thao tác đã triển khai có full access; chỉ xóa thành phần BOM/bao bì/công đoạn ở phiên bản
  còn sửa được, có xác nhận. Không hard delete danh mục/header/version hoặc thêm approval.
- Audit actor fields nullable để NULL cho lần tạo/cập nhật trong no-auth mode.
  Không fake UUID, không đổi schema hoặc tạo business migration.
- Quyết định và hướng dẫn hiện tại: [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).
  Mọi nội dung cũ yêu cầu Supabase Auth/membership, multi-tenant, role/grants theo
  user hoặc organization selection trong báo cáo/spec SDLC đã **superseded**.
- Schema `costing` có thể nằm cùng Supabase project/database với `hrm` hoặc schema khác, nhưng **Costing không phụ thuộc HRM về nghiệp vụ hoặc Foreign Key**.

### Precedence rule

Nếu tài liệu cũ có nội dung như:
- tích hợp HRM hiện hữu;
- tham chiếu `hrm."CongTy"`;
- kế thừa trực tiếp database HRM;
- quyết định kiến trúc chỉ để tương thích HRM;

thì các nội dung đó được xem là **superseded/outdated**.

Thứ tự ưu tiên:
1. Source code và database/schema hiện tại.
2. Implementation/spec mới nhất.
3. `AI_CONTEXT.md`.
4. Business Domain.
5. System Architecture.
6. Engineering Guide.
7. Các tài liệu SDLC theo phase.

## 2. Tài liệu AI phải đọc mặc định khi implement feature

### Bắt buộc

1. `02_BUSINESS_DOMAIN.md`
2. `03_SYSTEM_ARCHITECTURE.md`
3. `04_ENGINEERING_GUIDE.md`
4. Feature specification hiện tại, ví dụ `FRONTEND_IMPLEMENTATION_SPEC.md`
5. Source code liên quan trực tiếp:
   - `apps/core/models.py`
   - app đang implement
   - `config/settings.py`
   - `config/urls.py`
   - shared templates/static khi làm frontend

## 3. Tài liệu chỉ đọc theo loại task

### `01_REQUIREMENTS_SCOPE.md`
Đọc khi:
- thay đổi scope;
- tạo feature mới;
- phân tích requirement;
- viết acceptance criteria;
- rà soát FR/NFR;
- lập backlog.

Không bắt buộc cho mọi coding task.

Lưu ý: một số assumption lịch sử về HRM trong tài liệu gốc đã superseded.

### `05_QA_TESTING.md`
Đọc khi:
- viết test plan;
- integration/E2E/security/performance tests;
- QA/UAT;
- regression/golden Excel.

### `06_DEPLOYMENT_DEVOPS.md`
Đọc khi:
- Docker;
- CI/CD;
- staging/production;
- database deployment;
- secrets;
- rollback;
- backup/DR;
- release.

### `07_OPERATIONS_MAINTENANCE.md`
Đọc khi:
- logging/metrics/tracing;
- SLO/SLI;
- incident;
- performance tuning;
- capacity;
- database maintenance;
- production operations.

## 4. Tài liệu không cần AI đọc mặc định

### `00_So_tay_SDLC_Tong_the.docx`
Chỉ là bản đồ tổng thể/stage gate. Nội dung triển khai cụ thể đã nằm ở các tài liệu phase.

### `07_Phu_luc_Bieu_mau_va_Checklist.docx`
Chỉ là template/checklist. Đọc khi cần tạo ADR, RTM, test case, release note, post-mortem, risk register.

### `README_Bo_tai_lieu.txt`
Chỉ là index. Không cần nếu đã có `AI_CONTEXT.md`.

### `Thiet_ke_he_thong_tinh_gia_thanh_linh_hoat.docx`
Là tài liệu tổng hợp Business Blueprint + Architecture, nhưng trùng nhiều với:
- `02_BUSINESS_DOMAIN.md`
- `03_SYSTEM_ARCHITECTURE.md`
- một phần `01_REQUIREMENTS_SCOPE.md`

Để tránh AI đọc nhiều phiên bản của cùng quyết định, **không đọc mặc định**. Giữ làm archive/reference.

## 5. Context tối thiểu theo task

### Frontend CRUD
```text
AI_CONTEXT.md
02_BUSINESS_DOMAIN.md
03_SYSTEM_ARCHITECTURE.md
04_ENGINEERING_GUIDE.md
FRONTEND_IMPLEMENTATION_SPEC.md
apps/core/models.py
app liên quan
```

### Formula Engine
```text
AI_CONTEXT.md
02_BUSINESS_DOMAIN.md
03_SYSTEM_ARCHITECTURE.md
04_ENGINEERING_GUIDE.md
05_QA_TESTING.md
apps/core/models.py
apps/formula_engine/
```

### Costing Engine
```text
AI_CONTEXT.md
02_BUSINESS_DOMAIN.md
03_SYSTEM_ARCHITECTURE.md
04_ENGINEERING_GUIDE.md
05_QA_TESTING.md
apps/core/models.py
apps/costing/
```

### CI/CD / Production
```text
AI_CONTEXT.md
03_SYSTEM_ARCHITECTURE.md
04_ENGINEERING_GUIDE.md
05_QA_TESTING.md
06_DEPLOYMENT_DEVOPS.md
07_OPERATIONS_MAINTENANCE.md
```

## 6. Quy tắc dành cho Codex

Không yêu cầu Codex “đọc tất cả docs”.

Prompt nên nói:

> Đọc `AI_CONTEXT.md` trước. Sau đó chỉ đọc các tài liệu được đánh dấu bắt buộc cho task hiện tại. Không nạp toàn bộ thư mục docs nếu không cần.

Mục tiêu:
- giảm context noise;
- tránh quyết định cũ xung đột quyết định mới;
- tránh trộn HRM với Costing;
- tăng độ nhất quán khi sinh code.

## 7. Định dạng tài liệu

Markdown (`.md`) là format mặc định cho tài liệu AI-facing vì:
- dễ index/search;
- heading rõ;
- diff tốt trong Git;
- AI parse table/code/list tốt;
- ít noise layout Word;
- dễ link chéo.

Dùng thêm:
- YAML: config/rules nhỏ;
- JSON: schema/example payload;
- CSV: mapping/data table;
- Mermaid trong Markdown: architecture/flow/sequence.

Không cần chuyển mọi tài liệu sang JSON/YAML. Business/architecture/coding guide nên giữ Markdown.
