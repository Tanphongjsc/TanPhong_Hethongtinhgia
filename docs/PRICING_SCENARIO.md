# Kịch bản giá bán — 08/10/2026

Phạm vi: Pricing Scenario, solver Decimal, cấu thành giá bán, snapshots/trace và
Golden. Không so sánh kịch bản, publish, approval, audit nhân sự, Auth hoặc company UI.
Không thay đổi schema/migrations/core models. Không thêm dependency.

## 1. Schema thực tế

`apps.core.models.PriceScenario`, unmanaged, bảng `costing.price_scenario`.

- id; organization FK tương thích nội bộ; code/name; base_run FK CostingRun;
  channel FK tùy chọn trong DB nhưng bắt buộc cho tính giá; currency_code FK Currency.
- pricing_method; target_margin/target_markup numeric(18,10); target_profit_per_unit,
  minimum_price/suggested_price/final_price numeric(24,8).
- scenario_context_jsonb/output_snapshot_jsonb; status; valid_from/valid_to;
  created_at; created_by/approved_by/approved_at nullable.
- Unique organization+code. Margin [-1,1), markup >= -1; end >= start nếu có cả hai.
- CHECK phương pháp: MARGIN/MARKUP/PROFIT_PER_UNIT/RULE_BASED/MANUAL_APPROVED.
  Runtime chỉ dùng ba phương pháp đầu. Không dùng mã MANUAL_APPROVED để đưa duyệt trở lại.
- CHECK lifecycle: DRAFT/CALCULATED/IN_REVIEW/APPROVED/EXPIRED/CANCELLED.
  Runtime tạo DRAFT → CALCULATED; không invent FAILED/LOCKED cho bảng này.
  Lỗi tính giữ DRAFT, lưu diagnostics/trace_id trong JSON; có thể sửa hoặc thử lại.
- Không có Product/SKU FK trực tiếp, pricing_date column, quantity column, version,
  result lines, trace/snapshot table riêng hoặc immutable trigger. Product/SKU lấy qua
  base_run; ngày/context được lưu có cấu trúc trong JSON, lines/trace trong output JSON.
  valid_from/valid_to là hiệu lực kịch bản, không bị dùng thay ngày định giá.
- Actor NULL. Không query auth.users/OrganizationMember hoặc viết Approval/AuditEvent.

## 2. Lifecycle và nguồn giá thành

`/pricing/scenarios/`: list/search/filter/sort/pagination 25/50/100, tạo Nháp,
chi tiết, sửa Nháp, tính giá và nhân bản thành kịch bản mới. Các tên URL
`pricing:scenario_list/create/detail/edit/calculate/options`.

Costing Run hợp lệ là **LOCKED**, có persisted full_cost >= 0, quantity > 0,
per_unit Decimal hợp lệ và có result lines. Không có COMPLETED trong enum hiện tại.
Chọn Product → SKU → 100 Run gần nhất đúng scope; giữ Run cũ đã chọn trong scope.
Label gồm SKU/sản phẩm, ngày, giá đơn vị, phương án và tham chiếu Run.
Pricing chỉ đọc per_unit đã lưu; không chạy lại Costing/BOM/SupplierPrice/ResourceRate.
Giá tính cho **một đơn vị quantity_uom của Costing Run**, không tự đổi sang sales_uom.

CALCULATED chỉ đọc ở application; POST sửa bị chặn, GET sửa về detail. Calculate
lặp lại trả cùng snapshot, không resolve master lại. Muốn đổi input hoặc tính theo
rule mới: nhân bản, nhập mã mới, lưu Nháp và tính. Không giả lập version table.

## 3. Chính sách tính được xác nhận trong phiên làm việc

Người dùng xác nhận margin trên giá khách trả, markup trên giá vốn và policy phí
phía dưới; giao agent lựa chọn policy thuế/FX phù hợp. Policy v1 lưu trong snapshot.

Đặt P = giá khách trả gồm thuế, C = giá vốn đơn vị quy đổi sang tiền bán,
S = giá bán trước thuế, T = thuế bán hàng, F = phí kênh.

```text
P = S × (1 + tổng thuế suất) + tổng thuế cố định
T = P − S
F_i(P) = min(cap_i, max(floor_i, rate_i × P + fixed_i))
Lợi nhuận = P − ΣF_i − ΣT_i − C
Margin = lợi nhuận / P
Markup = lợi nhuận / C
```

