# Lần tính giá thành

Iteration 07/10/2026. URL `/costing/runs/`, namespace `costing:`. Single-company,
truy cập trực tiếp, UI tiếng Việt. Không schema change, business migration,
authentication, organization UI, queue hoặc Pricing.

## Schema, quan hệ và lifecycle thực tế

Đã kiểm tra Supabase bằng transaction READ ONLY. Models vẫn unmanaged trong core:

| Model | Sử dụng |
| --- | --- |
| CostingRun | public_id UUID/run_no, run_type/status, SchemeVersion FK, Product/SKU FK, quantity/UoM, result_currency_code, effective_at, context/version/fx snapshot JSON, các money result fields, trace_id, idempotency_key, supersedes/compares_to_run FK, nullable actors/timestamps |
| CostingRunLine | exact SchemeLine/CostElement/FormulaVersion FK, code/label/source/type/order, typed amount/quantity/number/percent/bool/text, input/source trace/warnings JSON, computed_at |
| CostingOverride | Có trong DB: original/override value, reason, PENDING/APPROVED/REJECTED; chưa mở workflow điều chỉnh kết quả |

Không có result/trace/source/error tables riêng hoặc completed_at/failed_at/run_time.
JSON versioned `schema: 1` giữ notes/started_at/finished_at/warnings/errors. Ngày tính
lưu trong effective_at là nửa đêm theo TIME_ZONE. UI yêu cầu Product; SKU tùy chọn,
nhưng tính bao bì cần SKU. Scheme chưa có Product/SKU assignment nên chọn thủ công.

Stored statuses: DRAFT, CALCULATED, IN_REVIEW, APPROVED, LOCKED, FAILED, SUPERSEDED.
Thành công: DRAFT → CALCULATED → LOCKED trong một transaction. Thất bại: FAILED.
Không fake RUNNING/COMPLETED. Trigger DB bảo vệ header/lines APPROVED/LOCKED/
SUPERSEDED; OLD LOCKED/SUPERSEDED không UPDATE được. UI không edit/delete Run.
Chỉ mở STANDARD/PLANNED; chưa có actual-consumption/channel/pricing execution.
created_by/approved_by luôn NULL. Reuse company compatibility helper/access nội bộ,
không membership/user session/organization selector.

Unique: public_id; compatibility organization + run_no; organization + idempotency_key;
Run + line_code; Run + display_order. run_no dùng public UUID, không giả định CR-YYYY.
Rerun dùng supersedes_run để liên kết lần gốc, không sửa trạng thái lần gốc.

## Execution và resolver contracts

View → RunForm → create_run → ExecutionContext/dated resolvers → Formula Engine
→ CostingResult/typed lines → persisted results/sources/snapshot/trace. Engine không
biết request/HTTP/session; caches thuộc riêng một Run. Chạy synchronous.

SchemeVersion phải là đúng một version EFFECTIVE theo ngày tính. Root formula dùng
exact FormulaVersion FK; nested formulas được engine hiện có resolve đúng ngày.
Config validation reuse parser, type/unit, dependency completeness/cycle. Execution
order từ graph, display_order chỉ trình bày. Versions/masters phải active/VALID
nếu có validation_status. Không eval/exec/parser riêng hoặc executable JSON.

| SYSTEM code (text config, không DB enum mới) | Kết quả |
| --- | --- |
| MATERIAL_COST | Tổng tiền nguyên liệu từ RecipeVersion/Lines |
| PACKAGING_COST | Tổng tiền bao bì từ assignment SKU + ConfigVersion/Lines |
| RESOURCE_COST | Tổng tiền sử dụng primary_resource của RoutingOperations |
| RUN_QUANTITY | Sản lượng theo UoM của CostElement QUANTITY |
| ALLOCATION:&lt;rule_code&gt; | Phân bổ NORMAL_CAPACITY có đủ số liệu kỳ và đơn vị |

Resolver cần CE có kiểu tương ứng. MONEY trả tổng tiền, không default_uom đơn giá,
cùng currency Run. MANUAL sinh field typed từ SchemeLine; giữ yêu cầu gốc, raw/
rounded value và trace nguồn thủ công. Đây là input, không silently override SYSTEM.
FORMULA gọi Plan.run/budget của Formula Engine; inferred type bảo toàn cả dòng
không gán CE. LOOKUP/EXTERNAL/condition_jsonb/mã chưa đăng ký bị chặn.

