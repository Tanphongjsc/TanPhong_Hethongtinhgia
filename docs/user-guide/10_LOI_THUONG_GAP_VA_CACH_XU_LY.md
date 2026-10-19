# Lỗi thường gặp và cách xử lý

Đối chiếu source ngày09/10/2026. `[HỆ THỐNG HIỆN TẠI]` Các bảng dùng mã lỗi thực tế khi source có mã, hoặc trích đoạn thông báo khi form chỉ trả lỗi tiếng Việt. Tên vật tư, mã công thức, ngày và dòng/cột thay theo dữ liệu. Không coi tên nhóm trong tài liệu là mã lỗi mới.

## 1. Xác định lỗi đang ở bước nào

| Hiện tượng | Ý nghĩa | Bước tiếp theo |
|---|---|---|
| Form vẫn hiện các ô đã nhập và có lỗi | Dữ liệu form/chọn nguồn chưa hợp lệ; có thể chưa tạo bản ghi | Sửa ô được đánh dấu, kiểm tra tham chiếu/ngày/đơn vị, lưu hoặc chạy lại trên form |
| Run có trạng thái Thất bại | Đã tạo Run, nhưng thực thi không hoàn tất | Đọc lỗi/mã tham chiếu, sửa nguồn hoặc cấu hình; chọn **Tạo lần tính mới**. Không có kết quả nửa vời để sửa |
| Kịch bản giá bán vẫn Nháp sau Tính giá bán | Pricing lưu chẩn đoán của lần thử; không có trạng thái FAILED | Sửa kịch bản Nháp/nguồn, chọn **Tính giá bán** lại |
| Kết quả đã khóa/đã tính không đổi khi giá/rate/FX đổi | Đúng cơ chế snapshot lịch sử | Run: **Tạo lần tính mới**; Scenario: **Nhân bản thành kịch bản mới**, mã mới rồi tính |
| Danh sách trống | Có thể do từ khóa/bộ lọc/kỳ, không phải toàn bộ dữ liệu bị xóa | **Đặt lại**, xem ngày và trạng thái; thử mã cụ thể |
| Cấu hình Nháp lưu được nhưng Run không nhận | Trạng thái bản ghi khác hiệu lực theo ngày; Run cần EFFECTIVE | Kiểm tra hai thông tin riêng; lưu ý gap kích hoạt upstream ở [GAP_REGISTER](GAP_REGISTER.md) |

Ghi lại tên trang, mã đối tượng, ngày tính, sản lượng/đơn vị/tiền tệ, thông báo, Run/Scenario và **Mã tham chiếu** nếu có. Không gửi mật khẩu hoặc chuỗi kết nối. Không đổi dữ liệu thực tế để vượt lỗi; không seed/reset/sửa DB như một bước hỗ trợ người dùng.

## 2. Tôi không chạy được Costing — kiểm tra gì?

1. **Phương án:** đang hoạt động, đúng một phiên bản EFFECTIVE tại ngày tính; **Kiểm tra cấu hình** đạt; đúng một OUTPUT MONEY, không đơn vị giá, thuộc MANUFACTURING.
2. **BOM:** đúng Product, có version EFFECTIVE duy nhất, output/yield/scrap và lines đầy đủ.
3. **Packaging:** chọn SKU, assignment chính đúng Product/ngày, một version hiệu lực; cơ sở đóng gói nhập dương và đúng đơn vị.
4. **Supplier Price:** đúng Item/ngày/trạng thái/đơn vị/tiền/min_qty, nhà cung cấp hoạt động, đúng một giá phù hợp.
5. **UoM Conversion:** đúng một cặp trực tiếp hoặc nghịch đảo theo ngày và phạm vi vật tư, không trùng chung/riêng.
6. **Routing:** đúng Product/version, công đoạn có nguồn lực/thời gian/cơ sở sản lượng hợp lệ.
7. **Resource Rate:** đúng một rate EFFECTIVE theo Resource/ngày; rate_type không tự quyết định bản thắng.
8. **Formula:** đúng phiên bản/hiệu lực, đủ biến, kiểu/đơn vị tương thích, không chia0 hoặc vòng.
9. **Allocation:** NORMAL_CAPACITY, có một kỳ EFFECTIVE, công suất dương/đơn vị/tiền rõ, không vượt công suất.
10. **Input/làm tròn:** đủ mọi dòng MANUAL, đúng kiểu và min/max; kết quả nằm trong độ chính xác lưu trữ.

```text
Run Thất bại
├─ MISSING_SOURCE / AMBIGUOUS_SOURCE
│  └─ Đọc tên nguồn trong thông báo → kiểm tra Scheme/BOM/Bao bì/Routing/Allocation và ngày/trạng thái
├─ MISSING_PRICE / AMBIGUOUS_PRICE
│  └─ Giá nhà cung cấp → Item + đơn vị + tiền + min_qty + ngày; cần đúng một giá
├─ MISSING_CONVERSION / AMBIGUOUS_CONVERSION
│  └─ Quy đổi đơn vị tính → cặp/chiều/ngày/Item; không tự nối chuỗi hoặc ưu tiên bản riêng
├─ MISSING_RATE / AMBIGUOUS_RATE
│  └─ Đơn giá nguồn lực → Resource + ngày; không tự chọn rate_type
├─ FORMULA_ERROR / thiếu biến / vòng / kiểu đơn vị
│  └─ Thiết lập công thức và phương án → sửa bản Nháp mới nếu bản cũ đã chốt
├─ MISSING_DENOMINATOR / UNSUPPORTED_ALLOCATION_DRIVER / UNSUPPORTED_CAPACITY
│  └─ Quy tắc + số liệu kỳ → NORMAL_CAPACITY và giới hạn hỗ trợ
├─ MISSING_FX / UNSUPPORTED_TAX / nguồn hoặc scope chưa hỗ trợ
│  └─ Kiểm tra dữ liệu thật và GAP_REGISTER; Pricing FX/Tax không tự xử lý Costing mua
└─ SYSTEM_ERROR
   └─ Cung cấp Run + Mã tham chiếu cho người phụ trách; không suy đoán tổng thành công
```

