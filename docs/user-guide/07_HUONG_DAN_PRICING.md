# 07. Hướng dẫn giá bán và so sánh kịch bản

**[HỆ THỐNG HIỆN TẠI]** Nhóm menu **GIÁ BÁN** gồm Kênh bán, Quy tắc phí kênh, Quy tắc thuế, Tỷ giá, Kịch bản giá bán và So sánh kịch bản. Chương này hướng dẫn theo đúng thứ tự cần chuẩn bị. [Tham chiếu từng trường](12_FIELD_REFERENCE.md) ghi đầy đủ giới hạn nhập.

## 1. Giá vốn nào được dùng?

Pricing lấy **giá thành đơn vị đã lưu** của một Lần tính giá thành có trạng thái **Đã khóa**. Nó không đọc lại giá mua hoặc chạy lại BOM. Một lần tính 10 hộp tổng 583.000 VND cung cấp giá vốn 58.300 VND cho **một hộp**.

Sản phẩm/SKU của kịch bản phải khớp nguồn giá thành. Bỏ trống SKU chỉ chọn được nguồn tính ở cấp Product, không dùng nguồn của một SKU bất kỳ. Đơn vị bán trong phép tính là **đơn vị đầu ra của Run**; phần mềm chưa tự đổi hộp sang thùng ở bước Pricing.

## 2. Kênh bán

**Dùng khi:** phân biệt bán trực tiếp, bán lẻ, B2B, thương mại điện tử, xuất khẩu hoặc kênh khác. Loại kênh giúp phân loại; nó không tự tải biểu phí của một nền tảng.

**Trước khi tạo:** nên có tiền tệ bán. Tiền tệ mặc định của kênh được để trống nếu chưa xác định.

**Thao tác:** **GIÁ BÁN → Kênh bán → + Thêm mới**. Nhập mã, tên, chọn loại. Nếu có, nhập mã nền tảng, thị trường, loại người bán và tiền tệ mặc định. Giữ **Đang hoạt động**, bấm **Lưu kênh bán**.

**Ví dụ hợp lệ:** mã `TRAIN_DIRECT`, tên `Bán trực tiếp đào tạo`, loại Bán trực tiếp (`D2C`), thị trường `VN`, tiền tệ VND. Mã tự trim/uppercase. Mã trùng hoặc bỏ loại kênh bị từ chối. Bỏ chọn hoạt động khi không muốn dùng cho kịch bản mới; lịch sử đã tính vẫn còn.

**Tìm/lọc:** mã, tên, nền tảng, thị trường; lọc trạng thái, loại và tiền tệ mặc định. Sắp xếp mã/tên/loại/ngày tạo. Sau khi lưu, chuyển sang Quy tắc phí kênh.

## 3. Quy tắc phí kênh

Phí là khoản trừ để bán được một đơn vị hàng. Một quy tắc có thể chứa **tỷ lệ**, **số tiền cố định**, hoặc cả hai. Không có lựa chọn loại phép tính tự ẩn trường; người dùng điền trực tiếp các trường hiện có.

**Thao tác:** **GIÁ BÁN → Quy tắc phí kênh → + Thêm mới**. Chọn kênh; nhập mã loại phí và mã cơ sở tính phí; điền số; chọn cách thể hiện thuế; nhập phạm vi và hiệu lực; chọn trạng thái rồi **Lưu quy tắc phí kênh**.

**[VÍ DỤ NGHIỆP VỤ]** Để thu phí hoa hồng 5%: mã loại `COMMISSION`, cơ sở `LIST_PRICE`, Tỷ lệ `5`, số tiền cố định để trống, Tỷ lệ được hoàn `0`, Thuế trong phí **Giá đã bao gồm thuế**, mức ưu tiên `100`. Để thêm phí thanh toán 1.000 VND: tạo **bản khác**, loại `PAYMENT_FEE`, cơ sở `LIST_PRICE`, tỷ lệ trống, tiền cố định `1000`, tiền tệ VND, tỷ lệ hoàn `0`, phí đã gồm thuế.

