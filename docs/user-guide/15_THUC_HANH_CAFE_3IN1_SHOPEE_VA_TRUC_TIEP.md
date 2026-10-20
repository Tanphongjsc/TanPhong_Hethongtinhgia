# 15. Cà phê 3 trong 1: tính từ một gói 18 g, quy lên túi 50 gói và bán trên hai kênh

**Dành cho người dùng kế toán, sản xuất, mua hàng và kinh doanh. Cập nhật 20/10/2026.**

Bài này thay cách nhập tổng tiền ở bản trước bằng **định mức, đơn giá và các khoản cấu thành**. Đơn vị cơ sở là **một gói nhỏ 18 g**. Sau đó tính **một túi lớn 50 gói**, rồi lấy đúng giá vốn một túi để lập giá Shopee và bán trực tiếp.

Nguồn: [file Excel cà phê 3 trong 1](<Update 10092026_HẠCH TOÁN GIÁ BÁN CAFE 3 in 1 (18 gram x 50 bags).xlsx>). Dùng **cột giá gốc C**, chưa tăng 40%. Giữ nguyên dòng **Nestle đỏ, lấy theo giá hương Cappuccino**, giá 1.820.000 đồng/kg theo xác nhận của chủ dữ liệu.

## Xử lý ngay lỗi chạy giá thành ở bản hướng dẫn trước

Đã kiểm tra ba mã tham chiếu:

- `64e4a7e5-7e65-4744-821b-fb708afe7020`
- `c302b0b6-0647-4b22-bade-d0694ce4ca19`
- `6baf0bac-5c57-4c8a-96e5-46324bd0a8e4`

Cả ba dùng phương án **CF_3IN1_GIA_THANH**, phiên bản 1. Dòng `TOTAL` đang đặt **Vai trò của dòng = Dữ liệu đầu vào**, nguồn là **Công thức**. Khi chạy, bộ tính cần đúng một dòng **Vai trò của dòng = Đầu ra**, nên từ chối trước khi tính tiền.

**Hai ô này có ý nghĩa khác nhau:**

| Ô | Dòng tổng phải chọn |
|---|---|
| Vai trò của dòng | **Đầu ra** |
| Nguồn dữ liệu | **Công thức** |
| Phạm vi chi phí | **Sản xuất** |
| Phần tử chi phí | Kiểu **Tiền tệ**, tiền VND, **Đơn vị tính mặc định để trống** |

Công thức cộng đúng và bộ kiểm thử đạt chưa bảo đảm dòng tổng đã được phân loại đúng. Kiểm tra cấu hình hiện chưa chặn trường hợp thiếu Đầu ra này trước khi kích hoạt; bộ chạy giá thành vẫn chặn.

**Nếu chỉ muốn chạy lại cách nhập tổng tiền cũ:** giữ nguyên phương án đã hiệu lực; tạo phương án riêng, chẳng hạn `CF_3IN1_GIA_THANH_FIX`, tạo lại sáu dòng như bản cũ, sửa **dòng TOTAL thành Đầu ra**, giữ nguồn Công thức. Đặt **Số chữ số làm tròn = 8 tại cả sáu dòng** để khớp đáp án, vì các phần tử đang dùng hiện đặt 6 chữ số. Kiểm tra, kích hoạt phương án mới rồi tạo lần tính mới. Không tạo phiên bản mới chồng kỳ hiệu lực với bản cũ, không sửa kết quả Thất bại thành thành công.

**Nếu muốn tính từ các thành phần như yêu cầu mới:** làm theo lộ trình bên dưới, dùng phương án mới `C3_SCHEME_UNIT`. Không nhập lại năm tổng tiền 716.265, 158.772… vào phương án này.

Tôi chỉ đọc các lần lỗi để chẩn đoán; tài liệu này không tự sửa dữ liệu của bạn.

## Đọc theo thứ tự

