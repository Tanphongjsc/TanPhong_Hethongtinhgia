# Hướng dẫn dữ liệu sản xuất

[Về mục lục](README.md) · [Danh mục cần chuẩn bị](04_HUONG_DAN_DANH_MUC.md) · [Công thức và tính giá thành](06_HUONG_DAN_FORMULA_VA_COSTING.md) · [Tra cứu từng trường](12_FIELD_REFERENCE.md)

**[HỆ THỐNG HIỆN TẠI]** Đối chiếu source ngày 09/10/2026. Chương này hướng dẫn tám mục trong menu **Sản xuất**. Dữ liệu sản xuất mô tả vật tư, bao bì, thời gian và chi phí chung cần cho sản phẩm. Các màn hình này lưu cấu hình; việc chọn nguồn theo ngày và tính tiền diễn ra khi chạy **Lần tính giá thành**.

## 1. Điểm cần hiểu trước khi nhập

| Dữ liệu | Trả lời câu hỏi | Chuẩn bị trước | Được dùng ở đâu? |
| --- | --- | --- | --- |
| BOM / Công thức sản xuất | Làm một sản lượng chuẩn cần bao nhiêu vật tư? | Sản phẩm, Vật tư / Hàng hóa, Đơn vị tính, quy đổi nếu khác đơn vị gốc | Nguồn `MATERIAL_COST` của lần tính |
| Cấu hình bao bì | Một cơ sở đóng gói cần những vật tư bao bì nào? | Sản phẩm, vật tư bao bì, đơn vị, SKU để gán | Nguồn `PACKAGING_COST` |
| Trung tâm sản xuất | Công việc diễn ra tại đâu, có công suất gì? | Đơn vị công suất nếu nhập công suất | Nguồn lực và công đoạn |
| Nguồn lực | Máy, người hoặc dịch vụ nào được sử dụng? | Trung tâm nếu cần, đơn vị nếu nhập công suất | Đơn giá nguồn lực, công đoạn |
| Đơn giá nguồn lực | Một đơn vị sử dụng nguồn lực tốn bao nhiêu tiền? | Nguồn lực, tiền tệ, đơn vị tính giá | Nguồn `RESOURCE_COST` |
| Quy trình sản xuất | Có những công đoạn, thời gian và nguồn lực nào? | Sản phẩm; nguồn lực, trung tâm, đơn vị thời gian nếu dùng | Nguồn `RESOURCE_COST` |
| Nhóm chi phí chung | Chi phí chung được tập hợp vào nhóm nào? | Không có danh mục nghiệp vụ bắt buộc khác trong form | Quy tắc phân bổ, số liệu kỳ |
| Quy tắc phân bổ | Chia chi phí chung theo cơ sở nào? | Nhóm chi phí; đơn vị tiêu thức nếu cần | Nguồn `ALLOCATION:<mã quy tắc>` |

**Cập nhật 20/10/2026:** tạo hoặc sao chép BOM, bao bì, quy trình luôn tạo phiên bản **Nháp**. Với BOM và bao bì, mở chi tiết phiên bản rồi chọn **Kích hoạt phiên bản → Xác nhận kích hoạt** sau khi kiểm tra dữ liệu. Quy trình, đơn giá nguồn lực và quy tắc phân bổ vẫn chưa có thao tác đưa vào hiệu lực. Nhập ngày hôm nay, đánh dấu **Đang hoạt động**, hoặc gán SKU không đổi Nháp thành Đang hiệu lực. Lần tính chỉ chọn nguồn có mã trạng thái `EFFECTIVE` phù hợp ngày tính. Vì vậy có thể hoàn thành bài nhập dữ liệu bằng UI, nhưng chưa thể tự hoàn tất toàn bộ chuỗi từ dữ liệu mới đến tính giá bằng UI. Xem [GAP_REGISTER](GAP_REGISTER.md); bài thực hành dùng dữ liệu demo đã chuẩn bị sẵn trạng thái.

## 2. Cách dùng màn hình chung

Mở menu **Sản xuất**, chọn module. Gõ từ khóa vào ô tìm kiếm; bảng cập nhật sau khi ngừng gõ khoảng 0,4 giây. Chọn bộ lọc để thu hẹp kết quả. Nhấn tiêu đề cột có chức năng sắp xếp hoặc chọn thứ tự sắp xếp; chọn 25, 50 hoặc 100 dòng mỗi trang và chuyển trang ở cuối bảng. Trạng thái tìm, lọc, sắp xếp và trang được giữ trong địa chỉ trang.

| Màn hình danh sách | Tìm kiếm | Bộ lọc |
| --- | --- | --- |
| Định mức nguyên vật liệu | Mã/tên định mức, sản phẩm hoặc SKU | Sản phẩm; SKU của sản phẩm; trạng thái phiên bản mới nhất; hiệu lực theo ngày; trạng thái định mức |
| Cấu hình bao bì | Mã/tên/mô tả cấu hình, sản phẩm, SKU đã gán | Sản phẩm; SKU đã gán; trạng thái phiên bản mới nhất; hiệu lực theo ngày; trạng thái cấu hình |
| Trung tâm sản xuất | Mã/tên trung tâm, mã địa điểm | Trạng thái |
| Nguồn lực sản xuất | Mã/tên nguồn lực | Loại nguồn lực; Trung tâm sản xuất; Trạng thái |
| Đơn giá nguồn lực | Mã/tên nguồn lực hoặc trung tâm | Nguồn lực; Loại nguồn lực; Trung tâm sản xuất; Mã loại đơn giá; Tiền tệ; Đơn vị tính giá; Hiệu lực theo ngày; Trạng thái bản ghi |
| Quy trình sản xuất | Mã/tên quy trình, sản phẩm hoặc SKU | Sản phẩm; SKU của sản phẩm; trạng thái phiên bản mới nhất; hiệu lực theo ngày; trạng thái quy trình |
| Nhóm chi phí chung | Mã/tên/mô tả nhóm | Loại nhóm chi phí; Trạng thái |
| Quy tắc phân bổ | Mã/tên quy tắc hoặc nhóm chi phí | Nhóm chi phí; Tiêu thức phân bổ; Đơn vị tiêu thức; Trạng thái bản ghi; Hiệu lực theo ngày |

Nếu bảng trống, bỏ bộ lọc trước khi kết luận thiếu dữ liệu. Dùng **Xem chi tiết** để kiểm tra bản ghi; dùng **Chỉnh sửa** hoặc liên kết chỉnh sửa thông tin ở trang chi tiết để sửa. Trường báo lỗi giữ lại nội dung đã nhập. Sửa trường có thông báo rồi nhấn lại nút lưu. Khi lưu thành công, thông báo xác nhận xuất hiện và trang chi tiết/bảng thành phần được cập nhật.

**Hủy** đóng form mà không lưu. Thành phần BOM mở vùng nhập ngay trong trang; thành phần bao bì và công đoạn mở bảng nhập trượt từ cạnh màn hình. Có thể mở đường dẫn form riêng nếu không sử dụng được vùng nhập này. Xóa dòng luôn cần nhấn **Xóa** rồi **Xác nhận xóa**; chỉ mở hộp xác nhận chưa xóa dữ liệu.

Các header có ô **Đang hoạt động**. Bỏ chọn rồi lưu sẽ mở xác nhận **Ngừng hoạt động danh mục**; nhấn **Xác nhận và lưu** để hoàn tất. Không có thao tác xóa hẳn danh mục, header hoặc phiên bản trong các module này. Ngừng hoạt động giữ dữ liệu để xem lịch sử, nhưng có thể khiến lần tính mới không chọn được nguồn.

Nhập số thập phân bằng dấu chấm, ví dụ `0.08333333`. Bảng hiển thị theo định dạng Việt Nam, ví dụ `0,08333333`. Tiền, số lượng, thời gian và quy cách hỗ trợ tối đa tám chữ số thập phân; trường phần trăm BOM hỗ trợ tối đa sáu chữ số thập phân trên UI. Đơn vị và tiền tệ được chọn rõ ràng, không suy ra từ tên trường.