## 3. Tôi không tính được giá bán — kiểm tra gì?

1. **Costing Run:** đã LOCKED, có dòng/kết quả đơn vị hợp lệ đã lưu, thuộc đúng Product/SKU đang chọn.
2. **Channel:** đang hoạt động; currency/khu vực/giao dịch phù hợp.
3. **Fee:** EFFECTIVE đúng ngày/scope; fee_base=LIST_PRICE, phí có chi phí đã gồm thuế, refundable_ratio=0; không hòa xếp hạng cùng fee_type.
4. **Tax:** chọn rõ REQUIRED hoặc NONE; nếu REQUIRED cần khu vực và rule phù hợp; basis/thuế/inclusion nằm trong contract hỗ trợ.
5. **FX:** currency khác nhau cần tỷ giá direct đúng chiều/loại tại0hngày định giá; không nghịch đảo/nối chuỗi tự động.
6. **Mục tiêu:** chỉ nhập mục tiêu của phương pháp đã chọn; Margin%/Markup% trên UI là phần trăm, khác tỷ lệ thập phân của Formula/Run MANUAL.
7. **Khả thi:** phí/thuế/margin/sàn/trần phải cho phép giá dương và mẫu số hợp lệ.

```text
Tính giá bán → vẫn Nháp và có lỗi
├─ base_run chưa hợp lệ / INVALID_COSTING_RUN / INVALID_COST
│  └─ Chọn Run đã khóa có giá vốn đơn vị hợp lệ; không tạo giá vốn giả hoặc tái tính Costing trong Pricing
├─ AMBIGUOUS_RULE
│  └─ Phí/Thuế → xem type, scope và priority; xử lý hòa, không đổi priority tùy ý
├─ MISSING_TAX / UNSUPPORTED_TAX_BASE / MIXED_TAX_INCLUSION
│  └─ Thuế và tax mode → đúng ngày/khu vực/giao dịch/basis/inclusion
├─ MISSING_FX_TYPE / MISSING_FX / AMBIGUOUS_FX
│  └─ Tỷ giá → loại + chiều +0hngày + khoảng [start,end)
├─ UNSUPPORTED_FEE_BASE / UNSUPPORTED_FEE_TAX / UNSUPPORTED_REFUND
│  └─ Phí hiện chưa theo contract thực thi → đọc gap, giữ đúng chính sách phí thực tế
└─ INVALID_DENOMINATOR / INVALID_MARGIN / INVALID_MARKUP / INVALID_PRICE
   └─ Phương pháp/mục tiêu/giá vốn/phí/thuế → kiểm tra giả định, sau đó Tính giá bán lại
```

Không có phí phù hợp là cảnh báo và không khấu trừ phí kênh. Không có thuế khi đã chọn REQUIRED là lỗi, không tự coi thuế0. Không chọn NONE chỉ để né lỗi thiếu thuế.

## 4. Lỗi form và danh mục dùng chung

