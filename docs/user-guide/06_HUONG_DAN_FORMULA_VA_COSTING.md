# Thiết lập công thức, phương án và lần tính giá thành

Tài liệu được đối chiếu source ngày 09/10/2026. Nhãn `[HỆ THỐNG HIỆN TẠI]` chỉ hành vi đã có; `[DEMO]` chỉ bộ mẫu Cappuccino; `[VÍ DỤ NGHIỆP VỤ]` chỉ cấu hình minh họa cần tạo riêng; `[CHƯA HỖ TRỢ]` chỉ giới hạn thực thi.

## 1. Ba màn hình có vai trò gì?

| Menu hiện tại | Dùng để làm gì? | Đường dẫn | Kết quả được dùng ở đâu? |
|---|---|---|---|
| CÔNG THỨC & QUY TẮC → Thiết lập công thức | Khai báo phép tính, kiểm tra kiểu dữ liệu, lưu dữ liệu kiểm thử và kích hoạt phiên bản | `/formula-engine/formulas/` | Gán phiên bản công thức vào dòng phương án |
| CÔNG THỨC & QUY TẮC → Phương án tính giá thành | Ghép nguyên liệu, bao bì, nguồn lực, phân bổ, dữ liệu nhập và công thức thành một bảng tính có phiên bản | `/costing/schemes/` | Người chạy chọn phương án phù hợp với sản phẩm/SKU |
| TỔNG QUAN → Lần tính giá thành | Tính một sản lượng tại một ngày, lưu kết quả và dữ liệu đã dùng | `/costing/runs/` | Xem giá thành, giải thích và làm giá vốn đầu vào cho kịch bản giá bán |

[HỆ THỐNG HIỆN TẠI] Công thức là quy tắc tính; phương án là cách nối dữ liệu với quy tắc; lần tính là một kết quả đã lưu. Tạo công thức không tự tạo lần tính. Kiểm tra phương án không kiểm tra sự tồn tại của mọi giá mua, đơn giá hoặc số liệu kỳ chi phí cho lần tính thực tế.

Đọc trước [danh mục](04_HUONG_DAN_DANH_MUC.md), [sản xuất](05_HUONG_DAN_SAN_XUAT.md) và tra từng ô ở [Field Reference](12_FIELD_REFERENCE.md). Bài thực hành đầy đủ ở [Cappuccino](09_THUC_HANH_CAPPUCCINO_END_TO_END.md).

## 2. Chuẩn bị dữ liệu trước khi thiết lập

1. Có Phần tử chi phí cho từng biến cần dùng. Khai báo đúng Loại giá trị, Tiền tệ, Đơn vị tính mặc định, Đại lượng và làm tròn. Mã phần tử là tên biến trong công thức.
2. Có Sản phẩm, và có SKU nếu cần tính bao bì. SKU có đơn vị bán, lượng tịnh và đơn vị lượng tịnh rõ ràng; lượng tịnh không mặc định là kg.
3. Chuẩn bị các nguồn mà phương án thực sự sử dụng: BOM, bao bì chính cho SKU, quy trình và nguồn lực, giá nhà cung cấp, đơn giá nguồn lực, quy đổi đơn vị, quy tắc phân bổ và số liệu kỳ.
4. Những nguồn được bộ máy chọn theo ngày phải có trạng thái `EFFECTIVE` phù hợp. Bản Nháp vừa tạo trong màn hình danh mục chưa đủ để chạy.

[CHƯA HỖ TRỢ] UI BOM/bao bì/quy trình/giá nhà cung cấp/đơn giá nguồn lực/quy tắc phân bổ hiện chưa có thao tác kích hoạt tương đương công thức và phương án; số liệu kỳ chi phí chung chưa có màn hình nhập. Vì vậy, một chuỗi nguồn mới hoàn toàn không thể tự hoàn thành chỉ bằng các nút hiện có. Bộ DEMO đã được chuẩn bị qua lệnh quản trị có kiểm tra. Người nhập liệu cần phối hợp với người phụ trách dữ liệu; không đổi trực tiếp trạng thái trong cơ sở dữ liệu theo tài liệu này.

## 3. Tạo và kiểm thử công thức

### 3.1 Tạo công thức đầu tiên

Vào **Thiết lập công thức** → **+ Thêm công thức**. Trang có tiêu đề **Thiết lập công thức**.

| Ô cần nhập | Cách hiểu và ví dụ |
|---|---|
| Mã công thức | Bắt buộc, tối đa 120 ký tự; bắt đầu bằng chữ cái, tiếp theo chỉ chữ cái ASCII, số hoặc `_`. Ví dụ `TOTAL_DIRECT`. Hệ thống chuẩn hóa mã mới thành chữ hoa; mã phải duy nhất. Không dùng `TRUE`, `FALSE`, `AND`, `OR`, `NOT`. |
| Tên công thức | Bắt buộc, tối đa 255 ký tự. Ví dụ `Tổng chi phí trực tiếp`. |
| Mô tả | Tùy chọn; ghi mục đích và quy ước nghiệp vụ. |
| Phần tử chi phí kết quả | Tùy chọn khi tạo. Nếu chọn, kiểu/tiền tệ/đơn vị kết quả phải khớp. Nếu bỏ trống, hệ thống suy ra từ biểu thức. |
| Đang hoạt động | Mặc định chọn. Công thức ngừng hoạt động không được kích hoạt/dùng làm nguồn hợp lệ. |
| Biểu thức | Bắt buộc. Ví dụ `$MATERIAL_TOTAL + $PACK_TOTAL + $RESOURCE_TOTAL`, sau khi đã tạo ba phần tử tương ứng. |
| Hiệu lực từ ngày | Có thể để trống khi lưu Nháp, bắt buộc trước khi kích hoạt. |
| Hiệu lực đến ngày | Tùy chọn. Nếu nhập, phải có ngày bắt đầu và ngày cuối phải sau ngày đầu. |
| Lý do thay đổi | Tùy chọn. Ví dụ `Áp dụng định nghĩa chi phí trực tiếp kỳ mới`. |

