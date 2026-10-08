# Bộ máy công thức — 07/10/2026

Đã triển khai Formula Management / Studio / kiểm thử độc lập. Không tính BOM,
bao bì, nguồn lực, phân bổ, Pricing hoặc Costing Run. Không thay schema/migration,
core models, authentication hoặc company workflow.

## Schema đã đối chiếu Supabase bằng READ ONLY

| Model | Dữ liệu |
|---|---|
| Formula | organization compatibility FK, code/name/description/output_element/is_active, timestamps |
| FormulaVersion | formula/version_no/expression/ast_jsonb/ast_hash/status/effective dates/validation_status/message/change_reason; actor nullable |
| FormulaDependency | formula_version + depends_on_element hoặc depends_on_formula, dependency_kind/code |
| FormulaTestCase | formula/name/input_context/expected_value_numeric hoặc text/tolerance/is_active/timestamps |

Unique: `uq_formula(organization_id,code)`, `uq_formula_version(formula_id,version_no)`.
Status: DRAFT, IN_REVIEW, APPROVED, EFFECTIVE, RETIRED. Validation: NOT_VALIDATED,
VALID, INVALID. Period CHECK: end > start; non-draft/review cần start. Test tolerance
>= 0. Dependency kinds DB còn SYSTEM_FIELD/RULE_TABLE/RESOLVER nhưng chưa expose.
Không có formula_type/result_type riêng; khai báo đầu ra dùng CostElement. Nếu không
khai báo đầu ra, engine suy ra kiểu từ biểu thức.

Trigger khóa UPDATE/DELETE version và INSERT/UPDATE/DELETE dependency khi version
APPROVED/EFFECTIVE/RETIRED. Actor FK auth.users vẫn tồn tại trong DB, nhưng app để
NULL; không gọi Supabase Auth. Test fixture chỉ tạo bảng/check/trigger trong
`test_costing_slice` trên localhost; production không có DDL.

## DSL v1

```text
MATERIAL_COST + PACKAGING_COST
$MATERIAL_COST * 1.05
ROUND(@DIRECT_COST / (1 - TARGET_MARGIN), 2)
IF(QUANTITY > 100, PRICE_A, PRICE_B)
NOT IS_EXPORT OR QUANTITY >= 100
IF(IS_EXPORT, "Xuất khẩu", "Nội địa")
```

Identifier ASCII chữ cái đầu, tiếp theo chữ/số/underscore; chuẩn hóa chữ hoa.
Bare symbol tự resolve nếu chỉ có một namespace phù hợp. `$CODE` luôn là CostElement;
`@CODE` luôn là Formula. Nếu code trùng ở hai namespace thì bare symbol bị chặn.
Legacy khác hoa/thường được resolve qua Upper ORM; nhiều bản ghi cùng normalized
code báo mơ hồ. Code legacy không thuộc grammar không được đưa vào token palette.
Tên/mô tả có thể chỉnh sửa; code/output_element là định danh ổn định khi edit.

Số thập phân dùng dấu chấm; không exponent, float, NaN, Infinity. Văn bản dùng nháy
đơn/đôi, chỉ escape nháy và backslash. Boolean TRUE/FALSE; UI hiển thị Có/Không.

Toán tử: `+ - * / % > >= < <= == != AND OR NOT`, dấu ngoặc, unary +/−.
Thứ tự OR → AND → so sánh → +/− → */% → unary. NOT bao quanh phép so sánh.
Không chain comparison như Python; dùng AND cho nhiều điều kiện.

| Hàm | Tham số | Hành vi |
|---|---|---|
| ROUND | 2 | Decimal HALF_UP, scale là hằng số nguyên 0..12 |
| MIN / MAX | 2..20 | Các giá trị số cùng kiểu/đơn vị |
| ABS | 1 | Giá trị tuyệt đối |
| IF | 3 | Điều kiện Boolean; hai nhánh cùng kiểu/đơn vị; tính một nhánh |

Registry tập trung trong functions.py. AND/OR short-circuit. Cả nhánh IF không chạy
vẫn được kiểm tra kiểu và dependency trước khi tính. Không thêm LOOKUP giả hoặc
resolver network/DB vào biểu thức.

## Kiểu, đơn vị, Decimal và giới hạn