Mã loại phí là mã tự quy định. **Đổi tên loại phí không đổi thuật toán.** Cơ sở thực thi hiện chỉ hỗ trợ `LIST_PRICE`, nghĩa là giá khách trả đã gồm thuế. Các cơ sở khác có thể lưu cấu hình nhưng khi tính sẽ báo chưa hỗ trợ.

### Phạm vi và mức ưu tiên

Để trống Nhóm sản phẩm và SKU: áp dụng chung kênh. Chọn nhóm: áp dụng nhóm đó. Chọn SKU: áp dụng SKU. Nếu chọn cả nhóm và SKU, SKU phải thuộc nhóm.

Với **cùng mã loại phí**, hệ thống chọn phạm vi **SKU → nhóm → chung**, sau đó mức ưu tiên lớn hơn. Hòa cả phạm vi và ưu tiên thì lỗi, không chọn theo ngày tạo hay ID. Các **loại phí khác nhau** được cộng.

Ví dụ hai quy tắc COMMISSION chung 5%/ưu tiên 999 và riêng SKU 4%/ưu tiên 1: SKU được tính 4%. Thêm PAYMENT_FEE 1.000 thì vẫn trừ thêm 1.000. Không tạo hai COMMISSION chung cùng ưu tiên khi không muốn lỗi mơ hồ.

### Sàn/trần

```text
Phí thô = giá khách trả × tỷ lệ + tiền cố định
Phí áp dụng = phí thô, nâng đến sàn nếu thấp, hạ về trần nếu cao
```

Sàn/trần áp riêng từng quy tắc đã chọn. Trần phải ≥ sàn; các số tiền phải ≥ 0. Có tiền cố định/sàn/trần thì phải chọn tiền tệ. Một trong tỷ lệ/tiền cố định phải có; **0 là giá trị được nhập**, khác với bỏ trống cả hai.

### Điều kiện để bộ tính sử dụng

- Bản ghi **Đang hiệu lực**, ngày nằm trong khoảng áp dụng.
- `refundable_ratio` phải bằng 0 trong phạm vi thực thi hiện tại.
- Phí có giá trị phải được đánh dấu đã gồm thuế. Chưa có bộ xử lý thuế riêng trên phí.
- Tiền tệ khác tiền tệ bán cần tỷ giá đúng chiều và loại.

Form chấp nhận tỷ lệ được hoàn > 0 để lưu cấu hình; **Pricing chưa tính trường hợp đó**. Nếu có nhiều nguồn, mở **Nguồn và diễn giải đã lưu** để biết quy tắc nào thắng và quy tắc nào bị loại.

**Lọc/sắp xếp:** kênh/nhóm/SKU, loại/cơ sở phí, tiền tệ, trạng thái bản ghi, hiệu lực; sắp theo kênh, loại phí, tỷ lệ, ưu tiên, ngày bắt đầu hoặc ngày tạo.

## 4. Quy tắc thuế

Thuế bán hàng được cấu hình riêng với giá vốn. Các tỷ lệ minh họa trong tài liệu là giả định, không phải hướng dẫn thuế pháp lý.

**Thao tác:** **GIÁ BÁN → Quy tắc thuế → + Thêm mới**. Nhập mã khu vực, loại thuế, cơ sở thuế; điền tỷ lệ hoặc tiền cố định; chọn Thuế trong giá; điền phạm vi, hiệu lực, trạng thái; **Lưu quy tắc thuế**.

**[DEMO]** `VN`, `VAT`, `SELLING_PRICE`, Thuế suất `10`, tiền cố định trống, Tỷ lệ được khấu trừ `0`, **Giá đã bao gồm thuế**. Để trống nhóm thuế/người bán/giao dịch để áp dụng chung. Chọn Đang hiệu lực để bộ tính dùng.

