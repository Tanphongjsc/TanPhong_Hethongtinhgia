**BỘ HỒ SƠ VÒNG ĐỜI PHÁT TRIỂN PHẦN MỀM**

> **Deployment regression 08/10/2026:** `apps/master_data/test_deployment.py`
> kiểm tra production settings bằng subprocess với env test-safe, thiếu/sai secret/
> host/SSL/transport, command guards, health/readiness/schema, redacted JSON logs,
> real Waitress+WhiteNoise/manifest, DEBUG=False/CSRF/error pages/Chromium và Golden.
> HTTP fixture test dùng PostgreSQL localhost/public schema do test runner tạo;
> schema costing/search_path production được kiểm riêng, không giả là test fixture
> mapping live. `scripts/smoke_production.py` chỉ GET, không seed/tính engine.
> Full suite qua scripts/test.ps1, browser và volume opt-in giữ như hardening.
> Evidence/giới hạn: [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md).

> **Hardening 08/10/2026:** baseline 703 tests; regression bổ sung toàn bộ route
> catalogue/full/HTMX/history, query sai, CSRF tiếng Việt, no GET writes, failure
> matrix và audit dữ liệu chỉ đọc. Chromium kiểm tra 1366/1440/900px và gửi lặp
> native version form. Benchmark opt-in trên PostgreSQL localhost test, không
> Supabase: `COSTING_HARDENING_BENCHMARK=1`. Kết quả/gate và giới hạn phép đo:
> [SYSTEM_HARDENING.md](SYSTEM_HARDENING.md).

> **Scope test 08/10/2026:** Approval/Maker-Checker/business Audit Log và user/role/Auth
> không còn runtime; các ma trận WF/AUD/AuthZ cũ đã superseded cho iteration hiện tại.
> Giữ regression versioning/immutability/history/effective resolution, snapshot/source/
> explain/trace_id, Decimal, CSRF và Golden Costing. Pricing Foundation có CRUD,
> percentage boundaries, scope/time/direction/ambiguity, HTMX/mobile và query-count tests.
> Test DDL chỉ trong PostgreSQL localhost cô lập, không Supabase schema changes.
> [PRICING_FOUNDATION.md](PRICING_FOUNDATION.md).

> **Pricing Scenario gate 08/10/2026:** Golden expected tính độc lập, waterfall
> reconcile, margin khác markup, multiple fixed/%/bounded fees, tax inclusive/exclusive,
> direct FX/date boundaries/missing/ties, snapshot history, Costing fingerprint không
> đổi, CRUD/HTMX/Chromium/query-count/CSRF. Test fixtures chỉ DDL localhost guarded.
> Lệnh verify_pricing_demo chỉ đọc Costing đã khóa, seed Pricing idempotent và đối
> soát Golden/future. [PRICING_SCENARIO.md](PRICING_SCENARIO.md).
> Comparison gate: Golden 3 persisted columns độc lập, 0/1/2/5/6 IDs, duplicate/invalid/
> missing/corrupt/failed attempt, SKU/Product/UoM compatibility, mixed currency,
> Decimal absolute/relative/percentage-point delta, zero baseline, no writes/engine/
> current rules, history after Fee/Tax/FX changes, constant query count và Chromium.
> Pricing/Costing Golden vẫn chạy trong full regression. [SCENARIO_COMPARISON.md](SCENARIO_COMPARISON.md).

04 - KIỂM THỬ & ĐẢM BẢO CHẤT LƯỢNG

Quality Assurance & Testing - chức năng, hồi quy, hiệu năng, bảo mật, dữ liệu và UAT

| Mã tài liệu   | SDLC-04                                                                                |
|---------------|----------------------------------------------------------------------------------------|
| Phiên bản     | 1.0                                                                                    |
| Trạng thái    | Baseline đề xuất - cần phê duyệt theo dự án                                            |
| Công nghệ nền | Django + Supabase PostgreSQL (baseline hiện tại)                                       |
| Phạm vi       | Costing & Pricing Engine: giá thành, giá bán, Formula/Rule Engine, BOM, version, audit |

# Mục lục nội dung

> **1. Test strategy**
>
> **2. Test pyramid**
>
> 3\. Environment & test data
>
> 4\. Functional test
>
> 5\. Formula/rule tests
>
> 6\. Database/data integrity
>
> 7\. Integration/API/contract
>
> 8\. E2E/UAT
>
> 9\. Golden master Excel
>
> 10\. Performance test
>
> 11\. Security test
>
> 12\. Resilience/DR test
>
> 13\. Defect management
>
> 14\. Test metrics
>
> 15\. Exit criteria

# 1. Test Strategy

| **Hạng mục** | **Nội dung**                                                                                                      |
|--------------|-------------------------------------------------------------------------------------------------------------------|
| Mục tiêu     | Chứng minh đúng nghiệp vụ, an toàn, tái lập được và chịu tải trong điều kiện mục tiêu.                            |
| Scope        | Core configuration, formula/rule, manufacturing costing, pricing, approval/audit, migration/integration.          |
| Risk focus   | Sai giá, sai version, sai UoM/currency, access leak, ambiguous rule, duplicate run, migration mismatch.           |
| Automation   | Unit + integration + API regression chạy CI; E2E chọn luồng trọng yếu; performance/security theo release cadence. |
| Evidence     | Report có build/version/environment/test data/trace link; UAT sign-off lưu cùng release.                          |