| Phần | Việc làm |
|---|---|
| [A. Cấu trúc và số liệu](#phan-a) | Hiểu giá một gói được tạo từ những thành phần nào |
| [B. Nhập định mức và chạy tính](#phan-b) | Nhập vật tư, giá, bao bì, công thức; tính một gói rồi một túi |
| [C. Giá bán hai kênh](#phan-c) | Dùng giá vốn một túi để tính Shopee và trực tiếp |
| [D. Kiểm tra và dùng lại](#phan-d) | Xem nguồn, đổi sản lượng, xử lý lỗi và giữ lịch sử |

**Cập nhật 20/10/2026:** BOM và bao bì đã có nút **Kích hoạt phiên bản → Xác nhận kích hoạt** trên trang chi tiết phiên bản; thực hiện ở bước 6 bên dưới. Giá mua mới vẫn lưu Nháp: mở chi tiết từng giá và chọn **Kích hoạt giá → Xác nhận kích hoạt**. Không tự sửa database. Kích hoạt BOM/bao bì không tự kích hoạt giá mua; cần làm riêng từng nguồn.

<a id="phan-a"></a>

## A. Một gói 18 g có những chi phí con nào?

### 1. Cách chia nhóm trong hệ thống

```text
Giá thành 1 gói 18 g
├─ Nguyên liệu
│  ├─ Đường: định mức × giá mua
│  ├─ Bột kem: định mức × giá mua
│  ├─ Cà phê hòa tan: định mức × giá mua
│  ├─ Hương cà phê: định mức × giá mua
│  └─ Nestle đỏ: định mức × giá mua
├─ Bao bì
│  ├─ 1 túi nhỏ
│  ├─ 1/50 túi ngoài
│  └─ Phần carton phân bổ
├─ Máy móc / nhà xưởng / cuộn in
│  ├─ Khấu hao máy
│  ├─ Nhà xưởng và điện nước
│  └─ Cuộn in ngày
├─ Vận chuyển đầu vào
│  ├─ Đi kiểm tra/thử máy, phân bổ theo Excel
│  ├─ Chặng HCM → Hà Nội
│  └─ Chặng Hà Nội → công ty
└─ Nhân công
   └─ Chi phí nhân công / sản lượng tham chiếu
```

**Hiện chưa có trường “phần tử cha” trên danh mục Phần tử chi phí.** Cây trên là cấu trúc nghiệp vụ: nguyên liệu được chi tiết trong **BOM / Công thức sản xuất**, bao bì trong **Cấu hình bao bì**, các khoản khác dùng **phần tử đầu vào và công thức nhóm**. Trong kết quả có thể mở **Nguồn dữ liệu / Diễn giải** để xem thành phần. Không có nút tạo cây cha–con hoặc tự mở rộng mọi nhóm ngay trong bảng chính.

### 2. Định mức nguyên liệu

Dùng bảng cập nhật ở trang `GIÁ NGUYÊN LIỆU`, dòng 72–77. Dù dùng cột giá gốc ở trang tổng hợp, giá nguyên liệu đang liên kết tới **79.585 đồng/kg**, không phải bảng cũ 41.635,92 đồng/kg.

| Vật tư | Định mức cho 1 kg thành phẩm | Giá đồng/kg | Lượng trong 1 gói 18 g | Tiền trong 1 gói |
|---|---:|---:|---:|---:|
| Đường | 0,58 kg | 19.200 | 10,44 g | 200,448 |
| Bột kem không sữa 061 | 0,322 kg | 59.500 | 5,796 g | 344,862 |
| Cà phê hòa tan | 0,087 kg | 340.000 | 1,566 g | 532,44 |
| Hương cà phê | 0,001 kg | 1.510.000 | 0,018 g | 27,18 |
| Nestle đỏ, lấy theo giá hương Cappuccino | 0,01 kg | 1.820.000 | 0,18 g | 327,60 |
| **Tổng** | **1 kg** | | **18 g** | **1.432,53 đồng** |

Ví dụ đường: **0,58 kg/kg × 0,018 kg/gói × 19.200 đồng/kg = 200,448 đồng/gói**.

Trên phần mềm nhập định mức chuẩn **1 kg**, không nhập lại số tiền 1.432,53. Bộ tính tự quy theo lượng 18 g của lần chạy và tra giá từng vật tư.

### 3. Bao bì cho một gói

| Thành phần | Lượng cho một gói nhỏ | Giá vật tư | Tiền/gói |
|---|---:|---:|---:|
| Túi nhỏ | 1 cái | 239,2 đồng/cái | 239,2 |
| Túi ngoài chứa 50 gói | 0,02 cái | 1.067,2 đồng/cái | 21,344 |
| Carton theo phân bổ Excel | 0,003 thùng | 19.000 đồng/thùng | 57 |
| **Tổng** | | | **317,544 đồng** |

Cấu hình bao bì vẫn khai báo cho **một túi lớn**: 50 túi nhỏ + 1 túi ngoài + 0,15 thùng. Khi tính một gói nhỏ, bộ tính dùng hệ số 1/50.

Carton 0,15 thùng/túi lớn xuất phát từ Excel: **19.000 đồng / 6 kg × 0,9 kg**. Đây là **tỷ lệ phân bổ**, chưa khẳng định quy cách đóng thùng thực tế. Nếu thực tế carton chứa số túi khác thì phải xác nhận lại định mức.

### 4. Suất chi phí máy, nhà xưởng, vận chuyển và nhân công

Các con số dưới đây là tiền tương ứng với **cơ sở 1 kg thành phẩm**. Bạn nhập từng khoản một lần cho cơ sở này; phần mềm tự nhân với 0,018 kg khi chạy một gói, hoặc 0,9 kg khi chạy một túi.

| Thành phần | Cách Excel xác định | Số nhập đồng/1 kg |
|---|---|---:|
| Máy sản xuất | 374.000.000 / 24 tháng / 17.160 kg mỗi tháng | `908.11965812` |
| Nhà xưởng và điện nước | 20.581.600 / 17.160 kg | `1199.39393939` |
| Cuộn in ngày | 1.600.000 / 5.280 kg | `303.03030303` |
| Đi kiểm tra/thử máy | 15.000.000 / 100.000 kg | `150` |
| HCM → Hà Nội | 32.000.000 / 25.000 kg | `1280` |
| Hà Nội → công ty | 4.500.000 / 25.000 kg | `180` |
| Nhân công | 60.000.000 / 12.714 kg | `4719.20717319` |

Đây là suất phân bổ từ Excel, **không phải giá mua máy để nhập thẳng vào một gói**. Bài chưa tự lập lịch khấu hao tài sản hay tính lương thực tế.

| Nhóm kết quả cho 1 gói | Đồng |
|---|---:|
| Nguyên liệu | 1.432,53000000 |
| Bao bì | 317,54400000 |
| Máy/nhà xưởng/cuộn in | 43,38979021 |
| Vận chuyển đầu vào | 28,98000000 |
| Nhân công | 84,94572912 |
| **Tổng giá thành 1 gói** | **1.907,38951933** |
| **Tổng tính trực tiếp cho 1 túi 50 gói** | **95.369,47596636** |

Chênh cực nhỏ ở phần số lẻ khi lấy giá một gói đã làm tròn nhân 50 là do làm tròn từng nhóm. Muốn giá một túi để bán, chạy trực tiếp **1 túi** theo bước 11; không nhập ngược con số đã hiển thị tròn đồng.

### 5. Khoản nào trong Excel không dùng?

Trang `CAFE 3 TRON 1`!C11 = 110.966,08440707… đồng/kg có cả **chi phí xuất khẩu 2.000 đồng/kg** và **lợi nhuận 3.000 đồng/kg**.

Bài bán nội địa dùng cơ sở: **C11 − C9 − C10 = 105.966,08440707… đồng/kg**. Không cộng lợi nhuận vào giá vốn rồi tính lợi nhuận lần nữa ở giá bán. Không đưa xuất khẩu vào hai kênh nội địa nếu thực tế không phát sinh.

Cước 1.610 đồng/kg được giữ theo Excel, giả định là chi phí đầu vào phục vụ sản xuất. Kế toán cần xác nhận cách phân loại trước áp dụng thật; không đổi nhãn/phạm vi để đưa cước giao khách hoặc phí sàn vào sản xuất.

Không dùng cột tăng 40%, giá chào USD, ô `#REF!`, các bảng 20 gói × 25 g cũ hoặc công thức thuế bao bì bất thường. Kích thước túi nhỏ còn ghi không nhất quán 176×104/176×114; cần xác nhận khi dùng bao bì thật.

<a id="phan-b"></a>

## B. Nhập dữ liệu và chạy từ một gói lên một túi

### Bước 1 — Dùng lại danh mục đã đúng, bổ sung đơn vị gói

Mở hệ thống, không cần đăng nhập/chọn công ty. Ngày thực hành **20/10/2026**.

Bạn đã tạo sản phẩm/SKU ở bài trước thì dùng lại nếu đúng. Mã `HD_…` là mã minh họa; nếu đang dùng `CF_…` thì chọn đúng bản ghi của bạn, **không đổi tên mã hoặc tạo bản trùng để giống tài liệu**. Riêng các phần tử/công thức/phương án mới dùng mã `C3_…` để tách cách tính mới khỏi bản cũ đã hiệu lực.

Trong ô số: không có phân cách hàng nghìn, dấu chấm thập phân; ví dụ `0.018`, `908.11965812`. Ngày chọn bằng lịch. Dấu — nghĩa là để trống.

Chuẩn bị tiền VND và các đơn vị hoạt động:

| Mã minh họa | Tên | Đại lượng |
|---|---|---|
| `KG` | Kilôgam | MASS |
| `HD_PACKET_18G` | Gói cà phê 18 g | COUNT |
| `HD_BAG_900G` | Túi 50 gói × 18 g | COUNT |
| Đơn vị cái hiện có | Cái bao bì | COUNT |
| Đơn vị carton hiện có | Thùng carton | COUNT |

Hai đơn vị Gói 18 g và Túi 50 gói phải thuộc **cùng nhóm đơn vị số lượng**. Tạo nhóm trước nếu thiếu; không tạo lại KG/Cái/Thùng đã đúng. Giữ độ chính xác phù hợp, ví dụ 8 cho lượng phân bổ.

**Quy đổi đơn vị tính → + Thêm mới**:

| Ô | Giá trị |
|---|---|
| Đơn vị nguồn | Túi 50 gói × 18 g |
| Đơn vị đích | Gói cà phê 18 g |
| Hệ số | `50` |
| Vật tư / Hàng hóa | Để trống cho cặp đơn vị đặc thù này |
| Hiệu lực từ / đến | 20/10/2026 / để trống |

Nghĩa là **1 túi = 50 gói**. Chỉ cần một chiều này; bộ tính có thể dùng nghịch đảo. Không thêm bản ngược chiều cùng kỳ gây nhiều nguồn. Không tạo quy đổi chung Cái→KG.

### Bước 2 — Sản phẩm và SKU bán túi

**DỮ LIỆU DANH MỤC → Sản phẩm**, mở bản đã tạo hoặc **+ Thêm mới**:

| Ô | Giá trị |
|---|---|
| Nhóm sản phẩm | Nhóm cà phê đã có, ví dụ HD_COFFEE |
| Mã / Tên | Giữ mã đang dùng / Cà phê 3 trong 1 |
| Đơn vị tính giá thành | Gói cà phê 18 g |
| Vật tư đầu ra / Mã nhóm thuế | Để trống nếu chưa có căn cứ |
| Đang hoạt động | Chọn |

Nếu chưa có sản phẩm, mã gợi ý `HD_CAFE_3IN1`. Bấm **Lưu sản phẩm**.

**SKU → mở bản cũ hoặc + Thêm mới**:

| Ô | Giá trị |
|---|---|
| Sản phẩm | Đúng sản phẩm trên |
| Mã / Tên | Giữ mã đang dùng / Cà phê 3 trong 1 — túi 50 gói × 18 g |
| Đơn vị bán | **Túi 50 gói × 18 g** |
| Lượng tịnh | `0.9` |
| Đơn vị lượng tịnh | KG |
| Mã vạch / Vật tư bán | Trống nếu chưa có dữ liệu |
| Đang hoạt động | Chọn |

Mã SKU gợi ý nếu chưa có: `HD_CAFE_3IN1_18G50`. **Lưu SKU**. SKU vẫn là túi bán; Gói 18 g là đơn vị cơ sở để phân tích giá thành. Một lần tính được chọn đơn vị sản lượng là gói hoặc túi nhờ quy đổi ở bước 1.

### Bước 3 — Nhập vật tư và giá từng vật tư

**Vật tư / Hàng hóa → + Thêm mới**, hoặc dùng lại bản đúng:

| Mã gợi ý | Tên | Loại | Đơn vị cơ sở/mua/sản xuất | Giá đồng/đơn vị |
|---|---|---|---|---:|
| `HD_RM_SUGAR` | Đường | Nguyên liệu | KG | 19.200 |
| `HD_RM_CREAMER061` | Bột kem không sữa 061 | Nguyên liệu | KG | 59.500 |
| `HD_RM_INSTANT_COFFEE` | Cà phê hòa tan | Nguyên liệu | KG | 340.000 |
| `HD_RM_COFFEE_FLAVOR` | Hương cà phê | Nguyên liệu | KG | 1.510.000 |
| `HD_RM_NESTLE_RED` | Nestle đỏ — theo giá hương Cappuccino | Nguyên liệu | KG | 1.820.000 |
| `HD_PK_SACHET18G` | Túi nhỏ cà phê 18 g | Bao bì | Cái | 239,2 |
| `HD_PK_OUTER900G` | Túi ngoài cà phê 900 g | Bao bì | Cái | 1.067,2 |
| `HD_PK_CARTON` | Thùng carton theo Excel | Bao bì | Thùng carton | 19.000 |

Giữ hoạt động; số đo chưa biết để trống. Lưu từng vật tư.

Tạo hoặc chọn **Nhà cung cấp** đã xác nhận rồi vào **Giá nhà cung cấp → + Thêm mới** cho từng vật tư: đơn giá theo bảng, VND, đơn vị báo giá đúng, tối thiểu `0`, bắt đầu 20/10/2026, kết thúc trống, nguồn `EXCEL_10092026`, tham chiếu tên trang/ô Excel.

Trong môi trường học có thể dùng `HD_NCC_EXCEL — Nhà cung cấp tham chiếu Excel`. Đây không phải khẳng định tám vật tư do một nhà cung cấp thực tế bán. Thực tế phải dùng đúng nhà cung cấp/báo giá.

**Thuế mua:** bài dùng giá trước thuế với giả định thuế được khấu trừ toàn bộ. Nguồn đào tạo cho bộ tính hiện có: giá chưa gồm thuế, tỷ lệ thuế trống hoặc `0`, tỷ lệ được khấu trừ `1`. Không sửa mức thuế trên nguồn thật thành 0 để lách giới hạn: Costing hiện chặn nguồn mua có thuế khác 0; cần người phụ trách xác định cách xử lý. Thuế bán minh họa ở C là việc riêng.

Lưu mới là **Nháp**. Sau khi kiểm tra báo giá, mở chi tiết từng giá → **Kích hoạt giá → Xác nhận kích hoạt**. Kiểm tra **Trạng thái bản ghi: Đang hiệu lực** cho cả tám giá trong bảng. Không chỉ nhìn badge theo ngày; giá còn Nháp chưa được bộ tính sử dụng.

### Bước 4 — Nhập định mức chuẩn 1 kg

**SẢN XUẤT → BOM / Công thức sản xuất → + Thêm định mức**:

| Ô | Giá trị |
|---|---|
| Sản phẩm | Sản phẩm cà phê 3 trong 1 ở bước 2 |
| Mã / Tên | `HD_BOM_3IN1_KG` / Định mức cà phê 3 trong 1 — chuẩn 1 kg |
| Sản lượng chuẩn | `1` |
| Đơn vị đầu ra | **KG** |
| Tỷ lệ thu hồi (%) | `100` |
| Hiệu lực từ / đến | 20/10/2026 / trống |
| Đang hoạt động | Chọn |

**Lưu định mức nguyên vật liệu**, **+ Thêm thành phần**, nhập từng dòng:

| Thứ tự | Vật tư | Số lượng | Đơn vị | Hao hụt (%) |
|---:|---|---:|---|---:|
| 10 | Đường | `0.58` | KG | `0` |
| 20 | Bột kem 061 | `0.322` | KG | `0` |
| 30 | Cà phê hòa tan | `0.087` | KG | `0` |
| 40 | Hương cà phê | `0.001` | KG | `0` |
| 50 | Nestle đỏ | `0.01` | KG | `0` |

Để trống nhóm thay thế/mã công đoạn, không chọn thành phần tùy chọn. **Lưu thành phần** cho mỗi dòng.

Một gói 18 g tương đương **0,018 kg**, nên hệ số định mức **0,018 / 1 = 0,018**. Bộ tính nhân từng dòng với hệ số đó, rồi tra giá vật tư. Không nhập số lượng một gói vào bảng đang khai báo sản lượng chuẩn 1 kg.

Nếu trước đó đã có BOM hiệu lực cho cùng sản phẩm/ngày, không tạo thêm bản chồng kỳ. Nhờ người phụ trách kiểm tra nguồn nào sẽ dùng.

### Bước 5 — Nhập bao bì cho một túi 50 gói

**Cấu hình bao bì → + Thêm cấu hình bao bì**: đúng sản phẩm, mã `HD_PACK_3IN1`, tên **Bao bì túi 50 gói 18 g**, giữ hoạt động, ngày đầu phiên bản 20/10/2026.

Thêm các thành phần:

| Thứ tự | Vật tư | Số lượng | Đơn vị | Cấp đóng gói |
|---:|---|---:|---|---|
| 10 | Túi nhỏ cà phê 18 g | `50` | Cái | Cấp 1 · Bao bì trực tiếp |
| 20 | Túi ngoài 900 g | `1` | Cái | Cấp 2 · Bao bì nhóm |
| 30 | Carton | `0.15` | Thùng carton | Cấp 3 · Bao bì vận chuyển |

Không điền cha/con hoặc số lượng trên cấp cha để nhân thêm lần nữa. Phiên bản hiện không có ô sản lượng đầu ra: nhớ cơ sở của bảng này là **1 túi lớn** và sẽ nhập ở form chạy.

**+ Gán SKU**: chọn đúng SKU túi 50 gói, liên kết chính, bắt đầu 20/10/2026, kết thúc trống, lưu.

### Bước 6 — Kích hoạt BOM, bao bì và kiểm tra nguồn

1. Mở định mức đã tạo ở bước 4, vào đúng phiên bản. Kiểm tra **Hiệu lực từ ngày** là 20/10/2026 hoặc ngày bắt đầu thực tế đã thống nhất, sản lượng chuẩn **1 kg**, đủ nguyên liệu ở bước 3 và đúng số lượng. Nhấn **Kích hoạt phiên bản → Xác nhận kích hoạt**.
2. Mở cấu hình bao bì ở bước 5, vào đúng phiên bản, kiểm tra ngày áp dụng và đủ các vật tư ở bước 5. Nhấn **Kích hoạt phiên bản → Xác nhận kích hoạt**. Liên kết SKU túi 50 gói vẫn phải được lưu riêng.
3. Cả hai phiên bản phải có trạng thái **Đang hiệu lực**. Nếu báo lỗi, sửa đúng nội dung trên đầu trang rồi thử lại; không tạo thêm nguồn để thử mò. Nút chỉ hiện cho bản còn sửa được.
4. Khi bản cũ đã chốt, không chỉnh sửa thành phần trực tiếp. Muốn thay phải tạo phiên bản mới, chọn kỳ không chồng ngày với bản cũ. Không tự sửa database; bản cũ mở không giới hạn cần báo người phụ trách thống nhất lịch áp dụng.

Trước khi chạy, cùng người phụ trách hệ thống xác nhận:

- [ ] Tám giá mua, phiên bản BOM và bao bì **Đang hiệu lực** tại ngày chạy.
- [ ] Mỗi vật tư có đúng một giá phù hợp ngày, lượng và đơn vị.
- [ ] Sản phẩm có đúng một BOM phù hợp; SKU có đúng một gán bao bì chính phù hợp.
- [ ] Quy đổi **1 túi = 50 gói** có đúng một nguồn tại ngày chạy.
- [ ] SKU có lượng tịnh 0,9 kg/túi; định mức chuẩn 1 kg; bao bì chuẩn 1 túi.
- [ ] Không có nguồn thuế mua/điều kiện/thay thế chưa được bộ tính hỗ trợ.

**Nếu BOM/bao bì còn Nháp: thực hiện hai nút kích hoạt ở trên. Nếu giá mua còn Nháp: mở chi tiết từng giá → Kích hoạt giá → Xác nhận kích hoạt.** Ngày bắt đầu đúng không tự làm nguồn thành Đang hiệu lực. Không tự sửa database hoặc thêm giá khác để thử mò. Có thể tiếp tục chuẩn bị công thức/phương án ở bước 7–9, nhưng chỉ chạy khi checklist này đạt.

### Bước 7 — Tạo phần tử cho đầu vào và các nhóm kết quả

Vào **Phần tử chi phí → + Thêm mới**. Tạo các mã mới sau, để tách khỏi sáu phần tử nhập tổng ở bản trước.

Hai phần tử số lượng:

| Mã | Tên | Loại giá trị | Đơn vị mặc định | Nguồn |
|---|---|---|---|---|
| `C3_RUN_KG` | Khối lượng thành phẩm cần tính | Số lượng | KG | Hệ thống |
| `C3_BASIS_KG` | Cơ sở áp dụng suất chi phí — 1 kg | Số lượng | KG | Nhập thủ công |

Không chọn tiền tệ cho hai phần tử này; Đại lượng có thể để trống để lấy từ đơn vị.

Bảy khoản cấu thành bằng tiền cho **cơ sở 1 kg**:

| Mã | Tên | Nguồn |
|---|---|---|
| `C3_MACHINE_KG` | Máy sản xuất — tiền cho cơ sở 1 kg | Nhập thủ công |
| `C3_FACTORY_KG` | Nhà xưởng/điện nước — tiền cho cơ sở 1 kg | Nhập thủ công |
| `C3_INK_KG` | Cuộn in — tiền cho cơ sở 1 kg | Nhập thủ công |
| `C3_SHIP_TEST_KG` | Kiểm tra/thử máy — tiền cho cơ sở 1 kg | Nhập thủ công |
| `C3_SHIP_HCM_HN_KG` | HCM–Hà Nội — tiền cho cơ sở 1 kg | Nhập thủ công |
| `C3_SHIP_HN_FACTORY_KG` | Hà Nội–công ty — tiền cho cơ sở 1 kg | Nhập thủ công |
| `C3_LABOR_KG` | Nhân công — tiền cho cơ sở 1 kg | Nhập thủ công |

Sáu nhóm/kết quả:

| Mã | Tên | Nguồn |
|---|---|---|
| `C3_RM_COST` | Chi phí nguyên liệu | Hệ thống |
| `C3_PK_COST` | Chi phí bao bì | Hệ thống |
| `C3_DEPR_COST` | Chi phí máy/nhà xưởng/cuộn in | Công thức |
| `C3_INBOUND_COST` | Chi phí vận chuyển đầu vào | Công thức |
| `C3_LABOR_COST` | Chi phí nhân công | Công thức |
| `C3_TOTAL_COST` | Tổng giá thành | Công thức |

Cả 13 phần tử tiền: **Loại giá trị = Tiền tệ, Tiền tệ = VND, Đơn vị tính mặc định để trống**. Các khoản suất chi phí là tiền cho cơ sở 1 kg đã tách riêng ở `C3_BASIS_KG`, không gắn KG làm đơn vị của một trường Tiền tệ.

Cả 15 phần tử: nhóm tùy chọn để trống; phạm vi kế toán **Chi phí hàng tồn kho** theo giả định sản xuất của bài; phạm vi chi phí **Sản xuất**; **Số chữ số làm tròn 8**, **Làm tròn nửa về số chẵn**, hoạt động. Lưu từng bản ghi.

### Bước 8 — Tạo bốn công thức và kiểm thử một gói

Mỗi công thức: **CÔNG THỨC & QUY TẮC → Thiết lập công thức → + Thêm công thức**; chọn phần tử kết quả, nhập ngày bắt đầu 20/10/2026, kết thúc trống, giữ hoạt động.

**8.1. Máy móc, nhà xưởng, cuộn in**

Mã công thức `C3_F_DEPR`, kết quả `C3_DEPR_COST`:

```text
ROUND(($C3_MACHINE_KG + $C3_FACTORY_KG + $C3_INK_KG) * ($C3_RUN_KG / $C3_BASIS_KG), 8)
```

Mẫu thử: `C3_MACHINE_KG=908.11965812`; `C3_FACTORY_KG=1199.39393939`; `C3_INK_KG=303.03030303`; `C3_RUN_KG=0.018`; `C3_BASIS_KG=1`. **Kết quả mong đợi: `43.38979021`.**

**8.2. Vận chuyển**

Mã `C3_F_INBOUND`, kết quả `C3_INBOUND_COST`:

```text
ROUND(($C3_SHIP_TEST_KG + $C3_SHIP_HCM_HN_KG + $C3_SHIP_HN_FACTORY_KG) * ($C3_RUN_KG / $C3_BASIS_KG), 8)
```

Mẫu thử: các khoản `150`, `1280`, `180`; `C3_RUN_KG=0.018`; `C3_BASIS_KG=1`. **Kết quả: `28.98`.**

**8.3. Nhân công**

Mã `C3_F_LABOR`, kết quả `C3_LABOR_COST`:

```text
ROUND($C3_LABOR_KG * ($C3_RUN_KG / $C3_BASIS_KG), 8)
```

Mẫu thử: `C3_LABOR_KG=4719.20717319`; `C3_RUN_KG=0.018`; `C3_BASIS_KG=1`. **Kết quả: `84.94572912`.**

**8.4. Tổng giá thành**

Mã `C3_F_TOTAL`, kết quả `C3_TOTAL_COST`:

```text
$C3_RM_COST + $C3_PK_COST + $C3_DEPR_COST + $C3_INBOUND_COST + $C3_LABOR_COST
```

Mẫu thử: nguyên liệu `1432.53`; bao bì `317.544`; máy/nhà xưởng `43.38979021`; vận chuyển `28.98`; nhân công `84.94572912`. **Kết quả: `1907.38951933`.**

**Làm đủ cho từng công thức:** Kiểm tra công thức → Kiểm thử với mẫu → Lưu công thức. Ở trang phiên bản, điền lại mẫu, đáp án, tên mẫu **Một gói 18 g** → **Lưu bộ kiểm thử → Chạy bộ kiểm thử đã lưu → Kích hoạt phiên bản → Xác nhận kích hoạt**. Kiểm tra Đang hiệu lực.

`ROUND(...,8)` là làm tròn đến 8 số lẻ để mẫu thử có đáp án lưu được; không phải làm tròn giá bán lên tròn nghìn. Trong phép thử nhập tay `C3_RUN_KG=0.018`; khi chạy giá thành thật, phần mềm tự cung cấp lượng này.

### Bước 9 — Tạo phương án mới có đúng một dòng Đầu ra

Tạo phương án `C3_SCHEME_UNIT`, tên **Giá thành 3 trong 1 từ định mức — gói 18 g**, mục đích `PLANNED_COST`, phạm vi `SKU`, ngày bắt đầu 20/10/2026, hoạt động. Giữ phương án cũ để tra cứu.

Ở bản Nháp, thêm 15 thành phần sau. **Mã dòng dùng đúng mã phần tử** để dễ đối chiếu.

| Thứ tự | Mã dòng và phần tử | Vai trò của dòng | Nguồn | Mã lấy dữ liệu / Công thức |
|---:|---|---|---|---|
| 10 | C3_RUN_KG | Thông tin | Hệ thống | `RUN_QUANTITY` |
| 20 | C3_BASIS_KG | Thông tin | Nhập thủ công | — |
| 30 | C3_MACHINE_KG | Dữ liệu đầu vào | Nhập thủ công | — |
| 40 | C3_FACTORY_KG | Dữ liệu đầu vào | Nhập thủ công | — |
| 50 | C3_INK_KG | Dữ liệu đầu vào | Nhập thủ công | — |
| 60 | C3_SHIP_TEST_KG | Dữ liệu đầu vào | Nhập thủ công | — |
| 70 | C3_SHIP_HCM_HN_KG | Dữ liệu đầu vào | Nhập thủ công | — |
| 80 | C3_SHIP_HN_FACTORY_KG | Dữ liệu đầu vào | Nhập thủ công | — |
| 90 | C3_LABOR_KG | Dữ liệu đầu vào | Nhập thủ công | — |
| 100 | C3_RM_COST | Dữ liệu đầu vào | Hệ thống | `MATERIAL_COST` |
| 110 | C3_PK_COST | Dữ liệu đầu vào | Hệ thống | `PACKAGING_COST` |
| 120 | C3_DEPR_COST | Tính toán | Công thức | C3_F_DEPR đã hiệu lực |
| 130 | C3_INBOUND_COST | Tính toán | Công thức | C3_F_INBOUND đã hiệu lực |
| 140 | C3_LABOR_COST | Tính toán | Công thức | C3_F_LABOR đã hiệu lực |
| 150 | **C3_TOTAL_COST** | **Đầu ra** | **Công thức** | **C3_F_TOTAL đã hiệu lực** |

Mỗi dòng có Tên hiển thị theo tên phần tử ở bước 7; phạm vi **Sản xuất**, hiển thị **Tất cả**, số chữ số làm tròn để trống để dùng 8 của phần tử. Không nhập nguồn khác cho dòng không cần. Với C3_BASIS_KG có thể đặt giá trị tối thiểu `0.00000001` để tránh nhập 0; bài luôn nhập `1`.

**Điểm tránh lặp lỗi cũ:** dòng C3_TOTAL_COST phải chọn **Vai trò của dòng Đầu ra**, không phải Dữ liệu đầu vào hay Tính toán. Có công thức chưa đủ. Chỉ một dòng Đầu ra; phần tử của nó phải là tiền VND, không có đơn vị mặc định.

**Kiểm tra cấu hình → Kích hoạt phiên bản → Xác nhận kích hoạt**. Kiểm tra lại bảng sau khi lưu, nhất là cột Vai trò của dòng của dòng tổng.

### Bước 10 — Chạy thật cho một gói nhỏ

Sau khi checklist nguồn ở bước 6 đạt, vào **TỔNG QUAN → Lần tính giá thành → + Chạy tính giá**:

| Ô | Giá trị |
|---|---|
| Sản phẩm | Cà phê 3 trong 1 đang dùng |
| Ngày tính | 20/10/2026 |
| Sản lượng | **`1`** |
| Đơn vị sản lượng | **Gói cà phê 18 g** |
| Tiền tệ | VND |
| Loại lần tính | Giá thành kế hoạch |
| SKU | Túi 50 gói × 18 g của sản phẩm |
| Phương án | C3_SCHEME_UNIT |
| Số thành phẩm theo định mức bao bì | **`1`** |
| Đơn vị thành phẩm đóng gói | **Túi 50 gói × 18 g** |

Tám ô nhập tay là dữ liệu **cho cơ sở 1 kg**, không phải tổng tiền lần chạy:

| Ô theo mã | Số nhập |
|---|---:|
| C3_BASIS_KG | `1` |
| C3_MACHINE_KG | `908.11965812` |
| C3_FACTORY_KG | `1199.39393939` |
| C3_INK_KG | `303.03030303` |
| C3_SHIP_TEST_KG | `150` |
| C3_SHIP_HCM_HN_KG | `1280` |
| C3_SHIP_HN_FACTORY_KG | `180` |
| C3_LABOR_KG | `4719.20717319` |

Không nhập Nguyên liệu/Bao bì bằng tiền: hai khoản đó được lấy tự động. Không nhập C3_RUN_KG: nguồn RUN_QUANTITY tự đổi theo SKU/quy đổi. Với 1 gói, lượng phải ra **0,018 kg**.

Ghi chú **Tính cơ sở 1 gói 18 g; nguồn Excel giá gốc; bao bì chuẩn 1 túi 50 gói**. Bấm **Chạy tính giá**, đợi kết quả.

Thành công phải **Đã khóa**, tổng **1.907,38951933 đồng cho 1 gói**. Mở diễn giải:

- Nguyên liệu: đủ năm vật tư, đúng lượng và giá; tổng **1.432,53**.
- Bao bì: 1 túi nhỏ + 0,02 túi ngoài + 0,003 thùng; tổng **317,544**.
- Máy/nhà xưởng: ba suất thành phần × 0,018/1; **43,38979021**.
- Vận chuyển: ba suất × 0,018/1; **28,98**.
- Nhân công: 4.719,20717319 × 0,018/1; **84,94572912**.

Bảng còn có các dòng suất chi phí tiền/1 kg để giải thích, chúng **không phải các chi phí cộng thêm lần nữa**. Tổng chỉ lấy năm nhóm được liệt kê trong công thức.

### Bước 11 — Quy lên túi 50 gói và lấy nguồn giá bán

**Tạo lần tính mới** từ lần thành công ở bước 10; giữ sản phẩm, SKU, phương án và tám suất đầu vào. Đổi:

| Ô | Giá trị |
|---|---|
| Sản lượng | `1` |
| Đơn vị sản lượng | **Túi 50 gói × 18 g** |

Giữ cơ sở đóng gói **1 túi**. **Không nhân các suất chi phí nhập tay với 50**; phần mềm tự tính lượng thành phẩm **0,9 kg** thay cho 0,018 kg.

**Chạy tính giá**. Kết quả **95.369,47596636 đồng cho 1 túi**, Đã khóa. Ghi số lần tính này để dùng cho giá bán.

Có thể kiểm tra thêm bằng một lần tính **50 Gói 18 g**: tổng cũng **95.369,47596636 đồng**, nhưng đơn giá của nguồn đó vẫn là **mỗi gói**, không phải mỗi túi.

**Phần C phải chọn nguồn 1 Túi ở bước 11.** Đừng chọn nguồn 1 Gói hoặc 50 Gói rồi kỳ vọng Pricing tự nhân lên túi: giá bán tính theo đơn vị đầu ra của nguồn, phí cố định cũng tính trên đơn vị đó.




<a id="phan-c"></a>

## C. Tính giá bán Shopee và trực tiếp

**Chọn nguồn 1 Túi ở bước 11, không chọn nguồn 1 Gói/50 Gói.** Giá vốn và phí cố định trong phần này đều tính cho một túi 50 gói. Mã HD_ là mã minh họa; nếu bạn đã dùng mã khác, chọn đúng sản phẩm/SKU của mình.

### Bước 12 — Thống nhất giả định bán hàng

| Nội dung | Trực tiếp | Shopee minh họa |
|---|---|---|
| Đơn vị | Một túi 900 g | Một túi 900 g |
| Giá vốn | Cùng lần tính ở bước 11 | Cùng lần tính ở bước 11 |
| Hoa hồng | Không | 10% giá khách trả |
| Thanh toán | Không | 2% giá khách trả |
| Phí cố định | Không | 1.000 đồng **mỗi túi** |
| Thuế bán hàng | Minh họa 10%, đã gồm trong giá | Minh họa 10%, đã gồm trong giá |
| Biên lợi nhuận mục tiêu | 20% | 20% |
| Quảng cáo/voucher/hoàn hàng/cước giao khách | Chưa đưa vào bài | Chưa đưa vào bài |

Các mức trên là giả định đào tạo, không phải chính sách Shopee thực tế. Phần mềm không tự tải phí từ Shopee.

**Biên lợi nhuận 20% = lợi nhuận sau phí, thuế / giá khách trả.** Không lấy giá vốn cộng 20%. Khoản lợi nhuận 3.000 đồng/kg trong Excel là một cách đặt mục tiêu khác; không cộng khoản này rồi đòi thêm biên 20%.

### Bước 13 — Tạo hai kênh

**GIÁ BÁN → Kênh bán → + Thêm mới**, tạo riêng từng kênh:

| Ô | Trực tiếp | Shopee |
|---|---|---|
| Mã | `HD_DIRECT` | `HD_SHOPEE` |
| Tên | Bán trực tiếp — thực hành cà phê | Shopee — phí minh họa |
| Loại kênh bán | Bán trực tiếp | Thương mại điện tử |
| Mã nền tảng | — | `SHOPEE` |
| Mã thị trường | `VN` | `VN` |
| Loại người bán | — | — |
| Tiền tệ mặc định | VND | VND |
| Đang hoạt động | Chọn | Chọn |

**Lưu kênh bán**. Mã nền tảng chỉ để nhận biết, không tự sinh phí.

### Bước 14 — Nhập ba khoản phí Shopee

**GIÁ BÁN → Quy tắc phí kênh → + Thêm mới**. Tạo **ba bản ghi riêng**:

| Ô | Hoa hồng | Thanh toán | Phí mỗi túi |
|---|---|---|---|
| Kênh bán | HD_SHOPEE | HD_SHOPEE | HD_SHOPEE |
| Loại phí | `COMMISSION` | `PAYMENT_FEE` | `SERVICE_PER_UNIT` |
| Cơ sở tính phí | `LIST_PRICE` | `LIST_PRICE` | `LIST_PRICE` |
| Tỷ lệ (%) | `10` | `2` | Để trống |
| Số tiền cố định | Để trống | Để trống | `1000` |
| Tiền tệ | VND | VND | VND |
| Tỷ lệ được hoàn (%) | `0` | `0` | `0` |
| Thuế trong phí | Giá đã bao gồm thuế | Giá đã bao gồm thuế | Giá đã bao gồm thuế |
| Giá trị sàn / trần | Để trống | Để trống | Để trống |
| Nhóm sản phẩm | Để trống | Để trống | Để trống |
| SKU | HD_CAFE_3IN1_18G50 | HD_CAFE_3IN1_18G50 | HD_CAFE_3IN1_18G50 |
| Mức ưu tiên | `100` | `100` | `100` |
| Hiệu lực từ | 20/10/2026 | 20/10/2026 | 20/10/2026 |
| Hiệu lực đến | Để trống | Để trống | Để trống |
| Trạng thái | Đang hiệu lực | Đang hiệu lực | Đang hiệu lực |
| Tham chiếu | Phí minh họa đào tạo | Phí minh họa đào tạo | Phí minh họa đào tạo |

**Lưu quy tắc phí kênh** sau mỗi bản ghi. Dùng ba **loại phí khác nhau** để chúng được cộng. Nếu cùng ghi `COMMISSION`, phần mềm chọn một quy tắc cùng loại hoặc báo trùng nguồn.

`LIST_PRICE` là giá khách trả đã gồm thuế. Trong ô Tỷ lệ, nhập `10` cho 10%, không nhập `0.1`.

Bài **không tạo phí cho HD_DIRECT**; kiểm tra không có quy tắc khác áp dụng cho kênh đó.

**Phí mỗi đơn khác phí mỗi túi:** nếu 1.000 đồng thực tế thu cho cả đơn nhiều túi, phải xác định cách phân bổ trước. Không nhập 1.000 mỗi túi rồi gọi đó là phí của cả đơn; bài này chưa mô phỏng giỏ hàng.

### Bước 15 — Tạo thuế minh họa riêng

Dùng mã khu vực `VN_THUCHANH_3IN1` để tách bài học khỏi quy tắc của doanh nghiệp. Đây là **mã nhận diện đào tạo, không phải mã khu vực pháp lý**.

**GIÁ BÁN → Quy tắc thuế → + Thêm mới**:

| Ô | Giá trị nhập |
|---|---|
| Mã khu vực | `VN_THUCHANH_3IN1` |
| Loại thuế | `VAT` |
| Cơ sở tính thuế | `SELLING_PRICE` |
| Thuế suất (%) | `10` |
| Số tiền cố định | — |
| Tiền tệ | VND |
| Tỷ lệ được khấu trừ (%) | `0` |
| Thuế trong giá | Giá đã bao gồm thuế |
| Nhóm thuế / Loại người bán / Loại giao dịch | Để trống |
| Mức ưu tiên | `100` |
| Hiệu lực từ | 20/10/2026 |
| Hiệu lực đến | — |
| Trạng thái | Đang hiệu lực |
| Tham chiếu | Thuế giả định để học; không làm căn cứ xuất hóa đơn |

**Lưu quy tắc thuế**. Cả hai kịch bản phải nhập đúng mã khu vực trên.

Thuế đã gồm trong giá: **giá khách trả / 1,1 × 10%**, không phải giá khách trả × 10%. Thuế mua nguyên liệu và thuế bán là hai việc khác; không chép các mức thuế mua Excel sang đây.

### Bước 16 — Tính giá bán trực tiếp

**GIÁ BÁN → Kịch bản giá bán → + Thêm kịch bản**:

| Ô | Giá trị nhập |
|---|---|
| Mã kịch bản | `HD_3IN1_DIRECT_M20` |
| Tên kịch bản | Cà phê 3 trong 1 — trực tiếp — biên 20% minh họa |
| Sản phẩm | HD_CAFE_3IN1 |
| SKU | HD_CAFE_3IN1_18G50 |
| Nguồn giá thành | Đúng số lần tính Đã khóa ở bước 11 |
| Kênh bán | HD_DIRECT |
| Ngày định giá | 20/10/2026 |
| Tiền tệ bán | VND |
| Thuế bán hàng | Áp dụng thuế theo quy tắc |
| Mã khu vực áp dụng thuế | `VN_THUCHANH_3IN1` — nhập đè gợi ý VN |
| Mã loại giao dịch; Mã loại tỷ giá | — |
| Phương pháp định giá | Biên lợi nhuận mục tiêu |
| Biên lợi nhuận mục tiêu (%) | `20` |
| Tỷ lệ cộng trên giá vốn (%) | **Để trống** |
| Lợi nhuận mục tiêu trên một đơn vị | **Để trống** |
| Giá bán tối thiểu | — để đối chiếu đúng đáp án |
| Hiệu lực từ | 20/10/2026 |
| Hiệu lực đến | — |

Chọn **Sản phẩm → SKU → Nguồn giá thành** theo thứ tự. Nếu đổi sản phẩm/SKU, chọn lại nguồn. Nguồn phải cung cấp khoảng 95.369,48 đồng **mỗi túi**, không lấy giá 1.907,39 của một gói làm giá vốn một túi.

**Lưu Nháp → Tính giá bán**. Thành công chuyển **Đã tính**, giá khách trả khoảng **134.495,41 đồng/túi**.

### Bước 17 — Tính giá Shopee

Tạo kịch bản mới như bước 16, chỉ thay:

| Ô | Giá trị |
|---|---|
| Mã kịch bản | `HD_3IN1_SHOPEE_M20` |
| Tên kịch bản | Cà phê 3 trong 1 — Shopee — biên 20% minh họa |
| Kênh bán | HD_SHOPEE |

Giữ cùng sản phẩm/SKU/nguồn giá vốn/ngày/VND/mục tiêu 20%. Kiểm tra mã khu vực vẫn `VN_THUCHANH_3IN1` sau khi chọn kênh.

**Lưu Nháp → Tính giá bán**. Giá khách trả khoảng **163.590,16 đồng/túi**. Mở **Nguồn và diễn giải đã lưu**, kiểm tra đủ ba phí và đúng thuế minh họa.

### Bước 18 — Đối chiếu kết quả

Đơn vị đồng/túi; bảng làm tròn hai số lẻ cho dễ đọc:

| Chỉ tiêu | Trực tiếp | Shopee minh họa |
|---|---:|---:|
| Giá khách trả | 134.495,41 | 163.590,16 |
| Hoa hồng 10% | 0 | 16.359,02 |
| Thanh toán 2% | 0 | 3.271,80 |
| Phí cố định | 0 | 1.000,00 |
| **Tổng phí** | **0** | **20.630,82** |
| Thuế minh họa | 12.226,86 | 14.871,83 |
| Doanh thu sau phí và thuế | 122.268,56 | 128.087,51 |
| Giá vốn | 95.369,48 | 95.369,48 |
| **Lợi nhuận sau phí và thuế** | **26.899,08** | **32.718,03** |
| **Biên lợi nhuận trên giá khách trả** | **20%** | **20%** |

**Giá khách trả − Tổng phí − Thuế − Giá vốn = Lợi nhuận.** Cộng các số đã làm tròn có thể chênh 0,01–0,02 đồng; xem số đầy đủ trong diễn giải khi đối chiếu.

Giá Shopee cao hơn để đạt cùng tỷ lệ lãi sau phí. Không kết luận kênh nào luôn tốt hơn chỉ từ tiền lãi/túi: chúng đang có **hai mức giá bán khác nhau**, chưa tính hết chi phí quảng cáo, hoàn hàng và giao khách.

Có thể tự kiểm tra bằng máy tính:

```text
Trực tiếp:
Giá khách trả = Giá vốn / (1 / 1,1 − 0,20)

Shopee minh họa:
Giá khách trả = (Giá vốn + 1.000) / (1 / 1,1 − 0,12 − 0,20)
```

Công thức tính tay chỉ đúng giả định bài, không có sàn/trần phí hoặc loại thuế khác.

### Bước 19 — So sánh trên màn hình

1. **GIÁ BÁN → So sánh kịch bản**.
2. Chọn sản phẩm HD_CAFE_3IN1, SKU HD_CAFE_3IN1_18G50.
3. Đánh dấu hai kịch bản HD_3IN1_DIRECT_M20 và HD_3IN1_SHOPEE_M20, đều Đã tính.
4. Chọn trực tiếp làm **Kịch bản mốc**.
5. **So sánh kịch bản**.
6. Kiểm tra cùng giá vốn/đơn vị túi; giá Shopee cao hơn khoảng **29.094,74 đồng/túi**, biên cùng 20%.

Không coi hai SKU khác quy cách hoặc hai nguồn khác đơn vị đầu ra là cùng một hàng để so sánh.

### Bước 20 — Thay bằng chính sách thật

Xin người phụ trách kinh doanh/kế toán cung cấp từng phí, cơ sở tính, tỷ lệ, tiền cố định, sàn/trần; phí mỗi đơn hay mỗi túi; thuế bán; quảng cáo, voucher, vận chuyển và hoàn hàng; mục tiêu lợi nhuận.

Dùng **kênh/quy tắc thực tế riêng**, không biến dữ liệu đào tạo thành chính sách bán. Bộ tính hiện hỗ trợ phí trên `LIST_PRICE`, đã gồm thuế, tỷ lệ được hoàn 0. Chính sách khác cơ sở, hoàn phí hoặc điều kiện chưa hỗ trợ cần được xác định cách xử lý trước; không ép thành một tỷ lệ tùy ý.

Quy tắc mới có thể chọn **Đang hiệu lực** trên form sau kiểm tra. Bản chốt không sửa trực tiếp; tạo kỳ mới không chồng kỳ. Phí/thuế kết thúc 01/11 nghĩa là **không còn áp dụng ngày 01/11**. Nút **Kết thúc hiệu lực** chỉ cho đặt mốc tương lai theo điều kiện màn hình.

Kịch bản đã tính giữ nguyên. Dùng **Nhân bản thành kịch bản mới**, nhập mã mới, chọn ngày/quy tắc đúng rồi tính. Tính lại trên bản cũ không cập nhật chính sách hôm nay.

Muốn giá tròn dễ niêm yết: phần mềm chưa tự làm tròn thương mại lên 500/1.000 đồng. Có thể tạo bản mới và đặt **Giá bán tối thiểu** cao hơn giá giải, tính lại và kiểm tra lợi nhuận. Đây là giá sàn, không phải ô ép mọi giá tùy ý.

**Nếu giữ mục tiêu lợi nhuận 3.000 đồng/kg của Excel:** túi 0,9 kg tương ứng **2.700 đồng/túi**. Chọn **Lợi nhuận trên một đơn vị**, nhập `2700`, để trống biên và tỷ lệ cộng. Với phí/thuế minh họa, giá khách trả là **107.876,42356300 đồng trực tiếp** hoặc **125.548,87507258 đồng Shopee**. Đây là mục tiêu khác biên 20%; không cộng thêm 2.700 vào giá vốn.


<a id="phan-d"></a>

## D. Kiểm tra, cập nhật và xử lý lỗi

### 1. Khi đổi số lượng, phần mềm tự tính gì?

| Chạy cho | Khối lượng tự xác định | Hệ số nguyên liệu chuẩn 1 kg | Hệ số bao bì chuẩn 1 túi |
|---|---:|---:|---:|
| 1 gói 18 g | 0,018 kg | 0,018 | 0,02 |
| 50 gói 18 g | 0,9 kg | 0,9 | 1 |
| 1 túi 50 gói | 0,9 kg | 0,9 | 1 |
| 10 túi 50 gói | 9 kg | 9 | 10 |

Bạn giữ **Cơ sở chi phí = 1 kg**, giữ các suất tiền/kg; không sửa thành tổng tiền cho lần chạy. Khi suất phân bổ hoặc giá thực tế đổi, mới cập nhật căn cứ tương ứng cho lần tính mới.

Nguyên liệu lấy từng lượng từ BOM và giá vật tư theo ngày; bao bì lấy từng lượng từ cấu hình và giá theo ngày. Các khoản máy/nhà xưởng, vận chuyển, nhân công dùng suất nhập tay đã có căn cứ Excel, không có kết nối tự động với phần mềm khấu hao/lương.

### 2. Các nhóm chi phí được thể hiện chi tiết ở đâu?

| Nhóm | Nơi nhập cấu thành | Nơi xem trong kết quả |
|---|---|---|
| Nguyên liệu | BOM năm vật tư + Giá nhà cung cấp | Nguồn dữ liệu / Diễn giải dòng C3_RM_COST |
| Bao bì | Cấu hình ba vật tư + Giá nhà cung cấp | Diễn giải dòng C3_PK_COST |
| Máy/nhà xưởng/cuộn in | Ba phần tử suất tiền/kg + C3_F_DEPR | Các dòng suất đầu vào và diễn giải dòng C3_DEPR_COST |
| Vận chuyển | Ba phần tử tiền/kg + C3_F_INBOUND | Các dòng suất đầu vào và diễn giải dòng C3_INBOUND_COST |
| Nhân công | Suất 60.000.000 / 12.714 kg + C3_F_LABOR | Dòng suất đầu vào và diễn giải C3_LABOR_COST |
| Tổng | C3_F_TOTAL cộng năm nhóm | C3_TOTAL_COST, loại Đầu ra |

Mở **Xem dữ liệu và phiên bản đã sử dụng** để đối chiếu nguồn đã chốt. Kết quả không tự đổi khi sửa dữ liệu hiện tại; tạo lần tính mới rồi tạo kịch bản giá bán mới nếu muốn áp dụng thay đổi.

Nếu cần giao diện có cây cha–con mở rộng từng dòng ngay trong bảng kết quả, đó là phần giao diện chưa có trong mô hình hiện tại; bài này không giả định tính năng đó đã tồn tại.

### 3. Bảng tìm lỗi

| Hiện tượng | Cần kiểm tra |
|---|---|
| “Lần tính cần đúng một dòng đầu ra…” | Dòng tổng phải Đầu ra, phạm vi Sản xuất, phần tử Tiền tệ không có đơn vị mặc định; không có hai dòng Đầu ra. |
| Kiểm thử đạt nhưng Run vẫn lỗi | Thử công thức chưa kiểm tra đủ nguồn sản xuất/ngày/cấu hình dòng tổng. Đọc thông báo Run, làm checklist bước 6 và 9. |
| Không tìm thấy giá/BOM/bao bì | Kiểm tra cả ngày và trạng thái phiên bản. BOM/bao bì Nháp: mở đúng phiên bản, nhấn Kích hoạt phiên bản → Xác nhận kích hoạt. Giá mua Nháp: mở chi tiết giá, nhấn Kích hoạt giá → Xác nhận kích hoạt, rồi tạo lần tính mới. |
| Nhiều nguồn phù hợp | Có giá/phiên bản/gán bao bì trùng kỳ? Không tự lấy mới nhất hoặc xóa lịch sử. |
| Không quy đổi được gói ↔ túi | Đúng cặp đơn vị, hệ số 50, cùng nhóm, đúng ngày, chỉ một bản phù hợp? |
| C3_RUN_KG của 1 gói không ra 0,018 | SKU phải 0,9 KG mỗi túi; đơn vị bán là túi; Run chọn Gói 18 g; có quy đổi 1 túi = 50 gói. |
| C3_BASIS_KG bằng 0 hoặc 0,018 | Bài luôn nhập 1 KG. 0 gây chia cho 0; 0,018 khiến dùng suất 1 kg như tiền một gói. |
| Một gói có 50 túi nhỏ | Cơ sở đóng gói có chọn nhầm 1 Gói thay vì 1 Túi không? Bảng bao bì là 50 túi nhỏ cho 1 Túi lớn. |
| Nguyên liệu cao gấp khoảng 55,56 lần | Có dùng định mức 1 kg nhưng gán sản lượng chuẩn 1 Gói không? Đầu ra BOM phải 1 KG. |
| Máy/nhân công sai 50 lần | Có nhân suất tiền/kg nhập tay với 50 dù công thức đã tự quy khối lượng không? |
| Giá khác vài phần số lẻ | Phần tử/dòng có làm tròn 6 thay vì 8 không? Đọc số lưu đầy đủ, không chỉ VND hiển thị tròn đồng. |
| Giá bán túi chỉ khoảng vài nghìn | Có lấy nhầm nguồn 1 Gói hoặc 50 Gói thay cho nguồn 1 Túi không? |
| So sánh bị chặn | Cùng SKU nhưng khác đơn vị đầu ra vẫn không cùng cơ sở giá. Dùng hai nguồn 1 Túi. |
| Sửa nguồn nhưng giá cũ không đổi | Giá thành/giá bán đã tính giữ lịch sử; tạo lần/kịch bản mới. |

Nếu cần hỗ trợ, gửi **mã lần tính, mã tham chiếu, ngày, sản phẩm/SKU và thông báo**. Không cần chạy lại nhiều lần cùng cấu hình chưa sửa; các lần đều sẽ gặp cùng lỗi.

### 4. Phiếu kiểm tra

- [ ] Một gói cơ sở là 18 g; một túi bán là 50 gói = 900 g.
- [ ] BOM chuẩn 1 KG; bao bì chuẩn 1 Túi; SKU 0,9 KG/Túi.
- [ ] Đã có quy đổi 1 Túi = 50 Gói, nguồn hợp lệ.
- [ ] Nguyên liệu có năm dòng lượng/giá; bao bì có ba dòng lượng/giá.
- [ ] Máy/nhà xưởng và vận chuyển có các khoản cấu thành riêng; tiền nhập là cho cơ sở 1 kg.
- [ ] Không nhập năm tổng tiền của cách cũ vào phương án C3_SCHEME_UNIT.
- [ ] Nguồn sản xuất đủ trạng thái/ngày; tất cả công thức và phương án đã kích hoạt.
- [ ] **Dòng C3_TOTAL_COST là Đầu ra**, nguồn Công thức, không nhầm với Dữ liệu đầu vào.
- [ ] Chạy 1 Gói ra khoảng 1.907,39 đồng; chạy 1 Túi ra khoảng 95.369,48 đồng.
- [ ] Giá bán hai kênh dùng nguồn **1 Túi**, phí cố định minh họa là mỗi Túi.
- [ ] Đã thay phí/thuế minh họa bằng chính sách xác nhận trước khi báo giá thật.
- [ ] Lưu số lần tính, mã kịch bản, ngày và tài liệu căn cứ tại nơi công ty quản lý.

## Tài liệu tra cứu và phạm vi kiểm chứng

- [03. Thứ tự khởi tạo](03_THU_TU_KHOI_TAO_DU_LIEU.md).
- [04. Danh mục](04_HUONG_DAN_DANH_MUC.md), [05. Sản xuất](05_HUONG_DAN_SAN_XUAT.md).
- [06. Công thức và giá thành](06_HUONG_DAN_FORMULA_VA_COSTING.md), [07. Giá bán](07_HUONG_DAN_PRICING.md).
- [10. Lỗi thường gặp](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md), [12. Từng trường nhập](12_FIELD_REFERENCE.md), [Giới hạn hiện tại](GAP_REGISTER.md).

Luồng mới đã được kiểm chứng trên **PostgreSQL kiểm thử riêng**: tạo dữ liệu định mức/giá, kiểm thử và kích hoạt bốn công thức, kích hoạt phương án, chạy thành công 1 Gói, 50 Gói và 1 Túi; đồng thời tái hiện lỗi khi đặt dòng tổng thành Dữ liệu đầu vào. Nguồn sản xuất trong phép thử đã được chuẩn bị Đang hiệu lực; việc này không đồng nghĩa UI hiện có đủ nút tự chuyển trạng thái nguồn.

Không có thay đổi code nghiệp vụ, schema hoặc dữ liệu đang dùng để tạo tài liệu. Ba lần lỗi thực tế chỉ được đọc để xác định nguyên nhân.


