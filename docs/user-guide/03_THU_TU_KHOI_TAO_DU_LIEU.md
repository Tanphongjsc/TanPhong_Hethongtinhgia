# Thứ tự khởi tạo dữ liệu

[Mục lục](README.md) · [Ma trận phụ thuộc đầy đủ](13_DEPENDENCY_MATRIX.md) · [Tra cứu trường](12_FIELD_REFERENCE.md)

**[HỆ THỐNG HIỆN TẠI]** Thứ tự dưới đây dựa trên form, dịch vụ lưu và bộ chọn nguồn hiện có, đối chiếu 09/10/2026. “Tạo được bản ghi” và “đủ nguồn để tính” là hai mốc khác nhau. Nhập đúng thứ tự giúp tránh danh sách lựa chọn trống, liên kết sai đơn vị và nguồn không đủ điều kiện theo ngày.

**Giới hạn từ database rỗng:** giao diện chưa cung cấp mọi bước để tự khởi tạo toàn bộ hệ thống và đưa nguồn mới vào tính giá. Nhóm phần tử chi phí có dropdown nhưng chưa có màn hình quản lý; nhóm này **tùy chọn**, có thể để trống. BOM và bao bì có thao tác **Kích hoạt phiên bản → Xác nhận kích hoạt** ở trang chi tiết phiên bản. Giá nhà cung cấp có **Kích hoạt giá → Xác nhận kích hoạt** ở trang chi tiết. Phiên bản quy trình, đơn giá nguồn lực và quy tắc phân bổ mới lưu Nháp vẫn chưa có thao tác đưa vào hiệu lực. Số liệu kỳ chi phí chung và lịch công suất chưa có UI. Người vận hành bắt đầu khi ứng dụng và ngữ cảnh dữ liệu đã được người phụ trách hệ thống chuẩn bị; không có bước tự tạo bằng menu đăng nhập/công ty trong hướng dẫn này. Dùng [bài thực hành DEMO](09_THUC_HANH_CAPPUCCINO_END_TO_END.md) để học chuỗi tính trên nguồn đã chuẩn bị hợp lệ; không coi lệnh chuẩn bị demo hay sửa database là bước UI.

## 1. Bản đồ thứ tự LEVEL 0–8

| Level | Tạo gì? | Vì sao cần trước? | Module dùng sau | Nếu thiếu |
| --- | --- | --- | --- | --- |
| **LEVEL 0 — Nền tảng** | Tiền tệ; Nhóm đơn vị tính; Đơn vị tính | Tiền phải có currency; lượng và thời gian phải có đơn vị đúng đại lượng | Phần tử chi phí, Item, Product/SKU, giá, sản xuất, Run/Pricing | Thiếu lựa chọn tiền/đơn vị; số đo hoặc phép tính không hợp lệ |
| **LEVEL 1 — Master Data** | Phần tử chi phí; Nhóm sản phẩm; Vật tư / Hàng hóa; Nhà cung cấp; quy đổi chung/riêng sau khi có đơn vị/Item | Xác định biến chi phí và vật tư mua/sản xuất | Formula, giá mua, Product/SKU, BOM/bao bì | Không chọn được vật tư/biến/nhà cung cấp; thiếu quy đổi |
| **LEVEL 2 — Product/SKU** | Sản phẩm; SKU nếu cần quy cách bán/bao bì | BOM/Routing thuộc Sản phẩm; bao bì chính chọn theo SKU | Sản xuất, Run, Pricing/Compare | Không gắn cấu hình; tính bao bì thiếu SKU |
| **LEVEL 3 — Procurement Price** | Giá nhà cung cấp theo Item, tiền tệ, đơn vị, kỳ/ngưỡng | Vật tư có quantity chưa đủ để tính tiền | MATERIAL_COST, PACKAGING_COST | Thiếu giá, nhiều giá phù hợp hoặc giá không đủ trạng thái |
| **LEVEL 4 — Manufacturing** | BOM; bao bì/phiên bản/dòng/gán SKU; trung tâm→nguồn lực→đơn giá; quy trình/công đoạn; nhóm chi phí→quy tắc | Mô tả cấu trúc lượng, thời gian và phân bổ | Các nguồn SYSTEM của Run | Thiếu định mức/bao bì/quy trình/rate; thiếu cơ sở hoặc số liệu kỳ |
| **LEVEL 5 — Cost Configuration** | Công thức và mẫu kiểm thử; phương án/phiên bản/dòng; kích hoạt hợp lệ | Nối các biến với nguồn và công thức rõ ràng | Lần tính giá thành | Không có phương án hiệu lực; thiếu biến; vòng phụ thuộc; nguồn chưa hỗ trợ |
| **LEVEL 6 — Costing** | Lần tính giá thành cho một ngày/sản lượng/đơn vị/tiền tệ | Tạo giá vốn đơn vị đã lưu và nguồn/trace | Pricing Scenario | Không có giá vốn đã khóa để chọn |
| **LEVEL 7 — Pricing** | Kênh; phí/thuế/FX cần thiết; Kịch bản giá bán | Nối giá vốn với chính sách bán và mục tiêu lợi nhuận | Kết quả giá bán, So sánh kịch bản | Thiếu kênh/thuế/FX; mục tiêu sai; nguồn chưa tính |
| **LEVEL 8 — Analysis** | Chọn 2–5 kịch bản đã tính để so sánh | So sánh kết quả trên cùng cơ sở | Quyết định phương án bán | Không đủ kịch bản hoặc khác SKU/cơ sở đơn vị |

