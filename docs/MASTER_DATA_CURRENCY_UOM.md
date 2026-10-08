# Currency + UoM Category + UoM + UoM Conversion

> **SUPERSEDED về authentication/access — 07/10/2026:** organization membership,
> user grants và organization switching trong báo cáo lịch sử này không còn dùng.
> Các module dùng full internal access và company context tập trung; Organization
> Scope đã được bỏ khỏi UI. Xem [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).

Báo cáo iteration, không thay thế canonical implementation spec. Tài liệu
canonical thực tế nằm tại `docs/`, thay vì đường dẫn `docs/ai/` trong prompt.

## Phạm vi hoàn thành

Bốn danh mục có list, search, filters, sorting, pagination 25/50/100, detail,
create/edit, validation, empty state, permission hooks và HTMX partials.
Currency / UoM Category / UoM đổi trạng thái qua edit; UI xác nhận deactivation.
Không có hard delete. Item chỉ là lookup cho conversion, không có CRUD Item.

| Module | URL list | URL names |
| --- | --- | --- |
| Currency | `/master-data/currencies/` | `master_data:currency_{list,create,detail,edit}` |
| UoM Category | `/master-data/uom-categories/` | `master_data:uom_category_{list,create,detail,edit}` |
| UoM | `/master-data/uoms/` | `master_data:uom_{list,create,detail,edit}` |
| UoM Conversion | `/master-data/uom-conversions/` | `master_data:uom_conversion_{list,create,detail,edit}` |

Detail/edit Currency nhận primary key `code`; các module còn lại nhận `id`.

## Files tạo trong iteration

```text
apps/master_data/test_reference_data.py
apps/master_data/test_reference_browser.py
templates/master_data/reference_data_list.html
templates/master_data/reference_data_form.html
templates/master_data/reference_data_detail.html
templates/master_data/partials/reference_data_filters.html
templates/master_data/partials/reference_data_table.html
templates/master_data/partials/reference_data_actions.html
templates/master_data/partials/reference_data_status.html
templates/master_data/partials/reference_data_form_content.html
templates/master_data/partials/reference_data_detail_content.html
templates/master_data/partials/currency_rows.html
templates/master_data/partials/uom_category_rows.html
templates/master_data/partials/uom_rows.html
templates/master_data/partials/uom_conversion_rows.html
docs/MASTER_DATA_CURRENCY_UOM.md
```

## Files sửa trong iteration

```text
apps/master_data/access.py
apps/master_data/constants.py
apps/master_data/context_processors.py
apps/master_data/errors.py
apps/master_data/forms.py
apps/master_data/navigation.py
apps/master_data/selectors.py
apps/master_data/services.py
apps/master_data/testing.py
apps/master_data/validators.py
apps/master_data/views.py
apps/master_data/urls.py
templates/layouts/app_shell.html
templates/layouts/sidebar.html
templates/components/filter_select.html
templates/components/pagination.html
templates/components/search_box.html
templates/components/sort_header.html
templates/partials/form_errors.html
static/js/app.js
static/js/htmx-config.js
static/css/app.css (generated bằng Tailwind)
README.md
```

Không sửa core models, PostgreSQL schema, business migrations, config/settings
hay dependencies. Không cài dependency mới; giữ Tailwind 4.3.3, HTMX 2.0.11,
Alpine.js/Focus 3.17.4 và Playwright hiện có.

## Reuse và kiến trúc

Giữ Request → View → Form → Service/Selector → core models → PostgreSQL.
Các module có form, validator, service và selector riêng. Helper nhỏ chia sẻ
pagination/sorting, form styling, transaction/error handling và request rendering;
không thêm CRUD framework hoặc architecture khác.

Reuse shell, sidebar/topbar, breadcrumb/header, button, form/detail fields,
status badge, search, filter select, sort header, pagination, loading, empty state,
toast và confirm dialog. Templates chung phục vụ bốn danh mục; mỗi danh mục có
rows partial riêng. Sidebar active state so khớp URL name chính xác để tránh
UoM và UoM Conversion cùng được đánh dấu active.

Search/filter/sort/pagination chạy ở ORM. UoM dùng `select_related("category")`;
conversion dùng `select_related("organization", "from_uom", "to_uom", "item")`.
Test xác nhận đọc các relations này chỉ cần một SELECT.

HTMX giữ convention Cost Element: outerHTML table swap, hx-select, push URL,
debounce 400ms, loading và request sync. History restore trả full page, không
lưu DOM history cache. Form dùng POST Django với CSRF; HTMX callers nhận form
partial và HX-Redirect. JS chỉ quản lý UI và đồng bộ sort/page size sau swap.

## Database và validation

Đã kiểm tra read-only các columns, constraints, indexes và triggers trong schema
`costing`. Mapping bốn model phù hợp database. Không có schema mismatch cần sửa.

- Currency: tạo mới trim/uppercase code, đúng 3 ký tự, unique; decimal places
  0–8. PK bị khóa khi edit, kể cả record chưa được tham chiếu. Legacy casing
  của PK được giữ nguyên để không làm hỏng references.
- UoM Category: code/dimension trim/uppercase; code unique, dimension bắt buộc.
- UoM: code trim/uppercase và unique; name/symbol trim; category bắt buộc;
  precision 0–12. Không tạo mới với category inactive; edit giữ được reference
  inactive hiện tại. Đổi category bị từ chối nếu làm conversion chung hiện có
  khác category.