Nhấn **Kiểm tra công thức**. Danh sách **Biến dữ liệu** giúp tìm mã và chèn đúng cú pháp. Kiểm tra đạt sẽ hiện kiểu đầu ra và các phụ thuộc; các ô nhập mẫu được sinh theo những phần tử chi phí đầu vào cuối cùng. Nhập dữ liệu mẫu, chọn **Kiểm thử**, rồi **Lưu công thức** để tạo phiên bản Nháp. Kiểm thử trong trang soạn thảo là bước thử tính; bộ kiểm thử cần được lưu ở trang phiên bản sau đó.

Sau khi tạo, kiểm tra:

- [ ] Mã, tên và phần tử kết quả đúng nghiệp vụ.
- [ ] Tất cả mã trong biểu thức đã tồn tại và đang hoạt động.
- [ ] Kiểu, tiền tệ, đại lượng, đơn vị đầu ra đúng.
- [ ] Biểu thức đã lưu thuộc phiên bản Nháp mong muốn.
- [ ] Có ngày bắt đầu trước khi chuyển sang kích hoạt.

### 3.2 Lưu bộ kiểm thử và kích hoạt

Tại trang phiên bản, phần **Kiểm thử công thức** cho nhập:

| Ô | Cách nhập |
|---|---|
| Các biến có nhãn `Tên phần tử · MÃ` | Tất cả bắt buộc. Tiền/Số/Tỷ lệ/Số lượng dùng số; Có/Không chọn giá trị; Văn bản nhập chữ. Đơn vị và tiền tệ được hiển thị theo phần tử. Tỷ lệ nhập dạng thập phân, ví dụ `0.1` là 10%. |
| Kết quả mong đợi | Tùy chọn nếu chỉ thử tính; bắt buộc khi lưu bộ kiểm thử. Số lưu tối đa 24 chữ số, trong đó 8 chữ số thập phân. Văn bản rỗng hiện chưa thể lưu làm kết quả mong đợi. |
| Tên bộ kiểm thử | Tùy chọn nếu chỉ thử tính; bắt buộc khi chọn **Lưu bộ kiểm thử**, tối đa 255 ký tự. |

Chọn **Kiểm thử** để xem kết quả và diễn giải. Chọn **Lưu bộ kiểm thử** để lưu mẫu, rồi **Chạy bộ kiểm thử đã lưu** để đối chiếu các mẫu còn hoạt động. Bộ kiểm thử mới so sánh chính xác, sai số cho phép bằng 0; UI không có ô đặt sai số. Bộ cũ được chạy theo sai số đã lưu. **Ngừng sử dụng** bỏ mẫu khỏi nhóm đang hoạt động, không xóa bản ghi.

[DEMO] `DEMO_DIRECT_FORMULA` dùng ba đầu vào `260000`, `150000`, `120000`; kết quả mong đợi `530000`. `DEMO_FULL_FORMULA` dùng các đầu vào lá đó và `DEMO_OVERHEAD_COST=53000`; kết quả mong đợi `583000`. Đây là tổng cho 10 hộp, không phải giá một hộp.

Chọn **Kích hoạt phiên bản** → **Xác nhận kích hoạt**. Hệ thống kiểm tra lại biểu thức, kiểu, đơn vị và vòng phụ thuộc; cần công thức đang hoạt động, có ngày bắt đầu, đúng một phiên bản công thức phụ thuộc `EFFECTIVE` bao phủ ngày bắt đầu, ít nhất một bộ kiểm thử đang hoạt động và toàn bộ bộ kiểm thử đều đạt. Tối đa 200 bộ đang hoạt động. Trạng thái đã lưu là **Hợp lệ** không thay thế bước kiểm tra lại này.

Sau khi kích hoạt, phiên bản và cấu trúc phụ thuộc không sửa/xóa được. Muốn đổi biểu thức, chọn **Tạo phiên bản mới**, sửa bản Nháp rồi kiểm thử lại. Bộ kiểm thử gắn với công thức chung và được dùng lại cho phiên bản mới, không nhân đôi tự động. **Chỉnh sửa** thông tin công thức chỉ đổi tên, mô tả, tình trạng hoạt động; Mã công thức và Phần tử chi phí kết quả được giữ cố định.

### 3.3 Cú pháp đang hỗ trợ

| Thành phần | Cách viết | Lưu ý |
|---|---|---|
| Phần tử chi phí | `$MATERIAL_TOTAL` | Dùng mã của Phần tử chi phí |
| Công thức khác | `@TOTAL_DIRECT` | Dùng mã công thức, không phải mã dòng phương án |
| Mã không có tiền tố | `MATERIAL_TOTAL` | Chỉ hợp lệ nếu không trùng giữa phần tử và công thức; nên dùng `$`/`@` rõ ràng |
| Số | `1.05`, `0.1`, `100` | Dấu chấm thập phân; không viết `1,05`, dấu phân cách hàng nghìn hay dạng `1e3` trong biểu thức |
| Văn bản | `"Nội địa"`, `'Xuất khẩu'` | Phải đặt trong dấu nháy |
| Có/Không | `TRUE`, `FALSE` | Giá trị Boolean |
| Số học | `+ - * / %`, dấu ngoặc | `%` là số dư, không phải ký hiệu phần trăm |
| So sánh | `> >= < <= == !=` | Dùng `==` để so bằng; so sánh phải cùng kiểu/đơn vị phù hợp |
| Điều kiện | `AND OR NOT` | Không viết so sánh nối như `0 < X < 1`; viết hai điều kiện với `AND` |