Money/Number/Percent/Quantity/Boolean/Text đúng vocabulary CostElement DB.
Kiểu đầu vào lấy từ master data, không từ giá trị text trong form. Tiền tệ, đại
lượng và UoM được so sánh; QUANTITY dùng category dimension nếu chưa có dimension_code,
MONEY mặc định dimension MONEY. NUMBER/PERCENT không có đơn vị có thể kết hợp như
scalar. Cộng/trừ/modulo/so sánh/IF/MIN/MAX cần compatibility. Có thể nhân/chia một
đại lượng với scalar; chia hai đại lượng cùng đơn vị ra NUMBER. Không tự quy đổi
VND/USD hoặc g/kg, không xây symbolic algebra đại lượng phái sinh.

Numeric luôn Decimal, local context precision 38; không Decimal → float. ROUND
HALF_UP công khai là policy DSL v1. Không tự áp rounding_scale/mode của CostElement
khi tính đầu ra; người dùng đặt ROUND trong biểu thức nếu cần. Phép chia lặp vô hạn
làm tròn theo context 38 chữ số, không cam kết rational arithmetic vô hạn.

`settings.FORMULA_LIMITS` có thể override; defaults: length 8000, AST nodes 512,
depth 40, graph nodes 200/depth 40, total execution steps 50000, trace rows 1000,
numeric input digits 64, magnitude 100. Có absolute ceilings để tránh config vô hạn.
Budget dùng chung giữa công thức phụ thuộc và toàn bộ batch chạy test. Diễn giải
vượt giới hạn được rút gọn và có thông báo; không thay kết quả tính.

## Luồng kiến trúc và an toàn

```text
View → Form → Service/Selector → core unmanaged models
Expression → tokenize → precedence parser → immutable Node AST
          → batched dependency snapshot → topo/cycle check → type/unit validator
          → iterative Decimal interpreter → value/type/trace/warnings
```

Không có eval/exec/compile Python trên input, import động, shell/SQL expression,
attribute access, subscript, comprehension hoặc lookup object. AST là JSON data có
dsl_version và SHA256 canonical (không source position), không executable object.
AST stored không được tin trực tiếp: đường chạy hiện tại parse lại expression và
kiểm tra AST allow-list/arity/depth. Evaluator không ORM/I/O. Inputs resolve trước
khi chạy; graph tải theo lớp, references cùng lớp query chung và tránh per-node DB.
Cycle detector/topological evaluator iterative; báo đường vòng bằng mã công thức.
SQL CRUD dùng ORM; text/template escape mặc định, token insertion dùng setRangeText.
CSRF giữ nguyên; GET không mutate hoặc activate.

## Phiên bản và kích hoạt

Create Formula + v1 + AST/dependencies atomic. Edit expression chỉ ở DRAFT/IN_REVIEW.
Tạo phiên bản mới prefill expression/config từ bản mới nhất, cho chỉnh trước khi lưu;
AST/dependencies được dựng lại, actor NULL, status Nháp, số phiên bản max + 1.
Không copy runtime result hoặc nhân đôi test cases vì tests thuộc Formula identity.
Mutations serialize qua company compatibility row hiện có và parent/version locks;
không membership/user/workspace selector. Concurrency test xác minh số version không trùng.

Studio/detail kiểm tra với phiên bản **mới nhất** của dependency, kể cả bản Nháp;
hiển thị version thực tế trong trace. List ghi rõ «Phiên bản mới nhất», không gọi đó
là phiên bản hiệu lực cho Costing. Khi bấm «Kích hoạt phiên bản» có confirmation và:

1. Reload/lock version, đảm bảo editable, active identity và có effective_from.
2. Parse/type/unit/dependency/cycle lại từ source, không tin validation_status cũ.
3. Dependency Formula cần đúng một phiên bản EFFECTIVE bao phủ ngày bắt đầu root.
4. Chạy lại toàn bộ tests đang hoạt động (tối đa 200), cần ít nhất một test và tất cả đạt.
5. Lưu AST/hash/dependency trước khi chuyển EFFECTIVE; toàn bộ atomic.

Không approval/maker-checker flow. Không sửa version cũ để retire vì DB trigger
hiện tại khóa cả mutation trạng thái của version đã chốt. Không tự thêm overlap
policy: nhiều EFFECTIVE bao phủ cùng ngày báo mơ hồ khi resolve. Ngày cuối bao gồm
ngày đó, nhất quán các màn hình effective-dated hiện có.