## 3. BOM / Công thức sản xuất

### Khi nào dùng?

BOM là định mức đầu vào của **Sản phẩm**. Mỗi phiên bản mô tả sản lượng chuẩn, đơn vị đầu ra, tỷ lệ thu hồi và các dòng vật tư. Dùng khi tạo sản phẩm mới, thay công thức hoặc thay mức hao hụt. BOM tham chiếu Vật tư / Hàng hóa đã tồn tại; không tạo vật tư hay SKU ngầm.

SKU trong bộ lọc giúp tìm BOM của Sản phẩm chứa SKU đó. BOM không có trường gán riêng cho từng SKU. Nếu các SKU dùng chung sản phẩm, chúng cùng tìm nguồn BOM của sản phẩm ấy; lượng tịnh của SKU giúp quy đổi sản lượng khi chạy tính giá.

### Tạo định mức và thành phần

1. Chuẩn bị Sản phẩm, các vật tư và đơn vị. Nếu dòng dùng đơn vị khác **Đơn vị cơ sở** của vật tư, chuẩn bị quy đổi trực tiếp phù hợp ngày bắt đầu phiên bản; nếu phiên bản chưa có ngày bắt đầu, hệ thống kiểm tra theo hôm nay.
2. Vào **Sản xuất → BOM / Công thức sản xuất**, nhấn **+ Thêm định mức**. Trang có tiêu đề **Thêm định mức**.
3. Chọn **Sản phẩm**, nhập **Mã định mức**, **Tên định mức**; điền **Mô tả** nếu cần và giữ **Đang hoạt động** nếu tiếp tục sử dụng. Mã được bỏ khoảng trắng đầu/cuối và chuyển thành chữ hoa; mã không được trùng.
4. Trong phần phiên bản đầu, nhập **Sản lượng chuẩn**, **Đơn vị tính đầu ra**, **Tỷ lệ thu hồi (%)**. Thu hồi mặc định 100%; phải lớn hơn 0 và không vượt 100%. Có thể để trống cả hai ngày hiệu lực của Nháp. Nếu nhập ngày kết thúc, phải nhập ngày bắt đầu và ngày kết thúc phải sau ngày bắt đầu.
5. Nhấn **Lưu định mức nguyên vật liệu**. Header và phiên bản đầu được lưu cùng nhau; lỗi ở phiên bản không để lại một định mức tạo dở.
6. Ở chi tiết phiên bản, nhấn **+ Thêm thành phần**. Chọn **Vật tư / Hàng hóa**, nhập **Số lượng**, chọn **Đơn vị tính**, nhập **Tỷ lệ hao hụt (%)**; mặc định hao hụt 0%. Nhập **Mã công đoạn**, **Nhóm thay thế**, đánh dấu **Thành phần tùy chọn**, nhập **Thứ tự**, **Ghi chú** chỉ khi cần. Nhấn **Lưu thành phần**.
7. Lặp lại cho các vật tư. Kiểm tra bảng có đủ dòng, đúng đơn vị, số lượng và hao hụt. Hai dòng cùng một vật tư được phép; tránh nhập lặp ngoài ý muốn vì lần tính cộng từng dòng.

**[VÍ DỤ NGHIỆP VỤ]** Một mẻ chuẩn 100 kg cần 20 kg cà phê, 60 kg đường, 20 kg bột sữa, thu hồi 100%, hao hụt từng dòng 0%. Tính cho 250 kg thì hệ số sản lượng là `250 / 100 = 2,5`; nhu cầu tương ứng 50, 150 và 50 kg. Nếu dòng cà phê có hao hụt 2% và phiên bản thu hồi 98%, nhu cầu là `20 × 2,5 / 0,98 / (1 − 0,02) = 52,06164098… kg`. Không cộng thu hồi với hao hụt hoặc tự tăng số lượng đã nhập. Công thức thực thi là `số lượng dòng × hệ số sản lượng / thu hồi / (1 − hao hụt)`; tiền vật tư còn cần giá mua và quy đổi phù hợp.

Form cho lưu **Nhóm thay thế** và **Thành phần tùy chọn**, nhưng engine chưa có quy tắc chọn các thành phần ấy và sẽ chặn lần tính. Khi chuẩn bị BOM cho khả năng tính hiện tại, dùng các dòng bắt buộc đã xác định rõ, không bật tùy chọn hay điền nhóm thay thế. **Mã công đoạn** là tham chiếu văn bản, không tự liên kết với công đoạn Routing hay phân bổ vật tư theo công đoạn.

### Kích hoạt BOM để dùng khi tính giá

1. Mở **Sản xuất → Định mức / Công thức sản xuất**, chọn định mức và đúng phiên bản cần dùng.
2. Kiểm tra Sản phẩm, sản lượng chuẩn, đơn vị, thu hồi và đủ thành phần. Muốn bổ sung ngày, chọn **Chỉnh sửa phiên bản**, nhập **Hiệu lực từ ngày** rồi lưu. Nếu có ngày kết thúc, ngày đó phải sau ngày bắt đầu.
3. Nhấn **Kích hoạt phiên bản → Xác nhận kích hoạt**. Nếu báo lỗi, đọc nội dung trên đầu trang, sửa dữ liệu rồi thực hiện lại. Bản lỗi vẫn là Nháp; không có kích hoạt dở dang.
4. Kiểm tra trạng thái phiên bản **Đang hiệu lực**. Ngày tính giá phải nằm trong khoảng áp dụng. Trạng thái theo ngày và ô **Đang hoạt động** không thay thế bước này.
5. Sau khi kích hoạt, không chỉnh sửa/xóa thành phần trực tiếp. Muốn đổi định mức, tạo phiên bản mới. Không tự sửa database hoặc đổi lịch sử đã chốt.

Hệ thống không cho hai phiên bản Đang hiệu lực của các định mức đang hoạt động cùng Sản phẩm chồng ngày. Ngày cuối vẫn được tính: bản cũ kết thúc 31/10 thì bản mới có thể bắt đầu 01/11. Nếu bản cũ không có ngày kết thúc, báo người phụ trách để thống nhất lịch áp dụng; nút kích hoạt không tự đóng bản cũ. Giá mua vật tư vẫn cần đủ điều kiện riêng; kích hoạt BOM không kích hoạt giá mua.

### Sửa và thay phiên bản

Ở chi tiết, **Chỉnh sửa thông tin định mức** sửa header; **Chỉnh sửa phiên bản** sửa sản lượng, đơn vị, thu hồi, ngày và lý do của bản còn sửa được. Trong bảng thành phần, dùng **Chỉnh sửa**, **Xóa** tương ứng từng dòng. Đổi ngày bắt đầu sẽ kiểm tra lại quy đổi của tất cả thành phần.

Để thay công thức và giữ bản trước, mở phiên bản nguồn rồi chọn **Tạo phiên bản mới từ phiên bản N**, hoặc dùng **Lịch sử phiên bản → Tạo phiên bản mới** ở dòng nguồn. Form được điền cấu hình từ bản nguồn; sửa ngày, **Lý do thay đổi** và các thông số cần thiết, nhấn **Lưu phiên bản định mức**. Toàn bộ thành phần được sao chép, kể cả các dòng không nằm trên trang đang xem. Phiên bản mới Nháp; bản nguồn giữ nguyên. Nút **+ Tạo phiên bản mới** từ lịch sử, khi không chọn nguồn, tạo bản mới chưa có thành phần.

**Trường hợp hợp lệ:** sản lượng và số lượng dòng > 0; thu hồi trong `(0,100%]`; hao hụt trong `[0,100%)`; quy đổi trực tiếp phù hợp nếu dùng đơn vị khác đơn vị gốc. **Trường hợp không hợp lệ:** sản lượng bằng 0, thu hồi 0%, hao hụt 100%, thiếu vật tư/đơn vị, ngày kết thúc không sau ngày bắt đầu, chọn mới danh mục đã ngừng hoạt động, hoặc thiếu quy đổi.

