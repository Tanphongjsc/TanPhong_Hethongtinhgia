# Nhóm sản phẩm, danh mục vật tư / hàng hóa và Việt hóa UI

Ngày triển khai: 07/10/2026. Phạm vi chỉ gồm Product Category, Item Master và
presentation của các màn hình đã có; không triển khai Product, SKU, BOM hay nhà cung cấp.

## File và kiến trúc

Tạo mới:

- `apps/product/constants.py`, `validators.py`, `forms.py`, `selectors.py`,
  `services.py`, `urls.py`, `test_catalog.py`, `test_browser.py`.
- `templates/product/catalog_list.html`, `catalog_form.html`, `catalog_detail.html`,
  `partials/category_rows.html`, `partials/item_rows.html`, `partials/catalog_detail_content.html`.
- `apps/master_data/presentation.py`, `query_helpers.py`, `ui_helpers.py`,
  `test_vietnamese_ui.py`.

Sửa:

- `config/urls.py`; `static/src/tailwind.css`, generated `static/css/app.css`,
  `static/js/htmx-config.js`.
- `apps/product/views.py` thay nội dung scaffold bằng request orchestration thực tế.
- `apps/master_data/access.py`, `constants.py`, `context_processors.py`, `navigation.py`,
  `company_context.py` (nhãn lỗi cấu hình),
  `forms.py`, `selectors.py`, `services.py`, `validators.py`, `views.py`, `errors.py`,
  `templatetags/workspace_tags.py`, `testing.py` và các test hồi quy hiện có.
- Templates base, layouts/sidebar/topbar/app_shell; components status/version/filter;
  partial form errors; các partial bảng/form/detail/filter/actions của master data.
- `README.md`, `docs/00_AI_CONTEXT.md`, `03_SYSTEM_ARCHITECTURE.md`,
  `FRONTEND_IMPLEMENTATION_SPEC.md`, tài liệu này.

Xóa `apps/product/tests.py` là file test placeholder, thay bằng test thực tế.
Không cài thêm dependency. Không sửa `apps/core/models.py`, schema hoặc business migrations.

Luồng: request → view → form → service/selector → core models → PostgreSQL.
Company context/internal policy dùng chung; không user, membership, login hoặc
organization UI. Form không cho mass assignment organization/id/timestamps.

Search, ID filtering, whitelisted sort và pagination dùng helper ORM nhỏ tái sử dụng
từ selector cũ; không generic CRUD framework. UI dùng lại app shell, header, search,
filter, reference table, row actions, pagination, empty state, form fields, toast,
deactivation confirmation và HTMX conventions. Helper request/error/redirect dùng
chung để tránh lặp orchestration. `Item` dùng `select_related` cho category và cả
năm relation UoM; không query theo từng dòng.

## Routes và nghiệp vụ

- `/product/categories/`, `/create/`, `/<id>/`, `/<id>/edit/`;
  URL names `product:category_list/create/detail/edit`.
- `/product/items/`, `/create/`, `/<id>/`, `/<id>/edit/`;
  URL names `product:item_list/create/detail/edit`.

Nhóm sản phẩm: tìm mã/tên/mô tả, lọc trạng thái, sort mã/tên/ngày tạo;
form mã/tên/mô tả/trạng thái. Mã trim + uppercase, tên trim, mã unique trong công ty.
`parent` không expose và được giữ nguyên khi chỉnh sửa. Chưa triển khai hierarchy UI.

Item: tìm mã/tên, lọc nhóm/loại/đơn vị cơ sở/tồn kho/trạng thái;
sort mã/tên/loại/ngày tạo; pagination 25/50/100. Form chia thông tin chung, đơn vị
tính, thuế, trọng lượng, kích thước, quản lý. Không raw metadata JSON.

Schema được kiểm tra read-only trong Supabase:

- `uq_product_category` và `uq_item`: unique `(organization_id, code)`.
- `ck_item_type`: `RAW_MATERIAL`, `PACKAGING`, `SEMI_FINISHED`, `FINISHED_GOOD`,
  `SERVICE`, `BY_PRODUCT` (phụ phẩm). Không dùng enum `MATERIAL` giả định.
- `ck_item_weight` và `ck_item_dimension`: nullable hoặc >= 0.
- Các dimension codes hiện có gồm `MASS` và `LENGTH`.
- Không có thiếu field/table cần sửa schema cho iteration này.

