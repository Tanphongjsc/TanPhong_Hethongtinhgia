# Hướng dẫn dữ liệu danh mục

[Về mục lục](README.md) · [Thứ tự nhập dữ liệu](03_THU_TU_KHOI_TAO_DU_LIEU.md) · [Tra cứu từng trường](12_FIELD_REFERENCE.md) · [Bản đồ phụ thuộc](13_DEPENDENCY_MATRIX.md)

Tài liệu này mô tả 11 mục trong menu **DỮ LIỆU DANH MỤC** theo source hiện tại ngày 09/10/2026. Nhãn **[HỆ THỐNG HIỆN TẠI]** chỉ hành vi đã có; **[VÍ DỤ NGHIỆP VỤ]** là dữ liệu minh họa để người học tự nhập; **[DEMO]** chỉ dữ liệu đã được định nghĩa trong bộ mẫu của dự án. Không coi ví dụ là bản ghi đã tồn tại trong dữ liệu của doanh nghiệp.

## 1. Bắt đầu và cách thao tác chung

Các danh mục cung cấp mã, đơn vị, cấu trúc sản phẩm và nguồn giá cho các bước tính tiếp theo. Tạo được danh mục chưa đồng nghĩa đã đủ điều kiện tính giá: chẳng hạn một báo giá lưu thành công ở **Nháp** vẫn chưa được bộ tính giá chọn.

| Menu | Đường dẫn danh sách | Nút lưu đúng trên form | Cần có trước khi tạo |
|---|---|---|---|
| Phần tử chi phí | `/master-data/cost-elements/` | Lưu phần tử chi phí | Tiền tệ nếu loại Tiền tệ; đơn vị nếu loại Số lượng |
| Nhóm sản phẩm | `/product/categories/` | Lưu nhóm sản phẩm | Không có danh mục bắt buộc |
| Vật tư / Hàng hóa | `/product/items/` | Lưu vật tư / hàng hóa | Đơn vị cơ sở |
| Sản phẩm | `/product/products/` | Lưu sản phẩm | Đơn vị tính giá thành |
| SKU | `/product/skus/` | Lưu SKU | Sản phẩm, đơn vị bán, đơn vị lượng tịnh |
| Tiền tệ | `/master-data/currencies/` | Lưu tiền tệ | Không có danh mục bắt buộc |
| Nhóm đơn vị tính | `/master-data/uom-categories/` | Lưu nhóm đơn vị tính | Không có danh mục bắt buộc |
| Đơn vị tính | `/master-data/uoms/` | Lưu đơn vị tính | Nhóm đơn vị tính |
| Quy đổi đơn vị tính | `/master-data/uom-conversions/` | Lưu quy đổi đơn vị tính | Hai đơn vị khác nhau; Item nếu quy đổi riêng |
| Nhà cung cấp | `/master-data/suppliers/` | Lưu nhà cung cấp | Tiền tệ chỉ cần nếu khai báo mặc định |
| Giá nhà cung cấp | `/master-data/supplier-prices/` | Lưu giá nhà cung cấp | Nhà cung cấp, Item, đơn vị giá, tiền tệ |

Mỗi mục có trang danh sách, tạo mới, chi tiết và chỉnh sửa. Chọn **+ Thêm mới**, điền form, nhấn nút **Lưu …** tương ứng. Thành công sẽ mở chi tiết và hiện thông báo **Đã tạo …**. Từ danh sách chọn **Xem chi tiết** hoặc **Chỉnh sửa**; từ chi tiết chọn **Chỉnh sửa**, sau đó **Lưu …** để nhận thông báo **Đã cập nhật …**. **Hủy** trở về danh sách nếu đang tạo, trở về chi tiết nếu đang sửa.

Nếu form không hợp lệ, trang giữ nội dung đã nhập và chỉ rõ trường lỗi. Có phần thông báo **Không thể lưu …**; sửa các trường được chỉ ra rồi lưu lại. ID và thời điểm tạo do hệ thống ghi, không nhập trên form. Không có thao tác xóa danh mục. Với danh mục có ô **Đang hoạt động**, bỏ chọn rồi lưu để ngừng dùng; khi sửa một bản đang hoạt động, hộp **Ngừng hoạt động danh mục** yêu cầu **Xác nhận và lưu**. Có thể tích lại để hoạt động trở lại.

Dropdown tạo mới chỉ cho chọn tham chiếu đang hoạt động. Khi sửa, tham chiếu cũ đã ngừng hoạt động vẫn có thể giữ nguyên, thường có hậu tố **(ngừng hoạt động)**; không được chọn mới một tham chiếu ngừng hoạt động khác. Lưu được bản ghi cũ với tham chiếu ngừng hoạt động không bảo đảm chạy Costing mới được: bộ tính kiểm tra nguồn đang hoạt động.

Danh sách dùng **Tìm kiếm**, các dropdown bộ lọc, **Lọc**, **Đặt lại**, **Sắp xếp**, **Mỗi trang**, **Trước**, **Sau**. Tìm kiếm theo một cụm ký tự nằm trong các trường được nêu dưới đây, không phân biệt hoa/thường. Sau khoảng 400 ms ngừng gõ, bảng tự cập nhật; đổi dropdown cũng cập nhật bảng. URL giữ điều kiện để quay lại hoặc chia sẻ. Có thể nhấn **Lọc**. **Mỗi trang** cho chọn 25, 50 hoặc 100, mặc định 25. Chọn **Sắp xếp** hoặc tiêu đề cột có liên kết để tăng/giảm. Khi không có kết quả, bảng hiện **Không có kết quả phù hợp.** và **Xóa bộ lọc**; khi chưa có dữ liệu, bảng báo **Chưa có …**.

Số trên danh sách/chi tiết dùng dấu phân cách Việt Nam, chẳng hạn `130.000,25`. Khi nhập số thập phân, dùng dấu chấm như `130000.25`, không chèn dấu phân cách hàng nghìn. Ngày được trình bày theo ngày/tháng/năm; ô lịch có thể theo thiết lập trình duyệt. Checkbox là lựa chọn Có/Không, được phép bỏ tích; các ô số có giá trị mặc định vẫn cần giữ hoặc nhập giá trị khi lưu.

## 2. Tiền tệ

