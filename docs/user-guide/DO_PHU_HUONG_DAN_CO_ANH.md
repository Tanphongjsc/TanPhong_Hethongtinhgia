# Đối chiếu độ phủ hướng dẫn sử dụng có ảnh

Ngày đối chiếu: 23/10/2026. Đây là phụ lục kiểm tra nội dung, không phải hướng dẫn kỹ thuật cho người nhập liệu. Hướng dẫn chính: [Markdown](HUONG_DAN_SU_DUNG_CO_ANH.md) · [PDF](HUONG_DAN_SU_DUNG_DAY_DU_DESKTOP.pdf).

Nguồn đối chiếu: menu thực tế `apps/master_data/navigation.py`, routes/views/forms/templates của master_data, product, bom, formula_engine, costing, pricing; các chương 04–07 và bảng trường 12 hiện có. Các cập nhật kích hoạt, nhãn diễn giải và xóa được đọc bổ sung từ `docs/00_AI_CONTEXT.md`, `docs/ui-redesign/EXPLANATION_READABILITY.md`, `docs/delete-feature/DELETE_POLICY.md`. Nội dung cũ chưa có kích hoạt/xóa được thay theo hành vi hiện tại.

## 1. Toàn bộ 28 mục menu

Các thao tác tìm/lọc/sắp xếp/phân trang, thêm/xem/sửa/ngừng hoạt động/xóa dùng chương 2 và được bổ sung điều kiện riêng tại từng mục. “Xóa có điều kiện” không có nghĩa dữ liệu đang sử dụng được phép xóa.

| Mục menu hiện có | Mục trong hướng dẫn | Thao tác và giới hạn được mô tả |
|---|---|---|
| Lần tính giá thành | 13 | Tạo/chạy, tra danh sách, kết quả, trace, snapshot, chạy lại thành Run mới; không sửa/xóa Run |
| Phần tử chi phí | 4.1 | Thêm/xem/sửa/ngừng/xóa có điều kiện, kiểu/đơn vị và nối nguồn |
| Nhóm sản phẩm | 4.2 | Thêm/xem/sửa/ngừng/xóa, ảnh hưởng nhóm phí |
| Vật tư / Hàng hóa | 4.3 | Thêm/xem/sửa/ngừng/xóa, loại/đơn vị/thuế/số đo/tồn kho |
| Sản phẩm | 4.4 | Thêm/xem/sửa/ngừng/xóa, đơn vị tính giá thành, Item đầu ra |
| SKU | 4.5 | Thêm/xem/sửa/ngừng/xóa, quy cách bán/lượng tịnh/mã vạch |
| Tiền tệ | 3.1 | Thêm/xem/sửa/ngừng/xóa, mã và số lẻ |
| Nhóm đơn vị tính | 3.2 | Thêm/xem/sửa/ngừng/xóa, đại lượng |
| Đơn vị tính | 3.3 | Thêm/xem/sửa/ngừng/xóa, nhóm/ký hiệu/độ chính xác/cờ cơ sở |
| Quy đổi đơn vị tính | 3.4 | Thêm/xem/sửa/xóa có điều kiện; quy đổi chung/riêng/ngày/chiều, bản dùng chung chỉ xem |
| Nhà cung cấp | 5.1 | Thêm/xem/sửa/ngừng/xóa, chặn khi còn báo giá |
| Giá nhà cung cấp | 5.2–5.4 | Thêm/xem/sửa/xóa Nháp, kích hoạt, giá mới theo kỳ, thuế mua và nguồn mơ hồ |
| BOM / Công thức sản xuất | 6 | Hồ sơ, phiên bản, thành phần, thu hồi/hao hụt, lịch sử/sao chép/kích hoạt/xóa có điều kiện |
| Cấu hình bao bì | 7 | Hồ sơ/phiên bản/thành phần/cấp, gán/sửa/xóa liên kết SKU, sao chép/kích hoạt/cơ sở Run |
| Trung tâm sản xuất | 8.1 | Thêm/xem/sửa/ngừng/xóa, công suất và nguồn lực liên quan |
| Nguồn lực | 8.2 | Thêm/xem/sửa/ngừng/xóa, trung tâm/loại/năng lực/lịch sử đơn giá |
| Đơn giá nguồn lực | 8.3 | Thêm/xem/sửa/xóa Nháp, đơn vị/kỳ/loại; giới hạn action hiệu lực |
| Quy trình sản xuất | 9 | Hồ sơ/phiên bản, công đoạn thêm/sửa/xóa, thứ tự, nguồn lực chính, cơ sở và thời gian, sao chép |
| Nhóm chi phí chung | 10.1 | Thêm/xem/sửa/ngừng/xóa; không có CostPoolMember UI |
| Quy tắc phân bổ | 10.2 | Thêm/xem/sửa/xóa Nháp; tiêu thức/công thức/ưu tiên/ngày; giới hạn dữ liệu kỳ và thực thi |
| Thiết lập công thức | 11 | Hồ sơ/biểu thức/biến, kiểm tra, thử tính, lưu/chạy/ngừng test, kích hoạt, lịch sử/bản mới/xóa |
| Phương án tính giá thành | 12 | Hồ sơ/phiên bản/dòng CRUD, nguồn động, kiểm tra phụ thuộc, Đầu ra, kích hoạt, sao chép/xóa |
| Kênh bán | 14.1 | Thêm/xem/sửa/ngừng/xóa có điều kiện |
| Quy tắc phí kênh | 14.2, 14.5 | CRUD Nháp, phạm vi/ưu tiên/sàn-trần, đưa hiệu lực, đóng kỳ và thay chính sách |
| Quy tắc thuế | 14.3, 14.5 | CRUD Nháp, phạm vi/cơ sở/thuế trong giá, hiệu lực/đóng kỳ |
| Tỷ giá | 14.4–14.5 | CRUD Nháp, chiều/loại/thời điểm, hiệu lực/đóng kỳ |
| Kịch bản giá bán | 15.1–15.3 | Nháp CRUD, nguồn/đơn vị/mục tiêu, tính, diễn giải, lỗi, nhân bản bản đã tính |
| So sánh kịch bản | 15.4 | Chọn 2–5, lọc/mốc/chênh lệch/khả năng tương thích; chỉ đọc, không entity CRUD |