Sau khi nhập, kiểm tra: đúng Sản phẩm; đúng sản lượng/đơn vị đầu ra; đủ dòng; đúng đơn vị/thu hồi/hao hụt; đúng phiên bản/ngày. Chọn **Kích hoạt phiên bản → Xác nhận kích hoạt** trước khi chạy tính giá; xem hướng dẫn ngay phía trên. Sau đó kiểm tra Giá nhà cung cấp của từng vật tư và cấu hình phương án tính giá thành.

## 4. Cấu hình bao bì và gán SKU

### Cấu hình bao bì khác BOM thế nào?

BOM mô tả vật tư theo sản lượng sản xuất; bao bì mô tả vật tư đóng gói cho SKU qua liên kết riêng. Header bao bì thuộc Sản phẩm; SKU được gán vào **cấu hình**, không gán trực tiếp vào một phiên bản. Phiên bản chứa quy cách và các dòng bao bì. Không có trường sản lượng chuẩn, đơn vị đầu ra, thu hồi hay hao hụt trong phiên bản bao bì. Người chạy lần tính phải khai báo cơ sở sản lượng đóng gói rõ ràng.

### Tạo, thêm dòng và gán SKU

1. Chuẩn bị Sản phẩm, SKU của cùng Sản phẩm, vật tư bao bì, đơn vị và giá nhà cung cấp. Loại vật tư **Bao bì** được ưu tiên trong lựa chọn; form vẫn cho chọn loại vật tư khác.
2. Vào **Sản xuất → Cấu hình bao bì**, nhấn **+ Thêm cấu hình bao bì**. Chọn **Sản phẩm**, nhập **Mã cấu hình**, **Tên cấu hình**, **Mô tả** nếu cần; giữ **Đang hoạt động**.
3. Nhập quy cách nếu biết: **Khối lượng tổng**, **Đơn vị trọng lượng**, **Chiều dài**, **Chiều rộng**, **Chiều cao**, **Đơn vị kích thước**. Giá trị không âm. Khi nhập khối lượng, phải chọn đơn vị thuộc đại lượng khối lượng; khi nhập bất kỳ kích thước nào, phải chọn đơn vị thuộc đại lượng chiều dài. Quy cách đều có thể để trống. Nhập ngày và **Lý do thay đổi** nếu cần.
4. Nhấn **Lưu cấu hình bao bì**; nhận phiên bản đầu Nháp. Nhấn **+ Thêm thành phần**, chọn **Vật tư bao bì**, nhập **Số lượng**, chọn **Đơn vị tính**, **Cấp đóng gói**. Nhập **Cấp cha**, **Số đơn vị trong cấp cha** nếu cần mô tả cấu trúc; số đơn vị phải > 0 khi có. Nhập các thông tin bổ sung rồi nhấn **Lưu thành phần bao bì**.
5. Trong **SKU sử dụng cấu hình**, nhấn **+ Gán SKU**. Chọn **SKU**, đánh dấu **Cấu hình chính** nếu muốn dùng làm cấu hình chính; nhập **Hiệu lực từ ngày**, **Hiệu lực đến ngày** nếu cần. Nhấn **Lưu liên kết SKU**. SKU phải thuộc cùng Sản phẩm của cấu hình. Ngày liên kết độc lập với ngày phiên bản.
6. Kiểm tra thông tin gán ở trang chi tiết. Trang chỉ xem trước năm liên kết gần nhất; dùng **Xem tất cả liên kết SKU** để tìm, lọc hiệu lực, sắp xếp và phân trang các liên kết khác. Dùng **Chỉnh sửa** bên cạnh SKU để sửa liên kết.

| Cấp đóng gói trên UI | Mã lưu | Cách hiểu |
| --- | --- | --- |
| Cấp 1 · Bao bì trực tiếp | PRIMARY | Bao bì tiếp xúc/bao từng đơn vị trực tiếp |
| Cấp 2 · Bao bì nhóm | SECONDARY | Gộp các đơn vị nhỏ |
| Cấp 3 · Bao bì vận chuyển | TERTIARY | Đơn vị dùng khi vận chuyển |
| Kiện trên pallet | PALLET | Nhóm trên pallet |
| Công-ten-nơ | CONTAINER | Cấp container |

**[VÍ DỤ NGHIỆP VỤ]** Quy ước cơ sở đóng gói là **1 hộp bán**, mỗi hộp có 20 gói: lưu dòng túi gói số lượng 20 cái, dòng hộp số lượng 1 cái. Nếu một thùng chứa 12 hộp thì lượng vật tư thùng trên cơ sở 1 hộp có thể nhập `0.08333333` cái, hoặc chọn cơ sở 12 hộp và nhập 240 túi, 12 hộp, 1 thùng. Cách thứ hai biểu diễn trọn thùng chính xác hơn. Khi chạy 120 hộp với cơ sở 12 hộp, hệ số là 10: 2.400 túi, 120 hộp, 10 thùng. Khi chạy 10 hoặc 100 hộp, nhân từng dòng với `10/12` hoặc `100/12`; hệ thống không tự làm tròn số thùng thành số nguyên.

Nếu nghiệp vụ gọi một hộp có 20 gói và một carton riêng cho mỗi hộp, nhập rõ các dòng 20 gói, 1 hộp, 1 carton trên cơ sở 1 hộp; lần tính 10/100 hộp sẽ dùng 200/2.000 gói, 10/100 hộp, 10/100 carton. Chọn số liệu theo cấu trúc đóng gói thực tế, tránh vừa tính gói như vật tư BOM vừa tính lại cùng vật tư trong bao bì.

**Cấp cha** và **Số đơn vị trong cấp cha** chỉ mô tả cấu trúc; engine dùng số lượng dòng đã nhập nhân hệ số cơ sở. Nó không tự đi qua cây đóng gói, nhân cấp cha hay tính số thùng/container. **Mã thị trường** và **Mã mẫu thiết kế** là dữ liệu có thể lưu nhưng Run chưa có bộ chọn điều kiện; có giá trị ở các trường này sẽ chặn nguồn bao bì khi tính.

### Sửa, đổi bao bì và lỗi thường gặp

**Chỉnh sửa thông tin cấu hình** sửa header. **Chỉnh sửa phiên bản** sửa quy cách/ngày/lý do. Sửa hoặc xóa thành phần bằng thao tác trên dòng. Muốn giữ lịch sử quy cách, mở bản nguồn rồi chọn **Tạo phiên bản mới từ phiên bản N**, sửa thông số và nhấn **Lưu phiên bản bao bì**. Toàn bộ dòng được sao chép; các liên kết SKU thuộc header vẫn giữ nguyên, không tạo lại theo phiên bản mới.

Ngày bắt đầu liên kết mặc định hôm nay, **Cấu hình chính** mặc định được chọn. Hệ thống cấm lặp đúng bộ SKU + cấu hình + ngày bắt đầu; nhưng form chưa cấm nhiều cấu hình chính hoặc bản Nháp trùng kỳ. Riêng khi kích hoạt phiên bản bao bì, hệ thống chặn chồng ngày với bản Đang hiệu lực của cùng cấu hình. Engine cần duy nhất một liên kết chính và một phiên bản hiệu lực. Khi đổi cấu hình cho SKU, thêm liên kết kỳ mới, kiểm tra ngày kết thúc kỳ cũ và tránh cùng ngày biên. Chưa có nút xóa liên kết SKU hoặc khóa liên kết do đã được dùng.

