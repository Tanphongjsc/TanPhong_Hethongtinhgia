# Triển khai Hethongtinhgiathanh trên Render

Ngày chuẩn bị: 08/10/2026. Target: **Render Web Service + Supabase PostgreSQL**.
Chủ dự án xác nhận chưa có service; phiên làm việc không có kết nối tài khoản/API
Render. Tài liệu này hướng dẫn tạo service; không phải bằng chứng deploy thành công.

**DEPLOYMENT STATUS: READY TO DEPLOY ON RENDER** sau các kiểm tra ghi cuối tài liệu.
**ACCESS SECURITY STATUS: REQUIRES ACCESS RESTRICTION**.
Không authentication, login/logout, Basic Auth, user/role, workflow phê duyệt hoặc
organization selector. Giữ lịch sử, snapshot, trace và technical logging hiện có.

## 1. Cấu hình copy vào Dashboard

| Mục | Giá trị |
|---|---|
| Service Type | Web Service |
| Tên đề xuất | `hethongtinhgiathanh` (chưa tạo; Render cấp hostname thực tế) |
| Repository | `ThanhTrung2308/Hethongtinhgiathanh` |
| Branch | `main` |
| Region | Singapore; Supabase hiện tại là `ap-southeast-1`, không đổi database region |
| Language / Runtime | Python 3 |
| Root Directory | Để trống: `manage.py`, `build.sh`, `package.json` nằm tại repository root |
| Build Command | `bash build.sh` |
| Start Command | `gunicorn -c config/gunicorn.py config.wsgi:application` |
| Health Check Path | `/health/` |
| Auto Deploy | Ban đầu tắt, dùng Manual Deploy |
| Python | `.python-version`: **3.11.5** |
| Node | `.node-version`: **24.11.0**, npm **11.6.1** |
| Database / Disk / Docker | Không tạo Render PostgreSQL, persistent disk hoặc Docker |

