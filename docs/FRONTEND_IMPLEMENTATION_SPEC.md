# FRONTEND_IMPLEMENTATION_SPEC.md
## Hệ thống tính giá thành & giá bán linh hoạt

**Hardening 08/10/2026:** sidebar chỉ hiển thị destination đã triển khai, mỗi module
một liên kết; bỏ placeholders History/Overrides/Import/Settings và các section rỗng.
Lịch sử phiên bản và đầu vào điều chỉnh vẫn nằm trong module nghiệp vụ. Quy định
giữ placeholder global trong spec cũ đã superseded. CSRF từ chối bằng thông báo
tiếng Việt có trace; history restore trả trang đầy đủ cả khi lỗi. Native POST form
chặn gửi lặp; các form HTMX dùng cơ chế disable submit sẵn có.

**08/10/2026 — superseding runtime/UI:** không Approval Workflow/Maker-Checker,
Approval Inbox/My Requests hoặc business Audit Log; bỏ section Workflow, giữ
Version History và business input overrides. Không account/Auth/role/company UI.
Giữ nguyên mọi version/history/effective dates, activate Formula/Scheme, Costing
snapshot/source/explain/trace_id và technical logs. Các phần Approval/Audit cũ bên
dưới là thiết kế lịch sử đã superseded; không dùng để đưa chúng trở lại.

Pricing Foundation dùng `apps/pricing`, bốn menu GIÁ BÁN liên kết tới `/pricing/channels/`,
`/pricing/channel-fee-rules/`, `/pricing/tax-rules/`, `/pricing/fx-rates/`.
Reuse Foundation list/form/detail/filters/pagination/status/toast, 400ms HTMX search,
25/50/100 và URL query state; không redesign. Nhãn tiếng Việt, mã nghiệp vụ giữ nguyên.
UI nhập tỷ lệ %, DB Decimal phần số; FX chiều “1 nguồn = tỷ giá đích”, đủ precision.
Scope và fields theo actual models, không giả code/name rule, Tax FK hoặc fee UoM.
Nháp sửa được, trực tiếp đưa vào hiệu lực sau validation; definition đã chốt chỉ đọc,
đóng kỳ tương lai qua action riêng. Hiệu lực Pricing [start,end), FX datetime aware.
API FX ngoài không có. Phạm vi Foundation cũ không tính giá; execution Scenario hiện
được mô tả dưới đây và supersedes các câu “Scenario chưa triển khai” trong spec cũ.
Chi tiết/giới hạn/tests: [PRICING_FOUNDATION.md](PRICING_FOUNDATION.md).

**Pricing Scenario 08/10/2026:** `/pricing/scenarios/`, list/filter/date/sort/pagination
Foundation 25/50/100, HTMX 400ms/query URL/history; create/edit Nháp và detail. Product →
SKU → nguồn Costing đã khóa; Channel gợi ý currency/khu vực khi chưa chọn. Form tách
margin %, markup %, lợi nhuận đơn vị; tax mode rõ ràng, FX type nhập khi cần.
Calculate POST + CSRF, indicator, disable submit, refresh cấu thành giá tại chỗ.
Detail hiển thị giá khách trả/giá niêm yết/doanh thu trước phí chưa thuế/doanh thu thuần/
lợi nhuận/target và actual margin/markup; waterfall từ persisted result components,
sources/fee bounds/tax basis/FX/hash/trace trong disclosure, không raw JSON.
Đã tính chỉ đọc; nhân bản cần mã mới. Lỗi tính giữ Nháp và lỗi tiếng Việt/mã tham chiếu;
không có FAILED giả hoặc duyệt. So sánh kịch bản được triển khai riêng như dưới đây.
Currency/UoM/date/number display Việt; price tính cho một đơn vị sản lượng Costing.
Shared history restore đồng bộ visible filters từ URL. [PRICING_SCENARIO.md](PRICING_SCENARIO.md).

**Scenario Comparison 08/10/2026:** `/pricing/scenarios/compare/`, sidebar GIÁ BÁN active
riêng. Product → SKU → danh sách đã tính, chọn 2–5; search 400ms/filter/sort/pagination
server-side + HTMX/push URL. GET repeated `scenario` + `baseline`, không session/model.
Bảng cột kịch bản/hàng chỉ tiêu, phần cấu thành phí/thuế/FX disclosure và link nguồn.
Cùng SKU/Product và output basis; hash snapshot hợp lệ. Khác currency hiện rõ, không
trừ tiền hoặc quy đổi current FX. Delta Decimal, tỷ lệ dùng điểm %, mốc 0 hiện —.
Không engine calls/writes/approval/charts/export. [SCENARIO_COMPARISON.md](SCENARIO_COMPARISON.md).

**Lần tính giá thành 07/10/2026:** `/costing/runs/`, list/search/filter ngày/sort/
pagination 25/50/100, tạo Run HTMX, Product → SKU và chọn phương án có version hiệu
lực theo ngày nhập. Schema không gán phương án vào Product/SKU nên chọn thủ công.
Phương án dùng packaging yêu cầu sản lượng/đơn vị cơ sở đóng gói do người chạy nhập.
Detail đọc summary, breakdown, nguồn và trace đã lưu; drawer chỉ diễn giải persisted
data, snapshot render bảng và công thức, không raw JSON. Rerun tạo record mới,
không sửa lịch sử. Trạng thái thực tế LOCKED/FAILED, trace_id để tra log. Decimal,
no-auth/single-company, không schema change/queue/Pricing. Xem [COSTING_RUN.md](COSTING_RUN.md).

**Phương án tính giá thành 07/10/2026:** `/costing/schemes/`, CRUD/header + initial
Draft, history/clone, components drawer HTMX, source/FormulaVersion dropdown,
config validation panel/dependency table và confirmed activation. Reuse Foundation,
UI Vietnamese, English identifiers/codes, no-auth/single-company compatibility.
Shared HTMX dùng defaultSettleDelay=0 để khởi tạo controls mới ngay trong swap;
không có transition cần settle delay ở các bảng/drawer.
List ghi phiên bản mới nhất; effective status riêng. Schema không có Product/SKU/
manufacturing assignments/base currency/base quantity/required flag hoặc selection
policy; không expose fake controls/raw JSON. Currency/UoM từ CostElement/Formula.
Clone giữ exact mappings và conditions; locked versions chỉ tạo bản mới. Nguồn
SYSTEM đã có registry typed từ Costing Run; mã không đăng ký và LOOKUP/EXTERNAL
chặn activation. App cấu hình không thực thi công thức/tính giá/rate lookup. Chi tiết:
[COSTING_SCHEME.md](COSTING_SCHEME.md).

**Formula Engine 07/10/2026:** đã triển khai `/formula-engine/formulas/`, Studio
3 vùng với textarea/token palette, HTMX validation/sample test, dependency/type/unit
và Decimal trace. Reuse Foundation; không Monaco/SPA/new dependency. Lịch sử/clone
phiên bản, test persistence/ngừng dùng và kích hoạt có confirmation + validation/test
gate. Mã lưu English, UI Vietnamese, no-auth/single-company compatibility hiện có.
List ghi «Phiên bản mới nhất», khác resolver hiệu lực; không gán giá/rate hoặc
Costing vào Formula. Chi tiết DSL/schema/limits: [FORMULA_ENGINE.md](FORMULA_ENGINE.md).

