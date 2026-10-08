# Pricing Foundation và dọn Approval/Audit — 08/10/2026

Phạm vi hoàn thành: Kênh bán, Quy tắc phí kênh, Quy tắc thuế, Tỷ giá.
Không có Pricing Scenario, giá bán, margin, waterfall, so sánh kịch bản hoặc API tỷ giá ngoài.
Code/database giữ tiếng Anh; nội dung UI bằng tiếng Việt. Không thêm dependency.

## Runtime và database compatibility

- Xóa hai app khung `apps/workflow/`, `apps/audit/` và đăng ký trong settings.
  Chúng chưa có URL, view nghiệp vụ, service hoặc consumer đang chạy.
- Bỏ section Workflow, Approval Inbox, My Requests và business Audit Log khỏi navigation.
  Giữ Version History placeholder và các màn hình lịch sử phiên bản thực tế trong từng module.
  Overrides placeholder chuyển sang Quản trị; khả năng nhập điều chỉnh khi chạy Costing,
  giới hạn/lý do điều chỉnh và trace/snapshot vẫn giữ.
- Gỡ `approval_policy_code` khỏi form/allow-list ghi/template dòng phương án. Giá trị cũ
  vẫn nằm trong model, bản sao chính xác và config hash để không mất tương thích lịch sử.
  Field không được dùng để yêu cầu duyệt. Clone không thay đổi definition của version gốc.
- Không xóa/sửa core models, bảng, enum, FK, constraint hoặc trigger. `ApprovalRequest`,
  `ApprovalAction`, `AuditEvent`, `CostingOverride`, các field actor chỉ là mappings cũ.
  Không query hoặc tạo Approval/AuditEvent trong runtime. Không fake user UUID.
- Giữ lifecycle, legacy APPROVED/IN_REVIEW display và DB immutability guards; không có
  Submit/Approve/Reject action. Formula/Scheme tiếp tục kích hoạt trực tiếp qua validation/test gate.
- Giữ toàn bộ BOM/Packaging/Routing/Formula/Scheme versions, effective resolution, Supplier Price,
  Resource Rate, Costing Run history, snapshot/hash, source references, explain trace, timestamps,
  trace_id và technical error/server logging. “Audit tích hợp” trong báo cáo DEMO là đối soát kỹ thuật,
  không phải tính năng theo dõi thao tác nhân sự bị loại bỏ.
- No authentication/account/role/session/membership hoặc organization UI. Compatibility FK dùng
  `get_default_organization()`/Workspace/InternalAccess hiện có, không tạo company flow mới.

## Schema thực tế đã đối chiếu read-only với PostgreSQL

Tất cả model tại `apps/core/models.py`, `managed=False`.

| Model | Các trường nghiệp vụ | Quan hệ / constraint |
| --- | --- | --- |
| Channel | code, name, channel_type, platform_code, market_code, seller_type, default_currency_code, is_active, created_at, updated_at | organization FK nội bộ, Currency FK tùy chọn; unique organization+code; updated_at trigger |
| ChannelFeeRule | channel, product_category, sku, fee_type, fee_base, rate, fixed_amount, currency_code, cap_amount, floor_amount, refundable_ratio, tax_inclusive, priority, effective_from, effective_to, status, source_reference, created_by, created_at | Channel bắt buộc; category/SKU/Currency tùy chọn; không code/name/UoM/line/version |
| TaxRule | jurisdiction_code, tax_type, tax_class_code, seller_type, transaction_type, rate, fixed_amount, currency_code, tax_base, recoverable_ratio, inclusive, priority, effective_from, effective_to, status, source_reference, created_by, created_at | Currency tùy chọn, organization FK nội bộ; không Channel/Product/SKU FK hoặc code/name/line/version |
| FxRate | rate_type, from_currency_code, to_currency_code, rate, effective_at, valid_to, source_name, source_reference, status, created_at | Hai Currency FK; organization FK nội bộ; hiệu lực là timestamptz, không phải date |

