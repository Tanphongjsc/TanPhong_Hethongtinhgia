# System Hardening & Full Regression — 08/10/2026

Phạm vi: hardening các module hiện có, không thêm feature nghiệp vụ, không deploy.
Internal single-company, truy cập trực tiếp, giao diện tiếng Việt, identifiers tiếng Anh.
Giữ Supabase PostgreSQL/schema `costing`, 51 business models unmanaged, FK compatibility
nội bộ và actor nullable. Không có Auth, membership, Approval hoặc user Audit runtime.

## Audit trước khi thay đổi

| Mục | Kết quả rà soát |
|---|---|
| A. Architecture | Django Templates/HTMX/Alpine/Tailwind; service/selector/form; database-first |
| B. Apps | core, master_data, product, bom, formula_engine, costing, pricing |
| C. URLs | 6 namespace; root vào phần tử chi phí; 28 destination đã triển khai |
| D. Services | Atomic create/clone; Run idempotency + REPEATABLE READ; Scenario row lock/retry |
| E. Selectors | ORM search/filter/sort/page; joins/prefetch và batch resolvers đã có |
| F. Forms | Allow-list fields; Decimal; normalization và lỗi tiếng Việt; không company/user input |
| G. Templates | Foundation thống nhất; còn placeholder menu, CSRF mặc định tiếng Anh, 404 fallback sai tên |
| H. Tests | Baseline 703 tests đạt, gồm unit/integration/concurrency/Chromium/Golden |
| I. Dead code | Menu/mapping chưa triển khai, session-cookie settings không còn dùng |
| J. Imports | Không thấy broken import; Django check đạt; 240 Python files parse được |
| K. Approval/Audit | Không app/view/URL/event writes; chỉ legacy mappings, actor nullable, status bảo vệ lịch sử |
| L. Auth/Organization | Không auth middleware/session/request.user/membership query; company helper nội bộ còn cần vì FK |
| M. Integration | Costing inclusive end; Pricing [start,end); không được đổi hàng loạt theo tài liệu cũ |
| N. Queries | Run list tải version/fx snapshot lớn dù table không dùng; dropdown vẫn tải các lựa chọn phù hợp |
| O. Coverage | Cần smoke chung, malformed-query matrix, localized CSRF/history errors, native double-submit, volume measurements |

Audit và kế hoạch đã báo trước khi sửa. Không phát hiện nhu cầu sửa schema.

## A. BASELINE

1. **Tests ban đầu:** 703/703 PASS trong 186,954s, có Chromium.
   `artifacts/hardening-baseline.log`.
2. **Golden Costing ban đầu:** 10 hộp, tổng 583.000 VND, đơn vị 58.300 VND;
   giá/rate tương lai cho tổng 647.000 VND. Delta tại boundary đã công bố = 0.
   `artifacts/hardening-baseline-costing.json`.
3. **Golden Pricing ban đầu:** giá vốn 58.300; giá khách trả 89.972,41379310 VND;
   phí 5.498,62068966; thuế 8.179,31034483; lợi nhuận 17.994,48275861;
   biên lợi nhuận 20%. Tương lai giá khách trả 92.526,00506044 VND, vẫn dùng
   cùng Costing Run gốc. Expected độc lập, mọi delta = 0.
   `artifacts/hardening-baseline-pricing.json`.

## B. BUGS

4. **P0 phát hiện:** 0. Golden, tổng tiền và fingerprint không sai.
5. **P1 phát hiện:** 0 trong phạm vi thực thi đã định nghĩa. Nguồn thiếu/mơ hồ bị chặn.
6. **P2 phát hiện và sửa:**
   - CSRF mặc định trả tiếng Anh; HTMX mô tả lỗi này thành lỗi quyền truy cập.
   - Error history restore trả partial; 404 route không rõ module mang tên phần tử chi phí.
   - Sidebar hiện các mục chưa có chức năng và lặp Kịch bản giá bán ở hai section.
   - Run list tải toàn bộ JSON snapshot nguồn lớn không dùng trong table.
   - Native POST tạo phiên bản chưa chặn gửi lặp ở client. Backend atomic/unique
     vẫn bảo vệ dữ liệu; bổ sung guard để một thao tác không tạo hai phiên bản hợp lệ.
7. **P3:** session-cookie settings và mapping/markup placeholders còn thừa đã dọn.
   Giới hạn đếm candidate bị hỏng snapshot ở Comparison còn được ghi ở §H.

## C. FIXES

