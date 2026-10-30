# Báo cáo triển khai chức năng Xóa

Ngày: 21/10/2026. Dự án được sửa: **D:/TANPHONGJSC/HeThongTinhGiaThanh/TanPhong_Hethongtinhgia**. Không triển khai vào thư mục dự án cũ.

## Kết quả và phạm vi

- Kiểm kê 51 model business, 28 đích sidebar và 38 loại dữ liệu có chính sách tại lớp xóa.
- 36 loại có xóa có điều kiện; 2 loại giữ lại: CostingRun và FormulaTestCase. FormulaDependency được xóa cùng bản nháp sở hữu, không có xóa độc lập.
- 13 model không có endpoint xóa riêng được phân loại trong [ma trận](DELETE_COVERAGE_MATRIX.md). So sánh kịch bản và các trang nguồn/trace chỉ đọc, không tạo dữ liệu mới để xóa.
- Không còn phạm vi CRUD hiện hành chưa có quyết định. Hai giới hạn cần thiết kế lưu giữ lịch sử nếu muốn mở rộng sau này: dọn Run lỗi mà vẫn giữ khóa chống gửi lặp; xóa cứng bộ kiểm thử mà vẫn xác định được lịch sử sử dụng. Task này giữ nguyên schema.
- Không thêm dependency. Không sửa model, migrations, engine, công thức hoặc expected Golden. Không thêm Authentication, Organization UI, workflow hay business audit log.

## Cách dùng

Mở chi tiết danh mục/cấu hình, chọn **Xóa …** ở phần tiêu đề. Phiên bản nháp có thêm **Xóa phiên bản …** ở phần nội dung phiên bản. Liên kết SKU với cấu hình bao bì có thùng rác ở cột thao tác. Dòng BOM/bao bì/công đoạn/phương án dùng thao tác xóa dòng đã có, được bổ sung bảo vệ.

Hộp thoại kiểm tra và nêu nguyên nhân không xóa được. Bản đủ điều kiện mới có nút xác nhận **Xóa**. Bấm Hủy/Escape không gửi POST. Sau thành công có toast và điều hướng hợp lý; xóa từ bảng liên kết SKU giữ bộ lọc/sắp xếp/số dòng mỗi trang bằng HTMX.

[Chính sách và hướng dẫn đầy đủ](DELETE_POLICY.md).

## Backend và bảo vệ dữ liệu

- Registry whitelist, trạng thái từng loại và danh sách dòng sở hữu rõ ràng; không phải generic CRUD tự xóa mọi model.
- GET chỉ xem xác nhận. POST + CSRF + token có chữ ký, đúng resource/ID/fingerprint, hạn 30 phút. Fingerprint bao gồm field của các dòng sở hữu, không chỉ content_hash phiên bản.
- Kiểm tra mọi reverse FK thực tế trong mappings, kể cả bảng không có UI. Dữ liệu inactive/expired vẫn có quan hệ, không bị bỏ qua. Không tự cascade qua các entity độc lập.
- Chỉ năm loại phiên bản nháp được xóa các dòng sở hữu trong cùng transaction: RecipeLine, PackagingLine, RoutingOperation, FormulaDependency, CostingSchemeLine. Kiểm tra external FK/lịch sử của từng dòng trước khi xóa. Shared FormulaTestCase giữ nguyên.
- Tham chiếu bằng mã: parser nhận diện đúng identifier trong biểu thức; phân biệt CODE1 với CODE10. Kiểm tra formula_code trong phân bổ và ALLOCATION:<code> trong phương án. Không tìm mã tràn lan trong mọi JSON/text.
- Quy đổi: bảo vệ các cặp đơn vị được cấu hình trong vật tư/BOM/bao bì/giá mua, Product/SKU/output, routing time/basis/batch, resource rate, công suất kỳ và RUN_QUANTITY; không hard-code đơn vị hoặc thực hiện tính giá.
- Lịch sử: đọc typed source references, kiểm tra schema/hash và trường nguồn đầy đủ. Nguồn đầy đủ chỉ cảnh báo khi không có FK khác; tham chiếu hỏng/thiếu chặn. JSON không liên quan bị hỏng không làm crash các thao tác xóa khác. Snapshot/kết quả cũ không bị viết lại.
- Transaction và khóa bản ghi; tái sử dụng mutex nội bộ đang có để phối hợp với Formula/Scheme/Run. Chỉ giao dịch xóa dùng khóa bảng NOWAIT cho các nguồn tham chiếu gián tiếp không có FK; không thêm decorator vào các writer/calculation service hiện hữu. Writer đang chạy thì thao tác xóa trả thông báo đang bận. FK/trigger PostgreSQL vẫn bảo vệ cuối cùng.
- Bốn remove service cũ chỉ thêm lời gọi kiểm tra xóa, giữ payload, response và hash invalidation cũ.
- Lỗi database trả tiếng Việt, không xuất SQL/traceback/credentials và không báo thành công giả. Kiểm thử có cả FK thật và rollback nguyên tử.

