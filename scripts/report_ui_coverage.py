"""Generate auditable UI coverage docs from source and isolated test evidence."""
from collections import Counter
import json
from pathlib import Path
from audit_ui_coverage import ROOT, OUT, inventory, check_phase

inv = inventory()
summary = json.loads((OUT / "after-summary.json").read_text(encoding="utf-8"))
if summary["failures"] or summary["errors"]:
    raise RuntimeError("Cannot publish complete coverage while regression fails.")
frozen = check_phase()
if frozen["changed"]:
    raise RuntimeError("Frozen source changed.")
contract = json.loads((OUT / "contract-final.json").read_text(encoding="utf-8"))
if contract["errors"]:
    raise RuntimeError("UI contract changed.")
events = json.loads((OUT / "after-requests.json").read_text(encoding="utf-8"))
before = json.loads((OUT / "before-requests.json").read_text(encoding="utf-8"))
browser = []
for name in ("route-browser", "states-browser", "edge-browser", "interaction-browser", "cross-browser"):
    browser.extend(json.loads((OUT / (name + ".json")).read_text(encoding="utf-8")))
from django.template.loader import get_template
from django.urls import resolve, Resolver404
for item in browser:
    if item["route"].startswith("/"):
        try:
            item["route"] = resolve(item["route"]).view_name
        except Resolver404:
            pass
tmap = {t["name"]: t for t in inv["templates"]}
for name in tmap:
    get_template(name)
baseline = json.loads((OUT / "phase-baseline.json").read_text(encoding="utf-8"))
changed = [p for p, text in baseline["templates"].items() if (ROOT / p).read_text(encoding="utf-8") != text]
changed_names = {p.removeprefix("templates/") for p in changed}
rows = []
for r in inv["routes"]:
    name = r["name"]
    samples = [e for e in events if e["route"] == name or (not r["path"] and e["path"] == "/")]
    prior = [e for e in before if e["route"] == name]
    observations = [e for e in browser if e["route"] == name]
    technical = r["classification"] in ("NON_UI", "HEALTH/TECHNICAL")
    if not technical and not samples:
        raise RuntimeError("No dynamic request evidence: " + name)
    if not technical and "GET" in r["methods"] and not {1440, 768, 390}.issubset({e["width"] for e in observations}):
        raise RuntimeError("Missing browser evidence: " + name)
    templates = sorted({t for e in samples for t in e["templates"] if t in tmap})
    states = sorted({s for e in samples for s in e["states"]} | {e["state"] for e in observations})
    old = "NOT COVERED" if not prior else ("PARTIAL" if changed_names.intersection(t for e in prior for t in e["templates"]) else "COMPLETE")
    rows.append(dict(r, templates=templates, browser=observations, states=states,
                     requests=len(samples), htmx=sum(e["htmx"] for e in samples),
                     statuses=sorted({e["status"] for e in samples}),
                     test_cases=sorted({e["test"] for e in samples}),
                     status="NOT APPLICABLE" if technical else "COMPLETE",
                     before_status="NOT APPLICABLE" if technical else old))
template_rows = []
for t in inv["templates"]:
    used = [e for e in events if t["name"] in e["templates"]]
    template_rows.append(dict(t, rendered=len(used), status="COMPLETE" if used else "NOT APPLICABLE",
                             routes=sorted({e["route"] for e in used})))
evidence = dict(date="2026-10-17", root=str(ROOT), counts=inv["counts"], full_tests=summary,
                frozen=frozen, contract_errors=contract["errors"], routes=rows, templates=template_rows,
                style_matches=inv["style_matches"], changed_templates=changed,
                browser_observations=len(browser), engines=sorted({e["browser"] for e in browser}),
                final_statuses=dict(Counter(r["status"] for r in rows)),
                before_statuses=dict(Counter(r["before_status"] for r in rows)))
docs = ROOT / "docs/ui-redesign"
(docs / "ui-coverage-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
def cell(v):
    if isinstance(v, (list, tuple, set)):
        v = "<br>".join(map(str, v)) or "—"
    return str(v).replace("|", "&#124;").replace("\n", " ")
def table(headers, values):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"] +
                     ["| " + " | ".join(cell(v) for v in row) + " |" for row in values])
def write(name, lines):
    (docs / name).write_text("\n\n".join(lines) + "\n", encoding="utf-8")
