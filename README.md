# Hethongtinhgiathanh

Django Costing & Pricing độc lập, database-first trên schema `costing`.
Đã triển khai Frontend Foundation, Cost Element và Currency / UoM Category /
UoM / UoM Conversion Management, nhóm sản phẩm và danh mục vật tư / hàng hóa.
Đã có danh mục sản phẩm và SKU.
Đã có nhà cung cấp và lịch sử giá mua theo ngày hiệu lực.
Đã có định mức nguyên vật liệu, phiên bản và thành phần theo sản phẩm.
Đã có cấu hình bao bì, phiên bản/thành phần và liên kết SKU theo ngày hiệu lực.
Đã có trung tâm sản xuất, nguồn lực và lịch sử đơn giá theo ngày hiệu lực.
Đã có quy trình sản xuất, phiên bản và công đoạn với nguồn lực chính/thời gian/sản lượng cơ sở.
Đã có nhóm chi phí chung và quy tắc phân bổ theo tiêu thức/ngày hiệu lực.
Đã có Formula Engine và phương án tính giá thành theo phiên bản/cấu hình.
Các màn hình đã triển khai sử dụng tiếng Việt; mã nghiệp vụ và identifiers giữ nguyên.
Chế độ hiện tại: **single-company, không authentication**.
Không Approval Workflow hoặc business Audit Log; giữ version/history,
Costing snapshots, explain trace và logging kỹ thuật.

Hardening/hồi quy toàn hệ thống: [SYSTEM_HARDENING.md](docs/SYSTEM_HARDENING.md).
Sidebar chỉ hiện các module đang hoạt động; lịch sử phiên bản vẫn nằm trong từng
module. CSRF vẫn bắt buộc dù không đăng nhập; lỗi hết hạn yêu cầu tải lại trang.

Production: cài `requirements-production.txt`, cấp process environment theo
[.env.production.example](.env.production.example), build/collectstatic, kiểm tra
`python -m config.serve --check`, start bằng **`python -m config.serve`**.
Không dùng runserver/migrate/seed trong deployment. Production không tự đọc `.env`.
Runbook build/start/backup/restore/rollback/checklists:
[06_DEPLOYMENT_DEVOPS.md](docs/06_DEPLOYMENT_DEVOPS.md).
Trạng thái và evidence: [PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md).

So sánh kịch bản giá bán: `/pricing/scenarios/compare/`. Chọn 2–5 kịch bản đã tính,
cùng SKU và cùng đơn vị cơ sở; đọc dữ liệu đã lưu, chọn mốc và xem chênh lệch.
Khác tiền tệ không trừ trực tiếp khoản tiền. Scope, manifest và kiểm thử:
[SCENARIO_COMPARISON.md](docs/SCENARIO_COMPARISON.md).

Đã có Pricing Foundation: [Kênh bán](/pricing/channels/),
[Quy tắc phí kênh](/pricing/channel-fee-rules/), [Quy tắc thuế](/pricing/tax-rules/),
[Tỷ giá](/pricing/fx-rates/). CRUD/HTMX/Decimal, hiệu lực và selectors cấu hình;
Pricing Scenario tính từ Costing Run đã lưu; so sánh kịch bản chỉ đọc snapshot.
Schema, cleanup, giới hạn và kiểm thử: [PRICING_FOUNDATION.md](docs/PRICING_FOUNDATION.md).

## Chạy local

```powershell
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
npm run build
python manage.py check
python manage.py runserver
```

Giữ `.env` hiện có. Nếu chưa có, sao chép `.env.example` rồi điền thông tin
database và `DJANGO_SECRET_KEY`. Bật `DJANGO_DEBUG=True` cho local.
Mở `http://127.0.0.1:8000/master-data/cost-elements/`.

Truy cập trực tiếp, không cần user hoặc membership. `.env` dùng
`APP_MODE=single_company`. Một organization active được dùng tự động; nếu có nhiều,
đặt `DEFAULT_ORGANIZATION_ID` bằng ID công ty đang hoạt động cần sử dụng.
Không có công ty active hoặc cấu hình sai sẽ nhận 503 với lỗi cấu hình rõ ràng.
Xem [company context, cấu hình và hướng dẫn dữ liệu ban đầu](docs/SINGLE_COMPANY_NO_AUTH.md).

