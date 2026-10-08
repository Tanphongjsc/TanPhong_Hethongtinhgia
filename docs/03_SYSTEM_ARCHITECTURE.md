**BỘ HỒ SƠ VÒNG ĐỜI PHÁT TRIỂN PHẦN MỀM**

> **Deployment preparation 08/10/2026:** production WSGI dùng Waitress, WhiteNoise
> phục vụ hashed/compressed static; settings `config.production`, process environment,
> Supabase session pooler/SSL/search_path costing,public. Không Docker/queue/proxy
> mới hoặc schema change. Health/readiness và JSON technical logging là infrastructure,
> không audit/auth/workflow. Chưa deploy vào target; runbook thực thi nằm ở đầu
> [06_DEPLOYMENT_DEVOPS.md](06_DEPLOYMENT_DEVOPS.md).

> **Runtime 08/10/2026:** apps/workflow và apps/audit đã gỡ; Approval/Maker-Checker
> và business Audit UI/event writes bên dưới đã superseded. Core DB mappings giữ
> nguyên, không migrations. Version/history/effective resolver, activation gates,
> Costing snapshot/source/explain/trace_id và technical logs vẫn giữ. No auth/role.
> Pricing Foundation và Scenario ở apps/pricing, tách biệt Costing Engine.
> Scenario chỉ đọc Run LOCKED; engine HTTP-independent reuse fee/tax/FX selectors,
> atomic Decimal execution, PriceScenario JSON snapshot/trace/hash, DRAFT/CALCULATED.
> Không schema mới hoặc approval. [PRICING_SCENARIO.md](PRICING_SCENARIO.md).
> Scenario Comparison stateless tại `/pricing/scenarios/compare/`: selection GET,
> selector ORM bounded + snapshot validation + presentation, không Comparison model,
> không engine calls/current rule queries/writes. [SCENARIO_COMPARISON.md](SCENARIO_COMPARISON.md).

> **Costing Scheme 07/10/2026:** app/namespace costing, `/costing/schemes/`,
> configuration only. Scheme/version/line unmanaged hiện có, FK CE/FormulaVersion/
> RuleTable; không manufacturing/Product/SKU assignments hoặc currency/base quantity.
> Reuse Formula Engine build_plan/type/unit/graph, không evaluator; kiểm tra nguồn
> CE/dependency/cycle giữa dòng. Clone atomic, guarded activation/config hash,
> immutable versions/lines. Không price/rate queries, Run/Pricing/Auth/schema change.
> Source registry/LOOKUP resolver/selection policy và full execution snapshots chưa
> có. Xem [COSTING_SCHEME.md](COSTING_SCHEME.md).

> **Formula Engine 07/10/2026:** app `apps/formula_engine/`, namespace
> formula_engine, `/formula-engine/formulas/`. DSL riêng + AST allow-list/hash,
> typed CostElement/Formulas, batched dependency snapshot, iterative topo/cycle
> detection và Decimal evaluator không ORM/I/O. Version/test models hiện có,
> Studio/HTMX và guarded activation; DB khóa approved/effective/retired.
> Không RuleTable resolver, execution snapshot hoặc Costing Run; không auth/new
> organization workflow. Xem [FORMULA_ENGINE.md](FORMULA_ENGINE.md).

> **CostPool / AllocationRule 07/10/2026:** configuration slice ở
> `apps/bom/overhead_*`, `/bom/cost-pools/`, `/bom/allocation-rules/` và namespace
> bom theo manufacturing boundary hiện có. CostPool → AllocationRule qua pool FK;
> không có CostElement members, line/target tables hoặc versioning. basis_type là
> mã theo CHECK, basis_uom FK tùy chọn, formula_code text không FK; condition_jsonb
> chưa có target schema và được giữ nguyên khi chỉnh sửa. Services atomic/allow-list,
> rule lock → pool lock → unit lock và refresh active/scope khi ghi. New rule Nháp,
> NULL actor; không trạng thái/approval action. DB không khóa lịch sử rule hoặc
> cấm overlap; generic immutable-version assumptions bên dưới chưa áp dụng cho
> AllocationRule. Period amounts ở CostPoolPeriod ngoài scope iteration này.
> Không cost calculation/Formula Engine/schema change. Xem
> [COST_POOL_ALLOCATION_RULE.md](COST_POOL_ALLOCATION_RULE.md).

