# Regression report — UI/UX redesign

Ngày kiểm tra: 16/10/2026. Baseline Git: `f4e0030`. Phạm vi là presentation; không triển khai nghiệp vụ hay hạ tầng mới.

**UI/UX REDESIGN COMPLETE — BUSINESS LOGIC PRESERVED**

Full suite cuối: **752 tests trong 275.375s, OK (skipped=1)**. 747 tests cũ giữ nguyên; thêm 5 test presentation. Golden Costing/Pricing, Comparison, production HTTP/static/CSRF/history đều đạt.

## A. Design system

Indigo/Slate light theme, Inter variable local Latin/Vietnamese, body 14px/table 13px, spacing 4/8/16/24px, radius chủ đạo 8px, shadow nhỏ. Lucide static 1.58.0 build 52 SVG symbols; Fontsource Inter 5.3.0. Hover/focus/sidebar motion 160ms và reduced-motion support. Không dark mode, gradient đại trà hoặc icon JavaScript runtime.

[DESIGN_SYSTEM](DESIGN_SYSTEM.md) là hướng dẫn tokens, hierarchy, responsive và local assets; [COMPONENT_CATALOG](COMPONENT_CATALOG.md) mô tả component/state/usage.

## B. Components

- Button primary/secondary/ghost/danger, size sm/md; row icons có accessible name/tooltip và text sr-only.
- Form control/field/section thống nhất, required marker giữ nguyên, readonly/disabled/error rõ.
- Table/filter/search/sort/pagination, code monospace và số tabular; không giấu cột hay đổi page size.
- Panel/metadata/metric chỉ trình bày giá trị backend hiện có; không KPI hoặc phép tính mới.
- Badge/version, modal/drawer, toast, empty/loading/alert/disclosure/navigation theo cùng tokens.
- Hai include mới `icon.html`, `metric.html`; không tạo generic CRUD framework.

## C. Screens

Phủ 28 đích nghiệp vụ/38 template có extends qua shared shell/components và partials: danh mục, sản phẩm/SKU, supplier/price, BOM, bao bì, work center/resource/rate, routing, cost pool/allocation, Formula Studio, Scheme, Run, Pricing Foundation/Scenario/Comparison.

Chi tiết scope/template/luồng nằm trong [SCREEN_ROLLOUT](SCREEN_ROLLOUT.md). Run giữ breakdown/trace/snapshot; Scenario giữ metric/waterfall/fee/tax/FX đã lưu. Comparison chỉ thay layout/sticky/baseline styling.

## D. UX và accessibility

- Gọn/Thoáng: khoảng 44/52px mỗi hàng; lưu localStorage, không ảnh hưởng pagination/DB.
- Sidebar 240/72px; collapsed rail giữ 28 liên kết và tooltip; mobile dùng overlay/focus trap/inert/Escape.
- Error focus trên native response và sau HTMX settle; không sửa lỗi validation, dữ liệu nhập hoặc request.
- HTMX giữ endpoint/payload/CSRF/query; busy state phản ánh request hiện có.
- Keyboard tooltip/focus-visible, th/scope/label/ARIA, reduced motion; bảng rộng scroll trong container.
- Sidebar chỉ animate sau toggle chủ động; layout đầu trang và khi đổi breakpoint không bị che.

## E. Business safety

| Contract | Kết quả đối chiếu |
|---|---|
| Models/database/managed=False/schema/migrations | NONE — không thay đổi |
| Services/selectors/validators/views/forms/settings/URLs hiện có | NONE — 251 Python SHA-256 khớp baseline |
| Costing/Pricing/Formula engines, Decimal, calculations | NONE |
| Required/default/choice/label/validation semantics | NONE — 43 lớp form và biến thể động khớp |
| URL/name/view | NONE — 163 route khớp |
| Menu/nhãn/thứ tự | NONE — 28 đích trong 5 nhóm khớp |
| POST/action/name/value/ID/hx-* hiện có | NONE — source audit không phát hiện mất/đổi/thêm request attrs |
| Effective dates/status/versioning/history/snapshot/trace | NONE |
| Auth/account/Organization/approval flow | Không thêm hoặc đưa trở lại |