| Thông báo/trường hợp | Nguyên nhân và kiểm tra | Cách xử lý | Ảnh hưởng sau đó |
|---|---|---|---|
| Trường bắt buộc/mã/tên trống | Bỏ ô required hoặc chỉ khoảng trắng | Nhập đủ; xem [Field Reference](12_FIELD_REFERENCE.md) | Chưa lưu thành công; không có nguồn mới |
| Mã đã tồn tại, Mã SKU đã tồn tại, Mã vạch đã tồn tại | Trùng mã sau chuẩn hóa; barcode có giá trị trùng | Tìm bản đã có hoặc dùng mã đúng khác; không nhân đôi cùng đối tượng | Tránh sai tham chiếu ở nguồn/Run |
| Danh mục tham chiếu không hợp lệ / không còn tồn tại | Dropdown đã cũ, reference không đúng bản ghi hoặc nguồn vừa đổi | Tải lại, chọn từ danh sách hiện tại | Giữ form đến khi có nguồn hợp lệ |
| Không thể chọn danh mục đã ngừng hoạt động | Chọn mới FK ngừng hoạt động | Chọn nguồn đang hoạt động; hoạt động lại chỉ nếu phù hợp nghiệp vụ | Một FK cũ còn giữ được khi sửa chưa bảo đảm chạy Run mới |
| Dữ liệu không còn hợp lệ…vượt giới hạn lưu trữ | Constraint/FK/unique/precision hoặc thay đổi đồng thời | Tải lại, kiểm tra ô lỗi; nếu lặp, gửi mã/thời điểm/trang | Không coi toast/lưu thất bại là dữ liệu đã cập nhật |
| Giá trị tiền tệ cần khai báo đơn vị tiền tệ | Phần tử MONEY thiếu Currency | Chọn Tiền tệ đúng | Formula/Scheme/Run mới dùng tiền tệ đó |
| Giá trị số lượng cần khai báo đơn vị tính | Phần tử QUANTITY thiếu default_uom | Chọn đơn vị mặc định đúng đại lượng | RUN_QUANTITY và Formula kiểm tra đơn vị |
| Đại lượng phải phù hợp với nhóm đơn vị tính… | dimension_code lệch đại lượng của UoM | Sửa đúng mã đại lượng hoặc chọn đúng đơn vị | Tránh type/unit mismatch |
| Số chữ số làm tròn phải từ0đến12 | Scale sai hoặc không nguyên | Nhập0–12; cân nhắc giới hạn lưu8dp/10dp | Có thể vẫn overflow nếu scale cho phép nhiều hơn lưu trữ |
| Mã tiền tệ phải có đúng3ký tự | Currency code không đúng độ dài | Dùng mã3ký tự; mã bản có sẵn không sửa được | Không tạo FX chỉ bằng tạo currency |
| Đơn vị nguồn và đơn vị đích phải khác nhau | Tạo conversion cùng UoM | Không cần quy đổi cho cùng đơn vị | Engine dùng identity khi cùng UoM |
| Quy đổi chung phải sử dụng các đơn vị cùng nhóm… | Khác category nhưng không chọn Item | Chọn cặp cùng nhóm hoặc quy đổi riêng theo Item có căn cứ | Không tự suy ra kg/hộp từ metadata |
| Hệ số quy đổi phải lớn hơn0 | Factor≤0/không hữu hạn | Nhập factor dương: đích=nguồn×factor | Run mới dùng đúngfactor theo ngày |
| Đổi nhóm sẽ làm quy đổi chung hiện có khác nhóm… | Đổi category UoM làm hỏng conversion chung | Rà các quy đổi liên quan trước | Không đổi nhóm để né kiểm tra |
| Lượng tịnh phải lớn hơn0 | SKU quantity≤0 | Nhập lượng tịnh dương và đơn vị đúng | Run mới có thể thay scaling; Run cũ giữ snapshot |
| Khối lượng tổng không được nhỏ hơn khối lượng tịnh | Gross<net hoặc nhầm đơn vị | Sửa số đo/đơn vị có căn cứ | Số đo là metadata, không tự tạo chargeable freight |
| Vui lòng chọn đơn vị…khối lượng/chiều dài | Có số đo nhưng thiếu MASS/LENGTH | Chọn đúng nhómđại lượng | Dữ liệu form hợp lệ; không đồng nghĩa có logisticsengine |
| Đơn giá/Số lượng tối thiểu phải≥0 | Giá/min_qty âm hoặc không hữu hạn | Nhập dữ liệu thật không âm | min_qty không phải automatic tier winner |
| Tỷ lệ thuế/khấu trừ phải từ0đến1 | SupplierPrice nhập10thay0.1 | Giá nhà cung cấp dùng tỷ lệ thập phân0–1 | Khác UI% của BOM/Pricing; Costing giá có thuế vẫn bị chặn |
| Ngày kết thúc phải sau ngày bắt đầu | end≤start hoặc có end thiếu start | Sửa kỳ đúng quy tắc module | Costing inclusive; fee/tax/FX Pricing endexclusive |

## 5. Lỗi cấu hình sản xuất

| Thông báo/trường hợp | Nguyên nhân và kiểm tra | Cách xử lý | Ảnh hưởng sau đó |
|---|---|---|---|
| Không thể chỉnh sửa phiên bản đã được chốt… | BOM/bao bì/routing APPROVED/EFFECTIVE/RETIRED | **Tạo phiên bản mới** từ bản nguồn, sửa Nháp | Bản chốt/Run cũ giữ nguyên; có gap kích hoạt upstream |
| Không thể đổi sản phẩm vì… | Header đã có bản chốt; bao bì còn liên kết SKU | Giữ quan hệ đúng hoặc tạo header nghiệp vụ mới | Không chuyển cấu hình lịch sử sang Product khác |
| Sản lượng chuẩn phải lớn hơn0 | BOM output_qty≤0 | Nhập output dương và UoM đúng | Đây là mẫu số scaling |
| Tỷ lệ thu hồi phải lớn hơn0/không vượt100% | Yield ngoài(0,100] trên UI | Nhập tỷ lệ% hợp lệ | Costing chia lượng cho yield |
| Tỷ lệ hao hụt phải nhỏ hơn100% | Scrap ngoài[0,100) | Nhập% hợp lệ có căn cứ | Costing chia cho(1−scrap); không phải cộng hao hụt đơn giản |
| Số lượng phải lớn hơn0 | Dòng BOM/bao bì qty≤0 | Nhập lượng dương | Không bỏ chi phí bằng qty0 |
| ITEM: không tìm thấy quy đổi…tại ngày… | Dòng dùng UoM khác Item.base_uom, thiếu cặp ở ngày đầu version/hôm nay | Kiểm tra đúng cặp/ngày/Item | Form chỉ kiểm tra cặp; Run còn kiểm tra duy nhất và quy đổi sang đơn vị giá |
| Số đơn vị trong cấp cha phải lớn hơn0 | units_per_parent≤0 | Dương hoặc để trống nếu chưa khai báo | Metadata này không được nhân tự động trong Costing |
| SKU phải thuộc sản phẩm của cấu hình bao bì | Gán SKU khác Product | Chọn SKU cùng Product | Assignment mới hợp lệ; còn cần primary/dateunique |
| SKU đã được gán cấu hình này với cùng ngày bắt đầu | Trùng SKU+config+start | Mở bản gán đã có hoặc kỳ mới đúng nghiệp vụ | Không bảo đảm tránh mọi overlap khác |
| Thứ tự công đoạn phải lớn hơn0/đã tồn tại | sequence≤0 hoặc trùng trong version | Dùng số nguyên dương khác | Thứ tự operation không phải mã công đoạn bắt buộc duy nhất |
| Nguồn lực không thuộc trung tâm sản xuất đã chọn | Resource thuộc WorkCenter khác | Chọn đúng center/resource hoặc nguồn dùng chung hợp lệ | Run cũng kiểm tra tính nhất quán |
| Vui lòng chọn đơn vị thời gian/…đại lượng thời gian | Setup/run khác0 nhưng thiếu TIME UoM | Chọn phút/giờ/đơn vị TIME phù hợp | Không mặc định giờ hoặc tự chia60 |
| Thiếu sản lượng lô/cơ sở hoặc đơn vị kèm theo | Batch/operationbasis nhập một nửa cặp | Nhập lượng dương+đơn vị, hoặc bỏ cả cặp nếu không dùng | Run_time>0 cần basis; ưu tiên operation trước batch |
| Vui lòng nhập mã loại đơn giá | Rate thiếu rate_type | Nhập mã nghiệp vụ thống nhất | rate_type vẫn không là lựa chọn tự động của Run |
| Mức ưu tiên phải là số nguyên… | Priority ngoài32bit hoặc không nguyên | Dùng số nguyên trong giới hạn | Allocation priority không tự chọn giữa nguồn mơ hồ |
| Số phiên bản đã tồn tại… | Xung đột lưu/numbering đồng thời | Tải lại và tạo lại, không nhập sốversion thủ công | Bản nguồn không sửa đổi |

