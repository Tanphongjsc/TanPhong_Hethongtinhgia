# Remaining UI audit — final pass 17/10/2026

Project: D:\TANPHONGJSC\HeThongTinhGiaThanh\TanPhong_Hethongtinhgia. Phạm vi chỉ verification/polish, giữ Design System và business contracts.

## A. Coverage found

| Metric | Result |
|---|---|
| templates | 151 |
| full_page_extends | 38 |
| partials | 90 |
| components | 18 |
| layouts | 5 |
| routes | 163 |
| GET_routes | 159 |
| user_facing_routes | 160 |
| user_facing_GET_routes | 156 |
| forms | 43 |
| navigation | 28 |

Full suite: 758 tests; failures=0, errors=0, skipped=1.

Dynamic requests=2706; browser observations=1016; engines Chromium/Firefox/WebKit. 163 routes và 151 templates classified/compiled; 150 runtime templates rendered, version_badge unused.

## B. Screens actually incomplete — fixed

| Surface | ISSUE có bằng chứng | Presentation fix |
|---|---|---|
| Comparison | 5 tên dài làm trang tràn 23px ở 1440 | Giới hạn baseline native select trong toolbar |
| Scheme line full page | hx-sync tham chiếu ID không tồn tại, gây JS null | Bổ sung wrapper ID đúng selector đã có, giữ hx-* |
| Cost Element header | Mã 120 ký tự làm tràn ở 1024 | min-width/wrap/break-all, giữ nguyên code |
| Modal | Nội dung scrollWidth 974 > clientWidth 510 | Wrap text, giữ confirmation |

## C. Partials actually incomplete — fixed

Bốn nút noscript fallback, hai link tạo phiên bản và Hủy Studio dùng style cũ đã chuẩn hóa. Source scan trước pass có 5 partial legacy và 1 component fallback; các lỗi DOM được bổ sung bằng chứng riêng.

## D. Components actually incomplete — fixed

| Surface | ISSUE có bằng chứng | Presentation fix |
|---|---|---|
| Drawer invalid | Trap giành focus ô lỗi sau swap | UI helper autofocus cùng ô aria-invalid |
| Fallback/actions | 4 nút noscript, 2 link version, Hủy Studio lệch style | Map về button variants hiện có |

Source delta so phase baseline: templates/bom/packaging/partials/version_rows.html, templates/bom/partials/version_rows.html, templates/components/pagination.html, templates/costing/line_form.html, templates/formula_engine/partials/studio_content.html, templates/master_data/partials/cost_element_detail_content.html, templates/master_data/partials/cost_element_table.html, templates/master_data/partials/reference_data_table.html, templates/pricing/comparison/partials/content.html. CSS/JS UI helper thay riêng; không Python runtime changes.

## E. State coverage gaps

Đã audit empty/one/many records, invalid/preserved input, DRAFT/EFFECTIVE/readonly/disabled/LOCKED/FAILED/history, loading/HTMX, pagination, no-JS và comparison 2/5 columns. DOM visual fixtures được phân biệt với persisted/business fixtures.

LIMITATION: không exhaustive mọi tổ hợp dữ liệu; không tạo trạng thái stored mới. COMPLETED/SUPERSEDED không bị thêm vào workflow để đủ checklist.

## F. Responsive issues

Các overflow comparison/header/modal đã sửa. Smoke 1440/1280/1024/768/390 không còn lỗi đã biết; bảng scroll ngang là INTENTIONAL DESIGN DECISION.

## G. Accessibility issues

Labels/th/scope/ARIA/icon names, keyboard/focus-visible, trap/return, Escape/backdrop, error focus và reduced motion được kiểm tra. LIMITATION: chưa screen reader/WCAG certification.

## H. Browser limitations

Chromium full document sweep; Firefox/WebKit targeted layouts/forms/error focus. Không tuyên bố exhaustive full suite trên mọi browser.

## I. Intentionally unchanged native controls

Date/select/number/checkbox giữ native widgets; radio chưa có runtime use case. Browser/OS khác nhau không mặc định là bug. Format/default/required/choices/precision/labels không đổi.

