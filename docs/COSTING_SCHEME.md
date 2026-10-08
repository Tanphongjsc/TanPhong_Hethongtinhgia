# Phương án tính giá thành

Iteration cấu hình, 07/10/2026. URL `/costing/schemes/`, namespace `costing:`.
Single-company, direct access, UI tiếng Việt; không authentication, organization
selector, membership, schema change hoặc business migration.

**Cập nhật iteration Costing Run:** nội dung «SYSTEM chưa có checker» của scope
cũ đã superseded. Các mã trong `engine/registry.py` được kiểm tra kiểu và có resolver;
mã không đăng ký/LOOKUP/EXTERNAL vẫn bị chặn. Config validation không chạy giá/rate;
Run kiểm tra công thức ở đúng ngày tính, không yêu cầu công thức còn hiệu lực sau
ngày Run. Xem [COSTING_RUN.md](COSTING_RUN.md) cho hợp đồng execution.

## Schema thực tế đã kiểm tra READ ONLY

| Model unmanaged ở core | Cấu trúc |
| --- | --- |
| CostingScheme | organization compatibility FK, code/name, purpose/context_scope text, description, is_active, timestamps |
| CostingSchemeVersion | scheme FK, version_no, status, effective_from/to, change_reason, content_hash, nullable created_by/approved_by/approved_at |
| CostingSchemeLine | scheme_version FK, optional cost_element FK, line_code/label/line_type/source_mode, optional formula_version/rule_table FK, resolver/adapter codes, condition_jsonb, override configuration, visibility_scope/cost_scope/display_order/rounding_scale/notes |

Không có SchemeComponent/Assignment/Method entity riêng. Không có Product/SKU/category,
Recipe/BOM, Packaging, Routing, CostPool hoặc AllocationRule FK trên ba bảng.
Không có base_currency/base_uom/base_quantity, required flag, priority/fallback hoặc
price/rate selection policy. Không tạo các controls, JSON keys hoặc resolver codes
giả để mô phỏng những quan hệ này. `purpose/context_scope` là mã nghiệp vụ tự do,
không phải enum/method thực thi. Stored technical codes giữ nguyên.

Nguồn của dòng theo CHECK: SYSTEM, MANUAL, LOOKUP, FORMULA, EXTERNAL.
Loại dòng: INPUT, CALCULATION, SUBTOTAL, OUTPUT, INFO.
Phạm vi hiển thị: INTERNAL, SCREEN, QUOTE, REPORT, ALL.
Phạm vi chi phí reuse CostElement: MANUFACTURING, LANDED, COST_TO_SERVE, CHANNEL,
PRICING, ANALYTICS. Display mappings dùng `master_data/presentation.py`.

Unique: organization + scheme code; scheme + version_no; version + line_code;
version + display_order. Không có unique version + CostElement; nhiều mapping
được lưu, nhưng một dependency cần nguồn rõ ràng sẽ báo lỗi nếu có nhiều nguồn.
Thứ tự là signed integer theo DB, không phải thứ tự tính. UI gợi ý max + 10.
Rounding scale nullable hoặc 0..12. Override minimum <= maximum nếu cả hai có giá trị;
không tự cấm giá trị âm vì DB không quy định. Decimal(24,8), không float.

## CRUD, phiên bản và HTMX

- List/search/filter/sort/pagination ở DB, 25/50/100. Search code/name/description/
  purpose/context_scope; filters purpose/context_scope/status/effective/active.
- List/detail mặc định ghi **phiên bản mới nhất**, không coi đó là phiên bản hiệu lực
  được resolver chọn cho ngày tính giá. Trạng thái bản ghi và hiệu lực theo ngày riêng.
- Header + initial Draft atomic. Lịch sử có filter/sort/pagination.
- Clone toàn bộ dòng, FK FormulaVersion và condition_jsonb sang Draft atomic. Không
  đổi source version, không clone master data, prices/rates/runs/results.
- Lines add/edit/remove qua reusable drawer, validation inline/aria, CSRF, loading,
  success table refresh + editor close + toast OOB. GET remove chỉ xác nhận, POST xóa.
- Source mode/CostElement thay đổi → backend HTMX trả source fields và dropdown
  FormulaVersion phù hợp. Full GET/POST fallback vẫn có; khi không JavaScript, đổi
  source mode rồi gửi form để nhận field tham chiếu cần bổ sung.
- Shared HTMX config `defaultSettleDelay=0`: giao diện không dùng transition cho
  fragment; controls mới được khởi tạo ngay trong swap, tránh bỏ lỡ change event
  khi sort/dependent dropdown được thao tác ngay sau khi bảng/drawer xuất hiện.
