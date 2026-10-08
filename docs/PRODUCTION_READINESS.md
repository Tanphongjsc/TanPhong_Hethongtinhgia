# Deployment & Production Readiness — 08/10/2026

Phạm vi: production configuration/static/WSGI/probes/logging/safety/runbooks và
regression. Không sửa engine, Formula semantics, Golden expected values, business
schema/mappings, Auth/Organization workflow, Approval hoặc business Audit Log.
Chưa deploy thật. Thiết kế/cấu hình giới hạn truy cập được bỏ khỏi task theo yêu cầu
mới nhất của chủ dự án; không tạo gate xác nhận network boundary trong code.

Runbook thực thi duy nhất: đầu [06_DEPLOYMENT_DEVOPS.md](06_DEPLOYMENT_DEVOPS.md).
Các số thứ tự dưới đây khớp 43 mục acceptance/report của iteration.

## A. Environment

1. **Architecture:** `config.production` kế thừa `config.settings`, cho production/
   staging; local giữ settings cũ. Python 3.11.5/Django 5.2.17 đã test. Không tách
   settings thành framework mới; không Docker hoặc provider giả định.
2. **Variables:** APP_ENV/DJANGO_SETTINGS_MODULE, strong DJANGO_SECRET_KEY,
   DJANGO_ALLOWED_HOSTS, DB_HOST/PORT/NAME/USER/PASSWORD/SSLMODE và APP_TRANSPORT.
   Proxy/CSRF/HSTS/static/log/threads/timeout tùy target. Bảng đầy đủ trong runbook
   và [.env.production.example](../.env.production.example).
3. **Secrets:** process environment/secret store; production không đọc local .env.
   .env/.env.* thật, dumps/backups/caches ignored; examples chỉ placeholder.
4. **DEBUG:** production luôn False; cấu hình True bị từ chối trước startup.
5. **Hosts/CSRF:** hosts cụ thể, không wildcard/URL/port; exact trusted origins,
   same-origin mặc định; fail-fast invalid config. Không CORS wildcard.

## B. Database

6. **Supabase:** giữ session pooler port5432 hiện có, không đổi sang transaction
   pooling, không Supabase Auth/API/service_role.
7. **SSL:** require mặc định, production từ chối disable; credentials không hard-code.
8. **Schema:** mọi runtime connection `search_path=costing,public`. Preflight/readiness
   kiểm tra current_schema/search_path và costing.cost_element thực sự tồn tại.
   Đã kiểm tra SELECT/GET trên Supabase hiện có với production settings: PASS.
9. **Connections:** CONN_MAX_AGE60, health checks bật, connect_timeout10s; configurable.
   Không thay đổi engine query/performance tuning; đo connection budget trên target.
10. **Migration policy:** 51/51 business models vẫn unmanaged; không schema change,
    không migration. Deployment không có migrate/makemigrations/flush.

## C. Frontend

11. **Build:** npm ci với chính lockfile đã sửa PASS trong thư mục build sạch;
    npm run build (vendor + build:css) PASS, Tailwind4.3.3, không major upgrade.
    Chỉ thêm hai metadata bundled @emnapi/core/runtime thiếu; không đổi version
    trực tiếp hoặc version entry cũ. Windows node_modules cũ có native file bị Node
    giữ; không dừng process, đã khôi phục dependency từ clean install cùng version.
12. **Static:** WhiteNoise6.12.0, CompressedManifestStaticFilesStorage, 7 base assets
    hash/compression/cache immutable; raw Tailwind src bị loại khỏi collection.
    Không CDN, không static server thứ hai. Node chỉ cần build.
13. **Collectstatic:** production command exit0; 10 source assets, 30 post-process
    outputs. Manifest check PASS, gzip/hash/cache đã kiểm tra qua HTTP thật.

## D. Application

14. **App server:** Waitress3.0.2 WSGI, một process, default4 threads (configurable),
    defaultloopback8000, idle channel timeout120s; không deadline engine giả định.
15. **Start:** `python -m config.serve`; `--check` kiểm tra env/static/DB/context không
    bind, không writes. Đã start/stop process local với config.production thành công.
16. **Proxy:** chưa có proxy infra. Nếu chọn https_proxy: exact peer/IP + một hop,
    chỉ X-Forwarded-Proto được tin qua Waitress; Host canonical được giữ. Không thêm
    Nginx/config provider khi chưa có target. Django không tin header tùy ý trực tiếp.