`static/js/app.js`, `static/js/htmx-config.js` và vendor HTMX/Alpine giữ nguyên nội dung. Existing tests/expected values và production smoke script không sửa. `alpine-components.js` bổ sung UI state/helpers và giữ nguyên formulaEditor.

### Review binding/condition thủ công

Audit không che giấu template binding khác baseline. Bảy mục báo riêng đã đối chiếu:

| Template | Thay đổi được chấp nhận |
|---|---|
| `components/button.html` | Điều kiện primary/danger để chọn CSS/icon, không thay hành động/label |
| `components/form_field.html` | Điều kiện span của name/description chuyển vào class; trường và wrapper giữ nguyên |
| `components/status_badge.html` | `data-status` dùng status hiện có để style badge |
| `components/toast.html` | `data-severity` lấy message tags hiện có để style/timeout |
| `layouts/sidebar.html` | Active section data và tooltip từ nhãn hiện có; không đổi menu/route |
| `layouts/topbar.html` | Breadcrumb hoặc tên hệ thống theo context; layout trình bày |
| `pricing/scenarios/partials/detail_content.html` | label/value chuyển vào include metric; row.kind thành data attribute waterfall |

`icon.html` include có argument `name` để chọn SVG, không phải POST field. Audit loại riêng include trình bày này khỏi quét HTML request attrs; mọi `name/value` trường/form thật vẫn được kiểm tra. Baseline JSON tạo trước thay đổi, không ghi đè.

## F. Regression và build

### Môi trường

Windows, Python trong `env`, Node 24.11.0/npm 11.6.1, Tailwind 4.3.3, HTMX 2.0.11, Alpine/Focus 3.17.4. Playwright Chromium 1.58 trong `artifacts/ui-redesign/playwright`. PostgreSQL test riêng `127.0.0.1:55432`, `config.test_settings`; không chạm Supabase production.

### Kết quả

| Gate | Kết quả |
|---|---|
| Full baseline trước sửa | 747 tests, 274.724s, OK, 1 benchmark opt-in skip |
| Full suite cuối | 752 tests, 275.375s, OK (751 đạt, 1 benchmark opt-in skip) |
| Django check | `manage.py check` và check với test settings PASS, 0 issues |
| Python/form/URL/menu/HTMX source audit | PASS, errors=[] |
| Golden Costing | 583.000 VND/10 hộp; 58.300 VND/hộp; expected giữ nguyên |
| Golden Pricing | 89.972,41379310 VND/đơn vị; margin 20%; future 92.526,00506044; expected giữ nguyên |
| Responsive smoke mới | 28 đích × 1440/1280/768/390; top-level create forms 1440/390 |
| Reference screenshots | 6 trang × 4 kích thước + collapsed navigation |
| UI interaction | Density/persistence, tooltip keyboard/Escape, mobile inert, reduced motion, first render/resize, focus lỗi |
| Browser console/static requests | PASS, không pageerror hoặc static 404 trong smoke mới |
| JavaScript syntax | `node --check static/js/alpine-components.js` PASS |
| npm clean install | `npm ci --offline=false --cache .npm-cache --no-audit --no-fund` PASS, 75 packages |
| Production frontend build | `npm run build` → build:vendor + build:css PASS |
| Production static | WhiteNoise CompressedManifestStaticFilesStorage, hashed CSS/JS/SVG/fonts PASS; src Tailwind không publish; 0 DB queries |
| Production HTTP/CSRF/safe errors/history | PASS qua Waitress/WhiteNoise; giữ 7 CSS/JS assets, Golden fingerprints và history |

Skip duy nhất là `HardeningVolumeTests.test_volume_and_execution_measurements`, yêu cầu `COSTING_HARDENING_BENCHMARK=1`; đây là benchmark opt-in đã skip ở baseline. Browser tests bật, không skip vì thiếu Chromium.

### Các lỗi trung gian đã xử lý trong presentation