- MARGIN giải lợi nhuận = target_margin × P; MARKUP giải lợi nhuận = target_markup × C;
  PROFIT_PER_UNIT giải lợi nhuận = target_profit_per_unit. UI nhập %, DB giữ phần số.
  Không cho nhập đồng thời nhiều mục tiêu. Targetprofit/minimum có đơn vị tiền bán.
- Phí % trên P, fixed/sàn/trần trên một đơn vị đầu ra. Chỉ hỗ trợ fee_base LIST_PRICE.
  Phí theo đơn hàng, discount/payment/payout bases khác bị chặn, không tự chia số lượng.
- Nhóm theo fee_type; SKU > category > general, rồi priority DESC. Hòa ở mức cao nhất
  báo AMBIGUOUS_RULE; các loại khác nhau cộng, mỗi loại một dòng riêng. Snapshot ghi
  các candidate bị bỏ và lý do thứ hạng. Priority không được dùng để bịa thứ tự tính.
- Chỉ hỗ trợ số tiền phí đã gồm thuế (`tax_inclusive=True`) hoặc phí bằng 0.
  Phí chưa gồm thuế cần mô hình thuế trên phí; engine báo UNSUPPORTED_FEE_TAX.
  refundable_ratio khác 0 bị chặn, không tự giảm nghĩa vụ phí.
- Tax mode được chọn rõ REQUIRED hoặc NONE. REQUIRED mặc định; thiếu rule là lỗi.
  NONE ghi cảnh báo/snapshot rõ, không phải fallback khi thiếu rule.
- Khu vực có thể gợi ý từ Channel.market_code; người lập xác nhận/nhập rõ.
  Tax class từ Product, seller_type từ Channel, transaction_type nhập trong context.
  NULL scope là wildcard theo selectors Foundation.
- Nhóm theo tax_type, scope cụ thể nhiều field hơn rồi priority DESC; hòa báo lỗi.
  Các loại thuế tính **song song trên cùng S**, không tax-on-tax, không trừ phí khỏi basis.
  Hỗ trợ tax_base SELLING_PRICE/LIST_PRICE theo nghĩa giá trước thuế chung của policy này.
  Quy tắc basis khác, recoverable_ratio khác 0 hoặc hỗn hợp inclusive/exclusive bị chặn.
- Với inclusive, P là giá niêm yết và S được tách ngược. Với exclusive, S là giá niêm
  yết, thêm thuế để có P. Margin luôn chia P trong cả hai trường hợp.
- Không hard-code tỷ lệ thuế, tên thuế VAT, tiền tệ hoặc FX trong engine.

## 4. Solver, precision và FX

Solver chia miền giá theo các breakpoint sàn/trần phí, giải phương trình tuyến tính
trong từng miền, kiểm tra nghiệm thuộc miền và mẫu số > 0. Không vòng lặp hội tụ
tùy tiện; tối đa 200 candidate rule mỗi loại truy vấn. Nếu không có nghiệm: lỗi rõ ràng.
minimum_price nâng giá sau giải; recompute toàn bộ fees/taxes/profit/actual ratios.

Decimal precision 50 cho trung gian. Giá/thành phần tiền lưu 8 chữ số thập phân
ROUND_HALF_EVEN, tỷ lệ thực tế 10 chữ số. Không có commercial rounding tự đặt.
Lợi nhuận tính lại từ các thành phần đã làm tròn để waterfall reconcile chính xác.
Trace giữ trung gian đầy đủ; UI diễn giải hiển thị tối đa 8 chữ số.

FX dùng selector Foundation, đúng chiều nguồn → tiền bán, nhân rate. Loại tỷ giá
do người lập nhập, thời điểm 00:00 ngày định giá Asia/Ho_Chi_Minh. Không inverse,
internet API, latest rate hoặc fallback 1. Cùng tiền tệ không query FX.
Tiền cố định/sàn/trần phí/thuế khác currency được quy đổi qua cùng resolver và snapshot.
Thiếu/trùng/zero FX chặn tính. Hiệu lực Pricing **[start,end)**.

## 5. Persistence, snapshot, trace và lịch sử