Nếu giá khách trả 110 và thuế 10% thì giá trước thuế là 100, thuế 10; không lấy 110 × 10% = 11. Với nhiều loại thuế, tất cả dùng cùng giá trước thuế và cộng độc lập, không tính thuế chồng thuế. Cùng mã loại thuế chọn độ cụ thể theo số trường phạm vi được điền, rồi ưu tiên lớn nhất; hòa thì báo lỗi.

Các cơ sở thực thi: `SELLING_PRICE` hoặc `LIST_PRICE`, đều biểu diễn giá trước thuế chung của mô hình hiện tại. Tỷ lệ khấu trừ phải 0 khi tính Pricing. Có thể cấu hình thuế đã gồm **hoặc** chưa gồm trong giá niêm yết; chưa hỗ trợ trộn hai cách trong cùng kịch bản. Khi chưa gồm, giá niêm yết là trước thuế, giá khách trả gồm thuế; khi đã gồm, hai giá trùng nhau.

**Không tìm thấy thuế** trong chế độ áp dụng thuế là lỗi, không tự coi thuế bằng 0. Nếu bài toán không áp dụng thuế, người lập chọn rõ **Không áp dụng thuế** trên kịch bản.

**Lọc/sắp xếp:** khu vực, loại/nhóm thuế, người bán/giao dịch, tiền tệ, trạng thái, hiệu lực; sắp khu vực, loại thuế, tỷ lệ, ưu tiên, ngày bắt đầu/ngày tạo.

## 5. Tỷ giá

**Dùng khi:** giá vốn hoặc các khoản tiền của phí/thuế khác tiền tệ bán. Không cần FX khi mọi khoản cùng tiền tệ. Currency phải tồn tại trước.

**Thao tác:** **GIÁ BÁN → Tỷ giá → + Thêm mới**. Chọn tiền nguồn và đích; nhập tỷ giá, mã loại, thời điểm hiệu lực, nguồn; chọn trạng thái; **Lưu tỷ giá**.

**[VÍ DỤ NGHIỆP VỤ]** `VND → USD`, tỷ giá `0.00004`, loại `SPOT`: 1 VND = 0,00004 USD. Giá vốn 58.300 VND trở thành 2,332 USD. Đây là tỷ giá đào tạo tự đặt, không phải tỷ giá thị trường.

Pricing tra tại **00:00 ngày định giá, giờ Việt Nam**. Tỷ giá bắt đầu 09:00 cùng ngày chưa dùng cho ngày đó. Cần nguồn đã bắt đầu trước hoặc đúng 00:00 và chưa hết hiệu lực tại 00:00.

Chỉ tra **đúng chiều, đúng loại**. Có USD→VND không tự suy ra VND→USD. Không lấy bản mới nhất hoặc chuỗi qua tiền tệ trung gian. Thiếu thì lỗi; hai bản cùng phù hợp thì lỗi. Tỷ giá phải > 0 và tiền nguồn ≠ tiền đích.

**Lọc/sắp xếp:** loại tỷ giá, tiền nguồn/đích, trạng thái và hiệu lực; sắp nguồn/đích, tỷ giá, loại, thời điểm hiệu lực/ngày tạo. Thuế và phí số tiền cố định được đổi riêng nếu cần; phí % không đổi như một số tiền.

## 6. Hiệu lực và thay đổi chính sách

Phí/thuế dùng ngày, FX dùng thời điểm; các khoảng đều **[bắt đầu, kết thúc)**. Bản cũ kết thúc 01/11/2026 và bản mới bắt đầu 01/11/2026 thì ngày 01/11 chỉ dùng bản mới. Kết thúc phải sau bắt đầu.

Form mới mặc định **Nháp**. Có thể chọn **Đang hiệu lực** và lưu trực tiếp sau kiểm tra. Bản Nháp chỉnh sửa được; bản đã chốt chỉ xem, cần thêm bản mới cho kỳ mới.