> **Routing 07/10/2026:** nằm trong `apps/bom/routing_*`, URL `/bom/routings/`,
> namespace bom. Product → Routing → RoutingVersion → RoutingOperation;
> WorkCenter và primary_resource nullable, không có bảng nhiều nguồn lực/công đoạn.
> Version có batch_size/batch_uom và effective dates; operation lưu thời gian
> setup/run riêng và quantity_basis/quantity_uom. Tạo header+initial version và
> clone atomic; khóa Routing → Version → Operation → references theo thứ tự ổn định.
> Parent lock tuần tự hóa cấp số phiên bản/công đoạn; source version không đổi.
> APPROVED/EFFECTIVE/RETIRED khóa theo trigger DB và service, không thêm approval.
> List annotated Subqueries; detail join FK, công đoạn ordered/paginated ở DB;
> clone bulk query/bulk insert không N+1. Không schema change hoặc costing/rate lookup.
> Xem [ROUTING.md](ROUTING.md) cho tính bất biến và giới hạn SQL ngoài ứng dụng.

> **WorkCenter / Resource / ResourceRate 07/10/2026:** nghiệp vụ sản xuất nằm trong
> `apps/bom/resource_*`, models unmanaged ở core, URL namespace bom giữ nguyên.
> Selectors eager-load WorkCenter/Uom/Currency; list và rate history phân trang ở DB.
> Services atomic, refresh/lock references, allow-list bỏ metadata/status/actors.
> ResourceRate có effective dates nhưng không version/immutable trigger/overlap
> constraint. Amount >= 0 và end > start theo CHECK thật. Generic immutable-version
> assumptions bên dưới chưa áp dụng cho bảng giá này; không invent policy hoặc
> xây resolver/cost engine. No auth/membership/organization workflow mới.
> Xem [WORK_CENTER_RESOURCE_RATE.md](WORK_CENTER_RESOURCE_RATE.md).

> **Kiến trúc hiện tại 07/10/2026:** single-company, no-auth. Supabase chỉ cung cấp
> PostgreSQL; không dùng Supabase Auth, user session hoặc membership/RBAC theo user.
> Các phần multi-tenant/auth bên dưới đã superseded cho runtime hiện tại.
> Model/table/FK Organization và OrganizationMember giữ nguyên.
> Xem [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).

> **Recipe / BOM 07/10/2026:** slice ở `apps/bom/` chứa forms/selectors/services/
> validators/views, models vẫn unmanaged ở core. Định mức gắn Product qua Recipe;
> version giữ sản lượng/đơn vị/tỷ lệ thu hồi/hiệu lực; lines tham chiếu Item + Uom.
> Tạo ban đầu và clone atomic, khóa Recipe → Version → Line khi ghi; parent lock
> bảo vệ số phiên bản tăng dần khi có request đồng thời. Trigger DB khóa phiên bản
> APPROVED/EFFECTIVE/RETIRED và các lines, được enforce thêm ở service.
> Không triển khai approval, BOM expansion/cycle, Costing hoặc schema change.
> Xem [RECIPE_BOM.md](RECIPE_BOM.md) cho conversion policy và giới hạn trigger DB.

> **Packaging 07/10/2026:** nằm trong `apps/bom/packaging_*`, `/bom/packaging/` và
> namespace bom hiện có. Config thuộc Product, version/lines quản lý riêng với Recipe;
> SKU gán Config qua SkuPackagingAssignment có effective dates. Không có quy mô đầu ra
> ở model Packaging. Tạo Config+initial version và clone atomic; khóa Config → Version
> → Line/Assignment. Shared helpers chỉ gồm table metadata, date annotation, safe PK
> lookup và UoM compatibility; không generic CRUD framework. Không costing/expansion/
> approval/schema change. Xem [PACKAGING_CONFIGURATION.md](PACKAGING_CONFIGURATION.md).

02 - THIẾT KẾ HỆ THỐNG & KIẾN TRÚC

System Architecture & Detailed Design - HLD, LLD, dữ liệu, API, bảo mật và tích hợp

| Mã tài liệu   | SDLC-02                                                                                |
|---------------|----------------------------------------------------------------------------------------|
| Phiên bản     | 1.0                                                                                    |
| Trạng thái    | Baseline đề xuất - cần phê duyệt theo dự án                                            |
| Công nghệ nền | Django + Supabase PostgreSQL (baseline hiện tại)                                       |
| Phạm vi       | Costing & Pricing Engine: giá thành, giá bán, Formula/Rule Engine, BOM, version, audit |