## J. No-action items

- Giữ palette/font/icons/radius/shadows/motion và shell/sidebar/component architecture.
- Giữ unused version_badge/skeleton/radio; không thêm use case giả.
- Formula EFFECTIVE edit chuyển sang detail chỉ đọc là behavior đúng, không tạo form disabled mới.
- Contextual inline loading/compact empty rows giữ nguyên request IDs/text.
- Không Auth/Organization/approval/features mới.

Frozen phase audit: 256 files unchanged; canonical 251 business Python, 43 forms, 163 URLs, 28 menu, errors=[]. Baseline JSON không sửa.

Trước pass, trạng thái dựa trên request đã quan sát và templates có gap đã chứng minh; NOT COVERED là thiếu bằng chứng động, không khẳng định route hỏng.

| Before route status | Count |
|---|---|
| COMPLETE | 102 |
| NOT APPLICABLE | 3 |
| NOT COVERED | 3 |
| PARTIAL | 55 |

| Final route status | Count |
|---|---|
| COMPLETE | 160 |
| NOT APPLICABLE | 3 |

PARTIAL=0; NOT COVERED=0; UNKNOWN=0 cho UI. 3 technical/redirect endpoints NOT APPLICABLE. Intentional unchanged decisions không cộng vào route count.

## Files

Created: apps/master_data/test_ui_coverage.py, apps/master_data/ui_coverage_testing.py, scripts/audit_ui_coverage.py, scripts/report_ui_coverage.py; UI_COVERAGE_MATRIX.md, COMPONENT_COVERAGE.md, REMAINING_UI_AUDIT.md, ui-coverage-evidence.json.

Modified: 9 templates listed above, static/src/tailwind.css, generated static/css/app.css, static/js/alpine-components.js; documentation cross-references. No existing Python runtime file touched.

## Evidence / reproduction

Run scripts/audit_ui_coverage.py inventory; full tests với --testrunner=apps.master_data.ui_coverage_testing.DeepUICoverageRunner, UI_COVERAGE_PHASE=after, COSTING_BROWSER_TESTS=1; audit_ui_contract.py compare --report artifacts/ui-deep-coverage/contract-final.json; audit_ui_coverage.py check; scripts/report_ui_coverage.py.

```powershell
$env:APP_ENV='test'
$env:DJANGO_SETTINGS_MODULE='config.test_settings'
$env:COSTING_BROWSER_TESTS='1'
$env:UI_COVERAGE_PHASE='after'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path (Get-Location) 'artifacts/ui-deep-coverage/playwright'
$env:PYTHONIOENCODING='utf-8'
.\env\Scripts\python.exe -m playwright install chromium firefox webkit
.\scripts\test.ps1 apps --testrunner=apps.master_data.ui_coverage_testing.DeepUICoverageRunner
.\env\Scripts\python.exe scripts/audit_ui_contract.py compare --report artifacts/ui-deep-coverage/contract-final.json
.\env\Scripts\python.exe scripts/audit_ui_coverage.py check
.\env\Scripts\python.exe scripts/report_ui_coverage.py
```

Raw logs/JSON/screenshots nằm trong artifacts/ui-deep-coverage; summary và source hashes/classifications trong ui-coverage-evidence.json được giữ cùng docs. Artifacts không là runtime dependency.

Initial recording attempt có 9 lỗi observer đọc lại unresolved 404 URL. Observer đã sửa; ứng dụng/test cũ không đổi. Full suite cuối là gate nghiệm thu.

npm ci/build/check/static verification PASS. Đã tạm dừng đúng Tailwind watcher khóa native binary; muốn tiếp tục watcher chạy npm run dev:css tại repo này.

Golden Costing 583.000 VND/10 hộp, 58.300 VND/hộp; Pricing 89.972,41379310, margin 20%; future 92.526,00506044 giữ nguyên. Production HTTP/CSRF/safe errors/history/WhiteNoise đã chạy qua tests cũ không sửa.

FINAL UI COVERAGE VERIFIED — NO KNOWN USER-FACING UI GAPS