## 6. Lỗi Formula và Scheme

| Thông báo/trường hợp | Nguyên nhân và kiểm tra | Cách xử lý | Ảnh hưởng sau đó |
|---|---|---|---|
| Mã phải bắt đầu bằng chữ cái… | Mã Formula sai quy tắc ASCII hoặc trùng TRUE/FALSE/AND/OR/NOT | Chữ cái đầu, tiếp theo chữ/số/_; không dùng từ dành riêng | Không áp quy tắc mã Formula cho mọi danh mục |
| Biểu thức công thức không được để trống | Expression rỗng | Nhập biểu thức có biến/hàm đang hỗ trợ | Sau đó mới kiểm tra được dữ liệu mẫu |
| Thiếu dấu đóng văn bản / Cần ký hiệu… / Ký hiệu hoặc giá trị dư… | Thiếu nháy/ngoặc hoặc cú pháp dư | Xem dòng/cột, sửa dấu; số thập phân dùng dấu chấm | Không nhập dấu nhóm nghìn hoặc công thức Excel tùy ý |
| Không hỗ trợ hàm… / tham số không hợp lệ | Hàm ngoài ROUND/MIN/MAX/ABS/IF hoặc sai số tham số | Dùng danh sách hàm trong [chương06](06_HUONG_DAN_FORMULA_VA_COSTING.md) | LOOKUP không có trong ngôn ngữ công thức |
| Không tìm thấy biến hoặc công thức… | Mã chưa có, sai tên hoặc ngừng hoạt động | Chọn mã từ Biến dữ liệu; `$` cho phần tử, `@` cho Formula | Mã dòng phương án không tự trở thành biến |
| Mã mơ hồ giữa phần tử/công thức | Mã không có tiền tố trùng giữa hai loại; hoặc mã cũ khác hoa/thường | Dùng tiền tố rõ; xử lý dữ liệu cũ mơ hồ | Không tự chọn tùy bản ghi |
| Kiểu dữ liệu hoặc đơn vị…không tương thích | Tiền cộng Số thường, VND cộng USD, kg cộng g, hai nhánh IF khác kiểu | Dùng các phần tử tương thích; cấp dữ liệu đã quy đổi qua nguồn được hỗ trợ | Muốn cộng phụ phí, tạo biến Tiền thay vì cộng số1000 vào tiền |
| Chưa hỗ trợ nhân hai đại lượng có đơn vị / chia tạo đại lượng phái sinh | MONEY×QUANTITY hoặc tạo đơn vị mới | Nhập tổng MONEY đã xác định; hoặc thiết kế Số thường có quy ước rõ | Không tự kiểm soát công thức vận tải tấn-km |
| NOT/AND/OR/IF yêu cầu Có/Không | Dùng số/văn bản làm điều kiện | Cung cấp Boolean hoặc phép so sánh cùng kiểu | IF vẫn kiểm tra cả hai nhánh trước tính |
| Không thể chia cho0 | Mẫu số bằng0, kể cả phép lấy số dư | Sửa input/công thức theo nghiệp vụ | Trong Run có mã FORMULA_ERROR; cần tạo kết quả mới |
| Phát hiện phụ thuộc vòng… | A→B→A hoặc vòng giữa các dòng cung cấp biến trong phương án | Đọc đường vòng, bỏ tham chiếu quay lại | Đổi thứ tự hiển thị không sửa được vòng |
| Vượt giới hạn độ dài/nút/độ sâu/thực thi | Biểu thức, quan hệ phụ thuộc hoặc input quá lớn | Đơn giản hóa/chia cấu hình có kiểm thử | Diễn giải dài có thể được rút gọn kèm lưu ý |
| Cần ít nhất một bộ kiểm thử… | Kích hoạt mà không có mẫu đang hoạt động | Lưu tên, input, kết quả mong đợi ở trang phiên bản | Kiểm thử trong Studio chưa lưu mẫu |
| Bộ kiểm thử chưa đạt… | Mẫu cho kết quả khác mong đợi hoặc có lỗi | Kiểm tra dữ liệu, ý nghĩa và công thức; không đổi expected chỉ để khớp actual | Phiên bản chưa được kích hoạt |
| Quá nhiều bộ kiểm thử; tối đa200 | Hơn200 mẫu đang hoạt động | **Ngừng sử dụng** mẫu không còn phù hợp | Không có ô chỉnh sai số cho phép trên UI |
| Vui lòng nhập tên/kết quả mong đợi để lưu bộ kiểm thử | Lưu mẫu nhưng thiếu tên hoặc expected | Điền tên và expected; số lưu tối đa24 chữ số/8 số thập phân | Nếu chỉ thử tính có thể bỏ expected |
| Phiên bản công thức chưa được kích hoạt/không hợp lệ/không hiệu lực… | Phương án chọn sai trạng thái/validation/ngày | Chọn đúng phiên bản; kích hoạt Formula cần mẫu kiểm thử và ngày | Công thức gốc gán bằng phiên bản cụ thể; công thức lồng chọn theo ngày |
| Phương án chưa cung cấp dữ liệu cho phần tử… | Đầu vào cuối cùng của công thức thiếu dòng cung cấp | Thêm đúng một dòng nguồn cho phần tử ấy | Không có dữ liệu mặc định0 |
| Phần tử…có nhiều nguồn trong phương án | Nhiều dòng cùng cung cấp biến cần dùng | Giữ nguồn duy nhất cho biến đó | Không tự chọn dòng có thứ tự thấp nhất |
| Mã dòng/Thứ tự đã tồn tại trong phiên bản này | Trùng mã dòng hoặc display_order | Dùng mã/thứ tự duy nhất | Thứ tự hiển thị khác thứ tự tính |
| Mã bộ lấy dữ liệu chưa được đăng ký… | Mã SYSTEM ngoài danh sách hỗ trợ | Dùng MATERIAL_COST/PACKAGING_COST/RESOURCE_COST/RUN_QUANTITY/ALLOCATION:<code>, hoặc MANUAL nếu phù hợp | Không có MACHINE_COST/LABOR_COST/SHIPPING_COST riêng |
| Nguồn dữ liệu…chưa có bộ kiểm tra cấu hình… | LOOKUP/EXTERNAL | Chưa thể kích hoạt; chỉ thay nguồn khi giữ đúng nghiệp vụ | Lưu Nháp không tạo bộ máy thực thi |
| Điều kiện nâng cao/chưa có bộ thực thi… | Cấu hình cũ có condition JSON không rỗng | Ghi nhận gap; không có ô JSON để người nhập liệu sửa | Không tự bỏ điều kiện thật để chạy |
| Vui lòng đặt ngày bắt đầu hiệu lực… | Kích hoạt Formula/Scheme thiếu ngày đầu | Sửa ngày trên bản Nháp | Ngày cuối phải sau ngày đầu và bao gồm ngày cuối của Costing |
| Không thể chỉnh sửa phiên bản đã được chốt… | Formula/Scheme ngoài DRAFT/IN_REVIEW | **Tạo phiên bản mới** | Không dùng đổi trạng thái để né tính bất biến |