- Formula choices: active Formula, EFFECTIVE/VALID version, output phù hợp CE hoặc
  chưa khai báo output, hiệu lực tại ngày kiểm tra; label code/name/version/status.
  Clone form điền sẵn ngày hiệu lực/lý do từ nguồn. Service kiểm tra lại scope,
  active, dated applicability, syntax/type/dimension/unit trước ghi.
- Existing inactive/legacy references giữ được để xem và sửa cấu hình; clone giữ
  nguyên exact references. Validation/activation báo lỗi, không silently thay thế.
- Raw condition_jsonb không expose; giữ nguyên khi edit/clone. Unsupported condition
  có diagnostic và ngăn activation vì chưa có condition schema/validator.

## Kiểm tra cấu hình

`configuration.validate_costing_scheme()` trả errors/warnings/dependencies/order.
`analyze_formula()` dùng `formula_engine.build_plan(publication=True)` cùng parser,
type/unit validator, dependency/cycle detector. **Không gọi Plan.run/evaluate.**

Kiểm tra phiên bản Formula được gán cụ thể tại ngày bắt đầu phương án (hoặc hôm nay
cho Draft chưa đặt ngày). Formula phải EFFECTIVE/VALID, active, cùng company context
nội bộ; declared output CE phải khớp mapping và inferred type/unit phải tương thích.
Currency/UoM lấy từ CE, không giả một tiền tệ chung cho cả Scheme. Không tự quy đổi.

Tất cả leaf CostElements trong graph Formula cần được các dòng phương án cung cấp.
Thiếu/multiple source được báo rõ. Graph giữa dòng Formula và dòng cung cấp CE phát
hiện cycle ngay cả khi từng Formula riêng không có vòng. Trình bày dependency table
và thứ tự topo; không có tiền, giá hoặc numeric calculation trace.

Giới hạn số dòng theo Formula Engine graph_nodes (mặc định 200), graph/expression
budgets dùng lại. Formula plans trùng version/target được cache trong một lần kiểm
tra; lines/references đọc join, không N+1 khi render. Detail chỉ load trang lines,
validation là action riêng và tải tối đa giới hạn + 1.

SYSTEM có registry typed trong Costing Run; EXTERNAL chưa có adapter, LOOKUP chưa
có RuleTable resolver. Cho lưu Draft đúng source-reference CHECK, nhưng báo errors
và không kích hoạt những nguồn chưa kiểm chứng. Không tự tạo selection policies.
RuleTable FK không đồng nghĩa AllocationRule FK; không nhập nhằng hai khái niệm.

## Kích hoạt và tính bất biến

Ngày kết thúc **>** ngày bắt đầu theo CHECK; Draft có thể chưa đặt ngày bắt đầu,
nhưng activation bắt buộc có ngày. Status thực tế: DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/
RETIRED. Chỉ Draft/In review sửa được. Approved/Effective/Retired và lines bất biến
theo trigger DB, thêm service guard trên mọi write/delete. Không fake LOCKED/status.

Kích hoạt POST có confirmation và CSRF, khóa context compatibility cùng convention
Formula Engine → Scheme → Version. Revalidate toàn bộ cấu hình; có errors thì không
đổi trạng thái/hash. Thành công ghi content_hash từ config và chuyển EFFECTIVE.
Không approval workflow; nullable actors để NULL, approved_at không giả phê duyệt.
Header code/purpose/context_scope được cố định sau khi có phiên bản chốt; name/
description/is_active vẫn là master metadata, không chứa kết quả tính.

Parent/context locks tuần tự hóa numbering, clone, line edits và activation trong
ứng dụng. DB uniqueness/trigger là lớp bảo vệ cuối; database errors được map tiếng
Việt. Trigger lines DB hiện kiểm tra NEW parent khi UPDATE, không OLD parent khi
reparent. Service không expose/chuyển parent; giới hạn SQL ngoài ứng dụng vẫn còn.

## Giới hạn và iteration sau

- Không có BOM/Packaging/Routing/Pool/Allocation assignments hoặc price/rate policies
  trong schema này; cần quyết định architecture resolver contract ở iteration sau.
- Nested Formula references đang trỏ Formula identity. Config check chọn EFFECTIVE
  dependency tại ngày đầu, không bảo đảm không có ambiguous/gap mọi ngày trong kỳ.
  FormulaVersion có end hữu hạn phải phủ end phương án; end phương án vô hạn không
  dùng FormulaVersion kết thúc hữu hạn. UI nêu rõ giới hạn kiểm tra tại ngày đầu.