## URL, view và template

Chỉ thêm route `master_data:record_delete`:

`GET/POST /master-data/delete/<resource>/<identifier>/`

Identifier hỗ trợ cả mã Currency ba ký tự có dấu `/` theo contract hiện có, không tự giới hạn lại thành mã ISO. Các ID số được kiểm tra kiểu và khoảng bigint; resource không được hỗ trợ trả 404. Các route tạo/sửa/xóa dòng/kích hoạt cũ không đổi.

View: `apps/master_data/deletion_views.py:record_delete`. Thành công từ chi tiết dùng convention redirect hiện có; riêng bảng liên kết bao bì render lại partial và đóng modal qua OOB, không reload trang. Hộp thoại dùng modal, focus trap, Alpine và HTMX local đã có; icon Lucide; không JavaScript mới.

## Files tạo

Backend:

- `apps/master_data/deletion_registry.py`
- `apps/master_data/deletion.py`
- `apps/master_data/deletion_history.py`
- `apps/master_data/deletion_conversions.py`
- `apps/master_data/deletion_views.py`
- `apps/master_data/templatetags/deletion_tags.py`

Templates:

- `templates/components/delete_action.html`
- `templates/master_data/delete_confirm.html`
- `templates/master_data/partials/delete_confirm_content.html`
- `templates/master_data/partials/delete_form.html`
- `templates/master_data/partials/delete_assignment_success.html`

Tests:

- `apps/master_data/test_deletion.py`
- `apps/master_data/test_deletion_policy.py`
- `apps/master_data/test_deletion_concurrency.py`
- `apps/master_data/test_deletion_browser.py`

Tài liệu:

- `docs/delete-feature/IMPLEMENTATION_PLAN.md`
- `docs/delete-feature/DELETE_COVERAGE_MATRIX.md`
- `docs/delete-feature/DELETE_POLICY.md`
- `docs/delete-feature/DELETE_IMPLEMENTATION_REPORT.md`

## Files sửa

- `apps/master_data/urls.py`: route mới, giữ route cũ.
- `apps/bom/services.py`, `packaging_services.py`, `routing_services.py` và `apps/costing/services.py`: mỗi file thêm kiểm tra trong remove service hiện có.
- `apps/costing/testing.py`, `apps/master_data/testing.py`: bổ sung các mapped table còn thiếu vào fixture runner **chỉ cho PostgreSQL localhost test_costing_slice**. Không migration business hoặc DDL trên Supabase.
- `templates/layouts/page_header.html`: hiển thị action dùng chung ở đúng trang chi tiết.
- `templates/bom/partials/detail_content.html`
- `templates/bom/packaging/partials/detail_content.html`
- `templates/bom/routing/partials/detail_content.html`
- `templates/formula_engine/partials/detail_content.html`
- `templates/costing/partials/detail_content.html`: các partial trên có action cho phiên bản nháp, không lặp action ở trang phiên bản riêng.
- `templates/bom/packaging/partials/assignment_rows.html`: thêm thùng rác đúng cột thao tác.
- `static/css/app.css`: CSS build. File này đã có thay đổi từ trước task; không reset về Git HEAD, không sửa source typography/design system.
- `docs/00_AI_CONTEXT.md`, `docs/user-guide/README.md`: thông báo phạm vi chức năng mới, liên kết hướng dẫn; không viết lại tài liệu nghiệp vụ cũ.

