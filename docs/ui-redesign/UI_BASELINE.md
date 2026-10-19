# Baseline giao diện và contract

Ngày chốt: 16/10/2026. Source Git trước redesign: `f4e0030`. Các file hướng dẫn người dùng chưa commit đã tồn tại từ task trước và được giữ nguyên. Đây là thay đổi trình bày; không thay đổi nghiệp vụ.

## Kiểm kê trước thay đổi

| Hạng mục | Baseline |
|---|---:|
| Template HTML | 149 |
| Template trang đầy đủ dùng extends | 38 |
| Partial trong thư mục partials | 90 |
| Component trong components | 16 |
| Layout | 5 |
| URL route | 163 |
| Đích nghiệp vụ nhận GET | 152, có tái sử dụng template/panel |
| Lớp form | 43, gồm 4 lớp nền và 39 lớp cụ thể |
| Mục điều hướng | 28 trong 5 nhóm |

Số template khác số URL và số màn hình độc lập. Kiểm kê chi tiết đã có trong bộ hướng dẫn tại [bản đồ chức năng](../user-guide/02_BAN_DO_CHUC_NANG_VA_NGHIEP_VU.md).

## Bằng chứng contract

[ui-contract-baseline.json](ui-contract-baseline.json) được tạo **trước khi thay đổi UI** bằng:

```powershell
.\env\Scripts\python.exe scripts/audit_ui_contract.py capture
```

Không ghi đè baseline khi kiểm tra kết quả. Chế độ capture từ chối nếu file đã tồn tại. Audit dùng settings test và chặn mọi truy vấn database.

File ghi toàn bộ route/name/view; menu và nhãn; lớp form/trường/kiểu/label/required/disabled/initial/choices/validators/error messages/widget attributes; ba ngữ cảnh ClosePeriodForm (phí, thuế, tỷ giá); HTMX, ID, tên/value, form action/method, liên kết, label association và các biểu thức/điều kiện template. SHA-256 của Python hiện có bao phủ models, services, selectors, validators, engines, views, forms, URLs, constants, test expected và settings.

Trường Formula test và MANUAL Run có số lượng phụ thuộc cấu hình. Logic sinh trường nằm trong Python bị đóng băng; bộ browser/regression kiểm tra chúng trong ngữ cảnh thật. Không suy ra số lượng trường động chỉ từ base_fields.

## Quy tắc được giữ

- URL, URL name, query filters/sort/page/per_page và repeated scenario/baseline IDs.
- Tên trường, labels nghiệp vụ, kiểu, required/optional, defaults, choices, disabled/readonly và lỗi validation.
- CSRF, POST action/name/value, HTMX endpoint/target/swap/trigger/push URL/select/disabled/sync.
- Cột, dữ liệu, thứ tự và định dạng số/ngày của bảng; giá trị backend và Decimal.
- Các điều kiện cho phép tạo/sửa/xóa dòng, confirmation, trạng thái, effective dates và versioning.
- Run/Scenario history, snapshot, trace; không tính toán tài chính trong JavaScript.
- Truy cập nội bộ trực tiếp, không UI tài khoản, công ty hoặc phê duyệt mới.

## Các luồng cần regression

Danh mục tạo/xem/sửa/tìm/lọc/sort/phân trang; ngừng hoạt động với confirmation; dòng BOM/bao bì/công đoạn và drawer; clone phiên bản; Formula validate/test/save/testcase/activate; Scheme nguồn phụ thuộc/validate/activate; Run dependent fields/create/trace/snapshot/rerun; Pricing Foundation đóng kỳ; Scenario dependent fields/save/calculate/clone; Comparison giữ lựa chọn/mốc trong URL.

Golden cố định: Costing **583.000 VND/10 hộp**, **58.300 VND/hộp**; Pricing **89.972,41379310 VND/đơn vị**, margin **20%**. Golden Pricing future giữ vốn cũ và cho **92.526,00506044**. Không sửa expected để ép giao diện pass.

## Test baseline

Lần đầu full suite phát hiện 747 tests nhưng 22 browser test không khởi chạy vì Chromium chưa được cài; đây là lỗi môi trường trước redesign. Đã cài Chromium vào `artifacts/ui-redesign/playwright`, chạy lại toàn bộ với `COSTING_BROWSER_TESTS=1`. Kết quả baseline cuối và đối chiếu sau nằm trong [REGRESSION_REPORT](REGRESSION_REPORT.md).

Baseline sau khi đủ môi trường: **747 tests, 274.724s, OK (skipped=1)**. Sau redesign: **752 tests, 275.375s, OK (skipped=1)**, gồm 5 test mới. Skip duy nhất ở cả hai lượt là benchmark dung lượng opt-in; browser tests đã chạy. Audit cuối: **errors=[]**, 163 routes/43 forms/28 menu destinations/251 Python cũ giữ nguyên.

Các kiểm thử chỉ dùng PostgreSQL riêng tại `127.0.0.1:55432` và `config.test_settings`. Không chạy migration/seed/test vào database doanh nghiệp. Screenshot/log cục bộ nằm trong `artifacts/ui-redesign/`; không phải tài nguyên runtime.

## Cách so sánh sau rollout

```powershell
.\env\Scripts\python.exe scripts/audit_ui_contract.py compare
```

Route/form/menu và Python hiện có phải giữ nguyên. Audit từ chối thay đổi thuộc tính request/ID/label association hiện có. Những thay đổi binding/condition được báo riêng để review: chỉ chấp nhận icon, local UI state, metric layout và presentation. Browser tests kiểm tra DOM thực; source audit không thay thế kiểm thử tương tác.

## Làm rõ số đếm sau deep verification — 17/10/2026

Bảng trên là baseline trước redesign, không ghi đè. Source hiện tại có 151 templates,
18 components; 38 extends/90 partials/5 layouts/43 forms/28 menu không đổi.
Có 163 routes: 160 UI + 3 technical/redirect; 156 UI routes nhận GET, gồm 152 document
flows và 4 supporting fragments. Vì vậy “152 GET destinations” trong baseline nói
các document flows, không bao gồm bốn fragment support.

Phase mới tại TanPhong_Hethongtinhgia giữ nguyên baseline JSON. Bằng chứng:
[UI_COVERAGE_MATRIX](UI_COVERAGE_MATRIX.md), [REMAINING_UI_AUDIT](REMAINING_UI_AUDIT.md).
Full suite 758 tests/541.840s OK, 1 benchmark opt-in skip. 256 file phase không đổi;
business Python semantic diff bằng zero.
