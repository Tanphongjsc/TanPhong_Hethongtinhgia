# Trung tâm sản xuất, nguồn lực và đơn giá nguồn lực

Iteration ngày 07/10/2026. Truy cập trực tiếp, một công ty, UI tiếng Việt.
Không thay đổi business model, schema, migration hoặc dependency.

## Model và schema thực tế

Đã đối chiếu `apps/core/models.py` với metadata Supabase bằng transaction chỉ đọc.
Các model giữ `managed=False`; không tạo model trong app nghiệp vụ.

| Model | Fields thực tế | Quan hệ / constraint |
|---|---|---|
| WorkCenter | id, organization, code, name, site_code, capacity_value, capacity_uom, normal_capacity_value, is_active, created_at, updated_at | capacity_uom → Uom; UNIQUE organization + code (`uq_work_center`); hai giá trị công suất NULL hoặc >= 0 |
| Resource | id, organization, work_center, code, name, resource_type, capacity_value, capacity_uom, metadata, is_active, created_at, updated_at | WorkCenter và capacity_uom tùy chọn; UNIQUE organization + code (`uq_resource`); CHECK loại nguồn lực |
| ResourceRate | id, organization, resource, rate_type, amount, currency_code, per_uom, effective_from, effective_to, status, source_reference, created_by, created_at | Resource, Currency, Uom bắt buộc; amount >= 0; ngày kết thúc NULL hoặc > ngày bắt đầu; CHECK trạng thái |

Công suất / đơn giá dùng Decimal(24,8). WorkCenter/Resource không có mô tả riêng.
ResourceRate không có `rate`, `rate_uom`, `currency`, `is_active`, `updated_at` hay
version_no; dùng đúng `amount`, `per_uom`, `currency_code`. Metadata không hiển thị.

Resource type đúng CHECK: MACHINE (Máy móc), LABOR (Nhân công), WORK_CENTER
(Trung tâm sản xuất), SERVICE (Dịch vụ). Không thêm ENERGY/FACILITY vào enum.
`rate_type` là varchar(50) bắt buộc, không có CHECK enum hoặc danh mục riêng, chưa
có mã đã sử dụng trong database tại thời điểm inspect. Form cho nhập mã nghiệp vụ,
trim và giữ casing; filter lấy các mã distinct đã lưu, không tạo enum mới.

Status đúng DB: DRAFT, IN_REVIEW, APPROVED, EFFECTIVE, RETIRED. UI dịch qua
`presentation.py`, không thay stored values. Record mới Nháp, created_by NULL.
Audit actor FK nullable tới auth.users được giữ nguyên mapping, không dùng Auth.

Organization FK còn tồn tại trong schema: reuse duy nhất company context hiện có
để tương thích DB. Không có workflow, selector, membership hoặc authentication mới.

## Routes và chức năng

Giữ app/namespace BOM hiện có cho nghiệp vụ sản xuất, không tạo app mới.

| Module | List | URL names |
|---|---|---|
| Trung tâm sản xuất | `/bom/work-centers/` | bom:work_center_list/create/detail/edit |
| Nguồn lực sản xuất | `/bom/resources/` | bom:resource_list/create/detail/edit |
| Đơn giá nguồn lực | `/bom/resource-rates/` | bom:resource_rate_list/create/detail/edit |

Mỗi route có `/create/`, `/<id>/`, `/<id>/edit/`. GET đầy đủ trả page; HTMX trả
table/form/detail partial. History restore trả full page. POST có CSRF; success
redirect/HX-Redirect và toast tiếng Việt; invalid POST giữ input và field errors.

- WorkCenter tìm mã/tên/mã địa điểm, lọc hoạt động, sort mã/tên/ngày tạo. Detail
  hiển thị tối đa 10 nguồn lực kèm link tới danh sách có filter/pagination đầy đủ.
- Resource tìm mã/tên, lọc loại/trung tâm/hoạt động; sort mã/tên/loại/ngày tạo.
  Detail có lịch sử đơn giá phân trang, tìm kiếm/sort/HTMX, link tới danh sách giá
  của nguồn lực và thêm đơn giá được chọn sẵn nếu nguồn lực còn hoạt động.
