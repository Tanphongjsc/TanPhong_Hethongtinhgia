# Recipe / BOM — báo cáo implementation

Ngày: 07/10/2026. Phạm vi: định mức nguyên vật liệu, phiên bản, thành phần.
Không triển khai Packaging, Routing, Workflow, BOM expansion hoặc Costing.
Không thay đổi model/database business, không chạy migration trên Supabase.
Hệ thống tiếp tục single-company/no-auth; UI tiếng Việt, identifiers/mã giữ nguyên.

## Model và database thực tế

Đã inspect `apps/core/models.py` và metadata PostgreSQL thật bằng query chỉ đọc.
Tên bảng, kiểu/nullability/precision, CHECK/unique/FK và trigger liên quan khớp model.
Các model đều `managed = False`, schema `costing` theo search_path hiện có.

| Model | Trường thực tế sử dụng |
| --- | --- |
| Recipe | organization, product, code, name, description, is_active, created_at, updated_at |
| RecipeVersion | recipe, version_no, output_qty, output_uom, yield_rate, status, effective_from, effective_to, change_reason, content_hash, created_by, created_at, approved_by, approved_at |
| RecipeLine | recipe_version, component_item, qty, uom, scrap_rate, operation_code, substitute_group, is_optional, display_order, notes |

Recipe bắt buộc thuộc Product. Không có FK trực tiếp tới SKU hoặc Item đầu ra.
Item ở line là đầu vào, không tạo Item/Product/SKU ngầm trong BOM. Tìm/lọc SKU
trên list là tìm Recipe của Product chứa SKU đó, không tạo định mức riêng theo SKU.
UI dùng tên «Định mức nguyên vật liệu»; sidebar «BOM / Công thức sản xuất».

Unique thực tế:

- `uq_recipe`: (organization_id, code).
- `uq_recipe_version`: (recipe_id, version_no).
- RecipeLine không có unique theo Item, cho phép nhiều dòng cùng Item.

CHECK thực tế:

- `output_qty > 0`; `yield_rate > 0 AND yield_rate <= 1`.
- `qty > 0`; `scrap_rate >= 0 AND scrap_rate < 1`.
- Ngày kết thúc NULL hoặc ngày bắt đầu NULL hoặc ngày kết thúc > ngày bắt đầu.
- Ngoài DRAFT/IN_REVIEW, ngày bắt đầu phải có giá trị.
- Status: DRAFT, IN_REVIEW, APPROVED, EFFECTIVE, RETIRED.

Quantity/output là Decimal(24,8); tỷ lệ là Decimal(12,8). DB có index unique theo
version và index lines theo (recipe_version_id, display_order). FK version → Recipe
và line → version có ON DELETE CASCADE ở DB thật; không sử dụng cascade để xóa
header/version trong UI. Mapping `DO_NOTHING` hiện có được giữ nguyên.

## Chức năng và routes

| Màn hình | URL | URL name |
| --- | --- | --- |
| Danh sách | /bom/ | bom:bom_list |
| Thêm định mức + phiên bản đầu | /bom/create/ | bom:bom_create |
| Chi tiết, mặc định bản mới nhất | /bom/&lt;id&gt;/ | bom:bom_detail |
| Sửa thông tin định mức | /bom/&lt;id&gt;/edit/ | bom:bom_edit |
| Lịch sử phiên bản | /bom/&lt;id&gt;/versions/ | bom:bom_version_list |
| Tạo phiên bản | /bom/&lt;id&gt;/versions/create/ | bom:bom_version_create |
| Chi tiết phiên bản cụ thể | /bom/&lt;id&gt;/versions/&lt;version_id&gt;/ | bom:bom_version_detail |
| Sửa phiên bản | /bom/&lt;id&gt;/versions/&lt;version_id&gt;/edit/ | bom:bom_version_edit |
| Thêm thành phần | /bom/&lt;id&gt;/versions/&lt;version_id&gt;/lines/create/ | bom:bom_line_create |
| Sửa thành phần | /bom/&lt;id&gt;/versions/&lt;version_id&gt;/lines/&lt;line_id&gt;/edit/ | bom:bom_line_edit |
| Xác nhận/xóa thành phần | /bom/&lt;id&gt;/versions/&lt;version_id&gt;/lines/&lt;line_id&gt;/remove/ | bom:bom_line_remove |