## Ngày hiệu lực và quy mô

Mọi resolver dùng `effective_from <= costing_date` và end NULL hoặc
`effective_to >= costing_date` (end inclusive), không dùng ngày server. Schema vẫn
yêu cầu end > start khi tạo/cập nhật source/version.

- Recipe/Routing gắn Product: đúng một EFFECTIVE version trong các header active.
  Nhiều header/version phù hợp thì FAILED, không chọn mới nhất.
- SKU: Run quantity chuyển sang sales_uom; lượng đầu ra cho Recipe/Routing/capacity
  là số đơn vị bán × net_quantity, quy đổi từ net_quantity_uom. Không mặc định kg.
  Không SKU: quantity/UoM chuyển trực tiếp, dùng Product.output_item nếu cần.
  Basis thuộc đại lượng đơn vị bán (ví dụ thùng so với hộp, lượng tịnh là kg)
  chuyển trực tiếp số đơn vị bán, không đi qua khối lượng tịnh.
- Recipe scale = output cần tính / output_qty. Quy tắc người dùng xác nhận:
  **RecipeLine.qty × scale / yield_rate / (1 − scrap_rate)**. Trace lưu riêng base,
  scale, yield, scrap và adjusted quantity. Không sửa BOM.
- PackagingVersion không có output_qty/output_uom. Người chạy nhập lượng và đơn vị
  cơ sở đóng gói, lưu trong context.request. Scale = Run quantity theo đơn vị cơ sở
  / lượng cơ sở. PackagingLine.qty đã là nhu cầu đầy đủ trên cơ sở này; level/parent/
  units_per_parent là evidence, không nhân ngầm lần nữa. Assignment phải primary,
  đúng Product, active, dated và duy nhất. Quantity fractional Decimal giữ precision.
- Routing: **setup một lần mỗi Run; usage = setup + run_time × scale**. Basis ưu tiên
  Operation.quantity_basis/quantity_uom; nếu basis NULL dùng Version.batch_size/
  batch_uom. Thời gian khác 0 cần primary_resource, TIME UoM, Resource/WorkCenter
  nhất quán. Không mặc định basis = 1 hoặc snapshot current rate vào Routing.
  Công đoạn chỉ có setup không yêu cầu sản lượng cơ sở cho run_time bằng 0.

Không expand nested BOM, chọn optional/substitute item hoặc market/artwork bao bì
khi chưa có policy. Các trường hợp đó FAILED, không bỏ qua chi phí.

## Giá mua, đơn giá, quy đổi và FX

PriceResolver dùng chung cho nguyên liệu/bao bì. Query candidate EFFECTIVE, supplier
active, item/date; chuyển required quantity sang price_uom, kiểm tra min_qty.
Chỉ dùng đúng một giá phù hợp cùng currency. Không fallback giá 0, chọn latest/
lowest/supplier hoặc tier cao nhất. Tiers xét nhu cầu từng dòng; chưa có policy
cộng gộp nhu cầu BOM + Packaging để áp dụng chiết khấu chung.

ResourceRateResolver cần đúng một rate EFFECTIVE theo Resource/date; không đoán
rate_type. Chuyển usage sang per_uom từ master. amount >= 0 theo DB; không mặc định
đơn giá tính theo giờ hoặc chia 60 trong code.

UomResolver query đúng các cặp cần dùng theo ngày, global/current company và item
scope. Hỗ trợ trực tiếp hoặc nghịch đảo 1/factor. Không chain hoặc ưu tiên item-
specific thay global nếu cả hai cùng có. Cùng UoM là identity; khác UoM thiếu quy
đổi thì FAILED. Khác đại lượng cần conversion theo Item. ID/fields/factor thực tế
được snapshot và trace, không hard-code kg/g/minute/hour.

Chưa có hợp đồng FX/provider hoặc xử lý thuế mua hàng được xác nhận. Nguồn khác
currency, tax_inclusive hoặc tax_rate khác 0 → FAILED. Không API FX, hard-code tỷ
giá, lấy giá gross làm cost hoặc bỏ thuế ngầm. fx_snapshot_jsonb hiện {}.

## Phân bổ và tổng hợp