# Mục lục nội dung

> **1. Architecture principles & ADR**
>
> **2. C4 Context/Container/Component**
>
> 3\. Module boundaries
>
> 4\. Database architecture & ERD
>
> 5\. Formula/Rule Engine design
>
> 6\. Costing execution design
>
> 7\. API design
>
> 8\. Security/RBAC/RLS/Threat Model
>
> 9\. Integration & async processing
>
> 10\. Data migration design
>
> 11\. UI/UX design
>
> 12\. Performance/caching
>
> 13\. Deployment architecture
>
> 14\. LLD checklist & Exit Gate

# 1. Architecture Principles & ADR

| **ID** | **Nguyên tắc**                                  | **Áp dụng**                                                                                                          |
|--------|-------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| AP-01  | Modular Monolith first                          | Bắt đầu modular monolith để giữ transaction consistency; tách worker/adapter/reporting khi tải hoặc tổ chức yêu cầu. |
| AP-02  | Relational master, JSONB snapshot               | Master/core relation ở PostgreSQL; JSONB cho context, condition, immutable snapshot/trace.                           |
| AP-03  | Version everything that changes business result | Formula, rule, BOM, packaging, routing, rate, scheme có version/effective date.                                      |
| AP-04  | Explainability by construction                  | Run line lưu source/formula/version/input/output.                                                                    |
| AP-05  | Security by design                              | No arbitrary code; resolver whitelist; parameterized query; RLS/RBAC; immutable audit.                               |
| AP-06  | Idempotent & observable                         | Persist API có idempotency; trace_id xuyên request/worker/integration.                                               |

| **ADR** | **Chủ đề**        | **Quyết định**                    | **Phương án khác**        | **Lý do**                                   | **Hệ quả**                      |
|---------|-------------------|-----------------------------------|---------------------------|---------------------------------------------|---------------------------------|
| ADR-001 | Kiến trúc         | Modular Monolith                  | Microservices, serverless | Transaction consistency + tốc độ triển khai | Có thể tách worker/adapters sau |
| ADR-002 | Database          | Supabase PostgreSQL               | NoSQL-first               | Dữ liệu quan hệ/version/audit mạnh          | JSONB chỉ dùng có kiểm soát     |
| ADR-003 | Formula execution | DSL + AST allow-list              | eval Python/JS/SQL        | An toàn, type-check, audit                  | Cần parser/compiler riêng       |
| ADR-004 | IDs               | bigint nội bộ + UUID public/trace | UUID cho mọi PK           | Tương thích HRM hiện tại, index nhỏ         | Cần public_id khi expose        |

# 2. C4 Context & System Boundary

<img src="media/image1.png" style="width:6.7in;height:2.32107in" />

Hình 1. C4 Context - phạm vi hệ thống và các hệ thống/người dùng xung quanh.

# 3. HLD - Kiến trúc tổng thể

<img src="media/image2.png" style="width:6.7in;height:2.93625in" />

Hình 2. High-Level Design (HLD - Thiết kế mức cao) đề xuất.

| **Layer**              | **Trách nhiệm**                                                              |
|------------------------|------------------------------------------------------------------------------|
| Web UI                 | Formula Studio, Costing Workspace, Scenario Compare, Approval/Audit          |
| Django API/Application | Validation, authorization, transactions, use-case orchestration, idempotency |
| Domain                 | Product, Cost Master, Formula, Costing, Pricing, Workflow                    |
| PostgreSQL             | Master/version/rule/run/audit; constraints; RLS nếu expose Data API          |
| Worker                 | Bulk roll-up, import, reconciliation, heavy scenario                         |
| Adapters               | ERP/accounting, purchase/inventory, marketplace, carrier, FX, Excel          |
| Object Storage         | Import files, evidence, generated report/quote                               |
| Observability          | Structured logs, metrics, traces, formula/run latency/error                  |

# 4. Module Boundaries

**Boundary triển khai hiện tại 07/10/2026:** `master_data` chứa Cost Element và
Currency/UoM cùng helper UI/query/company context. Product Category và Item Master
mới nằm trong `apps/product/` (`product:` URL namespace); không di chuyển model
hoặc module đang chạy. Bảng đề xuất lịch sử bên dưới không yêu cầu đưa Item CRUD
về `master_data`. Cả hai app chỉ import persistence models từ `apps/core/models.py`.