**Trường hợp hợp lệ:** số lượng dòng > 0; số đơn vị trong cấp cha > 0 nếu nhập; quy cách ≥ 0 với đúng đơn vị; SKU cùng Sản phẩm; ngày kết thúc sau ngày bắt đầu. **Trường hợp không hợp lệ:** SKU thuộc Sản phẩm khác, lặp cùng ngày gán, số lượng 0, thiếu đơn vị trọng lượng/kích thước khi đã nhập số đo, thiếu quy đổi của dòng.

Kiểm tra sau khi nhập: đúng Sản phẩm/SKU; một cấu hình chính phù hợp ngày dự kiến; đủ vật tư; lượng dòng cùng một cơ sở đóng gói; ngày liên kết và phiên bản đúng; giá mua có sẵn. Ghi lại cơ sở đóng gói để nhập vào Run. Gán SKU thành công không đưa phiên bản Nháp vào hiệu lực.

### Kích hoạt phiên bản bao bì

Sau khi nhập đủ thành phần và gán đúng SKU, mở chi tiết đúng phiên bản bao bì. Kiểm tra ngày bắt đầu/kết thúc, vật tư và đơn vị. Nhấn **Kích hoạt phiên bản → Xác nhận kích hoạt** và kiểm tra trạng thái phiên bản **Đang hiệu lực**.

Nếu thiếu ngày, chưa có thành phần, danh mục ngừng hoạt động, thiếu quy đổi hoặc chồng ngày với bản hiệu lực của cùng cấu hình, hệ thống báo lỗi trên trang và chưa kích hoạt. Sửa đúng nguyên nhân rồi thử lại. Không tự đóng hoặc sửa bản cũ đã chốt. Sau kích hoạt, muốn thay thành phần phải tạo phiên bản mới.

Gán SKU và trạng thái **Đang hoạt động** không tự kích hoạt phiên bản. Lần tính vẫn cần đúng liên kết SKU, giá mua hiệu lực của từng vật tư và cơ sở đóng gói nhập trên form chạy. Nút này không tự lấy giá hoặc tính chi phí bao bì.

## 5. Trung tâm sản xuất

Trung tâm là nơi hoặc nhóm thực hiện sản xuất, ví dụ tổ trộn hoặc dây chuyền đóng gói. Dùng để tổ chức nguồn lực và công đoạn; không phải hồ sơ tài sản hay lịch vận hành máy.

1. Vào **Sản xuất → Trung tâm sản xuất**, nhấn **+ Thêm mới**.
2. Nhập **Mã trung tâm sản xuất**, **Tên trung tâm**; nhập **Mã địa điểm** nếu có.
3. Nhập **Công suất**, **Công suất bình thường** nếu đã xác định và chọn **Đơn vị công suất**. Hai giá trị có thể trống; nếu nhập một trong hai, đơn vị bắt buộc. Giá trị 0 hợp lệ, số âm không hợp lệ. Không có kiểm tra buộc công suất bình thường nhỏ hơn công suất.
4. Giữ **Đang hoạt động**, nhấn **Lưu trung tâm sản xuất**. Kiểm tra tên, công suất và đơn vị trên trang chi tiết.
5. Muốn sửa, chọn **Chỉnh sửa**, sửa các trường và lưu. Muốn ngừng sử dụng, bỏ **Đang hoạt động**, lưu và xác nhận.

**[VÍ DỤ NGHIỆP VỤ]** `WC_TRON` — Tổ trộn, địa điểm `XUONG_A`, công suất 120, công suất bình thường 100, đơn vị kg. Bản ghi không có trường kỳ thời gian, nên cần thống nhất ngoài hệ thống ý nghĩa công suất này. Nó không tự sinh lịch công suất hay số liệu kỳ dùng để phân bổ.

Trang chi tiết hiển thị tối đa mười nguồn lực của trung tâm; dùng liên kết danh sách để xem đầy đủ. Tiếp theo tạo nguồn lực. Kiểm tra: mã duy nhất; tên rõ ràng; đơn vị công suất đúng khi có giá trị; trạng thái hoạt động phù hợp. Thay công suất tại đây không tự ghi **Công suất bình thường** vào số liệu kỳ của Nhóm chi phí chung.

## 6. Nguồn lực

Nguồn lực là máy, nhân công, trung tâm hoặc dịch vụ được dùng cho công đoạn. Đây là đầu mối lưu đơn giá sử dụng. Không có trường mô tả, nguyên giá tài sản, thời gian khấu hao hay hồ sơ nhân viên trong form này.

1. Vào **Sản xuất → Nguồn lực**, nhấn **+ Thêm mới**.
2. Nhập **Mã nguồn lực**, **Tên nguồn lực**; chọn **Loại nguồn lực**: **Máy móc** (`MACHINE`), **Nhân công** (`LABOR`), **Trung tâm sản xuất** (`WORK_CENTER`), hoặc **Dịch vụ** (`SERVICE`).
3. Chọn **Trung tâm sản xuất** nếu nguồn lực thuộc trung tâm. Có thể để trống để dùng nguồn lực chung. Nhập **Công suất** nếu cần và **Đơn vị công suất** tương ứng; không âm.
4. Giữ **Đang hoạt động**, nhấn **Lưu nguồn lực sản xuất**. Kiểm tra loại, trung tâm và đơn vị.
5. Tại chi tiết có lịch sử đơn giá, nút **Thêm đơn giá** chọn sẵn nguồn lực còn hoạt động. Tạo đơn giá trước khi tính công đoạn.

**[VÍ DỤ NGHIỆP VỤ]** `MAY_TRON` — Máy trộn, loại **Máy móc**, thuộc `WC_TRON`; `TO_DONG_GOI` — Tổ đóng gói, loại **Nhân công**. Một nguồn lực có thể có nhiều bản ghi giá theo ngày. Tên loại không tự chọn đơn giá hay gắn loại chi phí vào phương án.

**Chỉnh sửa** cho sửa bản ghi hiện tại; dữ liệu kỹ thuật ẩn được giữ. Nếu chọn mới một trung tâm đã ngừng hoạt động hoặc mã nguồn lực trùng, form báo lỗi. Tham chiếu đã ngừng hoạt động đang gắn với bản ghi vẫn được giữ để xem/sửa lịch sử; điều đó không làm nguồn ấy đủ điều kiện cho lần tính mới.

Kiểm tra: đúng loại; trung tâm đúng; không gán nhầm máy và nhân công; công suất có đơn vị; trạng thái hoạt động; có đơn giá phù hợp ngày. Tiếp theo dùng nguồn lực làm **Nguồn lực chính** ở công đoạn.

## 7. Đơn giá nguồn lực

Đơn giá diễn tả một khoản tiền trên một đơn vị sử dụng, ví dụ VND/giờ. Form không ép đơn vị phải là thời gian; để tính công đoạn hiện tại, đơn vị tính giá phải quy đổi được với đơn vị thời gian công đoạn. Đơn giá không có bảng phiên bản riêng.

1. Vào **Sản xuất → Đơn giá nguồn lực → + Thêm mới**, hoặc vào chi tiết nguồn lực → **Thêm đơn giá**.
2. Chọn **Nguồn lực**. Nhập **Mã loại đơn giá** do doanh nghiệp thống nhất, ví dụ `STANDARD`. Đây là văn bản tự nhập, tối đa 50 ký tự; không có danh mục loại giá riêng. Hệ thống bỏ khoảng trắng đầu/cuối và giữ cách viết hoa/thường.
3. Nhập **Đơn giá**, chọn **Tiền tệ**, **Đơn vị tính giá**. Giá 0 hợp lệ; giá âm không hợp lệ. Không tự lấy tiền tệ hay đơn vị từ nguồn lực.
4. Nhập **Hiệu lực từ ngày** (mặc định hôm nay); để trống **Hiệu lực đến ngày** nếu chưa giới hạn. Nếu nhập ngày kết thúc, phải sau ngày bắt đầu. Điền **Nguồn dữ liệu / Tham chiếu** như bảng đơn giá tháng hoặc tài liệu xác nhận.
5. Nhấn **Lưu đơn giá nguồn lực**, kiểm tra mức tiền/đơn vị/ngày và trạng thái bản ghi trên chi tiết. Bản mới là Nháp; chưa có nút đổi trạng thái ở đây.