List tìm mã/tên định mức, mã/tên Product, mã/tên SKU. SKU search dùng EXISTS để
không nhân dòng. Filters Product/SKU, trạng thái bản mới nhất, hiệu lực theo ngày,
is_active. Sort mã/tên/ngày tạo/ngày hiệu lực/số phiên bản, whitelist và stable PK.
Pagination 25/50/100 tại database. Search debounce 400ms, HTMX table-only và
hx-push-url giữ query string; refresh/history restore trả full page đúng convention.

Chi tiết gồm header, sản lượng, thu hồi, hiệu lực, lịch sử và bảng thành phần.
Lịch sử có sort/filter/status/date/pagination; không tải tất cả versions ở list.
Thành phần có Item/type/quantity/UoM/scrap/công đoạn/nhóm thay thế/tùy chọn/thứ tự/ghi chú.
Lines phân trang 25/50/100; không tự tăng quantity từ scrap/yield.
Header chỉ deactivation qua is_active, không hard delete.

## Phiên bản và transaction

Tạo Recipe và phiên bản đầu tiên là một transaction; lỗi version rollback cả Recipe.
Số phiên bản được cấp bởi service, không expose để user tự sửa. Khóa parent Recipe
trước MAX(version_no)+1 để serialize các yêu cầu tạo phiên bản đồng thời.

Tạo mới không nguồn cho phép nhập cấu hình và có 0 thành phần. Thêm `?source=<id>`
hoặc chọn «Tạo phiên bản mới từ phiên bản …» clone cấu hình và **toàn bộ** lines
trong một transaction, không chỉ trang lines đang xem. Form cho đổi sản lượng/
hiệu lực/lý do trước khi lưu. Nguồn được kiểm tra cùng Recipe/công ty; version mới
luôn DRAFT, actor/approved_at/hash NULL; không sửa nguồn. Cấu hình/thành phần có
tham chiếu đã inactive vẫn được giữ để sao chép lịch sử; không cho chọn thêm một
tham chiếu inactive khác. Conversion được kiểm tra lại theo ngày phiên bản mới.

Database trigger `prevent_approved_version_mutation` và `protect_recipe_line`
khóa APPROVED/EFFECTIVE/RETIRED. Service cũng kiểm tra trạng thái vừa đọc dưới lock;
GET form bản khóa không có submit hoạt động, POST cố tình gửi vẫn bị từ chối.
DRAFT/IN_REVIEW sửa được; update giữ nguyên status. Không có approval/publish/
transition action trong iteration này. Content hash của bản còn sửa được được xóa
khi thay đổi cấu hình/thành phần; chưa có cơ chế tính/chốt hash.

Header mã/tên/mô tả/is_active còn sửa được. Product bị giữ cố định nếu có version
đã chốt để tránh đổi ý nghĩa đầu ra lịch sử. Không xóa Recipe/RecipeVersion.
Xóa line chỉ ở bản còn sửa được, GET mở xác nhận, POST có CSRF mới thực hiện.
Recipe → Version → Line là thứ tự khóa chung; lưu line reload FK trước khi validate
để không nhận master data stale. Lỗi unique/FK/CHECK/trigger chuyển thành lỗi tiếng
Việt, không expose SQL/traceback. Các lỗi ngoài dự kiến đi qua trace_id middleware.

**Phiên bản mới nhất** ở list/detail mặc định là version_no lớn nhất, không phải
«phiên bản đang áp dụng» cho một Costing Run. Trang version cụ thể giữ URL/id riêng.
Hiệu lực theo ngày là display annotation tách khỏi status duyệt: Chưa đặt hiệu lực,
Sắp hiệu lực, Đang hiệu lực, Hết hiệu lực; ngày kết thúc tính bao gồm ngày đó.

## Validation và UoM

- Code/name bắt buộc; trim, code uppercase, unique trong công ty (precheck case-insensitive).
- Product/Item scoped theo get_default_organization; không expose organization/user.
- Dropdown mới chỉ active, giữ FK đang gắn nếu inactive để xem/sửa lịch sử.
- Sản lượng/quantity > 0; thu hồi trong (0,100%], hao hụt trong [0,100%).
- UI nhập % bằng Decimal, lưu tỷ lệ /100 chính xác; không dùng float. Nhập tối đa
  6 số lẻ ở % tương ứng 8 số lẻ của tỷ lệ DB. Số hiển thị bỏ zero dư, không mất precision.
- Ngày kết thúc phải sau ngày bắt đầu theo CHECK DB (bằng ngày cũng bị từ chối).
  Form yêu cầu ngày bắt đầu nếu đã nhập ngày kết thúc. Cả hai trống được lưu Draft.
