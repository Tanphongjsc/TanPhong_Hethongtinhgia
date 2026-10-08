# So sánh kịch bản giá bán — 08/10/2026

## 1. Kiến trúc và persistence thực tế

`GET /pricing/scenarios/compare/`, URL name `pricing:scenario_compare`.
Selection, bộ lọc và mốc nằm trong query string; không session hoặc bảng Comparison.
Luồng: View → selector ORM → kiểm tra snapshot/compatibility → presentation → template.
Không gọi Pricing/Costing runner, solver hoặc rule resolver. Không ghi dữ liệu.
Reuse centralized internal workspace; không user, membership, login hoặc company UI.

Model `apps.core.models.PriceScenario`, unmanaged, bảng `costing.price_scenario`:

- `code`, `name`, `base_run`, `channel`, `pricing_method`;
- `target_margin`, `target_markup`, `target_profit_per_unit`, `minimum_price`;
- `suggested_price`, `final_price`, `currency_code`, `status`, `valid_from`, `valid_to`;
- `scenario_context_jsonb`, `output_snapshot_jsonb`, timestamps và actor nullable cũ.

Product/SKU qua `base_run → CostingRun`; không FK trực tiếp trên Scenario.
Không version/revision, result-lines hoặc comparison-group model riêng.
Live introspection xác nhận PK `id`, `uq_price_scenario(organization_id, code)`.
Không sửa model/schema/migration hoặc actor fields.

Snapshot schema 1 chứa `policy`, `inputs`, `costing`, `display`, `sources`, `result`,
`trace`, `hash`, `trace_id`, `calculated_at`. `result` đã có unit_cost, fees, tax,
gross_price, pre_tax_revenue, net_revenue, profit, actual_margin và actual_markup.
Fee/tax lines và FX trace đã lưu, không dựng lại từ bảng cấu hình hiện tại.
SHA-256 kiểm tra snapshot dùng helper digest thuần dữ liệu hiện có; không chạy engine.

## 2. Compatibility và validation

- Backend yêu cầu 2–5 ID khi so sánh; không ID trùng, invalid/bigint overflow/missing.
- Chỉ CALCULATED, base Run LOCKED, cùng workspace nội bộ, schema/hash/result hợp lệ.
  Failed attempt hiện lưu DRAFT + errors, không invent status FAILED của Scenario.
- Cùng SKU và Product. Hỗ trợ Product-level khi tất cả cùng Product và SKU NULL.
  Không trộn SKU-level với Product-level hoặc hai SKU khác nhau.
- Cùng output UoM ID và pricing basis. Policy v1 giá cho đúng một đơn vị Costing output;
  không giả conversion hoặc so sánh 1 hộp với 1 kg chỉ vì cùng SKU.
- Cross-check captured Product/SKU/Run/UoM với FK Run, snapshot hash và finite Decimal.
  Snapshot thiếu/hỏng/không hỗ trợ báo tiếng Việt, không sửa hay tự tính lại.

## 3. Selection, HTMX và UI

Chọn Product → SKU → danh sách kịch bản có kết quả đã tính. Product bắt buộc để tải
candidates; share URL chỉ chứa scenario IDs tự suy ra Product/SKU từ snapshot đã chọn.
Search code/name, filter channel/currency/date, sort code/name/pricing_date, pagination
25/50/100 tại DB. Master labels của bộ lọc có thể là hiện tại; cột kết quả dùng labels
snapshot lịch sử. Không giới hạn active masters để tránh làm mất lịch sử.

Ví dụ: `/pricing/scenarios/compare/?scenario=1&scenario=2&compare=1&baseline=1`.
IDs lặp giữ nguyên khi tìm kiếm/lọc/phân trang/đổi mốc hoặc bỏ chọn. Lựa chọn ngoài
trang hiện tại được giữ bằng hidden inputs. Backend quyết định dropdown/queryset.
Alpine chỉ đếm/giới hạn checkbox, không tính tài chính. Không JS dependency mới.

Normal/history restore trả full page; HX trả `#scenario-comparison`. Search 400ms,
`hx-push-url=true`, indicator và request synchronization reuse Foundation. Sidebar GIÁ BÁN
mở link So sánh kịch bản, active riêng với Kịch bản giá bán.
List/matrix dùng table/th, labels/aria, focus chuẩn; desktop-first, bảng scroll ngang
trên mobile. Không chart/export/approval/audit/publishing/dashboard hoặc redesign.

## 4. Chỉ tiêu và tiền tệ