Nếu bản đang hiệu lực chưa có mốc kết thúc, trang chi tiết có **Kết thúc hiệu lực**. Chỉ đặt được mốc **trong tương lai** và sau bắt đầu; không dùng thao tác này để sửa kỳ đã qua hoặc sửa lại mốc đã đặt. Nó giữ nguyên tỷ lệ/số tiền/phạm vi. Sau đó tạo quy tắc mới từ đúng mốc kết thúc. Không tự có quy tắc thay thế chỉ vì đóng bản cũ.

Các biểu mẫu không cấm mọi trường hợp chồng kỳ. Khi tính, nguồn đồng hạng hoặc FX trùng sẽ bị từ chối. Do đó người nhập phải kiểm tra lịch trước khi chốt.

## 7. Margin và markup

Đặt `P` = giá khách trả; `F` = tổng phí; `T` = thuế; `C` = giá vốn một đơn vị:

```text
Doanh thu thuần sau phí và thuế = P − F − T
Lợi nhuận = P − F − T − C
Biên lợi nhuận thực tế (margin) = lợi nhuận / P
Tỷ lệ cộng thực tế trên giá vốn (markup) = lợi nhuận / C
```

**Mẫu số margin của hệ thống là giá khách trả đã gồm thuế**, không phải doanh thu chưa thuế. Markup cũng dùng lợi nhuận **sau phí/thuế**, không chỉ lấy giá khách trả trừ giá vốn.

**[VÍ DỤ NGHIỆP VỤ]** Không phí/thuế, giá vốn 100: markup 20% cho giá 120, margin 20% cho giá 125. Khi có phí/thuế, không áp dụng trực tiếp hai con số này; bộ tính tìm giá đáp ứng mục tiêu sau tất cả khoản trừ.

Có ba phương pháp: **Biên lợi nhuận mục tiêu**, **Tỷ lệ cộng trên giá vốn**, **Lợi nhuận trên một đơn vị**. Chỉ nhập mục tiêu của phương pháp đã chọn. Margin cho phép từ −100% đến dưới 100%; markup ≥ −100%; mục tiêu lợi nhuận cố định có thể âm. Dùng giá trị âm chỉ cho phân tích chấp nhận lỗ có chủ đích.

## 8. Tạo và tính kịch bản giá bán

**Trước:** có nguồn Costing đã khóa và đúng Product/SKU; kênh và tiền tệ hoạt động; phí/thuế/FX cần thiết đã hiệu lực.

1. **GIÁ BÁN → Kịch bản giá bán → + Thêm kịch bản**.
2. Nhập mã riêng và tên dễ hiểu; chọn Sản phẩm.
3. Chọn SKU nếu dùng nguồn của SKU. Danh sách SKU và nguồn tự tải lại khi đổi Product/SKU. Chọn lại nguồn đúng sau khi đổi.
4. Chọn **Nguồn giá thành**: nhãn có ngày, giá vốn/đơn vị, phương án và số lần tính. Danh sách mặc định giới hạn 100 nguồn gần nhất; một nguồn cũ đã được chọn trong đúng phạm vi có thể được giữ.
5. Chọn kênh và ngày định giá. Tiền tệ/khu vực được gợi ý từ kênh nếu chưa nhập, vẫn sửa được trước khi tính.
6. Chọn Thuế bán hàng; nếu áp dụng, nhập mã khu vực. Nhập loại giao dịch nếu muốn khớp phạm vi thuế cụ thể. Nhập loại tỷ giá nếu cần đổi tiền tệ.
7. Chọn phương pháp, nhập đúng **một** mục tiêu; các mục tiêu còn lại để trống. Ví dụ margin nhập `20`, không nhập `0.2` để biểu diễn 20%.
8. Giá bán tối thiểu có thể bỏ trống. Nếu nhập lớn hơn giá giải ra, hệ thống nâng giá đến sàn và tính lại margin thực tế; sàn không phải ô nhập giá bán tùy ý.
9. Hiệu lực từ/đến của kịch bản là thông tin áp dụng của kịch bản; không thay **Ngày định giá** để tra phí/thuế/FX. Hai ngày này có thể bằng nhau; chỉ lỗi khi kết thúc trước bắt đầu.
10. Bấm **Lưu Nháp**. Bản ghi ở **Nháp**, chưa có giá bán.
11. Tại chi tiết, bấm **Tính giá bán**. Thành công chuyển **Đã tính**; lỗi giữ **Nháp** và hiện thông báo/mã tham chiếu.

