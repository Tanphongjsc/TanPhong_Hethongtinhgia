# Single company + no authentication

Quyết định kiến trúc ngày **07/10/2026** thay thế iteration Supabase Auth trước đó.
Phần mềm nội bộ cho một công ty, truy cập trực tiếp vào workspace.
Database-first trên Supabase PostgreSQL, schema `costing`, được giữ nguyên.

## Runtime

```text
Request (không user/session)
  → require_access / get_workspace
  → get_default_organization
  → Workspace(organization, INTERNAL_ACCESS)
  → Form / Service / Selector
  → apps.core.models (managed=False)
  → Supabase PostgreSQL
```

Helper duy nhất resolve công ty là
`apps/master_data/company_context.py:get_default_organization()`.
Không resolve bằng user, header, UUID, cookie, membership hoặc query string.
Workspace được cache trên request, không cache toàn cục qua các request.

`InternalAccess` trong `apps/master_data/access.py` có full internal access cho
Cost Element, Currency, UoM Category, UoM và UoM Conversion, gồm dữ liệu sensitive.
Giữ hooks presentation/service, nhưng không có role/user grant. Không thêm
delete/approval feature nếu chưa được triển khai.

| Cấu hình/dữ liệu | Kết quả |
| --- | --- |
| Không DEFAULT_ORGANIZATION_ID, một công ty active | Tự dùng công ty đó |
| Không công ty active | ConfigurationError, trang/HTMX trả 503 rõ ràng |
| Nhiều công ty active, chưa cấu hình ID | ConfigurationError, không chọn ngẫu nhiên |
| DEFAULT_ORGANIZATION_ID hợp lệ và active | Dùng đúng công ty đã cấu hình |
| ID sai/không tồn tại/inactive, APP_MODE khác | ConfigurationError, không fallback |

Cost Element list/detail/edit giới hạn theo công ty mặc định; form không có
organization field. Organization/audit fields gửi thêm trong POST bị bỏ qua.
Service vẫn dùng allow-list và scope khi ghi. Nhóm Cost Element/Item tham chiếu
phải thuộc công ty đó. Currency/UoM Category/UoM giữ phạm vi danh mục dùng chung.
Conversion mới gán công ty mặc định; conversion legacy organization_id=NULL vẫn
chỉ hỗ trợ xem theo policy nghiệp vụ cũ, không tự đổi ownership.

## Auth/session và UI đã loại bỏ

- Xóa toàn bộ `apps/accounts/` (13 files Python) và ba auth templates.
- Xóa login/logout/session/workspace-selection routes và organization-switch route.
- Bỏ /admin/, Django admin/auth/session/contenttypes apps, authentication/session
  middleware và auth context processor; bỏ unused admin imports trong scaffold apps.
- Không import SDK, không gọi Supabase Auth API, không dùng service-role key.
  supabase-auth và portalocker đã được gỡ khỏi requirements và virtualenv.
- Xóa actor resolver, role/grant mapping theo membership, user UUID access checks
  và login redirect; không query OrganizationMember trong runtime.
- Xóa các biến Auth/session-lock khỏi settings, .env.example và .env thực tế.
  Giữ mọi giá trị DB_*; không xóa database credentials.
- Xóa accounts caches và các file session/lock cũ trong workspace. Không user session
  storage. CSRF vẫn enforce trên POST; toast dùng Django CookieStorage cho thông báo.
  Framework SESSION_COOKIE_SECURE/SAMESITE được CookieStorage reuse để đặt cookie,
  không có SessionMiddleware hoặc session backend được sử dụng.
- Topbar chỉ có tên hệ thống và nút sidebar. Không login/logout, menu/email/avatar
  user, organization selector/switcher. Sidebar bỏ Organization và Users & Roles.
  UoM Conversion bỏ Organization Scope ở list/detail. Metadata Cost Element chỉ
  hiển thị timestamps, bỏ actor UUID khỏi UI.