Đây là thứ tự đào tạo, không phải mọi hàng ở level trước đều là điều kiện bắt buộc của level sau. Có thể tạo Nhà cung cấp trước Item; tạo Product chỉ cần đơn vị tính giá thành, không bắt buộc Item đầu ra; tạo công thức không cần Product/SKU. Kênh, thuế và FX có thể chuẩn bị sớm độc lập với Run. Chỉ chuẩn bị các nhánh nguồn mà phương án thực sự dùng; phương án chỉ dùng đầu vào thủ công không bắt buộc có BOM/bao bì/Routing.

## 2. LEVEL 0 — Nền tảng

1. Vào **DỮ LIỆU DANH MỤC → Tiền tệ**, tạo các tiền tệ thực sự dùng, ví dụ VND và USD. Thống nhất số chữ số thập phân hiển thị; tạo USD không tự tạo tỷ giá.
2. Tạo **Nhóm đơn vị tính** với đại lượng phù hợp như khối lượng, thời gian, số lượng, chiều dài. Sau đó tạo **Đơn vị tính** trong nhóm, ví dụ kg/g, giờ/phút, hộp/cái. Mã đơn vị là mã của doanh nghiệp, không bắt buộc giống ví dụ.
3. Kiểm tra trạng thái hoạt động của tiền tệ, nhóm và đơn vị. Đơn vị kg thuộc khối lượng; phút thuộc thời gian. Không chọn kg cho thời gian công đoạn.

Sau level 0:

- [ ] Có tiền tệ dùng cho giá mua, giá nguồn lực, Run và giá bán.
- [ ] Có đơn vị nguyên liệu, sản lượng, đóng gói và thời gian cần dùng.
- [ ] Mỗi đơn vị thuộc đúng nhóm/đại lượng; tên/ký hiệu rõ ràng.
- [ ] Hiểu rằng đơn vị khác nhau chưa tự quy đổi được; bước quy đổi thực hiện riêng.

## 3. LEVEL 1 — Danh mục nghiệp vụ

