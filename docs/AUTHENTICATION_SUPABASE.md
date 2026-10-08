# Authentication và workspace Supabase

> **SUPERSEDED — 07/10/2026:** tài liệu lịch sử của iteration Auth. Runtime hiện tại
> đã bỏ toàn bộ adapter/login/logout/session/membership và dùng single-company,
> no-auth. Không áp dụng các bước cấp user/membership hoặc Auth config bên dưới.
> Đọc [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md) cho kiến trúc hiện tại.

Implementation hiện tại dùng Supabase Auth cho tài khoản nghiệp vụ. Không tạo
Django User thay cho `auth.users`, không thay schema hay `managed=False`.

## Nguyên nhân HTTP 403 trước đây

Repository chỉ có Django `AuthenticationMiddleware` và hook
`COSTING_ACTOR_RESOLVER=apps.master_data.access.authenticated_actor_id`; chưa có
login/logout hoặc adapter Supabase. Request chưa đăng nhập có `AnonymousUser`,
resolver trả `None`, workspace không có actor/membership/organization và
`require_access()` trả `PermissionDenied`. Django admin có primary key số nên
không map được với UUID Supabase; quyền superuser Django không phải quyền Costing.

Kiểm tra database chỉ đọc ngày 06/10/2026 cũng thấy **0 organization và 0 active
membership**. Vì vậy, xác thực thành công vẫn chưa đủ để truy cập nghiệp vụ nếu
chưa cấp membership. Model và database khớp ở phần này: FK
`costing.organization_member.user_id → auth.users.id`, FK organization, unique
`(organization_id, user_id)`. `permissions` là PostgreSQL **text[]**, không phải JSON.

Sau khi người dùng bổ sung `.env`, request đọc `GET /auth/v1/settings` trả **200**,
email login được bật. Không dùng mật khẩu người thật và không ghi dữ liệu Supabase
trong quá trình triển khai/kiểm thử.
Đã đối chiếu project reference từ cấu hình database và Auth URL: cùng project.

## Luồng hiện tại

```text
POST /accounts/login/ + CSRF + email/password
  → official supabase-auth SDK: sign_in_with_password
  → Supabase GET /auth/v1/user xác minh access token và UUID
  → session phía server; browser chỉ giữ opaque session ID
  → SupabaseAuthenticationMiddleware xác minh user ở mỗi request
  → authenticated_actor_id lấy verified Supabase UUID
  → get_workspace: active membership + active organization
  → permissions_for: role_code và explicit grants từ database
  → view/service thực thi quyền và selector giới hạn organization
```

Không lấy quyền từ `user_metadata`, header, UUID gửi trong form hay Django
superuser. Một active membership được chọn tự động; nhiều membership hoặc
organization đã chọn không còn hợp lệ sẽ chuyển sang màn hình chọn organization.
POST chọn organization kiểm tra membership lại trước khi lưu ID trong session.

| Tình trạng | Kết quả |
| --- | --- |
| Anonymous hoặc phiên không hợp lệ | 302 tới login, giữ đường dẫn trong `next` |
| HTMX request chưa xác thực | 200 với `HX-Redirect` để điều hướng cả trang |
| Verified user, không có active membership/organization | 403 với thông báo chưa được gán tổ chức |
| Nhiều membership, chưa chọn organization | Chuyển tới `/accounts/organizations/` |
| Có workspace nhưng thiếu quyền thao tác | 403 theo policy hiện có |
| Supabase không thể xác minh phiên | 503; không query dữ liệu nghiệp vụ hoặc dùng identity đã cache |

## Cấu hình và chạy ứng dụng