- Save allow-list + normalization + service validation + atomic + row locks.
  Không nhận actor/organization/status/output/suggested_price từ POST.
- Calculate atomic, REPEATABLE READ ở transaction gốc, khóa scenario, retry serialization/
  deadlock tối đa ba lần. Không lock/write Costing Run. Hai calculate đồng thời không
  tạo hai kết quả; lần sau đọc CALCULATED cũ. DB errors không lộ SQL.
- Context JSON schema 1: pricing_date, tax_mode, jurisdiction_code, transaction_type,
  fx_rate_type và display labels. Output JSON: policy/input/costing reference & unit result,
  snapshot hash Costing, Channel/Currency/Product/rule/FX sources đủ fields, result components,
  waterfall, trace, warnings, trace_id/calculated_at và SHA-256 toàn bộ output trừ hash.
- Detail/list lịch sử lấy display/result/trace từ JSON đã lưu; không query current Fee/Tax/FX
  để dựng lại kết quả. Link Costing dùng tham chiếu immutable, không mutate Costing.
- Không overwrite kết quả cũ. Application immutability chưa bảo vệ được SQL viết trực tiếp,
  vì không sửa trigger/schema trong iteration này. Snapshot/hash không phải chữ ký chống giả mạo.
- Technical exceptions log scenario_id/trace_id; UI báo tiếng Việt và mã tham chiếu.

## 6. UI / reuse / queries

Foundation list/filter/table/pagination/search 400ms, form sections/errors, status/toast,
Alpine shell và HTMX query state được reuse. Product/SKU và Channel dependent fields
do backend query. Normal GET và history restore trả full page, HTMX trả partial.
POST CSRF bắt buộc; calculate chỉ POST. HTMX refresh waterfall tại chỗ, disable submit
khi pending và indicator. Forms giữ input/errors; không raw JSON/FK selection ID.
Không thêm English display labels, auth hoặc company controls.

Read queryset join base_run, defer snapshot lớn của Run; dropdown giới hạn Run và chỉ lấy
fields dùng để render. Search/filter/sort/pagination DB-side. Rule selectors select_related;
list query count không tăng khi tăng từ 1 lên 21 scenario. Historical detail không query
Fee/Tax/FX/OrganizationMember. Shared app.js sửa history restore input từ URL vì cache
HTMX lưu HTML attribute khác DOM value; browser test phủ bug này.

## 7. Golden Pricing độc lập

Lệnh reuse Costing Run ngày 07/10/2026 đã khóa; **không** tự chạy lại Costing:

```powershell
python manage.py verify_pricing_demo --report artifacts/pricing-scenario-golden.json
```

Seed idempotent DEMO_DIRECT, 2 phí, thuế và hai kịch bản. Khóa DEMO channel để serialize
seed cùng dataset; không reset hoặc ghi đè dữ liệu khác định nghĩa. Phí/thuế tương lai
bắt đầu 01/11, không sửa rule lịch sử. Mọi con số DEMO là giả định kiểm thử, không thuế suất
hoặc giá thị trường khuyến nghị.

Golden ngày 08/10: C = 58.300 VND/hộp; phí hoa hồng 5% P, phí thanh toán 1.000 VND/hộp;
thuế 10% inclusive; margin 20%. Không FX vì cùng VND.

Tính tay: S=P/1,1; `P/1,1 − 0,05P − 1.000 − 58.300 = 0,20P`;
`P = 2.609.200 / 29`. Expected cố định trong test, không lấy engine output làm expected.

| Chỉ tiêu | Expected | Actual Supabase | Delta |
| --- | ---: | ---: | ---: |
| Giá vốn | 58.300 | 58.300 | 0 |
| Tổng phí | 5.498,62068966 | 5.498,62068966 | 0 |
| Thuế | 8.179,31034483 | 8.179,31034483 | 0 |
| Lợi nhuận | 17.994,48275861 | 17.994,48275861 | 0 |
| Giá khách trả | 89.972,41379310 | 89.972,41379310 | 0 |
| Biên lợi nhuận | 20% | 20% | 0 |