**Nhóm chi phí chung / Quy tắc phân bổ 07/10/2026:** dùng `/bom/cost-pools/` và
`/bom/allocation-rules/`, app/namespace BOM theo boundary sản xuất hiện có.
Reuse UI danh mục, bộ lọc/tìm kiếm 400ms, bảng/sort/pagination 25/50/100, form,
validation, status, toast và confirmation ngừng hoạt động. Pool list gồm code/name/
pool_type/số quy tắc/is_active; detail có các quy tắc liên quan với bộ lọc/phân trang.
Rule form gồm pool/code/name/basis_type/basis_uom/formula_code/priority/effective dates.
Choices chỉ dùng pool_type/basis_type/status thực tế trong CHECK, nhãn tiếng Việt
tại mapping dùng chung. Không đổi stored code. Nhãn aria breadcrumb đã Việt hóa.

Schema không có member relation tới CostElement, target FK, rule lines hoặc version.
Không thêm controls giả hoặc raw condition_jsonb; dữ liệu điều kiện hiện có được
giữ nguyên khi edit. formula_code là text tùy chọn, không thực thi hoặc resolve FK.
Pool/unit active khi chọn mới, giữ reference inactive hiện có khi edit/history.
New rule Nháp/NULL actor, edit giữ status; không invent immutable rule hoặc overlap.
Form nhắc thêm mã quy tắc mới khi thay đổi kỳ để giữ lịch sử; edit cập nhật row cũ.
Effective status theo ngày hiển thị riêng trạng thái bản ghi. Date end > start
theo DB; priority signed integer theo schema, không giả mức âm bị DB cấm.
HTMX partial/full/history restore và query state giữ pattern cũ; không SPA,
cost preview, allocation run hoặc Organization/Auth. Chi tiết schema/giới hạn/tests:
[COST_POOL_ALLOCATION_RULE.md](COST_POOL_ALLOCATION_RULE.md).

**Quy trình sản xuất 07/10/2026:** đã triển khai `/bom/routings/`, reuse app/namespace
`bom`, page header, form, bảng danh mục, tìm kiếm, bộ lọc, phân trang và drawer hiện có.
Header thực tế: product/code/name/is_active; không giả SKU/description. Version:
batch_size/batch_uom/effective_from/effective_to/change_reason; bản mới và clone Nháp.
Công đoạn gồm sequence_no/operation_code/operation_name/work_center/primary_resource,
setup_time/run_time/time_uom/quantity_basis/quantity_uom/notes. Trung tâm và nguồn lực
chính không bắt buộc theo schema. Không có OperationResource/multi-resource assignment.

List/search/filter/sort/pagination HTMX/server-side; SKU filter tìm quy trình của
Product tương ứng, nhãn ghi rõ «SKU của sản phẩm». Hiển thị «Phiên bản mới nhất»,
không giả hiệu lực Costing. Hiệu lực theo ngày tách trạng thái duyệt.
Detail có cấu hình phiên bản và bảng công đoạn ordered theo sequence, phân trang 25/50/100.
Add/edit/confirmed-remove qua reusable drawer; lỗi giữ input/aria, success cập nhật
bảng/toast và đóng editor OOB. Dropdown nguồn lực cập nhật HTMX khi đổi WorkCenter,
chỉ lấy nguồn lực cùng trung tâm hoặc dùng chung, backend kiểm tra lại trước ghi.
Có full GET/POST fallback, focus trap/Escape/focus restore, CSRF, không user session.
Time Decimal >= 0 theo DB; số khác 0 cần đơn vị TIME, không hard-code giờ/quy đổi.
Batch/quantity_basis > 0 nếu nhập; ngày kết thúc > ngày bắt đầu theo CHECK thực tế.
APPROVED/EFFECTIVE/RETIRED chỉ đọc, tạo version mới để sửa; clone nguyên công đoạn
atomic sang Nháp. Không UI approval, chi phí tạm thời, ResourceRate snapshot hoặc
policy overlap chưa tồn tại. Xem [ROUTING.md](ROUTING.md).

**Trung tâm / Nguồn lực / Đơn giá 07/10/2026:** dùng namespace `bom:` và routes
`/bom/work-centers/`, `/bom/resources/`, `/bom/resource-rates/`, reuse UI danh mục.
WorkCenter có site_code/capacity_value/normal_capacity_value/capacity_uom, không có
description. Resource có WorkCenter optional, resource_type đúng CHECK
MACHINE/LABOR/WORK_CENTER/SERVICE; capacity_value/capacity_uom, không expose metadata.
ResourceRate dùng resource/rate_type/amount/currency_code/per_uom/effective dates/
source_reference. rate_type là mã text tự do, không invent enum. Amount >= 0 theo DB,
end phải > start; không giả rate_uom/hour hoặc version table. New row Nháp/NULL actor;
edit giữ status gốc, UI nhắc thêm row mới khi đổi kỳ. Hiệu lực theo ngày hiển thị
riêng trạng thái bản ghi. Resource Detail có lịch sử phân trang/HTMX; WorkCenter
có tối đa 10 resources + link danh sách đầy đủ. Search/filter/sort/pagination ở DB,
query state giữ URL và history restore trả full page. No auth, org UI/workflow,
Costing hoặc overlap/immutability policy chưa có. Chi tiết schema/validation/tests:
[WORK_CENTER_RESOURCE_RATE.md](WORK_CENTER_RESOURCE_RATE.md).

**Packaging 07/10/2026:** đã triển khai `/bom/packaging/` trong namespace `bom:`
và app `apps/bom/`, reuse Foundation/Recipe helpers. Schema thực tế gồm
`PackagingConfig → Product`, `PackagingConfigVersion → PackagingConfig`,
`PackagingLine → PackagingConfigVersion + Item + Uom` và `SkuPackagingAssignment`
để gán SKU cùng Product theo ngày hiệu lực. Không giả field SKU trực tiếp trên Config.

Config có code/name/description/is_active. Version có ngày hiệu lực, gross_weight/
weight_uom, length/width/height/dimension_uom/change_reason; **không có sản lượng
chuẩn/đơn vị đầu ra**. Line có qty Decimal(24,8), level_code, parent_level_code,
units_per_parent, market_code/artwork_code/display_order/notes; không có scrap.
Cấp DB: PRIMARY/SECONDARY/TERTIARY/PALLET/CONTAINER; nhãn tiếng Việt dùng mapping
chung. Parent là mã text, không FK; dropdown gợi ý cấp đã biết, giữ mã tùy chỉnh cũ.
Không xây cây/auto-multiply số lượng hoặc tự giả định cấu hình cho 1 SKU.

List/search/filter/sort/pagination server-side/HTMX; chi tiết có SKU liên kết và
version/lines, lịch sử phân trang, clone toàn bộ lines atomic sang Nháp. Trạng thái
APPROVED/EFFECTIVE/RETIRED bất biến theo DB trigger; không có approval/status action.
Phiên bản mới nhất hiển thị riêng, không coi là effective resolver. Lines add/edit/
confirmed-remove dùng reusable drawer có focus trap/Escape/restore focus; invalid
POST giữ input, success OOB đóng editor + refresh table + toast. Có full GET/POST fallback.
Quantity/units_per_parent > 0 (units optional), hỗ trợ số lẻ 8 chữ số; ngày kết thúc
phải > ngày bắt đầu theo CHECK thật. UoM compatibility reuse Recipe validation trực
tiếp hai chiều theo ngày đầu version/hôm nay. Không giá mua/cost preview hoặc overlap
policy chưa được định nghĩa. Xem [PACKAGING_CONFIGURATION.md](PACKAGING_CONFIGURATION.md).