1. Tạo **Phần tử chi phí** cho các biến cần dùng trong công thức/phương án. Chọn đúng loại giá trị: Tiền tệ cần tiền tệ; Số lượng cần đơn vị. Nhóm phần tử chi phí tùy chọn; thiếu nhóm không phải lý do dừng bài nhập. Phần tử chi phí chỉ định nghĩa biến, không tự lấy giá mua hay nguồn lực.
2. Tạo **Nhóm sản phẩm** nếu cần phân loại hoặc áp phí theo nhóm. Nhóm của Item và nhóm của Product được chọn riêng; không tự truyền từ Item sang Product.
3. Tạo **Vật tư / Hàng hóa** cho nguyên liệu và bao bì: mã/tên/loại, **Đơn vị cơ sở** bắt buộc. Đơn vị mua/sản xuất, nhóm và số đo chỉ nhập khi có. Vật tư Bao bì không tự có cấu hình bao bì hoặc giá mua.
4. Tạo **Nhà cung cấp**. Tiền tệ mặc định có thể trống; tạo nhà cung cấp không cần Item trước.
5. Tạo **Quy đổi đơn vị tính** cho những cặp trực tiếp cần dùng. Quy đổi chung sau khi có hai đơn vị; quy đổi riêng theo vật tư sau khi có Item. Khác nhóm đại lượng cần quy đổi riêng theo Item và căn cứ nghiệp vụ rõ. Không tạo đồng thời nhiều cặp chung/riêng/ngược chiều cùng hiệu lực nếu khiến engine có nhiều lựa chọn.

**[VÍ DỤ NGHIỆP VỤ]** Cà phê có đơn vị gốc kg, dòng BOM dùng g và báo giá mua dùng kg. Cần cặp g↔kg hợp lệ ngày dùng; việc kg và g cùng nhóm khối lượng không tự sinh hệ số 1.000. Kiểm tra chiều và hệ số thật trước khi lưu.

Sau level 1:

- [ ] Mã phần tử chi phí đúng với tên biến sẽ dùng; loại/đơn vị/tiền tệ nhất quán.
- [ ] Nguyên liệu/bao bì có Item riêng, đúng loại và đơn vị cơ sở.
- [ ] Nhà cung cấp đã có, hoạt động.
- [ ] Có đúng cặp quy đổi cần thiết; ngày và phạm vi đúng; không kỳ vọng quy đổi qua nhiều bước.

## 4. LEVEL 2 — Sản phẩm và SKU

1. Tạo **Sản phẩm** với mã/tên, **Đơn vị tính giá thành**. Nhóm sản phẩm và Vật tư / Hàng hóa đầu ra có thể trống. Chỉ tạo Item đầu ra trước nếu muốn gắn liên kết này.
2. Tạo **SKU** nếu muốn tính quy cách bán và bao bì. Chọn Sản phẩm; **Đơn vị bán**, **Lượng tịnh** > 0, **Đơn vị lượng tịnh** bắt buộc. Item bán tùy chọn; chỉ cần tạo Item ấy trước nếu sử dụng liên kết.
3. Kiểm tra lượng tịnh biểu diễn đúng lượng cho **một đơn vị bán**. Ví dụ một hộp 20 gói có tổng lượng 0,5 kg: lượng tịnh của hộp là 0,5 kg, không phải 20 gói hay lượng của một gói. Đây là ví dụ quy ước lượng; không tự suy từ tên SKU.

Sau level 2:

- [ ] Product có đơn vị tính giá thành đúng.
- [ ] SKU thuộc đúng Product và có đơn vị bán/lượng tịnh/đơn vị lượng tịnh.
- [ ] Quy đổi từ đơn vị Run sang đơn vị bán/lượng tịnh/đầu ra dự kiến đã có khi cần.
- [ ] Biết BOM và Routing gắn Product; không có gán BOM/Routing riêng theo SKU.

## 5. LEVEL 3 — Giá mua

Vào **Giá nhà cung cấp**; chọn Nhà cung cấp, Item, Đơn vị tính giá và Tiền tệ; nhập Đơn giá không âm, Số lượng tối thiểu, thông tin thuế/nguồn và ngày hiệu lực theo form. Tạo giá từng nguyên liệu và vật tư bao bì cần cho nguồn SYSTEM.

