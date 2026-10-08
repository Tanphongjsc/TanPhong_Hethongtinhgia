**BỘ HỒ SƠ VÒNG ĐỜI PHÁT TRIỂN PHẦN MỀM**

> **Quyết định hiện tại 08/10/2026:** single-company, no-auth/account/role;
> Approval/Maker-Checker và business Audit Log không còn trong runtime/scope.
> BR-005, FR-AU-001, SOD-001/AUD-001 và các acceptance về submit/approve/reject
> hoặc actor audit bên dưới đã superseded. Version immutability, history,
> effective dating, snapshot/source/explain và technical logging vẫn bắt buộc.
> Pricing Foundation gồm Channel/Fee/Tax/FX; Pricing Scenario đã triển khai trên
> persisted Costing Run, không ghi ngược Costing. Contract margin/fee/tax/FX và
> giới hạn thực thi: [PRICING_SCENARIO.md](PRICING_SCENARIO.md).
> Compare đã triển khai chỉ đọc 2–5 snapshot cùng SKU/Product và cùng cơ sở đơn vị;
> không recalculation hoặc raw monetary delta khác currency. [SCENARIO_COMPARISON.md](SCENARIO_COMPARISON.md).

01 - KHỞI TẠO DỰ ÁN & PHÂN TÍCH YÊU CẦU

Discovery & Requirements Analysis - Biến nhu cầu kinh doanh thành yêu cầu rõ ràng, khả thi và đo lường được

| Mã tài liệu   | SDLC-01                                                                                |
|---------------|----------------------------------------------------------------------------------------|
| Phiên bản     | 1.0                                                                                    |
| Trạng thái    | Baseline đề xuất - cần phê duyệt theo dự án                                            |
| Công nghệ nền | Django + Supabase PostgreSQL (baseline hiện tại)                                       |
| Phạm vi       | Costing & Pricing Engine: giá thành, giá bán, Formula/Rule Engine, BOM, version, audit |

# Mục lục nội dung

> **1. Mục tiêu và đầu vào**
>
> **2. Project Charter & Scope**
>
> 3\. Stakeholders & RACI
>
> 4\. Khảo sát As-Is/To-Be
>
> 5\. BRD
>
> 6\. SRS
>
> 7\. FR/NFR catalogue
>
> 8\. Use Case & Business Rules
>
> 9\. Data requirements
>
> 10\. Security & compliance requirements
>
> 11\. RTM
>
> 12\. Backlog & ưu tiên
>
> 13\. Feasibility & Risk
>
> 14\. Sign-off / Exit Gate

# 1. Mục tiêu và đầu vào

Giai đoạn này xác lập bài toán đúng trước khi thiết kế kỹ thuật. Với hệ thống tính giá, trọng tâm không chỉ là “tính ra một con số”, mà phải xác định rõ các lớp chi phí, quy tắc version/effective date, khả năng giải thích kết quả, phân quyền và nhu cầu tái lập lịch sử.

| **Hạng mục**  | **Nội dung**                                                                                                             |
|---------------|--------------------------------------------------------------------------------------------------------------------------|
| Đầu vào       | 03 workbook tính giá hiện tại; tài liệu nghiệp vụ; cấu trúc HRM tham chiếu; stakeholder knowledge; quy định nội bộ       |
| Đầu ra        | Project Charter, BRD, SRS, Use Cases, Business Rules, RTM, Data Dictionary, prioritized backlog, risk register, sign-off |
| Vai trò chính | Sponsor/Product Owner, BA, Cost Accountant, Pricing Manager, Architect/Tech Lead, QA, Security/DBA                       |
| Timebox gợi ý | 2-4 tuần cho baseline đầu tiên; sau đó quản lý thay đổi qua backlog/CR                                                   |

# 2. Project Charter & Scope

| **Mục**          | **Baseline đề xuất**                                                                                                                         |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| Business Problem | Excel phân tán, hard-coded formula/rate, thiếu version và audit; khó mở rộng nhiều SKU/kênh.                                                 |
| Vision           | Nền tảng Costing & Pricing cấu hình được, có Formula/Rule Engine, version, snapshot, approval và explainability.                             |
| In Scope         | Master data, Cost Element, Formula/Rule, Scheme, BOM/Packaging, Standard/Planned Cost, Channel Pricing, Costing Run, audit/approval.         |
| Out of Scope v1  | Full ERP replacement, accounting GL engine hoàn chỉnh, AI price optimization tự động, marketplace settlement realtime nếu chưa có connector. |
| Success Criteria | Tái lập kết quả workbook mẫu trong tolerance; thay rule/rate không deploy code; run lịch sử không đổi; truy vết tới source/version.          |
| Constraints      | Supabase/PostgreSQL; tích hợp HRM hiện hữu; ngân sách/nguồn lực dự án; dữ liệu Excel chưa chuẩn hóa.                                         |