**Recipe / BOM 07/10/2026:** đã triển khai `/bom/`, phiên bản và thành phần tại
`apps/bom/`. Schema thực tế dùng `Recipe → Product`, `RecipeVersion → Recipe`,
`RecipeLine → RecipeVersion + Item + Uom`, không có SKU/output Item FK ở Recipe.
Header gồm mã/tên/mô tả/sản phẩm/is_active; phiên bản chứa `output_qty`, `output_uom`,
`yield_rate`, ngày hiệu lực và lý do thay đổi. Thành phần dùng `qty`, `scrap_rate`,
mã công đoạn, nhóm thay thế, tùy chọn, thứ tự và ghi chú. UI nhập/hiển thị tỷ lệ theo
%, database giữ tỷ lệ Decimal [0,1]. Số lượng > 0; yield trong (0,1], scrap trong
[0,1); ngày kết thúc phải > ngày bắt đầu theo CHECK thực tế. Không cấm Item trùng.

Tạo định mức kèm phiên bản đầu tiên và clone phiên bản/thành phần đều atomic.
Phiên bản mới ở Nháp; `APPROVED`, `EFFECTIVE`, `RETIRED` khóa cấu hình/thành phần
theo trigger hiện có; không thêm approval/status transition UI. List/detail mặc
định hiển thị **phiên bản mới nhất**, không tuyên bố đó là bản hiệu lực cho Costing.
Tìm/lọc SKU chỉ tìm định mức của Product tương ứng. Hiệu lực theo ngày hiển thị
riêng trạng thái bản ghi, gồm «Chưa đặt hiệu lực»; không thay đổi enum DB.

Thành phần thêm/sửa/xóa có xác nhận qua inline HTMX, lỗi giữ input, bảng/toast
cập nhật tại chỗ; có fallback GET/POST đầy đủ. Reuse search/filter/pagination
và app shell; menu Sản xuất tự mở, active cả ở trang phiên bản/thành phần.
UoM khác Item.base_uom cần cặp quy đổi trực tiếp hợp lệ ở ngày bắt đầu phiên bản
hoặc hôm nay; chấp nhận chiều thuận/ngược, shared/company và item-specific theo
thiết kế UoM hiện có. Không chọn giá/hệ số, tính hao hụt/sản lượng thực tế, tạo chuỗi
quy đổi, BOM expansion/cycle engine hoặc Costing. Chi tiết giới hạn và phát hiện
trigger DB: [RECIPE_BOM.md](RECIPE_BOM.md). Nội dung lịch sử dưới đây chỉ áp dụng
khi phù hợp model/constraint và phạm vi hiện tại; không đưa auth/workflow trở lại.

**Supplier/Supplier Price 07/10/2026:** đã có `/master-data/suppliers/` và
`/master-data/supplier-prices/`, dùng shared reference views/forms/templates.
Supplier có `default_currency_code` và `payment_terms`, không có address/country/contact.
SupplierPrice dùng `price_uom`, `currency_code`, `min_qty`, `unit_price`, các tỷ lệ
thuế và ngày hiệu lực; không có maximum quantity/lead time hoặc is_active.
Đơn giá và min_qty >= 0; tỷ lệ thuế/khấu trừ trong [0,1]; effective_to phải >
effective_from theo CHECK hiện tại. Ngày kết thúc bao gồm ngày đó trong bộ lọc UI.
Giá mới giữ trạng thái Nháp; edit giữ trạng thái gốc, không triển khai approval.
Hiệu lực theo ngày là display annotation, không thay đổi status DB hoặc chọn giá
cho Costing. Chưa áp dụng guardrail edit effective version/usage lock trong phần
lịch sử của spec cho SupplierPrice; giới hạn này được ghi rõ, UI nhắc thêm giá
mới khi đổi kỳ. Xem [SUPPLIER_PRICE.md](SUPPLIER_PRICE.md).

**Product/SKU 07/10/2026:** `/product/products/`, `/product/skus/` dùng chung
catalog views/templates và HTMX conventions với nhóm sản phẩm/Item. Schema thực tế:
Product có `costing_uom`, không có `base_uom`; SKU có `sales_uom`, `net_quantity`,
`net_quantity_uom`, không có weight/description/variant fields riêng. UI gọi
«Đơn vị tính giá thành», «Đơn vị bán», «Lượng tịnh», «Đơn vị lượng tịnh»; không giả
định tất cả SKU đo bằng khối lượng. Lượng tịnh > 0 theo DB; barcode trim/NULL khi
trống và unique trong công ty. Không expose `attributes` JSON, không quản lý
packaging assignments trong iteration này. Chi tiết: [PRODUCT_SKU.md](PRODUCT_SKU.md).

**Iteration hiện tại 07/10/2026:** UI đã Việt hóa toàn bộ các màn hình triển khai.
Chỉ dịch display labels; không đổi identifier, URL name, enum hoặc business code.
Mapping hiển thị tại `apps/master_data/presentation.py`; navigation keys giữ nguyên
và có nhãn tiếng Việt riêng. Các ví dụ UI tiếng Anh ở phần lịch sử bên dưới đã
superseded về presentation. Product Category và Item Master dùng app `product`,
company context/internal access có sẵn và các component/HTMX conventions hiện tại.
Phạm vi và validation: [PRODUCT_CATEGORY_ITEM_VI.md](PRODUCT_CATEGORY_ITEM_VI.md).

**Cập nhật kiến trúc 07/10/2026:** triển khai hiện tại là single-company, no authentication.
Không login/logout, user session/menu/roles, Supabase Auth hoặc organization selector.
Organization/model/FK vẫn giữ trong DB; company context tập trung tại
`get_default_organization()` với `DEFAULT_ORGANIZATION_ID` khi cần. Membership không
tham gia runtime. Policy nội bộ tập trung cấp quyền cho các thao tác đã triển khai;
audit actor nullable để NULL. Các yêu cầu auth/multi-tenant trong phần lịch sử bên
dưới đã superseded. Xem [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).

**Mục đích:** tài liệu này dùng trực tiếp cho Codex/Coding Agent để triển khai frontend trong VS Code.

**Stack frontend đã chốt:**

```text
Django Templates
+ HTMX
+ Alpine.js
+ Tailwind CSS
```

Tài liệu này thay thế phiên bản trước sử dụng Bootstrap/Tabler.

---

# 1. Bối cảnh và ràng buộc

Stack tổng thể:

- Backend: Django
- Database: Supabase PostgreSQL
- Business schema: `costing`
- Database được tạo trước bằng SQL
- Models tập trung tại `apps/core/models.py`
- Các business model dùng `managed = False`
- Frontend: Django Templates + HTMX + Alpine.js + Tailwind CSS

Các app hiện tại:

```text
apps/
├── audit/
├── bom/
├── core/
├── costing/
├── formula_engine/
├── master_data/
├── pricing/
├── product/
└── workflow/
```

Quy tắc kiến trúc:

- `apps/core/models.py` là persistence/model layer dùng chung.
- Không tạo lại các bảng business bằng Django migration.
- Không chuyển model sang các app nghiệp vụ.
- Các app nghiệp vụ import model từ `apps.core.models`.
- Không sửa schema PostgreSQL trong task frontend nếu không có yêu cầu riêng.
- Không chạy `makemigrations`/`migrate` để tạo lại các bảng `costing`.
- Business logic không được đặt trong template hoặc JavaScript.

---

# 2. Frontend Architecture

Sử dụng server-rendered Django.

```text
Browser
   ↓
Django View
   ↓
Form / Selector / Service
   ↓
apps.core.models
   ↓
Supabase PostgreSQL
```

Partial update:

```text
Browser
   ↓
HTMX request
   ↓
Django View
   ↓
Partial Template
   ↓
HTMX swap
```

Alpine.js chỉ quản lý UI state nhỏ:

- sidebar collapse;
- dropdown;
- tabs;
- modal;
- drawer;
- disclosure;
- toggle;
- temporary local state.

Không đưa vào Alpine.js:

- cost calculation;
- formula evaluation;
- rule resolution;
- approval policy;
- pricing calculation;
- database business validation.

Tailwind CSS chịu trách nhiệm styling. Không dùng Bootstrap, Tabler UI hoặc một component framework khác trong iteration này.

---

# 3. Mục tiêu UI/UX

Ứng dụng là phần mềm nghiệp vụ enterprise, data-heavy.

Phong cách:

```text
Enterprise
Data-dense
Precise
Low visual noise
Explainable
Workflow-oriented
```

Không thiết kế theo phong cách landing page.

Tránh UI có cảm giác AI-generated:

- gradient ở nhiều nơi;
- bo góc 16–24px cho mọi component;
- shadow lớn;
- card hóa toàn bộ nội dung;
- dashboard toàn KPI không có giá trị nghiệp vụ;
- icon trang trí;
- spacing quá rộng;
- heading quá lớn;
- màu dùng chỉ để trang trí;
- microcopy marketing;
- animation không phục vụ thao tác.

Mỗi màn hình phải ưu tiên:

```text
Business Task
→ Data
→ Decision
→ Action
```

---

# 4. Tailwind CSS Setup

## 4.1 Nguyên tắc

- Tailwind phải được build local.
- Không dùng Tailwind CDN trong production.
- File CSS output là generated artifact.
- Không chỉnh sửa trực tiếp file CSS output.
- Tailwind utility class là cách styling mặc định.
- Chỉ tạo CSS custom khi utility trở nên khó đọc hoặc style lặp lại có ý nghĩa semantic rõ ràng.

## 4.2 Cấu trúc

Tại project root:

```text
package.json
```

CSS:

```text
static/
├── src/
│   └── tailwind.css
└── css/
    └── app.css
```

Trong đó:

```text
static/src/tailwind.css   = source
static/css/app.css        = generated output
```

## 4.3 Cài Tailwind

Codex phải kiểm tra xem project đã có Node/Tailwind chưa.

Nếu chưa có:

```bash
npm init -y
npm install -D tailwindcss @tailwindcss/cli
```

Không cài Bootstrap/Tabler.

## 4.4 package.json scripts

Thêm:

```json
{
  "scripts": {
    "dev:css": "npx @tailwindcss/cli -i ./static/src/tailwind.css -o ./static/css/app.css --watch",
    "build:css": "npx @tailwindcss/cli -i ./static/src/tailwind.css -o ./static/css/app.css --minify"
  }
}
```

Nếu phiên bản Tailwind hiện có trong project dùng syntax/config khác, Codex phải giữ đúng version hiện tại thay vì tự ý upgrade major version.

---

# 5. Tailwind Design System

Tạo:

```text
static/src/tailwind.css
```

Baseline:

```css
@import "tailwindcss";

/*
Source paths phải bao phủ Django templates và Python files
có chứa Tailwind class literals.
Điều chỉnh syntax @source theo phiên bản Tailwind thực tế.
*/
@source "../../templates";
@source "../../apps";

/* Design tokens */
@theme {
    --font-sans:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    --font-mono:
        "SFMono-Regular",
        Consolas,
        "Liberation Mono",
        monospace;

    --color-brand-50: #eff6ff;
    --color-brand-100: #dbeafe;
    --color-brand-500: #3b82f6;
    --color-brand-600: #2563eb;
    --color-brand-700: #1d4ed8;

    --color-success-50: #f0fdf4;
    --color-success-600: #16a34a;
    --color-success-700: #15803d;

    --color-warning-50: #fffbeb;
    --color-warning-600: #d97706;
    --color-warning-700: #b45309;

    --color-danger-50: #fef2f2;
    --color-danger-600: #dc2626;
    --color-danger-700: #b91c1c;

    --color-info-50: #f0f9ff;
    --color-info-600: #0284c7;
    --color-info-700: #0369a1;
}

@layer base {
    html {
        font-family: var(--font-sans);
    }

    body {
        @apply bg-slate-50 text-slate-800 antialiased;
    }

    button,
    input,
    select,
    textarea {
        font: inherit;
    }
}

/*
Chỉ định nghĩa component class khi markup utility lặp lại nhiều
và class đó có ý nghĩa semantic xuyên hệ thống.
*/
@layer components {
    .app-focus {
        @apply outline-none ring-2 ring-brand-500 ring-offset-2;
    }
}
```

## 5.1 Tailwind class rule

Không tạo dynamic class kiểu:

```django
bg-{{ color }}-100
text-{{ status }}-700
```

vì Tailwind build có thể không detect được.

Sai:

```django
<span class="bg-{{ color }}-100">
```

Đúng:

- dùng mapping Python;
- dùng template component với class literals đầy đủ;
- hoặc explicit condition.

Ví dụ:

```django
{% if status == "EFFECTIVE" %}
    <span class="bg-emerald-50 text-emerald-700 ring-emerald-600/20">
{% elif status == "REJECTED" %}
    <span class="bg-red-50 text-red-700 ring-red-600/20">
{% endif %}
```

---

# 6. Visual Rules

## 6.1 Radius

Dùng chủ yếu:

```text
rounded
rounded-md
rounded-lg
```

Không dùng `rounded-2xl`, `rounded-3xl` tràn lan.

## 6.2 Shadow

Mặc định ưu tiên:

```text
border border-slate-200
```

Shadow chỉ dùng cho:

- modal;
- drawer;
- dropdown;
- floating popover.

## 6.3 Typography

Body:

```text
text-sm
```

Secondary:

```text
text-xs / text-sm text-slate-500
```

Page title:

```text
text-xl / text-2xl font-semibold
```

Section title:

```text
text-sm / text-base font-semibold
```

Technical code:

```text
font-mono
```

## 6.4 Data alignment

- text: left;
- numeric: right;
- money: right;
- percent: right;
- actions: right;
- status: compact badge.

---

# 7. Cấu trúc frontend

```text
templates/
├── base/
│   ├── base.html
│   └── base_error.html
├── layouts/
│   ├── app_shell.html
│   ├── sidebar.html
│   ├── topbar.html
│   ├── breadcrumbs.html
│   └── page_header.html
├── components/
│   ├── button.html
│   ├── badge.html
│   ├── alert.html
│   ├── modal.html
│   ├── drawer.html
│   ├── toast.html
│   ├── empty_state.html
│   ├── pagination.html
│   ├── search_box.html
│   ├── filter_bar.html
│   ├── status_badge.html
│   ├── version_badge.html
│   ├── confirm_dialog.html
│   └── money.html
├── partials/
│   ├── form_errors.html
│   ├── loading.html
│   └── pagination_partial.html
├── master_data/
├── product/
├── bom/
├── formula_engine/
├── costing/
├── pricing/
├── workflow/
└── audit/
```