Một giá tồn tại chưa đủ. Khi tính cần đúng một giá hiệu lực phù hợp ngày, vật tư, lượng/ngưỡng và tiền tệ, nhà cung cấp hoạt động; nếu khác đơn vị cần quy đổi. Bộ chọn không tự chọn rẻ nhất, mới nhất hoặc supplier ưu tiên. Các metadata thuế có thể lưu, nhưng Costing hiện chặn xử lý thuế mua chưa hỗ trợ; không xóa thuế thực tế để ép bài toán chạy. FX của Pricing không đổi giá mua sang tiền tệ Run.

**[HỆ THỐNG HIỆN TẠI — 20/10/2026]** Sau khi lưu giá Nháp, mở **Xem chi tiết → Kích hoạt giá → Xác nhận kích hoạt**. Kiểm tra trạng thái bản ghi **Đang hiệu lực** và khoảng ngày phù hợp ngày tính. Kích hoạt từng giá nguyên liệu và bao bì cần dùng; không chỉ giá của dòng đầu tiên. Nếu báo lỗi, sửa đúng dữ liệu rồi thử lại. Nguồn khác như thuế, quy đổi, tiền tệ và tính duy nhất vẫn cần đáp ứng điều kiện của bộ tính.

Sau level 3:

- [ ] Mọi Item sẽ được tính có giá, đơn vị, tiền tệ và ngưỡng hợp lý.
- [ ] Đúng một giá phù hợp ngày dự kiến; trạng thái bản ghi được kiểm tra riêng với badge theo ngày.
- [ ] Có quy đổi trực tiếp khi đơn vị lượng và đơn vị giá khác nhau.
- [ ] Đã nhận diện giá Nháp/thuế/ngoại tệ chưa được engine xử lý.

## 6. LEVEL 4 — Cấu hình sản xuất

Thực hiện các nhánh cần cho phương án, theo [hướng dẫn sản xuất](05_HUONG_DAN_SAN_XUAT.md):

1. **BOM / Công thức sản xuất:** tạo header và phiên bản đầu; khai báo sản lượng/đơn vị/thu hồi; thêm nguyên liệu với quantity/UoM/hao hụt. Dòng có tùy chọn/nhóm thay thế lưu được nhưng chưa được tính.
2. **Cấu hình bao bì:** tạo header/phiên bản/dòng; gán SKU cùng Sản phẩm và đánh dấu cấu hình chính phù hợp ngày. Ghi rõ các lượng dòng đáp ứng **bao nhiêu đơn vị đóng gói** để nhập cơ sở này vào Run. Không có trường sản lượng chuẩn trên PackagingVersion; cấp cha không tự nhân lượng.
3. **Trung tâm sản xuất → Nguồn lực → Đơn giá nguồn lực:** trung tâm có thể bỏ qua khi nguồn lực dùng chung; đơn giá cần nguồn lực, tiền, đơn vị tính giá. Giá thời gian phải quy đổi được với đơn vị công đoạn.
4. **Quy trình sản xuất:** tạo header/phiên bản; khai báo lô nếu cần; thêm công đoạn theo thứ tự, thời gian, trung tâm, nguồn lực chính và cơ sở. Công đoạn có thời gian khác 0 cần nguồn lực chính và TIME UoM để tính; thời gian chạy cần cơ sở công đoạn hoặc cơ sở lô.
5. **Nhóm chi phí chung → Quy tắc phân bổ:** chỉ dùng nguồn phân bổ `NORMAL_CAPACITY` trong phạm vi thực thi hiện tại. Cần số liệu kỳ chi phí chung có tiền/công suất/đơn vị hợp lệ. Nhóm chi phí không tự cộng các Phần tử chi phí vào số tiền kỳ.

**[HỆ THỐNG HIỆN TẠI — 20/10/2026]** Sau khi nhập đủ thành phần và ngày áp dụng, mở chi tiết phiên bản BOM và bao bì, chọn **Kích hoạt phiên bản → Xác nhận kích hoạt**. Bản được kích hoạt không sửa trực tiếp; muốn đổi cần tạo phiên bản mới. **[CHƯA HỖ TRỢ]** Phiên bản quy trình, Rate và Rule mới vẫn Nháp, chưa có nút hiệu lực. `CostPoolPeriod` có model nhưng chưa có form nhập kỳ. Lịch công suất (`CapacityCalendar`) chưa có module/form hoặc mapping model trong source đã kiểm tra; công suất trên WorkCenter/Resource không tự tạo số liệu kỳ hoặc lịch. Không nhập hoặc tìm các nút chưa tồn tại.