Cột là kịch bản; hàng gồm thông tin Product/SKU/ngày/kênh, Costing source/ngày/unit cost,
phương pháp và mục tiêu margin/markup/profit, giá vốn, phí, thuế, giá khách trả gồm thuế,
doanh thu trước phí chưa thuế, doanh thu thuần, lợi nhuận và actual margin/markup.
Disclosure hiển thị dynamic fee/tax labels, basis/rate/fixed/floor/cap, FX direction/date,
trace/hash và link Pricing/Costing detail. Không hard-code loại phí hay thuế suất.

Tất cả số tiền có currency. Khi khác currency, giữ các giá gốc, cảnh báo và bỏ monetary
delta cho toàn bảng; không convert bằng current FX, không raw-money ranking.
FX trace chỉ giải thích quy đổi đã áp dụng trong từng Scenario; không dùng nó để giả
một đơn vị tiền tệ so sánh chung. Margin/markup vẫn cùng denominator policy v1.
Không tự chọn kịch bản tốt nhất.

## 5. Kịch bản mốc và delta

Mốc mặc định là Scenario đầu tiên trong repeated IDs; có dropdown đổi mốc.
Mốc chỉ được thuộc selection. Absolute = value − baseline, relative = absolute /
abs(baseline) × 100. Baseline 0 hoặc ratio NULL → relative `—`; không chia 0.
Ratio absolute dùng điểm phần trăm. Decimal precision 80, relative display làm tròn
4 chữ số HALF_EVEN; dữ liệu nguồn không bị làm tròn/sửa. Tiền hiển thị giữ precision
đã lưu và bỏ zero thừa, ngày dd/mm/yyyy, datetime giờ Việt Nam.

## 6. Historical safety và queries

Selected snapshots lấy bằng **một query** join base_run, chỉ các fields dùng để render;
không lấy Run.version_snapshot_jsonb/fx_snapshot_jsonb hoặc query từng metric.
2 và 5 scenarios đều một query. Candidate pagination/filter/search/sort ở DB;
snapshot validation chỉ trên selection tối đa 5 và trang candidates tối đa 100.
Đếm đủ 2 scenarios cho SKU bằng LIMIT 2. Không query OrganizationMember.
Fee/Tax/FX hiện tại không được query để render hoặc tính lại lịch sử.

Tests patch engine calls thành lỗi, capture SQL để chặn writes/current source queries,
fingerprint cả Costing header + lines và so toàn bộ Pricing records trước/sau GET.
Thay current Channel/Fee/Tax/FX vẫn giữ nguyên comparison metrics/labels lịch sử.
Live Supabase smoke cũng chỉ đọc, không seed hoặc chạy lại engine.

## 7. Golden độc lập

Tests A/B/C có cùng SKU/đơn vị, khác margin hoặc fee/tax configuration; persisted fixture
expected là các hằng số độc lập. Test comparison không resolve source rules.

| Chỉ tiêu (VND/đơn vị, trừ margin) | A | B | C |
| --- | ---: | ---: | ---: |
| Giá vốn | 58.300 | 58.300 | 58.300 |
| Phí | 5.498,62068966 | 6.551,56030363 | 6.000 |
| Thuế | 8.179,31034483 | 9.169,24374473 | 9.090,90909091 |
| Giá khách trả | 89.972,41379310 | 92.526,00506044 | 100.000 |
| Lợi nhuận | 17.994,48275861 | 18.505,20101208 | 26.609,09090909 |
| Biên lợi nhuận thực tế | 20% | 20% | 26,60909091% |

B−A: giá bán +2.553,59126734 VND; lợi nhuận +510,71825347 VND;
giá bán relative +2,8382%; margin 0 điểm %. C−A margin +6,60909091 điểm %.
Hai DEMO Pricing đã lưu trên Supabase khớp A/B; cùng base Golden Run, unit cost
58.300, không dùng nhầm Future Costing unit cost 64.700.

## 8. Files tạo mới

- `apps/pricing/comparison_selectors.py`
- `apps/pricing/comparison.py`
- `apps/pricing/comparison_presentation.py`
- `apps/pricing/comparison_views.py`
- `apps/pricing/test_comparison.py`
- `apps/pricing/test_comparison_browser.py`
- `templates/pricing/comparison/page.html`
- `templates/pricing/comparison/partials/content.html`
- `templates/pricing/comparison/partials/matrix.html`
- `docs/SCENARIO_COMPARISON.md`

## 9. Files sửa