- ResourceRate tìm mã/tên nguồn lực hoặc trung tâm; lọc nguồn lực/loại/trung tâm/
  mã loại đơn giá/tiền tệ/đơn vị tính/hiệu lực theo ngày/trạng thái bản ghi;
  sort nguồn lực/đơn giá/ngày bắt đầu/ngày tạo.
- Pagination mặc định 25, chọn 25/50/100; debounce 400 ms; giữ query string khi
  sort/paginate và dùng `hx-push-url=true`. Có fallback GET/POST không JavaScript.
- Không hard delete; WorkCenter/Resource có thể ngừng hoạt động qua form và xác nhận.
- Sidebar đúng menu đang truy cập; thứ tự Sản xuất: BOM, Bao bì, Trung tâm,
  Nguồn lực, Đơn giá nguồn lực, Quy trình sản xuất (chưa triển khai).

## Validation và effective date

- Code/name bắt buộc; code trim/uppercase, name trim; duplicate kiểm tra theo scope
  và DB unique bảo vệ trường hợp ghi đồng thời. IntegrityError chuyển thông báo Việt.
- WorkCenter optional trên Resource, không ép thành required trái schema.
- Công suất không âm; khi nhập giá trị phải chọn đơn vị công suất. Không tự suy luận
  đơn vị, hiệu suất hoặc quan hệ giữa công suất thiết kế và công suất bình thường.
- Amount **>= 0** theo CHECK thực tế (khác ví dụ > 0 trong prompt). Chấp nhận 0,
  bác số âm/NaN/Infinity/vượt precision. Không thay DB hoặc tự siết rule số 0.
- Resource/Currency/Uom bắt buộc, danh mục active khi tạo; edit giữ được tham chiếu
  cũ inactive. Danh mục của nguồn lực/trung tâm dùng scope nội bộ có sẵn; dữ liệu
  legacy có quan hệ không nhất quán không được lộ qua list/detail hoặc chọn mới.
- References được đọc lại và khóa trong transaction trước khi validate/save để
  tránh lựa chọn active đã stale. Allow-list không nhận organization/status/actor/
  timestamps/metadata từ request. Metadata cũ và trạng thái gốc giữ nguyên khi edit.
- Ngày bắt đầu bắt buộc; ngày kết thúc phải **sau**, không bằng ngày bắt đầu theo
  CHECK `ck_resource_rate_period`. UI coi ngày kết thúc bao gồm chính ngày đó.
- Hiệu lực theo ngày là annotation: Sắp hiệu lực nếu start > hôm nay, Hết hiệu lực
  nếu end < hôm nay, còn lại Đang hiệu lực. Đây không phải resolver chọn giá cho
  Costing; bản ghi Nháp vẫn có thể thuộc khoảng ngày hiện tại và có hai badge riêng.
- Giá kỳ mới được thêm bằng bản ghi mới; không tự ghi đè giá cũ. Edit vẫn hỗ trợ
  điều chỉnh bản ghi hiện tại và có thông báo nhắc thêm bản ghi khi thay đổi kỳ.

## Kiến trúc và query

Request → View → Form → Selector/Service → core models → PostgreSQL.
Policy nội bộ tập trung `InternalAccess`, không user-based permissions.

Reuse ReferenceDataForm, CompactNumberInput, ReferenceChoiceField, UnitChoiceField,
table_context/date_status/get_by_pk, ORM search/filter/pagination, HTMX helpers,
shared list/form/status/filter/table/empty/pagination/toast/error components.
Không generic CRUD framework hoặc design system mới.

Service atomic, lock record/references, validate, full_clean và persist; thứ tự
dependency Rate → Resource → WorkCenter → Uom → Currency. Unique/check/FK errors
được map về field hoặc lỗi chung thân thiện, không raw SQL error.

WorkCenter select_related(capacity_uom); Resource select_related(work_center,
capacity_uom); ResourceRate select_related(resource, resource__work_center,
currency_code, per_uom). Search/filter/sort/LIMIT/OFFSET tại DB. History phân trang,
không load toàn bộ giá. Query count của list không tăng khi thêm hàng; truy cập
các relation của từng selector chỉ cần một query. Không raw SQL trong runtime.