# 3. Stakeholders & phỏng vấn

| **Stakeholder**          | **Câu hỏi trọng tâm**                                            |
|--------------------------|------------------------------------------------------------------|
| Sponsor / Ban lãnh đạo   | ROI, phạm vi, timeline, mức kiểm soát và báo cáo                 |
| Kế toán giá thành        | Cost boundaries, allocation, standard/actual, VAT recoverability |
| Pricing/Sales            | Margin, channel fee, quote, customer-specific pricing            |
| Mua hàng/Kho             | Supplier price, UoM, landed cost, receipt data                   |
| Sản xuất                 | BOM, yield, scrap, routing, work center, capacity                |
| IT/Backend               | Architecture, integration, security, operations                  |
| Auditor/Internal Control | Audit trail, segregation of duties, immutable historical results |

Bộ câu hỏi phỏng vấn tối thiểu: mục tiêu kinh doanh; quyết định nào đang dựa vào file Excel; nguồn dữ liệu; trường hợp ngoại lệ; ai có quyền thay đổi rate/công thức; khi nào phải phê duyệt; dữ liệu lịch sử cần giữ bao lâu; sai số/tolerance chấp nhận; báo cáo nào được dùng để ra quyết định.

# 4. Khảo sát As-Is / To-Be

<img src="media/image1.png" style="width:6.7in;height:1.33028in" />

Hình 1. Chuyển từ quy trình Excel phân tán (As-Is) sang nền tảng cấu hình có version và audit (To-Be).

| **Khía cạnh**        | **Mô tả**                                                                            |
|----------------------|--------------------------------------------------------------------------------------|
| As-Is: Nguồn dữ liệu | Nguyên liệu, bao bì, máy móc, nhân công, vận chuyển nằm ở sheet riêng                |
| As-Is: Tính toán     | Công thức tham chiếu ô; có magic number như tỷ giá, số thùng/container, điều chỉnh % |
| As-Is: Governance    | Thiếu version/effective date/audit/maker-checker                                     |
| To-Be: Master        | Product/SKU/UoM/Item/Supplier/Resource/Channel chuẩn hóa                             |
| To-Be: Logic         | Cost Element + Scheme + Formula Version + Rule Table                                 |
| To-Be: Execution     | Costing Run bất biến + line-level explain + version snapshot                         |
| To-Be: Governance    | Approval workflow + audit + RLS/RBAC + change reason                                 |

# 5. BRD - Business Requirement Document

Cấu trúc BRD nên gồm: Executive Summary (Tóm tắt), Business Objectives (Mục tiêu), Scope, Stakeholders, Current State, Target State, Business Requirements, Business Rules, Assumptions/Constraints, KPI/Success Criteria, Risks, Sign-off.

| **ID** | **Business Requirement**                                        | **Ưu tiên** | **Owner**               |
|--------|-----------------------------------------------------------------|-------------|-------------------------|
| BR-001 | Hệ thống cho phép cấu hình công thức tính mà không sửa code lõi | Must        | Formula Designer        |
| BR-002 | Kết quả lịch sử phải tái lập được theo version/rate đã dùng     | Must        | Cost Accountant/Auditor |
| BR-003 | Tách giá thành sản xuất khỏi chi phí kênh và mục tiêu lợi nhuận | Must        | Finance/Pricing         |
| BR-004 | Hỗ trợ nhiều SKU/quy cách/kênh/thị trường                       | Must        | Business                |
| BR-005 | Có maker-checker với thay đổi ảnh hưởng giá                     | Must        | Internal Control        |
| BR-006 | Có import/migration từ Excel và đối soát golden master          | Should      | Project Team            |

# 6. SRS - Software Requirements Specification

SRS là baseline kỹ thuật của yêu cầu. Mỗi yêu cầu cần ID, mô tả, rationale, actor, precondition, input, rule, output, error, acceptance criteria, priority, dependency và trace link.

