# Kiểm chứng dữ liệu DEMO và Costing tích hợp

Ngày kiểm chứng: 07/10/2026. Phạm vi: các module đã triển khai, một bộ mẫu,
đối soát trên database phát triển Supabase; không triển khai Pricing hoặc schema mới.
Tài liệu canonical nằm trực tiếp trong `docs/`, không có `docs/ai/`.

## Schema thực tế và dependency

Tất cả models dùng lại từ `apps/core/models.py`, `managed=False`.
Database thật được inspect ở transaction READ ONLY trước khi viết command.
Có một Organization `TANPHONG`; Currency 3, UoM Category 8, UoM 19; các bảng
nghiệp vụ cần cho demo còn trống. Company compatibility được resolve duy nhất
qua `get_default_organization()`, không tạo/sửa công ty hoặc query membership.

| Cấu trúc thực tế | Field bắt buộc / quan hệ được dùng | Constraint / giới hạn |
|---|---|---|
| Currency | code PK, name, decimal_places, is_active | Code 3 ký tự; decimals 0..8 |
| UomCategory → Uom | code/name/dimension; Uom.category/code/name/symbol/precision | Code global unique; precision 0..12 |
| UomConversion | from_uom/to_uom/factor/effective_from; compatibility company | Khác đơn vị; factor > 0; trực tiếp/nghịch đảo, không chuỗi |
| CostElement | code/name/value_type/default_source_mode/accounting_scope/cost_scope | Unique company+code; MONEY cần Currency |
| ProductCategory → Item | code/name; Item.item_type/base_uom | Unique company+code; RAW_MATERIAL, PACKAGING, SEMI_FINISHED, FINISHED_GOOD, SERVICE, BY_PRODUCT |
| Product → Sku | Product.costing_uom; Sku.product/sales_uom/net_quantity/net_quantity_uom | Unique company+code; net_quantity > 0; optional output_item/sell_item không dựng giả |
| Supplier → SupplierPrice | Price.supplier/item/price_uom/currency_code/unit_price/min_qty/effective_from | Giá/min_qty >= 0; thuế tỷ lệ [0,1]; end > start |
| Recipe → RecipeVersion → RecipeLine | Header.product; Version.output_qty/output_uom/yield_rate/version_no; Line.component_item/qty/uom/scrap_rate | Version unique header+number; output/qty > 0; yield (0,1], scrap [0,1) |
| PackagingConfig → Version → Line | Header.product; Line.packaging_item/qty/uom/level_code | Version unique; qty > 0; không output quantity/UoM, không scrap |
| SkuPackagingAssignment | sku/config/effective_from/is_primary | Unique sku+config+start; end > start |
| WorkCenter → Resource → ResourceRate | WC.code/name; Resource.code/name/type; Rate.resource/amount/currency_code/per_uom/rate_type/start | Resource types MACHINE/LABOR/WORK_CENTER/SERVICE; rate >= 0; end > start |
| Routing → RoutingVersion → RoutingOperation | Header.product; version batch_size/batch_uom; operation sequence/code/name/setup/run; optional WC/primary_resource/time_uom/basis | Sequence unique version+sequence; >0; time >=0 Decimal; không bảng đa nguồn lực |
| CostPool → CostPoolPeriod; AllocationRule → Pool | pool_type; period amount/currency/dates/normal_capacity/capacity_uom; rule basis_type/priority/start | Không CostPoolMember hoặc CostElement FK; không Target/Line/Version; capacity >0 nếu có |
| Formula → Version/Dependency/TestCase | expression/version_no; output_element; testcase input/expected/tolerance | DSL allow-list, type/unit/cycle, AST/hash, real saved tests trước activation |
| CostingScheme → Version → Line | line_code/label/type/source/order; CostElement, FormulaVersion hoặc resolver code | Unique version+code/order; source reference CHECK; activation validation |
| CostingRun → CostingRunLine | scheme_version/quantity/uom/currency/effective_at; snapshots; typed breakdown | Unique operation key; quantity>0; saved LOCKED history immutable |

Dependency: Currency/UoM → CostElement/Category → Item → Product/SKU → Supplier/Price
→ Recipe/Packaging → WorkCenter/Resource/Rate → Routing → Pool/Period/Allocation
→ Formula → Scheme → Run/Lines. Audit actors nullable luôn NULL.