8. **Bugs đã sửa:** localized CSRF/400, error full/partial/history, generic 404 fallback;
   giữ nhãn 404 chính xác cho Cost Element, sidebar chỉ destination thực tế.
9. **Integration fixes:** không thay đổi công thức/resolver. Bổ sung kiểm tra thống
   nhất cho 26 catalogue + Run + Comparison; kiểm tra không ghi business data qua GET.
10. **Validation fixes:** CSRF giữ HTTP 403 do yêu cầu không hợp lệ, có hướng xử lý
    tải lại trang và trace; không liên quan đăng nhập/quyền user. Bổ sung regression
    cho query sai, sort injection, Unicode ID, page quá lớn, lỗi thiếu Scheme/BOM/Routing.
11. **Performance fixes:** Run list `defer(version_snapshot_jsonb, fx_snapshot_jsonb)`;
    context/display snapshot vẫn có, detail/snapshot/trace giữ đầy đủ. Không lazy-fetch
    hai field này trong render list.
12. **UI fixes:** menu Việt hóa đang có được giữ; bỏ menu giả; native POST guard,
    giữ submitter name/value, reset khi bfcache `pageshow`; HTMX dùng disable sẵn có.
13. **Dead code removed:** mapping/section/markup placeholder và session-cookie
    settings không dùng. Không xóa file/model compatibility hoặc component nền tảng
    chỉ vì chưa thấy dùng trong một màn hình.
14. **Auth/Approval/Audit leftovers:** không có runtime cần gỡ thêm. Không query
    OrganizationMember/ApprovalRequest/ApprovalAction/AuditEvent/auth_user trong smoke.
    Giữ model legacy, status APPROVED để đọc/bảo vệ lịch sử, UUID actor nullable=NULL,
    technical logs, activation gates, manual input, version/history/trace.

### File manifest của task này

Tạo:

- `apps/costing/test_hardening.py`
- `apps/costing/test_hardening_audit.py`
- `apps/costing/test_hardening_browser.py`
- `scripts/audit_demo_integrity.py` — công cụ chẩn đoán chỉ đọc, không route/API mới
- `docs/SYSTEM_HARDENING.md`

Sửa:

- `apps/master_data/navigation.py`, `errors.py`, `views.py`
- `apps/costing/run_selectors.py`
- `apps/pricing/tests.py` — thay assertion placeholder bằng destination thực tế
- `config/settings.py`, `urls.py`, `test_settings.py`
- `templates/layouts/sidebar.html`
- `static/js/app.js`, `static/js/htmx-config.js`
- `static/css/app.css` — generated bằng Tailwind, không chỉnh tay
- `docs/00_AI_CONTEXT.md`, `FRONTEND_IMPLEMENTATION_SPEC.md`, `05_QA_TESTING.md`,
  `06_DEPLOYMENT_DEVOPS.md`, `07_OPERATIONS_MAINTENANCE.md`
- `README.md`

Không xóa file. Không cài/upgrade dependency. Không sửa models/schema/migration,
Costing/Pricing engines hoặc Expected Golden. Working tree đã có nhiều file chưa
track trước task; manifest này chỉ liệt kê thay đổi hardening.

## D. REGRESSION

15. **Master Data:** PASS. Cost Element, Currency, UoM Category/UoM/Conversion,
    Category/Item/Product/SKU, Supplier/Price: list/detail/create GET/edit GET,
    search/filter/sort/page/empty/HTMX/history. Các test CRUD hiện có vẫn chạy.
16. **Manufacturing:** PASS. Recipe/Packaging versions và lines, SKU assignment,
    WorkCenter/Resource/Rate, Routing operations, Pool/Rule/period; clone atomic,
    immutable definitions, quantities Decimal, fractional packaging, UoM compatibility.
17. **Formula:** PASS. DSL/AST allow-list, type/unit checks, bounded size/depth,
    safe evaluation, divide-by-zero, missing variables, dependency cycles, activation,
    immutable version, cached plans; không `eval`/`exec` trong production.
18. **Costing:** PASS. Scheme gate, nguồn đúng ngày, scaling/yield/scrap, setup một
    lần, packaging basis do người chạy nhập, batch/cache, persisted breakdown/trace,
    rollback lỗi, idempotency/concurrency và rerun record mới.
19. **Pricing:** PASS. Margin khác markup, phí theo specificity/priority và sàn/trần,
    thuế theo contract, FX đúng chiều/ngày, solver Decimal, controlled failures,
    Scenario immutable ở service boundary và clone/new calculation.