Channel type CHECK: B2B / RETAIL / ECOMMERCE / EXPORT / D2C / OTHER.
Các mã fee_type, fee_base, tax_type, tax_base, rate_type, jurisdiction/seller/transaction
là text tự do, không có CHECK enum; form không tự thêm enum. Mapping quen thuộc chỉ là
presentation, không hạn chế stored values hoặc hứa hỗ trợ công thức tính. Mã tùy chỉnh
được giữ như technical code. Không có fee/tax rule line hoặc version table.

DB CHECK:

- Fee/tax rate nullable trong [0,1], refundable/recoverable ratio trong [0,1]; phải có
  ít nhất rate hoặc fixed_amount, có thể có cả hai. Fee cap >= floor nếu cả hai có giá trị.
- effective_to NULL hoặc **>** effective_from; FX valid_to NULL hoặc **>** effective_at.
- FX from != to, rate > 0. Fee/Tax statuses có DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/RETIRED;
  FX không có IN_REVIEW. Không có immutable/overlap trigger cho ba bảng này.
- Không có composite unique trên fee/tax/FX; không tự thêm constraint hoặc cấm duplicate.
  Channel là bảng duy nhất trong scope có business unique.

Decimal DB: rate/ratios phí-thuế (12,8); số tiền (24,8); FX rate (24,12).
UI nhập phần trăm tối đa 6 chữ số thập phân; `8.123456` → `Decimal('0.08123456')`.
Chuyển đổi đúng một lần trong form; service nhận tỷ lệ phần số, không chia tiếp.
Hiển thị dùng `format_number`/`format_percent` tiếng Việt, không giảm precision lưu trữ.

## Features và validation

Các route trong namespace `pricing:`:

| Danh mục | List | Các route còn lại |
| --- | --- | --- |
| Kênh bán | `/pricing/channels/` | create/, `<id>/`, `<id>/edit/` |
| Quy tắc phí kênh | `/pricing/channel-fee-rules/` | create/, `<id>/`, `<id>/edit/`, `<id>/close/` |
| Quy tắc thuế | `/pricing/tax-rules/` | create/, `<id>/`, `<id>/edit/`, `<id>/close/` |
| Tỷ giá | `/pricing/fx-rates/` | create/, `<id>/`, `<id>/edit/`, `<id>/close/` |

Mỗi module có list/search/filter/sort/pagination 25/50/100, create/detail/edit,
empty state, field errors/aria, toast. HTMX partial table giữ query URL, debounce 400ms,
history restore trả full page; form full POST có CSRF và HTMX fallback. Sidebar active
đúng cả trang kết thúc hiệu lực. Pricing Scenario/Compare vẫn disabled placeholder.
Không hard delete, không raw JSON hoặc organization/actor fields trên UI.

- Code channel/mã nghiệp vụ trim + uppercase; name/source text trim, optional blank→NULL.
- Channel name/code/type bắt buộc, duplicate code friendly; active Currency dropdown.
- Fee chọn Channel, tùy chọn nhóm/SKU; SKU phải thuộc nhóm đã chọn. Dropdown chỉ active
  khi thêm, giữ reference inactive cũ khi sửa/đọc lịch sử. Service refresh/lock references
  và kiểm tra compatibility scope; không tin POST FK hoặc actor/organization do client gửi.
- Rate/ratios 0–100% trên UI; fixed/floor/cap >= 0 theo yêu cầu validation ứng dụng,
  dù DB chưa có CHECK không âm. Giá trị tiền yêu cầu Currency để đơn vị rõ ràng.
- Priority dùng đúng signed int32 range; không tự cấm mức âm mà DB cho phép.
- Inclusive/exclusive là select có nhãn rõ “Giá đã/chưa bao gồm thuế”; không suy đoán
  thứ tự Fee→Tax, không hard-code VAT, kênh/sàn hoặc tiền tệ.
