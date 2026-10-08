# Supplier + Supplier Price

Iteration 07/10/2026, single-company/no-auth; UI tiếng Việt. Chỉ triển khai nhà
cung cấp và giá mua; không triển khai BOM/Costing/approval hoặc module tiếp theo.

## Model và database thực tế

Models giữ nguyên tại `apps/core/models.py`, `managed=False`. Metadata/constraints,
indexes, triggers và incoming FK đã được kiểm tra bằng transaction READ ONLY trên
Supabase. Không sửa schema, migration, credentials hoặc dữ liệu database thật.

Supplier:

- `id`, `organization`, `code` (120), `name` (255).
- `tax_code` (100, nullable), `default_currency_code` (FK Currency, nullable),
  `payment_terms` (nullable), `is_active`, `created_at`, `updated_at`.
- `uq_supplier`: unique `(organization_id, code)`; trigger cập nhật `updated_at`.
- Không có country/address/email/phone/description/metadata; không tạo field giả.

SupplierPrice:

- `id`, `organization`, `supplier`, `item`, `price_uom`, `currency_code`.
- `min_qty`, `unit_price`: numeric(24,8), >= 0 theo CHECK.
- `tax_inclusive`, `tax_rate` nullable, `tax_recoverable_ratio` mặc định 1.
  Hai tỷ lệ numeric(12,8), trong [0,1]; không tự áp luật thuế hay tính landed cost.
- `effective_from` bắt buộc, `effective_to` nullable và phải **sau** ngày bắt đầu.
- `source_type` (50, nullable), `source_reference` nullable.
- `status`: DRAFT / IN_REVIEW / APPROVED / EFFECTIVE / RETIRED theo CHECK;
  `created_by` UUID nullable, `created_at`. Không có `updated_at`, `is_active`,
  maximum quantity, lead time, notes hoặc số báo giá riêng.
- `created_by` có FK tới auth.users trong DB, vẫn giữ nguyên; create để NULL,
  không dùng Auth hoặc query user. Edit không giả actor hay đổi thông tin tạo.
- Không có uniqueness/exclusion chống trùng/chồng giá, trigger immutability hoặc
  incoming FK từ bảng khác tới supplier_price. Có index lookup theo company,
  item, supplier, status, effective_from DESC.

## Luồng đã triển khai

- `/master-data/suppliers/`: list, code/name/tax search, active/currency filters,
  sort code/name/created_at, pagination 25/50/100, detail/create/edit.
- `/master-data/supplier-prices/`: list, supplier/item code/name search, filters
  supplier/item/currency/UoM/date status/record status, sort effective_from/
  supplier/item/unit_price, pagination 25/50/100, detail/create/edit.
- Tên URL giữ `master_data:supplier_*`, `master_data:supplier_price_*`.
- HTMX trả shared table partial; thường/history restore trả trang đầy đủ.
  Search debounce 400ms, giữ query string khi lọc/sort/paginate/back.
- Reuse header, breadcrumbs, search/filter, table, pagination, empty state,
  form layout/field errors, toast, badges, CSRF, deactivation confirmation.
- Sidebar active đúng; mọi nhãn/validation/thông báo bằng tiếng Việt. Technical
  identifiers, mã VND/USD, SKU, BOM, VAT, FX và API giữ nguyên.
- Không expose organization/user/status actor/JSON. Không có hard delete.
  Supplier có thể ngừng/kích hoạt qua form với confirmation hiện có.

## Validation, transactions và query

- Code supplier trim + uppercase; name trim; tax/payment/source/reference trim,
  optional text trống về NULL. Unique code trong company có kiểm tra trước và
  IntegrityError 23505 được đổi thành «Mã nhà cung cấp đã tồn tại.».
- Bắt buộc supplier/item/currency/price_uom/unit_price/effective_from;
  unit_price/min_qty >= 0; tỷ lệ thuế/khấu trừ trong [0,1]; end > start theo DB.
  Không tự thêm enum source_type, quantity maximum hoặc conversion policy.
- Dropdown tạo mới chỉ có danh mục active; supplier/item thuộc company context.
  Edit cho giữ FK cũ đã ngừng hoạt động, không cho chọn FK inactive khác.
  Hiển thị mã — tên hoặc tên đơn vị (ký hiệu), không raw ID.
- Services dùng allow-list, atomic transaction, khóa/reload FK để kiểm tra dữ
  liệu hiện tại. Không tin Model object stale; xử lý lỗi DB bằng message tiếng Việt.
- Company lấy qua `get_default_organization()`/workspace cache hiện có;
  InternalAccess tập trung, không user/session/membership.
- Supplier select_related default_currency_code; price select_related supplier,
  item, price_uom, currency_code; company và cả company-owned references phải khớp.
  Search/filter/sort/pagination ở PostgreSQL; không N+1. Test xác nhận đọc toàn bộ
  FK của nhiều giá chỉ 1 query, render list 21 giá tối đa 8 queries cả filters.
- UI số theo dấu phân cách Việt Nam và bỏ zero thừa; không làm tròn precision DB.
  Detail thuế hiển thị %, form nhập tỷ lệ 0..1. Number input HTML dùng dấu chấm,
  help text giải thích. Ngày list/detail dd/mm/yyyy; datetime dd/mm/yyyy HH:mm;
  date input native theo locale trình duyệt, giá trị gửi server ISO yyyy-mm-dd.