Sau level 4:

- [ ] BOM đúng Product/cơ sở; đủ dòng bắt buộc, thu hồi/hao hụt và đơn vị.
- [ ] SKU có một liên kết bao bì chính phù hợp; lượng dòng dùng cùng cơ sở rõ ràng.
- [ ] Quy trình có thời gian/nguồn lực/đơn vị/cơ sở đầy đủ; không nhầm setup với runtime.
- [ ] Nguồn lực dùng có đúng một đơn giá hiệu lực cùng tiền tệ Run.
- [ ] Phân bổ có nguồn kỳ thực sự; không lấy công suất header thay kỳ.
- [ ] Hiểu giới hạn hiệu lực của nguồn mới; không coi ngày hôm nay là trạng thái EFFECTIVE.

## 7. LEVEL 5 — Công thức và phương án

1. Vào **Thiết lập công thức**, tạo biểu thức từ các Phần tử chi phí đã có. Nếu tham chiếu công thức khác, chuẩn bị và kích hoạt công thức phụ thuộc trước. Không bắt buộc có Formula khi phương án chỉ cần các nguồn trực tiếp hợp lệ.
2. **Kiểm tra công thức**, nhập mẫu **Kiểm thử** và **Lưu bộ kiểm thử** đúng kết quả mong đợi; ít nhất một mẫu đang hoạt động và tất cả đạt trước khi **Kích hoạt phiên bản → Xác nhận kích hoạt**. Ngày bắt đầu cần có; kiểm tra kiểu/đơn vị và vòng phụ thuộc.
3. Tạo **Phương án tính giá thành** và các dòng nguồn. Gán phần tử và nguồn SYSTEM đã đăng ký, đầu vào MANUAL hoặc đúng FormulaVersion hiệu lực. Mỗi biến lá cần một nguồn cung cấp; dòng hiển thị thứ tự không thay quan hệ phụ thuộc tính toán.
4. **Kiểm tra cấu hình** rồi **Kích hoạt phiên bản** theo [chương Costing](06_HUONG_DAN_FORMULA_VA_COSTING.md). Không dùng LOOKUP/EXTERNAL hoặc mã SYSTEM tự đặt. Phương án không tự được gán cho Product/SKU; người chạy phải chọn.

Sau level 5:

- [ ] Công thức có mẫu đúng, kiểu/tiền/đơn vị đúng, các phụ thuộc hiệu lực.
- [ ] Phương án đủ nguồn cho các biến, không vòng phụ thuộc; nguồn nằm trong phạm vi hỗ trợ.
- [ ] Có đúng một phiên bản phương án hiệu lực ở ngày chạy dự kiến.
- [ ] Đã kiểm tra riêng dữ liệu mua/sản xuất: kiểm tra phương án không bảo đảm có mọi giá/rate/kỳ ở ngày Run.

## 8. LEVEL 6 — Tạo kết quả giá thành

Vào **Lần tính giá thành**, tạo lần tính với **Sản phẩm**, **SKU** khi cần, **Ngày tính giá**, **Phương án tính giá thành**, **Sản lượng cần tính**, **Đơn vị sản lượng**, **Tiền tệ kết quả**. Chọn Product sẽ tải SKU; đổi ngày có thể đổi phương án hiệu lực và các trường nhập. Khi chọn phương án, các đầu vào MANUAL được sinh theo các dòng nguồn; có `PACKAGING_COST` thì hai trường cơ sở đóng gói bắt buộc.