Giữ `.env` hiện có, thêm cấu hình của **cùng Supabase project với database Costing**:

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_your_public_key
# Nếu project dùng key legacy: SUPABASE_ANON_KEY=your_legacy_anon_key
SUPABASE_AUTH_TIMEOUT=10
SUPABASE_REFRESH_MARGIN=60
SESSION_COOKIE_AGE=86400
```

Lấy URL/key tại Dashboard → Project Settings → API/API Keys. Adapter chỉ chấp nhận
publishable hoặc legacy `anon` key; không chấp nhận secret/service-role key.
[Supabase API keys](https://supabase.com/docs/guides/api/api-keys).

```powershell
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
npm run build:css
python manage.py check
python manage.py runserver
```

Local HTTP dùng `DJANGO_DEBUG=True` và allowed hosts `localhost,127.0.0.1`.
Production dùng `DJANGO_DEBUG=False`, HTTPS; session và CSRF cookie dùng Secure.
Sau khi sửa `.env`, khởi động lại Django để nạp cấu hình.

Tailwind watcher trong terminal riêng: `npm run dev:css`.
Không cần `makemigrations` hoặc `migrate` cho adapter/business tables.

## Tạo tài khoản Supabase

1. Mở Dashboard của đúng project → **Authentication → Users → Add user → Create user**.
2. Điền email và mật khẩu. Với tài khoản do quản trị viên cấp cho luồng hiện tại,
   dùng tùy chọn xác nhận email ngay (Auto Confirm User), nếu Dashboard cung cấp.
   Nếu chưa xác nhận, phải hoàn tất xác nhận theo cấu hình Auth của project.
3. Copy **User UID** (UUID) của user vừa tạo. Đây là `auth.users.id`, không phải ID
   Django, email, organization public ID hay `organization_member.id`.

Supabase hỗ trợ quản lý user từ Dashboard; tài khoản cần membership Costing được
quản trị viên cấp riêng. [Supabase users](https://supabase.com/docs/guides/auth/users).
Ứng dụng chưa có self-signup, invite callback, password reset, OAuth hoặc giao diện MFA.

## Gán user vào organization

Các câu SQL dưới đây là **hướng dẫn thao tác dữ liệu cho quản trị viên**, chưa được
chạy tự động. Chạy tại Supabase SQL Editor sau khi thay placeholder bằng dữ liệu thật.
Không cần tạo bảng, constraint hay migration.

Đầu tiên kiểm tra organization hiện có:

```sql
SELECT id, code, name, is_active
FROM costing.organization
ORDER BY code;
```

Nếu chưa có organization, tạo organization với mã nghiệp vụ của bạn:

```sql
INSERT INTO costing.organization
    (public_id, code, name, timezone, is_active, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'YOUR_ORG_CODE', 'Tên tổ chức của bạn',
     'Asia/Ho_Chi_Minh', true, now(), now())
ON CONFLICT (code) DO NOTHING
RETURNING id, code, name;
```

Gán user bằng **UUID và organization code**, không hard-code organization ID.
Ví dụ sau cấp quyền đọc; không đổi role/quyền của membership đã tồn tại:

```sql
INSERT INTO costing.organization_member
    (organization_id, user_id, role_code, permissions,
     is_active, created_at, updated_at)
SELECT o.id, u.id, 'COSTING_VIEWER', ARRAY[]::text[], true, now(), now()
FROM costing.organization o
CROSS JOIN auth.users u
WHERE o.code = 'YOUR_ORG_CODE'
  AND u.id = 'REPLACE_WITH_SUPABASE_USER_UUID'::uuid
ON CONFLICT (organization_id, user_id)
DO UPDATE SET is_active = true, updated_at = now()
RETURNING organization_id, user_id, role_code, permissions, is_active;
```

Nếu không trả record, kiểm tra lại organization code/user UUID. Cả organization
và membership cần `is_active=true`. Để user được tạo/sửa Cost Element, quản trị viên
có thể chọn role `ADMIN` khi tạo membership hoặc cấp explicit grants
`cost_element.create`, `cost_element.edit` cho role hiện có. Dữ liệu sensitive vẫn
cần grant riêng theo policy đã triển khai.

Các role được constraint hiện tại chấp nhận:
`ADMIN`, `COSTING_VIEWER`, `COST_ACCOUNTANT`, `FORMULA_DESIGNER`, `APPROVER`,
`PRICING_MANAGER`, `AUDITOR`.

Currency/UoM Category/UoM là danh mục global nên ngay cả organization ADMIN vẫn
cần explicit grants `currency.create/edit`, `uom_category.create/edit`,
`uom.create/edit` để ghi. Giữ policy hiện có, không tự cấp tất cả quyền.

Kiểm tra membership sau khi gán:

```sql
SELECT m.user_id, o.code, o.is_active AS organization_active,
       m.role_code, m.permissions, m.is_active AS membership_active
