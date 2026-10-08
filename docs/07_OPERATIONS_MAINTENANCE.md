**BỘ HỒ SƠ VÒNG ĐỜI PHÁT TRIỂN PHẦN MỀM**

> **Operations preparation 08/10/2026:** đã có `/health/` (không DB), `/ready/`
> (DB/schema nhẹ), JSON stdout/trace_id/redaction, command guards và read-only smoke.
> Start/preflight/restart/rollback/backup/restore/troubleshooting thực thi ở đầu
> [06_DEPLOYMENT_DEVOPS.md](06_DEPLOYMENT_DEVOPS.md). Chưa có target/service manager,
> log retention/rotation, RPO/RTO hoặc restore/reboot evidence production được xác nhận;
> các SLA/backup/SLO baseline phía dưới không phải cấu hình đang chạy.

> **Current scope 08/10/2026:** không Auth/role review, multi-company, Approval
> hoặc user Audit runtime; các yêu cầu cũ tương ứng phía dưới đã superseded.
> Giữ technical logs/trace_id, version/effective dates, snapshots/hash/explain,
> Golden canary và historical integrity. Không queue/worker trong runtime hiện tại.
> SLO/p95 bên dưới là mục tiêu đề xuất: benchmark hardening chỉ chạy local,
> process ấm, tải tuần tự; chưa chứng nhận production SLO, HA, DR hoặc alerting.
> [SYSTEM_HARDENING.md](SYSTEM_HARDENING.md) ghi phạm vi và bằng chứng hiện có.

06 - VẬN HÀNH, BẢO TRÌ & TỐI ƯU

Monitoring, Operations & Maintenance - SLO, observability, incident, security, capacity và continuous improvement

| Mã tài liệu   | SDLC-06                                                                                |
|---------------|----------------------------------------------------------------------------------------|
| Phiên bản     | 1.0                                                                                    |
| Trạng thái    | Baseline đề xuất - cần phê duyệt theo dự án                                            |
| Công nghệ nền | Django + Supabase PostgreSQL (baseline hiện tại)                                       |
| Phạm vi       | Costing & Pricing Engine: giá thành, giá bán, Formula/Rule Engine, BOM, version, audit |

# Mục lục nội dung

> **1. Service ownership**
>
> **2. SLA/SLO/SLI**
>
> 3\. Observability architecture
>
> 4\. Metric catalogue
>
> 5\. Logging & tracing
>
> 6\. Alert matrix
>
> 7\. On-call & incident response
>
> 8\. Post-mortem/RCA
>
> 9\. Database maintenance
>
> 10\. Security maintenance
>
> 11\. Backup/DR drills
>
> 12\. Capacity & cost optimization
>
> 13\. Business monitoring
>
> 14\. Maintenance calendar
>
> 15\. Continuous improvement

# 1. Service Ownership

| **Vai trò**      | **Trách nhiệm**                                     |
|------------------|-----------------------------------------------------|
| Service Owner    | Chịu trách nhiệm business/operational outcome       |
| Technical Owner  | Architecture, reliability, technical roadmap        |
| On-call Engineer | Incident response theo lịch                         |
| DBA/Data Owner   | Database health, backup, integrity, data governance |
| Security Owner   | Vulnerability/incident/security review              |
| Business SME     | Validate costing/pricing anomaly                    |

# 2. SLA / SLO / SLI

SLI (Service Level Indicator - Chỉ số mức dịch vụ) là số đo; SLO (Service Level Objective - Mục tiêu mức dịch vụ) là mục tiêu nội bộ; SLA (Service Level Agreement - Cam kết mức dịch vụ) là cam kết chính thức với bên sử dụng nếu có.

| **SLI**                | **Định nghĩa**                       | **SLO baseline**                  |
|------------------------|--------------------------------------|-----------------------------------|
| Availability           | Successful eligible requests / total | 99.9%/tháng (đề xuất để xác nhận) |
| Single Costing Latency | p95 create/calculate                 | \< 500 ms khi data đã cache       |
| Explain Latency        | p95 explain                          | \< 1 s                            |
| Error Rate             | 5xx/domain unexpected / total        | \< 0.5% (đề xuất)                 |
| Worker Success         | successful jobs / attempted          | \> 99.5% (đề xuất)                |
| Audit Completeness     | controlled changes có audit event    | 100%                              |