- FX chiều rõ `1 USD = 26.000 VND`, tối đa 12 số thập phân, không float, không tự đảo chiều.
- Service atomic, allow-list, row lock, database exception→Vietnamese validation;
  lỗi bất ngờ đi qua error middleware/trace logging hiện có.

## Lịch sử và khoảng hiệu lực

Khoảng Pricing là **[start, end)** theo BRULE-001 canonical: đầu bao gồm, cuối không bao gồm.
Hiển thị ngày dd/mm/yyyy; FX hiển thị local datetime Asia/Ho_Chi_Minh, lưu timezone-aware.
Quy ước này độc lập với UI upstream cũ dùng inclusive end date; không thay đổi Costing resolvers.
Trạng thái bản ghi và hiệu lực theo thời gian hiển thị riêng; Nháp không tự trở thành effective.

Application guardrail cho ba bảng rule/FX: mới Nháp, chỉ sửa Nháp, có thể chọn Đang hiệu lực
ngay trong form sau validation. Không có phê duyệt. Legacy/Effective/Retired chỉ đọc definition;
thay mức hoặc phạm vi bằng row mới. Đây là bảo vệ application, không có DB trigger mới.
Thao tác riêng **Kết thúc hiệu lực** chỉ đặt end tương lai, > start, cho EFFECTIVE chưa có end;
không đổi rate/scope/status/đầu kỳ, không mở lại/kéo dài kỳ đã đóng hoặc sửa lịch sử quá khứ.
Row lock chống hai lần đóng đồng thời. Sau đó thêm row mới bắt đầu đúng end của row cũ.
Không tự đóng row khác, auto-retire hoặc invent overlap policy.

## Selectors chuẩn bị cho Scenario

`get_applicable_channel_fee_rules(organization, channel, on_date, sku=None,
product_category=None, currency=None)` lấy EFFECTIVE đúng ngày/kênh, category/SKU
NULL là wildcard. Khi có SKU, category lấy từ Product; thiếu context thì chỉ lấy
scope tổng quát, không áp dụng nhầm rule cụ thể. Currency NULL áp dụng chung;
có currency thì lấy NULL hoặc đúng mã. Trả **toàn bộ candidates** theo priority DESC, PK,
không chọn winner/deduplicate/cộng phí hoặc suy đoán thứ tự tính.

`get_applicable_tax_rules(organization, jurisdiction_code, on_date, tax_type=None,
tax_class_code=None, seller_type=None, transaction_type=None, currency=None)` dùng
scope text chính xác; NULL wildcard. Không giả Product/Channel FK mà schema không có.
Caller phải truyền context rõ; tax_type bỏ trống trả các loại phù hợp để engine sau xử lý.

`get_effective_fx_rate(organization, from_currency, to_currency, rate_type,
effective_at)` yêu cầu datetime aware, đúng chiều/loại/trạng thái/khoảng hiệu lực.
Trả đúng một FxRate; không có→MISSING_FX, nhiều→AMBIGUOUS_FX. Không chọn latest,
đảo tỷ giá, suy đoán múi giờ hoặc gọi mạng. Không đọc current FX từ historical Costing.

ORM search/filter/sort/paginate ở DB, select_related đúng FK; chỉ decorate page hiện tại.
Tests so sánh query count khi tăng số row và kiểm tra LIMIT; không N+1.

## Dữ liệu demo và kiểm thử

Reuse dataset DEMO Costing hiện có. Pricing test fixtures chỉ ở DB localhost cô lập:
kênh D2C mẫu, phí 8%, thuế 10%, USD→VND 26000.123456789012. Đây là số minh họa,
không là chính sách thực tế/pháp lý. Không seed các mức này lên Supabase hoặc reset demo cũ.
Đã inspect real Pricing tables: ban đầu đều trống. Không thêm dữ liệu Pricing production.

Lệnh:

```powershell
env\Scripts\python.exe manage.py check
npm run build:css
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 apps.pricing --verbosity=1
$env:COSTING_BROWSER_TESTS='1'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path (Get-Location).Path 'artifacts/playwright'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1 --verbosity=1
env\Scripts\python.exe manage.py verify_costing_demo --report artifacts/pricing-after-foundation.json
```

