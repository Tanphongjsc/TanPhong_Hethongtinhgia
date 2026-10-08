# Quy trình sản xuất — Routing vertical slice

Ngày triển khai: 07/10/2026. Canonical docs nằm tại `docs/`; repository chưa có
`docs/ai/`. Đã đọc context/domain/architecture/engineering/spec và phần QA liên quan.
Runtime giữ single-company, no-auth; organization FK chỉ reuse compatibility layer
hiện có, không thêm membership, selector, session hoặc permission theo user.

## Schema thực tế đã kiểm tra

Models giữ nguyên trong `apps/core/models.py`, `managed = False`. Metadata Supabase
được kiểm tra trong read-only transaction; không tạo bảng/migration hoặc sửa schema.

| Model | Fields / quan hệ |
|---|---|
| Routing | id, organization, product, code, name, is_active, created_at, updated_at |
| RoutingVersion | id, routing, version_no, batch_size Decimal(24,8), batch_uom, status, effective_from/to, content_hash, change_reason, created_by/approved_by/created_at/approved_at |
| RoutingOperation | id, routing_version, sequence_no, operation_code/name, work_center, primary_resource, setup_time/run_time Decimal(24,8), time_uom, quantity_basis Decimal(24,8), quantity_uom, notes |

Routing gắn **Product**, không gắn SKU trực tiếp. Tìm/lọc SKU lấy quy trình của
Product chứa SKU đó. WorkCenter và primary_resource của công đoạn đều nullable.
Không có OperationResource hoặc bảng assignment nhiều nguồn lực. Không có cycle_time,
capacity, yield/loss hay description ở Routing. Không giả lập các field này.

Unique constraints thực tế:

- `uq_routing`: organization + code.
- `uq_routing_version`: routing + version_no.
- `uq_routing_operation_sequence`: routing_version + sequence_no.

CHECKs: batch_size/quantity_basis > 0 nếu có; setup_time/run_time >= 0;
effective_to > effective_from nếu cả hai có giá trị; status chỉ
DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/RETIRED; các trạng thái chốt cần effective_from.
Operation_code không unique; cho phép cùng mã ở các sequence khác nhau.

## Backend và versioning

Forms chỉ expose field allow-list; status, số version, hash và actor không nhận từ
POST. Tạo header kèm version 1 atomic; tạo/clone version cấp số max + 1 dưới parent
row lock. Bản mới luôn DRAFT, content_hash/created_by/approved_by/approved_at NULL.
Clone giữ toàn bộ cấu hình và công đoạn, Decimal/FK/ghi chú; không sửa source.

Service khóa Routing → Version → Operation và refresh/lock references theo thứ tự
Resource → WorkCenter → Uom, ổn định theo PK. Kiểm tra lại active/scope/consistency
khi ghi, kể cả form đã load trước khi danh mục thay đổi. Clone dùng bulk queries và
bulk_create, không tăng query theo số công đoạn.

DRAFT/IN_REVIEW được sửa. APPROVED/EFFECTIVE/RETIRED bất biến theo
`trg_routing_version_immutable` và `trg_routing_operation_protect`; backend cũng
chặn sửa/xóa/thêm công đoạn. UI chỉ đọc và dẫn sang tạo bản mới, không thêm approval
hoặc chuyển trạng thái. Sản phẩm không đổi được nếu có bất kỳ version được chốt.
Header vẫn có thể đổi mã/tên hoặc ngừng hoạt động, không hard delete.

## Validation và đơn vị

- Mã quy trình/công đoạn trim + uppercase; tên trim, bắt buộc.
- Sequence số nguyên > 0, trong integer DB; unique/version. Form gợi ý max + 10,
  lỗi trùng do request đồng thời trả message tiếng Việt, không SQL raw.
- Time dùng Decimal, tối đa 8 chữ số thập phân theo DB. Setup và run giữ riêng;
  **0 được phép** theo CHECK. Time khác 0 phải chọn active UoM có dimension_code TIME.
- Batch_size và quantity_basis tùy chọn; > 0 nếu nhập, cần unit tương ứng. Chọn unit
  mà thiếu quantity báo lỗi. Không mặc định quy trình cho một đơn vị sản phẩm.
- Product/WorkCenter/Resource/Uom active khi tạo/chọn mới; reference inactive hiện có
  vẫn hiển thị và giữ được khi edit/clone, không chọn sang danh mục inactive khác.
- Resource thuộc WorkCenter đã chọn hoặc chưa gắn WorkCenter (nguồn lực dùng chung).
  Bỏ trống WorkCenter được phép theo schema; không tự chuyển Resource sang trung tâm.
- Ngày hết hiệu lực phải sau ngày bắt đầu theo DB; có ngày kết thúc cần ngày bắt đầu.
- Không hard-code giờ, không tự quy đổi/cộng time, không snapshot ResourceRate.
  Không query ResourceRate hoặc tính production cost.

## UI / HTMX

URL và namespace hiện có: `bom:routing_*`, base `/bom/routings/`.

- List/create/detail/edit, lịch sử phiên bản/create/clone/detail/edit.
- Operations add/edit/remove (GET confirmation, POST có CSRF).
- Search mã/tên quy trình, Product, SKU; filters Product, SKU của sản phẩm, trạng thái
  version mới nhất, khoảng hiệu lực theo ngày, trạng thái header.
- Sort code/name/effective_from/created_at/version; pagination 25/50/100 tại DB.
- Detail mặc định version **mới nhất**, không tuyên bố đó là effective resolver.
- Operations luôn ordered sequence tại DB, có pagination giữ URL state.
- Search debounce 400ms theo component hiện có; filter/sort/pagination push URL.
- Drawer reuse focus trap/Escape/focus restore; form errors giữ input và aria;
  thành công refresh bảng, toast, đóng editor OOB, không reload cả page.