URL cũ /accounts/*, /admin/, /master-data/context/organization/ trả 404.
GET / redirect trực tiếp tới Cost Elements. 403 có thể do CSRF hoặc thao tác ngoài
scope nghiệp vụ; không do thiếu user/login/membership.

## Database và audit

Không sửa apps/core/models.py. Organization, OrganizationMember, organization_id,
FK, constraints và mọi managed=False giữ nguyên. Không business migration,
makemigrations/migrate, DDL hoặc ghi dữ liệu lên Supabase trong task này.

Kiểm tra chỉ đọc ngày 07/10/2026: cả **26 created_by/updated_by/approved_by columns
đều nullable**. Tạo Cost Element: created_by/updated_by=NULL. Edit: updated_by=NULL,
giữ created_by và timestamps lịch sử của bản ghi cũ. Không fake/system UUID.
Các danh mục còn lại không ghi user audit fields; approved_by chưa có flow write
trong các module đã triển khai.

## Cấu hình

```dotenv
APP_MODE=single_company
# Chỉ cần khi có nhiều công ty active:
# DEFAULT_ORGANIZATION_ID=<existing-active-id>
```

Giữ DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_SSLMODE và DJANGO_SECRET_KEY.
Không cần Supabase Auth URL/public/anon key, user hoặc membership.
Khởi động lại Django sau khi đổi .env.

## Dữ liệu công ty ban đầu

Lúc kiểm tra, live database có **0 organization**. Runtime trả 503 vì thiếu dữ liệu
công ty, không phải lỗi authentication/schema. Khi company context hợp lệ, trang
Cost Element hoạt động trực tiếp với HTTP 200.

Người quản trị có thể kiểm tra/tạo company bằng Supabase SQL Editor.
SQL dưới đây là **hướng dẫn, chưa được chạy tự động**:

```sql
SELECT id, code, name, is_active
FROM costing.organization
ORDER BY code;

-- Thay mã/tên bằng dữ liệu công ty thực tế.
INSERT INTO costing.organization
    (public_id, code, name, timezone, is_active, created_by, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'YOUR_COMPANY_CODE', 'Tên công ty của bạn',
     'Asia/Ho_Chi_Minh', true, NULL, now(), now())
ON CONFLICT (code) DO NOTHING
RETURNING id, code, name;
```

Không tạo Auth user hoặc organization_member. Một công ty active không cần cấu
hình ID. Nhiều công ty active thì lấy ID thật từ SELECT để đặt vào .env;
không hard-code ID trong views/services.

## Chạy ứng dụng và Tailwind

```powershell
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
npm run build:css
python manage.py check
python manage.py runserver
```

Mở http://127.0.0.1:8000/ hoặc /master-data/cost-elements/ trực tiếp.
Company context hợp lệ → HTTP 200, create/edit không cần đăng nhập.
Watcher trong terminal riêng: npm run dev:css. Không chỉnh generated app.css.

## Files

Tạo company_context.py, test_company_context.py và báo cáo này.

Sửa:

- config/settings.py, urls.py, test_settings.py.
- apps/master_data/access.py, services.py, views.py, urls.py, middleware.py,
  errors.py, context_processors.py, navigation.py.
- tests.py, test_reference_data.py, test_browser.py, test_reference_browser.py:
  giữ business regressions, thay auth/role cases bằng tests no-auth/context.
- Scaffold admin.py trong audit/bom/core/costing/formula_engine/master_data/
  pricing/product/workflow để bỏ import admin không dùng.
- templates/layouts/topbar.html; master_data/partials/uom_conversion_rows.html,
  cost_element_metadata.html; static/src/tailwind.css và generated css/app.css.
- .env, .env.example, requirements.txt, README; AI context, frontend spec,
  domain/architecture/engineering docs và báo cáo cũ để đánh dấu superseded.

Xóa 13 files apps/accounts: __init__, apps, adapter, authentication, checks,
exceptions, forms, middleware, principals, urls, views, tests, test_browser.
Xóa templates/accounts: login, select_organization, auth_unavailable.

## Kiểm thử và giới hạn

- python manage.py check: pass, không issues.
- python -m pip check: pass.
- npm run build:css: pass, giữ Tailwind 4.3.3.
- 82 backend tests pass, PostgreSQL local riêng, không Supabase DDL/data writes.
- Full suite: **84/84 tests pass**, gồm hai browser tests. Browser vào từ /, không
  sessionid/login/switcher; CRUD, HTMX/search/filter/sort/pagination/history, toast,
  validation, responsive/sidebar và modal/drawer focus vẫn pass.
- Tests mới kiểm tra 0/1/nhiều active company, ID hợp lệ/sai/inactive, lỗi cấu hình
  DEBUG on/off, NULL audit, scope isolation, không query membership, bỏ auth routes,
  bỏ UI organization/user và bỏ qua cookie/header/query cũ.

```powershell
$env:COSTING_BROWSER_TESTS = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
```

Giới hạn thực tế: cần company active trước khi dùng live database; không tự
provision company/membership hoặc sửa schema. Audit lịch sử giữ nguyên, nhưng
no-auth không xác định danh tính người thực hiện các thay đổi mới.
Không triển khai module mới trong task này.