NORMAL_CAPACITY chỉ chạy khi rule EFFECTIVE không condition/formula, pool active,
đúng một CostPoolPeriod EFFECTIVE chứa ngày tính, amount/currency rõ ràng,
normal_capacity > 0 và capacity_uom. Tiêu thức là sản lượng đầu ra chuyển sang
capacity_uom, không đoán giờ máy. basis_uom nếu có phải trùng capacity_uom.
**allocated = period.amount × usage / normal_capacity**. Vượt capacity thì FAILED
vì chưa có policy phần vượt. Chưa hỗ trợ MACHINE_HOUR, LABOR_HOUR, KG, UNIT, BATCH,
PALLET_DAY, SHIPMENT, VALUE, CUSTOM: thiếu mẫu số/phạm vi dataset/hợp đồng thực thi.
Không lấy tổng driver nhà máy từ một SKU. CostPoolPeriod đã có DB nhưng chưa có UI
nhập số liệu kỳ; cần dữ liệu EFFECTIVE được chuẩn bị trước.

Run cần đúng một OUTPUT MONEY thuộc MANUFACTURING, không UoM đơn giá. Chỉ thực thi
MANUFACTURING/ANALYTICS; chưa LANDED/COST_TO_SERVE/CHANNEL/PRICING. Không cộng mọi
INPUT/SUBTOTAL/OUTPUT gây double count. Tổng OUTPUT lưu manufacturing_cost và
full_cost trong scope sản xuất hiện tại; cột khác NULL. Per-unit là Decimal string
trong context, UI round theo currency.decimal_places đã snapshot. Tỷ trọng hiển thị
hai chữ số thập phân, chỉ là
metric từng dòng so với tổng, xử lý total 0; các tổng phụ không được cộng lại.

Decimal context reuse precision/magnitude/budget của Formula Engine. Round tại
ranh giới dòng: SchemeLine.rounding_scale rồi CE scale/mode. Giữ raw intermediates;
reject vượt numeric 24,8 hoặc percent 18,10, không để DB tự truncate. JSON Decimal
serialize thành string; float bị từ chối.

## Transaction, thất bại và lịch sử

Root transaction REPEATABLE READ và lock compatibility company theo service hiện
có: các nguồn đọc cùng DB snapshot, kể cả giá thay đổi giữa lúc chạy. Retry tối đa
3 cho serialization/deadlock/unique race; không external effects. UUID idempotency
key + request hash: cùng key/yêu cầu trả Run cũ, khác yêu cầu báo validation error.
HTMX disable submit/loading; POST có CSRF.

Header outer transaction, calculation/bulk lines/snapshot/result/lock savepoint.
Lỗi rollback toàn bộ result data, giữ FAILED với code/stage/message/trace_id.
Unexpected error log traceback server, UI chỉ thông điệp an toàn. Không partial
success hoặc fake total. Input chưa hợp lệ/không SchemeVersion trả form errors.

Snapshot `schema: 1`, `engine: costing-v1`: sources table:ID + scalar fields/FKs/
dates/qty/price/rate, exact formula version/expression/AST hash/bindings/order,
rule algorithms và SHA256. Không chỉ FK tới master có thể đổi. Lines giữ inputs,
raw value/config; trace lưu quy mô/hao hụt/conversions/source price/rate/allocation/
formula và named input values/rounding. Snapshot đủ xem lại dữ liệu đã dùng.

Historical detail/drawer/snapshot chỉ đọc Run/RunLine và JSON, không query mutable
source masters hoặc gọi resolver/evaluator lại. Thay master không đổi summary/
trace/hash. Chưa có standalone replay offline từ snapshot. Rerun prefill yêu cầu/
manual inputs, key mới, supersedes_run FK và chọn current sources lại theo ngày
chọn; Run cũ giữ nguyên. Chưa full manual override approval workflow.

## UI, query và file manifest

Reuse Page Header/search/filter/table/pagination/empty state/form/errors/toast/drawer.
List search stored names/code; Product/SKU/Scheme/status/date range; whitelist sort,
DB pagination 25/50/100. Date filter cùng form giữ qua search/sort/page. Product →
SKU và date → Scheme versions qua HTMX; GET options không gửi CSRF/key/notes trong
URL. Full GET/POST fallback, HX-History-Restore theo convention.
Detail/trace/snapshot tiếng Việt, dd/mm/yyyy, dấu chấm nhóm và dấu phẩy thập phân,
không raw JSON. Drawer focus/Escape, field labels/aria, responsive desktop/mobile.
Sidebar active «Lần tính giá thành» trong Tổng quan.