Supplier/SupplierPrice hiện nằm trong `apps/master_data/`; không có auth/membership.
SupplierPrice giữ lịch sử bằng các bản ghi có ngày hiệu lực. DB không có overlap
constraint/immutability trigger hay incoming FK tới giá mua; usage lock khi đã tính
giá chưa triển khai. Guardrail generic «edit effective version = new version» bên
dưới chưa được áp dụng cho bảng này; xem giới hạn tại [SUPPLIER_PRICE.md](SUPPLIER_PRICE.md).

| **Module**    | **Phạm vi**                                           | **Quy tắc phụ thuộc**                         |
|---------------|-------------------------------------------------------|-----------------------------------------------|
| master_data   | Currency, UoM, Product, SKU, Item, Supplier, Channel  | Ít phụ thuộc domain khác                      |
| manufacturing | Recipe/BOM, Packaging, Routing, Resource, Cost Pool   | Cung cấp quantity/cost structure              |
| formula       | Formula identity/version, AST, dependency, test cases | Không trực tiếp truy DB arbitrary             |
| rules         | Generic rule table + fee/tax/rate resolvers           | Resolution theo date/priority/specificity     |
| costing       | Scheme/version/line, run/line, override, roll-up      | Orchestrator chính                            |
| pricing       | Price Scenario, margin/markup/floor, quotation        | Dựa trên immutable costing run                |
| workflow      | Approval, version state, audit                        | Cross-cutting governance                      |
| integration   | Adapters/import/export                                | Chuyển external payload thành domain contract |

# 5. Database Architecture & ERD

<img src="media/image3.png" style="width:6.7in;height:0.87486in" />

Hình 3. ERD mức cao của cấu hình Formula/Rule/Scheme và Costing Run.

| **Pattern**        | **Bảng**                                                                                                             | **Quy tắc**                                              |
|--------------------|----------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| Identity + Version | formula/formula_version; costing_scheme/costing_scheme_version; recipe/recipe_version; rule_table/rule_table_version | Không sửa approved/effective; edit = new version         |
| Version Detail     | formula_dependency; scheme_line; recipe_line; rule_row                                                               | Child có thể cascade delete khi Draft                    |
| Master             | cost_element, item, product, sku, supplier, resource, channel, currency, uom                                         | Unique code theo company; ON DELETE RESTRICT khi đã dùng |
| Execution          | costing_run, costing_run_line, override, price_scenario                                                              | Run approved/locked immutable                            |
| Governance         | approval_request/action, audit_event                                                                                 | Audit append-only                                        |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Chuẩn kiểu dữ liệu<br />
</strong>Không dùng FLOAT cho tiền/rate/quantity quan trọng. Dùng NUMERIC; mọi money có currency, quantity/rate có UoM; timestamptz cho thời điểm hệ thống; date/timestamptz cho effective dating.</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 6. Formula & Rule Engine Design

<img src="media/image4.png" style="width:6.7in;height:0.68241in" />

Hình 4. Vòng đời một Formula Version từ Draft tới Retired.

| **Thành phần**       | **Thiết kế**                                                                 |
|----------------------|------------------------------------------------------------------------------|
| Parser               | Parse expression thành AST; từ chối token/function ngoài allow-list          |
| Type checker         | Money/Number/Percent/Quantity/Boolean/Text                                   |
| Dimension checker    | Không cho VND + kg; conversion qua UoM/currency resolver                     |
| Dependency extractor | Trích element/formula/rule dependency                                        |
| Cycle detector       | Topological sort; chặn A→B→C→A                                               |
| Evaluator            | Chạy deterministic với execution budget                                      |
| Resolver layer       | SYSTEM/LOOKUP/EXTERNAL qua registry; không cho expression tự truy DB/network |
| Test runner          | Regression/golden test trước submit review                                   |
| Compiler cache       | Cache AST immutable theo formula_version_id/hash                             |

| **Source Mode** | **Ví dụ**                                                     | **Guardrail**                                               |
|-----------------|---------------------------------------------------------------|-------------------------------------------------------------|
| SYSTEM          | Resolver whitelist: recipe cost, machine hours, product field | Read-only domain API                                        |
| MANUAL          | User input có type/range/reason                               | Override record + optional approval                         |
| LOOKUP          | Rule table / fee / tax / freight                              | Effective date + priority + specificity                     |
| FORMULA         | AST/DSL expression                                            | Version + test + dependency                                 |
| EXTERNAL        | FX/marketplace/carrier                                        | Adapter timeout/retry/fallback + raw response hash/snapshot |