Static:

```text
static/
├── src/
│   └── tailwind.css
├── css/
│   └── app.css
├── js/
│   ├── app.js
│   ├── htmx-config.js
│   ├── alpine-components.js
│   └── modules/
│       ├── modal.js
│       ├── filter.js
│       ├── table.js
│       ├── formula-editor.js
│       ├── costing-tree.js
│       └── scenario-compare.js
└── vendor/
    ├── htmx/
    └── alpine/
```

Không tạo Bootstrap/Tabler assets.

---

# 8. Base Template

Tạo:

```text
templates/base/base.html
```

```html
{% load static %}

<!DOCTYPE html>
<html lang="vi" class="h-full">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>
        {% block title %}Costing Platform{% endblock %}
    </title>

    <link
        rel="stylesheet"
        href="{% static 'css/app.css' %}"
    >

    {% block extra_css %}{% endblock %}
</head>

<body class="min-h-full bg-slate-50 text-slate-800">

    {% block body %}{% endblock %}

    <div id="modal-root"></div>
    <div id="drawer-root"></div>
    <div id="toast-root"></div>

    <script src="{% static 'vendor/htmx/htmx.min.js' %}"></script>

    <script
        defer
        src="{% static 'vendor/alpine/alpine.min.js' %}"
    ></script>

    <script src="{% static 'js/htmx-config.js' %}"></script>
    <script src="{% static 'js/app.js' %}"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

---

# 9. Application Shell

Tạo:

```text
templates/layouts/app_shell.html
```

```html
{% extends "base/base.html" %}

{% block body %}
<div
    x-data="{ sidebarOpen: true, mobileSidebarOpen: false }"
    class="min-h-screen"
>
    {% include "layouts/sidebar.html" %}

    <div
        class="min-h-screen transition-[padding] duration-200"
        :class="sidebarOpen ? 'lg:pl-64' : 'lg:pl-[72px]'"
    >
        {% include "layouts/topbar.html" %}

        <main class="px-4 py-5 sm:px-6 lg:px-8">
            {% block breadcrumbs %}
                {% include "layouts/breadcrumbs.html" %}
            {% endblock %}

            {% block page_header %}
                {% include "layouts/page_header.html" %}
            {% endblock %}

            {% block content %}{% endblock %}
        </main>
    </div>
</div>
{% endblock %}
```

Desktop concept:

```text
┌───────────────────────────────────────────────────────────────┐
│ Sidebar │ Topbar                                              │
│         ├─────────────────────────────────────────────────────┤
│         │ Breadcrumb                                          │
│         │ Page title                         Page actions      │
│         │ Description                                         │
│         ├─────────────────────────────────────────────────────┤
│         │                 PAGE CONTENT                        │
└───────────────────────────────────────────────────────────────┘
```

---

# 10. Sidebar / Menu

Information architecture:

```text
Workspace
├── Tổng quan
├── Costing Runs
└── Pricing Scenarios

Master Data
├── Cost Elements
├── Sản phẩm
│   ├── Product Categories
│   ├── Items
│   ├── Products
│   └── SKUs
├── Đơn vị & tiền tệ
│   ├── Currency
│   ├── UoM
│   └── UoM Conversion
└── Nhà cung cấp
    ├── Suppliers
    └── Supplier Prices

Manufacturing
├── Recipe / BOM
├── Packaging
├── Routing
├── Work Centers
├── Resources
├── Resource Rates
├── Cost Pools
└── Allocation Rules

Formula & Rules
├── Formula Studio
├── Formula Versions
├── Rule Tables
└── Costing Schemes

Pricing
├── Channels
├── Channel Fee Rules
├── Tax Rules
├── FX Rates
├── Pricing Scenarios
└── Compare Scenarios

Workflow
├── Approval Inbox
├── My Requests
└── Overrides

Governance
├── Audit Log
└── Version History

Integration
├── Import Excel
├── Import History
└── Integrations

System
├── Organization
├── Users & Roles
└── Settings
```

Behavior:

- chỉ section hiện tại expand mặc định;
- sidebar collapse được trên desktop;
- mobile sidebar dùng overlay;
- active item rõ nhưng không quá nổi;
- không dùng nhiều màu;
- icon phải thống nhất một icon set;
- không tạo badge notification giả.

Icon có thể dùng SVG inline từ một icon set duy nhất. Không cài một UI framework chỉ để lấy icon.

---

# 11. Topbar

Chỉ chứa chức năng toàn cục:

```text
Organization switcher
Global search (future)
Pending approval indicator
User menu
```

Không đặt business action của page lên topbar.

Topbar gợi ý:

```html
<header
    class="
        sticky top-0 z-30 flex h-14 items-center
        border-b border-slate-200 bg-white/95
        px-4 backdrop-blur sm:px-6 lg:px-8
    "
>
    ...
</header>
```

---

# 12. Page Header Standard

Mẫu:

```text
Breadcrumb

Page Title                                  Primary Action
Description

Search / Filters
```

Ví dụ:

```text
Master Data / Cost Elements

Cost Elements                       [+ Tạo Cost Element]
Quản lý các biến nghiệp vụ dùng trong Formula và Costing Scheme.

[Search........] [Group ▼] [Type ▼] [Status ▼] [Reset]
```

Page title:

```html
<h1 class="text-xl font-semibold tracking-tight text-slate-900">
    Cost Elements
</h1>
```

Description:

```html
<p class="mt-1 text-sm text-slate-500">
    ...
</p>
```

Primary action tối đa 1 nút nổi bật.

---

# 13. Common Component Standards

## 13.1 Button

Primary:

```html
<button
    type="button"
    class="
        inline-flex items-center justify-center gap-2
        rounded-md bg-brand-600 px-3 py-2
        text-sm font-medium text-white
        hover:bg-brand-700
        focus:outline-none focus:ring-2 focus:ring-brand-500
        focus:ring-offset-2
        disabled:cursor-not-allowed disabled:opacity-50
    "
>
    Lưu
</button>
```

Secondary:

```text
border-slate-300 bg-white text-slate-700 hover:bg-slate-50
```

Danger chỉ cho destructive action.

Không tạo quá nhiều button variants.

## 13.2 Input

Baseline:

```text
h-9
rounded-md
border-slate-300
bg-white
text-sm
focus:border-brand-500
focus:ring-brand-500
```

## 13.3 Status Badge

Vocabulary:

```text
DRAFT
IN_REVIEW
APPROVED
EFFECTIVE
RETIRED
REJECTED
FAILED
LOCKED
SUPERSEDED
```

Màu:

```text
DRAFT          slate
IN_REVIEW      blue
APPROVED       emerald
EFFECTIVE      emerald
RETIRED        slate
REJECTED       red
FAILED         red
LOCKED         violet/slate
SUPERSEDED     slate
```

Không dùng dynamic Tailwind class string.

Tạo `templates/components/status_badge.html` với mappings explicit.

## 13.4 Version Badge

Neutral:

```text
v1
v2
v12
```

Không dùng cùng color semantic với status.

## 13.5 Empty State

Nhỏ, thực dụng:

```text
Chưa có Cost Element.
Tạo Cost Element đầu tiên để sử dụng trong Formula và Costing Scheme.