Ngày 01/11 vẫn dùng **cùng persisted C**, chỉ đổi phí 6% và thuế 11%:
`P = 329.115.000 / 3.557 = 92.526,00506044`; phí 6.551,56030363;
thuế 9.169,24374473; lợi nhuận 18.505,20101208, margin 20%. Cả 6 delta = 0.
Golden snapshot cũ không đổi sau seed future. Fingerprint Run header + toàn bộ lines
trước/sau Pricing: `b317df1c48d905f093089009a85fd0ad07c451d274a773ddb1996c799b89f0f2`.
Golden snapshot Pricing: `2165544f1417bbffbb5a5961f1424abdf7da4e992c2e51c29bb6bc26a7070b43`.

## 8. Files

Created:

- apps/pricing/scenario_constants.py, scenario_selectors.py, scenario_validators.py,
  scenario_forms.py, scenario_services.py, scenario_presentation.py, scenario_views.py.
- apps/pricing/engine/__init__.py, context.py, solver.py, resolvers.py, runner.py.
- apps/pricing/demo_scenario.py; management/__init__.py, management/commands/__init__.py,
  management/commands/verify_pricing_demo.py.
- apps/pricing/test_scenario_solver.py, test_scenarios.py, test_scenario_browser.py,
  test_scenario_concurrency.py.
- templates/pricing/scenarios/list.html, form.html, detail.html;
  partials/form_content.html, dependent_fields.html, rows.html, detail_content.html.
- docs/PRICING_SCENARIO.md.

Modified:

- apps/pricing/urls.py, selectors.py, testing.py.
- apps/master_data/access.py, navigation.py, context_processors.py, presentation.py.
- static/js/app.js; generated static/css/app.css qua build.
- docs/00_AI_CONTEXT.md, 01_REQUIREMENTS_SCOPE.md, 02_BUSINESS_DOMAIN.md,
  03_SYSTEM_ARCHITECTURE.md, 04_ENGINEERING_GUIDE.md, 05_QA_TESTING.md,
  FRONTEND_IMPLEMENTATION_SPEC.md; README.md.

Không xóa file/dependency, không sửa config/schema/core mappings/Costing engine.

## 9. Validation và evidence

Tests: solver margin/markup/profit, fixed/%/multiple fees, floor/cap/minimum,
inclusive/exclusive/parallel taxes, invalid denominator, Decimal/rounding/reconcile;
CRUD/filters/sort/pagination/full/partial/CSRF; run match/failed/inactive references;
fee specificity/ties/unsupported policy; tax required/none/bases; missing/ambiguous/zero FX
và đúng chiều/ngày; snapshot hash/historical preservation/idempotent calculate;
Costing fingerprint/query-count/no-membership; Chromium create/dependent fields/validation/
calculate/waterfall/readonly/history/mobile/no JS errors. Cross-currency và future FX
được phủ bằng PostgreSQL fixtures cô lập, không dùng API ngoài.

Commands/results:

| Kiểm tra | Kết quả |
| --- | --- |
| `python manage.py check` | PASS, 0 issues |
| `npm run build:css` | PASS, Tailwind 4.3.3 |
| Full suite + Chromium: `scripts/test.ps1 --verbosity=1` | **670/670 PASS**, 228,807 giây |
| Pricing cuối + Chromium: `scripts/test.ps1 apps.pricing --verbosity=1` | **90/90 PASS**, 20,053 giây |
| `verify_pricing_demo --report artifacts/pricing-scenario-golden.json` | Golden/future 12 metric delta = 0; history không đổi |
| Chạy lại verify Pricing | Số rows giữ nguyên: 2 scenario, 4 fee, 2 tax, 1 channel, 3 Costing Run |
| `verify_costing_demo --report artifacts/pricing-scenario-costing-regression.json` | Golden 583.000, future 647.000, delta = 0, historical_unchanged=true |
| Supabase HTTP smoke | List/create/2 detail/options: full và HTMX đều 200; historical detail chỉ 2 queries, không đọc rule/FX/membership hiện tại |

Full suite chạy trước khi thêm 5 regression cases cuối cho Pricing; gate 90 tests
chạy sau các sửa cuối và gồm toàn bộ Pricing hiện tại (47 Scenario + 43 Foundation).
Không tuyên bố full suite 675 tests đã chạy trong một lượt. Fixtures và Chromium
dùng localhost PostgreSQL cô lập; Supabase chỉ dùng commands DEMO DML đã nêu,
read-only schema inspect và HTTP smoke, không DDL.