## 7. Mã lỗi thực thi Costing

| Mã/thông báo | Nguyên nhân và kiểm tra | Cách xử lý / nơi xử lý | Ảnh hưởng sau đó |
|---|---|---|---|
| MISSING_SOURCE / AMBIGUOUS_SOURCE | Không có hoặc có nhiều phương án/BOM/assignment bao bì/version/routing/rule/period đúng ngày | Đọc tên nguồn trong thông báo, kiểm tra trạng thái/hoạt động/ngày để có đúng một nguồn | Không chọn bản mới nhất hoặc priority thay chính sách; tạo Run mới sau khi sửa |
| MISSING_PRICE | Giá Item không đạt ngày/trạng thái/tiền tệ/min_qty/nhà cung cấp hoạt động | **Giá nhà cung cấp**: kiểm tra đơn vị giá và lượng tối thiểu | Giá Nháp vừa tạo vẫn chưa dùng được |
| AMBIGUOUS_PRICE | Nhiều giá/bậc lượng/nhà cung cấp đủ điều kiện | Kiểm tra kỳ và dữ liệu thật; cần nguồn duy nhất | Không chọn rẻ nhất, mới nhất hoặc bậc cao nhất |
| MISSING_RATE / AMBIGUOUS_RATE | Không có hoặc có nhiều rate theo Resource/ngày, kể cả khác rate_type | **Đơn giá nguồn lực**: kiểm tra nguồn phù hợp | Run không có ô chọn rate_type |
| MISSING_CONVERSION / AMBIGUOUS_CONVERSION | Thiếu/trùng cặp trực tiếp/nghịch đảo, quy đổi chung/riêng Item | **Quy đổi đơn vị tính**: kiểm tra factor/ngày/Item/phạm vi | Không nối chuỗi hoặc ưu tiên bản riêng tự động |
| MISSING_FX | Tiền tệ phần tử/giá/rate/period khác Run | Kiểm tra nguồn và tiền tệ thật; đọc gap FX của Costing | Tỷ giá Pricing không sửa lỗi này |
| UNSUPPORTED_TAX | Giá mua tax_inclusive hoặc tax_rate khác0 | Giữ thuế đúng thực tế; contract xử lý hiện chưa có | Không xóa thuế thật để chạy |
| UNSUPPORTED_SUBSTITUTION | BOM có optional/substitute_group | Dùng BOM có thành phần đã xác định nếu phù hợp; ghi nhận thiếu bộ chọn | Không bỏ dòng âm thầm |
| UNSUPPORTED_PACKAGING_CONDITION | Dòng bao bì có market_code/artwork_code | Xem cấu hình bao bì và gap bộ chọn Run | Không tự chọn thị trường/mẫu |
| Tính bao bì cần chọn SKU / thiếu cơ sở đóng gói | Không có SKU hoặc lượng cơ sở dương/đơn vị | **Form Run**: chọn SKU, nhập cơ sở mà các dòng qty đáp ứng | Không suy ra cơ sở1hộp từ tên SKU |
| Định mức/bao bì chưa có thành phần; quy trình chưa có công đoạn | Header/phiên bản rỗng | Chuẩn bị dòng/công đoạn trên bản Nháp phù hợp | Cần nguồn EFFECTIVE được thiết lập |
| Công đoạn…thiếu nguồn lực chính/đơn vị thời gian | Thời gian khác0 nhưng thiếu Resource/TIME | **Quy trình/nguồn lực/trung tâm**: bổ sung đúng cấu hình | Setup tính một lần mỗi Run |
| Công đoạn…thiếu sản lượng cơ sở và đơn vị | run_time>0 nhưng thiếu cơ sở công đoạn và batch | Nhập đủ cặp lượng/đơn vị; cơ sở công đoạn ưu tiên batch | Không tự coi cơ sở bằng1 |
| UNSUPPORTED_ALLOCATION_DRIVER | Driver khác NORMAL_CAPACITY, hoặc có formula_code/condition | **Quy tắc phân bổ**: chỉ contract đã có số liệu kỳ rõ ràng | Priority/formula_code không tự tạo thuật toán |
| MISSING_DENOMINATOR | normal_capacity thiếu/không dương hoặc thiếu UoM | Cần số liệu kỳ được chuẩn bị; hiện chưa có UI nhập kỳ | Không lấy mẫu số toàn nhà máy từ một SKU |
| UNSUPPORTED_CAPACITY | Sản lượng quy đổi của Run vượt công suất kỳ | Kiểm tra giả định, kỳ và công suất có căn cứ | Không tự cắt lượng hoặc tăng công suất để né lỗi |
| Lần tính cần đúng một dòng đầu ra tổng tiền… | OUTPUT thiếu/trùng/sai kiểu MONEY/đơn vị/phạm vi | **Scheme bản mới**: một OUTPUT MONEY, không UoM, MANUFACTURING | Tổng không phải phép cộng tất cả dòng |
| Iteration này chỉ tính chi phí sản xuất… | Có dòng LANDED/COST_TO_SERVE/CHANNEL/PRICING | Đọc capability/gap; chưa chạy được các scope ấy | Không đổi scope sai bản chất khoản phí |
| INVALID_INPUT | Thiếu/thừa/sai kiểu MANUAL hoặc vượt giới hạn | Điền mọi dòng MANUAL trên form, đúng kiểu/min/max | editable=False vẫn hỏi MANUAL |
| FORMULA_ERROR / CALCULATION_ERROR | Lỗi Formula/Decimal trong khi thực thi | Xem công thức/input/giới hạn ở chương06 | Run FAILED không giữ kết quả nửa vời |
| PRECISION_OVERFLOW | Vượt số chữ số hoặc không lưu chính xác8dp,10dp với PERCENT | **Phần tử chi phí/Scheme**: cấu hình làm tròn, xem độ lớn giá trị | Không tự cắt số tại DB |
| SOURCE_LIMIT | Một truy vấn nguồn vượt2000 bản ghi | Thu hẹp dữ liệu/phạm vi, nhờ người phụ trách kiểm tra | Không tải nguồn không giới hạn |
| Khóa lần tính đã được dùng cho dữ liệu khác… | Khóa form cũ nhưng yêu cầu đã đổi | Mở form mới/tạo Run mới | Cùng khóa và cùng yêu cầu trả cùng Run |
| SYSTEM_ERROR / Không thể lưu lần tính giá… | Lỗi thực thi/lưu dữ liệu ngoài dự kiến | Cung cấp Run và Mã tham chiếu; thử lại cùng form nếu thông báo yêu cầu | Không kết luận đã tính thành công |