Version statuses thực tế: DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/RETIRED.
APPROVED/EFFECTIVE/RETIRED bất biến theo trigger cho các versioned structures.
SupplierPrice/ResourceRate/AllocationRule có effective dating và status, không có
version table hoặc overlap/usage-lock policy. Khoảng hiệu lực kết thúc **bao gồm**
ngày kết thúc theo implementation hiện tại; ngày kết thúc phải sau ngày bắt đầu.
CostPoolPeriod có DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/CLOSED.
Run thành công dùng **LOCKED**, không tồn tại enum COMPLETED trong schema.

Allocation basis CHECK: NORMAL_CAPACITY/MACHINE_HOUR/LABOR_HOUR/KG/UNIT/BATCH/
PALLET_DAY/SHIPMENT/VALUE/CUSTOM. Execution hiện chỉ hỗ trợ NORMAL_CAPACITY có
số liệu kỳ, công suất, đơn vị rõ ràng. Không giả FIXED_PERCENTAGE driver.

## Dataset và expected đóng băng trước execution

- Reuse VND/USD, MASS/TIME/COUNT và KG/G/HOUR/MINUTE nếu tồn tại đúng đại lượng,
  active; giữ nguyên dữ liệu tham chiếu cũ. Nếu thiếu mới tạo reference phù hợp.
  Thêm DEMO_PIECE và DEMO_BOX_UOM để không tạo category/đơn vị global trùng.
- Conversion: G→KG factor 0.001; HOUR→MINUTE factor 60. Engine thực sự dùng
  g→kg trực tiếp và phút→giờ nghịch đảo, không hard-code trong business logic.
- DEMO_COFFEE; Product DEMO_CAPPUCCINO; SKU DEMO_CAPPUCCINO_BOX20: 0,5 kg/hộp.
- DEMO_INSTANT_COFFEE, DEMO_SUGAR (RAW_MATERIAL, base/purchase KG), DEMO_SACHET,
  DEMO_BOX (PACKAGING, base/purchase DEMO_PIECE).
- DEMO_SUPPLIER: 100.000/kg cà phê; 20.000/kg đường; 500/cái sachet; 5.000/cái hộp.
- DEMO_BOM_CAPPUCCINO: output 1 hộp, yield 1; 200 g cà phê + 300 g đường, scrap 0.
- DEMO_PACK_CAPPUCCINO: 20 sachet + 1 hộp giấy; primary SKU assignment.
  Cơ sở quantity của Packaging nhập trong Run: **1 hộp**.
- DEMO_WC_MIXING + DEMO_MIXER (MACHINE): 120.000 VND/giờ;
  DEMO_WC_PACKING + DEMO_PACKING_LABOR (LABOR): 60.000 VND/giờ.
- DEMO_ROUTE_CAPPUCCINO: operation 10 phối trộn 3 phút/hộp, operation 20 đóng gói
  6 phút/hộp; setup 0, output basis 1 hộp; không snapshot giá vào routing.
- DEMO_FACTORY_OVERHEAD: FACTORY_FIXED; kỳ 01/10–31/12/2026, amount 530.000 VND,
  normal capacity 100 hộp; DEMO_OVERHEAD_NORMAL dùng NORMAL_CAPACITY.
- 6 phần tử chi phí DEMO_MATERIAL_COST/PACKAGING_COST/RESOURCE_COST/OVERHEAD_COST/
  DIRECT_COST/FULL_COST, MONEY/VND/MANUFACTURING/INVENTORY_COST, HALF_UP scale 6.
  Không dựng SYSTEM resolver MACHINE_COST/LABOR_COST; hai thành phần được kiểm tra
  từ trace nguồn lực và không cộng hai lần vào Scheme.
- DEMO_DIRECT_FORMULA = `$DEMO_MATERIAL_COST + $DEMO_PACKAGING_COST + $DEMO_RESOURCE_COST`.
  DEMO_FULL_FORMULA = `@DEMO_DIRECT_FORMULA + $DEMO_OVERHEAD_COST`.
  Mỗi identity có real golden testcase; AST/dependencies validated và activation service.
- DEMO_COSTING_SCHEME: 4 SYSTEM inputs, 1 FORMULA subtotal, 1 FORMULA output MONEY.
  SYSTEM codes giữ registry MATERIAL_COST/PACKAGING_COST/RESOURCE_COST/
  ALLOCATION:DEMO_OVERHEAD_NORMAL. Không chọn newest Draft để execution.