**Hợp lệ:** cùng Product/SKU với nguồn, margin 20%, thuế/khu vực rõ, nguồn duy nhất tại ngày định giá. **Không hợp lệ:** bỏ nguồn, nhập cả margin và markup, chọn nguồn chưa khóa, thiếu FX, fee base chưa hỗ trợ hoặc mẫu số giá không dương.

Sau lỗi nguồn, sửa tại danh mục tương ứng, quay lại kịch bản Nháp và tính lại. Bản đã tính chỉ xem; dùng **Nhân bản thành kịch bản mới**, nhập mã mới và thay các đầu vào cần thử. Gọi tính lại trên bản Đã tính trả kết quả cũ, không cập nhật theo quy tắc hôm nay.

**Tìm/lọc/sắp xếp:** tìm mã/tên/sản phẩm/SKU đã lưu; lọc Product, SKU, kênh, tiền tệ, trạng thái, khoảng ngày định giá; sắp mã/tên/ngày định giá/giá khách trả/ngày tạo. Danh sách có 25/50/100 dòng, giữ điều kiện khi chuyển trang.

## 9. Đọc cấu thành giá bán và nguồn

Trang chi tiết gồm **Kết quả giá bán**, **Cấu thành giá bán**, và mục mở rộng **Nguồn và diễn giải đã lưu**.

**[DEMO]** Cho giá vốn 58.300 VND/hộp, phí 5% + 1.000, thuế giả định 10% và margin 20%:

| Dòng | Giá trị VND | Cách kiểm tra |
|---|---:|---|
| Giá khách trả | 89.972,41379310 | Giá giải ra, đã gồm thuế |
| Hoa hồng | −4.498,62068966 | 5% × giá khách trả |
| Phí thanh toán | −1.000 | Cố định cho một đơn vị đầu ra |
| Thuế | −8.179,31034483 | Giá khách trả / 1,1 × 10% |
| Doanh thu thuần sau phí và thuế | 76.294,48275861 | Giá − phí − thuế |
| Giá vốn | −58.300 | Giá thành đơn vị từ nguồn đã khóa |
| Lợi nhuận | 17.994,48275861 | Doanh thu thuần − giá vốn |

Margin = 17.994,48275861 / 89.972,41379310 ≈ 20%. Không cộng lại các dòng “Doanh thu thuần” và “Lợi nhuận” như khoản thu mới; đó là các kết quả trung gian/cuối của bảng.

Mở **Nguồn và diễn giải đã lưu** để kiểm tra ngày Costing, giá vốn gốc, ID nguồn, hiệu lực phí/thuế, cách áp sàn/trần và chiều FX. Giá trị hiển thị giới hạn số lẻ để đọc; bản chụp giữ dữ liệu trung gian. Kết quả tiền lưu 8 chữ số thập phân với HALF_EVEN; **chưa có làm tròn thương mại** lên 500/1.000 đồng.

## 10. So sánh kịch bản

**Dùng khi:** chọn giữa kênh, mục tiêu lợi nhuận hoặc thời điểm định giá cho cùng hàng và cùng cơ sở đơn vị. Màn hình chỉ đọc kết quả đã lưu, không chạy bộ tính.