Validate cả form và service: required mã/tên/base_uom; số không âm;
gross_weight >= net_weight khi cả hai có giá trị. Nhập khối lượng (kể cả 0) cần
UoM thuộc `MASS`, kích thước cần `LENGTH`. Không tự tính quy đổi. Nhóm sản phẩm
phải thuộc công ty; dropdown tạo mới dùng category/UoM active. Giá trị inactive
đang tham chiếu được giữ để chỉnh sửa bản ghi cũ; không cho chọn mới.
Services kiểm tra lại reference trong transaction, lock theo thứ tự ổn định,
scope theo công ty và chuyển IntegrityError thành thông báo tiếng Việt.
Metadata và parent không bị ghi đè. `Item.metadata={}` là default JSON hợp lệ trong
DB; service bỏ kiểm tra `blank=False` riêng field ẩn này khi full_clean, không
thay đổi model/schema. Không có field actor audit trong hai model này.

## Việt hóa và định dạng

Đã Việt hóa sidebar/topbar/breadcrumb/header, nhãn bảng/form/filter/button,
placeholder, status/empty/errors/toast, modal/drawer và detail của phần tử chi phí,
tiền tệ, nhóm đơn vị tính, đơn vị tính, quy đổi, nhóm sản phẩm và vật tư / hàng hóa.

Enum mapping thống nhất: loại giá trị, nguồn dữ liệu, phạm vi kế toán/chi phí,
phương pháp làm tròn, trạng thái workflow và item_type. Database values giữ nguyên;
choices, table và detail dùng cùng nhãn tiếng Việt. Boolean hiển thị Có/Không hoặc
trạng thái/ngữ nghĩa quản lý tồn kho.

Ngày hiển thị `dd/mm/yyyy`, datetime `dd/mm/yyyy HH:mm`; native date input giữ ISO
value theo HTML. Số hiển thị phân cách nghìn bằng dấu chấm, thập phân bằng dấu phẩy,
bỏ zero dư và không làm tròn mất precision. Number input giữ dấu chấm theo chuẩn
HTML và bỏ zero dư ở dữ liệu khởi tạo, giữ nguyên input khi validation lỗi.

SKU, BOM, API, VAT, FX, mã tiền tệ/đại lượng/đơn vị và business technical codes
giữ nguyên vì là ký hiệu ngành hoặc định danh. Nội dung dữ liệu do người dùng nhập
không tự dịch hoặc ghi lại database. Không thêm framework dịch thuật.

## Chạy và kiểm tra

```powershell
.\env\Scripts\Activate.ps1
python manage.py check
npm run build:css
python manage.py runserver
# Terminal khác: npm run dev:css

# PostgreSQL test riêng; không kết nối Supabase để tạo fixture.
$env:COSTING_BROWSER_TESTS = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
```

Test cover CRUD/search/filter/sort/pagination/empty/HTMX, company scope, mã trùng,
numeric/dimension/UoM validation, giữ metadata/parent, CSRF, không auth/membership,
N+1, Vietnamese labels/status/number/date. Browser tests cover các slice cũ và mới,
HTMX/history, validation/toast, focus trong confirmation, responsive 1440/1100/800/390.
Fixture CHECK constraints chỉ được tạo trong `test_costing_slice` trên localhost,
mirror constraint Supabase đã đọc; không phải migration business.

Kết quả: `python manage.py check` không có lỗi; `npm run build:css` thành công với
Tailwind 4.3.3; full suite **120 tests đạt**, gồm 117 backend/presentation và 3
browser tests, không skip. Lượt full cuối chạy trong 24,551 giây. Screenshots
desktop/mobile nằm ở `artifacts/screenshots/`; đã kiểm tra bố cục Item trực quan.
Sau lần chỉnh hai nhãn lỗi cấu hình cuối cùng, 19 test company-context targeted
được chạy lại và đều đạt.
Supabase chỉ được query read-only để kiểm tra schema và GET pages, không tạo
hoặc chỉnh sửa bản ghi thật.

## Giới hạn

- Database thật đã có một organization active khi kiểm tra cuối iteration; helper
  resolve tự động. Các request GET danh mục và form mới trả 200; `/` redirect 302
  tới phần tử chi phí, không cookie user session. Nếu dữ liệu công ty thay đổi,
  nguyên tắc cấu hình vẫn theo [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).
  Không insert/update dữ liệu hoặc sửa schema thật trong iteration này.
- Không delete, hierarchy editor, metadata editor, inline tạo UoM hoặc conversion
  tự động. Deactivate/activate qua form chỉnh sửa.
- Rule overlap của quy đổi giữ như iteration trước (không suy đoán constraint mới).
- Khuyến nghị slice tiếp theo: Product + SKU, dựa trên Item đã có; chưa triển khai.