20. **Scenario Comparison:** PASS. 2–5 snapshot đã tính, cùng cơ sở, baseline/
    money delta/percentage points, currency warning, URL repeated IDs/HTMX/history;
    không ghi DB/gọi engine hoặc resolve nguồn hiện tại.

### Failure matrix được kiểm tra trong suite

| Trường hợp | Hành vi |
|---|---|
| Missing/ambiguous price | FAILED, MISSING_PRICE/AMBIGUOUS_PRICE; không fallback 0 |
| Missing conversion, cạnh tranh conversion | FAILED; không fallback 1, không đoán đường đi |
| Missing/ambiguous resource rate | FAILED; không lấy latest/tùy tiện |
| Missing formula/provider/version, divide-by-zero | Chặn configuration hoặc FAILED; không partial breakdown |
| Formula/scheme dependency cycle | Chặn validation/activation/execution; không vòng lặp vô hạn |
| Missing effective Scheme | ValidationError thân thiện trước khi tạo Run |
| Missing BOM/Routing | FAILED, diagnostics; snapshot và lines rỗng |
| Missing packaging basis/assignment | FAILED; không mặc định cơ sở đóng gói |
| Missing denominator/unsupported allocation | FAILED; không mẫu số giả hoặc phân bổ ngầm |
| Invalid/missing FX | Pricing giữ Nháp + diagnostics; không đảo chiều/latest/fallback 1 |
| Invalid margin/denominator | Form/solver từ chối; không giá bán âm do nghiệm sai |
| Fee/tax tie hoặc basis chưa hỗ trợ | Lỗi rõ; không chọn ngẫu nhiên hoặc thay 0 |
| Persistence/concurrency failure | Atomic rollback/retry; không ghi một phần kết quả |

### Ma trận driver phân bổ thực tế

| basis_type | Cấu hình CRUD | Thực thi Costing |
|---|---|---|
| NORMAL_CAPACITY | SUPPORTED | SUPPORTED: số liệu kỳ/công suất/UoM/currency rõ ràng |
| MACHINE_HOUR | SUPPORTED | NOT SUPPORTED: thiếu hợp đồng mẫu số/usage |
| LABOR_HOUR | SUPPORTED | NOT SUPPORTED |
| KG | SUPPORTED | NOT SUPPORTED |
| UNIT | SUPPORTED | NOT SUPPORTED |
| BATCH | SUPPORTED | NOT SUPPORTED |
| PALLET_DAY | SUPPORTED | NOT SUPPORTED |
| SHIPMENT | SUPPORTED | NOT SUPPORTED |
| VALUE | SUPPORTED | NOT SUPPORTED |
| CUSTOM | SUPPORTED | NOT SUPPORTED: không thực thi formula_code/condition tùy ý |

NORMAL_CAPACITY với formula_code/condition, currency khác hoặc vượt công suất vẫn
bị chặn; không quảng bá thành driver engine tổng quát. Schema không có PoolMember,
AllocationTarget/Lines/version tables; không giả lập chúng. Scheme không có Product/
SKU assignment table; người chạy chọn Scheme rõ ràng. Routing có primary_resource
trực tiếp; không giả lập OperationResource nhiều nguồn lực.

## E. DATA/HISTORY

21. **Effective-date:** PASS. Costing date resolver inclusive end; Pricing [start,end),
    FX aware theo 00:00 ngày định giá Việt Nam. Ngày hiện tại chỉ dùng cho preview/
    status/default form, không thay ngày nghiệp vụ. Boundary 31/10 → 01/11 được test.
    Không tạo overlap policy mới; nguồn mơ hồ gây lỗi rõ.
22. **Snapshot:** PASS. JSON Decimal strings, dates ISO/aware, source/version/AST/
    rule/trace/hash; lịch sử render từ persisted snapshot. Audit live kiểm tra hash
    và completeness của LOCKED Run/CALCULATED Scenario; FAILED không có partial lines.
23. **Historical Costing:** PASS. Fingerprint header + tất cả lines không đổi:
    `b317df1c48d905f093089009a85fd0ad07c451d274a773ddb1996c799b89f0f2`.
    Thêm giá/rate tương lai không đổi kết quả cũ; rerun tạo record mới.
24. **Historical Pricing:** PASS. Golden hash không đổi:
    `2165544f1417bbffbb5a5961f1424abdf7da4e992c2e51c29bb6bc26a7070b43`.
    Fee/Tax/FX thay đổi không được đọc lại khi xem/so sánh lịch sử.