| Hàm | Cách dùng hợp lệ | Điều kiện |
|---|---|---|
| `ROUND` | `ROUND($TOTAL_COST, 2)` | Hai tham số; số chữ số là hằng số nguyên 0–12; làm tròn HALF_UP |
| `MIN`, `MAX` | `MAX($COST_A, $COST_B)` | 2–20 số có kiểu/đơn vị tương thích |
| `ABS` | `ABS($DELTA_COST)` | Một giá trị số |
| `IF` | `IF($IS_EXPORT, $EXPORT_COST, $DOMESTIC_COST)` | Điều kiện Có/Không; hai nhánh cùng kiểu/đơn vị; chỉ tính nhánh được chọn |

Kiểu được lấy từ Phần tử chi phí, không đoán từ giá trị nhập. Có thể cộng hai tổng tiền VND; không cộng VND với USD, kg với g hoặc tổng tiền với số thường. Không tự đổi đơn vị trong công thức. Phép nhân chỉ hỗ trợ một đại lượng với một số/tỷ lệ không có đơn vị; chia hai đại lượng cùng đơn vị trả số thường. Chưa hỗ trợ phép nhân hai đại lượng có đơn vị hoặc phép chia tạo đơn vị mới.

Ví dụ `$TOTAL_COST * 1.05` hợp lệ khi `TOTAL_COST` là tiền. `$TOTAL_COST + 1000` không phải cách cộng phụ phí tiền: cần tạo phần tử tiền cho phụ phí rồi cộng hai biến tiền. `$OUTPUT_QTY > 100` cũng không hợp lệ nếu `OUTPUT_QTY` có kiểu Số lượng và đơn vị; cần ngưỡng có cùng kiểu/đơn vị, hoặc thiết kế đầu vào Số thường với quy ước rõ ràng. Cả nhánh `IF` không được chọn vẫn được kiểm tra kiểu và phụ thuộc.

[CHƯA HỖ TRỢ] `LOOKUP`, `SUM`, `AVG`, gọi Excel/Python, truy vấn bảng giá hay API từ biểu thức. Các mức giá phải được bộ lấy dữ liệu của lần tính cung cấp, hoặc người chạy nhập ở dòng Thủ công.

### 3.4 Bản mới nhất và bản đã dùng khác nhau

[HỆ THỐNG HIỆN TẠI] Danh sách và trang công thức mặc định mở **phiên bản mới nhất**. Khi thử tính một công thức, các công thức được tham chiếu được lấy theo bản mới nhất, kể cả Nháp; diễn giải cho biết phiên bản thực tế. Vì vậy, thử lại một biểu thức cũ có thể khác sau khi công thức phụ thuộc có bản mới.

Khi kích hoạt hoặc chạy Costing, phụ thuộc được kiểm tra theo ngày. Costing lưu phiên bản/biểu thức và dữ liệu thực tế đã dùng vào bản chụp. Muốn xem lại kết quả lịch sử, mở **Lần tính giá thành**, không dùng màn hình Kiểm thử để giả định đó là kết quả cũ.

## 4. Tạo phương án tính giá thành

### 4.1 Tạo thông tin và phiên bản

Vào **Phương án tính giá thành** → **+ Thêm phương án**. Nhập Mã phương án, Tên phương án, Mã mục đích, Mã phạm vi áp dụng; cả bốn bắt buộc. Mã tối đa 120 ký tự; tên 255; mục đích/phạm vi 100. Mã phạm vi mặc định `GENERAL`. Mô tả tùy chọn; Đang hoạt động mặc định chọn. Nhập ngày/lý do cho phiên bản đầu nếu đã xác định rồi **Lưu phương án tính giá thành**.

`purpose` và `context_scope` là mã nghiệp vụ tự quy định, không phải nút chọn phương pháp tính. `[DEMO]` dùng `STANDARD_COST` và `SKU`, nhưng phương án không tự gắn với SKU. Không có ô gán BOM, bao bì, quy trình, nhóm chi phí hoặc tiền tệ cơ sở ở thông tin phương án.

Trang phương án mặc định hiển thị phiên bản mới nhất. **Lịch sử phiên bản** mở từng bản; **Tạo phiên bản mới từ phiên bản N** sao chép toàn bộ dòng và giữ tham chiếu phiên bản công thức chính xác sang bản Nháp mới. Sau khi nhập ngày/lý do, chọn **Lưu phiên bản phương án**. Tạo phiên bản mới từ lịch sử mà không chọn nguồn không tự sao chép dòng. Sau khi có phiên bản chốt, mã/mục đích/phạm vi trên thông tin phương án bị cố định; tên, mô tả và Đang hoạt động vẫn là thông tin danh mục có thể sửa.

### 4.2 Thêm thành phần

Tại bản Nháp, chọn **+ Thêm thành phần**. Điền Mã dòng, Nhãn hiển thị, Loại dòng, Thứ tự hiển thị, Phần tử chi phí và Nguồn dữ liệu, cùng cấu hình còn lại; nhấn **Lưu thành phần**. Tham khảo đầy đủ giới hạn/default ở [Field Reference](12_FIELD_REFERENCE.md).