- `apps/pricing/urls.py`
- `apps/pricing/test_scenarios.py`: assertion menu chưa triển khai được thay bằng link thật.
- `apps/master_data/navigation.py`, `context_processors.py`
- `templates/components/pagination.html`: optional repeated-query pairs cho comparison.
- `static/css/app.css`: generated Tailwind build, không chỉnh tay.
- `docs/00_AI_CONTEXT.md`, `01_REQUIREMENTS_SCOPE.md`, `02_BUSINESS_DOMAIN.md`,
  `03_SYSTEM_ARCHITECTURE.md`, `04_ENGINEERING_GUIDE.md`, `05_QA_TESTING.md`,
  `FRONTEND_IMPLEMENTATION_SPEC.md` và `README.md`.

Không thêm dependencies hoặc chỉnh core models, DB schema, engine, Auth/company flow.

## 10. Validation evidence và giới hạn

Commands dùng Python trong `env`, tests qua `scripts/test.ps1`, config.test_settings
và PostgreSQL localhost guarded. Chromium bật `COSTING_BROWSER_TESTS=1`,
`PLAYWRIGHT_BROWSERS_PATH=<workspace>/artifacts/playwright`.

- `python manage.py check`: PASS, 0 issues.
- `npm run build:css`: PASS, Tailwind 4.3.3.
- Targeted comparison: **28/28 PASS**, gồm Chromium selection/matrix/baseline/search/
  history/mobile, independent Golden, compatibility, read-only và performance tests.
- Full regression + Chromium: **703/703 PASS** trong 180,797 giây, bao gồm Pricing Golden, Costing Golden,
  persisted history và các module đã triển khai. Assertion cũ yêu cầu menu Compare
  chưa được mở đã được cập nhật thành link thật theo scope iteration hiện tại.
- Sau full run, metadata tỷ lệ phí/thuế fixture B được sửa đúng 6%/11% (không đổi
  expected amounts hoặc production code); targeted **28/28 PASS** lại trong 6,017 giây.
- Supabase readonly smoke: full/HX **200**, selection **1 query**, Pricing snapshots,
  counts và Costing header/line fingerprint không đổi.
  Costing fingerprint `b317df1c48d905f093089009a85fd0ad07c451d274a773ddb1996c799b89f0f2`.

Evidence: `artifacts/comparison-targeted.log`, `scenario-comparison-full.log`,
`scenario-comparison-live.json`, screenshots `scenario-comparison-desktop.png`,
`scenario-comparison-mobile.png`. Artifacts gitignored, không credentials.

Giới hạn: snapshot schema/policy v1; không currency normalization hoặc UoM conversion
trong comparison. Unknown/legacy snapshots bị từ chối. Candidate footer count phản ánh
DB rows có cấu trúc eligibility; row hash/content hỏng bị bỏ khỏi lựa chọn tại render,
không scan toàn bộ lịch sử để sửa count. Hash là kiểm tra nhất quán, không chữ ký chống
giả mạo. Pricing immutability vẫn ở application vì DB không có trigger mới; không đổi
schema trong task này. Native date input phụ thuộc locale trình duyệt; ngày kết quả
hiển thị Việt Nam. Chưa load/security/UAT/restore validation cho production deployment.

Bước tiếp theo: **System Hardening** — kiểm thử tải, an toàn dữ liệu, vận hành và phục hồi
theo deployment scope được giao; không tự triển khai trong iteration này.

## 11. Nghiệm thu theo yêu cầu

| Mục | Kết quả |
| --- | --- |
| 1. Architecture | Stateless GET, read-only selector/validation/presentation |
| 2. Persistence reuse | PriceScenario JSON + CostingRun references, không model mới |
| 3. Compatibility | Same SKU/Product + captured output UoM/unit basis/schema/policy |
| 4. Selection | Product → SKU, 2–5, search/channel/currency/date/sort/page |
| 5. Metrics | Cost/fees/tax/revenue/price/profit/targets/actual ratios |
| 6. Currency | Explicit per amount/column, no raw money delta across currencies |
| 7. Baseline | First selected or explicit valid ID, Decimal absolute/%/points |
| 8. History | Snapshot/hash/trace only, no writes/engine/current rules |
| 9–10. Files | Manifest §8–9 |
| 11. HTMX | Full/partial, 400ms, URL/history, repeated IDs preserved |
| 12. Queries | Selection constant one query, DB-side bounded candidates |
| 13–14. Tests | §10, evidence logs |
| 15–16. Regressions | Full suite Pricing/Costing Golden + live readonly fingerprints |
| 17. Tailwind | Production build PASS, existing version |
| 18. Limitations | §10 |
| 19. Next phase | System Hardening, task stops here |

**READY FOR SYSTEM HARDENING.** Không có blocker trong phạm vi comparison; đây là
điều kiện để bắt đầu hardening, chưa thay thế các gate production/UAT đã nêu ở §10.
