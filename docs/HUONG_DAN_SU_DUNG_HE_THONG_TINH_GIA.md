# Hướng dẫn sử dụng hệ thống tính giá thành và giá bán

Bản dành cho người sử dụng, ngày 09/10/2026. Đọc từ đầu nếu mới tiếp cận; các bảng trường và phụ thuộc giúp tra cứu khi nhập liệu.

## Mục lục

1. [Phần mềm làm gì và những khái niệm chính](user-guide/01_TONG_QUAN_HE_THONG.md)
2. [Menu, màn hình và chức năng](user-guide/02_BAN_DO_CHUC_NANG_VA_NGHIEP_VU.md)
3. [Bắt đầu: nhập gì trước?](user-guide/03_THU_TU_KHOI_TAO_DU_LIEU.md)
4. [Hướng dẫn dữ liệu danh mục](user-guide/04_HUONG_DAN_DANH_MUC.md)
5. [Hướng dẫn cấu hình sản xuất](user-guide/05_HUONG_DAN_SAN_XUAT.md)
6. [Công thức, phương án và chạy giá thành](user-guide/06_HUONG_DAN_FORMULA_VA_COSTING.md)
7. [Kênh, phí, thuế, tỷ giá và giá bán](user-guide/07_HUONG_DAN_PRICING.md)
8. [20 kịch bản kinh doanh](user-guide/08_KICH_BAN_THUC_TE.md)
9. [Thực hành Cappuccino từ A–Z](user-guide/09_THUC_HANH_CAPPUCCINO_END_TO_END.md)
10. [Lỗi, cây quyết định và cách xử lý](user-guide/10_LOI_THUONG_GAP_VA_CACH_XU_LY.md)
11. [FAQ và từ điển thuật ngữ](user-guide/11_FAQ_VA_GLOSSARY.md)
12. [Tham chiếu từng trường trên form](user-guide/12_FIELD_REFERENCE.md)
13. [Phụ thuộc dữ liệu và ảnh hưởng thay đổi](user-guide/13_DEPENDENCY_MATRIX.md)
14. [Năng lực theo bài toán và ngành](user-guide/14_BUSINESS_CAPABILITY_MATRIX.md)
15. [Giới hạn và giải pháp tạm thời](user-guide/GAP_REGISTER.md)
16. [Phụ lục đối chiếu source và kiểm thử](user-guide/SOURCE_VERIFICATION.md)

## Đường đi nhanh cho người mới

**Dữ liệu → cấu hình → tính → đọc → quyết định.** Chuẩn bị tiền tệ/đơn vị; nhập vật tư, Product/SKU và nguồn giá; lập định mức/bao bì/quy trình; cấu hình phần tử/công thức/phương án; chạy giá thành; lấy kết quả đã khóa để định giá; so sánh các kịch bản tương thích.

Trong mẫu Cappuccino: 10 hộp cần nguyên liệu 260.000, bao bì 150.000, nguồn lực 120.000 và chi phí chung 53.000 VND. Tổng 583.000 VND, tức 58.300 VND/hộp. Kịch bản bán mẫu thêm phí 5% + 1.000 VND, thuế giả định 10% và biên mục tiêu 20% trên giá khách trả, cho 89.972,41379310 VND/hộp. Bài thực hành trình bày cách xem từng nguồn và tự kiểm tra phép tính.

## Ba nguyên tắc khi sử dụng

1. **Đúng cơ sở:** 100 kg khác 1 kg; giá theo giờ khác giá theo phút; tổng một lần tính khác giá thành đơn vị. Bao bì hiện cần nhập cơ sở đóng gói trên form lần tính.
2. **Đúng nguồn và thời gian:** bản Nháp không tự thành nguồn hiệu lực. Nhiều nguồn phù hợp có thể bị từ chối, không tự chọn giá rẻ nhất hay bản mới nhất.
3. **Giữ lịch sử:** xem kết quả cũ đọc bản chụp đã lưu. Muốn thử thay đổi, tạo bản/lần/kịch bản mới, không sửa kết quả cũ.

## Ranh giới hiện tại cần biết trước

Phần mềm phục vụ nội bộ, truy cập trực tiếp. Các danh mục, trường hoặc bảng còn tồn tại để tương thích database không tự trở thành chức năng giao diện.

Một người mới có thể học và thực hành trên bộ mẫu đã chuẩn bị. **Chưa thể tự hoàn tất toàn bộ từ database rỗng chỉ bằng UI**, vì chưa có màn hình nhập số liệu kỳ chi phí chung và chưa có thao tác đưa một số nguồn sản xuất/giá mua từ Nháp sang hiệu lực. Chương 03 chỉ rõ điểm cần người phụ trách dữ liệu hỗ trợ; tài liệu không giả lập nút bấm hoặc hướng dẫn bỏ qua kiểm tra.

Các chương dùng nhãn **[HỆ THỐNG HIỆN TẠI]**, **[DEMO]**, **[VÍ DỤ NGHIỆP VỤ]**, **[INDUSTRY PATTERN]**, **[CHƯA HỖ TRỢ]** để tách hành vi thật khỏi minh họa. Mức hỗ trợ **NATIVE / CONFIGURABLE / PARTIAL / NOT SUPPORTED** được giải thích tại [README](user-guide/README.md).

## Trước khi sử dụng số liệu thật

- [ ] Đọc xong bài thực hành và đối chiếu được từng khoản chi phí/giá bán.
- [ ] Xác định đúng sản phẩm/SKU, ngày, sản lượng và đơn vị đầu ra.
- [ ] Xác nhận nguồn đang hiệu lực, không chồng nhau và đúng tiền tệ.
- [ ] Hiểu phương án có đúng một dòng đầu ra chính; không cộng cả dòng tổng và dòng thành phần lần nữa.
- [ ] Phân biệt mục tiêu lợi nhuận và lợi nhuận thực tế sau phí/thuế.
- [ ] Biết mở diễn giải, bản chụp và cung cấp mã tham chiếu khi lỗi.
- [ ] Đọc [giới hạn](user-guide/GAP_REGISTER.md) đối với vận chuyển, thuế mua, ngoại tệ giá vốn và giá khuyến mại.

## Tài liệu dành cho người hỗ trợ

[SOURCE_VERIFICATION](user-guide/SOURCE_VERIFICATION.md) ghi các source và kiểm thử đã dùng. [Tài liệu triển khai](DEPLOYMENT_RENDER.md) dành riêng cho người vận hành hạ tầng; không cần làm theo để nhập liệu nghiệp vụ.
