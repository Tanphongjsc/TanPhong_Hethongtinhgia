# Product + SKU

Iteration 07/10/2026. Django Templates + HTMX + Alpine.js + Tailwind hiện có,
single-company nội bộ, không authentication/membership/organization UI.

Cập nhật sau iteration Packaging: editor cho SkuPackagingAssignment đã có ở
`/bom/packaging/<id>/skus/`; không nằm trong SKU master form và không thêm FK lên SKU.
Các giới hạn «chưa có packaging assignment editor» bên dưới là phạm vi lịch sử
của iteration Product/SKU, đã superseded về capability. Xem [PACKAGING_CONFIGURATION.md](PACKAGING_CONFIGURATION.md).

## Schema thực tế

Models vẫn ở `apps/core/models.py`, `managed = False`; đã kiểm tra metadata và
constraint Supabase bằng transaction read-only. Không có mismatch field, nullability,
length hoặc numeric precision; không tạo migration hay đổi schema/database thật.

Product:

- `organization`, `category` nullable, `output_item` nullable.
- `code` 120, `name` 255, `description` nullable.
- `costing_uom` required, `tax_class_code` nullable, `is_active`, timestamps.
- `uq_product`: unique `(organization_id, code)`.
- Không có `base_uom` hoặc metadata JSON. UI dùng «Đơn vị tính giá thành» cho
  `costing_uom`, không tạo field mới để khớp ví dụ trong prompt.

Sku:

- `organization`, `product` required, `sell_item` nullable.
- `code` 150, `name` 255, `barcode` nullable (100).
- `sales_uom`, `net_quantity` numeric(24,8), `net_quantity_uom` required.
- `attributes` JSON, `is_active`, timestamps.
- `uq_sku`: unique `(organization_id, code)`; `uq_sku_barcode`: unique
  `(organization_id, barcode)`; `ck_sku_net_quantity`: quantity > 0.
- Không có net_weight/gross_weight/description hoặc variant/size/pack_type columns.
  Lượng tịnh có thể là khối lượng, thể tích hoặc số lượng; không giới hạn đơn vị MASS.
- Bao bì là `SkuPackagingAssignment` riêng, không phải field trực tiếp trên Sku;
  không query/triển khai packaging trong iteration này.

Item, Product và SKU vẫn là ba entity riêng. `output_item`/`sell_item` là liên kết
FK tùy chọn có nhãn rõ ràng; không tạo Item tự động khi tạo sản phẩm hoặc SKU.

## File thay đổi và reuse

Tạo mới:

- `templates/product/partials/product_rows.html`, `sku_rows.html`.
- `apps/product/test_product_sku.py`, `test_product_sku_browser.py`.
- Tài liệu này.

Sửa:

- `apps/product/constants.py`, `forms.py`, `validators.py`, `selectors.py`,
  `services.py`, `views.py`, `urls.py`.
- `apps/master_data/access.py`, `navigation.py`, `forms.py`, `testing.py`,
  `test_vietnamese_ui.py`.
- Generated `static/css/app.css` qua build; không sửa trực tiếp output CSS.
- `README.md`, `docs/00_AI_CONTEXT.md`, `FRONTEND_IMPLEMENTATION_SPEC.md`.

Không xóa file hoặc thêm dependency. Không đổi settings, core models, static JS
hoặc Foundation design. Hooks policy Product/SKU tập trung trong InternalAccess,
không dựa vào user. ReferenceDataForm có hook normalization dùng chung để barcode
được trim trước validation. Không generic CRUD framework mới.

Reuse catalog list/form/detail, reference table/filter/actions/status, search 400ms,
pagination, empty states, form errors, toast, loading indicator và deactivation
confirmation. Normal request full page, HTMX partial với hx-push-url, query string
giữ khi search/filter/sort/page; history restore full page. POST giữ CSRF.

## Routes và chức năng

Product: `/product/products/`, `/create/`, `/<id>/`, `/<id>/edit/`;
namespace `product:product_list/create/detail/edit`.

- Tìm code/name/description; lọc category/costing_uom/active.
- Sort code/name/category/created_at; pagination 25/50/100.
- Form: nhóm, mã, tên, mô tả, đơn vị tính giá thành, liên kết Item đầu ra,
  mã nhóm thuế, trạng thái. Detail có timestamp và liên kết danh mục.

SKU: `/product/skus/`, `/create/`, `/<id>/`, `/<id>/edit/`;
namespace `product:sku_list/create/detail/edit`.

- Tìm code/name/product code/product name; lọc product/product category/active.
- Sort code/name/product/created_at; pagination 25/50/100.
- Form: sản phẩm, mã/tên SKU, mã vạch, đơn vị bán, lượng tịnh/đơn vị,
  liên kết Item bán, trạng thái. Không raw attributes JSON; giữ JSON cũ khi sửa.
- Sản phẩm/SKU inactive vẫn đọc được; deactivate/activate qua form edit, không delete.

## Validation và persistence

