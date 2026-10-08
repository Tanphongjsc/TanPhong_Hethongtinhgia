# Frontend Foundation + Cost Element

> **Architecture update 07/10/2026:** phần authentication, membership, user roles,
> organization selection và signed-cookie session của báo cáo lịch sử này đã
> superseded bởi [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).

Đây là báo cáo task, không thay thế canonical implementation spec.
Canonical docs trong repository hiện nằm trực tiếp dưới `docs/`.

## Phạm vi và hành vi

- Django Templates + HTMX + Alpine.js + Tailwind CSS local.
- Foundation: shell, sidebar collapse/mobile overlay, topbar chọn organization,
  breadcrumb/header, buttons, badges, toast, search/filter/pagination,
  modal/confirm, drawer và errors.
- Cost Element: list/search/filter/sort/pagination/detail/create/edit.
- Không có delete; có thể đổi `is_active` qua edit. UI xác nhận khi ngừng hoạt động.
- Các sidebar destination khác chưa có route và hiển thị disabled.
- Không triển khai module tiếp theo; không đổi schema/migrations business.

## Files tạo

```text
.env.example
requirements.txt
requirements-dev.txt
apps/__init__.py
apps/master_data/access.py
apps/master_data/constants.py
apps/master_data/context_processors.py
apps/master_data/errors.py
apps/master_data/forms.py
apps/master_data/middleware.py
apps/master_data/navigation.py
apps/master_data/selectors.py
apps/master_data/services.py
apps/master_data/urls.py
apps/master_data/validators.py
apps/master_data/testing.py
apps/master_data/test_browser.py
apps/master_data/templatetags/__init__.py
apps/master_data/templatetags/workspace_tags.py
config/test_settings.py
scripts/build-vendor.cjs
scripts/test.ps1
static/src/tailwind.css
static/css/app.css (generated)
static/js/app.js
static/js/htmx-config.js
static/js/alpine-components.js
static/vendor/htmx/htmx.min.js (copied)
static/vendor/htmx/LICENSE
static/vendor/alpine/alpine.min.js (copied)
static/vendor/alpine/focus.min.js (copied)
static/vendor/alpine/LICENSE.md
static/vendor/README.md
templates/base/base.html
templates/base/error.html
templates/layouts/app_shell.html
templates/layouts/sidebar.html
templates/layouts/topbar.html
templates/layouts/breadcrumbs.html
templates/layouts/page_header.html
templates/components/button.html
templates/components/status_badge.html
templates/components/version_badge.html
templates/components/modal.html
templates/components/drawer.html
templates/components/toast.html
templates/components/empty_state.html
templates/components/pagination.html
templates/components/search_box.html
templates/components/filter_bar.html
templates/components/filter_select.html
templates/components/sort_header.html
templates/components/form_field.html
templates/components/detail_field.html
templates/components/confirm_dialog.html
templates/partials/error.html
templates/partials/form_errors.html
templates/partials/loading.html
templates/master_data/cost_element_list.html
templates/master_data/cost_element_form.html
templates/master_data/cost_element_detail.html
templates/master_data/partials/cost_element_table.html
templates/master_data/partials/cost_element_rows.html
templates/master_data/partials/cost_element_form_content.html
templates/master_data/partials/cost_element_detail_content.html
templates/master_data/partials/cost_element_metadata.html
docs/FRONTEND_FOUNDATION_COST_ELEMENT.md
```

## Files sửa

- `apps/core/models.py`: alias `django_timezone` để field `Organization.timezone`
  không che khuất module; toàn bộ mapping và `managed=False` giữ nguyên.
- `apps/master_data/views.py`: request/form/service/selector orchestration.
- `apps/master_data/tests.py`: regression, authorization và PostgreSQL tests.
- `config/settings.py`: templates/static, locale, trusted actor resolver, signed
  cookie sessions, error middleware và environment settings.
