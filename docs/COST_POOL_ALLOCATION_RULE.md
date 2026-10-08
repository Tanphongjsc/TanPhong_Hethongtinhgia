# Nhóm chi phí chung và quy tắc phân bổ

Iteration ngày 07/10/2026, chỉ quản lý cấu hình. Canonical documents hiện ở `docs/`,
không có `docs/ai/`. Đã đọc context/domain/architecture/engineering/spec và QA liên quan.
Giữ single-company/no-auth, business models unmanaged ở core; company FK chỉ dùng
compatibility helper hiện có, không tạo organization UI/workflow hoặc membership.

## Schema thực tế

Metadata PostgreSQL được inspect READ ONLY; không đổi model, schema, FK hoặc migration.

| Model | Fields / quan hệ |
|---|---|
| CostPool | id, organization, code, name, pool_type, description nullable, is_active, created_at, updated_at |
| AllocationRule | id, organization, pool FK CostPool, code, name, basis_type, basis_uom FK Uom nullable, formula_code text nullable, priority integer default 100, effective_from/to, status default DRAFT, condition_jsonb default {}, created_by UUID nullable, created_at |
| CostPoolPeriod | pool FK, period_start/end, amount/currency, normal_capacity/capacity_uom, status, source_reference, actor/timestamp; có trong core/DB nhưng không thuộc CRUD iteration này |

Không có CostPoolMember/AllocationRuleLine/AllocationDriver/AllocationTarget hoặc
version tables. **Không có quan hệ CostPool → CostElement**; không tạo phần tử chi
phí mới, relation giả hoặc map JSON để thay thế một bảng còn thiếu. CostPool detail
hiển thị quy tắc liên quan, không giả số thành phần chi phí.

Rule không có Product/SKU/WorkCenter/Resource/Routing/Operation/Category target FK,
target_type/id, percentage, weight/factor hoặc is_active. condition_jsonb chưa có
cấu trúc target được canonical docs/schema định nghĩa; new rule dùng {}, edit giữ
nguyên giá trị đang lưu và chỉ hiển thị thông tin có/không điều kiện bổ sung. Không
expose raw JSON hoặc IDs, không tự tạo condition language/dependent target dropdown.

formula_code là mã text, không FK Formula/FormulaVersion. Form trim và giữ case;
không yêu cầu có công thức tương ứng, không parse/evaluate hoặc tạo Formula Engine.

## Enum và constraints

pool_type CHECK gồm:

| Stored code | Nhãn |
|---|---|
| FACTORY_FIXED | Chi phí cố định nhà máy |
| FACTORY_VARIABLE | Chi phí biến đổi nhà máy |
| QA | Đảm bảo chất lượng |
| WAREHOUSE | Kho vận |
| EXPORT | Xuất khẩu |
| OTHER | Khác |

basis_type CHECK gồm:

| Stored code | Nhãn |
|---|---|
| NORMAL_CAPACITY | Công suất bình thường |
| MACHINE_HOUR | Giờ máy |
| LABOR_HOUR | Giờ lao động |
| KG | Khối lượng (kg) |
| UNIT | Số đơn vị |
| BATCH | Số lô |
| PALLET_DAY | Ngày lưu pallet |
| SHIPMENT | Số chuyến hàng |
| VALUE | Giá trị |
| CUSTOM | Tùy chỉnh |

Không dùng MACHINE_HOURS/LABOR_HOURS/FIXED_PERCENTAGE từ ví dụ prompt. UI choices
và display dùng một mapping tại `apps/master_data/presentation.py`, code giữ nguyên.
Rule status CHECK: DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/RETIRED, nhãn shared hiện có.

- `uq_cost_pool`, `uq_allocation_rule`: organization + code, không phải pool + code.
- `ck_cost_pool_type`, `ck_allocation_basis`, `ck_allocation_rule_status` bảo vệ codes.
- `ck_allocation_rule_period`: effective_to NULL hoặc **> effective_from**.
- priority signed integer 32-bit, **không có CHECK >= 0**; dùng đúng range DB.
- Có updated_at trigger trên CostPool; không có immutable/version/overlap trigger
  trên AllocationRule và không incoming FK tới rule.
- Actor FK cũ tới auth.users được giữ nguyên schema; no-auth runtime để actor NULL,
  không gọi Supabase Auth hoặc tạo system UUID.

## Features và kiến trúc