- Mã required/trim/uppercase; tên required/trim; unique theo công ty. Duplicate code
  hiển thị «Mã sản phẩm đã tồn tại.» hoặc «Mã SKU đã tồn tại.».
- Barcode trim, giữ casing, blank → NULL; unique theo công ty; lỗi field barcode
  «Mã vạch đã tồn tại.». Không có format/EAN rule mới nếu DB/business không yêu cầu.
- SKU phải có Product cùng công ty, sales_uom và net_quantity_uom; quantity Decimal
  hữu hạn, > 0, tối đa precision/scale thực tế. Zero không hợp lệ theo CHECK.
- Dropdown tạo mới lấy references active; category/Item/Product scoped công ty.
  Edit cho phép giữ references inactive đang dùng, không chọn inactive mới.
- Transactions lock bản ghi, đọc lại FK và trạng thái để xử lý dữ liệu stale.
  Lock order Product → Item → category → units phù hợp với Item updates; units
  lock theo PK ổn định. Database constraints là lớp cuối, exceptions được đổi
  thành thông báo Việt ngữ, không raw SQL/traceback.
- Whitelist không nhận organization/id/timestamps/attributes từ POST. Company
  được lấy từ helper duy nhất. Timestamps giữ created_at và cập nhật updated_at.
- Sku.attributes={} là JSON default hợp lệ trong DB; field ẩn được exclude khỏi
  blank=False full_clean giống Item.metadata, không sửa model hoặc JSON đã lưu.
- Không có actor audit fields trên hai model này. Không fake user UUID.

## Query và presentation

Product select_related category/costing_uom/output_item. SKU select_related
product/product__category/sales_uom/net_quantity_uom/sell_item. SKU scope đồng thời
theo company của SKU và Product, tránh lộ legacy FK khác công ty.
ORM search/filter/sort; whitelisted ordering, pagination COUNT/LIMIT ở database.
Dropdown labels chỉ đọc fields đã lấy, không query theo từng option.

UI hoàn toàn Việt ngữ, technical code và SKU/VAT giữ nguyên. Không phát hiện thêm
English user-facing labels còn sót ở phần UI được reuse. Ngày dd/mm/yyyy, datetime
dd/mm/yyyy HH:mm; số có separator Việt Nam và bỏ zero dư, giữ đủ precision.
Các field/input/errors dùng label/aria association; status có text; confirmation
có focus trap. Không thay đổi Foundation layout.

## Kiểm thử và chạy local

```powershell
.\env\Scripts\Activate.ps1
python manage.py check
npm run build:css
python manage.py runserver
# Terminal thứ hai: npm run dev:css

# Backend targeted
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.product.test_product_sku --verbosity=1

# Full regression + browser
$env:COSTING_BROWSER_TESTS = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
```

Targeted Product/SKU: 40 tests đạt. Cover CRUD/search/filter/sort/pagination,
duplicate code/barcode, inactive refs, company scope, missing fields, zero/negative/
nonfinite/precision quantity, JSON preservation, HTMX/history, CSRF, N+1, dropdown
query count, stale references và DB constraint races.
Vietnamese UI checks được mở rộng cho list/detail/create/edit của Product/SKU.
Browser cover form errors/toasts/confirmation focus, inactive Product behavior,
search/filter/sort/page/history, URL state, local assets và responsive 1440/1100/800/390.

Fixture tables/CHECK và production unique constraint names chỉ tạo/rename trong
`test_costing_slice` localhost riêng, có safety checks; không tác động Supabase.
Screenshot artifacts: `artifacts/screenshots/products-*.png`, `skus-*.png`.

Kết quả cuối:

- `python manage.py check`: không có lỗi.
- `npm run build:css`: thành công, Tailwind 4.3.3 giữ nguyên.
- Full suite: **161 tests đạt**, gồm 157 backend/presentation và 4 browser tests,
  không skip; chạy trong 39,181 giây.
- GET Product/SKU list/create trên database thật: 200; HTMX list: 200 partial,
  không full document; root 302 tới phần tử chi phí, không user session cookie.
- Đã kiểm tra ảnh Product/SKU desktop và SKU form mobile; không JS page errors,
  responsive/focus/query state được xác nhận bằng browser tests.
- Supabase chỉ được SELECT/read-only để kiểm tra schema và GET pages; create/edit
  được kiểm thử trên PostgreSQL riêng, không ghi bản ghi thật.

## Giới hạn và slice tiếp theo

- Không editor cho SKU attributes/biến thể, packaging assignment hoặc tự quy đổi
  sales/net/costing UoM; các quan hệ đó chưa có use case trong iteration này.
- Không delete, không cascade deactivate SKU khi Product inactive; dữ liệu cũ
  vẫn hiển thị và chỉnh sửa được qua policy giữ reference hiện có.
- Schema khác ví dụ khối lượng/đơn vị cơ sở trong prompt được phản ánh bằng đúng
  field đang có, không thêm field hoặc ép quantity UoM thành MASS.
- Khuyến nghị iteration kế tiếp: Supplier + Supplier Price; chưa triển khai.
