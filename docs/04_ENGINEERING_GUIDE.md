**BỘ HỒ SƠ VÒNG ĐỜI PHÁT TRIỂN PHẦN MỀM**

> **Production config 08/10/2026:** `config.production` kế thừa settings hiện có,
> không tự đọc .env; production entry point `python -m config.serve`. Build dùng
> npm ci/build + collectstatic/manifest; không migration/seed trong release script.
> Demo commands chỉ development/test/staging; manage.py test bắt buộc localhost
> config.test_settings. Logging JSON redacts secrets, không body/query/debug SQL.
> [06_DEPLOYMENT_DEVOPS.md](06_DEPLOYMENT_DEVOPS.md) là runbook hiện hành.

> **Runtime 08/10/2026:** không Approval Workflow/business Audit Log, user/role/Auth.
> Các guideline về maker/checker/actor audit nhân sự bên dưới đã superseded.
> Giữ technical logging/trace_id, version/history/snapshot/explain và Decimal rules.
> Actor nullable không fake UUID. Không business schema migration. Pricing Foundation
> reuse service/selector/form/HTMX tại apps/pricing, không đưa Pricing vào Costing Engine.
> [PRICING_FOUNDATION.md](PRICING_FOUNDATION.md).

> **Pricing Scenario 08/10/2026:** scenario_* tách CRUD khỏi engine context/resolvers/
> solver/runner. Chỉ đọc Costing persisted result, JSON schema có contract rõ,
> snapshot/hash/trace và calculated immutability ở application; không approval/actor
> giả. Decimal 50 intermediate, money 8dp HALF_EVEN; tính sàn/trần theo piecewise
> equation, không đoán unknown basis/FX. [PRICING_SCENARIO.md](PRICING_SCENARIO.md).
> Comparison tách `comparison_selectors` / `comparison` / `comparison_presentation` /
> `comparison_views`: kiểm tra selection/hash/basis, đọc persisted metrics và Decimal
> delta; không gọi solver/resolver/runner. URL giữ repeated IDs và baseline, HTMX
> history restore trả full page. [SCENARIO_COMPARISON.md](SCENARIO_COMPARISON.md).

> **Kiến trúc hiện tại 07/10/2026:** single-company, no-auth. Các giả định lịch sử
> về authentication/membership theo user đã superseded. Company context và internal
> policy dùng chung; audit actor nullable để NULL.
> Xem [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).

03 - PHÁT TRIỂN MÃ NGUỒN & TÍCH HỢP

Implementation & Coding - Chuẩn repository, coding, migration, testing và code review

| Mã tài liệu   | SDLC-03                                                                                |
|---------------|----------------------------------------------------------------------------------------|
| Phiên bản     | 1.0                                                                                    |
| Trạng thái    | Baseline đề xuất - cần phê duyệt theo dự án                                            |
| Công nghệ nền | Django + Supabase PostgreSQL (baseline hiện tại)                                       |
| Phạm vi       | Costing & Pricing Engine: giá thành, giá bán, Formula/Rule Engine, BOM, version, audit |

# Mục lục nội dung

> **1. Repository & branching**
>
> **2. Local development**
>
> 3\. Project structure
>
> 4\. Coding standards
>
> 5\. Database migration standard
>
> 6\. Implementation order
>
> 7\. Formula engine coding rules
>
> 8\. API/service/repository patterns
>
> 9\. Testing in development
>
> 10\. Code review & quality gate
>
> 11\. Dependency/security management
>
> 12\. Excel migration implementation
>
> 13\. Sprint execution
>
> 14\. Definition of Done

# 1. Repository & Branching Strategy

| **Loại**    | **Quy ước**                                       | **Mục đích**                                 |
|-------------|---------------------------------------------------|----------------------------------------------|
| Khuyến nghị | Trunk-based nhẹ hoặc short-lived feature branches | Giảm long-lived divergence; PR nhỏ dễ review |
| Branch      | feature/\<ticket\>-\<short-name\>                 | Tính năng                                    |
| Branch      | fix/\<ticket\>-\<short-name\>                     | Sửa lỗi                                      |
| Branch      | hotfix/\<ticket\>-\<short-name\>                  | Production hotfix                            |
| Protection  | main/develop protected                            | PR + tests + approval bắt buộc               |
| Commit      | Conventional Commit                               | feat:, fix:, refactor:, test:, docs:, chore: |

# 2. Local Development Setup