## 8. Lỗi Pricing Foundation và Kịch bản giá bán

Pricing fee/tax/FX dùng `[start,end)`; nguồn kết thúc01/11 không dùng ngày01/11. Nguồn Costing kết thúc31/10 vẫn dùng31/10. Khoảng **Hiệu lực kịch bản** là metadata khác ngày chọn fee/tax/FX; validation kịch bản cho phép end=start và chỉ chặn end<start.

| Mã/thông báo | Nguyên nhân và kiểm tra | Cách xử lý / nơi xử lý | Ảnh hưởng sau đó |
|---|---|---|---|
| Vui lòng nhập tỷ lệ hoặc số tiền cố định | Fee/Tax không có cả rate lẫn fixed | Nhập ít nhất một;0 là giá trị, khác để trống | Lưu hợp lệ chưa bảo đảm basis được engine hỗ trợ |
| Tỷ lệ phải từ0%đến100% | Rate/refund/recovery ngoài khoảng | Foundation nhập% trên UI, DB giữ phân số | Formula/Run MANUAL dùng quy ước khác |
| Vui lòng chọn tiền tệ cho các giá trị tiền | Fixed/floor/cap có giá trị, kể cả0, nhưng thiếu currency | Chọn tiền tệ đúng | Cần FX nếu khác tiền Scenario |
| Giá trị trần không được nhỏ hơn giá trị sàn | Cap<floor | Sửa sàn/trần đúng biểu phí | Áp riêng từng loại phí |
| SKU không thuộc nhóm sản phẩm đã chọn | Phạm vi phí không nhất quán | Chọn SKU thuộc Product.category đã chọn | Phí dùng nhóm Product, không phải nhóm Item |
| Tỷ giá phải lớn hơn0 / tiền đích phải khác nguồn | Rate không dương hoặc cặp trùng | Nhập FX direct đúng chiều | Không tự nghịch đảo/nối chuỗi |
| Bản đã chốt chỉ được xem… | Sửa Fee/Tax/FX ngoài Nháp | Tạo bản mới cho kỳ mới; **Kết thúc hiệu lực** khi bản EFFECTIVE chưa có end và end hợp lệ | Chỉ đóng kỳ tương lai, không đổi amount/scope quá khứ |
| Chỉ kết thúc bản đang hiệu lực và chưa có mốc kết thúc | Bản không EFFECTIVE hoặc đã có end | Chọn đúng bản | Không thay Run/Scenario cũ |
| Mốc kết thúc phải trong tương lai và sau mốc bắt đầu | End không tương lai hoặc không sau start | Chọn mốc hợp lệ | Giữ định nghĩa lịch sử |
| Mã kịch bản đã tồn tại | Trùng code | Nhân bản cần mã mới | Không ghi đè bản CALCULATED |
| Vui lòng chọn lần tính giá thành đã hoàn thành… | Base Run chưa LOCKED/không có dòng/kết quả đầy đủ | Chọn Run hợp lệ đúng Product/SKU | Pricing không tính lại Costing |
| Lần tính giá thành không thuộc sản phẩm/SKU… | Phạm vi form khác Run | Chọn đúng Product/SKU và Run | Không trộn giá vốn khác quy cách |
| Lần tính giá thành chưa có kết quả đơn vị hợp lệ đã lưu | per_unit thiếu/sai/không hữu hạn/âm | Dùng Run đã hoàn thành hợp lệ, không nhập thay JSON | Có thể cần Run mới |
| Chỉ nhập mục tiêu tương ứng… | Nhập thêm mục tiêu của phương pháp khác | Chỉ giữ mục tiêu của method đang chọn | Không cộng dồn margin, markup và lợi nhuận đơn vị |
| Biên lợi nhuận phải từ−100%đến dưới100% | Margin ngoài khoảng | Kiểm tra% UI và ý nghĩa mục tiêu |100% không hợp lệ |
| Tỷ lệ cộng…không được dưới−100% | Markup thấp hơn−100% | Nhập giá trị hợp lệ | Engine còn yêu cầu giá vốn>0 |
| Vui lòng xác định có áp dụng thuế… / nhập mã khu vực… | Tax mode chưa rõ hoặc REQUIRED thiếu khu vực | Chọn REQUIRED/NONE có căn cứ, nhập đúng khu vực | Thiếu thuế không mặc định0 |
| INVALID_COSTING_RUN / INVALID_COST | Trạng thái Run hoặc giá vốn không hợp lệ | Chọn Run LOCKED có giá vốn đơn vị≥0 | Markup với giá vốn0 vẫn không hỗ trợ |
| INACTIVE_REFERENCE | Channel/Currency ngừng hoạt động | Chọn nguồn hợp lệ; hoạt động lại chỉ khi phù hợp | Bản đã tính vẫn đọc snapshot |
| AMBIGUOUS_RULE | Phí/thuế cùng type, cùng hạng phạm vi và priority | Rà phạm vi/priority theo chính sách thật | Loại phí khác nhau cộng; không áp policy này cho giá mua |
| RULE_LIMIT | Hơn200 phí hoặc thuế phù hợp | Thu hẹp phạm vi cấu hình | Không thay policy bằng tăng giới hạn |
| INVALID_RULE | Rule EFFECTIVE vi phạm validation hiện tại | Kiểm tra Fee/Tax; bản đã chốt cần bản mới | Lỗi giữ Scenario Nháp |
| UNSUPPORTED_FEE_BASE | fee_base khác LIST_PRICE | Chỉ dùng LIST_PRICE khi đúng chính sách thật | Không đổi NET thành LIST để né lỗi |
| UNSUPPORTED_REFUND | refundable_ratio khác0 | Contract hoàn phí chưa hỗ trợ | Không tự giảm phí |
| UNSUPPORTED_FEE_TAX | Phí có chi phí nhưng chưa gồm thuế | Cần policy thuế trên phí; hiện chỉ phí đã gồm thuế | Không đánh dấu tax_inclusive sai thực tế |
| MISSING_TAX | REQUIRED không có rule đúng ngày/khu vực/phạm vi | **Quy tắc thuế**: xem ngày/trạng thái/nhóm/người bán/giao dịch | Không tự chuyển NONE |
| UNSUPPORTED_TAX_BASE | Basis ngoài SELLING_PRICE/LIST_PRICE | Chỉ cơ sở giá bán trước thuế chung được hỗ trợ | Không thuế chồng thuế |
| UNSUPPORTED_TAX_RECOVERY | recoverable_ratio khác0 | Khấu trừ thuế bán hàng chưa có contract | Không xóa tỷ lệ thật chỉ để chạy |
| MIXED_TAX_INCLUSION | Các thuế được chọn trộn inclusive/exclusive | Bộ thuế này chưa theo contract hỗ trợ | Không tự bỏ một sắc thuế |
| MISSING_FX_TYPE | Cần quy đổi nhưng thiếu rate_type | Nhập Loại tỷ giá trên Scenario | Áp cho giá vốn/phí/thuế tiền khác currency |
| MISSING_FX / AMBIGUOUS_FX | Không có hoặc nhiều FX direct đúng chiều/loại tại0h ngày | **Tỷ giá**: kiểm tra cặp, thời điểm có múi giờ, khoảng[start,end) | Không chọn nghịch đảo hoặc mới nhất ngầm |
| INVALID_FX | Tỷ giá không hữu hạn/không dương | Kiểm tra nguồn FX | Không mặc định1 |
| INVALID_METHOD / INVALID_MARGIN / INVALID_MARKUP | Method/mục tiêu sai; markup khi cost=0 | Sửa phương pháp/mục tiêu hoặc chọn Run phù hợp | Giữ Nháp, không có FAILED |
| INVALID_DENOMINATOR | Phí/thuế/margin/sàn/trần không có giá dương khả thi | Rà giả định và mục tiêu; bộ giải đã xét từng khoảng sàn/trần | Không giảm dữ liệu thật tùy ý |
| INVALID_PRICE | Giá tính không dương | Rà giá vốn, mục tiêu, phí, thuế | Cần giá dương để tính margin |
| MONEY_RANGE / INVALID_NUMBER | Tiền vượt phạm vi hoặc số float/không hữu hạn | Sửa giá trị/độ chính xác có căn cứ | Tiền tính Decimal8dp HALF_EVEN |
| Kịch bản đã chốt chỉ được xem… | Sửa CALCULATED hoặc trạng thái cũ | **Nhân bản thành kịch bản mới** | Calculate lặp CALCULATED trả snapshot cũ |