25. **Demo seed idempotency:** hai lần `seed_demo()` liên tiếp không tạo thêm record,
    cả hai `created={}`; count, inventory, company data, toàn bộ Run fingerprints và
    Scenario records giữ nguyên. Không tạo/xóa/sửa company, không reset lịch sử.
    `artifacts/hardening-seed-idempotency.json`.

Audit live: 203 checks PASS, errors=[], warnings=[], một company nội bộ hiện có,
3 Run/18 lines, 2 Scenario. Kiểm tra unique keys, orphan FK, internal scope,
periods, inactive references cần review, SKU/Product mismatch và partial results.
`scripts/audit_demo_integrity.py` dùng PostgreSQL READ ONLY transaction; chỉ ghi file
báo cáo trong workspace. Có test fixture cố tình sai Product/SKU để chứng minh audit
phát hiện và không sửa dữ liệu. Không phải công cụ migration/repair.

## F. PERFORMANCE

26. **N+1:** không phát hiện N+1 đáng kể trong các list/detail/engine đã kiểm tra.
    Tests hiện có kiểm tra query count khi tăng lines/master records; test mới so
    25 với 100 dòng giữ nguyên số query. Công cụ audit offline có nhiều truy vấn
    kiểm tra từng relation/record; không nằm trong request UI hoặc engine.
27. **Optimizations quan trọng:** Run list bỏ tải hai snapshot lớn; joins/prefetch
    hiện có được giữ. Engine batch prices/rates/UoM, cache theo execution context;
    Formula plan cache; Comparison selection bounded, không resolve current sources.

Số đo lần full regression cuối (`artifacts/hardening-performance.json`): PostgreSQL
localhost test, Python process ấm, 10 mẫu tuần tự mỗi phép đo, p95 nearest-rank là
max của 10 mẫu. Có thêm 100 Item/100 quote/50 SKU/50 Run/50 Scenario bằng test fixtures;
không thêm bulk data vào Supabase. Số query bao gồm ORM/service/render và transaction
statements; execution dùng key/Scenario mới, không đo cache hit idempotency.

| Phép đo | p50 ms | p95 ms | Queries |
|---|---:|---:|---:|
| Run payload trước defer, 25 dòng | 14,644 | 68,346 | 2 |
| Run payload sau defer, 25 dòng | 2,774 | 3,652 | 2 |
| Costing execution thật | 85,263 | 88,947 | 51 |
| Pricing execution thật + tạo fixture Nháp | 16,738 | 18,986 | 12 |
| Comparison 5 cột, full rendering | 126,934 | 143,953 | 9 |

| List | Queries 25 dòng | Queries 100 dòng |
|---|---:|---:|
| Item | 5 | 5 |
| Supplier Price | 7 | 7 |
| SKU | 5 | 5 |
| Costing Run | 6 | 6 |
| Pricing Scenario | 7 | 7 |

28. **Performance limitations:** chưa load test concurrency/production/Supabase RTT,
    cold starts, hàng trăm nghìn nguồn hoặc p95 thống kê dài hạn. Số đo local thấp
    hơn mục tiêu tài liệu <500ms cached, nhưng không chứng nhận SLO đó. Dropdown có
    thể cần autocomplete khi master data lớn; không tạo feature đó trong hardening.
    Execution synchronous và row lock company của Run còn giới hạn throughput;
    chưa đổi isolation/locking/schema hoặc thêm queue.

## G. FINAL TEST

29. **Total tests:** 718, trong 199,165s; baseline 703 + 15 hardening mới.
30. **Passed:** 718; không skipped (Chromium và benchmark đều bật).
31. **Failed:** 0. `artifacts/hardening-final-regression.log`.
32. `python manage.py check`: PASS, 0 issues.
33. `npm run build:css`: PASS, Tailwind 4.3.3 local production build.
34. Golden Costing final: PASS, delta 0, tương lai/lịch sử và UI smoke 22 module đạt.
35. Golden Pricing final: PASS, delta 0, tương lai/historical snapshot/Costing
    fingerprint giữ nguyên. Expected không đổi để làm tests xanh.

15 test mới hardening targeted đã PASS (gồm browser và volume).
Full suite vẫn gồm unit, integration, transaction/concurrency, failure matrix,
Golden Costing/Pricing, Comparison, HTMX/history/CSRF, Chromium flows và responsive.
Không test skipped khi bật hai biến browser/benchmark. Log 503 intentional kiểm tra
thiếu company configuration và Broken pipe do hủy HTMX request không phải test failure.