- WorkCenter change cập nhật dropdown Resource bằng HTMX; queryset/validation ở backend.
- Normal request trả full page; partial riêng cho HTMX; history restore trả full page.
- Toàn bộ display/validation/toast tiếng Việt; technical code và SKU giữ nguyên;
  dates dd/mm/yyyy, Decimal formatting Việt Nam, không đổi precision lưu trữ.
- Menu Sản xuất active đúng ở tất cả trang Routing/version/operation.

## Query optimization

Routing join Product; latest-version và operation count bằng Subquery, SKU search
bằng Exists. Version join batch_uom; operation join WorkCenter, Resource và
Resource.work_center, time_uom, quantity_uom. Filter/sort/search và pagination ở DB.
Không cần prefetch assignments vì schema không có relation nhiều nguồn lực.

## Files

Tạo:

- `apps/bom/routing_constants.py`, `routing_validators.py`, `routing_forms.py`,
  `routing_selectors.py`, `routing_services.py`, `routing_views.py`, `routing_urls.py`.
- `apps/bom/test_routing.py`, `test_routing_concurrency.py`, `test_routing_browser.py`.
- `templates/bom/routing/detail.html`, `operation_form.html` và partials:
  `routing_rows`, `version_rows`, `detail_content`, `operations_table`,
  `operation_editor`, `operation_saved`, `resource_field`, `operation_form_content`.
- `docs/ROUTING.md`.

Sửa:

- `apps/bom/urls.py`, `apps/bom/testing.py`.
- `apps/master_data/access.py`, `navigation.py`, `context_processors.py`, `testing.py`.
- `docs/00_AI_CONTEXT.md`, `03_SYSTEM_ARCHITECTURE.md`, `FRONTEND_IMPLEMENTATION_SPEC.md`.
- `README.md`; generated `static/css/app.css` qua build, không sửa tay.

Không cài dependency hoặc thêm JS/component framework. Shared mappings, button,
status, field/form sections, empty state, toast, table/pagination và drawer được reuse.

## Kiểm thử

Fixture unmanaged tables/constraints/triggers chỉ được tạo trong PostgreSQL test
localhost `127.0.0.1:55432/test_costing_slice`, không dùng Supabase để ghi thử.

```powershell
python manage.py check
npm run build:css
$env:COSTING_BROWSER_TESTS = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.bom.test_routing apps.bom.test_routing_concurrency apps.bom.test_routing_browser
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

Test coverage: CRUD/search/filter/sort/pagination/empty/HTMX/history restore,
normal fallback, CSRF, no session/membership, stale/inactive references, numeric
precision và date rules, resource consistency, immutable service + DB triggers,
clone exact/old unchanged/atomic rollback, duplicate error mapping, bounded queries.
Threaded tests verify version numbering and same-sequence race; Chromium flow covers
drawer/errors/dependent dropdown/clone/history/query URL/desktop-mobile/focus.

Kết quả ngày 07/10/2026:

- `python manage.py check`: PASS, không có lỗi.
- `npm run build:css`: PASS, Tailwind 4.3.3 local production build; không đổi dependency.
- Targeted Routing: **42 tests PASS** (39 behavior/query, 2 concurrency, 1 Chromium flow).
- Full suite: **358 tests PASS**, bật toàn bộ browser flows; log
  `artifacts/routing-full-tests.log`. PostgreSQL test được dừng sau chạy.
- Chromium kiểm tra 1440/1100/800/390px, không page overflow/JavaScript error,
  focus/CSRF/OOB/dependent dropdown/decimal/history đều đạt. Screenshots:
  `artifacts/screenshots/routing-detail-desktop.png`, `routing-list-desktop.png`,
  `routing-drawer-mobile.png`.
- Read-only Supabase smoke: mapping cả 3 model đủ columns và managed=False;
  18 GET pages trả 200, root 302 về Cost Element, HTMX partial 200,
  history restore full page 200, không session cookie. Không POST thử dữ liệu thật.
- AST/UTF-8/conflict marker/trailing whitespace audit 31 source/template/docs files
  và `git diff --check`: đạt.

## Giới hạn được giữ rõ

1. Chỉ một primary_resource tùy chọn mỗi công đoạn, không nhiều assignment hoặc
   resource quantity/usage_factor. Muốn nhiều nguồn lực cần quyết định schema riêng.
2. Không SKU binding trực tiếp; không cycle_time/yield/loss hoặc flow dependency graph.
3. Chưa có overlap constraint/policy, approval, version hiệu lực resolver, rate
   resolver, UoM conversion engine hoặc production cost calculation.
4. Time/basis được lưu và kiểm tra đơn vị, không suy luận conversion với costing_uom
   của Product hay per_uom của ResourceRate ở iteration này.
5. DB operation trigger kiểm tra NEW parent khi UPDATE; SQL trực tiếp bên ngoài app
   có thể chuyển công đoạn từ version khóa sang Nháp. App không expose parent FK
   và luôn khóa/check parent cũ. Không sửa trigger/schema trong task này; cần quyết
   định DB riêng nếu muốn chặn hoàn toàn SQL ngoài ứng dụng, như BOM/Packaging.
6. Reference master có thể được đổi sau khi version chốt; iteration này không thêm
   snapshot danh mục hoặc kiểm tra usage với Costing. Dữ liệu legacy không hợp lệ cần
   được rà soát riêng; clone kiểm tra lại thay vì bỏ qua validation.

Bước kế tiếp đề xuất: **Cost Pool / Nhóm chi phí chung**, sau khi kiểm tra schema và
rule hiện có. Không triển khai bước tiếp theo trong iteration Routing.