## 9. Lỗi so sánh kịch bản

| Thông báo | Nguyên nhân | Cách xử lý |
|---|---|---|
| Vui lòng chọn từ2đến5kịch bản để so sánh | Số lượng ngoài khoảng | Chọn2–5 kịch bản đã tính |
| Mã tham chiếu kịch bản không hợp lệ / Không được chọn trùng… | ID không hợp lệ hoặc trùng | Chọn lại trên danh sách |
| Không tìm thấy một hoặc nhiều kịch bản đã chọn | ID không còn trong phạm vi/query | Mở lại danh sách, chọn bản hiện có |
| Kịch bản…chưa có kết quả đã lưu hợp lệ… | Chưa CALCULATED, snapshot thiếu/hỏng/sai schema/hash/cơ sở | Chọn bản hợp lệ; nếu nghi dữ liệu lỗi, gửi mã cho người phụ trách |
| Chỉ có thể so sánh…cùng một SKU… | Khác SKU/Product hoặc trộn có SKU và không SKU | Chọn cùng SKU; hoặc cùng Product khi tất cả không SKU |
| Các kịch bản phải có cùng đơn vị đầu ra và cơ sở giá đã lưu | Output UoM/cơ sở/policy khác | Chọn nhóm đồng nhất; không tự đổi đơn vị để so |
| Kịch bản mốc phải thuộc danh sách đã chọn | Baseline ngoài selection | Chọn một kịch bản đang so sánh làm mốc |
| Chênh tiền hiển thị — khi khác currency; chênh tương đối — khi mốc0 | Thiếu cơ sở so sánh, không phải lỗi tính | Xem tiền riêng theo currency; không trừ VND với USD hoặc chia0 |