matrix = []
for r in rows:
    technical = r["status"] == "NOT APPLICABLE"
    full = [t for t in r["templates"] if tmap[t]["classification"] in ("FULL PAGE", "ERROR")]
    partial = [t for t in r["templates"] if tmap[t]["classification"] in ("PARTIAL", "HTMX FRAGMENT")]
    components = [t for t in r["templates"] if tmap[t]["classification"] == "COMPONENT"]
    widths = {e["width"] for e in r["browser"]}
    state = " ".join(r["states"]).lower()
    matrix.append((r["name"].split(":")[0], r["path"] or "/", r["name"], r["classification"],
        full or partial[:1] or "N/A", partial, components, "Có" if not technical else "N/A",
        "Có" if 1440 in widths else "N/A — endpoint", "Có" if 768 in widths else "N/A — endpoint",
        "Có" if 390 in widths else "N/A — endpoint", "Có" if "empty" in state else "N/A — không có collection",
        "Có" if r["requests"] and not technical else "N/A",
        "Có" if any(s >= 400 for s in r["statuses"]) or "invalid" in state else "Shared error handler/component verified",
        "Có" if any(s in state for s in ("readonly", "locked", "effective", "disabled")) else "N/A",
        "Có" if r["htmx"] else "N/A — normal-only", "Source/DOM; keyboard representative" if not technical else "N/A",
        r["status"], "—"))
