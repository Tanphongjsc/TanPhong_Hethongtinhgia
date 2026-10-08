**BỘ HỒ SƠ VÒNG ĐỜI PHÁT TRIỂN PHẦN MỀM**

## Runbook hiện hành — 08/10/2026

Phần này là hướng dẫn thực thi hiện tại; các mục SDLC 1–14 phía dưới là baseline
cũ. Container, Kubernetes, migration, queue, auth/role, approval và audit trong
baseline **không phải yêu cầu runtime hoặc command triển khai hiện tại**.
Chưa có production target nên chưa deploy thật. Theo yêu cầu mới nhất của chủ
dự án, thiết kế/cấu hình giới hạn truy cập không nằm trong task này; không có gate
`APP_PRIVATE_ACCESS_ACK` hoặc authentication được thêm vào ứng dụng.

### 1. Runtime và artifact

- Python 3.11 (đã kiểm thử 3.11.5), Django 5.2.17; chọn patch Python trên server
  và chạy lại regression trước khi promote. Giữ dependencies hiện tại.
- Một process WSGI **Waitress 3.0.2**, mặc định 4 threads; **WhiteNoise 6.12.0**
  phục vụ static cùng process. Chưa dùng Docker, Nginx, Gunicorn, Redis/Celery.
- Node 24.11.0/npm 11.6.1 dùng lúc build, Tailwind 4.3.3, HTMX/Alpine local.
  Runtime sau build không cần Node/npm, Playwright hoặc local PostgreSQL test.
- Mỗi release có source, requirements, templates, static source + output vendor/CSS,
  `staticfiles/` và manifest cùng một build. Ghi commit/release ID và SHA256 artifact.
  Không đóng gói `.env*` thật, `env/`, `.test-postgres/`, node_modules, artifacts test,
  backup, cache hay credentials. Chỉ giữ env examples với placeholder.
- Không dùng `runserver` trong production. Một start command duy nhất:

```text
python -m config.serve
```

### 2. Environment và secrets

`config/settings.py` phục vụ development; `config/production.py` kế thừa tối thiểu
cho production/staging. Chỉ development đọc `.env` tự động. Production nhận biến
môi trường từ service/process manager hoặc secret store, **không tự đọc** `.env`,
`.env.production` hay `.env.production.example`. Không copy example thành secret
file trong source rồi mong app tự load.

| Biến | Cách cấu hình |
|---|---|
| `APP_ENV` | `production` hoặc `staging` |
| `DJANGO_SETTINGS_MODULE` | `config.production` |
| `DJANGO_SECRET_KEY` | Secret ngẫu nhiên >=50 ký tự, không placeholder; thiếu/sai thì fail startup |
| `DJANGO_DEBUG` | `False`; `True` bị từ chối |
| `DJANGO_ALLOWED_HOSTS` | Hostname/IP cụ thể, phân cách dấu phẩy; không wildcard, URL, port |
| `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` | Supabase PostgreSQL credentials hiện có; tất cả bắt buộc |
| `DB_SSLMODE` | `require` mặc định; hoặc verify-ca/verify-full khi đã cấu hình CA phù hợp |
| `DB_CONNECT_TIMEOUT` | 10 giây mặc định, configurable 1–60 |
| `DB_CONN_MAX_AGE` | 60 giây mặc định, configurable 0–3600; connection health checks bật |
| `APP_MODE` | `single_company`, giữ compatibility FK hiện có |
| `DEFAULT_ORGANIZATION_ID` | Chỉ cần khi helper nội bộ không resolve được duy nhất một công ty active; không UI/user flow |
| `APP_TRANSPORT` | Chọn rõ `private_http` hoặc `https_proxy` theo deployment thực tế |
| `APP_TRUSTED_PROXY` | Chỉ HTTPS proxy: exact TCP peer IP; không wildcard |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Thường để rỗng cho same-origin; nếu cần, exact origins có scheme, không wildcard/path |
| `DJANGO_SECURE_HSTS_SECONDS` | Mặc định 0; chỉ >0 khi HTTPS verified và `APP_HTTPS_VERIFIED=True` |
| `LOG_LEVEL` | INFO mặc định; WARNING/ERROR/CRITICAL được phép, không DEBUG |
| `DJANGO_STATIC_ROOT` | Tùy chọn absolute release-specific directory; mặc định `<release>/staticfiles` |
| `APP_BIND/APP_PORT` | `127.0.0.1:8000` mặc định; cấu hình theo target thực tế |
| `APP_THREADS` | 4 mặc định, configurable; đo workload và DB connection budget trước khi tăng |
| `APP_CHANNEL_TIMEOUT` | 120 giây idle connection timeout; không phải execution deadline của engine |