| **ID**     | **Chức năng**           | **Acceptance baseline**                                                                               |
|------------|-------------------------|-------------------------------------------------------------------------------------------------------|
| FR-CE-001  | Tạo Cost Element        | Formula Designer có thể tạo code/name/type/dimension/source/scope/rounding; code unique theo company. |
| FR-FM-004  | Publish Formula Version | Chỉ publish khi parser, type/UoM, DAG cycle check và regression tests pass; maker không tự approve.   |
| FR-BOM-003 | Resolve Recipe Version  | Theo product + effective date; không lấy “current row” bỏ qua ngày hiệu lực.                          |
| FR-RUN-001 | Tạo Costing Run         | Nhận SKU/qty/UoM/scheme/channel/effective_at; resolve version; persist snapshot và explain.           |
| FR-PR-002  | Pricing Scenario        | Cho margin/markup/profit-per-unit; lưu snapshot; không ghi ngược manufacturing cost.                  |
| FR-AU-001  | Audit                   | Lưu actor/timestamp/reason/before/after/hash cho thay đổi được kiểm soát.                             |

# 7. NFR - Non-Functional Requirements

| **ID**       | **Thuộc tính**                    | **Yêu cầu**                                                              | **Cách chứng minh**  |
|--------------|-----------------------------------|--------------------------------------------------------------------------|----------------------|
| NFR-PERF-001 | Performance - Hiệu năng           | Single product costing p95 \< 500 ms khi reference data đã cache         | Benchmark staging    |
| NFR-PERF-002 | Explainability latency            | Explain run p95 \< 1 giây                                                | APM/load test        |
| NFR-SEC-001  | Security - Bảo mật                | Không eval/exec arbitrary code; expression chỉ gọi allow-listed function | SAST/security tests  |
| NFR-AUD-001  | Auditability - Khả năng kiểm toán | Approved run/version không sửa tại chỗ; re-run tạo bản mới               | DB trigger + tests   |
| NFR-DATA-001 | Data Integrity - Toàn vẹn         | Money/rate/qty dùng NUMERIC; FK/check/unique; typed dimension            | DB tests             |
| NFR-REL-001  | Reliability - Độ tin cậy          | Persist API có idempotency key khi có side effect                        | Integration test     |
| NFR-OBS-001  | Observability - Khả năng quan sát | Mọi run có trace_id; structured log; error metrics                       | Log/trace inspection |

# 8. Use Case & Business Rules

<img src="media/image2.png" style="width:6.7in;height:8.55538in" />

Hình 2. UML Use Case tổng quan cho các vai trò chính.

| **Use Case** | **Tên**             | **Actor**        | **Precondition**             | **Output**                        | **Ngoại lệ**                                     |
|--------------|---------------------|------------------|------------------------------|-----------------------------------|--------------------------------------------------|
| UC-01        | Tạo Costing Run     | Cost Accountant  | Scheme/recipe/rate effective | Cost tree + totals + explain      | Rate thiếu / formula invalid / denominator \<= 0 |
| UC-02        | Tạo Formula Version | Formula Designer | Formula identity tồn tại     | Draft version + validation result | Circular dependency / type mismatch              |
| UC-03        | Approve Version     | Approver         | Version In Review            | Approved/Scheduled                | Self-approval bị chặn                            |
| UC-04        | Compare Scenarios   | Pricing Manager  | Có base run                  | Delta cost/price/margin           | Scenario context thiếu rule                      |

| **Rule ID** | **Business Rule - Quy tắc nghiệp vụ**                                                 |
|-------------|---------------------------------------------------------------------------------------|
| BRULE-001   | Một version hiệu lực trong \[effective_from, effective_to).                           |
| BRULE-002   | Không cho hai active rule cùng specificity/priority gây kết quả không xác định.       |
| BRULE-003   | Profit/Target Margin thuộc pricing scope, không cộng vào manufacturing cost.          |
| BRULE-004   | Manual override bắt buộc reason và có thể cần approval theo threshold.                |
| BRULE-005   | Nếu phí % + target margin làm mẫu số \<= 0, engine báo lỗi thay vì trả giá âm/vô hạn. |
| BRULE-006   | Costing Run lịch sử resolve theo effective_at của run, không theo dữ liệu “hiện tại”. |

# 9. Data Requirements & Data Dictionary

| **Domain**     | **Trường tối thiểu**                                                | **Loại dữ liệu**      |
|----------------|---------------------------------------------------------------------|-----------------------|
| Product/SKU    | code, name, category, costing/sales UoM, dimensions, tax class      | Master                |
| Item           | raw material/packaging/semi-finished/service                        | Master                |
| Supplier Price | supplier, item, UoM, currency, min qty, price, tax, effective dates | Versioned rate        |
| Recipe/BOM     | output, yield, component qty, UoM, scrap, version                   | Versioned structure   |
| Resource Rate  | resource, rate type, amount, per-UoM, effective dates               | Versioned rate        |
| Channel Fee    | fee type/base/rate/fixed/cap/floor/refund/effective                 | Versioned rule        |
| Formula/Scheme | expression/dependency/source mode/version/status                    | Configuration         |
| Costing Run    | context/version snapshot/lines/totals/trace                         | Immutable transaction |