Nằm ở `apps/bom/overhead_*`, namespace `bom:` theo manufacturing boundary của
Recipe/Packaging/Resource/Routing hiện có. Không chuyển module running hoặc đặt
configuration vào app execution engine `apps/costing/` đang là stub.

Routes:

```text
/bom/cost-pools/
/bom/cost-pools/create/
/bom/cost-pools/<id>/
/bom/cost-pools/<id>/edit/
/bom/allocation-rules/
/bom/allocation-rules/create/
/bom/allocation-rules/<id>/
/bom/allocation-rules/<id>/edit/
```

Names `bom:cost_pool_{list,create,detail,edit}` và
`bom:allocation_rule_{list,create,detail,edit}`. Sidebar giữ vị trí sau Routing,
nhãn tiếng Việt và active state cả CRUD pages.

CostPool có list/search code/name/description, filter pool_type/is_active, sort
code/name/created_at, pagination 25/50/100, create/detail/edit/deactivate, empty state.
Detail hiển thị quy tắc của nhóm, có search/filters/sort/pagination ở DB và CTA thêm
rule preselected pool khi active. Không hard delete Pool/Rule hoặc CRUD period amount.

Rule list/search code/name/pool code/name; filters pool/basis_type/basis_uom/status/
effective status; sort code/name/priority/effective_from/created_at; pagination như
trên. Detail có pool, driver/unit/formula reference/priority/dates, riêng status và
date status; linked Pool detail. Form chia thông tin chung/cơ sở phân bổ/hiệu lực.

Request → View → Form → Service/Selector → existing core models → PostgreSQL.
Services atomic, write allow-list loại bỏ organization/status/actor/conditions;
edit refresh/lock record, then pool and unit, validate latest active/scope before
persist. Database IntegrityError chuyển sang lỗi tiếng Việt theo constraint; lỗi
unexpected do handler hiện có xử lý với trace ID, không SQL/traceback UI production.

## Validation / lịch sử

- code bắt buộc, trim + uppercase; name trim, bắt buộc; unique theo constraint.
- pool_type/basis_type đúng CHECK; pool required cùng internal company context.
- Pool/Uom active khi chọn mới; dropdown Mã — Tên / Tên (ký hiệu). Reference inactive
  hiện có vẫn render/giữ được khi edit; không chọn mới sang danh mục inactive khác.
- basis_uom/formula_code optional theo DB. Không tự invent dimensional mapping
  driver ↔ UoM, CUSTOM → required formula hay conversion/calculation logic.
- effective_from bắt buộc; end > start; hiệu lực theo ngày hiển thị FUTURE/EFFECTIVE/
  EXPIRED bằng ngày local, end date inclusive theo convention hiện có.
- priority trong -2147483648..2147483647, không boolean/noninteger; không tự áp
  chính sách ưu tiên thấp/cao, resolver sẽ định nghĩa sau.
- **Không có version system/immutable trigger trên rule.** New rule DRAFT/NULL actor;
  edit giữ status/created_at/actor/condition_jsonb. Generic version assumptions của
  tài liệu cũ không tự áp dụng cho bảng rule này.
- Form nhắc thêm rule với **mã khác** cho kỳ mới để giữ row cũ; edit cập nhật trực
  tiếp row hiện tại. Không khóa effective rule/usage khi DB/business chưa định nghĩa.
- Không invent overlap exclusion, percentage sum, weight normalization hoặc target
  resolution. Có thể tồn tại nhiều rule trùng pool/date với code khác theo DB.

## HTMX, accessibility và performance

Shared reference list/form/table/filters/search/status/toast/confirmation được reuse.
Search debounce 400ms; server-side filters/sort/pagination, hx-push-url giữ state.
Normal request full page; HTMX partial; history restore full page. Pool detail có
một table/filter form với ID đúng pattern shared JS, update riêng table bằng HTMX.
Invalid input giữ form/errors + aria-invalid/describedby; CSRF được enforce; không
user session. Breadcrumb aria-label được đổi sang «Điều hướng trang».

CostPool Count liên quan được annotate ở DB với scope rõ; Rule select_related pool,
basis_uom và date Case annotation; không N+1. Không prefetch members/targets không
tồn tại; không query CostElement/CostPoolPeriod/ResourceRate/CostingRun để tính chi phí.
Active-only dropdown create, filter giữ inactive master để tìm lịch sử.

## Files