Xem [.env.production.example](../.env.production.example). Sinh secret bằng công cụ
secret của đơn vị vận hành; không ghi secret vào terminal history, source hoặc báo cáo.
Process chỉ cần read source/templates/static và DB DML phù hợp, không quyền DDL
cho business schema. Build user ghi static output; runtime user không cần ghi source.
Log stdout được process manager thu thập/rotate; nếu ghi file, chỉ cấp quyền thư mục
log riêng. Hiện chưa có upload/import storage cần triển khai.

### 3. Supabase PostgreSQL và schema

Kết nối hiện tại là **session pooler, port 5432**, SSL `require`; giữ nguyên endpoint
và mode, không đổi sang transaction pooler 6543. Đây là kết nối PostgreSQL, không
Supabase Auth/API/service_role. Connection mode được phân biệt theo
[hướng dẫn kết nối Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

Mọi connection đặt `options=-c search_path=costing,public`. `/ready/` và preflight
kiểm tra `current_schema()=costing`, `search_path=costing,public` và bảng
`costing.cost_element` tồn tại; không âm thầm fallback public khi schema thiếu.
Toàn bộ 51 business mappings giữ `managed=False`; không có business migration mới.
Installed apps không cần auth/contenttypes/session framework migrations.
**Không chạy `makemigrations`, `migrate`, `flush` trong deployment này.**
Không có SQL schema rollout mới; nếu schema lệch, dừng release và review DB riêng.

Với một process/4 threads, theo dõi connections thực tế trước khi tăng process/threads.
Không dùng transaction pooler để chữa exhaustion mà chưa review session semantics.
Không log connection URI/password. Readiness không thực thi Costing/Pricing hoặc seed.

### 4. Build, collectstatic và preflight

Từ release directory, sau khi service environment đã được cấp:

```text
python -m pip install -r requirements-production.txt
npm ci
npm run build
python manage.py collectstatic --noinput --settings=config.production
python manage.py check --deploy --fail-level=ERROR --settings=config.production
python -m config.serve --check
```

Hoặc sau khi cài Python dependencies, chạy `python scripts/prepare_release.py` để
thực hiện cùng chuỗi build/check. Script **không** deploy, restart, migrate hoặc seed.
`npm run build` gồm copy vendor local và `npm run build:css` minify. Không chỉnh CSS
generated trực tiếp. Lockfile đã bổ sung hai bundled metadata thiếu của WASM optional
dependencies; không đổi version dependencies trực tiếp hoặc version entry hiện có.

WhiteNoise đặt ngay sau SecurityMiddleware; dùng CompressedManifestStaticFilesStorage,
hashed assets/cache immutable, không static finder ở runtime. `BuiltAssetFinder`
loại `static/src/` khỏi collection, tránh xử lý `@import tailwindcss` nguồn như asset.
Manifest check bắt buộc đủ 7 CSS/JS assets của base template, khác thư mục source.
`collectstatic` không dùng `--clear`. Strategy dựa trên
[WhiteNoise Django integration](https://whitenoise.readthedocs.io/en/stable/django.html).

`check --deploy` có thể cảnh báo W004 khi HSTS=0, W008/W016 khi chọn private_http.
Không bật HTTPS/HSTS giả để làm sạch warning. Ghi rõ transport đã chọn và review
các warning còn lại; ERROR luôn dừng release. Không blanket SILENCED_SYSTEM_CHECKS.

### 5. HTTP, TLS proxy và start mechanism

`python -m config.serve --check` kiểm tra env, static, DB schema và compatibility
context rồi thoát; `python -m config.serve` làm cùng preflight trước khi bind HTTP.
Waitress không expose traceback; body limit theo DATA_UPLOAD_MAX_MEMORY_SIZE của
Django. Một process, 4 threads là default khởi đầu, không phải tuning/SLO đã chứng minh.
Waitress hỗ trợ Windows/Unix; cấu hình peer/header và idle timeout theo
[Waitress arguments](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).

Không cài proxy/service manager khi chưa biết server. Nếu target có TLS gateway:
chọn https_proxy, gateway giữ Host canonical, overwrite X-Forwarded-Proto, forward
HTTP tới app, không tự phục vụ static song song; WhiteNoise vẫn là static owner.
App chỉ tin X-Forwarded-Proto từ exact peer đã cấu hình, một hop; Waitress chuyển
thành wsgi.url_scheme. Django không tin trực tiếp header tùy ý. HTTPS redirect và
CSRF/message secure cookie bật ở mode này; health/readiness được miễn redirect cho
probe nội bộ. Test origin/host/POST qua gateway trước khi bật HSTS. Chưa có proxy
configuration file giả định cho hạ tầng chưa chọn.

### 6. Probes, logging và smoke

- `GET /health/` =>200 `{"status":"ok"}`; không DB/company/engine query.
- `GET /ready/` =>200 ok hoặc503 unavailable; một query nhẹ kiểm tra DB/schema,
  không trả SQL, credentials, settings hoặc package versions. Hai endpoint validate Host.
- JSON stdout có timestamp UTC aware, level, logger, message, environment, trace_id;
  HTTP có method/path/status/duration_ms, không body/query/header/token. Existing
  engine failures giữ run/scenario/stage context trong message; không business Audit Log.
  Redaction áp dụng DB password, signing key, database URI, token/password assignments
  và traceback. Logger DB không DEBUG SQL. Người dùng chỉ thấy lỗi tiếng Việt + trace_id.
- UI giữ Asia/Ho_Chi_Minh/vi, ngày và Decimal không phụ thuộc server locale.
- Probe live production bằng script **chỉ GET**:

```text
python scripts/smoke_production.py --base-url https://your-canonical-host --report artifacts/post-deploy-smoke.json
```

Script kiểm tra root/business pages/Comparison, probes, HTMX partial và đủ 7 static
assets; không theo redirect khác origin, không tắt TLS verification, không login,
không mutation, không tự tạo dữ liệu. Dùng đúng canonical HTTP hoặc HTTPS URL.

### 7. Deployment, rollback, restart

1. Chốt server/provider, transport/host/port, service identity, log destination và
   process manager hiện có. Ghi owner và release ID; chưa có các giá trị này thì
   chỉ prepare artifact, không tự deploy vào dịch vụ khác.
2. Lưu release N-1 + manifest, environment version (không secrets trong Git),
   kiểm tra backup gần nhất và restore evidence. Không auto chạy DEMO.
3. Test staging/isolated DB: full suite + browser + Golden Costing/Pricing/Comparison.
   Tests luôn config.test_settings/localhost; không dùng production credentials.
4. Build release N, collectstatic/preflight PASS. Không copy đè code của process đang
   chạy. Chuyển traffic/maintenance theo cơ chế target; stop nhận request mới, đợi
   request đang tính hoàn tất trước khi dừng process. Grace period dựa trên duration
   dài nhất đã đo ở target, không suy từ idle channel_timeout.
5. Supervisor chạy command canonical với cwd/venv/env release N. Smoke chỉ đọc, kiểm
   tra log và HTTP errors. Không gọi engine trên production để smoke.
6. Nếu bad release: dừng traffic mới, đợi in-flight, dừng N; trỏ service/cwd/static
   về **cùng artifact N-1**, giữ DB và secrets nguyên, start, chạy lại smoke/readiness.
   Không rollback bằng DB restore, seed/reset hoặc xóa Run/Scenario. Nếu version N
   đã ghi dữ liệu không tương thích N-1, dừng và review riêng thay vì blind rollback.

Process manager chưa được chọn: với Windows dùng Windows service wrapper của đơn
vị vận hành; với Linux dùng supervisor/systemd đang có. Không cài manager trong task.
Service phải auto-start sau reboot, restart-on-failure có backoff, không vòng lặp
restart liên tục khi DB mất, capture stdout/stderr, chạy least-privilege identity.
Sau khi biết target, ghi service name và **lệnh stop/start/restart/status cụ thể**,
test crash/reboot/rollback N→N-1 trước cutover. Hiện mới có foreground start/preflight
đã kiểm thử; chưa có bằng chứng reboot/recovery trên production server.

### 8. Backup và restore database

Chưa xác minh plan Supabase, cơ chế backup hiện bật, retention, backup timestamp,
owner hoặc RPO/RTO thực tế. Kiểm tra Dashboard Database/Backups và ghi evidence;
không coi bảng retention baseline phía dưới là cấu hình đã có. Cơ chế/khả năng
download/PITR phụ thuộc project/plan, xem
[Supabase Database Backups](https://supabase.com/docs/guides/platform/backups).
Đề xuất để owner chốt: backup ngày + trước release, off-site encrypted copy,
restore drill định kỳ; đây chưa phải lịch/retention đã triển khai.

Manual logical export (không sửa DB), dùng PostgreSQL client tương thích server
major; xác minh server_version trước, không dùng client cũ hơn server. Cấp PGHOST,
PGPORT, PGDATABASE, PGUSER, PGSSLMODE từ cấu hình kết nối được phép; password qua
PGPASSFILE được ACL chặt chỉ backup identity đọc. Không URI có password/CLI history.
Chọn đường dẫn tuyệt đối **ngoài source/static/webroot**, không ghi đè backup cũ:

```text
pg_dump --format=custom --schema=costing --no-owner --no-privileges --file=<absolute-new-backup.dump>
pg_restore --list <absolute-new-backup.dump>
```

Ghi exit status, checksum, thời điểm, server/client versions, schema/table counts,
release ID và nơi lưu off-site; không ghi credentials. Backup costing bảo vệ master,
effective prices/rates, business versions/lines/formula/scheme, Runs+snapshots+
explain, Scenarios+snapshots+traces. Backup source **không** thay thế backup dữ liệu.

**Export một schema không tự bao gồm external dependencies**: legacy FKs actor có
thể tham chiếu auth.users, cùng roles/extensions nằm ngoài costing. Đây là dependency
DB còn giữ, không Supabase Auth runtime mới. Kiểm kê external FKs/extensions/roles
trước restore; nếu cần sử dụng project-level backup/restore hoặc backup prerequisites
được DBA review. Không tự tạo auth user, disable trigger/FK hoặc bỏ constraint để
ép restore. Quy tắc schema-only export theo
[pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html).

Restore drill **chỉ vào database/project scratch mới, không production/shared DB**:

1. Chọn backup/checksum, xác định timestamp và dữ liệu có thể mất; tạo target trống
   riêng đã xác minh host/database/role bằng checklist của DBA.
2. Chuẩn bị external dependencies/role mapping đúng backup. PG* environment phải
   trỏ target, không source; không lấy env production của app chạy lệnh restore.
3. Review `pg_restore --list`; dùng client tương thích và chạy:

```text
pg_restore --exit-on-error --single-transaction --no-owner --no-privileges --dbname=<isolated-restore-database> <absolute-backup.dump>
```

4. Không `--clean`, drop schema, truncate hoặc migration. Stop khi bất kỳ error;
   không coi partial restore là thành công. Grants cho runtime role là bước DBA
   review riêng vì dump không mang privileges. Transaction/exit behavior theo
   [pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html).
5. Đối chiếu 51 mapped tables, data counts, FK/CHECK/unique constraints và immutable
   triggers; sequence next values; Run header+lines/snapshot hashes, Scenario hashes,
   versions/effective dates trước/sau. Lưu fingerprints trước restore nếu có.
6. App staging cấu hình DB scratch, preflight/readiness, read-only smoke; có thể chạy
   `scripts/audit_demo_integrity.py` chỉ đọc nếu backup chứa DEMO. Không seed để chữa
   dữ liệu thiếu. Golden executions chỉ trên test fixtures/staging được phép.
7. Ghi thời gian restore và xác nhận RPO/RTO/owner. Không chuyển app production
   sang target restore hoặc xóa source để thử trong task này.

Chưa thực hiện backup/restore production; procedure không phải bằng chứng restore PASS.

### 9. Checklist trước và sau deploy

Trước deploy:

- [ ] Server/transport/process manager, start-on-reboot và log rotation đã xác định.
- [ ] DEBUG=False, secret thật ở secret store, không .env trong artifact/Git.
- [ ] ALLOWED_HOSTS/CSRF/proxy/cookies phù hợp transport; HSTS chỉ khi verified.
- [ ] DB SSL/session pooler/search_path readiness PASS; role/grants đủ, không DDL.
- [ ] Backup timestamp/checksum/retention/restore drill evidence và N-1 artifact có sẵn.
- [ ] Python deps/pip check, npm ci, Tailwind/vendor build, collectstatic/manifest PASS.
- [ ] Django check + production check (review warnings), full/Golden/Comparison PASS.
- [ ] App starts, health/readiness PASS, JSON logs/trace/redaction hoạt động.
- [ ] Không auth/user/approval/audit UI, không auto seed/migration/reset production.
- [ ] Rollback/restart/reboot đã diễn tập trên target.

Sau deploy:

- [ ] `smoke_production.py` PASS: root (302→workspace200), Item/Product/SKU/BOM/
  Packaging/Formula/Run/Scenario/Comparison, health/readiness và 7 CSS/JS assets.
- [ ] HTMX search/filter, Alpine state, CSRF POST hợp lệ và thông báo lỗi hoạt động.
- [ ] Database read, Vietnamese/number/date display đúng; không login redirect/401/403
  do auth, không debug traceback/500; CSRF403 vẫn đúng với POST thiếu token.
- [ ] Log collection, error rate/connections và supervisor status được kiểm tra.
- [ ] Release ID và rollback target đã ghi, không tạo data production để smoke.

### 10. Troubleshooting / recovery

| Sự cố | Phát hiện | Xử lý tức thời / phục hồi / xác minh |
|---|---|---|
| App crash/start failure | Supervisor exit, health không200 | Xem JSON startup log/config; sửa env hoặc rollback artifact; start lại, probes+smoke |
| DB unavailable | health200, ready503, business500 an toàn | Kiểm tra Supabase/network/SSL/credentials bằng kênh vận hành; không seed/reset; chờ DB phục hồi, ready+read-only smoke |
| Sai schema/search_path | ready503, preflight từ chối | Kiểm tra endpoint/role/schema; không tạo costing hoặc fallback public; DBA review, preflight lại |
| Static thiếu | costing.E002, CSS/JS404 | Build vendor/CSS + collectstatic trong đúng release; dùng manifest cùng source, restart và asset smoke |
| Bad release | Regression/5xx/smoke fail | Drain in-flight, rollback N-1 code+static, giữ DB; probes+smoke, đối soát snapshot nếu cần |
| DB exhaustion | DB logs/connections cao, ready503 | Giảm traffic/concurrency, kiểm tra leaks/long transactions; không tăng threads/max_age mù quáng, khôi phục rồi kiểm tra DB + app |
| CSRF403 / redirect loop | Safe lỗi VI / repeated301 | Kiểm tra canonical host/origin/scheme/exact proxy peer/cookies; không csrf_exempt hoặc tin wildcard header |
| npm ci EPERM Windows | Native .node file bị process giữ | Build trong release directory sạch riêng; không xóa/kill process đang phục vụ. Lockfile chính vẫn phải hợp lệ |

Evidence và blockers hiện tại: [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md).

---

> **Current scope 08/10/2026:** internal single-company, truy cập trực tiếp, không
> Auth/user/role, Approval/Maker-Checker hoặc business Audit Log. Các checklist
> auth/cross-company/approval/actor audit phía dưới đã superseded. Organization
> chỉ còn FK compatibility nội bộ. Hiện không Celery/Redis/worker requirement;
> Costing/Pricing chạy synchronous, Comparison chỉ đọc persisted snapshots.
> Không chạy business migrations; schema costing đã được quản lý database-first.
> Task hardening chỉ đánh giá sẵn sàng *chuẩn bị* deployment; chưa deploy, chưa
> xác nhận backup/restore, RPO/RTO, network, TLS, production monitoring hoặc UAT.
> Các nội dung triển khai còn lại là gate cho giai đoạn sau, không phải bằng chứng
> đã hoàn tất. [SYSTEM_HARDENING.md](SYSTEM_HARDENING.md).

05 - TRIỂN KHAI & DEVOPS

Deployment & DevOps - môi trường, CI/CD, migration, cutover, rollback, backup và DR

| Mã tài liệu   | SDLC-05                                                                                |
|---------------|----------------------------------------------------------------------------------------|
| Phiên bản     | 1.0                                                                                    |
| Trạng thái    | Baseline đề xuất - cần phê duyệt theo dự án                                            |
| Công nghệ nền | Django + Supabase PostgreSQL (baseline hiện tại)                                       |
| Phạm vi       | Costing & Pricing Engine: giá thành, giá bán, Formula/Rule Engine, BOM, version, audit |

# Mục lục nội dung

> **1. Environment strategy**
>
> **2. CI/CD pipeline**
>
> 3\. Artifact & versioning
>
> 4\. Database deployment
>
> 5\. Secrets/config
>
> 6\. Release readiness
>
> 7\. Deployment runbook
>
> 8\. Cutover/data migration
>
> 9\. Rollback plan
>
> 10\. Backup & restore
>
> 11\. Disaster recovery
>
> 12\. Zero-downtime options
>
> 13\. Post-deploy validation
>
> 14\. Exit Gate

# 1. Environment Strategy

| **Environment** | **Mục đích**        | **Data**                                 | **Policy**                            |
|-----------------|---------------------|------------------------------------------|---------------------------------------|
| Local/Dev       | Developer iteration | Synthetic/seed                           | Debug enabled; no production secrets  |
| CI              | Automated ephemeral | Fixtures                                 | Fresh migrations + tests              |
| Staging         | Production-like     | Masked/synthetic + representative volume | Full integration/perf sanity          |
| UAT             | Business acceptance | Golden scenarios                         | Stable release candidate              |
| Production      | Live                | Live data                                | Strict access/audit/backup/monitoring |

# 2. CI/CD Pipeline

<img src="media/image1.png" style="width:6.7in;height:0.3469in" />

Hình 1. Continuous Integration / Continuous Delivery (CI/CD - Tích hợp liên tục / Phân phối liên tục).

| **Stage**           | **Nội dung**                                              |
|---------------------|-----------------------------------------------------------|
| PR Validation       | Lint/format, unit, SAST, migration check, dependency scan |
| Build               | Immutable container artifact tagged commit SHA/version    |
| Staging             | Auto deploy; migration dry run/execute; smoke/integration |
| Release Candidate   | E2E, UAT evidence, change log, DB compatibility           |
| Production Approval | Manual approval cho production                            |
| Deploy              | Rolling/Blue-Green tùy hạ tầng; DB backward-compatible    |
| Verify              | Smoke + business synthetic transaction + SLO watch        |
| Close               | Tag/release notes/RTM/update change record                |

# 3. Artifact & Versioning

| **Artifact**      | **Version key**                 | **Rule**                                |
|-------------------|---------------------------------|-----------------------------------------|
| Application       | Semantic version + commit SHA   | Không rebuild cùng tag                  |
| Container         | Registry digest                 | Promote same image staging→prod         |
| Database          | Migration version               | Applied migration log                   |
| Configuration     | Versioned non-secret config     | Diff reviewed                           |
| Formula/Rule data | Business version/effective date | Không gộp với app release nếu không cần |
| Docs              | Release documentation version   | Link release/build                      |

# 4. Database Deployment Strategy

1.  Additive migration trước: thêm table/column/index nullable/backward-compatible.

2.  Deploy application có thể chạy với old+new schema trong cửa sổ chuyển tiếp.

3.  Backfill data bằng job/batch có checkpoint.

4.  Switch read/write path khi backfill verified.

5.  Enforce constraint/drop old column ở release sau nếu cần.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Nguyên tắc quan trọng<br />
</strong>Application rollback chỉ an toàn nếu database migration vẫn tương thích. Vì vậy schema migration cần forward-compatible, tránh DROP/RENAME destructive trong cùng release.</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 5. Secrets & Configuration

| **Config**              | **Nơi lưu**                | **Guardrail**                    |
|-------------------------|----------------------------|----------------------------------|
| Database URL            | Secret manager/environment | Không log                        |
| Supabase service role   | Trusted backend only       | Tuyệt đối không client-side      |
| JWT/Auth config         | Environment                | Rotation/expiry                  |
| External API keys       | Secret manager             | Per environment                  |
| Feature flags           | Config store/DB            | Có owner/expiry                  |
| Business rates/formulas | Database versioned config  | Không hard-code .env/source code |

# 6. Release Readiness Checklist

- Release candidate build immutable và đã test đúng artifact.

- Migration plan + estimated duration + lock impact đã review.

- Backup/PITR status checked; restore procedure available.

- Rollback compatibility verified.

- Runbook có owner và communication channel.

- Monitoring dashboards/alerts cho feature mới đã active.

- Known issues/waivers documented.

- UAT/business approval attached.

- Support/on-call informed.

# 7. Deployment Runbook

| **Mốc**  | **Bước**                                                      | **Owner**       |
|----------|---------------------------------------------------------------|-----------------|
| T-30 min | Freeze/deploy window; verify backup, DB health, queue backlog | DevOps          |
| T-20     | Apply pre-deploy compatible migrations                        | DBA/DevOps      |
| T-15     | Deploy app to staging slot/canary                             | DevOps          |
| T-10     | Smoke internal endpoints + DB migrations state                | QA/DevOps       |
| T-5      | Shift traffic / rollout production                            | DevOps          |
| T+5      | Run synthetic costing scenario + authorization test           | QA/Business     |
| T+15     | Check error rate/p95/DB CPU/locks                             | SRE             |
| T+30     | Decision: complete / continue observation / rollback          | Release Manager |

# 8. Cutover & Data Migration

| **Phase**         | **Nội dung**                                                 |
|-------------------|--------------------------------------------------------------|
| Preparation       | Final source inventory; mapping sign-off; freeze window      |
| Dry run           | Run import staging; measure duration/error; reconcile counts |
| Cutover           | Backup; final delta import; promote; verify                  |
| Validation        | Record counts, sums, golden costing scenarios, spot checks   |
| Business sign-off | Key users confirm master/rates/schemes                       |
| Archive           | Keep source files/hash/mapping/report                        |

# 9. Rollback Plan

| **Tình huống**             | **Rollback/Recovery**                                                 | **Ghi chú**     |
|----------------------------|-----------------------------------------------------------------------|-----------------|
| App failure, DB compatible | Rollback container/app version                                        | Immediate       |
| Migration additive issue   | Disable feature flag; forward-fix data/schema                         | Preferred       |
| Bad business config        | Retire new formula/rule version; activate previous approved version   | No app rollback |
| Data corruption            | Stop writes; restore/PITR or corrective script after incident command | High severity   |
| External integration issue | Disable adapter/queue consumer; fallback/manual path                  | Containment     |

# 10. Backup & Restore

| **Asset**              | **Mechanism**                                   | **Cadence**                  | **Validation**                             |
|------------------------|-------------------------------------------------|------------------------------|--------------------------------------------|
| Database               | Supabase/Postgres backup + PITR nếu plan hỗ trợ | Daily/continuous per service | Restore drill quarterly                    |
| Object Storage         | Versioning/retention nếu cần                    | Policy-based                 | Verify critical evidence                   |
| Config/Code            | Git + registry                                  | Per commit/release           | Immutable tags                             |
| Business configuration | Database versions + audit                       | Every change                 | Export snapshot for major release optional |

# 11. Disaster Recovery (DR)

RTO (Recovery Time Objective - Mục tiêu thời gian khôi phục) và RPO (Recovery Point Objective - Mục tiêu điểm khôi phục dữ liệu) phải được business xác nhận. Baseline dưới đây là ví dụ khởi đầu, không phải cam kết SLA tự động.

| **Scenario**                    | **Target baseline**                    | **Recovery**                                             |
|---------------------------------|----------------------------------------|----------------------------------------------------------|
| Database unavailable            | RTO 4h / RPO 15m (đề xuất để xác nhận) | Restore/failover theo khả năng nền tảng; integrity check |
| Application region/host failure | RTO 2h                                 | Redeploy immutable artifact sang hạ tầng dự phòng        |
| Bad deployment                  | RTO 30m                                | Rollback application / disable feature                   |
| Business config error           | RTO 15m                                | Activate previous approved business version              |

# 12. Deployment Architecture

<img src="media/image2.png" style="width:6.7in;height:2.11542in" />

Hình 2. Topology triển khai baseline; Kubernetes là tùy chọn khi quy mô yêu cầu, không phải bắt buộc cho MVP.

# 13. Post-deploy Validation

| **Check**       | **Nội dung**                                               |
|-----------------|------------------------------------------------------------|
| Technical smoke | Health, auth, DB, worker, storage                          |
| Business smoke  | Run 1-3 known costing scenarios; compare expected          |
| Security smoke  | Role matrix, cross-company denied, sensitive fields        |
| Metrics         | Error rate, p95, DB CPU/connections/locks, worker failures |
| Audit           | Release/migration/config changes recorded                  |
| Decision        | Proceed/hold/rollback                                      |

# 14. Exit Gate

- Deployment hoàn tất bằng immutable artifact đúng release.

- Database migration state verified và backup/restore available.

- Post-deploy smoke pass.

- SLO/alerts/dashboard nhận telemetry.

- Runbook/rollback/DR được lưu và owner xác nhận.

- Release notes, change record và RTM cập nhật.

- Business owner được thông báo trạng thái production.
