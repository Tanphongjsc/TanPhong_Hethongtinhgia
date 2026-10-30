# Chính sách xóa dữ liệu

Áp dụng ngày 21/10/2026 cho dự án `TanPhong_Hethongtinhgia`. Không thay schema, không thêm đăng nhập, phân quyền nhân sự hoặc chọn công ty. Phạm vi là dữ liệu và màn hình đã triển khai; không mở module mới.

## Dành cho người sử dụng

1. Mở **trang chi tiết** của dữ liệu cần xóa. Chọn nút **Xóa …** cạnh thao tác chỉnh sửa.
2. Hộp thoại **Xác nhận xóa** hiển thị mã/tên, dữ liệu thuộc bản nháp sẽ xóa cùng và các cảnh báo nếu có.
3. Nếu được phép, chọn **Xóa** để xóa vĩnh viễn; chọn **Hủy** hoặc nhấn Escape để đóng. Mở hộp thoại chưa xóa dữ liệu.
4. Nếu đang được dữ liệu khác sử dụng, hộp thoại nêu loại dữ liệu và số bản ghi liên quan. Kiểm tra các liên kết đó, hoặc ngừng sử dụng danh mục thay vì xóa. Không xóa lịch sử chỉ để xóa được danh mục.
5. Với phiên bản BOM, bao bì, quy trình, công thức hoặc phương án: nút **Xóa phiên bản …** nằm trong phần thông tin phiên bản. Xóa từng bản nháp trước khi xóa hồ sơ cha; bản đã chốt không có thao tác xóa.
6. Liên kết SKU–bao bì có biểu tượng thùng rác ngay ở cột thao tác. Xóa liên kết này không xóa SKU, cấu hình hoặc vật tư bao bì.

Các dòng BOM/bao bì/công đoạn/phương án tiếp tục dùng thao tác xóa dòng hiện có. Chúng được bổ sung kiểm tra tham chiếu và lịch sử ở backend. Không thay payload hay cách xác nhận cũ của các màn hình đó.

## Những trường hợp cho phép

- Danh mục độc lập, chưa bị tham chiếu: phần tử chi phí, tiền tệ, đơn vị, vật tư, sản phẩm, SKU, nhà cung cấp, nguồn lực, trung tâm, kênh bán…
- Giá mua, đơn giá nguồn lực, phân bổ, phí, thuế, tỷ giá còn **Nháp**, chưa bị tham chiếu.
- Phiên bản **Nháp/Chờ duyệt** của năm họ cấu hình, nếu không bị tham chiếu. Chỉ xóa các dòng thuộc đúng phiên bản: RecipeLine, PackagingLine, RoutingOperation, FormulaDependency hoặc CostingSchemeLine. Hộp thoại công bố số dòng; thao tác nguyên tử. Không xóa vật tư, nguồn lực, công thức cha hoặc bộ kiểm thử dùng chung.
- Kịch bản giá bán còn **Nháp**, chưa có kết quả thành công. Một lần tính giá bán lỗi có cấu trúc diagnostics hiện hành không tự biến thành kết quả đã chốt.
- Nguồn danh mục chỉ xuất hiện trong bản chụp lịch sử có schema, hash và các trường nguồn đầy đủ: có thể xóa kèm cảnh báo nếu không còn ràng buộc khác. Không tính lại hoặc chỉnh sửa snapshot/kết quả cũ.

## Những trường hợp phải giữ

- **Mọi FK tham chiếu còn tồn tại**, kể cả dữ liệu ngừng hoạt động, giá hết hạn và danh mục con. Ví dụ: nhà cung cấp còn báo giá; Product còn SKU/BOM/bao bì/quy trình; CostPool còn AllocationRule hoặc CostPoolPeriod; Resource còn đơn giá/công đoạn; Currency/UoM còn bất kỳ FK tương ứng.
- Hồ sơ cha còn phiên bản, hoặc phiên bản đã chốt/hiệu lực/ngừng hiệu lực. Không tự xóa dây chuyền hồ sơ cha để thuận tiện thao tác.
- Biểu thức công thức còn tham chiếu chính xác mã `$ELEMENT`/`@FORMULA`; `AllocationRule.formula_code`; `CostingSchemeLine.system_resolver_code=ALLOCATION:<code>`; input bộ kiểm thử còn mã phần tử chi phí.
- Quy đổi có cặp đơn vị đang được cấu hình sử dụng: dòng BOM/bao bì với đơn vị vật tư/giá mua; đầu ra Product/SKU với sản lượng BOM hoặc cơ sở công đoạn; thời gian công đoạn với đơn vị đơn giá; cơ sở phân bổ và RUN_QUANTITY. Không hard-code kg/g/giờ; kiểm tra dữ liệu thực tế.
- Quy đổi dùng chung (`organization_id=NULL`) giữ chính sách chỉ xem hiện có.
- Nguồn lịch sử có tham chiếu định danh nhưng thiếu trường, sai hash hoặc có JSON không nhất quán: chặn với thông báo. Không suy diễn chỉ từ một chuỗi số hay tên mã giống nhau trong văn bản tự do.
- Đơn vị đóng gói còn được `context.request.packaging_uom` của một Run tham chiếu được giữ lại, kể cả Run thất bại: đầu vào này cần cho thao tác chạy lại.
- Run đã lưu, dòng kết quả, overrides, snapshot/trace và kịch bản CALCULATED được giữ nguyên. Màn hình so sánh không có bản ghi độc lập để xóa.