**Dùng để làm gì?** Xác định đồng tiền của phần tử chi phí, báo giá, đơn giá nguồn lực, lần tính giá thành, tỷ giá và kịch bản giá bán. Thêm USD vào danh mục không tự tạo tỷ giá.

**Trước khi nhập:** chuẩn bị mã và tên; không cần danh mục khác. Vào **DỮ LIỆU DANH MỤC → Tiền tệ → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Mã tiền tệ | Bắt buộc, đúng 3 ký tự, bỏ khoảng trắng đầu/cuối và chuyển chữ hoa khi tạo; không trùng mã hiện có. Không có kiểm tra danh sách ISO; nên dùng mã nghiệp vụ thống nhất như VND/USD. Khi sửa, mã bị khóa. |
| Tên | Bắt buộc, tối đa 100 ký tự; ví dụ Việt Nam đồng. |
| Số chữ số thập phân | Bắt buộc, số nguyên 0–8; mặc định 2. Có thể đặt VND là 0 theo cách doanh nghiệp trình bày. Không tự suy ra quy tắc làm tròn thương mại cho Pricing. |
| Đang hoạt động | Mặc định tích; bỏ tích để ngừng xuất hiện trong lựa chọn mới. |

**Thực hành thành công:** nhập `VND`, `Việt Nam đồng`, `0`, giữ **Đang hoạt động**, nhấn **Lưu tiền tệ**. Nếu VND đã tồn tại, dùng bản hiện có. **Lỗi thử:** mã `VN` không đủ 3 ký tự; `decimal places = 9` vượt phạm vi. Sửa về mã 3 ký tự và số 0–8.

**Tìm và kiểm tra:** tìm theo mã/tên; lọc **Trạng thái**; sắp xếp Mã/Tên/Số chữ số thập phân, hai chiều; mặc định Mã tăng. Chi tiết hiển thị mã, tên, số chữ số thập phân và trạng thái.

**Ảnh hưởng xuôi:** đổi tên hoặc ngừng tiền tệ ảnh hưởng danh sách lựa chọn và nguồn dùng cho tính mới. Không đổi mã được. Snapshot của lần tính/kịch bản đã lưu không tính lại theo tên hoặc thiết lập mới.

## 3. Nhóm đơn vị tính

Nhóm đơn vị tính gom những đơn vị cùng loại đại lượng. Ví dụ nhóm Khối lượng chứa kg và g; nhóm Thời gian chứa giờ và phút. Cần tạo nhóm trước đơn vị.

Vào **DỮ LIỆU DANH MỤC → Nhóm đơn vị tính → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Mã nhóm | Bắt buộc, tối đa 50 ký tự, chuẩn hóa chữ hoa, duy nhất; ví dụ `MASS`. |
| Tên | Bắt buộc, tối đa 150 ký tự; ví dụ Khối lượng. |
| Mã đại lượng | Bắt buộc, tối đa 50 ký tự, chuẩn hóa chữ hoa; là văn bản nhập trực tiếp. Dùng `MASS` cho khối lượng, `LENGTH` cho chiều dài, `TIME` cho thời gian, `COUNT` cho số lượng khi phù hợp. |
| Mô tả | Tùy chọn, văn bản nhiều dòng. |
| Đang hoạt động | Mặc định tích. |

**Thành công:** tạo `MASS / Khối lượng / MASS`, nhấn **Lưu nhóm đơn vị tính**, rồi chuyển sang Đơn vị tính. **Không hợp lệ:** mã nhóm đã tồn tại hoặc bỏ trống mã đại lượng. Kiểm tra danh sách, dùng mã khác hoặc hoàn thiện đại lượng.

**Tìm và kiểm tra:** tìm mã/tên/mã đại lượng; lọc **Trạng thái**; sắp xếp Mã/Tên/Mã đại lượng, mặc định Mã tăng.

**Ảnh hưởng xuôi:** nhóm và đại lượng quyết định lựa chọn đơn vị trọng lượng/kích thước của Item và đơn vị thời gian công đoạn. Đổi `MASS`, `LENGTH`, `TIME` tùy tiện có thể làm cấu hình đang có không hợp lệ khi dùng lần sau. Không có chuyển đổi đơn vị tự phát sinh từ mã đại lượng.

## 4. Đơn vị tính

Đơn vị tính trả lời “bao nhiêu theo đơn vị nào”. `0.5 kg`, `20 gói`, `2 giờ` là ba đại lượng khác nhau. Chọn đơn vị trong danh mục chỉ ghi liên kết; muốn đổi kg ↔ g phải có quy đổi tương ứng.

**Trước khi nhập:** cần Nhóm đơn vị tính đang hoạt động. Vào **DỮ LIỆU DANH MỤC → Đơn vị tính → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Nhóm đơn vị tính | Bắt buộc, chọn từ Nhóm đơn vị tính. |
| Mã đơn vị | Bắt buộc, tối đa 50 ký tự, chuẩn hóa chữ hoa, duy nhất; ví dụ `KG`. |
| Tên | Bắt buộc, tối đa 150 ký tự; ví dụ Kilôgam. |
| Ký hiệu | Bắt buộc, tối đa 30 ký tự; ví dụ `kg`. Không tự chuyển ký hiệu thành chữ hoa. |
| Độ chính xác | Bắt buộc, số nguyên 0–12; mặc định 6. |
| Đơn vị cơ sở | Mặc định không tích. Là cờ mô tả; hệ thống không buộc chỉ có một đơn vị cơ sở trong nhóm. |
| Đang hoạt động | Mặc định tích. |

**Thành công:** chọn nhóm MASS, nhập `KG / Kilôgam / kg / 6`, tích **Đơn vị cơ sở**, nhấn **Lưu đơn vị tính**. Làm tương tự với `G / Gam / g`. **Không hợp lệ:** độ chính xác 13 hoặc thiếu nhóm/ký hiệu. Nếu đổi nhóm của đơn vị làm một quy đổi chung đang có thành khác nhóm, hệ thống yêu cầu điều chỉnh quy đổi trước.

**Tìm và kiểm tra:** tìm mã/tên/ký hiệu; lọc **Nhóm đơn vị tính**, **Đơn vị cơ sở**, **Trạng thái**; sắp xếp Mã/Tên/Nhóm đơn vị tính/Độ chính xác, mặc định Mã tăng.

