# Cải thiện cách đọc diễn giải và nhãn trường — 20/10/2026

Phạm vi: trình bày kết quả đã lưu, nguồn dữ liệu và nhãn/gợi ý nhập. Không thay
models, schema, form fields/validation, selectors, services, routes, HTMX bindings,
JavaScript hoặc Costing/Formula/Pricing engines. Không sửa dữ liệu doanh nghiệp.

## Diễn giải

- Khung diễn giải Run rộng hơn trên desktop; mobile giữ theo chiều rộng màn hình.
- Đầu khung nêu khoản đang xem, mã, nguồn và giá trị đã tính. Số tiền không tính lại.
- Vật tư có bảng tên/mã, nhà cung cấp, lượng tính tiền, đơn giá và thành tiền.
- Công thức có bảng đầu vào kèm tên dễ đọc và mã biến; tên lấy từ snapshot.
- Các bước tính liên tiếp gom vào bảng thu gọn; mở ra vẫn có toán tử, đầu vào,
  kết quả, công thức và phiên bản. Các bước khác vẫn giữ thứ tự và đầy đủ trường.
- Tỷ lệ thu hồi/hao hụt hiển thị phần trăm; số lượng và tiền giữ precision khi hiển thị.
- Nguồn đã sử dụng chia nhóm; tên bản ghi phiên bản/giá lấy qua FK trong snapshot,
  không JOIN danh mục hiện tại. Snapshot cũ thiếu tên giữ nhãn/ref dự phòng.
- Diễn giải phí/thuế/tỷ giá Pricing dùng bảng từ các giá trị đã trình bày sẵn;
  không chạy lại bộ tính, không thay định nghĩa phí hay thuế.

## Nhãn hiển thị được làm rõ

Nguồn mapping: `apps/master_data/presentation.py`, dùng ở components form/detail,
filter và table header. Nhãn gốc trong form và identifiers được giữ nguyên.

| Nhãn trước | Nhãn hiển thị hiện tại |
|---|---|
| Sản lượng cơ sở đóng gói | Số thành phẩm theo định mức bao bì |
| Đơn vị cơ sở đóng gói | Đơn vị thành phẩm đóng gói |
| Tiền tệ kết quả | Tiền tệ tính giá |
| Nhãn hiển thị | Tên hiển thị |
| Loại dòng | Vai trò của dòng |
| Mã bộ lấy dữ liệu hệ thống | Mã nguồn tính tự động |
| Phạm vi hiển thị | Nơi hiển thị |
| Số chữ số làm tròn | Số chữ số sau dấu phẩy |
| Độ chính xác | Số chữ số thập phân |
| Thời gian thiết lập | Thời gian chuẩn bị |
| Tham chiếu / Số báo giá | Số báo giá / Tài liệu tham chiếu |

Hai ô định mức bao bì có ví dụ 1 túi chứa 50 gói; Vai trò của dòng có hướng dẫn
chọn Đầu ra cho dòng tổng. Các thuật ngữ đã rõ hoặc cần giữ nghĩa nghiệp vụ như
Phần tử chi phí, SKU, BOM, ngày hiệu lực, tỷ lệ thuế, mã kỹ thuật được giữ nguyên.

## Kiểm chứng

Tests tại `apps/costing/test_explanation_presentation.py` xác nhận GET không ghi
DB, không đọc lại giá/tên master, không gọi execute, snapshot/context/lines/tiền
không đổi; thêm kiểm tra escape HTML, cấu trúc cũ, số 0/boolean, nhãn/input bindings.
Playwright kiểm tra drawer, đóng bằng Escape, disclosure, nhãn gắn đúng input,
HTMX và overflow ở 1440/768/390px. Bằng chứng cục bộ tại
`artifacts/explanation-readability/` (gitignored).

Các baseline UI ngày 16/10 là bằng chứng lịch sử của đợt chỉ đổi style trước đó;
không ghi đè để hợp thức hóa nhãn mới được người dùng yêu cầu ở task này. Rà soát
phạm vi bằng SHA-256 so với trước task và bộ hồi quy nghiệp vụ độc lập.
Validation: 754 regression tests discovered, 734 passed, 20 opt-in skipped;
11 browser flows passed; Django check and Tailwind production build passed.
Financial Golden expectations and all calculation source files remain unchanged.