Các danh mục mới: `/master-data/currencies/`, `/master-data/uom-categories/`,
`/master-data/uoms/`, `/master-data/uom-conversions/`.
Nhóm sản phẩm: `/product/categories/`. Vật tư / hàng hóa: `/product/items/`.
Sản phẩm: `/product/products/`. SKU: `/product/skus/`.
Nhà cung cấp: `/master-data/suppliers/`. Giá mua: `/master-data/supplier-prices/`.
Định mức nguyên vật liệu: `/bom/`. Chi tiết phiên bản, clone, quy đổi đơn vị,
khóa lịch sử và báo cáo kiểm thử: [RECIPE_BOM.md](docs/RECIPE_BOM.md).
Cấu hình bao bì: `/bom/packaging/`, dùng namespace/app BOM hiện có.
Schema thực tế, cấp đóng gói, SKU assignment và kiểm thử:
[PACKAGING_CONFIGURATION.md](docs/PACKAGING_CONFIGURATION.md).
Trung tâm sản xuất: `/bom/work-centers/`. Nguồn lực: `/bom/resources/`.
Đơn giá nguồn lực: `/bom/resource-rates/`. Schema thực tế, validation, lịch sử giá
và kiểm thử: [WORK_CENTER_RESOURCE_RATE.md](docs/WORK_CENTER_RESOURCE_RATE.md).
Quy trình sản xuất: `/bom/routings/`. Công đoạn, clone phiên bản, đơn vị thời gian,
khóa lịch sử và kiểm thử: [ROUTING.md](docs/ROUTING.md).
Nhóm chi phí chung: `/bom/cost-pools/`. Quy tắc phân bổ: `/bom/allocation-rules/`.
Schema thực tế, các quan hệ chưa có và validation/kiểm thử:
[COST_POOL_ALLOCATION_RULE.md](docs/COST_POOL_ALLOCATION_RULE.md).
Schema, quy tắc ngày/thuế, tests và giới hạn: [SUPPLIER_PRICE.md](docs/SUPPLIER_PRICE.md).
Schema, validation và kiểm thử: [PRODUCT_SKU.md](docs/PRODUCT_SKU.md).
Chi tiết iteration: [PRODUCT_CATEGORY_ITEM_VI.md](docs/PRODUCT_CATEGORY_ITEM_VI.md).
Currency / UoM Category / UoM dùng chung, có full internal access;
conversion mới thuộc công ty mặc định. Xem validation và báo cáo lịch sử
[Currency / UoM](docs/MASTER_DATA_CURRENCY_UOM.md).

Không chạy migrations để tạo lại business tables. Database Costing hiện tại
phải được cung cấp sẵn. Supabase PostgreSQL được giữ nguyên; không dùng Supabase Auth
hoặc user session. CSRF và cookie thông báo success/toast vẫn hoạt động.

## Tailwind

Lần tính giá thành: `/costing/runs/`, tạo Run theo ngày/sản lượng/SKU/phương án,
chạy engine Decimal và lưu kết quả/nguồn/phiên bản/trace. Kết quả thành công khóa;
lịch sử không tính lại, chạy lại tạo record mới. Chuẩn bị các phiên bản/giá/rate
EFFECTIVE; không tự lấy newest hoặc dùng 0 nếu thiếu nguồn. Cơ sở đóng gói nhập
trên form. Resolver và giới hạn: [COSTING_RUN.md](docs/COSTING_RUN.md).

Phương án tính giá thành: `/costing/schemes/`, gồm cấu hình nguồn/phần tử chi phí/
công thức, phiên bản/clone, kiểm tra dependency và kích hoạt có validation gate.
Schema chưa có Product/SKU/manufacturing assignments hoặc selection policy;
app cấu hình không tính giá thành hoặc lấy giá; Costing Run thực thi riêng. Chi tiết scope/rules:
[COSTING_SCHEME.md](docs/COSTING_SCHEME.md).

Formula Engine: `/formula-engine/formulas/` để tạo công thức, kiểm tra/kiểm thử,
lưu bộ kiểm thử và quản lý phiên bản. DSL/activation/giới hạn:
[FORMULA_ENGINE.md](docs/FORMULA_ENGINE.md). Không dùng eval hoặc Supabase Auth;
không chạy Costing/Rule Table trong iteration này.

```powershell
npm run dev:css
```

Chạy trong terminal thứ hai. Sửa `static/src/tailwind.css` và templates/JS;
`static/css/app.css` là generated output. Production build: `npm run build:css`.
Vendor JS local được đồng bộ bằng `npm run build:vendor`.