1. Baseline lần đầu thiếu Chromium: cài browser rồi chạy lại toàn bộ **trước** rollout.
2. Bảng rộng chứa sr-only absolute làm page overflow: tạo positioning context cho icon action/table scroll.
3. Transition padding khi resize desktop→mobile làm assertion overflow tức thời: vô hiệu hóa chuyển động layout tại breakpoint.
4. Rà ảnh thấy first-render padding animation có thể che nội dung: animation chỉ bật cho toggle chủ động; thêm kiểm tra sidebar/workspace geometry.
5. npm clean install phát hiện thiếu metadata bundled optional dependency Tailwind WASM trong lock: refresh metadata, xác minh không đổi bất kỳ phiên bản dependency cũ; final lock diff chỉ thêm hai dependency tài nguyên UI.
6. Production smoke phát hiện asset count 8 thay vì 7: gộp helper UI vào `alpine-components.js`; không đổi smoke test/script.
7. Production browser yêu cầu body 14px: giữ 14px, table 13px theo design; không sửa test expected.

Các phase test đã chạy gồm danh mục 169, manufacturing 194, Formula/Scheme/Costing 96, Pricing/UI 122; lỗi breakpoint ở các phase đầu dẫn đến fix CSS và kiểm tra lại. Targeted resize regression 4/4 đạt. Full cuối là gate quyết định, không cộng các phase để báo một tổng test giả.

### Chạy lại

```powershell
npm ci
npm run build
.\env\Scripts\python.exe scripts/audit_ui_contract.py compare
.\env\Scripts\python.exe scripts/verify_ui_static.py
$env:APP_ENV = 'test'
$env:DJANGO_SETTINGS_MODULE = 'config.test_settings'
$env:COSTING_BROWSER_TESTS = '1'
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) 'artifacts\ui-redesign\playwright')
$env:PYTHONIOENCODING = 'utf-8'
.\scripts\test.ps1 apps
```

`scripts/test.ps1` khởi động/dừng cluster test riêng khi chưa chạy; nếu đã có cluster đúng cấu hình thì gọi trực tiếp `manage.py test apps --settings=config.test_settings --noinput`. Cài Chromium bằng Python Playwright nếu chưa có. Script verify static chỉ dùng cấu hình giả process-local, chặn DB và xuất vào artifacts.

Artifacts local: `baseline-tests.log`, `final-full-tests.log`, `contract-comparison.json`, `production-build.log`, `npm-ci.log`, `collectstatic.log`, `static-verification.json`, `before/`, `after/` trong `artifacts/ui-redesign/`. Production HTTP test còn xuất `artifacts/production-http-smoke.json`. Các file này được ignore, không là runtime dependency.

## G. Files

### Tạo mới

- `templates/components/icon.html`, `templates/components/metric.html`.
- `apps/master_data/templatetags/ui_tags.py`: mapping nhãn→icon thuần trình bày, không query/ORM/auth/business rule.
- `apps/master_data/test_ui_redesign.py`: 5 test mới (1 contract + 4 browser), không thay test cũ.
- `scripts/audit_ui_contract.py`, `scripts/verify_ui_static.py`: bằng chứng baseline/static, chặn DB.
- `static/vendor/fonts/inter-latin-wght-normal.woff2`, `inter-vietnamese-wght-normal.woff2`, `LICENSE-Inter`.
- `static/vendor/lucide/sprite.svg`, `LICENSE`.
- Sáu tài liệu `UI_BASELINE.md`, `UI_AUDIT.md`, `DESIGN_SYSTEM.md`, `COMPONENT_CATALOG.md`, `SCREEN_ROLLOUT.md`, `REGRESSION_REPORT.md` và `ui-contract-baseline.json`.

### Sửa hiện có

89 file tracked: 81 HTML templates (base 1, layouts 5, components 13, shared partials 3, master_data 10, product 1, bom 20, formula_engine 7, costing 14, pricing 7); `static/src/tailwind.css`, generated `static/css/app.css`, `static/js/alpine-components.js`; `scripts/build-vendor.cjs`; `package.json`, `package-lock.json`; `docs/00_AI_CONTEXT.md`, `docs/FRONTEND_IMPLEMENTATION_SPEC.md`.