[+ Tạo Cost Element]
```

Không dùng illustration lớn nếu không cần.

## 13.6 Modal

Dùng Alpine.js cho open/close/focus UI.

Modal chỉ cho:

- confirm;
- form nhỏ;
- action đơn giản.

Không nhét Formula Studio/Recipe form lớn vào modal.

## 13.7 Drawer

Dùng cho:

- source trace;
- cost detail;
- version info;
- approval detail.

---

# 14. Data Table Standard

Data table là component quan trọng nhất.

Container:

```text
overflow-x-auto
border border-slate-200
bg-white
```

Header:

```text
bg-slate-50
text-xs
font-semibold
uppercase/tracking nếu phù hợp
text-slate-600
```

Row:

```text
min-height ~44–48px
border-t border-slate-100
hover:bg-slate-50
```

Quy tắc:

- text: left;
- numbers: right;
- money: right;
- percentage: right;
- technical code: `font-mono text-xs`;
- status: badge;
- actions: right.

Không zebra stripe mạnh.

Money display:

```text
125,430,500 ₫
```

Không display:

```text
125430500.00000000
```

---

# 15. Search / Filter / Sort / Pagination

List page chuẩn hỗ trợ:

```text
Search
Filter
Sort
Pagination
Reset
```

HTMX ưu tiên.

Ví dụ:

```html
<form
    hx-get="{% url 'master_data:cost_element_list' %}"
    hx-target="#cost-element-table"
    hx-push-url="true"
    class="flex flex-wrap items-end gap-3"
>
    ...
</form>
```

Search:

```html
<input
    type="search"
    name="q"
    hx-get="{% url 'master_data:cost_element_list' %}"
    hx-target="#cost-element-table"
    hx-trigger="keyup changed delay:400ms"
    hx-include="closest form"
>
```

URL phải giữ query string để:

- refresh không mất filter;
- copy URL giữ context;
- back/forward hoạt động.

---

# 16. Form Standard

Không tạo form dài một cột nếu có thể chia nhóm nghiệp vụ.

Cost Element:

```text
General Information
├── Group
├── Code
├── Name
└── Description

Value Configuration
├── Value Type
├── Dimension
├── Currency
├── UoM
├── Rounding Scale
└── Rounding Mode

Scope
├── Accounting Scope
└── Cost Scope

Security
├── Sensitive
└── Active
```

Layout desktop:

```text
grid grid-cols-1 gap-4 md:grid-cols-2
```

Section:

```text
border-b border-slate-200 pb-6
```

Không cần card riêng cho mọi section.

Form action:

```text
[Hủy] [Lưu]
```

Validation:

- field error dưới field;
- summary lỗi ở đầu form nếu cần;
- server-side validation là nguồn chuẩn;
- client-side validation chỉ hỗ trợ UX.

---

# 17. HTMX Convention

## Full page và partial

View phải hỗ trợ cả:

```text
normal request → full template
HTMX request   → partial template
```

Ví dụ:

```text
master_data/cost_element_list.html
master_data/partials/cost_element_table.html
```

## CSRF

Không disable CSRF.

HTMX POST/PUT/PATCH/DELETE phải gửi CSRF token.

Tạo:

```text
static/js/htmx-config.js
```

để cấu hình header CSRF nếu cần.

## Loading

Dùng:

```text
htmx-indicator
```

Không viết spinner logic riêng cho mỗi page.

## Error

- validation error phải giữ form;
- không expose traceback;
- unexpected error có trace/reference ID nếu backend hỗ trợ.

---

# 18. Alpine.js Convention

Alpine dùng cho local state:

```text
sidebar collapse
mobile menu
dropdown
drawer
modal
tabs
disclosure
```

Không dùng Alpine để gọi trực tiếp database.

Không duplicate HTMX responsibility.

Quy tắc:

```text
HTMX = server interaction
Alpine = local interaction
Tailwind = styling
Django = business logic
```

---

# 19. Tailwind Reuse Strategy

Không biến tất cả thành custom CSS class.

Ưu tiên:

```text
Django template component
+ Tailwind utility classes
```

Ví dụ:

```text
components/button.html
components/status_badge.html
components/pagination.html
```

Chỉ dùng `@apply` khi một semantic pattern lặp đi lặp lại nhiều nơi và việc giữ utility trong template gây khó bảo trì.

Không xây một internal UI framework quá sớm.

---

# 20. Responsive Strategy

Desktop-first.

```text
>= 1280px
Full enterprise workspace

992–1279px
Collapsible sidebar

768–991px
List/detail/approval/simple form

< 768px
Review/approval/lookup/notification
```

Không bắt buộc Formula Studio, Costing Workspace hoặc Scenario Compare phải tối ưu hoàn hảo trên mobile.

Table trên màn hình hẹp:

- cho horizontal scroll;
- không cố nhồi tất cả cột;
- có thể ẩn các cột secondary bằng responsive utility.

---

# 21. Accessibility

Bắt buộc:

- input có label;
- focus state nhìn thấy được;
- action dùng `<button>`;
- navigation dùng `<a>`;
- icon-only button có `aria-label`;
- không dùng màu làm tín hiệu duy nhất;
- form error liên kết field;
- modal/drawer quản lý focus hợp lý;
- table header dùng `<th>`;
- interactive target đủ lớn;
- dropdown có keyboard behavior cơ bản.

---

# 22. Business Screens Baseline

Các màn hình đặc thù về sau:

```text
Formula Studio
Costing Workspace
Scenario Compare
Approval Inbox
Version Timeline
```

## Formula Studio

Desktop 3 vùng:

```text
┌───────────────────────────────────────────────────────────────────────┐
│ TARGET_PRICE                     Version 3      DRAFT   [Test] [Save] │
├────────────────┬───────────────────────────────────────┬──────────────┤
│ ELEMENTS       │ FORMULA EDITOR                        │ PROPERTIES   │
│ Search...      │ FULL_COST /                           │ Output MONEY │
│ Cost           │ (1 - PLATFORM_FEE - TARGET_MARGIN)   │ Precision 2 │
│ Pricing        │                                       │ Effective   │
├────────────────┴───────────────────────────────────────┴──────────────┤
│ Validation | Test Cases | Dependencies | Explain                     │
├───────────────────────────────────────────────────────────────────────┤
│ ✓ Syntax ✓ Type ✓ Dimension ✓ Dependency ✓ Cycle ✓ Tests 12/12      │
└───────────────────────────────────────────────────────────────────────┘
```

Guardrail:

- không arbitrary SQL/Python/JavaScript;
- element chọn/autocomplete từ Cost Element;
- inline validation;
- dependency rõ;
- test visible trước submit.

## Costing Workspace

Context:

```text
Product / SKU
Quantity / UoM
Channel
Currency
Effective Date
Run Status
Version
```

Cost tree:

```text
▼ Manufacturing Cost
    Raw Material
    Packaging
    Labor
    Machine
    Factory Overhead

▼ Landed Cost
    Transport
    Import / Export

▼ Channel Cost
    Platform Fee
    Transaction Fee
    Affiliate