Evidence: artifacts/pricing-scenarios-full.log,
pricing-scenarios-final-targeted.log, pricing-scenario-golden.json,
pricing-scenario-costing-regression.json; screenshots/pricing-scenario-desktop.png
và pricing-scenario-mobile.png. Các artifact gitignored, không chứa credentials.

## 10. Giới hạn và bước tiếp theo

- Không rule engine chung, discount/order allocation, phí hoàn trả, thuế trên phí,
  tax-on-tax hoặc mixed tax inclusion. Unknown basis báo lỗi, không dự đoán.
- Không manual selling-price analysis vì stored method MANUAL_APPROVED gắn legacy approval;
  không thêm method/enum. RULE_BASED chưa có contract thực thi.
- Không commercial rounding; money 8dp hiện có. Snapshot trung gian Decimal đủ precision.
- Không version table hay DB trigger Pricing immutable; bảo vệ ở application.
- Không tính theo đơn vị bán khác quantity_uom; không giả quantity order khi schema thiếu.
- Không bulk pricing/publishing/approval/user audit hoặc comparison trong iteration này.

Bước tiếp theo đề xuất: **Scenario Comparison** chỉ đọc các persisted snapshots cùng
đơn vị/tiền tệ hoặc chính sách quy đổi rõ. Không tự triển khai ở task này.

## 11. Báo cáo nghiệm thu theo 25 mục yêu cầu

| Mục | Kết quả |
| --- | --- |
| 1. Actual models | PriceScenario; CostingRun/CostingRunLine read-only; Channel/ChannelFeeRule/TaxRule/FxRate/Currency/Product/Sku hiện có |
| 2. Lifecycle | DRAFT → CALCULATED; lỗi giữ Nháp + diagnostics, không approval |
| 3. Costing integration | persisted per_unit của LOCKED Run; Product/SKU phải khớp; không recost |
| 4. Channel | active master, scope nội bộ, snapshot đủ fields/display |
| 5. Fee | Foundation selector, type/specificity/priority, tie error, fixed/%/floor/cap, từng component |
| 6. Tax | explicit REQUIRED/NONE, parallel common pretax base, inclusive/exclusive; scope/tie/missing guards |
| 7. FX | direct only, explicit type, pricing-date midnight Việt Nam; nguồn/số nhân snapshot |
| 8. Margin/Markup | UI %, DB fraction; profit/gross vs profit/cost; profit-per-unit riêng |
| 9. Solver | deterministic Decimal piecewise linear; denominator guard; minimum + recompute actual |
| 10. Waterfall | persisted component table, gross − fees − tax − cost = profit, delta 0 |
| 11. Snapshot | JSON schema 1 + source rows + Costing reference/result/hash + policy + outputs |
| 12. Trace | fees raw/floor/cap/final, tax basis/inclusion, FX direction, rejected candidates, trace_id/hash |
| 13. History | old Pricing/Costing không đổi sau future rules; calculated rerun idempotent, clone mã mới |
| 14. Golden input | C=58.300; 5% + 1.000 fee; 10% inclusive tax; margin 20%; VND; một hộp |
| 15. Expected | P=2.609.200/29, các hằng số độc lập trong bảng §7 |
| 16. Actual | Khớp toàn bộ expected trên Supabase thật |
| 17. Delta | 6 Golden + 6 future metrics đều 0; waterfall reconcile 0 |
| 18. Files created | Manifest §8, gồm tests/concurrency/command/report |
| 19. Files modified | Manifest §8; không Costing engine/core models/schema/config Auth |
| 20. Tests | Gate commands/evidence §9 |
| 21. Pass/Fail | 670 full PASS, 90 final Pricing PASS, không failed tests còn lại |
| 22. Costing regression | Golden 583.000; future 647.000; immutable fingerprint giữ nguyên |
| 23. Tailwind | Production build PASS; không thêm/upgrade package |
| 24. Limitations | §10; unsupported calculation báo lỗi, không trả giá sai |
| 25. Next slice | Scenario Comparison trên persisted results; chưa triển khai |

**READY FOR SCENARIO COMPARISON** trong phạm vi policy v1 đã mô tả.