**Ảnh hưởng xuôi:** đơn vị được dùng ở Item, Product, SKU, báo giá, BOM, bao bì, công đoạn, nguồn lực, phân bổ, phần tử chi phí và Run. Ngừng đơn vị đang tham chiếu có thể chặn tính mới; không sửa snapshot cũ. Không có thao tác đổi toàn bộ số lượng hiện có sang đơn vị mới.

## 5. Quy đổi đơn vị tính

Quy đổi xác định **giá trị đích = giá trị nguồn × hệ số**. [VÍ DỤ NGHIỆP VỤ] `G → KG`, hệ số `0.001`: `200 g × 0.001 = 0.2 kg`; báo giá `100000 VND/kg` tương ứng `20000 VND` cho lượng nguyên liệu này trước các điều chỉnh BOM khác.

**Trước khi nhập:** tạo hai đơn vị khác nhau. Nếu là quy đổi riêng như số kg trong một bao của một Item, tạo Item trước. Vào **DỮ LIỆU DANH MỤC → Quy đổi đơn vị tính → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Đơn vị nguồn | Bắt buộc, chọn đơn vị đang hoạt động. |
| Đơn vị đích | Bắt buộc, khác nguồn. |
| Hệ số quy đổi | Bắt buộc, số thập phân > 0, tối đa 24 chữ số tổng cộng/12 chữ số thập phân. |
| Vật tư / Hàng hóa | Tùy chọn. Để trống: quy đổi chung, hai đơn vị phải cùng nhóm. Chọn Item: quy đổi riêng, có thể khác nhóm. |
| Hiệu lực từ ngày | Bắt buộc, mặc định hôm nay. |
| Hiệu lực đến ngày | Tùy chọn, bỏ trống nghĩa không giới hạn; nếu nhập phải sau ngày bắt đầu. |
| Nguồn tham chiếu | Tùy chọn, ghi căn cứ đo/quy cách; ví dụ Quy cách đóng bao 25 kg. |

**Thành công:** chọn G → KG, nhập `0.001`, để trống Item, chọn ngày bắt đầu, nhấn **Lưu quy đổi đơn vị tính**. **Không hợp lệ:** hệ số 0; nguồn bằng đích; hoặc đổi KG → L mà không chọn Item. Đổi nguồn/đích đúng và cung cấp Item nếu quy đổi mang tính riêng theo hàng hóa.

**Tìm và kiểm tra:** tìm mã/tên đơn vị nguồn/đích hoặc Item; lọc **Đơn vị nguồn**, **Đơn vị đích**, **Vật tư / Hàng hóa**; sắp xếp Ngày bắt đầu/Đơn vị nguồn/Đơn vị đích, mặc định ngày bắt đầu giảm. Không có cờ Đang hoạt động và không có bộ lọc ngày hiệu lực trên màn hình này. Quy đổi dùng chung đã có từ nguồn thiết lập hệ thống được xem; nút chỉnh sửa chỉ có cho bản thuộc phạm vi dữ liệu hiện tại.

**Hiệu lực và Costing:** khoảng tính Costing gồm cả ngày đầu và ngày cuối. Bộ tính dùng một cặp trực tiếp hoặc đảo chiều bằng `1 / hệ số`; không ghép chuỗi G → KG → Tấn. Nếu nhiều bản phù hợp đồng thời, kể cả chung + riêng hoặc hai chiều, bộ tính báo mơ hồ; không tự ưu tiên bản riêng. Không nên tạo thêm bản nghịch đảo nếu một bản hiện có đã đủ dùng cho Costing. Màn hình lưu quy đổi chưa chặn trùng/chồng thời gian.

**Ảnh hưởng xuôi:** BOM/bao bì kiểm tra khả năng quy đổi khi cấu hình; Run mới dùng hệ số đúng ngày và ghi vào trace/snapshot. Thay hệ số không sửa Run cũ. Nếu đổi hệ số theo kỳ, thêm bản có ngày mới và kết thúc kỳ cũ trước ngày mới, tránh trùng ngày biên.

## 6. Nhóm sản phẩm

Nhóm sản phẩm phân loại Item và Product; trong Pricing, quy tắc phí theo nhóm xét nhóm của Product. Nhóm sản phẩm khác Nhóm đơn vị tính và khác Nhóm chi phí chung.

Vào **DỮ LIỆU DANH MỤC → Nhóm sản phẩm → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Mã | Bắt buộc, tối đa 100 ký tự, chuẩn hóa chữ hoa, không trùng; ví dụ `COFFEE`. |
| Tên nhóm sản phẩm | Bắt buộc, tối đa 255 ký tự; ví dụ Cà phê. |
| Mô tả | Tùy chọn, nhiều dòng. |
| Đang hoạt động | Mặc định tích. |

**Thành công:** nhập `COFFEE / Cà phê`, nhấn **Lưu nhóm sản phẩm**. **Không hợp lệ:** mã ` coffee ` trùng COFFEE sẽ bị từ chối sau chuẩn hóa. Tìm bản đã có hoặc đổi mã.

**Tìm và kiểm tra:** tìm mã/tên/mô tả; lọc **Trạng thái**; sắp xếp Mã/Tên/Ngày tạo, mặc định Mã tăng. Form không có trường nhóm cha; giao diện hiện tại quản lý danh sách phẳng.

**Ảnh hưởng xuôi:** đổi nhóm gắn vào Product có thể thay đổi quy tắc phí theo nhóm của kịch bản mới. Item và Product có thể chọn nhóm độc lập; không tự đồng bộ qua liên kết Item đầu ra. Snapshot đã tính không tự thay đổi.

## 7. Phân biệt Item, Product và SKU

| Khái niệm | Hiểu trong công việc | Ví dụ | Liên kết thực tế |
|---|---|---|---|
| Vật tư / Hàng hóa (Item) | Thứ mua, tiêu hao hoặc ghi nhận như hàng hóa/dịch vụ | Cà phê hòa tan, đường, túi sachet, hộp giấy | Có đơn vị cơ sở; dùng ở BOM, bao bì, báo giá |
| Sản phẩm (Product) | Sản phẩm gốc cần tổ chức định mức và tính giá | Cappuccino | Có đơn vị tính giá thành; BOM/bao bì/quy trình gắn Product |
| SKU | Mã bán cụ thể thuộc một Product | Cappuccino hộp 20 gói, lượng tịnh 0.5 kg/hộp | Bắt buộc Product; có đơn vị bán và lượng tịnh; gán bao bì ở module Cấu hình bao bì |