```

Click line mở drawer:

```text
Value
Source
Formula
Rule
Version
Effective Date
Inputs
Intermediate Values
Trace ID
Warnings
```

Explain lịch sử đọc persisted trace; không recompute bằng dữ liệu hiện tại.

## Scenario Compare

Pin 2–5 scenarios.

Ưu tiên comparison table trước chart.

## Approval Inbox

Hiển thị:

```text
Entity
Version diff
Maker
Submitted time
Reason
Validation
Test result
Impact
```

Approve không phải action “mù”.

## Version UX

Version là first-class UI:

```text
Version
Status
Effective From
Effective To
Created By
Created At
Approved By
Approved At
Change Reason
```

Effective version không edit trực tiếp. Action:

```text
Create New Version
```

---

# 23. Django App Responsibilities

## `apps/core`

Persistence models only.

## `apps/master_data`

```text
Cost Element
Currency
UoM
Supplier
Supplier Price
```

## `apps/product`

```text
Product Category
Item
Product
SKU
```

## `apps/bom`

```text
Recipe
Packaging
Routing
Resource
Work Center
Cost Pool
Allocation
```

## `apps/formula_engine`

```text
Formula
Formula Version
Dependency
Parser
AST
Validator
Evaluator
Rule Table
Rule Resolver
```

## `apps/costing`

```text
Costing Scheme
Costing Run
Roll-up
Override
Explain
```

## `apps/pricing`

```text
Channel
Fee
Tax
FX
Pricing Scenario
Scenario Compare
```

## `apps/workflow`

```text
Approval Request
Approval Action
Workflow
```

## `apps/audit`

```text
Audit Query
Audit UI
Trace / History
```

Business apps import:

```python
from apps.core.models import ...
```

Không import business service ngược vào `core`.

---

# 24. Backend Coding Pattern

Không viết toàn bộ nghiệp vụ trong view.

```text
View
 ↓
Form
 ↓
Service / Selector
 ↓
Core Model
 ↓
PostgreSQL
```

View:

- request;
- permission;
- form orchestration;
- response.

Service:

- transaction;
- business rule;
- persistence orchestration;
- audit integration.

Selector:

- optimized read query;
- filters;
- sorting;
- `select_related`;
- `prefetch_related`.

---

# 25. Iteration 1 – Foundation UI

Chỉ triển khai:

```text
1. Tailwind local build setup
2. static/src/tailwind.css
3. static/css/app.css generated output
4. base.html
5. app_shell.html
6. sidebar.html
7. topbar.html
8. breadcrumbs.html
9. page_header.html
10. button pattern
11. status badge
12. modal
13. drawer
14. toast
15. empty state
16. pagination
17. search box
18. filter bar
19. common data table pattern
```

Sau Foundation triển khai Cost Element.

Không làm Formula Studio trong iteration này.

---

# 26. Cost Element – Implementation Spec

Namespace:

```python
app_name = "master_data"
```

Routes:

```text
/master-data/cost-elements/
/master-data/cost-elements/create/
/master-data/cost-elements/<id>/
/master-data/cost-elements/<id>/edit/
```

URL names:

```text
master_data:cost_element_list
master_data:cost_element_create
master_data:cost_element_detail
master_data:cost_element_edit
```

Templates:

```text
templates/master_data/
├── cost_element_list.html
├── cost_element_form.html
├── cost_element_detail.html
└── partials/
    ├── cost_element_table.html
    └── cost_element_rows.html