- Thứ tự dùng range integer DB, không tự thêm rule cấm thứ tự âm/trùng.
- Không cấm Item trùng, không hard-code Item type chỉ nguyên liệu; không tạo UoM/conversion mới.

Nếu UoM bằng Item.base_uom, không cần lookup. Nếu khác, kiểm tra conversion trực
tiếp trong UomConversion tại effective_from của version, hoặc ngày hiện tại khi
chưa đặt ngày. Chấp nhận cả chiều thuận/ngược; organization NULL hoặc default;
item-specific hoặc general cùng category. General khác category không được coi
là phù hợp; item-specific khác category theo business design hiện có được phép.
Một query conversion cho các cặp cần kiểm tra, không query lại từng line khi clone.
Kiểm tra lại khi lưu line, clone và khi đổi ngày bắt đầu phiên bản.

## Reuse, HTMX và query performance

Reuse company context/InternalAccess, ReferenceDataForm, các choice/number widgets,
query_helpers, ui_helpers, presentation mappings, app shell/breadcrumb/page header,
search/filter/table/pagination/empty state/error/toast/loading/status và field layout.
Không dựng generic CRUD framework hoặc kiến trúc auth mới. Form sections được tách
thành include chung cho Recipe/header/version/line và các form danh mục cũ.

HTMX line editor là inline section, tự focus field đầu, có Hủy. Invalid POST giữ
input/field error/aria-describedby. POST thành công retarget bảng lines, clear editor
và append toast bằng OOB. Pagination links của kết quả POST trỏ về GET version detail,
không trỏ tới action POST. Full GET/POST line form hoạt động khi truy cập trực tiếp.
CSRF vẫn bật; phiên bản khóa ẩn thao tác và có giải thích bằng chữ.

Menu Sản xuất tự mở/active trên cả header, version, line routes. Module cũ giữ active
đúng resource, không dùng prefix đơn giản gây nhầm UoM/UoM Category.
Không thêm English display label; mã kỹ thuật, SKU/BOM, enum identifier vẫn giữ gốc.
Ngày dd/mm/yyyy, timestamp dd/mm/yyyy HH:mm, numeric căn phải; label liên kết input,
th/scope/aria, focus visible. Table cuộn ngang cục bộ trên mobile, không làm tràn page.

Selectors dùng select_related Product; versions/output_uom; lines/component_item/uom.
List lấy scalar metadata bản mới nhất bằng Subquery theo index version; không tải
lines. Test fixture lớn kiểm tra list/detail không quá 7 queries và chỉ render 25
lines mặc định; truy cập Item/UoM của line queryset là 1 query. Không raw SQL runtime.

## Files created

- apps/bom/constants.py, forms.py, selectors.py, services.py, validators.py, urls.py.
- apps/bom/testing.py, test_concurrency.py, test_browser.py.
- templates/bom/detail.html, line_form.html, version_list.html.
- templates/bom/partials/detail_content.html, line_editor.html, line_saved.html,
  lines_table.html, recipe_rows.html, version_rows.html.
- templates/components/form_sections.html.
- docs/RECIPE_BOM.md.

## Files modified

- apps/bom/views.py, tests.py (thay các stub bằng slice thực tế).
- config/urls.py (mount /bom/).
- apps/master_data/access.py, navigation.py, context_processors.py.
- apps/master_data/forms.py (aria-describedby dùng auto_id gồm prefix).
- apps/master_data/presentation.py, templatetags/workspace_tags.py (% và base URL pagination).
- apps/master_data/testing.py (fixture unmanaged + CHECK/unique/trigger local).
- templates/layouts/sidebar.html, components/button.html,
  master_data/partials/reference_data_form_content.html.
- static/src/tailwind.css; static/css/app.css (generated, không chỉnh tay).
- docs/00_AI_CONTEXT.md, 03_SYSTEM_ARCHITECTURE.md, FRONTEND_IMPLEMENTATION_SPEC.md, README.md.

Không cài dependency mới. Không sửa apps/core/models.py hoặc thêm business migration.

## Kiểm thử và kết quả

Test suite dùng PostgreSQL 17 localhost, không dùng Supabase. Fixture unmanaged thêm
3 model và CHECK/unique/trigger theo metadata đã inspect; trigger SQL chỉ được chạy
khi host=127.0.0.1 và database=test_costing_slice. Fixture FK vẫn được tạo từ model
DO_NOTHING, không chứng minh ON DELETE CASCADE của DB thật (UI không có xóa version).