- `config/urls.py`: namespace/routes, root redirect và error handlers.
- `manage.py`: mặc định dùng local test settings khi chạy `test`.
- `package.json`, `package-lock.json`: scripts/vendor dependencies, pin Tailwind.
- `.gitignore`: node modules, caches, test cluster, collected static và artifacts.
- `README.md`: cách chạy và giới hạn authentication.
- `.env` local (gitignored): thêm secret Django ngẫu nhiên và `DJANGO_DEBUG=True`
  khi các key chưa tồn tại; không đổi các DB credentials và không in secret.

## Dependencies

Đã có: Node 24.11.0, npm 11.6.1, Django 5.2.17, django-environ 0.14.0,
psycopg 3.3.6 và Tailwind 4.3.3. Giữ nguyên major Tailwind.

Đã cài:

- HTMX (`htmx.org`) 2.0.11.
- Alpine.js 3.17.4.
- Alpine Focus 3.17.4.
- Playwright 1.58.0 và Chromium phục vụ kiểm tra, chỉ trong dev environment.

## Kiến trúc và validation

View nhận request, kiểm tra permission và chọn full/partial; form kiểm tra input;
selector đọc bằng ORM; service normalize, validate, transaction/row lock và save.
JS chỉ xử lý interaction. `apps/core` không import service.

Schema được kiểm tra bằng SELECT chỉ đọc. Vocabulary các CHECK constraint hiện
có được khai báo trong `constants.py`; rounding scale từ 0 đến 12. Code trim/uppercase,
name trim; unique theo organization, nhận biết cả mã cũ khác chữ hoa/thường.

Theo business domain, MONEY cần currency, QUANTITY cần UoM. Khi khai báo cả
dimension và UoM, dimension phải khớp category của UoM. Không tự loại bỏ currency
hoặc UoM ở các type khác vì schema không cấm. Danh mục inactive hiện gắn với bản
ghi có thể được giữ khi edit; không cho chọn mới. Group luôn scoped theo organization.

Service allow-list các field có thể sửa, tự gán organization/audit UUID/timestamp,
giữ created fields khi edit. `IntegrityError` được chuyển sang ValidationError
tiếng Việt, gồm duplicate race; không trả raw database error.

List dùng select_related organization/group/currency/UoM; query test xác nhận
đọc relations trên nhiều rows chỉ cần một SELECT. Search, filter, sort và pagination
đều ở database. Sort được allow-list; pagination 25/50/100.

HTMX update table, debounce 400ms, push query URL, loading state và request sync
để tránh response cũ ghi đè. Form create/edit dùng POST Django. HTMX callers vẫn
nhận form/detail partial và HX-Redirect khi lưu thành công. History restore trả
full page; tắt history DOM cache để không giữ sensitive data hoặc stale filters.

CSRF được giữ ở middleware/form và header HTMX. Validation summary/field errors
giữ input và liên kết aria-describedby/aria-invalid. Modal/drawer/mobile overlay
dùng Alpine Focus để trap/return focus, Escape, inert background và scroll lock.
Table trên màn hình hẹp scroll ngang; document không overflow.

Production unexpected errors trả trace UUID; logger ghi exception ở server;
UI không trả traceback. Response có X-Trace-ID và private/no-store.

## Authentication và permission hook

Repository chưa có Supabase authentication. Task chỉ cung cấp abstraction theo
spec. Không có identity giả hay đường truy cập anonymous vào dữ liệu.

`COSTING_ACTOR_RESOLVER` là dotted Python callable `(request) -> UUID | None`.
Default resolver yêu cầu `request.user.is_authenticated` và active, lấy UUID
từ `request.user.supabase_user_id` hoặc UUID primary key. ID số Django bị từ chối.
Upstream authentication backend phải xác thực token/session trước khi tạo
principal hoặc thuộc tính server-side này. Không lấy identity từ form, query,
client header hoặc UUID tự khai báo.