**Kiểm tra trước khi tính:** đúng một SchemeVersion, đúng nguồn SYSTEM cần dùng, nguồn hoạt động/hiệu lực, giá/rate/quy đổi duy nhất, cơ sở đóng gói đầy đủ, lượng và đơn vị rõ, đầu vào thủ công đủ. Công thức/Phương án có thể kích hoạt bằng UI, BOM/bao bì và giá mua có thao tác kích hoạt riêng ở chi tiết. Các nguồn quy trình/đơn giá nguồn lực/quy tắc phân bổ mới vẫn giữ giới hạn hiệu lực đã nêu ở trên.

Khi thành công, kiểm tra tổng và giá thành một đơn vị, trace vật tư/bao bì/nguồn lực/phân bổ. Kết quả được lưu và khóa theo hành vi Run hiện tại; Pricing chỉ chọn nguồn **Đã khóa** có kết quả hợp lệ. Khi thất bại, đọc thông báo nguồn thiếu/mơ hồ, sửa nguyên nhân và tạo/tính lại theo thao tác tạo bản mới; không ghi đè Run lịch sử.

Sau level 6:

- [ ] Kết quả tổng và đơn vị hợp lý so với tính tay.
- [ ] Nguồn/phiên bản/ngày/quantity được trace đúng.
- [ ] Có Run Đã khóa cùng Product/SKU, đơn vị và tiền tệ mong muốn cho Pricing.

## 9. LEVEL 7 — Chính sách và kết quả giá bán

1. Tạo **Kênh bán**; tiền tệ mặc định có thể trống. Loại kênh/nền tảng không tự tải biểu phí.
2. Tạo **Quy tắc phí kênh** nếu có phí. Chọn kênh; nhóm/SKU chỉ khi cần phạm vi; nhập tỷ lệ/tiền cố định, sàn/trần nếu cần. Tiền cố định/sàn/trần cần tiền tệ. Cơ sở thực thi `LIST_PRICE`, phí có giá trị đã gồm thuế, tỷ lệ hoàn 0. Không có phí phù hợp thì có cảnh báo, không tự phát minh phí.
3. Tạo **Quy tắc thuế** nếu kịch bản áp thuế. Khu vực/loại/cơ sở là mã; tỷ lệ/tiền cố định; phạm vi nếu có. Chuẩn bị nguồn hợp lệ cùng quy ước bao gồm hoặc chưa gồm thuế; không trộn hai cách. Nếu nghiệp vụ không áp thuế, chọn rõ **Không áp dụng thuế** ở Scenario.
4. Tạo **Tỷ giá** khi giá vốn hoặc tiền cố định phí/thuế khác tiền bán: đúng chiều, loại, thời điểm. Thời điểm tra là 00:00 ngày định giá giờ Việt Nam; FX bắt đầu 09:00 cùng ngày chưa dùng cho ngày ấy.
5. Phí/thuế/FX có trường **Trạng thái**: chọn **Đang hiệu lực** và lưu sau khi kiểm tra. Bản đã chốt chỉ đọc; **Kết thúc hiệu lực** chỉ đặt mốc tương lai nếu bản EFFECTIVE chưa có kết thúc. Cơ chế này có trong Pricing, khác thiếu thao tác hiệu lực ở nguồn giá mua/sản xuất.
6. Tạo **Kịch bản giá bán**: chọn Sản phẩm→SKU→**Nguồn giá thành** cùng phạm vi; kênh/ngày/tiền bán; thuế/FX rõ ràng; chọn một phương pháp và nhập đúng một mục tiêu. **Lưu kịch bản** rồi **Tính giá bán**. Lỗi giữ Nháp; thành công Đã tính.

Sau level 7:

- [ ] Giá vốn lấy đúng Run Đã khóa và giá thành một đơn vị.
- [ ] Phí/thuế có phạm vi và mức ưu tiên không hòa; FX có duy nhất cặp đúng chiều/loại/thời điểm.
- [ ] Chỉ nhập mục tiêu đúng phương pháp; phần trăm nhập như 20 cho 20%.
- [ ] Đọc cấu thành giá: giá khách trả − phí − thuế − giá vốn = lợi nhuận.
- [ ] Kịch bản Đã tính có snapshot/hash/trace; tạo bản mới để thử chính sách khác.

## 10. LEVEL 8 — Phân tích