# 3. Observability Architecture

<img src="media/image1.png" style="width:6.7in;height:0.83297in" />

Hình 1. Incident lifecycle - vòng xử lý sự cố từ phát hiện tới hành động phòng ngừa.

| **Pillar**                 | **Nội dung**                                                                 |
|----------------------------|------------------------------------------------------------------------------|
| Metrics - Số liệu đo       | Request rate, latency, error, DB/worker/cache, business calculation failures |
| Logs - Nhật ký             | Structured JSON; trace_id/run_id/company/module/error_code; redact secrets   |
| Traces - Dấu vết phân tán  | API → service → resolver → DB/adapter; sampling policy                       |
| Events - Sự kiện nghiệp vụ | Formula activated, rule changed, costing run approved, override approved     |

# 4. Metric Catalogue

| **Metric**                      | **Mục đích**         | **Theo dõi**                            |
|---------------------------------|----------------------|-----------------------------------------|
| http_request_duration_seconds   | API latency          | p50/p95/p99 by endpoint/status          |
| http_requests_total             | Traffic/error        | rate; 4xx/5xx                           |
| costing_run_duration_seconds    | Engine latency       | by scheme/run_type                      |
| costing_run_failures_total      | Calculation failures | error_code: missing_rate/dimension/etc. |
| formula_validation_duration     | Formula validation   | latency/error                           |
| rule_resolution_ambiguous_total | Ambiguous rules      | should approach 0                       |
| db_connections/locks/query time | Database             | capacity/contention                     |
| worker_queue_depth/job_age      | Async worker         | backlog                                 |
| override_count                  | Business control     | manual override trend                   |
| price_margin_below_floor_count  | Business risk        | guardrail trigger                       |

# 5. Logging & Tracing

| **Rule**         | **Nội dung**                                                                                           |
|------------------|--------------------------------------------------------------------------------------------------------|
| Required context | timestamp, level, service, env, trace_id, request_id, company_id, user_id, run_id, version_id          |
| Never log        | Password/token/service role, full sensitive price data khi không cần, PII vượt mục đích                |
| Domain error     | error_code + safe message + context IDs                                                                |
| External calls   | provider, latency, status, retry count, correlation id; raw payload chỉ theo retention/security policy |
| Sampling         | Error traces 100%; success traces sampled theo volume                                                  |

# 6. Alert Matrix

| **Severity** | **Trigger ví dụ**                                              | **Channel**           | **SLA phản hồi** |
|--------------|----------------------------------------------------------------|-----------------------|------------------|
| P1           | API 5xx \> 5% 5 phút / DB unavailable / data corruption signal | Pager + Slack         | Immediate        |
| P1           | Unauthorized cross-tenant evidence / secret leak               | Security escalation   | Immediate        |
| P2           | p95 \> 1s sustained / queue age high                           | Slack/on-call         | 15 min           |
| P2           | Backup failure / PITR unavailable                              | On-call/DBA           | 30 min           |
| P3           | Disk/storage growth / slow query trend                         | Ticket                | Business hours   |
| Business     | Margin-below-floor spike / rule ambiguous                      | Pricing/Costing owner | Same day         |

# 7. On-call & Incident Response

1.  Acknowledge alert và gán Incident Commander nếu P1/P2.

2.  Triage: phạm vi user/company/module/release/version nào bị ảnh hưởng.

3.  Contain: disable feature/adapter/config version nếu có thể.

4.  Recover: rollback/activate previous version/restore service.

5.  Verify business correctness bằng known scenario và data checks.

6.  Communicate status theo cadence.

7.  Close khi metrics bình thường và risk tạm thời được kiểm soát.

8.  Post-Mortem/RCA trong thời hạn quy định.