- Mỗi cấu trúc versioned có version 1 EFFECTIVE và version 2 DRAFT clone bằng service
  để kiểm tra form chỉnh sửa. Không thay đổi version 1.

Run: STANDARD, SKU mẫu, 10 hộp, VND, ngày 07/10/2026, packaging basis 1 hộp.

| Thành phần | Tính tay độc lập | Expected VND |
|---|---|---:|
| Nguyên liệu | 200g ×10 /1000 ×100.000 + 300g ×10 /1000 ×20.000 | 260.000 |
| Bao bì | 20 ×10 ×500 + 1 ×10 ×5.000 | 150.000 |
| Máy | 3 phút ×10 /60 ×120.000 | 60.000 |
| Nhân công | 6 phút ×10 /60 ×60.000 | 60.000 |
| Nguồn lực tổng | Máy + nhân công | 120.000 |
| Trực tiếp | Nguyên liệu + bao bì + nguồn lực | 530.000 |
| Chi phí chung | 530.000 ×10 /100 | 53.000 |
| Tổng giá thành | Trực tiếp + chung | **583.000** |
| Giá thành/hộp | Tổng /10 | **58.300** |

Expected nằm trong `manual_expected()` độc lập với engine; không lấy actual để
điều chỉnh expected. Trace từ hệ số nghịch đảo 60 có thể có sai số Decimal khoảng
10^-33; đối soát máy/nhân công dùng HALF_UP 6 chữ số và giữ raw trace/raw delta.
Tổng header và sáu dòng persisted phải khớp tuyệt đối.

Sau Run đầu mới thêm giá cà phê 120.000/kg và rates máy 144.000/h, nhân công 72.000/h
từ 01/11/2026. Nguồn cũ hết hiệu lực 31/10. Golden tháng 11: vật liệu 300.000,
bao bì 150.000, nguồn lực 144.000, trực tiếp 594.000, chung 53.000, tổng 647.000,
64.700/hộp. Kỳ phân bổ không đổi. Giá/lịch sử đầu tháng 10 phải giữ nguyên.

## Commands và files

```powershell
python manage.py check
python manage.py seed_costing_demo
python manage.py seed_costing_demo
python manage.py verify_costing_demo --report artifacts/demo-verification.json
python manage.py runserver
```

Trang kết quả `/costing/runs/`; tìm `DEMO_CAPPUCCINO`. Các Run có run_no UUID do
service tạo; marker DEMO nằm trong notes/snapshot và các master code, không sửa
run_no trên bản đã khóa. Idempotency UUID là operation key, không phải actor.
Verify dùng ba khóa ổn định để chạy lại command không nhân bản Run.

Files tạo:

- `apps/costing/demo_data.py`
- `apps/costing/demo_verification.py`
- `apps/costing/management/__init__.py`
- `apps/costing/management/commands/__init__.py`
- `apps/costing/management/commands/seed_costing_demo.py`
- `apps/costing/management/commands/verify_costing_demo.py`
- `apps/costing/test_demo.py`
- `apps/costing/test_demo_browser.py`
- `docs/COSTING_DEMO_AUDIT.md`

Files sửa: `README.md`, `docs/00_AI_CONTEXT.md`, `apps/costing/run_forms.py` (help text
chọn phương án dùng lời giải thích nghiệp vụ tiếng Việt, bỏ từ "Schema"). Không thêm dependencies, không
sửa models/migrations/schema/auth/business views. Generated CSS build lại bằng
Tailwind 4.3.3; không chỉnh trực tiếp output.

Seed chỉ tạo/validate bản ghi; nếu dữ liệu có sẵn khác định nghĩa mẫu thì fail,
không overwrite. Lock compatibility company row serialize commands. `seed_demo`
atomic bao gồm cấu hình/lines/clones; Formula/Scheme kích hoạt bằng service gate.
Upstream source publication chỉ trong command sau service validation; không thêm
approval workflow. Period dùng ORM đã validate vì chưa có service/UI quản lý kỳ.
Không `--reset`: các version hiệu lực và locked Runs phải giữ lịch sử theo trigger.
Không disable trigger, xóa dữ liệu cũ hoặc TRUNCATE trên database phát triển.
Formula service có rebuild dependencies của chính bản Nháp vừa tạo trước activation;
đây là hành vi validated của service hiện có, không xóa dữ liệu lịch sử.

## Kiểm thử và giới hạn