Vào **So sánh kịch bản**, chọn **Sản phẩm**, SKU nếu dùng, rồi 2–5 kịch bản Đã tính. Chọn **Kịch bản mốc** và **So sánh kịch bản**. Tất cả phải cùng SKU hoặc cùng Product khi tất cả không SKU, cùng đơn vị đầu ra/cơ sở giá. Chênh tiền khác tiền tệ không tự trừ/quy đổi; chênh margin là điểm phần trăm.

Sau level 8, kiểm tra mốc, cơ sở so sánh, giá/lợi nhuận/margin và nguồn đã lưu. Màn hình chỉ đọc snapshot, không tra phí/thuế/FX hôm nay hoặc tự tính lại các scenario đã chọn.

## 11. Chọn ngày đúng trước khi nối kỳ mới

| Dữ liệu | Quy ước kết thúc | Ví dụ nối kỳ |
| --- | --- | --- |
| Giá mua, Quy đổi, BOM, Bao bì, gán SKU, Routing, Rate, AllocationRule, Formula/Scheme trong luồng Costing | Bao gồm ngày kết thúc | Cũ kết thúc 31/10, mới bắt đầu 01/11; tránh cùng ngày 31/10 |
| Phí/thuế Pricing | Không bao gồm ngày kết thúc `[start,end)` | Cũ kết thúc 01/11, mới bắt đầu 01/11; ngày 01/11 chỉ nguồn mới |
| Tỷ giá Pricing | Không bao gồm thời điểm kết thúc `[start,end)` | Cũ valid_to 01/11 00:00, mới effective_at đúng thời điểm ấy |
| Hiệu lực Scenario | Thông tin riêng của kịch bản | Không thay Ngày định giá; hai ngày được bằng nhau; không dùng làm khoảng chọn fee/tax/FX |

Không có quy tắc tự chọn “bản mới nhất” cho nguồn Costing; chồng nguồn có thể làm Run lỗi. Phí/thuế Pricing chọn theo phạm vi và ưu tiên; hòa bị lỗi. FX luôn cần duy nhất. Các module khác nhau có giới hạn sửa/đóng kỳ khác nhau; không áp thao tác Kết thúc hiệu lực Pricing sang BOM/Rate.

## 12. Nếu danh sách lựa chọn trống hoặc chưa tính được

Kiểm tra theo ba lớp: **có bản ghi**, **đúng phạm vi và hoạt động**, **đúng trạng thái/ngày và đủ nguồn thực thi**. Ví dụ SKU không xuất hiện thì kiểm tra Product/SKU; phương án không xuất hiện thì kiểm tra ngày và SchemeVersion; nguồn giá thành Pricing trống thì kiểm tra Product/SKU và Run Đã khóa, không tìm thêm giá mua ở Pricing.

[Ma trận phụ thuộc](13_DEPENDENCY_MATRIX.md) chỉ rõ từng điều kiện; [Lỗi thường gặp](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md) cung cấp cây xử lý. Khi gặp phần chưa có UI, ghi đúng gap thay vì tìm menu ẩn hoặc sửa trực tiếp database. Nếu đã có dữ liệu demo, thực hành kiểm tra/đọc/tính trên nguồn đó trước, sau đó học nhập cấu hình mới và dừng ở mốc Nháp nơi UI chưa hoàn chỉnh.

Nguồn: [forms danh mục](../../apps/master_data/forms.py), [forms sản phẩm](../../apps/product/forms.py), [forms BOM](../../apps/bom/forms.py), các forms/services/validators trong `apps/bom`; [Formula services](../../apps/formula_engine/services.py), [Scheme configuration](../../apps/costing/configuration.py), [RunForm](../../apps/costing/run_forms.py), [Costing resolvers](../../apps/costing/engine/resolvers/manufacturing.py), [Pricing forms](../../apps/pricing/forms.py), [ScenarioForm](../../apps/pricing/scenario_forms.py), [Pricing selectors](../../apps/pricing/selectors.py), [Comparison selectors](../../apps/pricing/comparison_selectors.py).