Lệnh tái lập, sau khi có dependencies và local PostgreSQL 17:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:COSTING_BROWSER_TESTS='1'
$env:COSTING_HARDENING_BENCHMARK='1'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path (Get-Location).Path 'artifacts/playwright'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
.\env\Scripts\python.exe manage.py check
npm run build:css
.\env\Scripts\python.exe manage.py verify_costing_demo --report artifacts/hardening-final-costing.json
.\env\Scripts\python.exe manage.py verify_pricing_demo --report artifacts/hardening-final-pricing.json
.\env\Scripts\python.exe scripts/audit_demo_integrity.py --report artifacts/hardening-integrity.json
```

`scripts/test.ps1` chỉ tạo tables/constraints/triggers trong PostgreSQL localhost
test guarded, không Supabase. Hai verify command dùng DB `.env`, reuse dataset/công ty
hiện có, seed idempotent và không ghi đè history. Không chạy business migrations.

Artifacts: baseline/final `*-costing.json`, `*-pricing.json`, `hardening-baseline.log`,
`hardening-targeted.log`, `hardening-final-regression.log`, `hardening-integrity.json`,
`hardening-seed-idempotency.json`, `hardening-performance.json`,
`hardening-static-review.json`, screenshots `hardening-1366/1440/900.png` và browser
screenshots module hiện có. Đã xem trực tiếp ảnh desktop/tablet; bảng cuộn trong vùng
riêng, filter xuống dòng, không page overflow.

## H. REMAINING

36. **Known limitations:**
    - Phạm vi driver/FX/tax/UoM đã định nghĩa có giới hạn nêu ở trên và contract
      Costing/Pricing; unsupported configuration bị chặn, không âm thầm thay số.
    - UoM dùng conversion một cạnh đúng/ngược khi được hỗ trợ; chưa tìm multi-hop.
    - Pricing CALCULATED immutable tại application, schema chưa có trigger khóa;
      direct SQL ngoài ứng dụng vẫn có thể sửa. Hash validation phát hiện drift;
      không thay schema trong task này.
    - Không full nested-BOM/cycle expansion hoặc multi-level packaging roll-up;
      không invent chính sách lịch sử/overlap/currency normalization mới.
    - Audit read-only không thay UAT/domain-owner validation hoặc restore drill.
37. **Remaining P2/P3:** không còn P0/P1 đã phát hiện. P3: Comparison paginator đếm
    structural candidates trước khi kiểm tra hash từng dòng; legacy snapshot hỏng
    có thể làm ít dòng hiển thị hơn count. Live DEMO không có trường hợp này; dòng
    hỏng bị loại khỏi selection, không tính/ghi lại. Không scan toàn bảng để sửa count.
38. **Technical debt:** thống nhất effective-end cần quyết định nghiệp vụ/migration
    riêng; autocomplete/dropdown lớn; measured concurrency/Supabase latency; review
    immutable storage cho Pricing khi được phép thay schema; SDLC còn phần lịch sử
    có superseding note, không coi là requirement để khôi phục Auth/Approval.
39. **Recommended next phase:** Deployment Preparation: xác định môi trường nội bộ/
    network, secrets/TLS/DEBUG/static, backup-restore/RPO-RTO, rollback, telemetry,
    performance/UAT trên môi trường dự kiến. Không tự thực hiện deploy, Auth, queue
    hoặc feature mới; không đưa Organization/Approval/Audit workflow trở lại.

## Acceptance gate

| Tiêu chí yêu cầu | Kết quả |
|---|---|
| 1–3. Django check / Tailwind / test suite | PASS / PASS / 718 PASS |
| 4–6. Golden Costing / Golden Pricing / Comparison | PASS, delta 0 / PASS, delta 0 / PASS |
| 7. Seed idempotent | PASS, created={} cả hai lần |
| 8–9. P0 / P1 | Không phát hiện blocker còn mở trong phạm vi đã định nghĩa |
| 10–12. Auth / Approval / User Audit dependency | Không có runtime |
| 13–14. Broken URL / menu chết | Smoke 28 module đạt; menu chỉ destination đã có |
| 15–16. Costing / Pricing history | Fingerprints/snapshots giữ nguyên |
| 17–18. Effective date / Decimal | Regression boundary/precision đạt |
| 19. Missing price/rate silently zero | Không; failure matrix chặn rõ |
| 20. UI regression nghiêm trọng | Không phát hiện qua Chromium/full/HTMX/responsive |

**READY FOR DEPLOYMENT PREPARATION**

Readiness này chỉ dành cho bước chuẩn bị deployment trong phạm vi đã kiểm tra,
không phải production go-live. Chưa deploy hoặc triển khai hạ tầng; dừng task tại đây.