Test runner chỉ tạo unmanaged fixture tables/CHECKs trong guarded localhost `test_costing_slice`.
Không business migration và không DDL Supabase. Fixtures mới reuse Channel đã có từ Run.
Coverage: CRUD/full/partial/query state/scope/negative/Decimal/CSRF/error mapping/legacy status,
inactive reference/history/close-period/selectors/query counts, browser CRUD/HTMX/mobile,
approval cleanup, exact clone metadata và Golden không đổi sau Pricing config.

Golden độc lập 10 hộp ngày 07/10/2026: MATERIAL 260.000, PACKAGING 150.000,
RESOURCE 120.000, DIRECT 530.000, OVERHEAD 53.000, FULL **583.000 VND**, UNIT **58.300 VND**.
Tương lai 01/11/2026: FULL 647.000 VND. Snapshot, breakdown và fingerprint lịch sử giữ nguyên.
Evidence: `artifacts/pricing-before-cleanup.json`, `pricing-cleanup-regression.log`,
`pricing-after-foundation.json`, `pricing-full-tests.log`, screenshots `pricing-*.png`.

## File manifest

Tạo: `apps/pricing/{constants,validators,forms,services,selectors,presentation,urls,testing,test_browser}.py`,
`templates/pricing/{list,form,detail}.html`, `templates/pricing/partials/{rows,detail_content}.html`,
`docs/PRICING_FOUNDATION.md`.

Sửa: `apps/pricing/{views,tests}.py`, `config/{settings,urls}.py`,
`apps/master_data/{access,navigation,presentation,context_processors,testing}.py`,
`apps/costing/{constants,forms,validators}.py`, `templates/costing/partials/lines_table.html`,
`README.md`, `docs/{00_AI_CONTEXT,01_REQUIREMENTS_SCOPE,02_BUSINESS_DOMAIN,03_SYSTEM_ARCHITECTURE,04_ENGINEERING_GUIDE,05_QA_TESTING,FRONTEND_IMPLEMENTATION_SPEC}.md`.
`static/css/app.css` chỉ được tạo lại qua build Tailwind.

Xóa 14 source files: mỗi `apps/workflow/` và `apps/audit/` gồm
`__init__.py`, `admin.py`, `apps.py`, `models.py`, `tests.py`, `views.py`, `migrations/__init__.py`.

## Giới hạn và bước kế tiếp

- Không calculation engine Pricing, Fee/Tax precedence/specificity/tie policy hoặc tiered formula;
  candidates không phải kết quả phí/thuế. Những quyết định này thuộc iteration Scenario.
- DB chưa ngăn overlap; form không tự thêm policy. FX fail rõ khi overlap, cần đóng kỳ đúng.
- Bảo vệ definition đã chốt chỉ ở application service; SQL ngoài ứng dụng vẫn theo DB hiện có.
- Không version table, không giả mã/tên rule, Tax FK scope hoặc fee UoM không có trong schema.
- Lịch sử phiên bản tổng hợp vẫn placeholder như trước; histories từng module hoạt động.
- Không real fee/tax/FX policy hay API ngoài; người nghiệp vụ nhập dữ liệu thực.

Bước tiếp theo đề xuất: Pricing Scenario dựa trên immutable Costing Run và snapshot các
rule/FX được chọn, sau khi xác định rõ code/basis hỗ trợ, ưu tiên và thứ tự áp dụng.
Iteration này dừng tại Foundation.

## Báo cáo nghiệm thu