Product có **Vật tư / Hàng hóa đầu ra** tùy chọn; SKU có **Vật tư / Hàng hóa bán** tùy chọn. Đây là các liên kết tới Item đã có. Tạo Product hoặc SKU không tự tạo Item, BOM, bao bì, quy đổi hoặc báo giá. Không có yêu cầu bắt buộc tạo Item đầu ra trước Product.

## 8. Vật tư / Hàng hóa

**Khi dùng:** khai báo nguyên liệu, bao bì, bán thành phẩm, thành phẩm, dịch vụ hoặc phụ phẩm trước khi gắn vào định mức/báo giá. **Trước khi nhập:** tối thiểu một Đơn vị tính đang hoạt động; nên có Nhóm sản phẩm. Vào **DỮ LIỆU DANH MỤC → Vật tư / Hàng hóa → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Nhóm sản phẩm | Tùy chọn, chọn nhóm hiện có. |
| Mã | Bắt buộc, tối đa 120 ký tự, chữ hoa sau chuẩn hóa, duy nhất; ví dụ `RM_COFFEE`. |
| Tên | Bắt buộc, tối đa 255 ký tự; ví dụ Cà phê hòa tan. |
| Loại vật tư / hàng hóa | Bắt buộc: Nguyên liệu, Bao bì, Bán thành phẩm, Thành phẩm, Dịch vụ, Phụ phẩm. Chọn đúng mục đích sử dụng. |
| Đơn vị cơ sở | Bắt buộc; đơn vị chuẩn mô tả Item. |
| Đơn vị mua | Tùy chọn; không tự sinh quy đổi với đơn vị cơ sở. |
| Đơn vị sản xuất | Tùy chọn; không tự sinh quy đổi. |
| Mã nhóm thuế | Tùy chọn, văn bản tối đa 100 ký tự; không phải dropdown thuế và không tự tính thuế mua. |
| Khối lượng tịnh | Tùy chọn, số ≥ 0. Nhập kể cả 0 thì cần đơn vị trọng lượng. |
| Khối lượng tổng | Tùy chọn, số ≥ 0; nếu cùng nhập khối lượng tịnh thì không được nhỏ hơn tịnh. |
| Đơn vị trọng lượng | Tùy chọn khi không có khối lượng; bắt buộc khi đã nhập ít nhất một khối lượng; chỉ đơn vị thuộc đại lượng MASS. |
| Chiều dài | Tùy chọn, số ≥ 0. |
| Chiều rộng | Tùy chọn, số ≥ 0. |
| Chiều cao | Tùy chọn, số ≥ 0. |
| Đơn vị kích thước | Tùy chọn khi không có kích thước; bắt buộc nếu đã nhập ít nhất một kích thước; chỉ đại lượng LENGTH. |
| Theo dõi tồn kho | Mặc định tích; đây là thông tin phân loại, không tạo giao dịch nhập/xuất kho. |
| Đang hoạt động | Mặc định tích. |

Các số đo cho phép tối đa 24 chữ số tổng cộng, 8 chữ số thập phân. Các nhóm trường luôn hiển thị; không có tự ẩn/hiện theo loại hoặc số đo. Backend kiểm tra điều kiện bắt buộc sau khi lưu.

**Thành công:** nhập mã RM_COFFEE, tên Cà phê hòa tan, loại **Nguyên liệu**, đơn vị cơ sở KG; để các số đo trống nếu không cần, nhấn **Lưu vật tư / hàng hóa**. Tiếp theo tạo báo giá và thêm Item vào BOM. **Không hợp lệ:** nhập tịnh 1, tổng 0.8 hoặc nhập chiều dài 10 mà không chọn đơn vị kích thước; chỉnh tổng ≥ tịnh và chọn đơn vị LENGTH.

**Tìm và kiểm tra:** tìm mã/tên; lọc **Nhóm sản phẩm**, **Loại**, **Đơn vị cơ sở**, **Hàng tồn kho**, **Trạng thái**; sắp xếp Mã/Tên/Loại/Ngày tạo, mặc định Mã tăng. Chi tiết đọc các nhóm thông tin chung, đơn vị, thuế, trọng lượng, kích thước, quản lý, ngày tạo/cập nhật.

**Ảnh hưởng xuôi:** Item nối báo giá, BOM, dòng bao bì, quy đổi riêng và các liên kết Item của Product/SKU. Đổi tên/loại/đơn vị không tự viết lại các dòng đã cấu hình. Kiểm tra định mức và quy đổi trước Run mới. Loại Dịch vụ/Phụ phẩm là danh mục đã có; không đồng nghĩa phần mềm tự lập hóa đơn dịch vụ hoặc tính giá thành liên sản phẩm/phân bổ phụ phẩm.

## 9. Sản phẩm

**Khi dùng:** tạo đầu mối cho BOM, bao bì, quy trình, SKU và Run. **Trước khi nhập:** có Đơn vị tính; Nhóm sản phẩm và Item đầu ra tùy chọn. Vào **DỮ LIỆU DANH MỤC → Sản phẩm → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Nhóm sản phẩm | Tùy chọn. Được dùng khi Pricing tìm phí theo nhóm Product. |
| Mã sản phẩm | Bắt buộc, tối đa 120 ký tự, chuẩn hóa chữ hoa, không trùng; ví dụ `CAPPUCCINO`. |
| Tên sản phẩm | Bắt buộc, tối đa 255 ký tự. |
| Mô tả | Tùy chọn. |
| Đơn vị tính giá thành | Bắt buộc; ví dụ Hộp nếu kết quả tính trên hộp. |
| Vật tư / Hàng hóa đầu ra | Tùy chọn, chọn Item có sẵn; không tự tạo mới. |
| Mã nhóm thuế | Tùy chọn, tối đa 100 ký tự; chưa phải lựa chọn tự động quy tắc thuế bán hàng. |
| Đang hoạt động | Mặc định tích. |

**Thành công:** nhập CAPPUCCINO, tên Cappuccino, chọn đơn vị tính giá thành Hộp, nhấn **Lưu sản phẩm**; chuyển sang SKU hoặc BOM. **Không hợp lệ:** thiếu đơn vị tính giá thành sẽ nhận **Vui lòng chọn đơn vị tính giá thành.**; vào Đơn vị tính nếu danh sách chưa có đơn vị cần dùng. Mã trùng sẽ nhận **Mã sản phẩm đã tồn tại.**