# 7. Costing Execution Design

<img src="media/image5.png" style="width:6.7in;height:1.2658in" />

Hình 5. Sequence Diagram rút gọn cho Create Costing Run.

1.  Validate request/context, authorization và idempotency key.

2.  Resolve Costing Scheme Version theo company/scheme/effective_at.

3.  Resolve Recipe/Packaging/Routing và rate/rule/FX versions theo effective_at.

4.  Build dependency DAG cho các line/formula cần chạy.

5.  Evaluate theo topological order; type/UoM/range/rounding validation.

6.  Persist costing_run + costing_run_line trong transaction.

7.  Persist version snapshot, source trace và audit event.

8.  Trả result + run public ID; explain endpoint đọc snapshot, không recompute dữ liệu hiện tại.

# 8. API Specification Baseline

| **Method** | **Endpoint**                             | **Mục đích**        | **Quyền**               | **Lưu ý**                 |
|------------|------------------------------------------|---------------------|-------------------------|---------------------------|
| POST       | /api/v1/costing/runs                     | Tạo và persist run  | Cost Accountant/Pricing | Idempotency-Key           |
| GET        | /api/v1/costing/runs/{public_id}         | Đọc result header   | Authorized viewer       | Tenant scoped             |
| GET        | /api/v1/costing/runs/{public_id}/explain | Explain tree        | Authorized viewer       | Sensitive fields filtered |
| POST       | /api/v1/formulas/{id}/versions           | Tạo formula draft   | Formula Designer        | No arbitrary SQL          |
| POST       | /api/v1/formula-versions/{id}/submit     | Submit review       | Formula Designer        | Validation/test must pass |
| POST       | /api/v1/approvals/{id}/approve           | Approve             | Approver                | Maker ≠ approver          |
| POST       | /api/v1/pricing/scenarios                | Tạo what-if pricing | Pricing Manager         | Base run immutable        |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>API Error Model<br />
</strong>Chuẩn hóa error code: VALIDATION_ERROR, MISSING_RATE, MISSING_FX, FORMULA_INVALID, CIRCULAR_DEPENDENCY, DIMENSION_MISMATCH, RULE_AMBIGUOUS, APPROVAL_REQUIRED, FORBIDDEN. Response luôn có trace_id.</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 9. Security / RBAC / RLS / Threat Model

| **Role**         | **Quyền chính**                         | **Guardrail**                       |
|------------------|-----------------------------------------|-------------------------------------|
| Costing Viewer   | Read approved runs/results              | Không sửa                           |
| Cost Accountant  | Create run, rate draft, manual override | Không tự approve thay đổi của mình  |
| Formula Designer | Create/edit/test formula draft          | Không activate                      |
| Approver         | Approve formula/rate/scheme/cost        | Maker-checker                       |
| Pricing Manager  | Pricing rules/scenarios/quote           | Sensitive target margin             |
| Auditor          | Read all versions/audit/explain         | Read-only                           |
| Admin            | Technical/master config                 | Không mặc định xem sensitive margin |

| **Threat** | **Kịch bản**              | **Rủi ro**              | **Mitigation**                                                        |
|------------|---------------------------|-------------------------|-----------------------------------------------------------------------|
| T-01       | Injection qua expression  | Arbitrary code/SQL      | Custom grammar + allow-list + no DB/network + parameterized resolvers |
| T-02       | Cross-company data access | Broken tenant isolation | company_id + service authorization + RLS nếu exposed                  |
| T-03       | Self approval             | Fraud/control bypass    | maker_id != approver_id; policy/DB/service check                      |
| T-04       | Sensitive margin leakage  | Unauthorized view       | is_sensitive + permission-filtered serializers/views                  |
| T-05       | Replay duplicate run      | Double persist          | Idempotency key unique per company                                    |

# 10. Integration & Async Processing