## 2. Kiểm tra các thao tác dễ bị bỏ sót

| Thao tác | Vị trí |
|---|---|
| Thu/mở sidebar, Gọn/Thoáng, nhãn biểu tượng, form lỗi | 2.1–2.2 |
| Xác nhận ngừng hoạt động và khôi phục hoạt động | 2.3 |
| Xóa hồ sơ/phiên bản/dòng, chặn liên kết và lịch sử | 2.4 và các chương chức năng |
| Gán/sửa/bỏ liên kết SKU–bao bì; xem tất cả | 7.2 |
| Lịch sử/sao chép phiên bản BOM/bao bì/quy trình/công thức/phương án | 6.4, 7.3, 9.3, 11.5, 12.4 |
| Kích hoạt BOM/bao bì/giá mua/công thức/phương án | 6.3, 7.3, 5.3, 11.4, 12.3 |
| Chèn biến, kiểm tra kiểu, hàm, phụ thuộc và thông báo vị trí lỗi | 11.1 |
| Thử tính khác lưu test, chạy test đã lưu, ngừng test | 11.2–11.3 |
| Dòng phương án nguồn động, một Đầu ra, kiểm tra thứ tự phụ thuộc | 12.2–12.3 |
| Run bao bì/MANUAL, nguồn/trace/snapshot, chạy lại và giữ lịch sử | 13 |
| Đóng kỳ tương lai phí/thuế/FX; khác quy ước ngày Costing | 14.5 |
| Kịch bản lỗi giữ Nháp, bản đã tính bất biến, nhân bản, so sánh | 15 |
| Bài thực hành 1 gói/1 túi; cập nhật kỳ; troubleshooting/checklist | 16 |

## 3. Ảnh và kiểm chứng

- Toàn bộ 44 ảnh được dùng trong hướng dẫn chụp từ cùng source hiện tại, Chromium desktop **1440 × 960**, không dùng ảnh mobile.
- Dùng PostgreSQL kiểm thử cục bộ tách biệt, schema fixture và dữ liệu DEMO; không chụp hoặc sửa dữ liệu thật trên Supabase.
- Bộ chụp kiểm tra 67 đích/màn hình/trạng thái HTTP 200; chọn 44 ảnh phù hợp vào tài liệu. Ảnh form chỉ minh họa phần đang thấy trên desktop, thao tác còn lại được nêu bằng văn bản.
- Kiểm tra đường dẫn ảnh/tài liệu, các mốc mục lục, tiêu đề chương và kết xuất PDF; đối chiếu ảnh kiểm thử/kiểm tra cấu hình/diễn giải.
- Không thay business source, UI templates, schema hay công thức engine. PDF tính lương chỉ tham khảo cách chia chương, bước và chú thích; không sử dụng nội dung nghiệp vụ.