Không xóa file. Không stage/commit/push hoặc deploy.

## Kiểm thử thực tế

Toàn bộ test dữ liệu dùng PostgreSQL **127.0.0.1:55439 / test_costing_slice** với fixture runner hiện có. Không chạy test xóa dữ liệu thật hoặc dữ liệu DEMO trên Supabase. Cụm test được khởi động riêng cho phiên kiểm tra, không cần cho runtime ứng dụng.

| Lần kiểm tra | Kết quả thực tế |
|---|---|
| Baseline trước sửa | 799 tests; 761 đạt, 35 bỏ qua; 1 audit UI cũ thất bại và 2 lỗi subprocess stderr do encoding Windows. `baseline-tests.log`. |
| Test đỏ trước endpoint | Xác nhận route chưa có (404), trước khi triển khai. `red-http.log`. |
| Test đỏ bảo vệ | Tái hiện hash hỏng, JSON thiếu, token không nhận child changes, race tham chiếu và các conversion bị bỏ sót. Các log `red-*.log`, `review-red.log`. |
| Toàn bộ suite sau sửa | **849 tests, 810 đạt, 38 skipped, 1 failure audit baseline cũ**; không errors. `full-tests-final.log`. Chạy UTF-8 nên hai lỗi encoding baseline không còn. |
| Toàn bộ test xóa server ở trạng thái cuối | **47/47 đạt**, gồm test FK PostgreSQL thật và lỗi FK deferred tại commit; `all-delete-tests-final.log`. |
| Chromium + Golden regression | **10/10 đạt**: 3 test Xóa, 4 test responsive/menu/forms hiện hữu và 3 test Golden/lịch sử. `browser-golden-regression.log`. |
| `python manage.py check` | Đạt: không phát hiện vấn đề. |
| `npm run build:css` | Đạt, exit 0, Tailwind v4.3.3. |
| `python scripts/audit_ui_contract.py compare` | **Không đạt** với baseline redesign 16/10. Không đổi baseline hoặc test để che lỗi. Xem phần dưới. |
| `git diff --check` | Đạt. |
| Hash model/engine/Golden/JS so với trước task | Không thay đổi; không mất file gốc. `source-review.json`. |

47 test server gồm: CRUD độc lập/các họ danh mục; FK hiện hữu kể cả inactive; trạng thái bất biến; xóa đúng dòng sở hữu; dependency code; typed JSON complete/partial/bad hash/malformed; quy đổi giá mua/output/time/capacity; token cũ/sai bản ghi; GET/CSRF; POST lặp; ID/mã Currency; HTMX success/error/query state; lỗi DB giả lập, FK thật và FK deferred tại commit; giao dịch ghi song song theo mã và thay đổi đơn vị.

Chromium kiểm tra Hủy không gửi POST, tên chứa HTML được escape, gửi hai lần chỉ một POST, modal đóng/focus/Escape, desktop 1440 và mobile 768/390 không tràn ngang, chặn NCC có giá mua, xóa phiên bản chỉ mất dòng sở hữu, xóa liên kết cập nhật bảng/toast và giữ query. Browser regression cũ kiểm tra toàn bộ menu/list/top-level forms và mật độ/collapse/mobile.

### Golden không đổi

Các test dùng nguyên expected và engine hiện có:

- Costing: **583.000 VND / 10 hộp = 58.300 VND/hộp**.
- Giá bán: **89.972,41379310 VND/đơn vị**, biên lợi nhuận **20%**.
- Giá bán kỳ tương lai: **92.526,00506044**.
- Reconciliation và fingerprint nguồn Costing, kết quả lịch sử giữ nguyên.

Không chạy seed/verify command vào database thật để lấy bằng chứng này.

### Giới hạn audit UI baseline

`UIContractTests.test_frozen_routes_forms_menu_python_and_htmx_attributes` đã fail trước task: baseline 16/10 không còn khớp với các thay đổi kích hoạt/diễn giải đã có trong HEAD. Chức năng xóa lần này còn bổ sung route/action và bốn guard service một cách có chủ đích, nên kiểm tra đóng băng mọi Python/route vẫn báo thay đổi. Không có cách gọi kết quả này là PASS; không ghi đè baseline lịch sử hay thay expected. Báo cáo JSON: `artifacts/delete-feature/ui-contract-comparison.json`; full suite ghi cùng lỗi đó. Form fields, tên POST, route cũ, menu và JS không bị đổi trong task; browser/CRUD regression đã chạy riêng.

Hai test deployment/Render baseline bị lỗi đọc stderr Unicode trên Windows. Chạy full suite với `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` giải quyết môi trường này, không sửa code deployment/tests.

## Lệnh tái kiểm tra

PowerShell, sau khi chuẩn bị PostgreSQL test riêng theo cấu hình dự án:

```powershell
$env:COSTING_TEST_DB_PORT='55439'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.\env\Scripts\python.exe manage.py check
.\env\Scripts\python.exe manage.py test apps.master_data.test_deletion apps.master_data.test_deletion_policy apps.master_data.test_deletion_concurrency --settings=config.test_settings --noinput
.\env\Scripts\python.exe manage.py test --settings=config.test_settings --noinput
npm run build:css
.\env\Scripts\python.exe scripts/audit_ui_contract.py compare --report artifacts/delete-feature/ui-contract-comparison.json
```

Để chạy test trình duyệt, thêm `COSTING_BROWSER_TESTS=1`, trỏ `PLAYWRIGHT_BROWSERS_PATH` tới Chromium đã cài; các test nằm ở `test_deletion_browser` và `test_ui_redesign.RedesignBrowserTests`. Không bật keepdb hoặc đổi guard test thành database thật.

## Review và giới hạn còn lại

Review độc lập đã phát hiện và sửa: thiếu đường quy đổi theo giá mua/output/capacity, token chưa bao gồm dòng con, malformed history có thể bỏ lọt hoặc crash, scope formula candidate và race cập nhật Item/Product/SKU. Test đỏ/xanh cho các trường hợp đã chạy.

- Không cleanup hàng loạt. Không undo sau xóa vật lý.
- Phần lưu Run lỗi và FormulaTestCase giữ chính sách bảo toàn đã nêu; không tự đề xuất hoặc áp SQL chưa được duyệt.
- Quy đổi dùng cặp đơn vị cấu hình được bảo vệ có chủ đích, không tự xét phương án thay thế hoặc tự sửa policy effective-date/overlap.
- Dữ liệu lịch sử quá cũ/thiếu snapshot có thể bị chặn và cần kiểm tra thủ công; không có nút bỏ qua ràng buộc.
- Không kiểm tra bằng cách xóa dữ liệu production. Những FK/trigger Supabase được tôn trọng, không disable trigger/RLS hoặc đổi quyền.
- Không thay những service ghi khác để buộc mọi cấu hình tương lai phải có conversion; task chỉ quyết định an toàn tại thời điểm xóa và chặn giao dịch đang ghi. Validation khi nhập mới giữ nguyên.

Hoàn thành trong phạm vi chức năng Xóa. Không tự triển khai module hoặc cơ chế lưu trữ mới.