# 8. Incident Post-Mortem / RCA

| **Mục**              | **Nội dung**                              |
|----------------------|-------------------------------------------|
| Summary              | Điều gì xảy ra, impact, duration          |
| Timeline             | Detect → actions → recovery               |
| Root Cause           | Nguyên nhân gốc, không chỉ triệu chứng    |
| Contributing Factors | Test gap, process, monitoring, dependency |
| What went well       | Điều giúp giảm impact                     |
| What went poorly     | Điểm cần cải thiện                        |
| Corrective Actions   | Owner + due date + priority               |
| Evidence             | Logs/traces/queries/release/config IDs    |

# 9. Database Maintenance

| **Cadence** | **Hoạt động**                                                                              |
|-------------|--------------------------------------------------------------------------------------------|
| Weekly      | Slow query review, failed jobs, index health, connection/lock anomalies                    |
| Monthly     | Growth, table/index bloat indicators, retention/archive candidates, restore metadata check |
| Quarterly   | Restore drill, query plan benchmark, partitioning need review                              |
| On change   | Analyze new indexes/queries/migrations; update statistics if needed                        |

# 10. Security Maintenance

- Patch framework/runtime/dependencies theo severity SLA.

- Rotate secrets/keys theo policy và khi incident/personnel change.

- Review privileged roles và company membership định kỳ.

- Review RLS/permission tests khi schema/API thay đổi.

- Security findings và exceptions phải có owner/expiry.

- Audit access to sensitive margin/purchase prices nếu policy yêu cầu.

# 11. Backup / DR Drills

| **Control**   | **Cadence**                                                       |
|---------------|-------------------------------------------------------------------|
| Backup status | Daily automated check                                             |
| Restore drill | Quarterly hoặc theo criticality                                   |
| PITR drill    | Khi service plan hỗ trợ và trước major release định kỳ            |
| DR tabletop   | 6-12 tháng                                                        |
| Evidence      | Restore duration, recovered point, checksum/count, issues/actions |

# 12. Capacity & Cost Optimization

| **Area**             | **Optimization**                                                       |
|----------------------|------------------------------------------------------------------------|
| Database             | Top queries, cache hit, indexes, connection pool, storage growth       |
| Application          | CPU/memory/request concurrency; serialization size                     |
| Worker               | Queue depth, batch size, retries, job age                              |
| Cache                | Hit ratio; invalidation correctness; memory                            |
| Business computation | Reuse manufacturing base between scenarios when dependencies unchanged |
| Archival             | Immutable audit/run retention tiering when volume grows                |

# 13. Business Monitoring

| **Business Signal** | **Mục đích**                                                |
|---------------------|-------------------------------------------------------------|
| Cost variance       | Standard vs actual by material/usage/labor/FX/channel       |
| Rule change impact  | SKU/channel affected before/after activation                |
| Manual override     | Count/value/actor/reason; outlier                           |
| Margin floor breach | Scenario/order below floor                                  |
| Missing rate/FX     | Calculation blocked due to reference gaps                   |
| Golden canary       | Scheduled known scenario to detect silent calculation drift |

# 14. Maintenance Calendar

| **Cadence** | **Hoạt động**                                                                    |
|-------------|----------------------------------------------------------------------------------|
| Daily       | Alert review, failed jobs, integration errors, backup status                     |
| Weekly      | Slow queries, queue backlog, error trends, pending security findings             |
| Monthly     | Dependency patching, role review, DB growth, SLO report, business anomaly review |
| Quarterly   | Restore drill, performance benchmark, access/RLS review, capacity forecast       |
| Semiannual  | DR tabletop, architecture health review, data retention/archive                  |
| Annual      | SLA/SLO review, major dependency/runtime upgrade roadmap                         |

# 15. Continuous Improvement

Mọi incident, performance regression, business discrepancy hoặc repeated manual workaround phải tạo feedback item quay lại backlog của Giai đoạn 1/2. SDLC là vòng lặp, không kết thúc ở production.