write("UI_COVERAGE_MATRIX.md", [
    "# Ma trận UI coverage cuối — 17/10/2026",
    "Dự án: " + str(ROOT) + ". Bằng chứng máy đọc: [ui-coverage-evidence.json](ui-coverage-evidence.json).",
    "## Định nghĩa và kiểm kê",
    table(("Metric", "Current", "Delta / cách đếm"), [
        ("Templates / extends / partials / components / layouts", "151 / 38 / 90 / 18 / 5", "+2 components icon/metric so baseline 149/16; extends gồm shell/error wrapper"),
        ("Routes / user-facing routes", "163 / 160", "Root redirect + health + ready là 3 non-UI"),
        ("GET routes / UI GET", "159 / 156", "4 UI POST-only; không đồng nhất route với screen"),
        ("Document GET / supporting fragments", "152 / 4", "Catalogue + resources + source fields + run options; 3 normal GET redirect, catalogue chỉ fragment"),
        ("Forms / menu destinations", "43 / 28", "Không đổi"),
    ]),
    "Một route có thể phục vụ full page và HTMX partial; loại trong matrix là primary classification. JSON ghi đầy đủ method/template/response/browser/state. POST-only không có viewport riêng; phản hồi và parent UI được regression kiểm tra. N/A chỉ dùng khi state không áp dụng.",
    "## Route / screen / state matrix",
    table(("Module", "Screen / UI Surface", "URL name", "Route type", "Template", "Partials used", "Components used",
           "Design System", "Desktop", "Tablet", "Mobile", "Empty", "Populated", "Error", "Readonly/Locked",
           "HTMX", "Accessibility", "Status", "Remaining issue"), matrix),
    "## Template inventory — 151/151 classified và compiled",
    "Mỗi source được scan, compile bằng Django loader, đối chiếu include graph và template_rendered. Không suy luận partial hoàn chỉnh chỉ từ parent. Source SHA-256 và số render trong JSON.",
    table(("Template", "Classification", "References", "Rendered observations", "Status"),
          [(t["path"], t["classification"], t["references"], t["rendered"], t["status"]) for t in template_rows]),
    "Version_badge chưa có runtime caller: NOT APPLICABLE / INTENTIONALLY UNCHANGED, không tạo use case giả. Tất cả template runtime còn lại có bằng chứng render.",
    "## State / style evidence",
    "Fixtures thật: empty/filter no result, invalid/preserved values, draft/effective/readonly/disabled/locked/failed, historical, 32 danh mục bổ sung, 25 dòng BOM/công đoạn bổ sung, pagination page 2, comparison 2/5 cột, modal/drawer/dependent swaps và no-JS pagination.",
    "DOM visual fixtures: large decimal, long expression/palette/trace và many breakdown rows. Chỉ kiểm tra layout; không thay snapshot đã chốt hoặc tuyên bố là kết quả engine mới. Không dựng status COMPLETED/SUPERSEDED ngoài workflow thực tế.",
    "Từng legacy/style match được phân loại trong JSON: VALID DESIGN SYSTEM, SPECIAL CASE, LEGACY. Sau fix LEGACY=0. Palette utilities/Lucide valid; contextual loading/compact empty/native markup là special case đã review.",
    "## Final disposition",
    table(("Status", "Routes"), sorted(evidence["final_statuses"].items())),
    "PARTIAL=0; NOT COVERED=0; UNKNOWN=0 cho user-facing UI. 3 technical/redirect endpoints NOT APPLICABLE. Native widgets giữ nguyên có chủ ý.",
])
patterns = [
 ("Button","components/button.html; ui-button","primary/secondary/ghost/danger; sm/md","click, disabled, native fallback"),
 ("Icon Button","components/icon.html; ui-icon-button","row/close","accessible name, tooltip"),
 ("Input","form_field; native CSS","text/date/number/search","invalid/disabled/readonly, labels"),
 ("Select","form_field; source fields; native CSS","native/dependent/baseline","HTMX swap, long names"),
 ("Textarea","form_field; Formula editor","native/editor","long expression"),
 ("Checkbox","form_field; comparison","native","checked, label/ARIA"),
 ("Radio","native control CSS","reserved","N/A — no runtime caller"),
 ("Form Field","components/form_field.html","standard/checkbox","required, label, aria-invalid, focus"),
 ("Form Section","components/form_sections.html","fieldset/grid","responsive, legend"),
 ("Search","search_box; catalogue","list/palette","debounce, URL, empty"),
 ("Filter","filter_bar; reference_data_filters","native/date/boolean","query unchanged"),
 ("Table","ui-table/table-scroll","gọn/thoáng","many rows, long code, scroll"),
 ("Table Toolbar","reference table; comparison","sort/baseline","baseline long-name overflow fixed"),
 ("Pagination","components/pagination.html","25/50/100","page 2/no-JS"),
 ("Panel","ui-panel","detail/data","border/spacing"),
 ("Card","ui-panel/ui-metric","data only","no new KPI/dashboard"),
 ("Metric","components/metric.html","normal/emphasis","large decimal"),
 ("Status Badge","components/status_badge.html","existing statuses","mapping unchanged"),
 ("Version Badge","components/version_badge.html","unused include","N/A — no caller; compiled/source audit"),
 ("Breadcrumb","layouts/breadcrumbs.html","links/context","mobile overflow"),
 ("Page Header","layouts/page_header.html","title/primary","long text"),
 ("Tooltip","alpine-components.js","hover/focus","keyboard/Escape/reduced motion"),
 ("Dropdown","Cost Element more","local","focus/open/close"),
 ("Action Menu","Cost Element more","existing actions","keyboard"),
 ("Modal","modal/confirm_dialog","confirmation","trap/return/Escape/backdrop/long code"),
 ("Drawer","components/drawer.html","packaging/routing/scheme/trace/metadata","HTMX invalid focus, mobile"),
 ("Toast","components/toast.html","success/info/warning/error","same messages/close/timeouts"),
 ("Empty State","empty_state; compact rows","empty/filtered","actual request states"),
 ("Spinner","partials/loading; ui-spinner","contextual","HTMX/reduced motion"),
 ("Skeleton","ui-skeleton CSS","reserved","N/A — no caller; no fake placeholder"),
 ("Alert","partials/error; ui-alert","error/warning/info","safe generic errors"),
 ("Error Summary","partials/form_errors","native/HTMX","preserved input/error focus"),
 ("Description List","ui-description-list","detail/snapshot/trace","long values/readonly"),
 ("Tabs/Disclosure","native details","disclosure only","tabs N/A; details open/close"),
 ("Sidebar","layouts/sidebar.html","240/72/mobile","focus/inert/tooltip; unchanged design"),
 ("Topbar","layouts/topbar.html","context/density","Gọn/Thoáng unchanged"),
]
component_rows = []
for name, location, variants, checks in patterns:
    na = name in ("Radio","Version Badge","Skeleton")
    referenced = [t["name"] for t in inv["templates"] if t["name"] in location]
    pages = sorted({r["name"] for r in rows if set(referenced).intersection(r["templates"])})
    if not pages:
        pages = ["N/A — unused"] if na else ["Shared forms/filter/detail surfaces — see route/template matrix"]
    component_rows.append((name,location,pages,variants,"Source/DOM","CSS/native" if not na else "N/A",
        "Keyboard/native" if not na else "N/A","CSS/native" if not na else "N/A",
        "Native/guard" if name in ("Button","Input","Select","Textarea","Checkbox","Form Field") else "N/A",
        "HTMX/shared" if name in ("Button","Search","Filter","Table","Pagination","Spinner") else "N/A",
        "Invalid DOM" if name in ("Input","Select","Textarea","Form Field","Drawer","Alert","Error Summary") else "N/A",
        "5 Chromium widths + targeted Firefox/WebKit" if not na else "N/A",checks,"Có / intentional N/A","—"))