**Tìm và kiểm tra:** tìm mã/tên/mô tả; lọc **Nhóm sản phẩm**, **Đơn vị tính giá thành**, **Trạng thái**; sắp xếp Mã/Tên/Nhóm sản phẩm/Ngày tạo, mặc định Mã tăng. Chi tiết hiển thị thông tin chung, đơn vị, liên kết và thuế, thời điểm tạo/cập nhật. Để xem SKU của sản phẩm, mở menu **SKU** rồi chọn bộ lọc **Sản phẩm**.

**Ảnh hưởng xuôi:** sửa Product thay đổi cấu hình mà lần tính mới có thể đọc. BOM, bao bì và quy trình vẫn là các bản ghi riêng, không tự điều chỉnh đơn vị/số lượng theo thao tác sửa Product. Product không có phiên bản; lịch sử tái lập nằm trong snapshot của Run và các phiên bản nguồn.

## 10. SKU

**Khi dùng:** nhiều quy cách bán của cùng Product hoặc cần tính phí/bao bì theo mã bán cụ thể. **Trước khi nhập:** Product, đơn vị bán và đơn vị lượng tịnh đang hoạt động. Vào **DỮ LIỆU DANH MỤC → SKU → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Sản phẩm | Bắt buộc, chọn Product hiện có. |
| Mã SKU | Bắt buộc, tối đa 150 ký tự, chuẩn hóa chữ hoa, duy nhất; ví dụ `CAP_BOX20`. |
| Tên SKU | Bắt buộc, tối đa 255 ký tự; ví dụ Cappuccino hộp 20 gói. |
| Mã vạch | Tùy chọn, tối đa 100 ký tự, bỏ khoảng trắng đầu/cuối nhưng giữ hoa/thường; nếu có phải duy nhất. Nhiều SKU được để trống. |
| Đơn vị bán | Bắt buộc; ví dụ Hộp. |
| Lượng tịnh | Bắt buộc, số > 0, tối đa 24 chữ số/8 chữ số thập phân; ví dụ `0.5`. |
| Đơn vị lượng tịnh | Bắt buộc; ví dụ kg. Có thể là khối lượng, thể tích hoặc số lượng, không giới hạn MASS. |
| Vật tư / Hàng hóa bán | Tùy chọn, liên kết Item đã có. |
| Đang hoạt động | Mặc định tích. |

**Thành công:** chọn Product Cappuccino, nhập CAP_BOX20, tên quy cách, đơn vị bán Hộp, lượng tịnh `0.5`, đơn vị lượng tịnh kg, nhấn **Lưu SKU**. Sau đó vào Cấu hình bao bì để gán SKU; không tìm trường bao bì trên form SKU. **Không hợp lệ:** lượng tịnh 0 nhận **Lượng tịnh phải lớn hơn 0.**; mã vạch trùng nhận **Mã vạch đã tồn tại.**

**Tìm và kiểm tra:** tìm mã/tên SKU hoặc mã/tên Product, không tìm theo mã vạch; lọc **Sản phẩm**, **Nhóm sản phẩm** của Product, **Trạng thái**; sắp xếp Mã SKU/Tên SKU/Sản phẩm/Ngày tạo, mặc định Mã SKU tăng. Form SKU không có dropdown phụ thuộc để tự nạp Item theo Product; chọn Product không tự điền Item bán hoặc lượng tịnh.

**Ảnh hưởng xuôi:** lượng tịnh có thể được Costing dùng để đổi số đơn vị bán sang lượng sản phẩm khi đại lượng của định mức yêu cầu; không phải mọi BOM đều nhân lượng tịnh. Bộ tính áp dụng nhánh theo đơn vị/đại lượng. SKU còn liên quan gán bao bì, phí kênh riêng và nhóm so sánh kịch bản. Thay quy cách bán cần kiểm tra cả BOM/bao bì/quy đổi trước lần tính mới; Run/kịch bản cũ giữ snapshot.

## 11. Nhà cung cấp

**Khi dùng:** khai báo nguồn báo giá của Item. Nhà cung cấp không bắt buộc có Item liên quan trước khi tạo. Vào **DỮ LIỆU DANH MỤC → Nhà cung cấp → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Mã nhà cung cấp | Bắt buộc, tối đa 120 ký tự, chuẩn hóa chữ hoa, duy nhất; ví dụ `SUP_COFFEE`. |
| Tên nhà cung cấp | Bắt buộc, tối đa 255 ký tự. |
| Mã số thuế | Tùy chọn, tối đa 100 ký tự; không có kiểm tra cấu trúc mã số thuế theo pháp luật trong form. |
| Tiền tệ mặc định | Tùy chọn, chọn danh mục Tiền tệ. |
| Điều khoản thanh toán | Tùy chọn, nhiều dòng; ví dụ Thanh toán trong 30 ngày. |
| Đang hoạt động | Mặc định tích. |

**Thành công:** nhập SUP_COFFEE, tên nhà cung cấp, chọn VND nếu cần, nhấn **Lưu nhà cung cấp**, rồi tạo Giá nhà cung cấp. **Không hợp lệ:** mã trùng sau bỏ khoảng trắng/chuyển chữ hoa; dùng nhà cung cấp đã có hoặc đổi mã. Form hiện không có địa chỉ, điện thoại, email, quốc gia.

**Tìm và kiểm tra:** tìm mã/tên/mã số thuế; lọc **Trạng thái**, **Tiền tệ mặc định**; sắp xếp Mã/Tên nhà cung cấp/Ngày tạo, mặc định Mã tăng. Chi tiết gồm thông tin giao dịch và ngày tạo/cập nhật.

**Ảnh hưởng xuôi:** ngừng nhà cung cấp khiến bộ tính không chọn báo giá của họ cho Run mới. Báo giá đã lưu vẫn xem được. Tiền tệ mặc định là thông tin giao dịch; chọn nhà cung cấp trên form giá không tự điền tiền tệ của báo giá.

## 12. Giá nhà cung cấp

**Dùng để làm gì?** Lưu đơn giá của một Item theo nhà cung cấp, đơn vị báo giá, tiền tệ, số lượng tối thiểu và khoảng thời gian. Đây là nguồn giá mua cho Costing khi đủ điều kiện. Không phải giá bán cho khách hàng.