Không sửa Python backend hiện có. Các file hướng dẫn người dùng untracked có từ task trước được giữ nguyên. Không xóa file nguồn hiện có; helper `ui.js` thử trong rollout đã gộp vào asset UI sẵn có, không còn reference/file dư thừa trong kết quả cuối.

### Dependency và kích thước

Chỉ thêm dev dependency `@fontsource-variable/inter=5.3.0`, `lucide-static=1.58.0`; tất cả phiên bản dependency cũ giữ nguyên. Build chỉ ship font subsets/sprite cần dùng. Font Latin 48.256 byte, Vietnamese 10.252 byte; sprite 10.878 byte; UI JS khoảng 6,6 KB, CSS khoảng 38 KB trước compression. Không icon/font CDN hoặc service bên ngoài.

## H. Issues và giới hạn

Chưa có business regression được phát hiện. Không còn lỗi overflow/sidebar overlap trong smoke đã kiểm tra. Bảng nhiều cột cố ý giữ scroll ngang thay vì bỏ dữ liệu. Native date picker/select vẫn phụ thuộc browser/OS; không thay widget/format contract để ép giao diện đồng nhất.

Đã kiểm tra Chromium; chưa chạy Firefox/WebKit hoặc nghiệm thu screen reader/WCAG đầy đủ. Benchmark dung lượng opt-in không chạy. Smoke/ảnh không bao phủ mọi tổ hợp dữ liệu thực tế. Chưa deploy lên Render; cấu hình build/start hiện có giữ nguyên. Các giới hạn nghiệp vụ có trước redesign không được sửa trong task này.

**UI/UX REDESIGN COMPLETE — BUSINESS LOGIC PRESERVED**

## Deep UI verification — 17/10/2026

Phase này thực hiện tại **D:\TANPHONGJSC\HeThongTinhGiaThanh\TanPhong_Hethongtinhgia**.
Full regression với recording runner: **758 tests, 541.840s, OK (skipped=1)**;
skip duy nhất vẫn là benchmark dung lượng opt-in. Sáu test mới chạy, không sửa test
hoặc expected values cũ. Chromium kiểm tra 152 document GET ở 5 viewport; các fragment
được kiểm tra trong host qua HTMX, cùng Firefox/WebKit targeted smoke.

Bằng chứng cuối: **160 UI route surfaces COMPLETE**, 3 technical/redirect endpoints
NOT APPLICABLE; **PARTIAL/NOT COVERED/UNKNOWN = 0**. 151 templates classified/compiled,
150 template runtime có observation; version_badge chưa có caller được giữ nguyên.
Có 1.016 browser observations, 49 representative/fixed screenshots.

Các issue thực đã sửa: baseline select với tên dài; thiếu wrapper ID ở Scheme line
full page; header Cost Element mã dài; overflow text trong modal; focus lỗi sau
HTMX drawer validation. Bốn nút noscript, hai link version và Hủy Studio chuẩn hóa
style. Chỉ 9 template, CSS và UI helper JS thay đổi; không Python runtime changes.
Audit 256 file phase và canonical 251 business Python/43 forms/163 URLs/28 menu
giữ nguyên; baseline JSON không sửa. npm ci/build/check/WhiteNoise manifest PASS.

Xem [UI_COVERAGE_MATRIX](UI_COVERAGE_MATRIX.md),
[COMPONENT_COVERAGE](COMPONENT_COVERAGE.md),
[REMAINING_UI_AUDIT](REMAINING_UI_AUDIT.md) và
[JSON evidence](ui-coverage-evidence.json) để xem phạm vi, state và giới hạn.
Native widgets giữ nguyên; chưa screen-reader/WCAG certification và cross-browser
chưa exhaustive. Tailwind watcher đã tạm dừng để giải phóng native binary khi npm ci;
bật lại bằng npm run dev:css nếu cần.

**FINAL UI COVERAGE VERIFIED — NO KNOWN USER-FACING UI GAPS**