| Cấu hình | Cách dùng |
|---|---|
| Mã dòng | Bắt buộc, duy nhất trong phiên bản; được chuẩn hóa thành chữ hoa. Đây là mã dòng, chưa tự trở thành biến `$...` nếu không gán Phần tử chi phí. |
| Nhãn hiển thị | Bắt buộc; xuất hiện ở bảng kết quả/ô nhập thủ công. |
| Loại dòng | `INPUT` Dữ liệu đầu vào, `CALCULATION` Tính toán, `SUBTOTAL` Tổng phụ, `OUTPUT` Đầu ra, `INFO` Thông tin. Loại dòng không tự quyết định nguồn hoặc phép tính. |
| Thứ tự hiển thị | Bắt buộc, số nguyên và duy nhất trong phiên bản; gợi ý tăng 10. Thứ tự tính được quyết định bởi quan hệ phụ thuộc. |
| Phần tử chi phí | Tùy chọn trên form tổng quát; cần có cho nguồn SYSTEM và dòng đầu ra tổng tiền. Dòng không gán phần tử không cung cấp biến cho công thức khác. |
| Nguồn dữ liệu | Hệ thống, Nhập thủ công, Tra cứu, Công thức, Nguồn bên ngoài. Các nguồn được hỗ trợ thực thi là Hệ thống/Nhập thủ công/Công thức. |
| Phạm vi chi phí | Khi chạy hiện tại chỉ chấp nhận `MANUFACTURING` hoặc `ANALYTICS`. Dòng OUTPUT tổng tiền phải `MANUFACTURING`. |
| Phạm vi hiển thị | Lưu lựa chọn `INTERNAL/SCREEN/QUOTE/REPORT/ALL`; màn hình kết quả hiện tại không dùng ô này để ẩn từng dòng. |
| Số chữ số làm tròn | Trống: dùng cấu hình Phần tử chi phí; nhập số nguyên 0–12: ghi đè số chữ số của dòng. Phương pháp làm tròn vẫn lấy từ phần tử. Không có phần tử thì mặc định 8 chữ số/HALF_EVEN. |
| Chính sách điều chỉnh | Cho phép điều chỉnh giá trị, tối thiểu/tối đa, Điều chỉnh cần lý do được lưu trong định nghĩa. Giới hạn tối thiểu/tối đa được dùng cho input MANUAL; chưa có thao tác điều chỉnh kết quả đã khóa hay ô lý do điều chỉnh khi chạy. |

Không có unique theo Phần tử chi phí trên mọi dòng; tuy nhiên nếu một công thức cần biến mà có nhiều dòng cùng cung cấp biến ấy, kiểm tra sẽ báo nhiều nguồn và ngăn kích hoạt.

| Nguồn dữ liệu | Ô nguồn xuất hiện | Hành vi hiện tại |
|---|---|---|
| `SYSTEM` | Mã bộ lấy dữ liệu hệ thống | Nhập đúng mã đã đăng ký trong bảng kế tiếp |
| `MANUAL` | Không có ô tham chiếu nguồn | Sinh ô nhập theo dòng ở form Chạy tính giá; bắt buộc người chạy nhập |
| `FORMULA` | Phiên bản công thức | Chọn đúng phiên bản đã kích hoạt/Hợp lệ, phù hợp phần tử và ngày phương án |
| `LOOKUP` | Bảng quy tắc | Có thể lưu cấu hình Nháp có tham chiếu; chưa kích hoạt/chạy được |
| `EXTERNAL` | Mã kết nối dữ liệu bên ngoài | Có thể lưu cấu hình Nháp có mã; chưa kích hoạt/chạy được |

Đổi Nguồn dữ liệu hoặc Phần tử chi phí làm mới ô nguồn và danh sách công thức. Khi lưu, hệ thống chỉ giữ tham chiếu tương ứng nguồn đã chọn. Bảng quy tắc không phải Quy tắc phân bổ; phân bổ dùng mã `ALLOCATION:...`, không chọn ở ô Bảng quy tắc.

### 4.3 Mã nguồn hệ thống thực sự có

| Mã chính xác | Kiểu phần tử cần có | Nguồn được dùng |
|---|---|---|
| `MATERIAL_COST` | Tiền, cùng tiền tệ Run, không có Đơn vị tính mặc định | Tổng tiền từ BOM hiệu lực của Product và giá mua |
| `PACKAGING_COST` | Như trên | Bao bì chính hiệu lực của SKU, phiên bản bao bì và giá mua; cần cơ sở đóng gói người chạy nhập |
| `RESOURCE_COST` | Như trên | Tổng thời gian dùng nguồn lực chính ở các công đoạn × đơn giá hiệu lực |
| `RUN_QUANTITY` | Số lượng, có đơn vị mặc định phù hợp | Sản lượng đầu ra quy đổi sang đơn vị phần tử; không trả tiền |
| `ALLOCATION:<mã quy tắc>` | Tiền, không có Đơn vị tính mặc định | `NORMAL_CAPACITY` với nhóm chi phí/số liệu kỳ đầy đủ; ví dụ `ALLOCATION:DEMO_OVERHEAD_NORMAL` |

[HỆ THỐNG HIỆN TẠI] Không có mã riêng `MACHINE_COST`, `LABOR_COST`, `SHIPPING_COST`, `FX_RATE` hoặc `TAX`. Máy/nhân công được xem trong diễn giải `RESOURCE_COST`. Mã đúng tên một Phần tử chi phí không tự trở thành mã bộ lấy dữ liệu.

### 4.4 Kiểm tra và kích hoạt phương án

Chọn **Kiểm tra cấu hình** để xem lỗi, lưu ý, bảng phụ thuộc và thứ tự tính. Mỗi biến đầu vào cuối cùng của các công thức phải được đúng một dòng cung cấp; không có vòng giữa dòng công thức và dòng cung cấp biến. Thứ tự hiển thị không sửa được lỗi phụ thuộc.

Khi kiểm tra cấu hình, ngày dùng là ngày bắt đầu phương án, hoặc hôm nay nếu Nháp chưa có ngày. Phiên bản công thức gán cụ thể và các công thức phụ thuộc phải có hiệu lực tại ngày đó. Nếu công thức có ngày cuối trước thời hạn phương án thì kiểm tra cấu hình yêu cầu thu hẹp thời hạn. Khi chạy Run, hệ thống kiểm tra theo đúng ngày Run; không yêu cầu công thức còn hiệu lực sau ngày ấy.

Chọn **Kích hoạt phiên bản** → **Xác nhận kích hoạt**. Cần ngày bắt đầu, phương án hoạt động, kiểm tra cấu hình không lỗi. Kích hoạt tạo mã băm cấu hình và chuyển `EFFECTIVE`; không tính giá/rate và không tạo lần tính. Phiên bản `APPROVED/EFFECTIVE/RETIRED` và các dòng là bất biến; sửa qua bản Nháp mới. Không có nút chuyển bản đã chốt sang nghỉ dùng.