Pin runtime khớp môi trường đã kiểm thử; không mặc định nâng major. Nếu Dashboard
có `PYTHON_VERSION`/`NODE_VERSION` cũ, xóa override hoặc đặt đúng các phiên bản trên
vì biến môi trường có ưu tiên cao hơn version files. Node chỉ dùng lúc build.
[Python](https://render.com/docs/python-version), [Node](https://render.com/docs/node-version),
[region](https://render.com/docs/regions).

Ứng dụng dùng WSGI, không cần ASGI/Uvicorn. `requirements-render.txt` bổ sung
Gunicorn 26.2.0 vào dependencies production hiện có. Waitress được giữ để chạy
Windows qua `python -m config.serve`; trên Render chỉ chạy Gunicorn.
Mặc định 1 worker, 4 threads, không preload DB connections trước fork; tăng concurrency
chỉ sau khi đo memory và connection budget. Timeout 30 giây là timeout heartbeat của
Gunicorn gthread, **không phải deadline từng request**. Graceful shutdown 25 giây.
Golden/volume regression phải qua trước khi tăng timeout để xử lý workload mới.
[Gunicorn settings](https://gunicorn.org/reference/settings/).

## 2. Environment variables

Nhập trực tiếp vào **Render → Environment**. Không upload `.env` phát triển và không
copy secret vào Git/chat/log. Production không tự đọc bất kỳ `.env` nào.
[.env.render.example](../.env.render.example) chỉ là tham chiếu, không phải secret file.

| Variable | Required | Example | Purpose | Secret? |
|---|---|---|---|---|
| `APP_ENV` | Có | `production` | Tách runtime production, chặn lệnh nguy hiểm | Không |
| `DJANGO_SETTINGS_MODULE` | Có | `config.production` | Production settings | Không |
| `APP_TRANSPORT` | Có | `render_https` | Chỉ tin managed HTTPS ingress của Render | Không |
| `DJANGO_DEBUG` | Có | `False` | Không traceback/SQL trên UI | Không |
| `DJANGO_SECRET_KEY` | Có | `***` | Khóa production mới, ngẫu nhiên >=50 ký tự; khác dev | Có |
| `DATABASE_URL` | Có trên Render | `postgresql://user:encoded-password@pooler-host:5432/postgres?sslmode=require` | Supabase connection từ Dashboard → Connect | Có |
| `DB_SSLMODE` | Khuyên đặt | `require` | SSL mặc định khi URL không ghi sslmode | Không |
| `DB_CONNECT_TIMEOUT` | Tùy chọn | `10` | Giây, 1–60 | Không |
| `DB_CONN_MAX_AGE` | Tùy chọn | `60` | Giây, 0–3600; bật health checks kết nối | Không |
| `APP_MODE` | Khuyên đặt | `single_company` | Chế độ nội bộ hiện có | Không |
| `LOG_LEVEL` | Tùy chọn | `INFO` | JSON technical logging; không DEBUG | Không |
| `WEB_CONCURRENCY` | Tùy chọn | `1` | Worker, 1–8 | Không |
| `GUNICORN_THREADS` | Tùy chọn | `4` | Threads/worker, 1–16 | Không |
| `GUNICORN_TIMEOUT` | Tùy chọn | `30` | Heartbeat timeout, 10–120 giây | Không |
| `DJANGO_ALLOWED_HOSTS` | Tự động cho Render | Không cần nhập | Thêm exact hostname từ `RENDER_EXTERNAL_HOSTNAME`; custom hosts sau này phân cách dấu phẩy, không `*` | Không |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Tự động cho Render | Không cần nhập | Thêm `https://` + exact Render hostname; không wildcard/`${VAR}` | Không |
| `DJANGO_SECURE_HSTS_SECONDS` | Tùy chọn | `0` | Chỉ bật sau khi xác minh HTTPS thật | Không |
| `APP_HTTPS_VERIFIED` | Tùy chọn | `False` | Phải True nếu bật HSTS | Không |
| `DJANGO_STATIC_ROOT` | Tùy chọn | Không cần nhập | Mặc định `<release>/staticfiles`, absolute, khác source `static/` | Không |
| `DEFAULT_ORGANIZATION_ID` | Chỉ khi dữ liệu cũ cần | ID đang tồn tại | Helper nội bộ cũ cho FK compatibility, không tạo company/user flow | Không |
| `RENDER` | Render tự cấp | `true` | Guard platform transport; không tự nhập | Không |
| `RENDER_EXTERNAL_HOSTNAME` | Render tự cấp | Hostname service thực tế | Exact host/CSRF, không tự nhập hoặc đoán | Không |
| `PORT` | Render tự cấp | Do platform cấp | Gunicorn bind `0.0.0.0:$PORT` | Không |

Không nhập `APP_TRUSTED_PROXY`, `APP_BIND/PORT/THREADS` của Waitress,
`GUNICORN_CMD_ARGS`, Supabase API/Auth keys hoặc `service_role` cho service này.
Generate `DJANGO_SECRET_KEY` mới bằng password/secret generator tin cậy rồi nhập
trực tiếp vào Dashboard; không reuse khóa development.

## 3. Supabase và DATABASE_URL

Giữ **Session pooler port 5432** đang hoạt động. Lấy connection string từ
**Supabase Dashboard → Connect → Session pooler**; không suy ra hostname/username
từ region. Direct connection có thể cần IPv6; session pooler hỗ trợ IPv4 cho backend
chạy lâu dài. Không tự chuyển transaction pooler 6543, tạo database trên Render,
migrate dữ liệu hoặc dùng Supabase Auth/API.
[Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres).

`DATABASE_URL` nếu có sẽ thay thế **toàn bộ** `DB_NAME/USER/PASSWORD/HOST/PORT`.
Không merge từng field. Nếu URL vắng, bộ `DB_*` cũ tiếp tục hoạt động ở development/
deployment Waitress. URL hỏng thì fail rõ ràng, không fallback sang DB khác.
Mật khẩu có `@ # ? & / : % +` hoặc khoảng trắng phải percent-encode; dùng
`urllib.parse.quote(password, safe="")` trong công cụ cục bộ an toàn, không dán secret
vào shell history/website encode công cộng. Không encode toàn connection URL;
không encode password hai lần. Không in URL ra log.

Parser hỗ trợ `postgres://`/`postgresql://`, query `sslmode` và `sslrootcert`.
Production chỉ chấp nhận `require`, `verify-ca`, `verify-full`; CA file cần có thật
nếu dùng verification. Không cho URL override host/options/search_path qua query.
Mọi kết nối giữ `options=-c search_path=costing,public`; connect timeout và tuổi
kết nối dùng các biến tuning nêu trên. Parser không sửa precision/model/schema.

`/ready/` và startup preflight kiểm tra đúng schema, search_path và bảng costing,
chỉ trả `{status:ok}` hoặc unavailable ra public; không expose host/schema/credentials.
Nếu có Render Shell, xác minh trực tiếp bằng SELECT sau (chỉ đọc):

```bash
python manage.py shell -c "from django.db import connection; c=connection.cursor(); c.execute(\"SELECT current_schema(), current_setting('search_path')\"); print(c.fetchone()); c.close()"
```

Expected: `('costing', 'costing,public')`. Không có Shell không chặn deployment:
startup preflight và GET `/ready/` xác minh contract này mà không cần viết dữ liệu.
Nếu nhiều công ty active tồn tại trong dữ liệu cũ, cấu hình helper compatibility
đã có bằng ID hợp lệ; không thêm organization selector/membership.

## 4. Build, static, HTTPS và probes

`build.sh` dùng Bash errexit/nounset/pipefail, lần lượt:

1. Cài `requirements-render.txt` bằng Python của runtime đã pin.
2. `npm ci` từ package-lock hiện có.
3. `npm run build` = copy HTMX/Alpine/focus local + `npm run build:css` minified.
4. `python manage.py collectstatic --noinput`.
5. `python manage.py check --deploy --fail-level=ERROR`.

Không migration, makemigrations, seed, reset, flush hoặc test suite trong build/start.
Chỉ migration package rỗng hiện có; không có Django auth/session tables cần tạo.
Start Command chỉ khởi động Gunicorn. Worker preflight đọc static manifest và DB
trước khi nhận request; lỗi cấu hình/DB/schema sẽ fail startup thay vì LIVE giả.

WhiteNoise sau SecurityMiddleware, CompressedManifestStaticFilesStorage; collectstatic
loại raw Tailwind source, giữ 7 CSS/JS chính và license assets. Hashed assets có cache
immutable/compression. Runtime không chạy Node, watcher hoặc `runserver`.

Kiểm tra dependency 08/10/2026: `npm audit` báo 4 mục High trong cùng chuỗi
`@tailwindcss/cli → @parcel/watcher → micromatch → braces` (công cụ build/dev).
`npm audit --omit=dev` báo 0. Advisory
[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
nêu lỗi cạn stack khi xử lý mẫu brace lồng sâu, chưa có bản braces được vá tại lúc
kiểm tra. Không chạy `audit fix --force` hoặc downgrade CLI theo gợi ý tự động.
Build chỉ dùng source/pattern đã review trong Git; không nhận pattern/upload từ user
và không chạy watcher ở runtime. Đây vẫn là dependency risk của build tools cần
theo dõi/cập nhật riêng, không phải kết luận toàn bộ dependencies đã sạch lỗ hổng.

Render cấp HTTPS ở managed ingress rồi chuyển HTTP vào service; public HTTP được
platform redirect sang HTTPS. `render_https` chỉ được bật với `RENDER=true` và exact
hostname `.onrender.com` hợp lệ; Django dùng `SECURE_PROXY_SSL_HEADER` cho
`X-Forwarded-Proto: https`. Không bật trust này cho deployment thông thường.
Gunicorn tắt tự suy luận các scheme/forwarder headers khác; không dùng wildcard
`forwarded_allow_ips`. Waitress private_http/https_proxy cũ giữ nguyên.
[Render web services](https://render.com/docs/web-services),
[Render xác nhận scheme header](https://community.render.com/t/setting-network-port-forward-reverse-proxy-manually-fusionauth/8419),
[Django proxy settings](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header).

`SECURE_SSL_REDIRECT=True`, CSRF/toast cookies Secure trong Render mode. Không tắt
CSRF. Cần kiểm tra trên URL thật không redirect loop và POST cùng origin có token
hợp lệ. Unit/HTTP Linux mô phỏng managed ingress không thay thế HTTPS test thực tế.
HSTS=0 ở deployment đầu; warning W004 được review: chưa xác minh HTTPS thật,
không preload/includeSubDomains. Sau xác minh có thể đặt HSTS theo policy riêng.

`/health/` nhẹ, GET 200 không query DB/company/engine, dùng làm Health Check Path.
`/ready/` GET có một query read-only, dùng kiểm tra thủ công, 503 nếu DB/schema sai.
Không dùng homepage có business DB query làm health path.
[Render health checks](https://render.com/docs/health-checks).

## 5. Git và các bước Dashboard

Mọi file triển khai phải nằm trong commit trên `main` trước khi Render build.
Review `git diff`/`git status`, commit và push các thay đổi của task này lên origin;
không commit `.env`, venv, artifacts, node_modules hoặc database credentials.
Không cần thay đổi branching strategy. `.gitattributes` giữ LF cho `build.sh`;
Build Command `bash build.sh` không phụ thuộc executable bit của Windows checkout.

1. Đăng nhập Render Dashboard bằng tài khoản của chủ dự án.
2. **New → Web Service → Connect Git repository**; cấp Render quyền đọc repo
   `ThanhTrung2308/Hethongtinhgiathanh` nếu là private.
3. Chọn branch `main`, Runtime Python 3, region **Singapore**, Root Directory trống.
4. Chọn instance/workspace plan phù hợp tài khoản; không giả định đã có plan trả phí.
5. Nhập Build Command `bash build.sh` và Start Command ở bảng mục 1.
6. **Environment**: nhập các biến bắt buộc/khuyên đặt ở mục 2, secret mới và
   Supabase session URL hiện có. Không tạo Render database.
7. Advanced/Settings: Health Check Path `/health/`, ban đầu Auto Deploy tắt.
8. **Create Web Service**. Theo dõi pip → npm ci → vendor/Tailwind → collectstatic
   → deploy check trong build logs, rồi Gunicorn bind/preflight/worker startup.
9. Mở hostname HTTPS thực tế Render cấp. Tự động host/CSRF không cần sửa code
   khi Render bổ sung hậu tố vào tên service. Ghi lại service URL và commit đã deploy.
10. Thực hiện checklist chỉ đọc bên dưới; không coi LIVE là đã an toàn với dữ liệu thật.

## 6. Kiểm tra sau deploy — chỉ đọc

Chạy từ máy có quyền mạng tới service, thay URL bằng hostname thực tế:

```text
python scripts/smoke_production.py --base-url https://<hostname-thuc-te>.onrender.com --report artifacts/render-smoke.json
```

Tool chỉ GET, xác minh health/readiness, root redirect và các main lists: phần tử
chi phí, vật tư, sản phẩm, SKU, BOM, bao bì, công thức, Run, kịch bản và so sánh.
Kiểm tra HTMX partial và 7 hashed CSS/JS. Không gửi forms, seed hoặc engine commands.
Khi có Run/kịch bản đã lưu, bổ sung `--costing-run <public-UUID>`
`--costing-line <line-ID-thuoc-run>` `--pricing-scenario <ID>` để đọc detail,
snapshot/trace Costing và Pricing detail có waterfall/nguồn/trace. Không tạo record
mới để làm smoke. Nếu database không có lịch sử, ghi rõ chưa kiểm chứng phần đó.

Trong browser: CSS có style, sidebar collapse/mobile overlay, Alpine dropdown,
HTMX tìm kiếm/phân trang giữ URL, modal/drawer nếu màn hình dùng. DevTools không
404 assets/console error. GET record không tồn tại trả trang 404 tiếng Việt, không
traceback. Mở lịch sử Run → breakdown/snapshot/trace và Pricing → kết quả/nguồn/
trace; đối chiếu các giá trị đã lưu. Không chạy lại Golden/seed trên production:
Golden được thực thi trên PostgreSQL test riêng trước release.

Review Render Logs: không startup worker failure, 500 ngoài dự kiến, connection/
manifest/CSRF/DisallowedHost errors; không password/SECRET_KEY/URL nguyên vẹn.
Request log có path/status/duration/trace_id, không query/body. Gunicorn accesslog
tắt để tránh log trùng hoặc query string; error/startup dùng JSON redaction.

## 7. Quyền truy cập — cần xử lý riêng

**SECURITY WARNING: Application có thể truy cập công khai nếu biết URL.**
Web Service có public onrender.com URL; HTTPS và URL khó đoán không hạn chế người
truy cập. Ứng dụng không login nên người truy cập được có thể đọc/ghi theo chức
năng nội bộ. **NOT SAFE FOR SENSITIVE PRODUCTION DATA** khi vẫn mở Internet.

Theo [Render Inbound IP Rules](https://render.com/docs/inbound-ip-rules), hạn chế
IP cho **Web Service** cần workspace **Scale hoặc Enterprise**; mua instance trả
phí đơn lẻ không đồng nghĩa có tính năng này. Tài khoản/plan chưa được kiểm chứng.
Nếu hỗ trợ: Settings → Networking → Inbound IP Restrictions, dùng IP ra Internet
của công ty/VPN, bỏ allow-all; test từ cả mạng được phép và không được phép.
Nếu không hỗ trợ: ghi trạng thái public, cần giải pháp hạn chế ở infrastructure
được quyết định riêng trước khi đưa dữ liệu nhạy cảm vào. Không tự thêm login/
Basic Auth/roles và không tự chuyển Private Service thiếu gateway browser.

## 8. Troubleshooting và rollback

| Lỗi | Kiểm tra / cách xử lý |
|---|---|
| Build failed | Xem bước đầu tiên fail; đúng root, Python/Node pins, requirements-render có trong commit |
| `npm ci` failed | Node 24.11.0, npm 11.6.1, lock đồng bộ; không bỏ lock hoặc tự upgrade major |
| Tailwind failed | Build local trước; kiểm source `static/src/tailwind.css` và package scripts |
| collectstatic/manifest failed | Vendor/CSS build trước collect, STATIC_ROOT khác source, quyền ghi build; không DEBUG=True |
| Gunicorn module not found | pip requirements-render hoàn tất; cwd root; đúng `config.wsgi:application` |
| No open ports | Start command đúng config/gunicorn.py, bind 0.0.0.0 theo PORT, preflight có fail không |
| Supabase connect failed | URL có/encoded đúng → host/user đúng Connect mode → port → SSL → session/direct → IPv4/IPv6 → search_path; không in URI |
| Direct/IPv6 lỗi | Kiểm networking, thử Session pooler lấy từ Dashboard; không đổi schema/tắt SSL |
| CSRF 403 | Exact HTTPS origin, Render scheme header, cookie/token; không csrf_exempt |
| DisallowedHost | Actual Render hostname/env, custom exact host nếu có; không `*` |
| CSS missing | npm build → output → collectstatic → manifest → WhiteNoise → hashed asset URL |
| Redirect loop | APP_TRANSPORT=render_https, platform env/hostname, forwarded proto thật; không tắt SSL redirect vĩnh viễn |
| 500 DEBUG=False | Tìm X-Trace-ID trong technical logs, che secrets trước khi chia sẻ; không bật DEBUG production |
| /health 200, /ready 503 | Process sống nhưng DB/schema chưa sẵn sàng; kiểm connectivity/search_path, không seed/migrate |

Rollback: Render → service → **Deploys → bản successful trước → Rollback** khi
artifact còn được plan giữ. Lần đầu chưa có bản successful thì sửa cấu hình/code
và Manual Deploy lại. Dashboard rollback tắt auto-deploy; review env/settings của
release quay lại. **Manual Deploy → Restart service** khởi động lại bản đang chạy;
env thay đổi cần deploy theo Dashboard. Không rollback bằng reset database.
[Render rollbacks](https://render.com/docs/rollbacks), [deploy/restart](https://render.com/docs/deploys).

Supabase bên ngoài không rollback cùng artifact. Không restore/truncate/drop hoặc
xóa DEMO. Backup/restore drill, giám sát dài hạn và giới hạn truy cập thật chưa
được task này kiểm chứng. Không chỉnh DNS/custom domain.

## 9. Manifest của iteration

Tạo mới:

- `.python-version`, `.node-version`, `.gitattributes`, `.env.render.example`.
- `requirements-render.txt`, `build.sh`.
- `config/database.py`, `config/gunicorn.py`.
- `apps/master_data/test_render.py`, `docs/DEPLOYMENT_RENDER.md`.

Sửa:

- `.env.example`, `.env.production.example`, `.gitignore`, `README.md`.
- `config/settings.py`, `config/production.py`, `config/logging.py`, `config/test_settings.py`.
- `apps/master_data/test_deployment.py`, `scripts/smoke_production.py`.
- `docs/00_AI_CONTEXT.md`, `docs/06_DEPLOYMENT_DEVOPS.md`.
- `static/css/app.css` được tạo lại bằng build, không chỉnh tay.

Không sửa `apps/core/models.py`, business calculations, package versions/lock,
database schema hoặc DEMO. Không thêm workflow/Auth/organization UI. Không xóa file.
Các harness/runtime Linux và evidence chỉ nằm trong `artifacts/` bị Git ignore.

## 10. Báo cáo A–I

Các kiểm tra local/Linux dưới đây không được gọi là Render build/LIVE/HTTPS PASS.

| Mục | Kết quả |
|---|---|
| A1 Service | Web Service, chưa tạo trên tài khoản Render |
| A2 Region | Singapore được đề xuất, phù hợp Supabase ap-southeast-1; chưa đo latency từ Render |
| A3 Branch | main |
| A4 Root | Repository root, Dashboard để trống |
| A5 Build | bash build.sh |
| A6 Start | gunicorn -c config/gunicorn.py config.wsgi:application |
| A7 Health path | /health/ |
| A8 Python | 3.11.5; Node build 24.11.0/npm 11.6.1 |
| B9 Connection | Giữ Supabase Session pooler |
| B10 Host/port | Shared Supabase pooler, 5432; không ghi credential thật vào báo cáo |
| B11 SSL | require; URL không được disable SSL ở production |
| B12 search_path | SELECT thật từ Linux: current_schema=costing, search_path=costing,public |
| B13 DB connectivity | Linux đọc Supabase PASS, ssl_in_use=True; chưa kiểm từ service Render thật |
| C14 Env names | Bảng đầy đủ ở mục 2, giữ naming DJANGO_*/DB_* đang có |
| C15 Missing | Render chưa có service, chưa nhập secret production/DATABASE_URL và runtime env trên Dashboard |
| C16 DEBUG | False, True bị từ chối |
| C17 Hosts | Exact RENDER_EXTERNAL_HOSTNAME tự cấp; không wildcard |
| C18 CSRF | Exact HTTPS origin tự thêm, Secure cookie và token bắt buộc; tests hợp lệ/bad-origin qua |
| D19 Tailwind | npm run build:css và clean npm ci/build trên Linux đã qua |
| D20 collectstatic | 10 files, 30 post-processed; manifest đủ assets |
| D21 Static strategy | WhiteNoise CompressedManifest, runtime không dùng Node/CDN |
| D22 CSS/JS smoke | 7 assets PASS cả test fixtures và Gunicorn Linux/Supabase; browser/HTMX trên test DB qua |
| E23 Startup | Gunicorn Linux 26.2.0/Python 3.11.5 PASS, SIGTERM dừng sạch; Render chưa start thật |
| E24 Health | Linux health/ready 200, không redirect loop với managed-ingress header mô phỏng; Render chưa kiểm chứng |
| E25 Main pages | 26 smoke checks GET/HTMX/assets/history trên Supabase thật qua, không login redirect |
| E26 Costing history | GET detail/snapshot/trace dữ liệu đã lưu qua; fingerprints cả 3 Run không đổi |
| E27 Pricing history | GET detail kết quả/nguồn/trace qua; snapshot hashes cả 2 kịch bản không đổi |
| F28 Django check | PASS, 0 issues |
| F29 check --deploy | 0 errors; security.W004 do HSTS=0, đã review ở mục 4 |
| F30 Tests | Full 747/747 PASS, 357.050 giây; sau fixes config cuối targeted deployment 29/29 PASS, 27.497 giây |
| F31 Golden Costing | Tổng 583000 / 10 đơn vị; đơn giá 58300, delta 0 |
| F32 Golden Pricing | Giá khách trả 89972.41379310; phí 5498.62068966; thuế 8179.31034483; lợi nhuận 17994.48275861; margin 20%, delta 0 |
| F33 Comparison | Regression so sánh snapshot/delta/baseline/HTMX qua, không gọi lại engine |
| G34 Authentication | Không Auth/login/logout, giữ kiến trúc hiện tại |
| G35 Exposure | Web Service có public URL; chưa tạo service, chưa hạn chế truy cập |
| G36 Inbound restrictions | Web Service cần Scale/Enterprise workspace; tài khoản/plan/cấu hình chưa kiểm chứng |
| G37 Real data | REQUIRES ACCESS RESTRICTION; NOT SAFE FOR SENSITIVE PRODUCTION DATA nếu vẫn public |
| H38 Created | 10 files ở mục 9 |
| H39 Modified | 13 files ở mục 9, không business/schema changes |
| H40 Docs | Runbook này, README, AI_CONTEXT và deployment runbook cũ được cập nhật |
| I41 Errors | Test runner cần script PG cô lập; tests CSRF ban đầu gọi DB giả; harness dùng sai status/run_status; Gunicorn validator từ chối forwarder_headers dạng list; logconfig_dict bật access log dù accesslog=None; npm build-tools audit warning |
| I42 Fixes | Chạy test.ps1; cô lập render lỗi trong unit test; dùng run_status thực tế trong harness; forwarder_headers=""; NullHandler chặn access log trùng/query strings; phân loại npm dev-chain risk, không force upgrade |
| I43 Blockers | Chưa có Render service/quyền tài khoản trong phiên; cần commit/push thay đổi, cấp env/secret Dashboard rồi deploy và kiểm HTTPS/logs/restart/rollback thật; access restriction và dependency risk build còn cần theo dõi |

Golden/Comparison chỉ chạy trên PostgreSQL test cô lập, không seed/recalculate
production. Full suite bật cả browser và volume checks. Evidence local bị Git ignore:
`artifacts/render-full-regression.log`, `artifacts/render-targeted-tests.log`,
`artifacts/production-http-smoke.json`, `artifacts/render-linux-build.log`,
`artifacts/render-linux-gunicorn.log`, `artifacts/render-linux-verification.json`,
`artifacts/render-source-review.json`.

### Xác minh Linux cuối

Clean build từ source copy không `.env`/node_modules: **PASS** với Python 3.11.5,
Node 24.11.0/npm 11.6.1 trên Ubuntu WSL. Gunicorn 26.2.0 khởi động production
settings, worker preflight qua và dừng SIGTERM sạch. Chỉ bind loopback trong bài
kiểm chứng; production config `0.0.0.0:$PORT` được kiểm riêng. HTTPS ingress được
mô phỏng bằng exact Host và scheme header; **chưa kiểm chứng TLS thật trên Render**.

26 HTTP checks gồm health/readiness, main pages, HTMX partial, 7 hashed assets và
lịch sử Costing/Pricing **PASS**. SELECT read-only xác nhận `costing`, `costing,public`,
SSL sử dụng thật. Fingerprint/hash trước/sau cả **3 Runs và 2 Pricing Scenarios**
không đổi; không seed/reset/recalculate. Chỉ còn HSTS W004 được phân loại ở mục 4
và npm dev-chain warning nêu rõ. Test token trong query không xuất hiện trong
Gunicorn/application log; không còn logger gunicorn.access trùng. Log startup/
request JSON không có ERROR/CRITICAL ở lần xác minh cuối.

Rà soát 463 source files: không thấy các secret hiện có, `.env` thật không track,
51 unmanaged business mappings và migrations giữ nguyên. 23 file của task được
stage; **chưa commit/push hoặc deploy**. Sau review, đưa chính các thay đổi đã stage
lên `main` trước khi tạo service:

```text
git diff --cached
git commit -m "Prepare Render WSGI deployment"
git push origin main
```

**DEPLOYMENT STATUS: READY TO DEPLOY ON RENDER**.
**ACCESS SECURITY STATUS: REQUIRES ACCESS RESTRICTION**.