Tạo:

- `apps/bom/overhead_constants.py`, `overhead_validators.py`, `overhead_forms.py`,
  `overhead_services.py`, `overhead_selectors.py`, `overhead_views.py`, `overhead_urls.py`.
- `apps/bom/test_overhead.py`, `test_overhead_concurrency.py`, `test_overhead_browser.py`.
- `templates/bom/overhead/detail.html`; partials `cost_pool_rows.html`,
  `allocation_rule_rows.html`, `detail_content.html`, `rule_history.html`.
- `docs/COST_POOL_ALLOCATION_RULE.md`.

Sửa:

- `apps/bom/urls.py`; `apps/master_data/access.py`, `navigation.py`, `presentation.py`,
  `testing.py` (fixtures chỉ localhost guarded test DB).
- `templates/layouts/breadcrumbs.html` (nhãn aria tiếng Việt).
- `docs/00_AI_CONTEXT.md`, `03_SYSTEM_ARCHITECTURE.md`, `FRONTEND_IMPLEMENTATION_SPEC.md`.
- `README.md`, generated `static/css/app.css` qua build, không sửa tay.

Không dependency mới; không chỉnh core models/settings hoặc app auth/migrations.

## Kiểm thử

```powershell
python manage.py check
npm run build:css
$env:COSTING_BROWSER_TESTS = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.bom.test_overhead apps.bom.test_overhead_concurrency apps.bom.test_overhead_browser
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

Coverage CRUD/search/type-active-status-effective filters/sort/pagination/history,
empty/HTMX/history restore/form partial/CSRF/no-session/no-membership, preserve JSON/
status/actor/history, stale and inactive references, real CHECKs/FKs/uniques, database
error mapping/rollback, no unsupported fields/routes, query counts vs table size.
Threaded race tests force two validations before insert to exercise actual unique
constraints and friendly duplicate messages; rule code unique across different Pools.
Browser flow verifies forms/errors/history/preselected Pool/filters/sort/pagination/
query reload/deactivate confirmation/desktop-mobile/responsive/no JavaScript errors.

Kết quả 07/10/2026:

- `python manage.py check`: PASS, không có lỗi.
- `npm run build:css`: PASS, Tailwind 4.3.3 local production build, không thêm dependency.
- Targeted suite: **37 tests PASS** (34 integration/query cases, 2 concurrency races,
  1 Chromium flow), log `artifacts/overhead-targeted-tests.log`.
- Full suite: **395 tests PASS**, bật toàn bộ browser flows, log
  `artifacts/overhead-full-tests.log`; PostgreSQL test đã dừng sau chạy.
- Chromium 1440/1100/800/390px: không page overflow hoặc JavaScript errors;
  form validation, query state/history, table refresh và deactivate confirmation đạt.
  Screenshots: `artifacts/screenshots/cost-pool-detail-desktop.png`,
  `allocation-rules-desktop.png`, `allocation-rule-form-mobile.png`.
- Read-only Supabase: models đủ columns, nullability khớp và managed=False;
  22 GET pages mới/cũ trả 200, root 302 về Cost Element, HTMX partial/history restore
  đúng, không session cookie. Không POST test vào Supabase.
- AST/UTF-8/conflict marker/trailing whitespace audit 26 tệp và `git diff --check`
  đạt; không business models/migrations/schema changes.

## Known limitations / next slice

1. Không quan hệ Pool–CostElement/member UI, target entity/dropdown, rule lines,
   weight/percentage/factor hoặc versioning vì schema không có.
2. condition_jsonb giữ nguyên nhưng không authoring UI; muốn target/configuration
   cần xác định cấu trúc và business policy trước. Không tự sửa database.
3. Formula reference chưa resolve/validate existence hoặc execute. Basis UoM chưa
   có compatibility/conversion resolver; không hard-code driver algorithm.
4. Chưa có overlap/priority resolution, effective rule immutability/usage guard,
   amounts period CRUD, allocation run, pool amount calculation hoặc Costing Engine.
5. Scope schema trên không thiếu mapping so với models; các feature tùy chọn trong
   prompt được bỏ qua đúng điều kiện «nếu schema có», không tạo workaround giả.

Vertical slice tiếp theo đề xuất: **Formula Studio / quản lý cấu hình công thức và
phiên bản**, sau khi kiểm tra schema/rules riêng. Không triển khai Formula Engine
trong iteration này.