**[VÍ DỤ NGHIỆP VỤ]** Máy trộn có giá 120.000 VND/giờ. Công đoạn dùng 15 phút thiết lập và 30 phút chạy cho 100 kg; tính 200 kg thì dùng `15 + 30 × 200/100 = 75 phút = 1,25 giờ`, tương ứng 150.000 VND nếu đơn giá nguồn lực hiệu lực là mức trên và có quy đổi phút/giờ.

Khi đơn giá thay đổi từ kỳ mới, **thêm bản ghi mới** để giữ giá cũ. **Chỉnh sửa** vẫn cập nhật trực tiếp bản ghi đang mở, kể cả trạng thái đã chốt; module này không có khóa phiên bản như BOM. Không suy ra giá đã được dùng sẽ tự khóa. Kiểm tra tác động trước khi sửa dữ liệu nguồn của lần tính mới.

**[HỆ THỐNG HIỆN TẠI]** Engine cần đúng một đơn giá `EFFECTIVE` của nguồn lực tại ngày tính, chưa chọn theo **Mã loại đơn giá**. Hai mức giá hiệu lực cùng ngày, dù khác loại giá, gây lỗi mơ hồ. Các ngày kết thúc nguồn Costing bao gồm ngày kết thúc; nếu mức cũ kết thúc 31/10 thì mức mới có thể bắt đầu 01/11, tránh để cả hai cùng ngày 31/10. Không có kiểm tra tự ngăn chồng kỳ trong form. Đơn giá khác tiền tệ Run bị chặn, không tự dùng FX của Pricing.

Kiểm tra: đúng nguồn lực; đúng mã loại giá; mức tiền không âm; đúng tiền tệ/đơn vị; quy đổi thời gian có sẵn; một giá hiệu lực duy nhất ở ngày dùng. Có thể tìm giá cũ trong lịch sử đơn giá ở chi tiết nguồn lực hoặc danh sách đơn giá đã lọc nguồn lực.

## 8. Quy trình sản xuất và công đoạn

Quy trình là thứ tự công việc để tạo **Sản phẩm**. Mỗi phiên bản có sản lượng lô và các công đoạn; mỗi công đoạn chỉ có **một Nguồn lực chính** tùy chọn. Dùng khi chi phí máy/nhân công phụ thuộc thời gian. Bộ lọc SKU tìm quy trình của Sản phẩm, không tạo quy trình gắn riêng SKU.

### Tạo quy trình

1. Chuẩn bị Sản phẩm; nguồn lực, trung tâm và đơn giá; đơn vị thời gian và quy đổi cần thiết.
2. Vào **Sản xuất → Quy trình sản xuất**, nhấn **+ Thêm quy trình**. Chọn **Sản phẩm**, nhập **Mã quy trình**, **Tên quy trình**, giữ **Đang hoạt động**.
3. Nhập **Sản lượng lô chuẩn** và **Đơn vị tính sản lượng lô** nếu dùng cơ sở chung cho các công đoạn. Có thể để trống cả cặp. Nếu nhập một trường thì trường còn lại bắt buộc; sản lượng phải > 0. Nhập ngày và **Lý do thay đổi** nếu cần.
4. Nhấn **Lưu quy trình sản xuất**. Kiểm tra phiên bản đầu Nháp. Nhấn **+ Thêm công đoạn**.
5. Nhập **Thứ tự công đoạn**; hệ thống gợi ý số lớn nhất hiện có + 10, bắt đầu 10. Số phải là số nguyên dương, không trùng trong cùng phiên bản. Nhập **Mã công đoạn**, **Tên công đoạn**; mã công đoạn được chuyển chữ hoa.
6. Chọn **Trung tâm sản xuất** nếu cần. Sau khi đổi trung tâm, danh sách **Nguồn lực chính** được tải lại, chỉ gồm nguồn lực của trung tâm ấy hoặc nguồn lực chung. Chọn nguồn lực chính trong phần **Nguồn lực sử dụng**. Nếu chọn nguồn lực thuộc một trung tâm, nên chọn đúng trung tâm ở công đoạn; để trống trung tâm dù form có thể lưu sẽ không đáp ứng kiểm tra thực thi khi tính thời gian.
7. Nhập **Thời gian thiết lập**, **Thời gian chạy**, **Đơn vị thời gian**. Hai thời gian mặc định 0, vẫn là trường phải có giá trị. Khi một trong hai khác 0, đơn vị thời gian bắt buộc và phải thuộc đại lượng thời gian.
8. Nếu công đoạn có cơ sở riêng, nhập **Sản lượng cơ sở**, **Đơn vị tính sản lượng cơ sở**; phải nhập đủ cặp, sản lượng > 0. Nếu để trống thì engine dùng cơ sở lô của phiên bản. Điền **Ghi chú**, nhấn **Lưu công đoạn**.
9. Thêm các công đoạn còn lại, kiểm tra thứ tự, thời gian, nguồn lực và cơ sở. Sửa bằng **Chỉnh sửa**, xóa bằng **Xóa → Xác nhận xóa** ở dòng.

### Thời gian tạo ra chi phí thế nào?

**[VÍ DỤ NGHIỆP VỤ]** Quy trình Trộn → Đóng gói → Kiểm tra. Mỗi công đoạn có máy hoặc nhân công chính và đơn giá riêng. Cho công đoạn trộn: thiết lập 15 phút; chạy 30 phút/100 kg. Tính 200 kg: thời gian thiết lập tính một lần; thời gian chạy nhân 2, tổng 75 phút. Không lấy `(15 + 30) × 2`. Nếu chỉ có thiết lập và thời gian chạy 0, không cần sản lượng cơ sở để nhân thời gian. Công đoạn có cả hai thời gian 0 được ghi nhận mức sử dụng 0.

Chi phí nguồn lực bằng lượng sử dụng đã quy đổi sang **Đơn vị tính giá** nhân đơn giá. Nguồn `RESOURCE_COST` cộng chi phí các công đoạn; loại Máy móc/Nhân công được nhận diện qua nguồn lực/trace, không có resolver máy và nhân công riêng. Không dùng **Công suất** của header nguồn lực để tự suy thời gian.

**Trường hợp form cho lưu nhưng chưa đủ để tính:** công đoạn có thời gian nhưng chưa chọn nguồn lực chính; thời gian chạy > 0 mà thiếu cả cơ sở công đoạn lẫn cơ sở lô; đơn vị giá không quy đổi được với thời gian; nguồn lực có nhiều đơn giá hiệu lực. Form chỉ kiểm tra cấu hình có thể lưu, không chạy thử engine ở màn hình này.

### Đổi quy trình và kiểm tra

**Chỉnh sửa thông tin quy trình** sửa header. **Chỉnh sửa phiên bản** sửa lô/ngày/lý do. Để giữ quy trình cũ, vào phiên bản nguồn → **Tạo phiên bản mới từ phiên bản N**, đổi ngày/lý do, nhấn **Lưu phiên bản quy trình**. Toàn bộ công đoạn và nguồn lực tham chiếu được sao chép sang Nháp; bản nguồn không đổi. **+ Tạo phiên bản mới** không chọn nguồn tạo bản chưa có công đoạn.

**Trường hợp hợp lệ:** thứ tự dương và duy nhất; mã/tên có giá trị; thời gian không âm; đơn vị TIME khi có thời gian; cơ sở dương với đơn vị; nguồn lực thuộc trung tâm chọn hoặc dùng chung. **Trường hợp không hợp lệ:** thứ tự 0/trùng, thời gian âm, dùng kg làm đơn vị thời gian, nhập cơ sở nhưng thiếu đơn vị, chọn nguồn lực khác trung tâm.