Tests dùng PostgreSQL localhost 17: `test_costing_slice`, guarded test runner.
Fixture company và cleanup/TRUNCATE của browser chỉ được dùng trong DB test cô lập;
command Supabase không tạo công ty hoặc xóa dữ liệu. Negative tests không chạy trên
Supabase. Browser HTMX thực sự nhập 10 hộp, POST CSRF, xem trace hai nguồn lực,
snapshot hai công thức, desktop/mobile, JavaScript errors và absence of session.

UI smoke trên DB được seed chỉ GET: 22 module, list/detail/create/edit, search,
positive/negative filter, empty search, sort/pagination/HTMX, active navigation, tiếng Việt,
version Nháp detail/edit và snapshot/trace/rerun của Run. Pages nghiệp vụ chưa có
implementation hiển thị disabled placeholder, không tạo links giả.

Query review: source lists được select_related/batched, SQL filter/date/pagination;
test kiểm tra số lần query price/rate/line/operation và không query membership.
GET smoke báo max_queries/page để thấy chi phí query; không phải load benchmark/SLA.

Chưa thể kiểm thử end-to-end: đa tiền tệ/FX, xử lý thuế giá mua, driver thiếu mẫu số,
multi-level packaging expansion, nested BOM/cycle expansion, đa resource/operation,
CostPoolMember/targets (không có schema), RuleTable/LOOKUP/EXTERNAL, actual costing,
approval/override workflow. Source mơ hồ hoặc unsupported bị chặn, không đoán/zero.
CRUD chưa có publish UI cho BOM/packaging/routing/prices/rates/allocation/period;
demo command chốt nguồn để kiểm chứng execution đã có. Không tuyên bố thay thế UAT
workbook thực tế hoặc kiểm thử hiệu năng production.

Kết quả chạy Supabase, bảng đối soát, lịch sử, UI từng module và báo cáo 29 mục được
ghi ở phần evidence bên dưới sau khi thực thi thật.

## Evidence Supabase và báo cáo theo 29 mục

1. **Dataset đã tạo:** một dataset DEMO_CAPPUCCINO_V1; 110 bản ghi mới sau toàn bộ audit, bao gồm cấu hình/version/clone/dependency/future và 3 Runs/18 RunLines. Seed lại không nhân bản.
2. **Existing Organization:** TANPHONG được resolve bằng helper hiện có. Count=1; hash tất cả field trước/sau giống nhau: `54acdfa0404b7b65cd0094f81eea4895ef5ff079d77b411fab60a91b2364c961`. Không INSERT/UPDATE Organization.
3. **Master data:** 6 Cost Elements, 1 ProductCategory, 4 Items, 2 UoM mới, 2 conversions; reuse VND/USD và MASS/TIME/COUNT/KG/G/HOUR/MINUTE; Currency count giữ 3.
4. **Product/SKU:** DEMO_CAPPUCCINO và DEMO_CAPPUCCINO_BOX20. Sales/costing basis 1 hộp; net quantity 0,5 kg.
5. **Supplier Prices:** 1 supplier; 4 giá ban đầu và 1 giá cà phê tương lai. Có thời gian hiệu lực và marker DEMO; actors NULL.
6. **BOM:** 1 Recipe, 2 versions, 4 lines gồm clone Nháp; hiệu lực version 1 cho 1 hộp, 200 g cà phê + 300 g đường.
7. **Packaging:** 1 config, 2 versions, 4 lines gồm clone, 1 SKU assignment. 20 sachet + 1 hộp giấy; Run nhập packaging basis 1 hộp.
8. **Work Centers/Resources/Rates:** 2 centers, 2 resources MACHINE/LABOR, 4 rates gồm 2 nguồn tương lai.
9. **Routing:** 1 header, 2 versions, 4 operations gồm clone. Sequence 10/20; setup 0; run 3/6 phút trên 1 hộp.
10. **Cost Pool/Allocation:** 1 pool, 1 period, 1 NORMAL_CAPACITY rule; 530.000 VND / 100 hộp. Không có member/target relation trong schema.
11. **Formulas:** 2 identities, 4 versions (2 EFFECTIVE + 2 DRAFT), 2 stored golden tests, 10 dependency rows; cả hai công thức thực sự xuất hiện trong snapshot execution.
12. **Costing Scheme:** DEMO_COSTING_SCHEME; 2 versions, 12 lines gồm clone; validation PASS, EFFECTIVE version 1 được chọn thay vì Nháp mới nhất.
13. **Golden input:** STANDARD, ngày 07/10/2026, 10 DEMO_BOX_UOM, VND; Product/SKU mẫu, Scheme mẫu, packaging base 1 hộp.
14. **EXPECTED RESULT:** FULL_COST=583.000; UNIT_COST=58.300 VND. Tính tay đóng băng trước engine trong manual_expected().
15. **ACTUAL RESULT:** FULL_COST=583.000; UNIT_COST=58.300 VND. Header/6 persisted lines nhất quán.
16. **DELTA từng Cost Element/thành phần:** bảng sau. MACHINE/LABOR đọc trace; không tạo dòng SYSTEM giả.