| **Thành phần**    | **Chuẩn**                                               | **Lưu ý**                           |
|-------------------|---------------------------------------------------------|-------------------------------------|
| Python            | Version pin qua .python-version/pyproject               | Không dùng “latest” không kiểm soát |
| Dependencies      | lock file                                               | Reproducible builds                 |
| Django            | settings split theo environment                         | Không hard-code secret              |
| Supabase/Postgres | local/dev project hoặc container PostgreSQL tương thích | Migration chạy từ zero              |
| Docker Compose    | app + worker + optional redis                           | One-command bootstrap               |
| .env.example      | Chỉ key name/example non-secret                         | Không commit secrets                |
| Seed              | Reference data tối thiểu                                | Currency/UoM/roles/sample company   |

# 3. Project Structure đề xuất

Cấu trúc module nên phản ánh domain boundary, tránh “models.py/service.py” khổng lồ dùng chung toàn hệ thống.

src/  
costing/  
master_data/  
manufacturing/  
formula/  
rules/  
costing_engine/  
pricing/  
workflow/  
integration/  
common/  
config/  
tests/  
unit/  
integration/  
e2e/  
migrations/  
docs/  
scripts/

# 4. Coding Standards

| **Chủ đề**   | **Quy chuẩn**                                                                                       |
|--------------|-----------------------------------------------------------------------------------------------------|
| Naming       | snake_case cho Python/PostgreSQL; PascalCase cho class; UPPER_SNAKE cho constants                   |
| Money/Rate   | Decimal ở application; NUMERIC ở database; không float                                              |
| Time         | timezone-aware; UTC lưu trữ; effective business date explicit                                       |
| Transactions | Use-case thay đổi nhiều bảng phải atomic                                                            |
| Exceptions   | Domain error codes ổn định; không leak stack trace ra client                                        |
| Logging      | Structured key-value; trace_id/run_id/version_id; không log secrets/sensitive value không cần thiết |
| Queries      | ORM/parameterized SQL; tránh dynamic SQL từ user input                                              |
| JSONB        | Validate schema ở application; không biến JSONB thành “dump everything”                             |

# 5. Database Migration Standard

| **Rule** | **Nội dung**                                                                |
|----------|-----------------------------------------------------------------------------|
| MIG-01   | Mỗi schema change có migration versioned trong Git.                         |
| MIG-02   | Không sửa migration đã chạy production; thêm migration mới.                 |
| MIG-03   | Additive-first cho zero/low downtime: add nullable/backfill/enforce.        |
| MIG-04   | DDL lớn phải đánh giá lock/time; index lớn cân nhắc concurrent khi phù hợp. |
| MIG-05   | Data migration có batch/idempotency/checkpoint.                             |
| MIG-06   | Có rollback hoặc forward-fix plan; backup trước destructive migration.      |
| MIG-07   | CI tạo database sạch và chạy full migrations từ đầu.                        |

# 6. Implementation Order

| **Mốc**        | **Capability**        | **Deliverable**                                                                 |
|----------------|-----------------------|---------------------------------------------------------------------------------|
| Sprint/Phase A | Foundation            | currency/uom/company_member/cost_element; common audit/authorization            |
| Sprint/Phase B | Formula + Rule        | formula/version/dependency/test; rule table/version/row; parser/validator       |
| Sprint/Phase C | Scheme + Run          | scheme/version/line; engine orchestration; run/line/override                    |
| Sprint/Phase D | Manufacturing         | item/product/sku; supplier price; recipe; packaging; routing/resource; overhead |
| Sprint/Phase E | Pricing               | channel fee/tax/fx; price scenario; approvals                                   |
| Sprint/Phase F | Migration/Integration | Excel staging, ERP/adapters, actual/variance as scoped                          |

# 7. Formula Engine Coding Rules

| **Layer**        | **Yêu cầu triển khai**                                         |
|------------------|----------------------------------------------------------------|
| Tokenizer/Parser | Grammar riêng; giới hạn expression length/AST depth.           |
| AST              | Node types allow-list; canonicalize trước hash.                |
| Functions        | Registry do developer deploy; user chỉ gọi approved functions. |
| Resolvers        | Interface typed; DB/network nằm ngoài evaluator.               |
| Execution        | No recursion; execution budget; deterministic input snapshot.  |
| Dependency       | Extract và persist; publish-time cycle detection.              |
| Validation       | Type, dimension, required context, output type.                |
| Security         | Không eval/exec; không string interpolation query.             |
| Testing          | Unit từng operator/function + golden formula regression.       |

# 8. API / Service / Repository Pattern