Kiểm tra sau khi nhập: đúng Sản phẩm; đúng phiên bản/ngày; đủ công đoạn; đúng thứ tự; thiết lập tách khỏi chạy; có nguồn lực chính và đơn giá cho công đoạn phát sinh thời gian; cơ sở lô/công đoạn đủ rõ. Tiếp theo kiểm tra phương án có dòng `RESOURCE_COST` nếu muốn tính nguồn này.

## 9. Nhóm chi phí chung và quy tắc phân bổ

Chi phí chung là khoản không gắn trực tiếp với một dòng vật tư, như chi phí chung nhà máy. **Nhóm chi phí chung** là nơi đặt tên nhóm; **Quy tắc phân bổ** mô tả cách chia. **Tiêu thức phân bổ** là cơ sở để chia, ví dụ sản lượng sử dụng so với công suất bình thường. Tạo một Nhóm chi phí không tự thêm khoản tiền hoặc phần tử chi phí vào phương án.

### Tạo nhóm và quy tắc

1. Vào **Sản xuất → Nhóm chi phí chung**, nhấn **+ Thêm nhóm chi phí**.
2. Nhập **Mã nhóm chi phí**, **Tên nhóm chi phí**, chọn **Loại nhóm chi phí**: Chi phí cố định nhà máy, Chi phí biến đổi nhà máy, Đảm bảo chất lượng, Kho vận, Xuất khẩu, Khác. Nhập **Mô tả** nếu cần; giữ **Đang hoạt động**. Nhấn **Lưu nhóm chi phí chung**.
3. Ở chi tiết nhóm, nhấn **+ Thêm quy tắc phân bổ** để chọn sẵn nhóm; hoặc vào **Sản xuất → Quy tắc phân bổ → + Thêm quy tắc phân bổ**.
4. Nhập **Mã quy tắc**, **Tên quy tắc**, chọn **Nhóm chi phí**, **Tiêu thức phân bổ**. Chọn **Đơn vị tiêu thức** nếu cần. **Mã công thức tham chiếu** là văn bản tùy chọn; form chỉ lưu mã, không kiểm tra sự tồn tại hay thực thi công thức.
5. Nhập **Mức ưu tiên** (mặc định 100); cho phép số nguyên âm trong phạm vi 32 bit, không có quy tắc phải ≥ 0. Nhập **Hiệu lực từ ngày** (mặc định hôm nay), **Hiệu lực đến ngày** nếu cần. Nhấn **Lưu quy tắc phân bổ**.
6. Kiểm tra chi tiết và bảng quy tắc ở chi tiết nhóm. Có thể tìm/lọc/sắp xếp/phân trang các quy tắc liên quan.

| Tiêu thức có trong form | Mã | Khả năng thực thi hiện tại |
| --- | --- | --- |
| Công suất bình thường | NORMAL_CAPACITY | Có, nếu đủ số liệu kỳ và điều kiện dưới đây |
| Giờ máy | MACHINE_HOUR | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Giờ lao động | LABOR_HOUR | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Khối lượng (kg) | KG | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Số đơn vị | UNIT | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Số lô | BATCH | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Ngày lưu pallet | PALLET_DAY | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Số chuyến hàng | SHIPMENT | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Giá trị | VALUE | Lưu cấu hình; engine phân bổ chưa hỗ trợ |
| Tùy chỉnh | CUSTOM | Lưu cấu hình; engine phân bổ chưa hỗ trợ |

### Điều kiện để phân bổ thực sự

**[HỆ THỐNG HIỆN TẠI]** Nguồn `ALLOCATION:<mã quy tắc>` chỉ thực thi `NORMAL_CAPACITY`, không có **Mã công thức tham chiếu** hay điều kiện bổ sung. Cần quy tắc hiệu lực đúng ngày, nhóm hoạt động, và đúng một bản **số liệu kỳ của nhóm chi phí** hiệu lực chứa ngày tính: có số tiền không âm, tiền tệ cùng Run, công suất bình thường > 0 và đơn vị công suất. Nếu quy tắc có đơn vị tiêu thức, phải trùng đơn vị công suất kỳ. Sản lượng sử dụng phải quy đổi được về đơn vị đó và không vượt công suất bình thường.

**[CHƯA HỖ TRỢ]** Chưa có màn hình nhập **số liệu kỳ của nhóm chi phí** (`CostPoolPeriod`). Nhập công suất ở Trung tâm sản xuất không thay thế bước này. UI cũng chưa đưa Quy tắc phân bổ mới từ Nháp vào hiệu lực. Khi thiếu hai điều kiện này, người vận hành không thể tự hoàn thành nguồn phân bổ chỉ qua các form trên. Bài demo dùng số liệu kỳ đã chuẩn bị; không hướng dẫn sửa trực tiếp database để vượt giới hạn.

**[DEMO]** Dữ liệu mẫu có chi phí kỳ 530.000 VND, công suất bình thường 100 hộp. Lần tính 10 hộp phân bổ `530.000 × 10 / 100 = 53.000 VND`, tức 5.300 VND/hộp. Đây là phân bổ theo công suất bình thường, không phải chia toàn bộ 530.000 VND cho lượng chạy 10 hộp. Xem [bài thực hành Cappuccino](09_THUC_HANH_CAPPUCCINO_END_TO_END.md).

**[INDUSTRY PATTERN]** Doanh nghiệp có thể muốn chia điện nhà máy theo giờ máy. Form có **Giờ máy** để lưu cấu hình, nhưng chưa có dữ liệu mẫu số/hợp đồng thực thi cho driver này; không coi đó là quy trình tự động đã hoàn chỉnh. Có thể mô hình hóa một khoản chi phí nhập rõ bằng phần tử chi phí và công thức phù hợp khả năng hiện tại; xem [các kịch bản thực tế](08_KICH_BAN_THUC_TE.md), tránh tính trùng với tiền điện đã nằm trong đơn giá máy.

### Sửa quy tắc và giữ lịch sử

Nhóm và quy tắc có **Chỉnh sửa**; nhóm có thể ngừng hoạt động bằng ô tương ứng. Quy tắc không có ô Đang hoạt động, không có bảng phiên bản, không có nút xóa hoặc nút đưa vào hiệu lực. Khi thay kỳ, thêm quy tắc mới **với mã khác** vì mã duy nhất trên toàn hệ thống hiện tại, không chỉ trong từng nhóm. Nếu phương án tham chiếu `ALLOCATION:<mã cũ>`, cần phiên bản phương án mới tham chiếu mã mới theo hướng dẫn Costing. Chỉ tạo quy tắc mới không tự chuyển phương án sang dùng nó.

Chỉnh sửa cập nhật trực tiếp và giữ trạng thái/điều kiện bổ sung đang lưu; không áp khóa phiên bản BOM cho quy tắc. **Mức ưu tiên** chưa biến thành chính sách tự chọn giữa nhiều quy tắc; nguồn thực thi tìm theo mã quy tắc. Không có bảng thành viên Nhóm chi phí → Phần tử chi phí, dòng chia theo sản phẩm hay trường chọn đối tượng phân bổ trong form.

**Trường hợp hợp lệ:** mã/tên có giá trị và mã duy nhất; loại/tiêu thức thuộc lựa chọn; nhóm hoạt động khi chọn mới; mức ưu tiên là số nguyên hợp lệ; ngày kết thúc sau ngày bắt đầu. **Trường hợp không hợp lệ:** mã trùng dù khác nhóm, thiếu nhóm, loại/tiêu thức ngoài lựa chọn, số ưu tiên ngoài phạm vi, ngày kết thúc bằng ngày bắt đầu. Quy tắc lưu hợp lệ vẫn có thể bị chặn khi chạy nếu dùng driver chưa hỗ trợ hoặc thiếu kỳ.