| Thành phần | Expected VND | Actual VND | Delta VND |
|---|---:|---:|---:|
| Nguyên liệu | 260.000 | 260.000 | 0 |
| Bao bì | 150.000 | 150.000 | 0 |
| Máy | 60.000 | 60.000 | 0 |
| Nhân công | 60.000 | 60.000 | 0 |
| Nguồn lực tổng | 120.000 | 120.000 | 0 |
| Chi phí trực tiếp | 530.000 | 530.000 | 0 |
| Chi phí chung | 53.000 | 53.000 | 0 |
| Tổng giá thành | 583.000 | 583.000 | 0 |
| Giá thành/hộp | 58.300 | 58.300 | 0 |

Máy raw trace `60000.000000000000000000000000000000001`; raw delta `1E-33` VND do nghịch đảo 60. So sánh tại money scale=6 HALF_UP đã cấu hình; không thay expected.

17. **Run status:** cả 3 Runs LOCKED (hoàn tất, bất biến); không có FAILED hoặc breakdown nửa vời. Schema không có trạng thái COMPLETED.
18. **Conversion thực sự dùng:** snapshot có đúng 2 conversion IDs; G→KG factor 0.001, MINUTE→HOUR nghịch đảo 60; trace ghi factor/input/output.
19. **Effective-date selection:** Run 07/10 dùng coffee price 100.000/kg, máy 120.000/h, labor 60.000/h. Run 01/11 dùng coffee 120.000/kg, máy 144.000/h, labor 72.000/h; tổng 647.000. Local test thêm boundary 31/10 bao gồm ngày và 01/11 dùng nguồn mới.
20. **Snapshot:** 63 source records; phiên bản/line/giá/rate/quy đổi/allocation kỳ; 2 formula expressions/AST/hash/bindings/order; execution rules và SHA256 `9fc7bb996ba17b15804f8616eef472b972def500c6ae128a9c57a5db93e98809`; request/basis/date lưu riêng trong context.
21. **Explain trace:** mỗi dòng giữ input_snapshot/source_trace; quantity scale, yield/scrap, conversion, supplier/rate ID và dates, cost, formula inputs/phép tính, rounding. Đọc lại trace/snapshot UI PASS.
22. **Historical result:** fingerprint header + mọi RunLine trước/sau nguồn tương lai giống nhau `b317df1c48d905f093089009a85fd0ad07c451d274a773ddb1996c799b89f0f2`. Run tái thực thi 07/10 vẫn 583.000; Run 01/11=647.000.
23. **UI smoke cho từng module:** bảng dưới. Bao gồm GET create/edit; CRUD POST/negative/HTMX/browser được covered bằng PostgreSQL test suite cô lập. Kiểm tra thêm 10 pages version Nháp, trang gốc redirect và 6 trace drawers.

| Module | Kết quả | Requests được báo cáo | Max DB queries/page |
|---|---|---:|---:|
| cost_element | PASS | 8 | 5 |
| currency | PASS | 8 | 3 |
| uom_category | PASS | 8 | 3 |
| uom | PASS | 8 | 4 |
| uom_conversion | PASS | 8 | 5 |
| category | PASS | 8 | 3 |
| item | PASS | 8 | 8 |
| product | PASS | 8 | 5 |
| sku | PASS | 8 | 6 |
| supplier | PASS | 8 | 4 |
| supplier_price | PASS | 8 | 7 |
| bom | PASS | 8 | 5 |
| packaging | PASS | 8 | 7 |
| work_center | PASS | 8 | 3 |
| resource | PASS | 8 | 4 |
| resource_rate | PASS | 8 | 8 |
| routing | PASS | 8 | 5 |
| cost_pool | PASS | 8 | 5 |
| allocation_rule | PASS | 8 | 5 |
| formula | PASS | 8 | 6 |
| scheme | PASS | 8 | 5 |
| run | PASS | 12 | 10 |