Tiền/số dùng format Việt, giữ 8 chữ số nếu có ý nghĩa và bỏ số 0 dư; ngày dd/mm/yyyy.
Currency/UoM/rate_type là mã dữ liệu, không dịch hoặc hard-code. Input có label,
aria-describedby/aria-invalid; th/caption đúng semantic; table scroll nằm trong
container trên mobile. Alpine chỉ cho UI địa phương, không tính giá.

## Files

Tạo:

- `apps/bom/resource_constants.py`, `resource_validators.py`, `resource_forms.py`,
  `resource_selectors.py`, `resource_services.py`, `resource_views.py`, `resource_urls.py`.
- `apps/bom/test_resources.py`, `test_resources_browser.py`.
- `templates/bom/resources/detail.html` và partials `detail_content.html`,
  `rate_history.html`, `work_center_rows.html`, `resource_rows.html`, `resource_rate_rows.html`.
- `docs/WORK_CENTER_RESOURCE_RATE.md`.

Sửa:

- `apps/bom/urls.py`.
- `apps/master_data/access.py`, `navigation.py`, `presentation.py`, `testing.py`.
- `README.md`, `docs/00_AI_CONTEXT.md`, `docs/03_SYSTEM_ARCHITECTURE.md`,
  `docs/FRONTEND_IMPLEMENTATION_SPEC.md`.
- `static/css/app.css` chỉ qua Tailwind build.

## Kiểm thử

Fixtures unmanaged/CHECK/unique names chỉ tạo trong localhost `test_costing_slice`;
runner chặn Supabase, --keepdb và parallel. Không tạo business migration.

```powershell
.\env\Scripts\python.exe manage.py check
npm run build:css
powerShell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.bom.test_resources
$env:COSTING_BROWSER_TESTS='1'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path (Get-Location).Path 'artifacts\playwright'
powerShell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

Tests bao phủ list/detail/search/filter/sort/pagination/create/edit/duplicate/
invalid/empty/HTMX, precision, date boundary, reference inactive/stale/scope,
historical row unchanged khi thêm giá mới, CHECK DB, integrity error mapping,
CSRF, internal policy, no membership/session và query count. Browser tạo/chỉnh sửa
cả ba module, validation/CSRF, pagination/search/filter/history/back navigation,
responsive 390 px và JS error checks. Screenshots/log tại `artifacts/` (gitignored).

Kết quả ngày 07/10/2026:

- `manage.py check`: PASS, không có issue.
- `npm run build:css`: PASS, Tailwind 4.3.3, minified generated CSS; không đổi dependency.
- Targeted lần đầu sau sửa helper test: 35 tests PASS; targeted kèm browser: 36 PASS.
- Sau bổ sung kiểm tra stale references/legacy scope/rendered query count, full suite
  **316 tests PASS / 75.666 s**, gồm **39 tests mới** và **8 browser flows** toàn hệ thống.
- GET smoke trong transaction READ ONLY với Supabase: sáu list/create pages mới
  và ba HTMX lists đều 200; root 302 tới Cost Element; Cost Element/BOM/Packaging
  vẫn 200, không session cookie. Không có POST/DDL/DML lên database thật.
- Kiểm tra screenshot desktop/mobile, UTF-8, syntax và source audit; không N+1,
  dynamic Tailwind class hoặc business logic tính giá trong template/JavaScript.

## Giới hạn và bước kế tiếp

- Không có version table, immutable trigger hoặc incoming FK tới ResourceRate.
  Chưa có policy/usage lock khi Costing sử dụng giá. Generic immutable-version
  assumptions trong tài liệu cũ chưa áp dụng cho ResourceRate.
- Không có unique/exclusion constraint hoặc policy rõ ràng chặn overlap trên
  Resource + rate_type + Currency + Uom; cho phép các bản ghi theo DB hiện tại.
- Chưa chuyển trạng thái/duyệt giá. Hiệu lực theo ngày chỉ phục vụ tra cứu; chưa
  lựa chọn một giá duy nhất cho Costing hoặc tự quy đổi UoM.
- Chưa có mô tả cho hai master, catalog riêng cho rate_type, lịch sử chỉnh sửa
  chi tiết, tính công suất/production cost hoặc Scheduling; không tự thêm field.

Vertical slice đề xuất tiếp theo: Routing / Quy trình sản xuất. Iteration này dừng
ở WorkCenter, Resource và ResourceRate, không triển khai Routing.