## Bộ dữ liệu DEMO và đối soát Costing thật

Dùng một dataset Cappuccino xuyên suốt các module đã có để kiểm tra hồi quy.
Các lệnh dưới dùng database trong `.env`, reuse công ty mặc định hiện có; không
tạo công ty, không thay đổi schema, không xóa/ghi đè dữ liệu cũ.

```powershell
python manage.py seed_costing_demo
python manage.py verify_costing_demo --report artifacts/demo-verification.json
```

Seed atomic, chạy lại không nhân bản; dữ liệu khác định nghĩa mẫu bị từ chối.
Verify thực thi engine thật, lưu 3 Run có khóa idempotency ổn định: ngày 07/10/2026,
chạy lại ngày đó sau khi thêm giá/rate tương lai, và ngày 01/11/2026. Kiểm tra
breakdown, conversion, formula/AST, snapshot/hash, lịch sử và GET UI của 22 module.
Golden 10 hộp: **583.000 VND**, **58.300 VND/hộp**; chi phí chung phân bổ theo
NORMAL_CAPACITY (530.000 / 100 hộp), không dùng tỷ lệ % chi phí trực tiếp.
Không có `--reset`: phiên bản hiệu lực và Run đã khóa phải giữ lịch sử theo trigger.
Chi tiết schema/dataset/giới hạn/evidence: [COSTING_DEMO_AUDIT.md](docs/COSTING_DEMO_AUDIT.md).

## Chạy tests cô lập

Kịch bản giá bán: `/pricing/scenarios/`, chọn nguồn Costing đã khóa, lưu Nháp rồi
tính giá. Kết quả cũ giữ snapshot; muốn thay input hãy nhân bản thành mã mới.
Golden Pricing reuse Costing DEMO hiện có, bổ sung phí/thuế và kỳ tương lai idempotent:

```powershell
python manage.py verify_pricing_demo --report artifacts/pricing-scenario-golden.json
```

Golden: giá vốn 58.300 VND/hộp, phí 5% + 1.000, thuế 10%, margin 20% trên giá khách
trả → 89.972,41379310 VND/hộp; toàn bộ delta 0. Không chạy lại hoặc sửa Costing.
Contract tính, files, tests và giới hạn: [PRICING_SCENARIO.md](docs/PRICING_SCENARIO.md).

Script dưới khởi tạo PostgreSQL local trong `.test-postgres`, bind `127.0.0.1:55432`,
chạy Django tests trong `test_costing_slice`, rồi dừng server. Không dùng Supabase.
Cần PostgreSQL 17; đặt `COSTING_PG_BIN` nếu binary ở đường dẫn khác.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

`python manage.py test` mặc định chọn `config.test_settings`; cần instance
PostgreSQL test trên chạy sẵn. Không dùng `--keepdb` hoặc `--parallel`.

Browser tests là tùy chọn:

```powershell
python -m pip install -r requirements-dev.txt
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\artifacts\playwright"
python -m playwright install chromium
$env:COSTING_BROWSER_TESTS = "1"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

Screenshots từ browser tests nằm trong `artifacts/screenshots/` (gitignored).

Đo tải hardening trên DB test cô lập (bật cùng browser để tái lập full regression):

```powershell
$env:COSTING_HARDENING_BENCHMARK = "1"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test.ps1
```

Số đo được lưu vào `artifacts/hardening-performance.json`; đây là benchmark local,
chưa chứng nhận SLO production. Audit dữ liệu hiện có **chỉ đọc**, không repair/delete:

```powershell
python scripts/audit_demo_integrity.py --report artifacts/hardening-integrity.json
```

Lệnh audit dùng DB `.env`, không tạo company/schema, không ghi dữ liệu nghiệp vụ.
Manifest, kết quả hồi quy, Golden/history và giới hạn:
[SYSTEM_HARDENING.md](docs/SYSTEM_HARDENING.md).

Chi tiết file, quyết định kiến trúc, validation và giới hạn:
[FRONTEND_FOUNDATION_COST_ELEMENT.md](docs/FRONTEND_FOUNDATION_COST_ELEMENT.md).
Iteration Currency / UoM: [MASTER_DATA_CURRENCY_UOM.md](docs/MASTER_DATA_CURRENCY_UOM.md).
Kiến trúc hiện tại: [SINGLE_COMPANY_NO_AUTH.md](docs/SINGLE_COMPANY_NO_AUTH.md).