| Mục | Kết quả cuối |
| --- | --- |
| 1. Approval code đã loại bỏ | App workflow khung, đăng ký settings, section/menu phê duyệt, field chính sách duyệt trong form/POST allow-list/UI phương án. Không có Approval service/URL runtime khác cần xóa. |
| 2. Audit code đã loại bỏ | App audit khung, đăng ký settings và menu business Audit Log. Technical logs và DEMO audit đối soát giữ nguyên. |
| 3. Files deleted | 14 source files, liệt kê theo từng app trong File manifest. |
| 4. Files modified | Config/access/navigation/context/fixtures, Costing form allow-list/template, Pricing views/tests, README và 7 canonical docs; generated CSS qua build. Xem File manifest. |
| 5. DB compatibility | Core models/managed=False/FK/tables/triggers/actor nullable giữ nguyên; không migrations/DDL/Supabase Auth. |
| 6. Version/history | BOM/Packaging/Routing/Formula/Scheme versions, clone/activation/immutability, giá mua/rate history, Costing Run history giữ nguyên. |
| 7. Costing trace/snapshot | Snapshot/hash/source references/breakdown/explain/trace_id giữ nguyên; historical fingerprint không đổi. |
| 8. Cleanup regression | 155/155 Formula/Costing/DEMO integration tests PASS trước khi implement Pricing. |
| 9. Sales Channel | Channel hiện có; CRUD, active Currency, enum CHECK thật, mã unique, search/filter/sort/pagination/HTMX/tiếng Việt. |
| 10. Channel Fee | ChannelFeeRule hiện có; tỷ lệ/số tiền/trần-sàn/hoàn/bao gồm thuế, phạm vi category/SKU, dates/priority/source. Không code/name/UoM giả. |
| 11. Tax Rule | TaxRule hiện có; khu vực/loại/nhóm thuế/người bán/giao dịch, %/fixed/khấu trừ, inclusive/exclusive, dates/priority/source. |
| 12. FX | FxRate hiện có; cặp Currency đúng chiều, Decimal(24,12), loại/nguồn/aware datetime, CRUD và lịch sử. Không API ngoài. |
| 13. Effective date | Pricing [start,end), DB end>start. Chỉ sửa Nháp; kích hoạt trực tiếp; bản chốt chỉ đọc definition. Đóng kỳ tương lai qua action riêng, không ghi đè mức/phạm vi cũ. |
| 14. Selectors | Fee/Tax trả candidates đúng scope/ngày/currency; FX yêu cầu đúng một row và báo thiếu/mơ hồ. Không selling-price computation. |
| 15. Demo Pricing | Dữ liệu minh họa trong isolated test fixtures; không seed phí/thuế/tỷ giá giả vào Supabase. DEMO Costing cũ không reset/nhân bản. |
| 16. Tests executed | `manage.py check`, Tailwind build, cleanup gate, full suite với Playwright, targeted Pricing cuối, real Supabase DEMO verification và read-only Pricing smoke. |
| 17. Passed | Full **628/628**, 191,575 giây; targeted Pricing cuối **43/43**, 9,815 giây; cleanup **155/155**, 15,190 giây. Browser bật, không skip. |
| 18. Failed | **0** trong full suite và targeted cuối. Assertion doctype/tên nút trong lượt test đầu đã sửa và chạy lại thành công. |
| 19. Golden trước/sau | FULL **583.000 VND**, UNIT **58.300 VND/hộp**; breakdown và dữ liệu tương lai **647.000 VND** giống hệt. Historical fingerprint `b317df1c48d905f093089009a85fd0ad07c451d274a773ddb1996c799b89f0f2` không đổi. Supabase 22 module cũ và 12 request Pricing mới PASS/200. |
| 20. Tailwind build | **PASS**, local Tailwind 4.3.3 production build; không thêm/upgrade dependency. Django check PASS, không issue. |
| 21. Known limitations | Không DB overlap/immutability mới; free business codes chưa là calculation contract; Fee/Tax selection/ordering và Scenario thuộc iteration tiếp theo. Menu lịch sử tổng hợp còn placeholder như trước, histories từng module hoạt động. |

**READY FOR PRICING SCENARIO** — Foundation và regression gates đã PASS.
Chưa triển khai Pricing Scenario; các quyết định calculation/priority/basis cần được
chốt trong scope của iteration tiếp theo trước khi thực thi giá bán.