**Trước khi nhập:** cần Nhà cung cấp, Item, Đơn vị tính, Tiền tệ đang hoạt động. Vào **DỮ LIỆU DANH MỤC → Giá nhà cung cấp → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Nhà cung cấp | Bắt buộc. |
| Vật tư / Hàng hóa | Bắt buộc. |
| Đơn giá | Bắt buộc, số ≥ 0, tối đa 24 chữ số/8 chữ số thập phân; giá 0 được lưu. |
| Tiền tệ | Bắt buộc; không tự lấy từ Nhà cung cấp. |
| Đơn vị tính | Bắt buộc, đúng đơn vị trên báo giá; không tự quy đổi về đơn vị cơ sở của Item. |
| Số lượng tối thiểu | Bắt buộc, mặc định 0, số ≥ 0, tối đa 24 chữ số/8 chữ số thập phân; tính theo đơn vị báo giá. |
| Đơn giá đã gồm thuế | Mặc định không tích. Lưu mô tả báo giá; không tự tách thuế mua. |
| Tỷ lệ thuế | Tùy chọn, từ 0 đến 1, tối đa 8 chữ số thập phân; nhập `0.1` cho 10%. |
| Tỷ lệ thuế được khấu trừ | Bắt buộc, mặc định 1, từ 0 đến 1, tối đa 8 chữ số thập phân; 1 là khấu trừ toàn bộ. |
| Hiệu lực từ ngày | Bắt buộc, mặc định hôm nay. |
| Hiệu lực đến ngày | Tùy chọn; nếu nhập phải sau ngày bắt đầu. |
| Nguồn dữ liệu | Tùy chọn, văn bản tối đa 50 ký tự; ví dụ Báo giá. Không có danh sách loại nguồn cố định. |
| Tham chiếu / Số báo giá | Tùy chọn, nhiều dòng; ví dụ BG-2026-101. |

Nhóm Thuế luôn hiển thị; đánh dấu đã gồm thuế không tự ẩn/hiện hoặc bắt buộc tỷ lệ thuế. Form có thể lưu cấu hình thuế mà Costing chưa xử lý được.

**Thành công khi lưu:** chọn SUP_COFFEE / RM_COFFEE, giá `100000`, tiền VND, đơn vị KG, tối thiểu `0`, không tích đã gồm thuế, để tỷ lệ thuế trống, giữ khấu trừ `1`, bắt đầu `01/01/2026`, nhấn **Lưu giá nhà cung cấp**. Bản mới hiển thị **Nháp**. Nếu thiếu Item/nhà cung cấp/tiền tệ/đơn vị, bổ sung danh mục đó rồi tạo lại. Giá âm, tỷ lệ `10` thay vì `0.1`, ngày kết thúc bằng ngày bắt đầu đều không hợp lệ.

### 12.1. Hai loại trạng thái cần đọc riêng

Chi tiết và danh sách hiển thị **Trạng thái bản ghi** cùng **Hiệu lực theo ngày**. Hiệu lực theo ngày được tính từ hôm nay: trước ngày bắt đầu là **Sắp hiệu lực**, sau ngày cuối là **Hết hiệu lực**, còn lại **Đang hiệu lực**. Ngày cuối vẫn được tính. Vì vậy một giá **Nháp** có thể đồng thời có badge ngày **Đang hiệu lực**.

**[CHƯA HỖ TRỢ]** UI hiện không có nút chuyển báo giá Nháp thành nguồn đang hiệu lực, và không cho nhập trạng thái trên form. Lưu mới luôn Nháp; sửa giữ trạng thái cũ. Bộ tính chỉ chọn trạng thái nguồn `EFFECTIVE`. Do đó tạo mới toàn bộ dữ liệu chỉ bằng các form hiện tại chưa hoàn tất được chuỗi nguồn giá mua để chạy Costing. Cần bộ nguồn đã được thiết lập hợp lệ; ghi nhận yêu cầu hoàn thiện thao tác thiết lập nguồn với người quản lý hệ thống. Không có bước duyệt giá dành cho người dùng. Câu nhắc cũ có từ “duyệt” trên form không cung cấp thêm chức năng.

### 12.2. Khi giá đổi theo kỳ

[VÍ DỤ NGHIỆP VỤ] Giá 100000 VND/kg từ 01/01/2026 đến 30/06/2026; giá 110000 từ 01/07/2026. Ngày 30/06 dùng kỳ đầu, ngày 01/07 dùng kỳ sau nếu cả hai là nguồn hợp lệ cho Costing. Thêm bản ghi mới cho kỳ mới và kết thúc kỳ cũ; không sửa đè giá cũ nếu cần giữ bảng lịch sử mua rõ ràng. **Chỉnh sửa** sẽ thay đổi chính bản giá đang mở; không tạo phiên bản giá và không sửa các bản giá kỳ khác.

Màn hình không chặn nhiều giá trùng/chồng hiệu lực hoặc nhiều nhà cung cấp cùng phù hợp. Bộ tính yêu cầu đúng một giá phù hợp sau đổi lượng sang đơn vị giá, so số lượng tối thiểu và tiền tệ; không tự chọn giá thấp nhất, nhà cung cấp ưu tiên hoặc bậc số lượng cao nhất. Nếu hai ngưỡng tối thiểu đều đạt, có thể phát sinh **AMBIGUOUS_PRICE**.

### 12.3. Các giới hạn khi dùng cho Costing

| Điều kiện | Kết quả thực tế và xử lý |
|---|---|
| Giá Nháp dù ngày hợp lệ | Không nằm trong nguồn bộ tính; đọc trạng thái bản ghi riêng với badge ngày. Chưa có thao tác chuyển nguồn trong UI. |
| Tiền tệ báo giá khác tiền tệ Run | Báo `MISSING_FX`; tỷ giá trong Pricing không tự quy đổi giá mua ở Costing. Cần nguồn giá cùng tiền tệ kết quả hoặc ghi nhận nhu cầu chưa hỗ trợ. |
| Tích đã gồm thuế hoặc tỷ lệ thuế khác 0 | Bộ tính báo `UNSUPPORTED_TAX`; chưa có xử lý thuế mua hàng. Không xóa thông tin thuế thực chỉ để vượt lỗi. |
| Đơn vị BOM khác đơn vị giá | Cần đúng một quy đổi cặp phù hợp, có thể đảo chiều; không tự ghép chuỗi. |
| Không đạt số lượng tối thiểu | Giá không phù hợp; kiểm tra lượng thực tế theo đơn vị báo giá. |
| Nhiều giá cùng phù hợp | Báo `AMBIGUOUS_PRICE`; điều chỉnh kỳ/điều kiện nguồn để còn đúng một giá. |