17. **Liveness:** GET /health/200 với JSON tối thiểu; test0 DB/workspace/engine queries.
18. **Readiness:** GET /ready/200 khi DB/schema đúng,503 tối thiểu khi unavailable;
    mismatchschema/path/table đều được test. Supabase read-only runtime check PASS.
19. **Logging:** JSON stdout UTC aware/level/logger/message/env/trace_id; HTTP method/
    path/status/duration, engine run/scenario/stage context giữ nguyên. Redaction
    message/extras/traceback, không request body/query/header/debug SQL.

## E. Security

20. **Access scope:** không Auth/login/user permission; phần cấu hình giới hạn truy
    cập được loại khỏi task theo yêu cầu mới nhất. Default bind vẫn loopback; không
    tự mở port/firewall hoặc deploy public. Không cần APP_PRIVATE_ACCESS_ACK.
21. **CSRF:** middleware/token/HTMX conventions giữ nguyên; POST thiếu token403
    an toàn tiếng Việt. Không csrf_exempt; anonymous GET vẫn200.
22. **Headers/cookies:** nosniff, DENY frame, same-origin referrer; https_proxy bật
    redirect + secure CSRF/toast cookies; private_http chọn rõ. HSTS0 ban đầu, chỉ
    bật sau HTTPS verified. Không thêm CSP gây lỗi Alpine/HTMX.
23. **Secrets review:** scan447 source/doc/template/static/script files với secret
    đang cấu hình:0 matches; .env ignored và chưa committed; production example
    không ignored. Đây không phải kết luận scan toàn bộ Git history hoặc external logs.
24. **Command safety:** 3 DEMO commands bị chặn production trước query; chỉ dev/test/
    staging. manage.py test bắt buộc isolated settings; scripts/test.ps1 force test
    env. flush/migrate/makemigrations bị chặn production. Không deploy auto seed.
    Search keyword không có auth decorators/request.user/OrganizationMember runtime
    dependency mới: approved nullable DB fields, rejected fee candidates, metadata
    x-ref và read-only integrity audit là technical/compatibility, không workflow.

## F. Operations

25. **Backup:** runbook có project backup inventory/retention check, manual pg_dump
    costing custom-format, ACL-protected credentials, checksum/off-site evidence.
    Không giả định Supabase plan/PITR/backup đã đủ; thực tế chưa xác minh.
26. **Restore:** scratch target riêng, external FK/role/extension prerequisites,
    pg_restore exit-on-error/single-transaction, verify tables/constraints/triggers/
    sequences/hashes/snapshots rồi smoke. Không --clean/disable-FK/restore production
    để thử. Legacy auth.users FK có thể là dependency backup dù runtime không Auth.
27. **Deploy:** prepare_release.py build/check, artifact N + N-1, test/staging gates,
    drain in-flight, start canonical command, read-only smoke; không DB mutation script.
28. **Rollback:** code+manifest cùng N-1, giữ database/snapshots/history, không reset/
    seed/restore DB để rollback code. Chưa diễn tập trên target thực tế chưa được cung cấp.
29. **Restart/recovery:** runbook yêu cầu supervisor auto-start/restart-on-failure,
    backoff/log capture/rotation và recovery matrix cho crash/DB/static/bad release/
    exhaustion/CSRF. Service name/lệnh quản lý và reboot drill chờ server đích, không
    cài service manager tùy tiện trong task.

## G. Regression — evidence

30. `python manage.py check`: PASS,0 issues; pip check PASS.
31. Targeted deployment suite16 tests PASS; full suite **734/734 PASS**,0 skipped,
    **217.149s**, Chromium và volume benchmark được bật. Exitcode0, local PostgreSQL
    test đã dừng sau suite. Không dùng production credentials trong automated tests.
32. Golden Costing independent expected/actual delta0: material260000 + packaging
    150000 + resource120000 = direct530000; overhead53000; total583000/10 hộp;
    **unit58300 VND**. Future total647000/unit64700; history/snapshot unchanged.
33. Golden Pricing delta0: price89972.41379310, fee5498.62068966, tax8179.31034483,
    profit17994.48275861, margin0.2. Future92526.00506044, margin0.2; Costing unchanged.
34. Comparison regression PASS: snapshot/hash/basis/selection/deltas/history/full/
    HTMX/browser tests nằm trong full suite; không evaluate lại engine bằng GET.