Trước khi chạy, kiểm tra:

- [ ] Có đúng một phiên bản phương án EFFECTIVE cho ngày chạy.
- [ ] Có đúng một dòng OUTPUT, kiểu Tiền, không đơn vị, phạm vi MANUFACTURING.
- [ ] Tất cả dòng nằm trong MANUFACTURING/ANALYTICS nếu dự kiến thực thi ngay.
- [ ] Mỗi công thức có đủ nguồn biến và không trùng nguồn.
- [ ] SYSTEM dùng đúng mã; không còn LOOKUP/EXTERNAL/điều kiện nâng cao.
- [ ] Đơn vị/tiền tệ/làm tròn phù hợp với các nguồn thực tế.

Lưu ý: một số điều kiện đặc thù Run, như đúng một OUTPUT hoặc phạm vi được thực thi, chỉ được kiểm tra khi chạy. **Kiểm tra cấu hình** đạt chưa bảo đảm lần tính thành công.

## 5. Chạy tính giá thành

### 5.1 Thao tác và dữ liệu nhập

Vào **TỔNG QUAN → Lần tính giá thành** → **+ Chạy tính giá**.

| Ô trên form | Bắt buộc/default | Cách nhập |
|---|---|---|
| Sản phẩm | Có | Chọn sản phẩm đang hoạt động, ví dụ `DEMO_CAPPUCCINO` |
| Ngày tính giá | Có; mặc định hôm nay | Dùng ngày nghiệp vụ muốn chọn nguồn, ví dụ 07/10/2026 |
| Sản lượng cần tính | Có; mặc định 1 | Số dương, tối đa 24 chữ số/8 số thập phân; ví dụ 10 |
| Đơn vị sản lượng | Có | Đơn vị đang hoạt động, ví dụ Hộp (`DEMO_BOX_UOM`) |
| Tiền tệ kết quả | Có | Ví dụ VND; nguồn tiền phải tương thích vì Costing chưa có FX |
| Loại lần tính | Có; mặc định Giá thành chuẩn | Giá thành chuẩn (`STANDARD`) hoặc Giá thành kế hoạch (`PLANNED`); cùng bộ máy nguồn/thuật toán hiện tại, chưa là actual consumption |
| SKU | Tùy chọn chung; cần khi phương án tính bao bì | Danh sách theo sản phẩm; ví dụ `DEMO_CAPPUCCINO_BOX20` |
| Phương án tính giá thành | Có | Chọn thủ công; danh sách có phiên bản hiệu lực theo ngày, không tự gán theo SKU |
| Sản lượng cơ sở đóng gói | Hiện và bắt buộc khi có PACKAGING_COST | Sản lượng mà các dòng bao bì đáp ứng; `[DEMO]` nhập 1 |
| Đơn vị cơ sở đóng gói | Cùng điều kiện | `[DEMO]` Hộp; không nhầm với số lượng sachet |
| Các ô Dữ liệu đầu vào thủ công | Mỗi dòng MANUAL là bắt buộc | Nhãn có tên dòng và mã; nhập đúng kiểu/giới hạn. Tỷ lệ là số thập phân. Không có giá trị mặc định từ dòng SYSTEM cũ |
| Ghi chú | Không; tối đa 3.000 ký tự | Ghi mục đích, căn cứ input hoặc kịch bản |

Chọn lại Sản phẩm/Ngày tính giá/Phương án khi thay điều kiện để các ô phụ thuộc được cập nhật. Nếu thấy **Phương án chưa có đúng một phiên bản hiệu lực tại ngày tính giá**, cần xử lý phiên bản thiếu/trùng trước khi chạy. Sau đó nhấn **Chạy tính giá**; màn hình hiển thị **Đang tính giá thành…**.

[HỆ THỐNG HIỆN TẠI] Các dòng MANUAL được hỏi dù ô Cho phép điều chỉnh giá trị trong định nghĩa đang bỏ chọn. Đây là nguồn đầu vào, không phải sửa giá đã tính. Nếu muốn thay giá trị SYSTEM bằng nhập tay, phải tạo phương án/bản Nháp mới có nguồn MANUAL phù hợp, kích hoạt rồi tạo Run mới; không sửa kết quả Run đã khóa.

### 5.2 Bộ máy chọn nguồn và tính lượng ra sao?