**Tìm và kiểm tra:** tìm mã/tên nhà cung cấp hoặc Item; lọc **Nhà cung cấp**, **Vật tư / Hàng hóa**, **Tiền tệ**, **Đơn vị tính**, **Hiệu lực theo ngày**, **Trạng thái bản ghi**; sắp xếp Nhà cung cấp/Item/Đơn giá/Hiệu lực từ ngày, mặc định ngày bắt đầu giảm. Không có filter chọn một ngày quá khứ cụ thể; badge hiệu lực theo ngày phản ánh hôm nay, còn Run xét ngày tính của Run.

**Ảnh hưởng xuôi:** Run mới có thể dùng giá/kỳ đã thay nếu thỏa điều kiện; Run cũ đọc kết quả, trace và snapshot đã lưu, không lấy lại giá hiện tại. Pricing dựa Run đã khóa và snapshot riêng, nên không cập nhật giá bán cũ chỉ vì đổi báo giá.

## 13. Phần tử chi phí

Phần tử chi phí là tên của một biến nghiệp vụ có kiểu và đơn vị rõ ràng, chẳng hạn chi phí nguyên liệu hoặc tổng giá thành. Nó trả lời **“giá trị này là gì?”**. Nó chưa phải phép tính, chưa phải nguồn giá và chưa phải một dòng kết quả đã thực hiện.

| Đối tượng | Vai trò | Ví dụ |
|---|---|---|
| Phần tử chi phí | Định nghĩa tên/kiểu/đơn vị của giá trị | Chi phí nguyên liệu, kiểu Tiền tệ/VND |
| Công thức | Cách kết hợp đầu vào ra kết quả | Nguyên liệu + Bao bì + Nguồn lực + Chi phí chung |
| Nhóm chi phí chung | Gom nguồn chi phí theo kỳ để phân bổ | Chi phí cố định nhà máy |
| Dòng phương án tính giá thành | Gán một phần tử với nguồn Hệ thống/Nhập thủ công/Công thức… | Phần tử nguyên liệu dùng resolver `MATERIAL_COST` |
| Dòng kết quả Run | Giá trị đã tính ở một lần chạy, kèm nguồn/trace | 260000 VND chi phí nguyên liệu của 10 hộp |

[DEMO] Sáu mã phần tử là `DEMO_MATERIAL_COST`, `DEMO_PACKAGING_COST`, `DEMO_RESOURCE_COST`, `DEMO_OVERHEAD_COST`, `DEMO_DIRECT_COST`, `DEMO_FULL_COST`. Mã resolver hệ thống là `MATERIAL_COST`, `PACKAGING_COST`, `RESOURCE_COST`, `RUN_QUANTITY`, `ALLOCATION:<mã quy tắc>`; mã phần tử và mã resolver không bắt buộc giống nhau. Máy/nhân công trong DEMO được đối soát trong trace nguồn lực; không có resolver riêng `MACHINE_COST` hay `LABOR_COST`.

[VÍ DỤ NGHIỆP VỤ] Có thể định nghĩa `TRANSPORT_COST`, nhưng tạo mã không làm hệ thống tự thu thập cước. Cần cấu hình nguồn được hỗ trợ, như nhập thủ công trong phương án hoặc công thức với đầu vào rõ ràng. `LOOKUP`/`EXTERNAL` xuất hiện trong dropdown từ điển nhưng chưa là nguồn thực thi được hỗ trợ khi kích hoạt phương án.

**Trước khi nhập:** Tiền tệ nếu giá trị là tiền, Đơn vị tính nếu là số lượng. **Nhóm chi phí** là tùy chọn; có dropdown các nhóm đã thiết lập nhưng không có màn hình CRUD Nhóm phần tử chi phí trong menu. Vào **DỮ LIỆU DANH MỤC → Phần tử chi phí → + Thêm mới**.

| Trường UI | Cách điền và quy tắc |
|---|---|
| Nhóm chi phí | Tùy chọn, nhóm phần tử chi phí đã có; khác Nhóm chi phí chung dùng phân bổ. |
| Mã | Bắt buộc, tối đa 120 ký tự, chuẩn hóa chữ hoa, duy nhất; dùng mã ổn định vì công thức có thể tham chiếu. |
| Tên | Bắt buộc, tối đa 255 ký tự; tên người dùng đọc. |
| Mô tả | Tùy chọn. |
| Loại giá trị | Bắt buộc: Tiền tệ, Số, Tỷ lệ phần trăm, Số lượng, Có / Không, Văn bản. |
| Đại lượng | Tùy chọn, văn bản tối đa 50 ký tự. Nếu có đơn vị mặc định và có nhập đại lượng, phải trùng đại lượng của nhóm đơn vị. Trường này không tự chuyển chữ hoa: nên nhập đúng mã như `MASS`. |
| Nguồn dữ liệu | Bắt buộc: Hệ thống, Nhập thủ công, Tra cứu, Công thức, Nguồn bên ngoài. Đây là mô tả mặc định; khả năng thực thi phụ thuộc dòng phương án. |
| Tiền tệ | Form cho để trống nhưng bắt buộc theo nghiệp vụ khi Loại giá trị = Tiền tệ. |
| Đơn vị tính mặc định | Form cho để trống nhưng bắt buộc khi Loại giá trị = Số lượng. |
| Số chữ số làm tròn | Bắt buộc, số nguyên 0–12, mặc định 6. |
| Phương pháp làm tròn | Bắt buộc: Làm tròn nửa lên, Làm tròn nửa về số chẵn, Ra xa số 0, Về phía số 0, Về phía dương vô cùng, Về phía âm vô cùng. |
| Phạm vi kế toán | Bắt buộc: Chi phí hàng tồn kho, Chi phí thương mại, Chỉ dùng cho giá bán, Phân tích. |
| Phạm vi chi phí | Bắt buộc: Sản xuất, Chi phí đến kho, Chi phí phục vụ, Kênh bán, Giá bán, Phân tích. |
| Dữ liệu nhạy cảm | Mặc định không tích; đánh dấu dữ liệu cần thận trọng khi chia sẻ. Không tạo phân quyền người dùng. |
| Đang hoạt động | Mặc định tích. |