select_related đúng FK; prices batch theo Item, rates theo Resource, conversions
batch đúng pairs/scopes, cache riêng Run. Giới hạn 2000 rows/source query, graph và
Formula budget hiện có. Detail result pagination; historical labels không join
nguồn mutable. Không filter table bằng Python hoặc query từng AST node.

Tạo Python trong `apps/costing/`: `run_constants`, `run_forms`, `run_selectors`,
`run_services`, `run_views`, `run_testing`, `run_test_data`; tests `test_run_integration`,
`test_run_resolvers`, `test_run_concurrency`, `test_run_browser`;
`templatetags/{__init__,costing_tags}`; `engine/{__init__,errors,context,registry,runner}`;
`engine/resolvers/{__init__,common,scheme,manufacturing,prices,uom,allocation}` (.py).

Tạo `templates/costing/runs/{list,form,detail,trace,snapshot}.html`,
`partials/{rows,form_content,dependent_fields,detail_content,lines,trace,trace_content,
snapshot_content}.html`; tài liệu này.

Sửa `apps/costing/{urls,configuration,forms}.py`,
`apps/master_data/{access,context_processors,navigation,presentation,testing}.py`,
`templates/master_data/partials/reference_data_filters.html`, `static/css/app.css`
(generated bằng build), README và docs 00_AI_CONTEXT/FRONTEND_IMPLEMENTATION_SPEC/
COSTING_SCHEME. Không dependency mới/core models/settings/business migrations.

## Chạy và kiểm thử

```powershell
env\Scripts\python.exe manage.py check
env\Scripts\python.exe manage.py runserver
npm run dev:css
npm run build:css
$env:COSTING_BROWSER_TESTS='1'
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD\artifacts\playwright"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

Test runner chỉ PostgreSQL localhost test_costing_slice/costing_test với guard trước
DDL. Fixtures mirror CHECK/FK/unique/immutable triggers production đã đọc; không write
Supabase. Golden: 40.000 nguyên liệu + 5.000 bao bì + 10.000 nguồn lực + 5.000 chung =
**60.000 VND**. Tests cover resolvers độc lập, full pipeline, date boundaries, yield/
scrap/setup/basis/fractional quantities, missing/ambiguous sources/FX/conversion,
formula errors, manual typed inputs, rounding/overflow, rollback, immutable history/
master changes, rerun/idempotency/race/read consistency, batching, CSRF/no-auth,
list/filter/sort/pagination/partial/error, browser dependent fields/drawer/mobile.
Logs/screenshots: `artifacts/`.

Kết quả kiểm chứng ngày 07/10/2026:

- `manage.py check`: không lỗi; `npm run build:css`: PASS, Tailwind 4.3.3.
- Full suite cuối với browser bật: **571/571 PASS**, 146,149 giây, không skip;
  gồm 66 test mới Costing Run và 505 regression tests của các iteration trước.
- Costing Run targeted với browser: **64/64 PASS**, 12,289 giây, gồm 9 resolver tests,
  integration/golden/history/concurrency/browser và basis thùng/hộp. Full suite cuối
  đã bổ sung setup-only, zero total và so sánh query count trước/sau tăng BOM lines.
- Golden total 60.000 VND; history test chứng minh nguồn đổi không sửa kết quả/
  trace/hash, không query masters ở historical detail. Double-submit tạo đúng một
  complete Run; concurrent price change dùng cùng repeatable transaction snapshot.
- Supabase GET trong READ ONLY: `/costing/runs/`, `/costing/runs/create/`,
  `/costing/schemes/`, `/master-data/cost-elements/` đều HTTP 200. Không POST/write
  production. Checks/fixture metadata không yêu cầu hoặc thay đổi schema.
- Log: `artifacts/run-full-tests.log`, `artifacts/run-targeted-tests.log`;
  screenshot `artifacts/screenshots/costing-run-desktop.png`,
  `artifacts/screenshots/costing-run-mobile.png`. Console server có broken pipe
  khi HTMX hủy request cũ theo replace policy; test outcomes vẫn PASS.

Manifest iteration: **39 file mới** (25 Python, 13 template, 1 tài liệu),
**14 file sửa**, không xóa file hoặc cài dependency.

Iteration tiếp theo đề xuất: **quản lý số liệu kỳ chi phí chung (CostPoolPeriod)**;
sau đó xác định selection policy, FX/thuế và driver datasets trước khi mở rộng
Costing/Pricing. Không triển khai thêm trong task này.