<img src="media/image1.png" style="width:6.7in;height:3.03355in" />

Hình 1. Test Pyramid - tháp kiểm thử: nhiều Unit/Formula test, ít hơn Integration, ít nhất E2E/UAT nhưng tập trung luồng quan trọng.

# 2. Test Environment & Test Data

| **Environment** | **Mục tiêu**                         | **Dữ liệu**                                    |
|-----------------|--------------------------------------|------------------------------------------------|
| Unit            | In-process                           | Fixtures typed; no external network            |
| Integration     | PostgreSQL thật tương thích Supabase | Seed deterministic, isolated schema/db         |
| Staging         | Gần production                       | Masked/synthetic data; external sandbox        |
| UAT             | Business-facing                      | Golden scenarios + representative master/rates |
| Performance     | Dedicated/non-noisy                  | Volume gần target; monitoring enabled          |
| Security        | Isolated authorized scope            | Test accounts/roles/tenant boundaries          |

# 3. Functional Test Matrix

| **Area** | **Module**       | **Test focus**                                                            |
|----------|------------------|---------------------------------------------------------------------------|
| CE       | Cost Element     | CRUD, type/dimension/source/scope, unique company code                    |
| FM       | Formula          | Parse/type/UoM/dependency/version/test/publish                            |
| RL       | Rule             | Effective date, priority, specificity, tie/ambiguity                      |
| BOM      | Recipe/Packaging | Yield/scrap/multi-level/conversion/version                                |
| RUN      | Costing Run      | Resolve version, calculation, rounding, snapshot, explain                 |
| PR       | Pricing          | Margin vs markup, % fee inversion, fixed/order allocation, floor/rounding |
| WF       | Workflow         | Submit/approve/reject/self-approval blocked/retire                        |
| AUD      | Audit            | Before/after/hash/reason/actor/append-only                                |
| SEC      | Authorization    | Role/tenant/sensitive field                                               |
| IMP      | Import           | Staging/validation/duplicate/idempotency/promote                          |

# 4. Formula / Rule Test Catalogue

| **TC**      | **Input/Case**                     | **Mục tiêu**              | **Expected**            |
|-------------|------------------------------------|---------------------------|-------------------------|
| TC-FM-01    | A + B                              | Money + Money             | Kết quả đúng precision  |
| TC-FM-02    | VND + KG                           | Dimension mismatch        | Reject validation       |
| TC-FM-03    | A→B→C→A                            | Circular dependency       | Reject publish          |
| TC-FM-04    | UnknownFunction()                  | Function not allow-listed | Reject parse/validation |
| TC-RL-01    | SKU+Channel vs Channel             | Specificity               | SKU+Channel được chọn   |
| TC-RL-02    | Hai rule cùng specificity/priority | Ambiguous                 | Error RULE_AMBIGUOUS    |
| TC-PRICE-01 | full_cost/(1-fee-margin)           | Valid denominator         | Đúng expected           |
| TC-PRICE-02 | fee+margin \>=1                    | Invalid denominator       | Explicit error          |

# 5. Database & Data Integrity Test

| **Nhóm**          | **Case**                                                                        |
|-------------------|---------------------------------------------------------------------------------|
| FK/Restrict       | Không xóa master đã được approved version/run tham chiếu                        |
| Unique            | company_id + code; run idempotency key                                          |
| Check             | rate 0..1; qty \> 0; effective_to \> effective_from                             |
| Immutability      | Approved/effective version update/delete bị chặn                                |
| Audit append-only | Update/delete audit_event bị chặn                                               |
| Precision         | Decimal round-trip DB/application                                               |
| Concurrency       | Hai user publish cùng version/rule; optimistic/unique guard xử lý deterministic |

# 6. Integration / API / Contract Test

| **Nhóm**        | **Kịch bản**                                                |
|-----------------|-------------------------------------------------------------|
| API validation  | Missing required context, wrong UoM, invalid UUID/public id |
| AuthZ           | Role matrix, cross-company access, sensitive field          |
| Idempotency     | Retry same create-run không sinh duplicate                  |
| Transaction     | Lỗi giữa run header/lines phải rollback toàn bộ             |
| Adapter timeout | External FX/carrier timeout theo fallback policy            |
| Contract        | Marketplace/ERP payload schema drift                        |
| Error model     | Error code + trace_id consistency                           |

# 7. E2E & UAT

| **ID** | **Scenario**                | **Flow**                                                               | **Acceptance**                                  |
|--------|-----------------------------|------------------------------------------------------------------------|-------------------------------------------------|
| E2E-01 | Cappuccino + Choco → TikTok | Setup master → resolve BOM/packaging/rates → calculate → approve price | Cost breakdown, fee, target price, explain đúng |
| E2E-02 | Wholesale 500 cartons       | No marketplace fee; volume discount/logistics allocation               | Price/margin theo B2B policy                    |
| E2E-03 | Export container            | Incoterm + FX + export cost + container conversion                     | Snapshot FX/rules; quote reproducible           |
| E2E-04 | Formula change              | Draft new version → regression → approve → effective                   | Old run không đổi; new run uses new version     |
| E2E-05 | Manual override             | Override special charge with reason/approval                           | Trace hiển thị original/override/actor/reason   |