## Các giới hạn có chủ đích

**Costing Run:** chưa cho xóa vật lý cả Run nháp/thất bại đã lưu. `idempotency_key`/dấu vết chạy lại đang nằm trong chính bản ghi; xóa sẽ làm mất khả năng nhận diện yêu cầu gửi lặp. Không thêm bảng/cột giữ khóa trong task này. Nếu sau này cần dọn Run lỗi, phải thiết kế lưu giữ khóa trước và duyệt SQL riêng; không chạy migration ở đây.

**FormulaTestCase:** dùng chung theo Formula, không theo từng phiên bản; schema không lưu lịch sử các lần kiểm thử đủ để xác nhận an toàn khi xóa. Giữ thao tác **Ngừng sử dụng** hiện có, không xóa test khi xóa bản nháp công thức.

**Quy đổi:** chính sách bảo vệ cặp đơn vị đã được cấu hình, không tự chọn một quy đổi khác thay thế, không tự xử lý overlap hoặc quyết định ngày nào chắc chắn không còn dùng. Nếu có nhiều quy đổi thay thế, vẫn có thể phải điều chỉnh cấu hình trước khi xóa. Không cấm mọi quy đổi chỉ vì một Run tương lai có thể nhập đơn vị bất kỳ; không xây dependency engine mới.

**Bảng cũ/chưa có màn hình:** RuleTable/RuleRow, CostElementGroup, CostPoolPeriod… chỉ được bảo vệ khi có FK từ bảng đó, không tạo CRUD/xóa mới. Organization/OrganizationMember/Approval/Audit mappings không đưa trở lại business flow. Không tìm kiếm tùy tiện `entity_id` trong các bảng workflow đã ngừng sử dụng.

## Bảo vệ ở backend

- Endpoint whitelist `master_data:record_delete`: GET chỉ đọc; POST mới được xóa, bắt buộc CSRF và xác nhận có chữ ký, đúng loại dữ liệu/ID/trạng thái, hạn 30 phút. Chữ ký gồm cả dữ liệu dòng thuộc phiên bản. Thay đổi sau khi mở hộp thoại phải xác nhận lại.
- Khóa và đọc lại bản ghi trong transaction, kiểm tra lại FK, trạng thái, tham chiếu mã và lịch sử. Lỗi bất kỳ không được báo thành công hoặc để lại phiên bản mất một phần dòng.
- Tái sử dụng khóa nội bộ đã có để phối hợp với Formula/Scheme/Run. Với nguồn tham chiếu mã/quy đổi không có FK trực tiếp, riêng giao dịch xóa lấy khóa bảng ngắn `NOWAIT`: không sửa service ghi/tính giá hiện hữu. Có thao tác ghi đang chạy thì báo đang bận, không chờ vô hạn trên các khóa bảng này. PostgreSQL FK/trigger vẫn là lớp bảo vệ cuối.
- Không tự thêm CASCADE, soft-delete, xóa hàng loạt hoặc nút xóa lịch sử. Chỉ xóa rõ ràng các dòng sở hữu thuộc bản nháp đã kiểm tra.
- HTMX vô hiệu nút khi gửi, chặn gửi lại. POST lặp trả thông báo đã xóa/không còn tồn tại. Xóa từ chi tiết chuyển về danh sách/cha; xóa liên kết từ bảng cập nhật bảng và giữ bộ lọc/phân trang.
- Không xuất SQL, traceback hoặc thông tin kết nối ra hộp thoại. Không kiểm thử xóa dữ liệu thật trên Supabase.