Với các dropdown Loại giá trị/Nguồn/Phạm vi/Làm tròn, form không khai báo một giá trị ban đầu riêng; trình duyệt hiển thị lựa chọn đầu (Tiền tệ/Hệ thống/Chi phí hàng tồn kho/Sản xuất/Làm tròn nửa lên). Hãy chọn chủ động theo mục đích. Không có ẩn/hiện ô tiền tệ hoặc đơn vị theo loại; khi lưu, backend kiểm tra điều kiện tương ứng.

**Thành công ở bước danh mục:** tạo `TRANSPORT_COST / Chi phí vận chuyển`, Loại giá trị **Tiền tệ**, tiền VND, Nguồn dữ liệu **Nhập thủ công**, Phạm vi kế toán **Chi phí thương mại**, Phạm vi chi phí **Chi phí phục vụ**, làm tròn phù hợp; nhấn **Lưu phần tử chi phí**. **Cấu hình lưu được này chưa chạy trong Costing hiện tại:** phạm vi COST_TO_SERVE chưa có đường thực thi. Không đổi nhãn/phạm vi để vượt kiểm tra. Ví dụ tổng cước thực sự thuộc chi phí sản xuất được trình bày riêng ở bài 15 chương 08. **Không hợp lệ:** chọn Tiền tệ nhưng không chọn tiền sẽ nhận **Giá trị tiền tệ cần khai báo đơn vị tiền tệ.**; chọn Số lượng nhưng thiếu đơn vị nhận **Giá trị số lượng cần khai báo đơn vị tính.**

**Tìm và kiểm tra:** tìm mã/tên/mô tả; lọc **Nhóm chi phí**, **Loại giá trị**, **Nguồn dữ liệu**, **Phạm vi chi phí**, **Trạng thái**; sắp xếp Mã/Tên/Loại giá trị/Ngày tạo, mặc định Mã tăng. Chi tiết có **Thao tác khác → Thông tin bản ghi**, mở ngăn bên hiển thị ngày tạo/cập nhật. Đây không phải lịch sử thay đổi nghiệp vụ.

**Ảnh hưởng xuôi:** công thức tham chiếu `$MÃ_PHẦN_TỬ`; đổi mã có thể làm công thức mất biến ở lần kiểm tra/tính sau. Đổi kiểu/đơn vị/phạm vi không tự sửa công thức hoặc phương án. Phần tử không có phiên bản riêng; nên giữ mã ổn định, kiểm tra lại các công thức và phương án liên quan trước dùng Run mới. Snapshot Run/kịch bản cũ không tính lại.

## 14. Kiểm tra trước khi chuyển sang cấu hình sản xuất

1. Có đơn vị cho lượng nguyên liệu, sản lượng đầu ra, đơn vị bán, lượng tịnh, thời gian máy/nhân công.
2. Item nguyên liệu và bao bì tồn tại, đúng loại và đúng đơn vị; Product và SKU đã tách rõ.
3. Quy đổi cần dùng tồn tại đúng cặp/ngày; không có nhiều bản đồng thời phù hợp.
4. Báo giá đúng Item/đơn vị/tiền tệ/ngày/số lượng tối thiểu; kiểm tra riêng trạng thái nguồn với badge ngày và các giới hạn thuế/FX.
5. Phần tử chi phí chỉ định nghĩa biến; tiếp theo cần BOM/bao bì/quy trình và công thức/phương án phù hợp.

Các thao tác tạo/xem/sửa/lọc danh mục là **NATIVE**. Áp chi phí mới qua phần tử + nguồn thủ công/công thức/phương án là **CONFIGURABLE**. Tạo từ đầu toàn bộ nguồn giá mua và chạy Costing chỉ qua UI là **PARTIAL** do thiếu thao tác chuyển nguồn. Giao dịch kho, chọn nhà cung cấp tối ưu, ghép chuỗi quy đổi, tự xử lý thuế mua/FX mua và cây nhóm sản phẩm trên UI là **NOT SUPPORTED** hiện tại. Xem [GAP_REGISTER](GAP_REGISTER.md) trước khi thiết kế quy trình vận hành.

## 15. Nguồn đối chiếu

- [URL danh mục](../../apps/master_data/urls.py), [URL sản phẩm](../../apps/product/urls.py), [menu tiếng Việt](../../apps/master_data/navigation.py).
- [Forms danh mục](../../apps/master_data/forms.py), [Forms sản phẩm](../../apps/product/forms.py), [models](../../apps/core/models.py).
- [Validation danh mục](../../apps/master_data/validators.py), [validation sản phẩm](../../apps/product/validators.py), [ghi danh mục](../../apps/master_data/services.py), [ghi sản phẩm](../../apps/product/services.py).
- [Tìm/lọc danh mục](../../apps/master_data/selectors.py), [tìm/lọc sản phẩm](../../apps/product/selectors.py), [trang sản phẩm](../../apps/product/views.py).
- [Form và xác nhận ngừng hoạt động](../../templates/master_data/partials/reference_data_form_content.html), [lọc](../../templates/master_data/partials/reference_data_filters.html), [phân trang](../../templates/components/pagination.html).
- [Chọn giá mua](../../apps/costing/engine/resolvers/prices.py), [quy đổi Costing](../../apps/costing/engine/resolvers/uom.py), [ngày hiệu lực Costing](../../apps/costing/engine/resolvers/common.py).
- Tests đã đọc: [reference data](../../apps/master_data/test_reference_data.py), [Supplier/Price](../../apps/master_data/test_supplier.py), [Cost Element](../../apps/master_data/tests.py), [Category/Item](../../apps/product/test_catalog.py), [Product/SKU](../../apps/product/test_product_sku.py). Các test danh mục này được đối chiếu source; bộ targeted đã chạy cho Golden/Formula/Pricing ghi ở [biên bản kiểm chứng](SOURCE_VERIFICATION.md). Không chạy lệnh tạo dữ liệu vào database doanh nghiệp trong task tài liệu.