| Bước | Quy tắc hiện tại | Nguyên nhân thường gây lỗi |
|---|---|---|
| Chọn phương án/BOM/bao bì/quy trình | Đúng một nguồn EFFECTIVE tại ngày Run, thông tin danh mục hoạt động | Có bản Nháp nhưng chưa có nguồn hiệu lực; hai nguồn cùng hiệu lực |
| Sản lượng theo SKU | Chuyển Run sang đơn vị bán; khi cần đại lượng lượng tịnh, lấy số đơn vị bán × net_quantity rồi quy đổi. Đơn vị cùng đại lượng bán được đổi trực tiếp, không đi vòng qua kg | Sai lượng tịnh/đơn vị bán hoặc thiếu quy đổi |
| Nguyên liệu | `qty dòng × hệ số sản lượng / yield_rate / (1 − scrap_rate)`; hệ số = đầu ra cần tính / output_qty BOM | Yield phải >0 và ≤1, scrap ≥0 và <1; tùy chọn/thay thế chưa có quy tắc chọn |
| Bao bì | `qty dòng × (Run theo đơn vị cơ sở / sản lượng cơ sở)` | Thiếu SKU/assignment chính/cơ sở; market/artwork condition chưa hỗ trợ |
| Nguồn lực | `setup_time + run_time × hệ số sản lượng` | Thời gian khác0 thiếu nguồn lực/đơn vị TIME; nguồn lực không đúng trung tâm |
| Cơ sở thời gian chạy | Ưu tiên quantity_basis/quantity_uom công đoạn; nếu quantity_basis trống dùng batch_size/batch_uom phiên bản | Không mặc định cơ sở=1; công đoạn chỉ setup không cần cơ sở cho run_time=0 |
| Giá mua | Lọc ngày/trạng thái/nhà cung cấp hoạt động, đổi lượng mỗi dòng sang đơn vị giá, kiểm tra min_qty; cần đúng một giá cùng tiền tệ | Không tự chọn rẻ nhất, mới nhất, nhà cung cấp ưu tiên hoặc bậc số lượng cao nhất |
| Đơn giá nguồn lực | Cần đúng một rate hiệu lực theo nguồn lực/ngày; đổi lượng thời gian theo đơn vị rate | Nhiều rate_type cùng hiệu lực vẫn là mơ hồ |
| Quy đổi | Cùng đơn vị giữ lượng; khác đơn vị dùng đúng một quy đổi trực tiếp hoặc nghịch đảo hiệu lực | Không nối chuỗi, không ưu tiên theo vật tư khi cùng có quy đổi chung, không tự chia60/1000 |
| Phân bổ | `amount kỳ × sản lượng theo capacity_uom / normal_capacity` | Chỉ NORMAL_CAPACITY; cần kỳ EFFECTIVE, normal_capacity>0, đơn vị/tiền tệ đúng; vượt công suất bị chặn |
| Công thức/tổng | Tính theo phụ thuộc, làm tròn từng ranh giới dòng; lấy đúng dòng OUTPUT | Không cộng lại mọi INPUT/SUBTOTAL/OUTPUT |

Bao bì có cấp/cấp cha/số đơn vị mỗi cấp cha để mô tả, nhưng bộ máy không tự nhân thêm cây cấp. Ví dụ `[DEMO]` các dòng đã là 20 sachet +1 hộp giấy trên cơ sở1 hộp; Run10 hộp cần200 sachet+10 hộp giấy, không nhân20 lần nữa.

Giá mua có `tax_inclusive=True` hoặc `tax_rate` khác0 bị chặn vì chưa có xử lý thuế mua hàng. Giá/rate/chi phí chung khác tiền tệ Run bị chặn vì Costing chưa có FX. Có quy tắc FX/thuế ở module Giá bán không tự giải quyết các lỗi này.

Ngày cuối của các nguồn Costing là **bao gồm ngày đó**: nguồn từ01/10 đến31/10 dùng được ngày31/10; nguồn mới bắt đầu01/11 được dùng từ01/11. Để tránh chồng lấn, không đặt nguồn cũ kết thúc01/11 nếu nguồn mới bắt đầu01/11. Quy tắc ngày của Pricing khác; xem [hướng dẫn Pricing](07_HUONG_DAN_PRICING.md).

### 5.3 Trạng thái thực tế

| Trạng thái | Người dùng gặp thế nào? | Thao tác tiếp theo |
|---|---|---|
| `DRAFT` Nháp | Trạng thái khởi tạo nội bộ khi lưu Run | UI không có Lưu Nháp hoặc mở lại để sửa Run |
| `CALCULATED` Đã tính | Bước nội bộ sau khi lưu kết quả thành công | Tự chuyển LOCKED trong cùng lần thực thi; UI không có nút khóa riêng |
| `LOCKED` Đã khóa | Kết quả thành công, bất biến | Xem kết quả/diễn giải/dữ liệu; tạo lần tính mới khi muốn thay đổi |
| `FAILED` Thất bại | Lỗi trong khi thực thi sau khi Run đã được tạo; có thông báo và mã tham chiếu | Sửa nguồn/cấu hình thích hợp, chọn Tạo lần tính mới |

Các mã `IN_REVIEW`, `APPROVED`, `SUPERSEDED` còn trong dữ liệu/ô lọc tương thích nhưng không có luồng chuyển các trạng thái ấy trong UI này. Không có trạng thái `RUNNING` hoặc `COMPLETED`. Nếu form sai hoặc không chọn được phiên bản phương án, hệ thống báo tại form và có thể chưa tạo Run. FAILED không giữ các dòng/kết quả/bản chụp thành công nửa chừng.

## 6. Đọc kết quả, diễn giải và lịch sử

Trang **Kết quả tính giá thành** hiện sản phẩm/SKU/phương án/phiên bản, ngày, sản lượng, trạng thái, tổng và giá thành trên đơn vị sản lượng. Giá thành trên đơn vị = tổng / sản lượng nhập; đơn vị là đơn vị Run, không mặc định chiếc hay kg. Giá trị này được làm tròn khi hiển thị theo số chữ số tiền tệ đã lưu.

Bảng dòng chứa thành phần, tổng phụ và đầu ra. Tổng phụ/đầu ra có thể đã bao gồm các dòng trước; không cộng cả cột để ra tổng mới. Tỷ trọng mỗi dòng là tỷ lệ với tổng, nên tỷ trọng của tất cả dòng không bắt buộc cộng100%.

Chọn **Nguồn dữ liệu / Diễn giải** ở dòng để xem lượng cơ sở, hệ số sản lượng, yield/scrap, quy đổi, nhà cung cấp/đơn giá/hiệu lực, công thức, đầu vào, bước làm tròn. Với nguồn lực, đây là nơi tách chi phí máy và nhân công. Chọn **Xem dữ liệu và phiên bản đã sử dụng** để xem bảng nguồn/phiên bản và biểu thức thực tế đã lưu. Mã tham chiếu ở phần thông tin lần tính giúp người hỗ trợ tìm lỗi kỹ thuật.

**Snapshot** là bản chụp dữ liệu đã dùng tại thời điểm tính, gồm giá/rate/phiên bản/quy đổi/biểu thức, không chỉ liên kết tới danh mục hiện tại. **Trace/diễn giải** là các bước tạo ra giá trị. **Mã băm** giúp nhận diện nội dung bản chụp; UI snapshot hiện bảng nghiệp vụ và biểu thức, không có ô sửa/nhập hash.

