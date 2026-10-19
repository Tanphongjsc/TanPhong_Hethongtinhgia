# Bộ hướng dẫn sử dụng tính giá thành và giá bán

Phiên bản tài liệu: 09/10/2026. Phạm vi: giao diện và bộ tính hiện có trong repository tại thời điểm kiểm chứng. Đây là tài liệu cho kế toán, sản xuất, mua hàng và kinh doanh; không cần biết lập trình để đọc các chương chính.

Bắt đầu tại [Sổ tay tổng hợp](../HUONG_DAN_SU_DUNG_HE_THONG_TINH_GIA.md). Để học bằng dữ liệu cụ thể, mở [Bài thực hành Cappuccino](09_THUC_HANH_CAPPUCCINO_END_TO_END.md).

| Chương | Khi nào đọc |
|---|---|
| [01. Tổng quan](01_TONG_QUAN_HE_THONG.md) | Lần đầu sử dụng; hiểu giá thành khác giá bán |
| [02. Bản đồ chức năng](02_BAN_DO_CHUC_NANG_VA_NGHIEP_VU.md) | Tìm đúng menu, màn hình và thao tác |
| [03. Thứ tự khởi tạo](03_THU_TU_KHOI_TAO_DU_LIEU.md) | Bắt đầu nhập dữ liệu hoặc tìm danh mục còn thiếu |
| [04. Dữ liệu danh mục](04_HUONG_DAN_DANH_MUC.md) | Tiền tệ, đơn vị, phần tử chi phí, vật tư, sản phẩm, SKU và giá mua |
| [05. Sản xuất](05_HUONG_DAN_SAN_XUAT.md) | Định mức, bao bì, nguồn lực, quy trình và phân bổ |
| [06. Công thức và giá thành](06_HUONG_DAN_FORMULA_VA_COSTING.md) | Công thức, phương án, lần tính, kết quả, nguồn và diễn giải |
| [07. Giá bán](07_HUONG_DAN_PRICING.md) | Kênh, phí, thuế, tỷ giá, định giá và so sánh |
| [08. Kịch bản thực tế](08_KICH_BAN_THUC_TE.md) | 20 bài toán kinh doanh, tính tay và mức hỗ trợ |
| [09. Thực hành Cappuccino](09_THUC_HANH_CAPPUCCINO_END_TO_END.md) | Làm theo 22 bước với dữ liệu DEMO có sẵn |
| [10. Lỗi và xử lý](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md) | Không lưu được, không tính được hoặc kết quả khác mong đợi |
| [11. FAQ và thuật ngữ](11_FAQ_VA_GLOSSARY.md) | Tra cứu câu hỏi thường gặp và khái niệm |
| [12. Từng trường nhập](12_FIELD_REFERENCE.md) | Tra bắt buộc, mặc định, điều kiện, ví dụ của từng form |
| [13. Ma trận phụ thuộc](13_DEPENDENCY_MATRIX.md) | Trước khi tạo X cần gì; sửa X ảnh hưởng đâu |
| [14. Ma trận năng lực](14_BUSINESS_CAPABILITY_MATRIX.md) | Kiểm tra hệ thống có đáp ứng bài toán của doanh nghiệp |
| [Giới hạn hiện tại](GAP_REGISTER.md) | Xác định phần phải chuẩn bị ngoài UI hoặc chưa hỗ trợ |
| [Kiểm chứng nguồn](SOURCE_VERIFICATION.md) | Phụ lục dành cho người hỗ trợ kỹ thuật; route, form và bằng chứng |

## Cách phân biệt thông tin

- **[HỆ THỐNG HIỆN TẠI]**: hành vi có trong source, form, giao diện hoặc kiểm thử hiện tại.
- **[DEMO]**: đúng dữ liệu Cappuccino do các lệnh mẫu của dự án định nghĩa; không phải số liệu doanh nghiệp hay giá thị trường.
- **[VÍ DỤ NGHIỆP VỤ]**: số tự đặt để học và tính tay; không khẳng định bản ghi đã tồn tại.
- **[INDUSTRY PATTERN]**: mô hình tham khảo từ nguồn ngành được dẫn ngay tại nội dung.
- **[CHƯA HỖ TRỢ]**: thiếu thao tác, dữ liệu hoặc bộ xử lý; không làm theo như một tính năng có sẵn.

Mức hỗ trợ chỉ dùng **NATIVE** (trực tiếp), **CONFIGURABLE** (cấu hình bằng phần tử/công thức/phương án hiện có), **PARTIAL** (mới đáp ứng một phần) và **NOT SUPPORTED** (chưa đáp ứng). Có trường để nhập không đồng nghĩa bộ tính sử dụng được mọi giá trị của trường.

## Điều kiện thực hành

Phần mềm phải được người phụ trách triển khai và kết nối database đã có schema. Người dùng truy cập trực tiếp URL hệ thống được cung cấp. Bộ tài liệu không yêu cầu tạo tài khoản.

**Database rỗng hoàn toàn chưa thể thiết lập đầy đủ chỉ bằng giao diện hiện có.** Một số nguồn mới lưu Nháp nhưng chưa có thao tác đưa vào hiệu lực; số liệu kỳ chi phí chung cũng chưa có màn hình nhập. Chương 03 và GAP_REGISTER chỉ rõ các điểm dừng. Bài thực hành sử dụng mẫu đã được người phụ trách chuẩn bị, không hướng dẫn sửa trực tiếp trạng thái trong database.

Đọc các ví dụ thuế như giả định đào tạo; doanh nghiệp tự xác định chính sách và mức thuế phù hợp thực tế. Mức 10%/11% trong DEMO không phải khẳng định thuế suất pháp lý hiện hành.