Kiểm tra: nhóm đúng; tiêu thức có khả năng thực thi; mã được phương án tham chiếu đúng; kỳ/tiền tệ/công suất/đơn vị đầy đủ; không tính trùng cùng khoản trong nguồn lực và chi phí chung.

## 10. Phiên bản, trạng thái và hiệu lực theo ngày

| Nội dung | Hành vi thực tế |
| --- | --- |
| Phiên bản mới nhất | Bản có số phiên bản lớn nhất trên trang chi tiết/danh sách. Có thể là Nháp tương lai; không tự là bản dùng cho Run |
| Nháp (`DRAFT`), Chờ duyệt (`IN_REVIEW`) | BOM/bao bì/quy trình còn sửa cấu hình và dòng được. Chờ duyệt là tên trạng thái tương thích dữ liệu, không có quy trình duyệt trên UI |
| Đã duyệt (`APPROVED`), Đang hiệu lực (`EFFECTIVE`), Ngừng hiệu lực (`RETIRED`) | BOM/bao bì/quy trình và dòng chỉ đọc; tạo bản mới để thay đổi. Không có thao tác đổi các trạng thái này trong module |
| Ngày còn trống | Chưa đặt hiệu lực; được phép lưu phiên bản Nháp |
| Hiệu lực theo ngày | Chưa đặt hiệu lực / Sắp hiệu lực / Đang hiệu lực / Hết hiệu lực, tính từ ngày hôm nay; độc lập trạng thái bản ghi |
| Ngày kết thúc | Phải sau ngày bắt đầu, được tính bao gồm ngày ấy cho các nguồn sản xuất/Costing này. Khác quy ước kết thúc không bao gồm của Fee/Tax/FX Pricing |
| Đang hoạt động | Thuộc header, không thay thế trạng thái phiên bản |
| Sản phẩm trên header | BOM/Quy trình bị khóa khi có bản đã chốt; Bao bì bị khóa khi đã gán SKU hoặc có bản đã chốt. Mã/tên và trạng thái header vẫn sửa được |
| Tham chiếu ngừng hoạt động | Giữ tham chiếu đang gắn để xem/sửa lịch sử hoặc sao chép; không cho chọn một tham chiếu ngừng hoạt động khác. Engine còn kiểm tra nguồn hoạt động |
| Chồng khoảng ngày | Form chưa tự ngăn; engine báo thiếu/mơ hồ thay vì tự lấy bản mới nhất hoặc ưu tiên cao nhất |

Đặt ngày bắt đầu hôm nay có thể khiến badge **Hiệu lực theo ngày** hiển thị **Đang hiệu lực** trong khi **Trạng thái bản ghi** vẫn **Nháp**. Khi kiểm tra nguồn cho Run, phải đọc cả trạng thái, ngày, header hoạt động và tính duy nhất của nguồn. BOM và bao bì có nút **Kích hoạt phiên bản → Xác nhận kích hoạt** cho bản còn sửa được; không có bước gửi duyệt hay duyệt theo người dùng. Các nguồn sản xuất khác giữ giới hạn đã nêu ở mục 1.

## 11. Lỗi và cách xử lý tại chỗ

| Thông báo / hiện tượng | Nguyên nhân thực tế | Cách xử lý |
| --- | --- | --- |
| Mã … đã tồn tại | Mã được chuẩn hóa/trùng trong module | Tìm bản đã có; sửa bản đó nếu điều chỉnh; dùng mã khác cho bản ghi mới |
| Không thể chỉnh sửa phiên bản đã được chốt. Vui lòng tạo phiên bản mới. | BOM/bao bì/quy trình thuộc trạng thái bất biến | Mở phiên bản nguồn, chọn Tạo phiên bản mới từ phiên bản N |
| Vui lòng nhập ngày bắt đầu khi có ngày kết thúc hiệu lực. | Phiên bản có ngày kết thúc nhưng thiếu bắt đầu | Điền ngày bắt đầu hoặc xóa ngày kết thúc |
| Ngày kết thúc/Ngày hết hiệu lực phải sau ngày bắt đầu hiệu lực. | Kết thúc bằng/trước bắt đầu | Chỉnh ngày; không dùng một khoảng bắt đầu/kết thúc cùng ngày |
| Mã vật tư: không tìm thấy quy đổi đơn vị phù hợp tại ngày … | Đơn vị dòng khác đơn vị gốc và thiếu cặp quy đổi trực tiếp | Vào Quy đổi đơn vị; kiểm tra cặp, ngày, vật tư/phạm vi; lưu lại dòng hoặc bản sao |
| SKU phải thuộc sản phẩm của cấu hình bao bì. | Liên kết sai Sản phẩm | Chọn SKU cùng Sản phẩm; tạo cấu hình khác nếu cần |
| SKU đã được gán cấu hình này với cùng ngày bắt đầu. | Trùng đúng khóa liên kết | Sửa liên kết hiện có hoặc tạo kỳ khác |
| Thứ tự công đoạn đã tồn tại trong phiên bản này. | Trùng số thứ tự | Đổi số thứ tự, ví dụ 10/20/30 |
| Nguồn lực không thuộc trung tâm sản xuất đã chọn. | Máy/người thuộc trung tâm khác | Chọn đúng trung tâm hoặc nguồn lực chung/phù hợp |
| Vui lòng chọn đơn vị thời gian. | Có thời gian khác 0 nhưng chưa có đơn vị | Chọn phút/giờ thuộc đại lượng TIME |
| Danh mục không còn tồn tại hoặc dữ liệu không còn hợp lệ | Danh mục vừa bị đổi/ngừng hoặc dữ liệu thay đổi khi đang nhập | Tải lại form, kiểm tra danh mục, chọn lại và lưu |
| Run báo không tìm thấy định mức/phiên bản/đơn giá có hiệu lực | Thiếu nguồn, nguồn Nháp, ngoài ngày hoặc header ngừng hoạt động | Đối chiếu nguồn/ngày/trạng thái; xem giới hạn đưa vào hiệu lực ở mục 1 |
| Có nhiều … phù hợp / Có nhiều đơn giá nguồn lực | Nhiều nguồn hiệu lực cùng ngày; rate_type chưa giải quyết chọn giá | Kiểm tra và xử lý các khoảng trùng; không kỳ vọng hệ thống chọn bản mới nhất |
| `UNSUPPORTED_SUBSTITUTION` | BOM có dòng tùy chọn/nhóm thay thế | Chuẩn bị định mức xác định rõ thành phần theo khả năng hiện tại |
| `UNSUPPORTED_PACKAGING_CONDITION` | Dòng bao bì có thị trường/mẫu in | Run chưa có bộ chọn; chỉ dùng cấu hình không có điều kiện ấy cho nguồn hiện tại |
| `UNSUPPORTED_ALLOCATION_DRIVER` | Driver khác NORMAL_CAPACITY, có công thức/điều kiện | Kiểm tra phạm vi engine; không chỉ đổi tên tiêu thức để ép chạy |
| `MISSING_DENOMINATOR` / thiếu số liệu kỳ | Kỳ thiếu công suất dương/đơn vị, hoặc không có kỳ phù hợp | Số liệu kỳ chưa có UI; ghi nhận thiếu dữ liệu, dùng nguồn demo đã chuẩn bị cho bài học |

Tra cứu các lỗi Run đầy đủ và thứ tự kiểm tra tại [Lỗi thường gặp](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md). Không sửa trực tiếp bản đã chốt hay xóa lịch sử để xử lý lỗi.

## 12. Bảo trì và ảnh hưởng thay đổi

Hằng ngày, kiểm tra nguyên liệu/bao bì/nguồn lực mới có đơn vị, giá và ngày sử dụng rõ ràng; xác nhận thay đổi công thức hoặc quy cách thực tế đã được ghi thành bản mới. Trước một lần tính, kiểm tra đúng nguồn duy nhất tại ngày tính và trạng thái cần thiết. Hằng tuần/tháng, rà soát giá/rate sắp hết kỳ, liên kết SKU chính, các bản Nháp mới nhất chưa đủ điều kiện sử dụng, quy đổi cần cho kỳ sắp tới và các công đoạn thiếu cơ sở tính thời gian.