| **Adapter**   | **Dữ liệu**                             | **Mode**              | **Kiểm soát**                             |
|---------------|-----------------------------------------|-----------------------|-------------------------------------------|
| ERP/Purchase  | PO/receipt/invoice/supplier price       | Inbound batch/API     | Idempotent upsert + source key            |
| Manufacturing | Actual consumption/output/labor/machine | Inbound event/batch   | Reconciliation table                      |
| Marketplace   | Orders/settlements/fees/refunds         | Inbound API/file      | Store source hash/raw reference           |
| Carrier/WMS   | Weight/dimensions/shipping quote        | Sync/async adapter    | Timeout + fallback policy                 |
| FX            | Reference/accounting/settlement rates   | Scheduled pull/manual | Source+timestamp+snapshot                 |
| Excel         | Migration/import                        | File staging          | Validate → preview error → atomic promote |

# 11. Data Migration Design

9.  Land raw workbook vào staging; lưu file hash, source sheet, row number.

10. Profile dữ liệu: null, duplicate, UoM/currency, magic numbers, formula patterns.

11. Mapping row/sheet sang master/rate/recipe/packaging/scheme/rule.

12. Validate domain constraints; không promote khi error blocking.

13. Preview và sign-off mapping với nghiệp vụ.

14. Atomic promote vào production master/config draft.

15. Golden master: chạy 10-30 scenario đại diện và so từng line với Excel trong tolerance.

16. Document intentional differences do sửa logic nghiệp vụ.

| **Nguồn**                   | **Đích**                                  | **Kiểm tra**                                      |
|-----------------------------|-------------------------------------------|---------------------------------------------------|
| GIÁ NGUYÊN LIỆU             | item + supplier_price + recipe_line       | UoM, currency, tax recoverability, effective date |
| GIÁ BAO BÌ                  | packaging_item + packaging config/version | conversion hierarchy                              |
| GIÁ MÁY MÓC NHÀ XƯỞNG       | resource + resource_rate + cost_pool      | normal capacity/allocation                        |
| GIÁ NHÂN CÔNG               | resource/labor rate                       | per hour/kg/batch                                 |
| GIÁ SANCHET / CAFE 3 TRON 1 | costing_scheme + formula + scenario       | profit separated from cost                        |
| Quotation Details           | packaging variants + pricing scenario     | container qty from rule/config                    |

# 12. UI/UX Design Baseline

| **Màn hình**      | **Thành phần**                                                               | **Guardrail**                                                       |
|-------------------|------------------------------------------------------------------------------|---------------------------------------------------------------------|
| Formula Studio    | Palette \| editor \| properties \| test panel \| dependency graph \| explain | Không cho gõ arbitrary element code; autocomplete/validation inline |
| Costing Workspace | Context header \| cost tree \| source/formula/version \| KPI \| warnings     | Click line để xem source trace                                      |
| Scenario Compare  | Pin 2-5 scenarios; delta absolute/%                                          | Giữ base manufacturing cost khi dependency không đổi                |
| Approval Inbox    | Change diff, impact preview, maker, reason, test result                      | Approve/reject với audit                                            |
| Master Data       | Version timeline, effective dates, status                                    | Edit effective version = create new version                         |

# 13. Performance / Caching

| **Workload**    | **Mục tiêu**                         | **Thiết kế**                                                 |
|-----------------|--------------------------------------|--------------------------------------------------------------|
| Single costing  | p95 \< 500 ms khi reference đã cache | Cache immutable formula/rate/version; memoize component cost |
| Explain         | p95 \< 1 s                           | Đọc persisted trace; không recompute                         |
| 10k SKU bulk    | Background batch                     | Chunk/progress/retry; dependency-based invalidation          |
| Rate lookup     | High cardinality                     | Composite index + effective range + cache                    |
| Audit retrieval | \< 2 s/run/version                   | Index entity/time; partition khi volume chứng minh cần       |

# 14. Deployment Architecture

<img src="media/image6.png" style="width:6.7in;height:2.11542in" />

Hình 6. Kiến trúc triển khai baseline cho Django + Supabase PostgreSQL.

# 15. LLD Checklist & Exit Gate

- Mỗi module có responsibility, public interface và dependency rules.

- Database table/column/constraint/index có data dictionary.

- API có request/response/error/idempotency/authz.

- Sequence cho luồng phức tạp: costing run, approval, formula publish, import.

- Threat Model có mitigation cho High risks.

- Migration/cutover/rollback được thiết kế trước implementation.

- ADR ghi các quyết định khó đảo ngược.

- Performance targets có benchmark plan.

- Architecture review được ký duyệt.