```

List columns:

```text
Code
Name
Group
Value Type
Source Mode
Accounting Scope
Cost Scope
Sensitive
Status
Actions
```

Filters:

```text
Keyword
Group
Value Type
Source Mode
Cost Scope
Active
```

Sort:

```text
code
name
value_type
created_at
```

Pagination:

```text
25 default
50
100
```

Form:

```text
group
code
name
description
value_type
dimension_code
default_source_mode
currency_code
default_uom
rounding_scale
rounding_mode
accounting_scope
cost_scope
is_sensitive
is_active
```

Không expose:

```text
id
created_by
updated_by
created_at
updated_at
```

---

# 27. Cost Element Service Rules

Create/update:

```text
organization = get_default_organization() qua workspace nội bộ
created_by/updated_by = NULL (no-auth)
code = uppercase + trimmed
name = trimmed
```

Validate:

```text
code không rỗng
code unique trong organization
rounding_scale hợp lệ
currency/UoM theo policy/value type
```

Database constraint vẫn là lớp bảo vệ cuối.

`IntegrityError` phải được chuyển thành lỗi nghiệp vụ dễ hiểu.

Không hard-code organization ID/user ID.

---

# 28. Cost Element Selector

QuerySet phải cân nhắc:

```python
select_related(
    "organization",
    "group",
    "currency_code",
    "default_uom",
)
```

Search:

```text
code
name
description
```

Filter dùng ORM.

Không raw SQL cho CRUD thông thường.

Tránh N+1.

---

# 29. Permission Hook

UI cần sẵn hook:

```django
{% if permissions.can_create_cost_element %}
    ...
{% endif %}
```

Ẩn button không phải security.

Backend vẫn bắt buộc kiểm tra quyền.

---

# 30. Error / Toast / Confirm

Validation:

```text
Không thể lưu Cost Element.
Vui lòng kiểm tra các trường được đánh dấu.
```

Permission:

```text
Bạn không có quyền thực hiện thao tác này.
```

Not found:

```text
Không tìm thấy Cost Element.
```

Unexpected:

```text
Đã xảy ra lỗi khi xử lý yêu cầu.
Mã tham chiếu: <trace_id>
```

Toast chỉ dùng cho success:

```text
Đã tạo Cost Element.
Đã cập nhật Cost Element.
```

Không dùng toast thay cho field validation.

Confirm message phải cụ thể, không chỉ:

```text
Are you sure?
```

---

# 31. Tailwind Guardrails cho Codex

Codex phải tuân thủ:

1. Không cài Bootstrap.
2. Không cài Tabler UI.
3. Không dùng Tailwind CDN cho production.
4. Không chỉnh sửa trực tiếp `static/css/app.css` nếu đó là generated output.
5. Không tạo class Tailwind động bằng Django interpolation.
6. Không spam `@apply`.
7. Không tạo custom CSS cho thứ Tailwind utility xử lý tốt.
8. Không dùng arbitrary value quá nhiều như `[13px]`, `[247px]` nếu theme/utility chuẩn đáp ứng được.
9. Không hard-code cùng một semantic style nhiều lần nếu có thể thành template component.
10. Không biến component library thành abstraction framework quá sớm.
11. Không dùng transition/animation không cần thiết.
12. Không dùng `!important` trừ trường hợp được giải thích rõ.

---

# 32. Definition of Done – Foundation

- [ ] Tailwind build local hoạt động.
- [ ] `npm run dev:css` hoạt động.
- [ ] `npm run build:css` hoạt động.
- [ ] Base template.
- [ ] App shell.
- [ ] Desktop sidebar.
- [ ] Mobile sidebar.
- [ ] Sidebar collapse.
- [ ] Topbar.
- [ ] Breadcrumb.
- [ ] Page header.
- [ ] Button pattern.
- [ ] Status badge.
- [ ] Modal.
- [ ] Drawer.
- [ ] Toast.
- [ ] Empty state.
- [ ] Search/filter pattern.
- [ ] Pagination pattern.
- [ ] Data table pattern.
- [ ] Focus/accessibility cơ bản.
- [ ] Responsive không vỡ.
- [ ] Không JS console error.
- [ ] Không Bootstrap/Tabler dependency.
- [ ] Không duplicate CSS lớn.
- [ ] Tailwind production build minified thành công.

---

# 33. Definition of Done – Cost Element

- [ ] List.
- [ ] Search.
- [ ] Filter.
- [ ] Sort.
- [ ] Pagination.
- [ ] Detail.
- [ ] Create.
- [ ] Edit.
- [ ] Validation.
- [ ] Empty state.
- [ ] HTMX loading state.
- [ ] Success toast.
- [ ] Permission hooks.
- [ ] Tests.
- [ ] Không N+1 nghiêm trọng.
- [ ] Không thay đổi DB schema.
- [ ] Tailwind classes build đầy đủ, không mất class sau production build.

---

# 34. Quy tắc bắt buộc cho Codex

1. Đọc cấu trúc project trước khi sửa.
2. Không sửa DB schema trong task này.
3. Không tạo lại business models.
4. Không chuyển models khỏi `apps/core/models.py`.
5. Không tạo business migration.
6. Không đưa business logic vào template.
7. Không đưa business logic vào JavaScript.
8. Không raw SQL nếu ORM làm được.
9. Không xây SPA.
10. Stack phải là Django Templates + HTMX + Alpine.js + Tailwind CSS.
11. Không thêm Bootstrap/Tabler/UI framework khác.
12. Reuse template component trước khi copy markup lớn.
13. Không over-engineer.
14. Iteration đầu chỉ Foundation + Cost Element.
15. Đặt tên theo nghiệp vụ.
16. Không hard-code organization ID.
17. Không hard-code user ID.
18. Không hard-code business rate/formula.
19. Không bypass CSRF.
20. Không expose credentials ra frontend.
21. Không tạo Tailwind dynamic class không thể detect khi build.
22. Không tự ý nâng major version Tailwind nếu project đã có version.
23. Chạy production CSS build trước khi báo hoàn thành.

---

# 35. Quy trình Codex

## Step 1 – Inspect

Đọc:

```text
package.json
config/settings.py
config/urls.py
apps/core/models.py
apps/master_data/
templates/
static/
```

nếu tồn tại.

Kiểm tra:

```text
Node/npm
Tailwind version
HTMX
Alpine.js
STATIC_URL
STATICFILES_DIRS
template DIRS
```

## Step 2 – Plan

Báo ngắn:

```text
Files to create
Files to modify
Files intentionally unchanged
Dependencies to install
```

## Step 3 – Tailwind

Nếu chưa setup:

- tạo/cập nhật package.json;
- cài Tailwind CLI;
- tạo `static/src/tailwind.css`;
- cấu hình source scanning phù hợp version;
- build `static/css/app.css`.

## Step 4 – Foundation

Tạo:

```text
base
app shell
sidebar
topbar
breadcrumbs
page header
common components
```

## Step 5 – Master Data URLs

Tạo namespace `master_data`.

## Step 6 – Cost Element backend

Tạo cấu trúc phù hợp, ví dụ:

```text
forms.py
selectors.py
services.py
views.py
urls.py
```

Không tạo `CostElement` model mới.

Dùng:

```python
from apps.core.models import CostElement
```

## Step 7 – Cost Element templates

Tạo:

```text
list
detail
form
partials
```

## Step 8 – HTMX

Áp dụng:

```text
search
filter
sort
pagination
```

Create/Edit không bắt buộc HTMX nếu làm tăng complexity.

## Step 9 – Validation

Chạy:

```bash
python manage.py check
npm run build:css
```

và tests phù hợp.

Nếu dùng pytest:

```bash
pytest
```

Nếu dùng Django test:

```bash
python manage.py test
```

## Step 10 – Report

Báo:

```text
Files created
Files modified
Dependencies installed
Architecture decisions
How to run Django
How to run Tailwind watcher
Tests executed
Build result
Known limitations
Next recommended step
```

---

# 36. Prompt dùng trực tiếp cho Codex

```text
Bạn đang làm việc trên dự án Django Hethongtinhgiathanh.

Đọc toàn bộ FRONTEND_IMPLEMENTATION_SPEC.md trước khi sửa code.

Stack frontend bắt buộc:
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

Không sử dụng Bootstrap, Tabler UI, React, Vue hoặc frontend framework khác.

Mục tiêu iteration:
1. Setup/kiểm tra Tailwind CSS local build.
2. Xây dựng Frontend Foundation.
3. Xây dựng App Shell: Sidebar, Topbar, Breadcrumb, Page Header.
4. Xây dựng common template components.
5. Triển khai Cost Element Management:
   - list;
   - search;
   - filter;
   - sort;
   - pagination;
   - detail;
   - create;
   - edit.

Database là database-first.
Business models nằm trong apps/core/models.py và có managed=False.
Không tạo lại bảng costing bằng Django migration.
Không thay đổi database schema.
Không tạo CostElement model mới.

Trước khi code:
- inspect project structure;
- đọc package.json nếu có;
- kiểm tra version Tailwind hiện tại nếu có;
- đọc config/settings.py;
- đọc config/urls.py;
- đọc apps/core/models.py;
- đọc apps/master_data;
- kiểm tra templates/static;
- trình bày kế hoạch files create/modify và dependency cần cài.

Tailwind:
- dùng local build, không dùng CDN production;
- source CSS: static/src/tailwind.css;
- generated CSS: static/css/app.css;
- không chỉnh trực tiếp generated app.css;
- không tạo class động kiểu bg-{{ color }}-500;
- không spam @apply;
- dùng utility classes làm mặc định;
- không tự ý nâng major Tailwind nếu project đã có version.

Khi code:
- business logic không nằm trong templates hoặc JavaScript;
- tránh N+1;
- search/filter/sort/pagination server-side;
- dùng HTMX cho partial update phù hợp;
- Alpine chỉ dùng cho local UI state;
- giữ CSRF;
- giữ query string;
- UI desktop-first, enterprise, data-dense;
- không gradient/card/shadow dư thừa;
- không over-engineer.

Sau khi code:
- chạy python manage.py check;
- chạy npm run build:css;
- chạy tests phù hợp;
- báo rõ files created/modified;
- báo dependency đã cài;
- báo test/build result;
- không tự triển khai Formula Studio hoặc module khác ngoài scope iteration.
```

---

# 37. Roadmap sau Foundation + Cost Element

Tiếp theo:

```text
Currency
UoM
UoM Conversion
Product Category
Item
Product
SKU
Supplier
Supplier Price
```

Sau khi master data ổn định:

```text
Recipe / BOM
Packaging
Resource
Work Center
Routing
Cost Pool
Allocation
Formula Studio
Rule Engine
Costing Scheme
Costing Workspace
Pricing Scenario
Approval
Audit
```

---

# 38. Nguyên tắc cuối cùng

Mục tiêu của UI không phải là trình diễn.

Ưu tiên:

```text
dễ đọc
dễ thao tác
dễ audit
dễ giải thích
ít lỗi nhập liệu
giữ context
version rõ ràng
workflow rõ ràng
```

Mỗi quyết định frontend phải phục vụ nghiệp vụ Costing & Pricing trước khi phục vụ yếu tố trang trí.