## Hiệu lực và lịch sử

- Khoảng UI gồm cả ngày đầu/ngày cuối; null end không giới hạn. Trước start:
  «Sắp hiệu lực»; sau end: «Hết hiệu lực»; còn lại: «Đang hiệu lực».
  Annotation ORM chỉ dùng hiển thị/lọc, không lưu status mới trong DB.
- Status bản ghi có nhãn riêng (Nháp/Chờ duyệt/Đã duyệt/Đang hiệu lực/Ngừng hiệu lực).
  Giá mới là DRAFT với actor NULL; edit giữ status đang có. Không có approval action.
  Giá Nháp có thể nằm trong khoảng hiệu lực; badge ngày không có nghĩa được duyệt.
- Thêm giá mới tạo bản ghi riêng, không overwrite giá cùng item/supplier. Edit
  không thay đổi các bản ghi kỳ khác; UI nhắc thêm bản ghi mới khi đổi kỳ giá.

## Files

Tạo:

- `templates/master_data/partials/supplier_rows.html`, `supplier_price_rows.html`.
- `apps/master_data/test_supplier.py`, `test_supplier_browser.py`.
- `docs/SUPPLIER_PRICE.md`.

Sửa:

- `apps/master_data/constants.py`, `forms.py`, `validators.py`, `services.py`,
  `selectors.py`, `views.py`, `urls.py`, `access.py`, `navigation.py`, `presentation.py`.
- `apps/master_data/testing.py`, `test_vietnamese_ui.py`.
- `apps/product/forms.py`: import UnitChoiceField dùng chung, giữ hành vi cũ.
- `templates/master_data/partials/reference_data_form_content.html`,
  `reference_data_detail_content.html`.
- Generated `static/css/app.css` qua Tailwind CLI.
- `README.md`, `docs/00_AI_CONTEXT.md`, `FRONTEND_IMPLEMENTATION_SPEC.md`,
  `03_SYSTEM_ARCHITECTURE.md`.

Không cài dependency mới; giữ Tailwind 4.3.3, HTMX 2.0.11, Alpine 3.17.4.

## Kiểm thử và chạy

```powershell
.\env\Scripts\python.exe manage.py check
npm run build:css
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.master_data.test_supplier apps.master_data.test_vietnamese_ui
$env:COSTING_BROWSER_TESTS = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

Test fixture thêm unmanaged Supplier/Price cùng CHECK/unique đã inspect vào
`test_costing_slice` trên PostgreSQL localhost riêng. Không chạy schema DDL trên
Supabase. Tests bao gồm CRUD/search/all filters/sort/pagination, không auth,
company scope, stale FK, IntegrityError race/rollback, price/tax/date boundaries,
history/overlap behavior, Decimal precision, HTMX/history, CSRF, tiếng Việt và query.
Browser mới kiểm tra tạo/sửa hai module, input/error giữ nguyên, search/filter/
paginate/sort/back, locale vi-VN, mobile không tràn viewport và không lỗi JS.
Screenshots: `artifacts/screenshots/supplier*.png` (gitignored).

Kết quả cuối:

- `manage.py check`: đạt, không có lỗi.
- `npm run build:css`: đạt, Tailwind 4.3.3 production minified output.
- Targeted Supplier + tiếng Việt: 38 tests đạt.
- Browser Supplier riêng: 1 test đạt.
- Full regression: **195 tests đạt**, gồm 5 browser tests, 48,443 giây, không skip.
- Review: không thêm auth/membership, raw English label, dynamic Tailwind class,
  migration/schema change hoặc business logic vào JS/template; không N+1.
- `git diff --check`: đạt; Git chỉ nhắc line ending LF/CRLF của README trên Windows.

Read-only smoke test Supabase: root 302 tới Cost Element; Cost Element, Item,
Product, SKU, hai list và hai create form trả 200; hai HTMX list 200 đúng partial;
không cookie sessionid. Chưa có bản ghi Supplier/Price trên DB thật lúc kiểm tra,
nên create/edit/detail được kiểm thử trên PostgreSQL fixture và trình duyệt local.

Chạy Django `python manage.py runserver`; watcher `npm run dev:css` ở terminal khác.
Không cần config mới ngoài APP_MODE/default organization đã có.

## Giới hạn và iteration tiếp theo

- Không tự chặn overlap/duplicate; DB/docs chưa xác định resolver priority cho
  bậc số lượng hoặc khoảng giá chồng nhau. Cần quyết định nghiệp vụ trước Costing.
- Edit giá đã dùng/chốt vẫn chưa có usage lock hoặc cơ chế tạo version thay thế;
  không bảo đảm immutable lịch sử chỉ bằng UI nhắc nhở. Cần thiết kế cùng snapshot
  và trace của Costing. Không triển khai guardrail/version workflow trong task này.
- Không có approval/status transition; giá mới vẫn Nháp. Không đổi giá thành
  EFFECTIVE tự động dựa vào ngày, không sử dụng những giá này cho tính toán ở đây.
- Không auto conversion, landed cost, pháp lý VAT, delete hay contact fields ngoài schema.
- Đề xuất tiếp theo: BOM / Định mức nguyên vật liệu theo Item + SKU. Chỉ là đề xuất;
  iteration này dừng tại Supplier/Supplier Price.