- Không invent overlap/priority/fallback. Nhiều SchemeVersion EFFECTIVE có thể có
  hiệu lực chồng nhau; iteration Run resolver phải có policy xử lý ambiguity.
- Activation chứng nhận cấu hình trong phạm vi kiểm tra, không chứng nhận dữ liệu
  đầu vào runtime/rate availability. Có thể có warnings; errors luôn chặn activation.
- Chưa snapshot toàn graph Formula/CE metadata hoặc dependency versions cho Costing.
  Immutable results cần execution snapshot riêng khi triển khai Run.
- Không SupplierPrice/ResourceRate lookup, BOM expansion, Allocation execution,
  cost roll-up, Formula numeric evaluation, Pricing hoặc Costing Run.

Đề xuất tiếp theo: chốt typed resolver/RuleTable/source contracts và quy tắc chọn
phiên bản theo ngày, cùng tests ambiguity/unit compatibility; sau đó mới Costing Run.

## Files và kiểm thử

Python mới: `apps/costing/constants.py`, `validators.py`, `configuration.py`,
`selectors.py`, `forms.py`, `services.py`, `urls.py`, `testing.py`,
`test_integration.py`, `test_concurrency.py`, `test_browser.py`.
View stub được thay bằng orchestration. Templates: `templates/costing/` (detail,
validation, line form và partials list/version/lines/source/drawer/success/report).
Shared changes: root URLs, access hooks, navigation active state, display mappings,
isolated test runner, base HTMX settle config; generated CSS build,
context/architecture/frontend spec/README.
Không thay core models, settings/auth, dependencies hoặc database schema.

24 file tạo mới: 11 Python được liệt kê ở trên; 12 template gồm `detail.html`,
`line_form.html`, `validation.html` và partials `detail_content.html`,
`lines_table.html`, `line_editor.html`, `line_form_content.html`, `line_saved.html`,
`scheme_rows.html`, `source_fields.html`, `validation.html`, `version_rows.html`;
cùng tài liệu này.

13 file sửa: `apps/costing/views.py`, `config/urls.py`,
`apps/master_data/access.py`, `navigation.py`, `context_processors.py`,
`presentation.py`, `testing.py`; `templates/base/base.html`,
`static/css/app.css` (generated); `docs/00_AI_CONTEXT.md`,
`docs/03_SYSTEM_ARCHITECTURE.md`, `docs/FRONTEND_IMPLEMENTATION_SPEC.md`, `README.md`.
Không xóa file. Các file đã thay đổi từ iteration trước được giữ nguyên.

Chạy Django: `env\Scripts\python.exe manage.py runserver`.
Tailwind watcher: `npm run dev:css`; production build: `npm run build:css`.
Tests: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.costing`.
Browser: `COSTING_BROWSER_TESTS=1`, `PLAYWRIGHT_BROWSERS_PATH=artifacts/playwright`.
Fixtures CHECK/unique/triggers chỉ tạo trong `127.0.0.1 / test_costing_slice`, tuyệt
đối không chạy test mutations/schema fixtures trên Supabase.

Kết quả ngày 07/10/2026:

- `env\Scripts\python.exe manage.py check`: không có lỗi.
- `npm run build:css`: thành công, Tailwind 4.3.3; không nâng version hoặc thêm dependency.
- Targeted `apps.costing` + browser BOM/Routing: **53/53 PASS** (52,262 giây).
- Full suite `scripts/test.ps1 --verbosity=1`, browser được bật: **505/505 PASS**
  (140,935 giây), không skip. Có CRUD, DB constraints/triggers, clone rollback,
  concurrent numbering/collision, missing/cyclic/ambiguous dependency, typed/unit
  Formula validation, CSRF, query counts, HTMX drawer/dropdowns và desktop/mobile.
- Supabase chỉ kiểm tra read-only: mappings/constraints/triggers khớp; root redirect,
  schemes list/create/HTMX và các trang CostElement/Formula trả response đúng,
  không cần session đăng nhập. Không tạo hay cập nhật dữ liệu production để test.
- Review UI tiếng Việt, focus/drawer/Escape, responsive và Tailwind literal classes;
  không có Formula evaluation hoặc runtime price/rate queries trong configuration.

Log kiểm thử: `artifacts/scheme-targeted-tests.log`, `artifacts/scheme-full-tests.log`.
Ảnh kiểm tra: `artifacts/screenshots/scheme-detail-desktop.png`,
`artifacts/screenshots/scheme-detail-mobile.png`.