[HỆ THỐNG HIỆN TẠI] Mở Run cũ chỉ đọc kết quả, diễn giải và snapshot đã lưu; không chọn lại giá hoặc tính lại. Thay tên master/giá/BOM/công thức không sửa Run cũ. Danh sách cũng tìm theo tên đã lưu trong Run, nên đổi tên sản phẩm hiện tại không viết lại nhãn lịch sử.

**Tạo lần tính mới** mở form **Chạy lại bằng dữ liệu hiện tại**, điền lại yêu cầu gốc và input MANUAL còn khớp mã dòng. Người chạy xem lại ngày/sản lượng/phương án/cơ sở rồi **Chạy tính giá**. Hệ thống tạo record/key mới, chọn lại nguồn hiện tại theo ngày được chọn, liên kết Run gốc và giữ nguyên Run gốc. Đây không phải phát lại ngoại tuyến snapshot; nguồn đã sửa có thể ảnh hưởng Run mới kể cả khi giữ ngày cũ.

| Thay đổi | Run đã khóa | Run mới |
|---|---|---|
| Giá nhà cung cấp/đơn giá nguồn lực | Giữ giá đã dùng | Chọn lại đúng ngày; thay đổi/mơ hồ có thể đổi kết quả hoặc gây lỗi |
| BOM/bao bì/quy trình | Giữ phiên bản/dòng đã dùng | Dùng nguồn EFFECTIVE duy nhất theo ngày |
| Formula | Giữ biểu thức/phiên bản đã dùng | Công thức gốc theo FK của phương án; công thức lồng theo ngày; có thể phải sửa phương án để chọn bản gốc mới |
| Scheme | Giữ phiên bản đã dùng | Chọn đúng một phiên bản EFFECTIVE cho ngày; nhiều bản cùng ngày gây lỗi |
| Input thủ công | Giữ giá trị gốc và diễn giải | Nhập/xác nhận lại trên form mới |

Lọc danh sách bằng Sản phẩm, SKU, Phương án, Trạng thái, Từ ngày/Đến ngày, tìm mã/tên đã lưu; chọn **Lọc** hoặc **Đặt lại**. Khoảng ngày Run bao gồm cả hai ngày nhập. Sắp xếp theo Ngày tính giá, Ngày tạo, Giá thành hoặc Mã lần tính; chọn25/50/100 dòng mỗi trang.

## 7. Đối chiếu nhanh Cappuccino

[DEMO] Run10 hộp ngày07/10/2026, VND, `DEMO_COSTING_SCHEME`, SKU `DEMO_CAPPUCCINO_BOX20`, cơ sở đóng gói1 Hộp.

| Thành phần | Tính tay độc lập | Kết quả VND |
|---|---|---:|
| Cà phê + đường | `200g×10/1000×100000 + 300g×10/1000×20000` | 260.000 |
| Bao bì | `20×10×500 + 1×10×5000` | 150.000 |
| Máy | `3phút×10/60×120000` | 60.000 |
| Nhân công | `6phút×10/60×60000` | 60.000 |
| Trực tiếp | `260000+150000+60000+60000` | 530.000 |
| Chi phí chung | `530000×10/100` | 53.000 |
| Tổng | `530000+53000` | **583.000** |
| Một hộp | `583000/10` | **58.300** |

Ngày01/11/2026: cà phê120.000/kg, máy144.000/giờ, nhân công72.000/giờ; nguyên liệu300.000, nguồn lực144.000, bao bì150.000, phân bổ53.000 → tổng647.000 và64.700/hộp. Run07/10 cũ vẫn583.000. Có bản Nháp2 mới nhất trên các cấu trúc mẫu nhưng Run chọn bản hiệu lực1.

Golden60.000 VND trong test kỹ thuật Costing Run là fixture khác (40.000 nguyên liệu +5.000 bao bì +10.000 nguồn lực +5.000 chung). Không dùng con số ấy thay cho bài DEMO Cappuccino. Kết quả đối soát đã thực thi trước đây được ghi ở [COSTING_DEMO_AUDIT](../COSTING_DEMO_AUDIT.md); bộ tài liệu này đối chiếu source, không tự seed/chạy lại dữ liệu thật.

## 8. Chi phí khác, vận chuyển và giới hạn cấu hình

[VÍ DỤ NGHIỆP VỤ] Nếu kế toán xác định một khoản vận chuyển vật tư thuộc chi phí sản xuất cần tính, có thể tạo phần tử MONEY/VND không UoM cho **tổng cước đã xác định**, tạo dòng MANUAL tương ứng trong phương án mới và cộng biến tiền vào công thức OUTPUT. Ví dụ `$BASE_MANUFACTURING_COST + $INBOUND_FREIGHT_TOTAL`. Khi chạy, nhập tổng cước và căn cứ trong Ghi chú; tổng/trace lưu input đó. Phải tự xác định khoản cước thuộc đúng phạm vi và tránh cộng lại khoản đã nằm trong giá nguyên liệu.

Cấu hình này cần phần tử mới, công thức có test đạt, phiên bản phương án mới và ngày hiệu lực không mơ hồ. Cước cố định trên một đơn vị phải được quy ra tổng cho sản lượng Run trước khi nhập nếu chưa thiết kế được công thức phù hợp. Nếu lưu trọng lượng/quãng đường như Số thường để nhân với một biến tiền, người thiết lập phải tự quy định và kiểm soát đơn vị trong tên/mô tả: bộ máy không xác minh được tấn/km trong các số thường đó.