24. **Integration bugs phát hiện:** không phát hiện sai tổng/nguồn/phiên bản/history trong pipeline trên dataset thật. Help text chọn Scheme còn từ kỹ thuật "Schema". Precision nghịch đảo 60 là đặc tính Decimal; instrumentation ban đầu so raw trace tuyệt đối gây false mismatch, không phải lỗi tiền đã persisted.
25. **Bugs đã sửa:** help text bằng lời giải thích nghiệp vụ tiếng Việt; verifier dùng money boundary 6 HALF_UP cho resource trace components và vẫn lưu raw delta; sửa fixture inventory chỉ đếm bảng test thực sự có. Thêm kiểm tra positive/negative filters, rollback/idempotency/history và real HTMX.
26. **Known limitations:** chỉ kiểm chứng dataset Manufacturing VND hỗ trợ hiện tại; không load/performance SLA hoặc UAT workbook thật. Source overlap không có policy chọn giá/rate, engine fail khi mơ hồ. Nested Formula chọn dependency theo ngày từng Run, exact version + AST đã snapshot. Không --reset dữ liệu đã chốt. Tên của Currency/UoM dùng chung có sẵn được giữ nguyên; label giao diện bằng tiếng Việt.
27. **Feature chưa thể test hoàn chỉnh:** FX/thuế/LOOKUP/EXTERNAL và allocation drivers thiếu mẫu số chưa có execution contract; CostPoolMember/Target/OperationResource không có schema; nested BOM/multi-level expansion/actual/approval/override chưa có execution. Không publish UI upstream hoặc CostPoolPeriod UI; command chỉ chốt demo có validation. Pricing app hiện mới skeleton; không triển khai route/feature trong task này.
28. **Tests PASS/FAIL:** full 585 PASS / 0 FAIL (158,193s), gồm 14 tests mới; sau thay help text và tăng negative filter smoke, targeted 69 PASS / 0 FAIL (27,577s). manage.py check PASS; npm run build:css PASS, Tailwind 4.3.3. Seed lần 2 tạo 0 trực tiếp. Verify Supabase lần đầu và lần lặp PASS. Schema constraints/triggers/columns hash trước/sau giống nhau `339aeb491a23244cc159b2b227efd64d37c3ab8fc7fc077b5183a60eac60772b`.
29. **Readiness:** READY FOR PRICING FOUNDATION trong phạm vi dataset/engine hỗ trợ đã kiểm chứng. Không tuyên bố FX/thuế/driver unsupported đã sẵn sàng; task kết thúc tại audit, không triển khai Pricing.

### Runs thực tế trên Supabase

| Run | Ngày nghiệp vụ (Asia/Ho_Chi_Minh) | Status | FULL_COST VND | URL |
|---|---|---|---:|---|
| Golden | 07/10/2026 | LOCKED | 583.000 | `/costing/runs/19dd1f8d-277f-4f2c-a7a5-fbea8e5cd93f/` |
| Tái thực thi sau nguồn tương lai | 07/10/2026 | LOCKED | 583.000 | `/costing/runs/887f20a0-6c63-4266-b26a-e3177e2ffc3b/` |
| Nguồn tháng 11 | 01/11/2026 | LOCKED | 647.000 | `/costing/runs/5315f160-bec1-4ddd-ba88-385c775c9679/` |

Evidence local (gitignored): `artifacts/demo-before.json`, `demo-after.json`,
`demo-verification.json`, `demo-seed-first.log`, `demo-seed-second.log`,
`demo-full-tests.log`, `demo-final-targeted-tests.log`; browser screenshots
`artifacts/screenshots/demo-golden-desktop.png` và `demo-golden-mobile.png`.

Chạy lại verify sau lần kiểm chứng đầu dùng các operation key ổn định. Đã đối chiếu
count của mọi business model trước/sau lần lặp: không đổi; vẫn 3 LOCKED Runs,
18 RunLines, 5 SupplierPrices và 4 ResourceRates. Mọi FK trong schema costing đều
đã được database validate; fingerprint Run đầu vẫn không đổi. Command không có
side effect ngoài dữ liệu DEMO đã mô tả.