- Targeted slice: 43 tests, gồm 41 form/view/service/query tests, 1 concurrent version
  TransactionTestCase và 1 Playwright browser flow. Tất cả đạt.
- Full regression bật browser: 238 tests, gồm 6 browser flows. Tất cả đạt.
- Test CRUD/search/filter/sort/25–50–100 pagination, duplicate code/race error,
  atomic rollback, version clone không đổi nguồn, scope cùng công ty/parent,
  nullable actors, unknown status bị DB chặn, 3 trạng thái bất biến và trigger bảo vệ.
- Lines thiếu Item/UoM, quantity 0/âm, tỷ lệ/precision, inactive dropdown/history,
  duplicate Item, direct conversion 2 chiều/item-specific/shared/effective date,
  stale reference và đổi ngày bắt đầu cần revalidate.
- Browser: tạo ban đầu/lỗi input; HTMX add/edit/confirm-remove; clone/history/nguồn
  không đổi; search/filter/sort/pagination/query URL; standalone POST fallback;
  responsive 1440/1100/800/390px; active menu, không JS error/session auth.
- Read-only Supabase smoke: / → 302 Cost Element; /bom/, /bom/create/, HTMX /bom/,
  Cost Element, Supplier Price, Product và Item → 200; không session cookie.
  Default company hiện có 0 Recipe; không thử ghi dữ liệu vào DB thật.
- python manage.py check: đạt. npm run build:css: đạt (Tailwind 4.3.3).

Log: artifacts/bom-full-tests.log. Screenshot: artifacts/screenshots/bom-detail-desktop.png,
bom-list-desktop.png, bom-line-mobile.png (gitignored, dữ liệu test local).

## Known limitations / issues cần quyết định ở iteration sau

1. Schema không có BOM riêng theo SKU hoặc Item đầu ra. Không bổ sung FK bằng suy đoán.
2. Chưa có overlap constraint/policy, effective-version resolver hoặc usage resolver
   cho Costing. Cho phép ngày trùng giữa các phiên bản theo DB hiện có.
3. Không approval/publish/status transition UI; dữ liệu mới luôn Nháp. Bản đã chốt
   từ dữ liệu hiện có vẫn xem/clone được. Không giả trạng thái Effective bằng ngày.
4. Conversion chỉ xác nhận **tồn tại cặp trực tiếp** tại một ngày; chưa chọn factor/
   priority nếu nhiều conversion, resolve chuỗi hoặc bảo đảm coverage cả khoảng thời gian.
   Chưa có cycle/dependency engine cho BOM lồng nhau; không thực hiện recursion/roll-up.
5. Không tính lượng thực tế từ yield/scrap, không chọn Supplier Price hoặc preview cost.
   Công đoạn/nhóm thay thế chỉ là code đã có, không triển khai Routing/substitution engine.
6. Phát hiện ở DB thật: protect_recipe_line kiểm tra NEW.recipe_version_id khi UPDATE,
   nên SQL ngoài ứng dụng có thể chuyển line từ bản khóa sang Draft mà không kiểm tra
   OLD parent. Service không expose parent field và luôn khóa/kiểm tra version nguồn,
   nên flow UI hiện tại chặn đường này. Đã giữ nguyên schema/trigger; hardening trigger
   cần task database riêng được cho phép. Trigger version giữ các bản chốt bất biến.
7. Content hash chưa được tính/chốt; integration bên ngoài phải tuân thủ status/locks.
   Các thay đổi ghi chỉ được kiểm thử trên DB local, live smoke là read-only.

Đề xuất slice kế tiếp: Packaging Configuration theo schema hiện có; đây chỉ là đề
xuất, chưa triển khai. Các resolver/chọn version/UoM expansion cần đặc tả riêng
trước khi xây Costing.

## Chạy và kiểm tra

```powershell
.\env\Scripts\Activate.ps1
python manage.py check
npm run build:css
python manage.py runserver
```

Mở http://127.0.0.1:8000/bom/ trực tiếp, không đăng nhập. Terminal thứ hai:
`npm run dev:css`. Dữ liệu Product, Item, UoM và conversion phù hợp cần có sẵn.
Company context/config giữ nguyên APP_MODE=single_company và DEFAULT_ORGANIZATION_ID
khi có nhiều organization active; không hard-code ID hoặc thêm selector UI.

```powershell
# Targeted, PostgreSQL riêng do script start/stop
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.bom
# Full suite có browser (Chromium đã cài theo README)
$env:COSTING_BROWSER_TESTS = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```