# 10. Security & Compliance Requirements

| **ID**       | **Nhóm**                              | **Yêu cầu**                                                                            |
|--------------|---------------------------------------|----------------------------------------------------------------------------------------|
| AUTH-001     | Authentication (Xác thực)             | User đăng nhập qua cơ chế chuẩn của hệ thống; session/token được bảo vệ.               |
| AUTHZ-001    | Authorization (Phân quyền)            | RBAC + tenant/company isolation; sensitive margin/purchase price cần permission riêng. |
| SOD-001      | Segregation of Duties (Tách nhiệm vụ) | Maker không tự approve thay đổi ảnh hưởng price/output.                                |
| AUD-001      | Audit                                 | Change có actor/timestamp/reason/before/after/hash.                                    |
| FORM-SEC-001 | Formula sandbox                       | Không file/network/database access trực tiếp từ expression.                            |
| DATA-SEC-001 | Data exposure                         | Schema/tables exposed qua Supabase Data API phải có RLS; ưu tiên API/views kiểm soát.  |

# 11. Requirement Traceability Matrix (RTM)

| **BR** | **FR/NFR**    | **Use Case** | **Design**  | **Code/DB**                  | **Test**        | **Release** |
|--------|---------------|--------------|-------------|------------------------------|-----------------|-------------|
| BR-001 | FR-FM-001/004 | UC-02/03     | HLD-FORMULA | formula_version / dependency | TC-FM-01..12    | Release 1   |
| BR-002 | FR-RUN-001    | UC-01        | HLD-COSTING | costing_run / line           | TC-RUN-01..20   | Release 1   |
| BR-003 | FR-PR-002     | UC-04        | HLD-PRICING | price_scenario               | TC-PRICE-01..10 | Release 2   |

# 12. Backlog & ưu tiên

| **Epic** | **Tên**                  | **Scope**                                                        | **Mốc**   |
|----------|--------------------------|------------------------------------------------------------------|-----------|
| Epic 1   | Core Configuration       | Cost Element, Formula DSL/version, Rule Table, Costing Scheme    | MVP       |
| Epic 2   | Manufacturing Cost       | Item/Product/SKU, Recipe, Packaging, Routing, Resource, Overhead | MVP       |
| Epic 3   | Costing Execution        | Run, line-level trace, snapshot, override, compare               | MVP       |
| Epic 4   | Pricing & Channels       | Channel fee, tax, FX, price scenario, quotation                  | Release 2 |
| Epic 5   | Actual & Variance        | Actual consumption/settlement, variance                          | Release 3 |
| Epic 6   | Optimization & Analytics | Batch scenario, BI, sensitivity                                  | Later     |

# 13. Feasibility & Risk

| **Khía cạnh** | **Đánh giá**                                                                       | **Hành động**                                        |
|---------------|------------------------------------------------------------------------------------|------------------------------------------------------|
| Technical     | Khả thi với PostgreSQL + Django; cần custom Formula Engine/DSL và version workflow | Prototype parser/resolver trước khi commit scope sâu |
| Data          | Workbook không chuẩn, magic number và UoM mixed                                    | Data profiling + mapping + golden master             |
| Operational   | Quy trình duyệt mới có thể tăng thời gian thay đổi giá                             | Thiết kế threshold approval + emergency rollback     |
| Security      | Sensitive margin/purchase price                                                    | RBAC/RLS + view/RPC + audit                          |
| Schedule      | Scope lớn nếu làm Standard + Actual + Marketplace cùng lúc                         | Triển khai theo phase, khóa MVP                      |

# 14. Sign-off / Exit Gate

- Project Charter, scope và success criteria đã được sponsor/Product Owner duyệt.

- BRD/SRS baseline có ID và owner; yêu cầu ưu tiên cao có acceptance criteria testable.

- Use Case, Business Rules và Data Dictionary đã review với nghiệp vụ.

- NFR về hiệu năng, bảo mật, audit, availability có cách đo.

- RTM baseline đã tạo.

- Rủi ro High có owner và mitigation.

- Backlog MVP được ưu tiên; các mục out-of-scope được ghi rõ.