1. Vào **GIÁ BÁN → So sánh kịch bản** (`/pricing/scenarios/compare/`).
2. Chọn **Sản phẩm** trước để tải danh sách; chọn SKU khi so sánh cấp SKU.
3. Lọc kênh/tiền tệ/ngày, tìm mã/tên; đánh dấu **2–5** kịch bản **Đã tính**. Có thể chuyển trang mà giữ lựa chọn.
4. Chọn **Kịch bản mốc**; bỏ trống dùng kịch bản đầu tiên đã chọn.
5. Bấm **So sánh kịch bản**. Đọc giá khách trả, phí, thuế, giá vốn, lợi nhuận và tỷ lệ cùng phần chênh lệch.
6. Muốn bỏ một lựa chọn, bấm **Bỏ chọn**; để xóa toàn bộ bộ lọc/lựa chọn, dùng **Đặt lại**.

Chỉ so sánh cùng SKU, hoặc cùng Product khi **tất cả** không có SKU; cùng đơn vị đầu ra và cơ sở giá. SKU khác nhau dù thuộc cùng Product vẫn bị từ chối. Kịch bản không có snapshot/hash hợp lệ không được chọn. Chênh tiền khác currency **không được trừ hay đổi tự động**; hệ thống chỉ hiển thị tiền gốc. Chênh margin dùng **điểm phần trăm**, ví dụ 25% − 20% = 5 điểm, không phải 5% tương đối. Mốc 0 không có tỷ lệ chênh tương đối, tránh chia cho 0.

Không có nhãn tự kết luận kịch bản nào luôn tốt nhất. Người dùng cân nhắc đồng thời mức giá, lợi nhuận và tính thực tế của kênh; phần mềm không dự báo nhu cầu hay sản lượng bán.

## 11. Bảo trì và xử lý tình huống

| Tôi muốn… | Thao tác | Tác động lịch sử |
|---|---|---|
| Phí/thuế kỳ sau đổi | Đóng kỳ tương lai nếu đủ điều kiện, thêm quy tắc mới, tránh hòa phạm vi/ưu tiên | Kịch bản đã tính không đổi |
| Tỷ giá đổi | Tạo cặp đúng chiều/loại và mốc mới không chồng nhau | Kịch bản đã tính giữ FX cũ |
| Margin từ 20 lên 25% | Nhân bản kịch bản, mã mới, mục tiêu 25, tính | Bản cũ giữ 20% |
| Giá nguyên liệu đổi | Tạo nguồn giá mua kỳ mới, chạy Costing mới, chọn nguồn đó cho Pricing mới | Pricing cũ vẫn giữ giá vốn cũ |
| Xem giá khuyến mại 80.000 có lãi bao nhiêu | [CHƯA HỖ TRỢ] Không có ô nhập giá bán cố định để tính ngược | Không dùng “giá tối thiểu” giả làm giá bán thấp hơn |

Hằng ngày kiểm tra tỷ giá/nguồn vừa cập nhật và các lỗi tính. Hằng tháng kiểm tra kỳ hiệu lực sắp hết, biểu phí thực tế của doanh nghiệp, các nguồn bị hòa và những cảnh báo “không có phí”. Đối chiếu kết quả mới với một ví dụ tính tay trước khi dùng ra quyết định.

Nguồn: [forms](../../apps/pricing/forms.py), [ScenarioForm](../../apps/pricing/scenario_forms.py), [validation](../../apps/pricing/scenario_validators.py), [selectors](../../apps/pricing/selectors.py), [resolver](../../apps/pricing/engine/resolvers.py), [solver](../../apps/pricing/engine/solver.py), [dịch vụ](../../apps/pricing/scenario_services.py), [UI kết quả](../../templates/pricing/scenarios/partials/detail_content.html), [so sánh](../../apps/pricing/comparison.py), [Golden](../../apps/pricing/test_scenario_solver.py).