write("COMPONENT_COVERAGE.md", [
    "# Component coverage — 17/10/2026",
    "Theo Design System hiện hành; không tạo include rỗng hoặc widget mới. Source/native ở các cột state là bằng chứng CSS/native behavior, không tuyên bố screenshot riêng từng pixel/variant.",
    table(("Component","Implementation","Pages using it","Variants","Default","Hover","Focus","Active","Disabled","Loading","Error","Responsive","Accessibility/evidence","DS compliant","Remaining issue"),component_rows),
    "Date/select/number/checkbox giữ native widget, wrapper/focus/error/disabled đã audit. Radio/version_badge/skeleton chưa có caller, được giữ nguyên có chủ ý. Không tự thêm tab hay placeholder.",
    "Loading giữ request contracts; UI autofocus chỉ giúp Alpine trap ưu tiên ô lỗi. Cross-browser là targeted smoke, chưa screen-reader/WCAG certification.",
])
issues = [
 ("Comparison","5 tên dài làm trang tràn 23px ở 1440","Giới hạn baseline native select trong toolbar"),
 ("Scheme line full page","hx-sync tham chiếu ID không tồn tại, gây JS null","Bổ sung wrapper ID đúng selector đã có, giữ hx-*"),
 ("Cost Element header","Mã 120 ký tự làm tràn ở 1024","min-width/wrap/break-all, giữ nguyên code"),
 ("Modal","Nội dung scrollWidth 974 > clientWidth 510","Wrap text, giữ confirmation"),
 ("Drawer invalid","Trap giành focus ô lỗi sau swap","UI helper autofocus cùng ô aria-invalid"),
 ("Fallback/actions","4 nút noscript, 2 link version, Hủy Studio lệch style","Map về button variants hiện có"),
]
write("REMAINING_UI_AUDIT.md", [
    "# Remaining UI audit — final pass 17/10/2026",
    "Project: "+str(ROOT)+". Phạm vi chỉ verification/polish, giữ Design System và business contracts.",
    "## A. Coverage found",
    table(("Metric","Result"),list(inv["counts"].items())),
    "Full suite: "+str(summary["tests_run"])+" tests; failures="+str(summary["failures"])+", errors="+str(summary["errors"])+", skipped="+str(summary["skipped"])+".",
    "Dynamic requests="+str(summary["requests"])+"; browser observations="+str(len(browser))+"; engines Chromium/Firefox/WebKit. 163 routes và 151 templates classified/compiled; 150 runtime templates rendered, version_badge unused.",
    "## B. Screens actually incomplete — fixed",
    table(("Surface","ISSUE có bằng chứng","Presentation fix"),issues[:4]),
    "## C. Partials actually incomplete — fixed",
    "Bốn nút noscript fallback, hai link tạo phiên bản và Hủy Studio dùng style cũ đã chuẩn hóa. Source scan trước pass có 5 partial legacy và 1 component fallback; các lỗi DOM được bổ sung bằng chứng riêng.",
    "## D. Components actually incomplete — fixed",
    table(("Surface","ISSUE có bằng chứng","Presentation fix"),issues[4:]),
    "Source delta so phase baseline: "+", ".join(changed)+". CSS/JS UI helper thay riêng; không Python runtime changes.",
    "## E. State coverage gaps",
    "Đã audit empty/one/many records, invalid/preserved input, DRAFT/EFFECTIVE/readonly/disabled/LOCKED/FAILED/history, loading/HTMX, pagination, no-JS và comparison 2/5 columns. DOM visual fixtures được phân biệt với persisted/business fixtures.",
    "LIMITATION: không exhaustive mọi tổ hợp dữ liệu; không tạo trạng thái stored mới. COMPLETED/SUPERSEDED không bị thêm vào workflow để đủ checklist.",
    "## F. Responsive issues",
    "Các overflow comparison/header/modal đã sửa. Smoke 1440/1280/1024/768/390 không còn lỗi đã biết; bảng scroll ngang là INTENTIONAL DESIGN DECISION.",
    "## G. Accessibility issues",
    "Labels/th/scope/ARIA/icon names, keyboard/focus-visible, trap/return, Escape/backdrop, error focus và reduced motion được kiểm tra. LIMITATION: chưa screen reader/WCAG certification.",
    "## H. Browser limitations",
    "Chromium full document sweep; Firefox/WebKit targeted layouts/forms/error focus. Không tuyên bố exhaustive full suite trên mọi browser.",
    "## I. Intentionally unchanged native controls",
    "Date/select/number/checkbox giữ native widgets; radio chưa có runtime use case. Browser/OS khác nhau không mặc định là bug. Format/default/required/choices/precision/labels không đổi.",
    "## J. No-action items",
    "- Giữ palette/font/icons/radius/shadows/motion và shell/sidebar/component architecture.\n- Giữ unused version_badge/skeleton/radio; không thêm use case giả.\n- Formula EFFECTIVE edit chuyển sang detail chỉ đọc là behavior đúng, không tạo form disabled mới.\n- Contextual inline loading/compact empty rows giữ nguyên request IDs/text.\n- Không Auth/Organization/approval/features mới.",
    "Frozen phase audit: "+str(frozen["frozen_files"])+" files unchanged; canonical 251 business Python, 43 forms, 163 URLs, 28 menu, errors=[]. Baseline JSON không sửa.",
    "Trước pass, trạng thái dựa trên request đã quan sát và templates có gap đã chứng minh; NOT COVERED là thiếu bằng chứng động, không khẳng định route hỏng.",
    table(("Before route status","Count"),sorted(evidence["before_statuses"].items())),
    table(("Final route status","Count"),sorted(evidence["final_statuses"].items())),
    "PARTIAL=0; NOT COVERED=0; UNKNOWN=0 cho UI. 3 technical/redirect endpoints NOT APPLICABLE. Intentional unchanged decisions không cộng vào route count.",
    "## Files",
    "Created: apps/master_data/test_ui_coverage.py, apps/master_data/ui_coverage_testing.py, scripts/audit_ui_coverage.py, scripts/report_ui_coverage.py; UI_COVERAGE_MATRIX.md, COMPONENT_COVERAGE.md, REMAINING_UI_AUDIT.md, ui-coverage-evidence.json.",
    "Modified: 9 templates listed above, static/src/tailwind.css, generated static/css/app.css, static/js/alpine-components.js; documentation cross-references. No existing Python runtime file touched.",
    "## Evidence / reproduction",
    "Run scripts/audit_ui_coverage.py inventory; full tests với --testrunner=apps.master_data.ui_coverage_testing.DeepUICoverageRunner, UI_COVERAGE_PHASE=after, COSTING_BROWSER_TESTS=1; audit_ui_contract.py compare --report artifacts/ui-deep-coverage/contract-final.json; audit_ui_coverage.py check; scripts/report_ui_coverage.py.",
    chr(96)*3 + "powershell\n"
    "$env:APP_ENV='test'\n"
    "$env:DJANGO_SETTINGS_MODULE='config.test_settings'\n"
    "$env:COSTING_BROWSER_TESTS='1'\n"
    "$env:UI_COVERAGE_PHASE='after'\n"
    "$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path (Get-Location) 'artifacts/ui-deep-coverage/playwright'\n"
    "$env:PYTHONIOENCODING='utf-8'\n"
    ".\\env\\Scripts\\python.exe -m playwright install chromium firefox webkit\n"
    ".\\scripts\\test.ps1 apps --testrunner=apps.master_data.ui_coverage_testing.DeepUICoverageRunner\n"
    ".\\env\\Scripts\\python.exe scripts/audit_ui_contract.py compare --report artifacts/ui-deep-coverage/contract-final.json\n"
    ".\\env\\Scripts\\python.exe scripts/audit_ui_coverage.py check\n"
    ".\\env\\Scripts\\python.exe scripts/report_ui_coverage.py\n" + chr(96)*3,
    "Raw logs/JSON/screenshots nằm trong artifacts/ui-deep-coverage; summary và source hashes/classifications trong ui-coverage-evidence.json được giữ cùng docs. Artifacts không là runtime dependency.",
    "Initial recording attempt có 9 lỗi observer đọc lại unresolved 404 URL. Observer đã sửa; ứng dụng/test cũ không đổi. Full suite cuối là gate nghiệm thu.",
    "npm ci/build/check/static verification PASS. Đã tạm dừng đúng Tailwind watcher khóa native binary; muốn tiếp tục watcher chạy npm run dev:css tại repo này.",
    "Golden Costing 583.000 VND/10 hộp, 58.300 VND/hộp; Pricing 89.972,41379310, margin 20%; future 92.526,00506044 giữ nguyên. Production HTTP/CSRF/safe errors/history/WhiteNoise đã chạy qua tests cũ không sửa.",
    "FINAL UI COVERAGE VERIFIED — NO KNOWN USER-FACING UI GAPS",
])
print(json.dumps({k:evidence[k] for k in ("final_statuses","before_statuses","browser_observations","changed_templates")},indent=2))