So sánh không gọi engine hoặc chọn phí/thuế/FX hiện tại. Sửa nguồn không đổi các cột đã tính. Muốn so thời điểm mới, tạo Scenario mới rồi chọn cùng nhóm hợp lệ.


## 10. Khi nào dừng kiểm tra dữ liệu và ghi nhận gap?

Nếu lỗi là nguồn/phạm vi/driver/hàm chưa hỗ trợ, hoặc cần thao tác UI chưa có, sửa đủ trường bắt buộc vẫn không tạo ra chức năng mới. Ví dụ CostPoolPeriod chưa có UI; LOOKUP/EXTERNAL chưa có resolver; LANDED/COST_TO_SERVE chưa được Run thực thi; thuế mua/CostingFX chưa có contract. Đọc [GAP_REGISTER](GAP_REGISTER.md), ghi nhu cầu và ảnh hưởng, chuyển người phụ trách quyết định. Không tạo menu/nút/schema hoặc workflow giả trong hướng dẫn.

Nguồn: [catalog validators](../../apps/master_data/validators.py), [product validators](../../apps/product/validators.py), [BOM validators](../../apps/bom/validators.py), [packaging](../../apps/bom/packaging_validators.py), [routing](../../apps/bom/routing_validators.py), [resource](../../apps/bom/resource_validators.py), [overhead](../../apps/bom/overhead_validators.py), [Formula parser](../../apps/formula_engine/parser.py), [types](../../apps/formula_engine/validator.py), [evaluator](../../apps/formula_engine/evaluator.py), [Formula services](../../apps/formula_engine/services.py), [Scheme configuration](../../apps/costing/configuration.py), [Run service](../../apps/costing/run_services.py), [Costing runner](../../apps/costing/engine/runner.py), [resolvers](../../apps/costing/engine/resolvers/prices.py), [Pricing validation](../../apps/pricing/scenario_validators.py), [Pricing resolver](../../apps/pricing/engine/resolvers.py), [solver](../../apps/pricing/engine/solver.py), [FX selectors](../../apps/pricing/selectors.py), [Comparison](../../apps/pricing/comparison.py).