35. DEBUG=False smoke PASS qua Waitress/WhiteNoise trên test DB và **config.production
    thật** trên localhost, Supabase existing chỉ SELECT/GET: **22 checks PASS**,
    root/workspace/Item/Product/SKU/BOM/Packaging/Formula/Run/Scenario/Compare/probes/
    HTMX/assets. Fingerprints Runs/Scenarios trước–sau không đổi; không phải deploy
    vào production server. Production-like browser PASS, screenshot đã kiểm tra.
36. Static smoke PASS đủ7 CSS/JS assets; hash/gzip/immutable/cache, safe404/500 vẫn
    load CSS; CSRF403 giữ enforcement. `check --deploy --fail-level=ERROR` exit0:
    W004/W008/W016 được ghi rõ vì transport HTTP của local smoke và HSTS chưa bật,
    không bị silenced. Chưa kiểm chứng TLS gateway của target.

Evidence local (ignored, không secrets/backup payload):

- `artifacts/production-final-regression.log`, `production-targeted.log`
- `artifacts/production-http-smoke.json` (test fixtures + Golden reports)
- `artifacts/production-runtime-smoke.json` (production settings + Supabase read-only)
- `artifacts/production-preflight.log`, `production-runtime.log`
- `artifacts/production-source-review.json`
- `artifacts/screenshots/production-waitress.png`

## H. Files

37. **Created:** `.env.production.example`, `requirements-production.txt`;
    `config/production.py`, `checks.py`, `command_safety.py`, `health.py`, `logging.py`,
    `serve.py`, `staticfiles.py`; `scripts/prepare_release.py`, `smoke_production.py`;
    `apps/master_data/test_deployment.py`; tài liệu này. Artifact harness/evidence
    không thuộc source release. Không files deleted.
38. **Modified:** `.gitignore`, `.env.example`, `package-lock.json`, `manage.py`,
    `config/settings.py`, `test_settings.py`, `urls.py`; `apps/master_data/middleware.py`;
    3 management commands seed_costing_demo/verify_costing_demo/verify_pricing_demo;
    `scripts/test.ps1`; CSS/vendor generated lại bằng build. Không sửa business services/
    selectors/forms/engine/models/templates hoặc Golden expected values.
39. **Docs:** README, docs/00_AI_CONTEXT.md, 03_SYSTEM_ARCHITECTURE.md,
    04_ENGINEERING_GUIDE.md, 05_QA_TESTING.md, 06_DEPLOYMENT_DEVOPS.md,
    07_OPERATIONS_MAINTENANCE.md và report này. Không duplicate deployment guide;
    runbook ở file06 hiện có, report này chỉ ghi kết quả/gates.

## I. Remaining

40. **P0 remaining:** không phát hiện từ các kiểm tra đã chạy. Financial Golden,
    source secret scan, history fingerprints, model mappings và schema-read probes PASS.
41. **P1 / cutover blockers:**
    - Chưa có production server/provider, transport/canonical hostname/port thực tế
      hoặc process manager/service identity. Chưa thể xác minh start-on-reboot,
      restart/log capture/rotation và rollback N→N-1 trên target.
    - Backup đang bật/retention/backup gần nhất và restore drill trên scratch target
      thực tế chưa được xác nhận. Cần evidence bảo vệ dữ liệu lịch sử trước cutover.
    - Post-deploy smoke trên **server đích** chưa thể chạy; local production smoke
      không thay bằng chứng vận hành target. Phần giới hạn truy cập không được đưa
      lại làm blocker trong task này theo yêu cầu mới nhất của chủ dự án.
42. **P2/P3:** connection/thread/timeout tuning theo workload target, monitoring/log
    retention/SLO owner, Python patch selection và dependency supply-chain checks
    rộng hơn chưa triển khai; không CI/provider/monitoring stack mới.
43. **Known limits:** chưa deploy thật hoặc backup/restore live; không test proxy TLS
    hoặc supervisor reboot. Requirements pin direct dependencies, chưa có full
    hash-locked Python transitive set. Static/app single process chưa có SLA/load
    capacity trên server thực tế. Scan secret không bao gồm Git history hoặc external
    stores. Những việc này không được biểu diễn thành PASS bằng giả định.

**NOT READY FOR PRODUCTION DEPLOYMENT**

Code/config/build/regression đã hoàn tất phần chuẩn bị. Để cutover cần server/process
manager cụ thể, backup/restore evidence và smoke/restart/rollback trên server đó.
Không tự triển khai feature hoặc chọn provider/deploy tiếp.