Hook khác có thể cấu hình qua `.env`, ví dụ dotted path tới callable của
authentication backend đã được dự án xác nhận. Không cần đổi model/schema.

Workspace query active memberships và organization active mỗi request. Một
membership được chọn tự động; nhiều membership yêu cầu chọn tổ chức ở topbar.
Selected organization trong signed session được kiểm tra lại membership.
Các query detail/list/edit và group choices chỉ truy cập organization hiện tại.

Policy tập trung trong `permissions_for`:

- Các role hợp lệ hiện có được xem Cost Element không nhạy cảm.
- ADMIN được create/edit; không tự được xem/manage sensitive.
- Permission array có thể cấp rõ `cost_element.view`, `cost_element.create`,
  `cost_element.edit`, `cost_element.view_sensitive`, `cost_element.manage_sensitive`.
- Manage sensitive bao gồm view sensitive, nhưng vẫn cần create/edit tương ứng.
- Không có active membership/context/grant thì từ chối ở backend.

UI hooks: can_view_cost_element, can_create_cost_element, can_edit_cost_element,
can_view_sensitive_cost_element và can_manage_sensitive_cost_element.
Các permission string trên là contract của slice, cần alignment với nơi provision
membership khi nối authentication. Không có thay đổi membership ở live database.

## Kiểm chứng

Commands chạy được:

```powershell
python manage.py check
npm run build:vendor
npm run build:css
npm run dev:css
node --check static/js/app.js
node --check static/js/htmx-config.js
node --check static/js/alpine-components.js
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.master_data.tests --verbosity=2
```

38 backend tests pass: list, search code/name/description, tất cả filters/sorts,
pagination sizes, detail/create/edit, duplicate/invalid forms, reference validation,
full/partial/history responses, empty state, permissions, tenant/sensitive isolation,
CSRF, N+1, real PostgreSQL check/unique, rollback và sanitized errors.

Browser check opt-in pass trên Chromium: list pagination, back/refresh, query
preservation, sort/filter/search, form errors, create/edit/toast, drawer/modal focus,
confirm cancel/save, sidebar collapse/mobile. Viewports 1440, 1100, 800 và 390px;
không document overflow hoặc JavaScript exception. Screenshots trong
`artifacts/screenshots/` chỉ chứa test fixtures.

Test runner chỉ tạo unmanaged fixtures trong `test_costing_slice` trên localhost,
không dùng production database và không thêm business migration. Script test
start/stop riêng instance tại .test-postgres; không dừng service PostgreSQL khác.

Full test suite với `COSTING_BROWSER_TESTS=1` đã pass **39/39 tests**. Tailwind
production minified build và Django system check pass; watcher được khởi động
trong terminal và dừng sau khi xác nhận hoạt động.

## Giới hạn và bước tiếp

- Cần nối authentication Supabase đã xác thực để dùng UI với user thực. Anonymous
  và Django user ID số nhận 403. Audit fields chỉ lưu UUID đã được resolver/membership
  xác nhận. Không implement login hoặc quản trị users trong slice này.
- Không thực hiện create/update lên live Supabase để kiểm chứng; CRUD/constraints
  được kiểm tra trên PostgreSQL riêng. Test fixtures không tái tạo RLS, triggers
  hoặc auth.users FK của Supabase; cần kiểm thử staging khi đã nối authentication.
- npm audit báo 4 high trong dev dependency chain Tailwind CLI → Parcel watcher →
  micromatch → braces. Không có high trong JS runtime dependencies mới. Giữ Tailwind
  4.3.3; không chạy audit fix --force hoặc đổi major để tự xử lý dependency ngoài scope.
- Signed cookies chỉ lưu organization context, không lưu access token hoặc credential.
- Roadmap khuyến nghị: nối authentication/context thực tế, sau đó Currency + UoM.
  Các bước này chưa được triển khai ở iteration hiện tại.