# 8. Golden Master Excel

1.  Chọn 10-30 scenario đại diện 3 workbook: có/không choco, 3-in-1, các packaging option, các tỷ giá khác nhau.

2.  Freeze input workbook/version và xác định expected từng line.

3.  Chạy hệ thống mới cùng effective date/input.

4.  So sánh line-level với tolerance được nghiệp vụ chốt.

5.  Phân loại mismatch: data mapping, rounding, logic bug, intentional correction.

6.  Chỉ chấp nhận intentional correction khi có Business Decision/CR được duyệt.

# 9. Performance Test

| **Scenario**        | **Load**                   | **Metrics**                                 | **Acceptance baseline**        |
|---------------------|----------------------------|---------------------------------------------|--------------------------------|
| Single costing      | 1-50 concurrent users      | p50/p95/p99 latency, error rate, DB time    | p95 target \< 500 ms cached    |
| Explain             | Concurrent reads           | latency, payload size                       | p95 target \< 1 s              |
| Rule-heavy          | Nhiều rules/dimensions     | lookup query time/cache hit                 | No ambiguous result            |
| Bulk roll-up        | 10,000 SKU                 | throughput, retry, memory, DB load          | Async progress; no UI blocking |
| Import              | Large Excel/CSV            | rows/s, validation errors, transaction time | Staging + atomic promote       |
| Concurrency publish | Multiple editors/approvers | lock/conflict behavior                      | No duplicate effective version |

# 10. Security Testing

| **Loại**        | **Tiếng Việt / mục tiêu**                               | **Thời điểm**              |
|-----------------|---------------------------------------------------------|----------------------------|
| SAST            | Static Application Security Testing - Phân tích mã tĩnh | CI                         |
| DAST            | Dynamic Application Security Testing - Kiểm thử động    | Staging/release            |
| Dependency Scan | CVE trong library/container                             | CI/nightly                 |
| Authorization   | IDOR/cross-tenant/role bypass                           | Integration/security suite |
| Formula abuse   | Injection, huge AST, recursion, resource exhaustion     | Dedicated negative tests   |
| Secrets         | Secret scanning/repository history                      | Pre-commit/CI              |
| RLS             | Policy bypass nếu expose Supabase Data API              | SQL/API tests              |

# 11. Resilience / Backup / DR Test

| **Kịch bản**               | **Expected**                                             |
|----------------------------|----------------------------------------------------------|
| DB connection interruption | Request fail cleanly; retry only safe operations         |
| Worker crash               | Job retry/idempotency; no duplicate output               |
| External provider down     | Timeout/fallback; run marks warning/error per policy     |
| Backup restore             | Khôi phục staging từ backup; verify record counts/checks |
| Rollback release           | Previous app + compatible DB path                        |
| Partial import failure     | No partial promote; rerun safe                           |

# 12. Defect Management

| **Severity/Priority** | **Định nghĩa**                                       | **Policy**                           |
|-----------------------|------------------------------------------------------|--------------------------------------|
| Critical              | Sai giá/permission/data corruption/production outage | Fix before release; immediate triage |
| Major                 | Core function broken nhưng có workaround hạn chế     | Must fix hoặc explicit waiver        |
| Minor                 | UI/cosmetic/non-critical                             | Schedule                             |
| Priority P0/P1/P2/P3  | Business urgency                                     | Owner + target date                  |

| **Bug ID** | **Title**  | **Env**           | **Steps** | **Expected** | **Actual** | **Severity** | **Owner** | **Status** | **Evidence**      |
|------------|------------|-------------------|-----------|--------------|------------|--------------|-----------|------------|-------------------|
| BUG-001    | Mô tả ngắn | Environment/build | Steps     | Expected     | Actual     | Severity     | Owner     | Status     | Evidence/trace_id |

# 13. Test Metrics

| **Metric**           | **Ý nghĩa**                          |
|----------------------|--------------------------------------|
| Requirement coverage | % FR/NFR có test                     |
| Pass rate            | Pass / executed                      |
| Defect escape        | Bug production / total               |
| Reopen rate          | Bug reopened / closed                |
| Automation coverage  | Critical flows automated             |
| Performance SLO pass | % scenarios đạt latency/error target |
| Security findings    | Open Critical/High                   |
| UAT acceptance       | Signed scenarios / planned           |

# 14. Exit Criteria

- Blocker/Critical defects = 0.

- Không còn High security finding chưa có waiver hợp lệ.

- 100% Must-have requirements có test evidence.

- Golden master pass trong tolerance; mismatch được giải trình/phê duyệt.

- Performance scenarios đạt acceptance baseline hoặc có documented capacity limitation.

- UAT signed-off bởi business owner.

- Regression suite xanh trên release candidate.

- Release known issues và rollback impact đã được chấp nhận.