FROM costing.organization_member m
JOIN costing.organization o ON o.id = m.organization_id
WHERE m.user_id = 'REPLACE_WITH_SUPABASE_USER_UUID'::uuid;
```

## Đăng nhập, kiểm tra session và Cost Element

1. Mở **http://127.0.0.1:8000/accounts/login/**, nhập email/mật khẩu Supabase.
2. Nếu thuộc nhiều organization, chọn workspace tại `/accounts/organizations/`.
3. Mở **http://127.0.0.1:8000/accounts/session/** trên cùng trình duyệt.
   JSON phải có `authenticated=true`, `user_id` trùng User UID, `workspace_state=selected`,
   organization/role/permission đúng. Endpoint không xuất token hay session key.
4. Mở **http://127.0.0.1:8000/master-data/cost-elements/**. Có membership đọc → 200;
   danh sách chưa có Cost Element vẫn hiển thị empty state. Thiếu membership → 403 rõ ràng.
5. Nhấn **Đăng xuất** ở topbar. Đây là POST có CSRF; GET `/accounts/logout/` trả 405.
   Mở lại Cost Element phải chuyển về login. Tab ẩn danh chưa đăng nhập cũng chuyển login.

Cookie trình duyệt tên `sessionid` chỉ là ID ngẫu nhiên, `HttpOnly`, `SameSite=Lax`.
Không copy nội dung file session vào log hoặc gửi file session khi trao đổi lỗi.

## Session và quyết định kiến trúc

- Dùng official modular SDK `supabase-auth==2.32.0`, không cần toàn bộ Supabase SDK
  hay service-role key. `get_user(access_token)` kiểm tra identity từ Supabase ở mỗi
  request. Không tin session/JWT payload chưa được xác minh làm identity.
- Password không trim; email được Form normalize. Lỗi upstream được chuyển thành
  thông báo chung, không xuất response body, traceback hay credential.
- Session lưu bằng Django file backend trong `.runtime/sessions`, lock trong
  `.runtime/session-locks`, cả hai gitignored và ngoài static. Có thể đổi
  `SESSION_FILE_PATH`/`COSTING_SESSION_LOCK_PATH` sang thư mục riêng do tài khoản chạy
  ứng dụng sở hữu. Trên Windows cần ACL hạn chế quyền đọc cho các thư mục đó.
  Signed-cookie sessions không mã hóa payload nên không dùng để giữ Auth tokens.
  [Django sessions](https://docs.djangoproject.com/en/5.2/topics/http/sessions/).
- `portalocker==4.4.0` khóa theo session từ trước lúc load đến sau lúc save.
  Các request song song trên **cùng một host** không dùng refresh token cũ đồng thời.
  Token đã rotate được lưu ngay trước business code, kể cả response sau đó là 500.
- Login flush session cũ và rotate CSRF, không giữ organization của tài khoản trước.
  Logout xóa session local dù Supabase đang lỗi; khi khả dụng, gọi logout scope `local`
  để kết thúc phiên Auth này, không đăng xuất các thiết bị khác. JWT đã cấp có thể còn
  hợp lệ đến expiry trên dịch vụ khác; cookie Django cũ không replay được sau flush.
  [Supabase signout](https://supabase.com/docs/guides/auth/signout),
  [Supabase sessions](https://supabase.com/docs/guides/auth/sessions).
- `/admin/` giữ authentication kỹ thuật Django riêng. Adapter nghiệp vụ không gọi
  `django.contrib.auth.login`, không tạo hoặc đồng bộ Django User, không query Django
  auth tables để xác thực request Costing.
- Reuse `get_workspace`, `permissions_for`, actor resolver, error handlers, organization
  switch và Foundation UI. Thay membership/role ở DB có hiệu lực ở request kế tiếp.

## Files và kiểm thử

Tạo `apps/accounts/`: adapter, UUID principal, session helper, middleware, forms,
views, URLs, system checks, exceptions, backend/HTTP contract/concurrency/browser tests.
Tạo templates login, chọn organization và thông báo Auth unavailable.

Sửa settings/URL/test settings, `master_data/access.py`, `errors.py`, request middleware, organization
switch, topbar, test expectations của redirect mới, Tailwind source/output,
requirements, `.env.example`, `.gitignore`, README và AI context.
Không sửa `apps/core/models.py` hay database schema.

Đã chạy:

```powershell
python manage.py check
python -m pip check
npm run build:css
# Tests backend + browser với fixture PostgreSQL local riêng:
$env:COSTING_BROWSER_TESTS = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
```

Kết quả: Django check không có lỗi; dependency check pass; Tailwind 4.3.3 production
build pass; **105/105 tests pass**, gồm 29 tests mới cho auth/browser và 76 tests
trước đó. Test coverage gồm SDK HTTP contract, UUID mapping, permissions/membership,
CSRF, redirect/HTMX, session fixation, refresh/concurrency/500, logout replay,
provider outage và browser login trên desktop/mobile. Browser screenshot ở
`artifacts/screenshots/auth-*.png` chỉ chứa fixture giả.

## Giới hạn hiện tại

- Chưa thử email/password của tài khoản Supabase thật; live check chỉ xác nhận Auth
  settings và public key kết nối được. Cần tạo user/gán organization rồi kiểm thử theo
  hướng dẫn trên. Database inspection không phát hiện mismatch cần sửa schema.
- File session/lock hỗ trợ deployment một host với nhiều worker. Nhiều host/container
  cần shared session store và distributed locking adapter trước khi mở rộng; không
  đổi riêng `SESSION_ENGINE` mà bỏ khóa refresh token.
- Supabase phải khả dụng để xác minh request; outage trả 503 và giữ session cho lần
  retry, không bypass authorization. CAPTCHA/MFA/OAuth/invite/reset chưa có UI;
  user có verified MFA factor không được password-only flow cấp quyền AAL1.
- Chưa có UI quản trị membership, role và user. Quản trị viên thao tác Dashboard/SQL
  theo quyền thực tế. Không tự provision user, organization hay ADMIN từ metadata.
- Scheduled cleanup `python manage.py clearsessions` có thể xóa session đã hết hạn.
  Lock files được giữ để tránh đổi inode khi request đang chạy; dọn lock cũ trong
  maintenance khi đã dừng toàn bộ worker.

Task authentication đã hoàn thành; không triển khai thêm module nghiệp vụ.
Bước tiếp theo nên là UAT authentication/membership bằng tài khoản thật trước khi
chọn vertical slice mới.