| Tôi thay đổi | Ảnh hưởng lần tính cũ đã lưu? | Ảnh hưởng lần tính mới? | Cách giữ lịch sử |
| --- | --- | --- | --- |
| BOM/bao bì/quy trình | Kết quả/trace/snapshot cũ không tự tính lại | Có nếu nguồn mới đủ trạng thái/ngày, được phương án dùng và không mơ hồ | Tạo phiên bản mới từ nguồn; giữ bản đã chốt |
| Liên kết SKU–bao bì | Lần tính cũ giữ snapshot liên kết đã chọn | Có thể chọn cấu hình khác hoặc báo thiếu/mơ hồ | Thêm kỳ mới, kiểm tra ngày cũ và tính duy nhất |
| Đơn giá nguồn lực | Kết quả và giá đã chụp trong lần tính cũ giữ nguyên | Có thể đổi chi phí hoặc gây mơ hồ tại ngày mới | Thêm bản ghi giá mới có ngày; tránh sửa đè giá cũ |
| Công suất Trung tâm/Nguồn lực | Không tự tính lại kết quả cũ | Không tự thay số liệu kỳ phân bổ hay thời gian; hoạt động/tham chiếu còn được kiểm tra | Ghi rõ lý do nghiệp vụ; không coi đây là lịch công suất |
| Nhóm chi phí/Quy tắc phân bổ | Snapshot cũ giữ nguyên | Có nếu nguồn ALLOCATION tham chiếu mã và đủ kỳ/đơn vị/trạng thái; ngừng nhóm có thể chặn | Quy tắc kỳ mới dùng mã khác, cập nhật phiên bản phương án nếu thay mã |

Khi cần đánh giá tác động, tạo **Lần tính giá thành** mới hoặc dùng thao tác tính lại tạo bản mới theo chương Costing; không kỳ vọng sửa nguồn sẽ đổi kết quả lịch sử. Sửa một header tên/mã có thể đổi thông tin danh mục hiện tại, nhưng snapshot nguồn của lần tính đã lưu vẫn là chứng cứ cho phép tính cũ.

## 13. Đường dẫn màn hình và bằng chứng source

`{id}` là mã nội bộ của bản ghi trong đường dẫn, không phải trường phải nhập. Tất cả đường dẫn dưới đây mở trong ứng dụng hiện tại.

| Mục | Danh sách | Tạo / sửa / chi tiết và thao tác bổ sung |
| --- | --- | --- |
| BOM | `/bom/` | `create/`, `{id}/`, `{id}/edit/`; `{id}/versions/`, `versions/create/`, `versions/{v}/`, `versions/{v}/edit/`; trong bản: `lines/create/`, `lines/{line}/edit/`, `lines/{line}/remove/` |
| Bao bì | `/bom/packaging/` | Tương tự BOM cho header/versions/lines; thêm `{id}/skus/`, `skus/create/`, `skus/{assignment}/edit/` |
| Trung tâm | `/bom/work-centers/` | `create/`, `{id}/`, `{id}/edit/` |
| Nguồn lực | `/bom/resources/` | `create/`, `{id}/`, `{id}/edit/`; lịch sử đơn giá ngay ở chi tiết |
| Đơn giá | `/bom/resource-rates/` | `create/`, `{id}/`, `{id}/edit/` |
| Quy trình | `/bom/routings/` | Header/versions như BOM; trong bản: `operations/create/`, `operations/{op}/edit/`, `operations/{op}/remove/` |
| Nhóm chi phí | `/bom/cost-pools/` | `create/`, `{id}/`, `{id}/edit/`; bảng quy tắc ở chi tiết |
| Quy tắc | `/bom/allocation-rules/` | `create/`, `{id}/`, `{id}/edit/` |

Các đường dẫn tương đối trong cột cuối nối tiếp base tương ứng; đường dẫn dòng/công đoạn nằm sau `{id}/versions/{v}/`. Endpoint tải lựa chọn nguồn lực trong Routing phục vụ dropdown, không phải một màn hình nghiệp vụ riêng.

| Nội dung đã đối chiếu | Nguồn chính |
| --- | --- |
| Nhãn menu và trạng thái/lựa chọn | [navigation.py](../../apps/master_data/navigation.py), [presentation.py](../../apps/master_data/presentation.py), các `*_constants.py` trong apps/bom |
| Trường BOM, đơn vị, thu hồi, hao hụt, khóa, sao chép | [forms.py](../../apps/bom/forms.py), [validators.py](../../apps/bom/validators.py), [services.py](../../apps/bom/services.py), [views.py](../../apps/bom/views.py), [tests.py](../../apps/bom/tests.py) |
| Bao bì, đo lường, dòng và liên kết SKU | [packaging_forms.py](../../apps/bom/packaging_forms.py), [packaging_validators.py](../../apps/bom/packaging_validators.py), [packaging_services.py](../../apps/bom/packaging_services.py), [packaging_views.py](../../apps/bom/packaging_views.py), [test_packaging.py](../../apps/bom/test_packaging.py) |
| Trung tâm, nguồn lực, đơn giá và sửa trực tiếp | [resource_forms.py](../../apps/bom/resource_forms.py), [resource_validators.py](../../apps/bom/resource_validators.py), [resource_services.py](../../apps/bom/resource_services.py), [resource_views.py](../../apps/bom/resource_views.py), [test_resources.py](../../apps/bom/test_resources.py) |
| Quy trình, cặp cơ sở, dropdown và công đoạn | [routing_forms.py](../../apps/bom/routing_forms.py), [routing_validators.py](../../apps/bom/routing_validators.py), [routing_services.py](../../apps/bom/routing_services.py), [routing_views.py](../../apps/bom/routing_views.py), [test_routing.py](../../apps/bom/test_routing.py) |
| Nhóm, quy tắc, lựa chọn và giữ trạng thái | [overhead_forms.py](../../apps/bom/overhead_forms.py), [overhead_validators.py](../../apps/bom/overhead_validators.py), [overhead_services.py](../../apps/bom/overhead_services.py), [test_overhead.py](../../apps/bom/test_overhead.py) |
| Kiểu, mặc định, quan hệ dữ liệu | [core/models.py](../../apps/core/models.py) |
| Ngày bao gồm kết thúc; chọn nguồn duy nhất | [definition_helpers.py](../../apps/bom/definition_helpers.py), các selectors trong apps/bom; [resolvers/common.py](../../apps/costing/engine/resolvers/common.py) |
| Phép nhân quy mô, điều kiện chưa hỗ trợ, thời gian và đơn giá | [resolvers/manufacturing.py](../../apps/costing/engine/resolvers/manufacturing.py), [resolvers/prices.py](../../apps/costing/engine/resolvers/prices.py) |
| Phạm vi phân bổ công suất bình thường | [resolvers/allocation.py](../../apps/costing/engine/resolvers/allocation.py), [registry.py](../../apps/costing/engine/registry.py) |
| Nút lưu, xác nhận ngừng, thao tác dòng | [form chung](../../templates/master_data/partials/reference_data_form_content.html), các templates [BOM](../../templates/bom/partials/detail_content.html), [bao bì](../../templates/bom/packaging/partials/detail_content.html), [quy trình](../../templates/bom/routing/partials/operation_form_content.html) |

Tài liệu triển khai cũ có câu “chưa tính Costing” mô tả thời điểm chỉ làm màn hình cấu hình; phạm vi thực thi hiện tại được xác nhận từ resolver bên trên. Từ 20/10/2026, BOM/bao bì có nút kích hoạt và kiểm tra chồng kỳ tại bước kích hoạt. Không suy rộng sang nguồn khác; UI nhập số liệu kỳ và nhân cây bao bì vẫn chưa có.