## Kiểm thử dành cho người dùng

Studio có Kiểm tra công thức / nhập mẫu / Kiểm thử trước khi lưu. Sau khi lưu có
Kiểm thử / Lưu bộ kiểm thử / Chạy bộ kiểm thử đã lưu. Form sinh input theo leaf
CostElement dependency, label tiếng Việt + technical code; không raw JSON.
Giá trị numeric JSON lưu dưới dạng chuỗi, Boolean lưu bool; output expected theo
numeric(24,8) hoặc text (Boolean TRUE/FALSE). Test mới tolerance 0; test legacy chạy
đúng tolerance đã lưu, không invent độ sai số. Có thể ngừng dùng test cũ, không xóa.
Kết quả mong đợi text rỗng chưa được expose để phân biệt với ô không nhập.
Trace hiển thị version tham chiếu, biến/tham số thay thế, bước tính và kết quả;
không lưu runtime result/cost snapshot trong bảng definition.

## URLs và file map

`/formula-engine/formulas/` — list/create/detail/edit; namespace `formula_engine:`.
`/<id>/versions/` — lịch sử phân trang; `versions/create/`,
`versions/<version_id>/`, `edit/`, POST `activate/`.
`/<id>/test/` — kiểm thử bản mới nhất; version detail test đúng bản root đang xem.
`/formula-engine/catalogue/?q=...` — token palette giới hạn 60 biến + 60 formulas.

App mới: ast_nodes, parser, functions, validator, dependencies, evaluator, engine,
limits/errors/constants, selectors/forms/services/views/urls, fixture testing,
unit/integration/concurrency/browser tests. Templates: studio/detail/versions và
partials catalogue/validation/test_fields/test_panel/result/formula_rows/version_rows.
Shared changes: URL, InternalAccess hooks, menu active state, presentation mapping,
formula_value filter, Alpine token insertion, test runner fixtures, generated CSS.

## Verification và giới hạn

Chạy `python manage.py check`, `npm run build:css` và
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1`.
Browser theo hướng dẫn README; screenshots artifacts/screenshots/formula-studio-*.
Tests cover parser/functions/security/limits, type/unit/Decimal/div-zero/missing
input, graph/self/two/three cycles, CRUD/filters/sort/pagination/HTMX/CSRF/scope,
AST/dependency persistence, test save/replay/text/Boolean/tolerance/deactivation,
publish validation/test gate/ambiguity/immutability, clone and concurrency/query counts.

Chưa có Rule Table/LOOKUP/SYSTEM/EXTERNAL resolver, cache Redis, Costing execution,
FX/UoM conversion tự động hoặc arbitrary derived units. Dependency table tham chiếu
Formula identity, không pin dependency FormulaVersion; preview lịch sử dùng các
phiên bản tham chiếu mới nhất và có thể thay đổi. Không tuyên bố đây là replay
Historical Costing Run: future execution snapshot phải pin toàn bộ version/input.
Không chọn dependency cho cả khoảng root, mới kiểm tra tại ngày bắt đầu khi activate.
External DB writes/type master changes có thể làm config đã lưu không còn hợp lệ;
engine kiểm tra lại ở mỗi lần chạy. Chưa có bộ golden Excel nghiệp vụ do chưa được cung cấp.

Kết quả kiểm tra: Django check và Tailwind 4.3.3 production build đạt; full regression
453 tests đạt trên PostgreSQL local, gồm browser. Sau tinh chỉnh vị trí lỗi trong
dependency, toàn bộ 59 tests Formula (unit/integration/concurrency/browser) đạt.
Rà AST source không có calls tới
eval/exec/compile/__import__; parser fuzz 6000 chuỗi không có lỗi ngoài FormulaError.
Smoke GET Supabase trong READ ONLY: các trang đã triển khai trả 200, root 302;
Formula HTMX trả partial và không có session cookie. Không tạo sample Formula
trên Supabase (bảng hiện chưa có bản ghi tại thời điểm kiểm tra).

Vertical slice đề xuất tiếp theo: Rule Table Management + typed LOOKUP resolver;
không được triển khai tự động trong iteration này.