| **Layer**           | **Trách nhiệm**                                       | **Không được làm**               |
|---------------------|-------------------------------------------------------|----------------------------------|
| API/View            | Parse request, authN/authZ boundary, response mapping | Không chứa pricing/costing logic |
| Application Service | Orchestrate use case, transaction, idempotency        | Gọi domain/resolver/repository   |
| Domain Service      | Business invariant/calculation policy                 | Không phụ thuộc HTTP             |
| Repository          | Persistence/query abstraction                         | Parameterized/ORM, tenant scoped |
| Resolver/Adapter    | Lookup/external integration contract                  | Timeout/retry/source snapshot    |
| Serializer/DTO      | Typed boundary objects                                | Validate input/output            |

# 9. Testing trong quá trình phát triển

| **Layer**     | **Scope**                                                                               | **Mục tiêu**                   |
|---------------|-----------------------------------------------------------------------------------------|--------------------------------|
| Unit          | Formula parser/functions, pricing formulas, UoM/FX, version resolution, domain policies | Nhanh, isolated                |
| Repository/DB | Constraints, indexes behavior, effective-date queries, immutability triggers            | Real PostgreSQL preferred      |
| Integration   | API + DB + adapters mock, transactions, idempotency                                     | CI                             |
| Contract      | External adapter payloads                                                               | Schema fixture                 |
| Golden        | Excel representative cases line-by-line                                                 | Regression trước merge/release |

# 10. Pull Request / Code Review

| **Checklist**   | **Câu hỏi review**                                                      |
|-----------------|-------------------------------------------------------------------------|
| Correctness     | Logic match requirement/business rule; edge cases; Decimal/UoM/currency |
| Architecture    | Đúng module boundary; không bypass domain/service                       |
| Security        | Authorization; input validation; injection; secrets; sensitive logs     |
| Database        | Migration safe; FK/check/index; query plan/N+1                          |
| Testing         | Happy path + negative + boundary; regression                            |
| Observability   | Error code, structured log, trace context                               |
| Documentation   | API/ADR/README/RTM thay đổi tương ứng                                   |
| Maintainability | Naming, complexity, dead code, duplication                              |

<img src="media/image1.png" style="width:6.7in;height:0.3469in" />

Hình 1. Pipeline chất lượng từ Pull Request tới Production; ở giai đoạn coding, tối thiểu phải chạy đến build + test + security scan.

# 11. Quality Gate đề xuất

| **Gate**                   | **Điều kiện**                                                  |
|----------------------------|----------------------------------------------------------------|
| Lint/format                | Pass                                                           |
| Unit/integration test      | Pass                                                           |
| Critical/High SAST finding | 0 chưa được accept có lý do                                    |
| Migration test             | Fresh DB + upgrade path pass                                   |
| Coverage                   | Không giảm coverage module trọng yếu; threshold được team chốt |
| Complexity                 | Không thêm hotspot vượt threshold mà không ADR/refactor task   |
| Dependency scan            | Không có critical vulnerability chưa xử lý/accept              |

# 12. Dependency & Secret Management

- Pin dependency và cập nhật định kỳ; dùng automated dependency scanning.

- Không commit .env, API key, database password, service-role key.

- Secrets theo environment và rotation policy.

- Supabase service-role chỉ ở trusted backend; không đưa client.

- Tạo SBOM (Software Bill of Materials - Danh mục thành phần phần mềm) khi release nếu quy trình yêu cầu.

# 13. Excel Migration Implementation

| **Step**      | **Implementation**                                   |
|---------------|------------------------------------------------------|
| Landing       | Upload file + hash + metadata                        |
| Staging       | Raw row có source_sheet/source_row                   |
| Validation    | Schema/type/UoM/currency/duplicate/business rule     |
| Preview       | Error/warning report; impact counts                  |
| Promote       | Transaction/atomic batch                             |
| Reconcile     | Source row ↔ destination record ↔ calculation result |
| Repeatability | Idempotency theo file hash/batch key                 |

# 14. Sprint Execution & Definition of Done

| **Nghi thức** | **Tiêu chuẩn**                                                                            |
|---------------|-------------------------------------------------------------------------------------------|
| Planning      | Story đã DoR; estimate; dependency; test notes                                            |
| Daily         | Blocker, migration/data issue, architecture decision surfaced early                       |
| Review        | Demo theo acceptance criteria; show explain/audit nếu liên quan                           |
| Retro         | Quality/lead time/incidents; action có owner/date                                         |
| DoD           | PR merged; tests pass; docs/RTM updated; deployable; no critical findings; acceptance met |