[CHƯA HỖ TRỢ] Chưa có danh mục hãng vận chuyển/tuyến/cước, chứng từ vận chuyển, khối lượng tính cước, pallet/ngày, tự phân bổ chuyến hàng, giá landed hoặc cost-to-serve thực thi. Dòng `LANDED/COST_TO_SERVE/CHANNEL/PRICING` có thể tồn tại trong định nghĩa nhưng Run hiện tại chặn. Không hướng dẫn chọn những phạm vi ấy để chạy cước. Phí kênh bán là luồng Pricing riêng, không đưa vào sản xuất mặc định.

Tương tự, điện/nước có thể nhập tổng tiền hợp lệ như MANUAL hoặc đưa vào NORMAL_CAPACITY khi đủ số liệu kỳ đã chuẩn bị; chưa có bộ lấy số điện/kWh hoặc phí theo bậc điện. Khai báo được Phần tử chi phí/nguồn trong form không có nghĩa đã có bộ máy thực thi tương ứng.

## 9. Khi không chạy được, kiểm tra theo thứ tự

1. **Phương án:** hoạt động, đúng một bản EFFECTIVE tại ngày; kiểm tra cấu hình; đúng một OUTPUT MONEY/MANUFACTURING; không nguồn hoặc phạm vi chưa hỗ trợ.
2. **BOM:** đúng Product, đúng một bản hiệu lực, lượng đầu ra/yield/scrap hợp lệ; không thành phần tùy chọn/thay thế chưa có bộ chọn.
3. **Bao bì:** chọn SKU, assignment chính hiệu lực duy nhất, có bản hiệu lực, cơ sở đóng gói dương đúng đơn vị.
4. **Giá nhà cung cấp:** đúng Item/ngày/đơn vị/tiền tệ, min_qty đáp ứng; duy nhất; không giá có thuế chưa hỗ trợ.
5. **Quy đổi đơn vị:** đúng cặp trực tiếp hoặc nghịch đảo, đúng ngày và vật tư nếu cần; không trùng chung/riêng hoặc hai chiều.
6. **Quy trình/nguồn lực:** đúng Product, thời gian và cơ sở; nguồn lực/WorkCenter phù hợp.
7. **Đơn giá nguồn lực:** đúng một rate hiệu lực theo ngày, đơn vị/tiền tệ phù hợp; không chọn rate_type tự động.
8. **Công thức:** phiên bản gốc phù hợp ngày, phụ thuộc hiệu lực, đủ biến, kiểu/đơn vị tương thích, không chia0.
9. **Phân bổ:** NORMAL_CAPACITY, một kỳ EFFECTIVE, amount/currency/capacity_uom rõ ràng, công suất dương, Run không vượt công suất.
10. **Thủ công/làm tròn:** đủ mọi dòng MANUAL, đúng kiểu/giới hạn; giá trị sau làm tròn nằm trong độ chính xác lưu trữ.

Không sửa Run FAILED để thử lại. Đọc thông báo, sửa nguồn/cấu hình ở nơi thích hợp rồi **Tạo lần tính mới**. Danh mục có bản chốt cần tạo phiên bản mới theo quy tắc của module. Danh sách mã lỗi và cây quyết định chi tiết ở [Lỗi thường gặp](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md).

## 10. Phụ lục kỹ thuật và nguồn đối chiếu

- Formula/Scheme: `DRAFT`, `IN_REVIEW` sửa được; `APPROVED`, `EFFECTIVE`, `RETIRED` bất biến. Validation Formula: `NOT_VALIDATED`, `VALID`, `INVALID`. Không có nút chọn trạng thái trên form phiên bản.
- Source modes lưu: `SYSTEM/MANUAL/LOOKUP/FORMULA/EXTERNAL`; line types: `INPUT/CALCULATION/SUBTOTAL/OUTPUT/INFO`. Run mở `STANDARD/PLANNED`.
- Biểu thức Formula tính Decimal với precision38. `ROUND` bên trong biểu thức là HALF_UP; Costing còn làm tròn tại ranh giới dòng theo scale dòng hoặc phần tử/mode phần tử. Kết quả tiền/số/số lượng lưu8 số thập phân; tỷ lệ lưu10; vượt lưu trữ được báo lỗi, không tự cắt.
- Mỗi form Run có khóa UUID ẩn chống gửi trùng. Gửi cùng khóa/cùng yêu cầu trả cùng Run; sửa yêu cầu nhưng dùng lại khóa cũ có thể báo lỗi cần mở form mới. Người dùng không nhập khóa này.
- Snapshot giữ nguồn, phiên bản, biểu thức/AST/mã băm/phụ thuộc/thứ tự; context giữ ngày, sản lượng, cơ sở, manual và ghi chú. Chưa có replay snapshot ngoại tuyến.
- Giới hạn mặc định: biểu thức8.000 ký tự, AST512 nút/độ sâu40, đồ thị200 nút/độ sâu40,50.000 bước tính, trace1.000 dòng. Đồ thị/phép tính quá lớn cần đơn giản hóa; diễn giải có thể được rút gọn có thông báo.

Đã đối chiếu [forms Formula](../../apps/formula_engine/forms.py), [views/services Formula](../../apps/formula_engine/services.py), [hàm](../../apps/formula_engine/functions.py), [kiểu/đơn vị](../../apps/formula_engine/validator.py), [forms phương án](../../apps/costing/forms.py), [kiểm tra cấu hình](../../apps/costing/configuration.py), [form Run](../../apps/costing/run_forms.py), [lưu Run](../../apps/costing/run_services.py), [registry](../../apps/costing/engine/registry.py), [bộ máy](../../apps/costing/engine/runner.py), [resolvers sản xuất](../../apps/costing/engine/resolvers/manufacturing.py), [giá/rate](../../apps/costing/engine/resolvers/prices.py), [quy đổi](../../apps/costing/engine/resolvers/uom.py), [phân bổ](../../apps/costing/engine/resolvers/allocation.py), [DEMO](../../apps/costing/demo_data.py) và [test tích hợp Run](../../apps/costing/test_run_integration.py). Nhãn thao tác đã đối chiếu templates Formula/Costing và navigation hiện tại.