- Conversion: from/to khác nhau, factor Decimal dương, tối đa 24 chữ số trong
  đó 12 chữ số thập phân; effective_to phải sau effective_from nếu có. Quy đổi
  chung không có Item yêu cầu cùng category. Quy đổi có Item cho phép khác
  category; Item phải thuộc organization hiện tại. References inactive chỉ
  được giữ nếu đã gắn với record đang edit.

Service dùng allow-list fields, đọc lại references, transaction và row locks.
Các UoM liên quan được lock theo PK để bảo vệ quy tắc category khi có ghi đồng
thời. Organization conversion được backend gán; input organization/id/timestamps
không được dùng để ghi. IntegrityError chuyển thành lỗi thân thiện trong form.
Production unexpected errors trả trace ID, không hiển thị traceback.

## Organization và permission

Currency, UoM Category, UoM không có organization field: đây là dữ liệu dùng
chung. Role đọc hợp lệ theo hook Cost Element được xem. Create/edit các bảng
dùng chung yêu cầu grant rõ ràng trong membership permissions, kể cả org ADMIN:

```text
currency.view / currency.create / currency.edit
uom_category.view / uom_category.create / uom_category.edit
uom.view / uom.create / uom.edit
uom_conversion.view / uom_conversion.create / uom_conversion.edit
```

Conversion mới luôn thuộc tổ chức hiện tại; ADMIN được create/edit conversion
thuộc tổ chức theo policy hiện có. Các grants khác có thể cấp quyền tương ứng.
Conversion global (`organization IS NULL`) có thể đọc khi không có Item hoặc
Item thuộc tổ chức hiện tại; không được edit qua UI tổ chức. Conversion của tổ
chức khác và mọi conversion tham chiếu Item của tổ chức khác bị ẩn.

Các hook `permissions.can_{view,create,edit}_{resource}` được enforce ở view;
service kiểm tra quyền ghi độc lập. Reuse `get_workspace`, signed-session
organization selection và verified actor resolver. Không hard-code IDs hay
admin cho mọi user; không sửa live memberships/grants.

## Chạy local và kiểm thử

```powershell
.\env\Scripts\Activate.ps1
python manage.py runserver
# Terminal khác:
npm run dev:css
```

Cần authenticated Supabase UUID và active organization membership qua
`COSTING_ACTOR_RESOLVER` như iteration trước; chưa có authentication integration
thì truy cập trang nghiệp vụ trả 403. Chi tiết setup trong README.

Commands kiểm chứng:

```powershell
python manage.py check
npm run build:css
node --check static/js/app.js
node --check static/js/htmx-config.js
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
# Bao gồm browser tests:
$env:COSTING_BROWSER_TESTS = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
```

Test runner dùng PostgreSQL 17 riêng tại 127.0.0.1:55432, database
`test_costing_slice`; không ghi Supabase. Test-only fixtures thêm Item,
ProductCategory (FK prerequisite) và UomConversion; không tạo business migrations.
CHECK constraints Currency/UoM/Conversion trong fixtures mirror constraints đã
kiểm tra read-only. Không dùng `--keepdb` hoặc parallel runner.

Kết quả: **76/76 tests đạt**, gồm 38 test Cost Element, 36 test danh mục mới và
2 browser tests. Kiểm tra CRUD/search/filter/sort/pagination, duplicate/range/
dates/category/Decimal, PK immutability, reference activity, organization isolation,
explicit grants, CSRF, empty states, HTMX/history, integrity race/rollback, errors
và N+1. Chromium kiểm tra các luồng create/edit, modal focus, toast, URL history,
responsive 1440/1100/800/390px; không JavaScript exception hoặc document overflow.
Screenshots chứa test fixtures nằm tại `artifacts/screenshots/` (gitignored).
Django check và Tailwind production build đạt.

## Giới hạn và bước tiếp

- Canonical docs và DB không quy định một base unit/category. DB chỉ có unique
  trên code UoM; nhiều base unit vẫn được phép.
- Conversion không có unique/exclusion constraint hoặc overlap policy trong docs.
  Duplicate và overlapping periods vẫn được phép. Chưa có resolver lựa chọn
  conversion, tự tạo chiều ngược hoặc conversion graph trong iteration này.
- Cross-category item-specific conversion tuân theo khả năng lưu hiện tại;
  không triển khai density/formula hay cách lựa chọn conversion để tính toán.
- Chưa nối authentication Supabase thực tế. Cần provision permission grants
  phù hợp vì các danh mục shared ảnh hưởng mọi tổ chức.
- Test fixtures không tái tạo Supabase RLS, auth.users FK và production triggers.
  CRUD đã kiểm tra trên PostgreSQL riêng; cần staging validation khi nối auth.
- Filters/forms dùng native selects; Item/UoM lookup rất lớn có thể cần search
  endpoint trong iteration được phê duyệt tiếp theo.

Vertical slice nghiệp vụ khuyến nghị tiếp theo: **Product Category + Item**, sau
khi nối trusted authentication/context và xác nhận policy shared-reference grants.
Iteration này dừng ở bốn danh mục Currency/UoM.
