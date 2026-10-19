# 09. Thực hành từ A–Z: tính giá cà phê Cappuccino

**[DEMO]** Bài học này dùng đúng bộ mẫu đã có trong dự án, không tạo một bộ số liệu mới. Mục tiêu cuối: tính **10 hộp**, tổng **583.000 VND**, giá thành **58.300 VND/hộp**, rồi giải giá bán với margin 20% sau phí/thuế và đọc nguồn của từng con số.

## Chuẩn bị và cách học

Mở URL hệ thống được người phụ trách cung cấp; trang `/` dẫn vào danh mục. Tài liệu dùng ngày cố định **07/10/2026 cho Costing**, **08/10/2026 cho Pricing**. Không thay bằng ngày hiện tại khi đối soát Golden.

1. Tìm mã `DEMO_CAPPUCCINO` ở Sản phẩm và `DEMO_COSTING_SCHEME` ở Phương án tính giá thành.
2. Nếu chưa có, dừng bài chạy và nhờ người phụ trách chuẩn bị môi trường đào tạo. Không tự nhập trùng hàng chục mã DEMO, không đổi trạng thái trực tiếp trong DB.
3. Các bước 1–17 là **kiểm tra dữ liệu đã chuẩn bị**, đồng thời đọc chương 04–06/12 để biết cách tạo từng đối tượng. Nguồn sản xuất mới lưu Nháp chưa thể đưa vào hiệu lực hoàn toàn qua UI; kỳ chi phí chung chưa có form. Đây là giới hạn sản phẩm, không phải bạn bỏ sót thao tác.
4. Các bước 18–22 là thao tác thật trên UI: tạo Run, xem diễn giải/snapshot, tạo Scenario riêng và so sánh. Dùng mã kịch bản `TRAIN_…` chưa tồn tại. Không sửa mẫu đã chốt.

Ghi vào phiếu học: mã Run, mã Scenario, ngày, tổng/đơn vị, mã nguồn Formula/Scheme, kết quả kiểm tra. Tick từng ô sau khi thấy đúng dữ liệu. Master đơn vị toàn cục có thể được tái sử dụng; nếu đã có KG/G/HOUR/MINUTE tương thích, bộ mẫu không tạo thêm bản trùng.

## Bước 1 — Kiểm tra tiền tệ

**Vì sao cần:** mọi giá mua, đơn giá nguồn lực, biến tiền và kết quả Golden phải cùng tiền VND. **Tiếp theo:** kiểm tra các đơn vị và quy đổi ở bước 2.

**DỮ LIỆU DANH MỤC → Tiền tệ**. Tìm VND, mở **Xem chi tiết**. VND hoạt động, số chữ số thập phân 0. USD hoạt động, số chữ số 2 dùng cho bài ngoại tệ tùy chọn.

- [ ] VND có thể chọn trên form; giá/rate/CE của Golden đều VND.
- [ ] Không hiểu số chữ số hiển thị 0 là database chỉ lưu số nguyên; bộ tính vẫn lưu đủ độ chính xác.

Nếu cần luyện tạo tiền tệ, đọc 04/12 trên dữ liệu đào tạo riêng; mã tiền 3 ký tự không được trùng. Không đổi mã khóa chính của VND.

## Bước 2 — Kiểm tra nhóm đơn vị, đơn vị và quy đổi

**Vì sao cần:** định mức dùng gam/phút nhưng nguồn giá dùng kilôgam/giờ; bộ tính chỉ đổi được khi có dữ liệu quy đổi. **Tiếp theo:** kiểm tra biến chi phí ở bước 3.

Mở **Nhóm đơn vị tính → Đơn vị tính → Quy đổi đơn vị tính**, tìm các đơn vị sau:

| Mã dự kiến | Nhãn | Đại lượng | Vai trò |
|---|---|---|---|
| KG | Kilôgam (kg) | MASS | Đơn vị giá mua nguyên liệu |
| G | Gam (g) | MASS | Đơn vị dòng BOM |
| HOUR | Giờ (h) | TIME | Đơn vị đơn giá máy/người |
| MINUTE | Phút (phút) | TIME | Đơn vị thời gian Routing |
| DEMO_PIECE | Cái | COUNT | Đơn vị giá/dòng bao bì |
| DEMO_BOX_UOM | Hộp | COUNT | Đơn vị đầu ra Run/Recipe/basis |

Quy đổi: **G→KG factor 0.001**; **HOUR→MINUTE factor 60**, hiệu lực từ 01/10/2026. Bộ tính dùng nghịch đảo của quy đổi thời gian khi đổi phút thành giờ. Không cần tạo thêm MINUTE→HOUR vì hai cặp cùng phù hợp có thể gây mơ hồ.

- [ ] Có đúng một quy đổi áp dụng cho từng cặp tại 07/10; không có bản chung/riêng cùng phù hợp.
- [ ] Hiểu 200 g×10=2 kg và 3 phút×10=0,5 giờ nhờ dữ liệu quy đổi, không phải mã hard-code.

## Bước 3 — Kiểm tra sáu phần tử chi phí

**Vì sao cần:** công thức và phương án cần đúng mã biến, kiểu tiền và phạm vi tính; tên giống nhau không thay thế được mã. **Tiếp theo:** kiểm tra vật tư đầu vào ở bước 4.

**Phần tử chi phí**, tìm `DEMO_`. Sáu mã sau là MONEY/VND, không có UoM, phạm vi kế toán INVENTORY_COST, phạm vi chi phí MANUFACTURING, scale 6/HALF_UP, đang hoạt động:

| Mã | Vai trò trong phương án | Nguồn |
|---|---|---|
| DEMO_MATERIAL_COST | Nguyên liệu | SYSTEM |
| DEMO_PACKAGING_COST | Bao bì | SYSTEM |
| DEMO_RESOURCE_COST | Máy và nhân công gộp | SYSTEM |
| DEMO_OVERHEAD_COST | Chi phí chung | SYSTEM |
| DEMO_DIRECT_COST | Tổng trực tiếp | FORMULA |
| DEMO_FULL_COST | Tổng đầu ra | FORMULA |

- [ ] Không tạo hai phần tử máy/nhân công mới để thay Golden: mẫu tách hai nguồn trong trace của RESOURCE, không tách hai CE.
- [ ] Nhóm chi phí tùy chọn không phải CostPool và không cần tự tạo cho bài này.

## Bước 4 — Kiểm tra nhóm sản phẩm và vật tư

**Vì sao cần:** BOM, bao bì và giá mua phải cùng tham chiếu đúng Item, loại và đơn vị. **Tiếp theo:** kiểm tra nhà cung cấp ở bước 5.

**Nhóm sản phẩm** có `DEMO_COFFEE`. **Vật tư / Hàng hóa** có bốn mã:

| Item | Loại lưu | Đơn vị cơ sở/mua/sản xuất |
|---|---|---|
| DEMO_INSTANT_COFFEE — Cà phê hòa tan | RAW_MATERIAL — Nguyên liệu | KG |
| DEMO_SUGAR — Đường | RAW_MATERIAL — Nguyên liệu | KG |
| DEMO_SACHET — Túi sachet | PACKAGING — Bao bì | Cái |
| DEMO_BOX — Hộp giấy | PACKAGING — Bao bì | Cái |

Tất cả hoạt động và theo dõi tồn kho. Cờ này là master; bài không thực hiện nhập/xuất kho. Item bao bì là vật tư đầu vào, khác SKU hộp thành phẩm.

- [ ] Nhìn thấy tên/mã và đơn vị thân thiện, không chọn theo ID thô.

## Bước 5 — Kiểm tra nhà cung cấp

**Vì sao cần:** mỗi báo giá cần một nhà cung cấp đang hoạt động để trở thành nguồn Costing hợp lệ. **Tiếp theo:** kiểm tra bốn báo giá ở bước 6.

Mở **Nhà cung cấp**, tìm `DEMO_SUPPLIER` — Nhà cung cấp mẫu, tiền tệ mặc định VND, đang hoạt động. Danh mục này không tự tạo báo giá khi lưu.

- [ ] Nhà cung cấp hoạt động; không thêm Supplier thứ hai có giá cà phê cùng kỳ trong bài Golden.

## Bước 6 — Kiểm tra giá nhà cung cấp

**Vì sao cần:** lượng định mức chỉ ra nhu cầu; giá mua mới chuyển nhu cầu ấy thành tiền. **Tiếp theo:** kiểm tra Product và đơn vị giá thành ở bước 7.

Mở **Giá nhà cung cấp**, lọc nhà cung cấp mẫu. Đối chiếu giá hiệu lực tại 07/10/2026:

| Item | Giá VND | Đơn vị giá | Bắt đầu | Kết thúc |
|---|---:|---|---|---|
| Cà phê hòa tan |100.000|KG|01/10/2026|31/10/2026|
| Đường |20.000|KG|01/10/2026|Trống|
| Túi sachet |500|Cái|01/10/2026|Trống|
| Hộp giấy |5.000|Cái|01/10/2026|Trống|

Nguồn mẫu đã được chuẩn bị **EFFECTIVE**; min_qty 0, giá chưa gồm thuế, tax_rate 0, tax_recoverable_ratio 1. Nguồn/tham chiếu mang dấu `DEMO_CAPPUCCINO_V1`. Ngày cuối giá Costing được bao gồm. Ngày 31/10 vẫn dùng 100.000/kg.

- [ ] Có đúng một giá đủ điều kiện cho mỗi Item/đơn vị/ngày; min_qty không vượt lượng dùng.
- [ ] Nếu tự tạo thử, không bỏ trống min_qty/tax_recoverable_ratio; chúng bắt buộc dù có gợi ý 0/1.
- [ ] Lưu giá mới ở Nháp không làm nó thành nguồn tính; không tìm nút “duyệt giá” chưa tồn tại.

## Bước 7 — Kiểm tra sản phẩm

**Vì sao cần:** Product là đối tượng gốc mà BOM, bao bì và Routing cùng gắn vào. **Tiếp theo:** kiểm tra quy cách bán SKU ở bước 8.

**Sản phẩm → DEMO_CAPPUCCINO — Cà phê Cappuccino mẫu**. Nhóm DEMO_COFFEE, **Đơn vị tính giá thành** là Hộp, đang hoạt động. Model hiện dùng `costing_uom`, không phải trường `base_uom` như tài liệu cũ.

- [ ] Sản phẩm là đối tượng nghiệp vụ gốc, không tự là Item nguyên liệu hoặc SKU.

## Bước 8 — Kiểm tra SKU

**Vì sao cần:** SKU xác định quy cách bán và liên kết bao bì; lượng tịnh 0,5 kg không thay số hộp cần tính. **Tiếp theo:** kiểm tra lượng nguyên liệu ở bước 9.

**SKU → DEMO_CAPPUCCINO_BOX20 — Cappuccino 20 gói / hộp**. Thuộc Product trên, đơn vị bán Hộp, lượng tịnh 0.5 KG, đang hoạt động.

- [ ] Đơn vị bán Hộp khác lượng tịnh KG; lượng tịnh không phải quantity Run.
- [ ] Bài dùng 10 Hộp; không nhập 10 KG rồi kỳ vọng cùng tổng 583.000.

## Bước 9 — Kiểm tra BOM

**Vì sao cần:** lượng 200 g/300 g chỉ đúng trên cơ sở đầu ra 1 Hộp và phiên bản/ngày đã chọn. **Tiếp theo:** kiểm tra cấu hình bao bì và liên kết SKU ở bước 10.

**SẢN XUẤT → BOM / Công thức sản xuất → DEMO_BOM_CAPPUCCINO**. Mở danh sách phiên bản, chọn **phiên bản 1 Đang hiệu lực**, không chọn bản 2 Nháp chỉ vì số lớn hơn.

Thông tin: output_qty 1 Hộp, yield_rate 1, hiệu lực từ 01/10/2026. Thành phần: thứ tự 10 cà phê 200 G; thứ tự 20 đường 300 G; scrap_rate 0, không optional/substitution.

- [ ] Định mức cho 1 Hộp;10 Hộp cần 2 KG cà phê+3 KG đường.
- [ ] Bản đã chốt không sửa được. Muốn luyện sửa, mở bản 2 Nháp, không đưa nó vào hiệu lực chồng v1.

## Bước 10 — Kiểm tra cấu hình bao bì và gán SKU

**Vì sao cần:** bao bì được chọn qua liên kết SKU; cơ sở của lượng dòng còn phải nhập lại rõ ràng trên Run. **Tiếp theo:** kiểm tra nơi thực hiện công đoạn ở bước 11.

**Cấu hình bao bì → DEMO_PACK_CAPPUCCINO → phiên bản 1 Đang hiệu lực**. Hai dòng:20 Túi sachet/Cái/cấp PRIMARY và 1 Hộp giấy/Cái/cấp SECONDARY. Gán `DEMO_CAPPUCCINO_BOX20` là liên kết chính từ 01/10/2026.

Cấu hình không có output_qty/output_uom trên version. Người chạy phải nhập **Sản lượng cơ sở đóng gói 1, Đơn vị cơ sở đóng gói Hộp** ở bước 18. Các dòng 20+1 đã là lượng cho cơ sở ấy.

- [ ] Có đúng một assignment chính hiệu lực; không tự nhân thêm theo cấp cha.
- [ ] Không có điều kiện thị trường/mẫu in trong Golden.

## Bước 11 — Kiểm tra trung tâm sản xuất

**Vì sao cần:** công đoạn và nguồn lực phải cùng thuộc trung tâm phù hợp; trung tâm không tự cung cấp đơn giá. **Tiếp theo:** kiểm tra máy và nhân công ở bước 12.

**Trung tâm sản xuất** có `DEMO_WC_MIXING` — Khu vực phối trộn mẫu; `DEMO_WC_PACKING` — Khu vực đóng gói mẫu. Cả hai hoạt động. Trung tâm là nơi làm, không phải đơn giá.

- [ ] Hai mã/tên đúng và đều đang hoạt động; không cần nhập hoặc sửa công suất cho Golden này.

## Bước 12 — Kiểm tra nguồn lực

**Vì sao cần:** Routing tham chiếu máy/người cụ thể; đơn giá theo ngày được tra từ nguồn lực đó. **Tiếp theo:** kiểm tra đơn giá ở bước 13.

**Nguồn lực** có `DEMO_MIXER` loại MACHINE thuộc `DEMO_WC_MIXING` và `DEMO_PACKING_LABOR` loại LABOR thuộc `DEMO_WC_PACKING`. Chọn đúng mã khi xem Routing, không ghép nhân công sang khu phối trộn.

- [ ] Hai nguồn lực đang hoạt động, đúng loại/trung tâm; chưa gắn giá trực tiếp lên Routing.

## Bước 13 — Kiểm tra đơn giá nguồn lực

**Vì sao cần:** cùng số phút nhưng đơn giá/ngày khác sẽ tạo chi phí khác; giờ và phút phải đổi đúng. **Tiếp theo:** kiểm tra thời gian công đoạn ở bước 14.

**Đơn giá nguồn lực** tại 07/10: máy 120.000 VND/HOUR, nhân công 60.000 VND/HOUR; rate_type STANDARD; nguồn EFFECTIVE từ 01/10 đến 31/10/2026.

- [ ] Một nguồn cho mỗi Resource/ngày; thêm ACTUAL cùng ngày vẫn có thể gây lỗi mơ hồ, vì resolver chưa chọn rate_type.
- [ ] Đơn vị tính giá là Giờ; Routing lưu Phút và cần quy đổi.

## Bước 14 — Kiểm tra quy trình/công đoạn

**Vì sao cần:** thời gian chạy cần cơ sở sản lượng, còn setup tính một lần mỗi Run; hai giá trị không cộng chung khi lưu. **Tiếp theo:** kiểm tra phân bổ chi phí chung ở bước 15.

**Quy trình sản xuất → DEMO_ROUTE_CAPPUCCINO → phiên bản 1**, batch_size 1 Hộp:

| Thứ tự | Mã công đoạn | Trung tâm / nguồn lực chính | Setup | Run | Cơ sở |
|---:|---|---|---:|---:|---|
|10|DEMO_MIX|Phối trộn / DEMO_MIXER|0|3 phút|1 Hộp|
|20|DEMO_PACK|Đóng gói / DEMO_PACKING_LABOR|0|6 phút|1 Hộp|

- [ ] Cùng 1 Hộp basis;10 Hộp dùng 30 phút máy +60 phút nhân công.
- [ ] Không sao chép giá 120.000/60.000 vào công đoạn; engine tra ResourceRate theo ngày.
- [ ] Bài setup khác 0 ở chương 08; DEMO setup 0 nên không dùng Golden để kết luận setup được scale.

## Bước 15 — Kiểm tra nhóm chi phí và phân bổ

**Vì sao cần:** phân bổ cần cả tiền kỳ và công suất làm mẫu số; chỉ có tên pool/rule chưa đủ. **Tiếp theo:** kiểm tra công thức tổng hợp ở bước 16.

**Nhóm chi phí chung → DEMO_FACTORY_OVERHEAD**, loại FACTORY_FIXED; **Quy tắc phân bổ → DEMO_OVERHEAD_NORMAL**, cơ sở NORMAL_CAPACITY, đơn vị Hộp, priority 100, hiệu lực từ 01/10/2026; condition/formula trống.

Số liệu kỳ đã chuẩn bị:01/10–31/12/2026, amount 530.000 VND, normal_capacity 100 Hộp, trạng thái EFFECTIVE. UI chưa có trang nhập CostPoolPeriod, nên không suy ra amount này từ năm phần tử chi phí hay từ members pool.

- [ ] Hiểu 53.000=530.000×10/100; không lấy toàn 530.000 cho Run 10 hộp.
- [ ] Q không vượt 100 Hộp trong bài dùng pool này.

## Bước 16 — Kiểm tra hai công thức và mẫu test

**Vì sao cần:** Formula quy định khoản nào được cộng, và test xác nhận đúng phép tính trước khi dùng trong phương án. **Tiếp theo:** kiểm tra nguồn của từng dòng phương án ở bước 17.

**CÔNG THỨC & QUY TẮC → Thiết lập công thức**:

```text
DEMO_DIRECT_FORMULA:
$DEMO_MATERIAL_COST + $DEMO_PACKAGING_COST + $DEMO_RESOURCE_COST

DEMO_FULL_FORMULA:
@DEMO_DIRECT_FORMULA + $DEMO_OVERHEAD_COST
```

Công thức đầu ra tương ứng CE DEMO_DIRECT_COST/DEMO_FULL_COST. Phiên bản 1 hiệu lực; phiên bản 2 Nháp dùng luyện tập. Mẫu test `DEMO_GOLDEN_10_BOX`: input 260000/150000/120000/53000, expected 530000 hoặc 583000, tolerance 0.

Mở phiên bản Nháp để xem/kiểm tra, nhập đầu vào và bấm **Kiểm thử**. Không sửa/kích hoạt v2 DEMO trùng ngày v1. Công thức độc lập với Run; test không tự đọc BOM/giá mua.

- [ ] `$` tham chiếu CE; `@` tham chiếu Formula; biến đủ kiểu MONEY/VND.
- [ ] Kết quả test đúng 530.000/583.000; muốn lưu mẫu test dùng nút **Lưu bộ kiểm thử** tại chi tiết phiên bản có plan hợp lệ.

## Bước 17 — Kiểm tra phương án tính giá thành

**Vì sao cần:** Scheme nối các biến với nguồn thực thi và chỉ định đúng một dòng đầu ra chính. **Tiếp theo:** nhập yêu cầu chạy ở bước 18.

**Phương án tính giá thành → DEMO_COSTING_SCHEME → phiên bản 1**. Purpose STANDARD_COST, context_scope SKU; chọn **Kiểm tra cấu hình**. Các dòng:

| Thứ tự | Mã dòng/CE | Loại | Nguồn / tham chiếu |
|---:|---|---|---|
|10|DEMO_MATERIAL_COST|INPUT|SYSTEM: MATERIAL_COST|
|20|DEMO_PACKAGING_COST|INPUT|SYSTEM: PACKAGING_COST|
|30|DEMO_RESOURCE_COST|INPUT|SYSTEM: RESOURCE_COST|
|40|DEMO_OVERHEAD_COST|INPUT|SYSTEM: ALLOCATION: DEMO_OVERHEAD_NORMAL|
|50|DEMO_DIRECT_COST|SUBTOTAL|FORMULA: DEMO_DIRECT_FORMULA v1|
|60|DEMO_FULL_COST|OUTPUT|FORMULA: DEMO_FULL_FORMULA v1|

- [ ] Kiểm tra không có lỗi; đúng một OUTPUT MONEY/VND không UoM, phạm vi MANUFACTURING.
- [ ] Không cộng SUBTOTAL/OUTPUT lặp; không đổi source mode LOOKUP cho bài này.

## Bước 18 — Chạy và đọc giá thành

**Vì sao cần:** tạo kết quả giá thành cùng nguồn/phiên bản đã lưu; kết quả đơn vị sẽ là giá vốn cho Pricing. **Tiếp theo:** kiểm tra kênh bán ở bước 19; giữ mã Run vừa tạo.

**TỔNG QUAN → Lần tính giá thành → + Chạy tính giá**. Nhập:

| Trường | Nhập / chọn |
|---|---|
|Sản phẩm|DEMO_CAPPUCCINO|
|SKU|DEMO_CAPPUCCINO_BOX20|
|Ngày tính giá|07/10/2026|
|Phương án tính giá thành|DEMO_COSTING_SCHEME|
|Sản lượng cần tính|10|
|Đơn vị sản lượng|Hộp|
|Tiền tệ kết quả|VND|
|Loại lần tính|Tiêu chuẩn (STANDARD)|
|Sản lượng cơ sở đóng gói|1|
|Đơn vị cơ sở đóng gói|Hộp|
|Ghi chú|Đào tạo Cappuccino; cơ sở bao bì 20 sachet+1 hộp giấy cho 1 hộp thành phẩm|

Đợi danh sách phụ thuộc tải xong khi đổi Product/SKU/ngày/phương án, kiểm tra lại lựa chọn, rồi **Chạy tính giá**. Thành công tự Đã khóa; không cần bấm nút khóa. Ghi mã Run.

| Khoản | Tính tay | VND |
|---|---|---:|
|Cà phê|200 g×10×0.001×100000|200.000|
|Đường|300 g×10×0.001×20000|60.000|
|Nguyên liệu|200000+60000|260.000|
|Sachet|20×10×500|100.000|
|Hộp giấy|1×10×5000|50.000|
|Bao bì|100000+50000|150.000|
|Máy|3 phút×10/60×120000|60.000|
|Nhân công|6 phút×10/60×60000|60.000|
|Nguồn lực|60000+60000|120.000|
|Trực tiếp|260000+150000+120000|530.000|
|Chi phí chung|530000×10/100|53.000|
|Đầu ra đầy đủ|530000+53000|**583.000**|
|Một hộp|583000/10|**58.300**|

Mở **Nguồn dữ liệu / Diễn giải** từng dòng: MATERIAL thấy hai Item/quy đổi/giá; PACKAGING thấy assignment/basis; RESOURCE thấy máy+người; OVERHEAD thấy kỳ/công suất; FULL thấy Formula. Mở **Xem dữ liệu và phiên bản đã sử dụng**, xác nhận v1 và 2 công thức. Ghi mã nguồn thay vì chỉ chụp tổng.

- [ ] Run Đã khóa, không có lỗi;583.000 và 58.300.
- [ ] Tất cả dòng có nguồn/diễn giải; không cộng 6 dòng thành một tổng mới.

## Bước 19 — Kiểm tra kênh bán

**Vì sao cần:** cùng giá vốn nhưng kênh khác có phí và giả định bán khác; không chọn kênh chỉ vì tên giống ví dụ. **Tiếp theo:** kiểm tra phí/thuế/FX tại ngày định giá ở bước 20.

**GIÁ BÁN → Kênh bán → DEMO_DIRECT**, loại D2C, thị trường VN, tiền VND, hoạt động. Đây là kênh mẫu có phí, khác bài bán trực tiếp không phí ở chương 08.

- [ ] Đúng kênh DEMO_DIRECT; không chọn kênh TRAIN không phí của bài khác.

## Bước 20 — Kiểm tra phí, thuế và FX

**Vì sao cần:** mục tiêu lợi nhuận phải xét sau phí/thuế; ngày Pricing và ngày Costing là hai đầu vào riêng. **Tiếp theo:** tạo kịch bản học viên ở bước 21.

Ngày 08/10/2026:

| Nguồn | Cấu hình | Khoảng Pricing |
|---|---|---|
|COMMISSION|rate 5%, LIST_PRICE, refund 0, tax_inclusive True|01/01/2026 đến trước 01/11/2026|
|PAYMENT_FEE|fixed 1.000 VND/đơn vị, LIST_PRICE, refund 0, tax_inclusive True|Cùng kỳ|
|VN / VAT|rate 10%, SELLING_PRICE, recoverable 0, inclusive True|Cùng kỳ|

Tất cả EFFECTIVE; priority 100; phí áp dụng chung kênh, thuế phạm vi chung. 10% là giả định DEMO, không hướng dẫn thuế suất pháp lý. VND→VND không cần FX; không tạo FX cùng tiền. Dùng USD chỉ ở bài mở rộng 11–12, không thuộc Golden VND này.

- [ ] Không tạo quy tắc VAT/COMMISSION đồng hạng cùng phạm vi kỳ trong bài học.
- [ ] Pricing không bao gồm ngày kết thúc 01/11; khác Costing kết thúc 31/10 bao gồm.

## Bước 21 — Tạo và tính kịch bản giá bán của học viên

**Vì sao cần:** giải giá khách trả sao cho lợi nhuận sau phí/thuế bằng 20% giá khách trả; không chỉ cộng 20% lên vốn. **Tiếp theo:** nhân bản và so sánh với mục tiêu 25% ở bước 22.

**Kịch bản giá bán → + Thêm kịch bản**:

| Trường | Giá trị |
|---|---|
|Mã kịch bản|TRAIN_CAPPUCCINO_20_01; đổi hậu tố nếu mã đã có|
|Tên kịch bản|Cappuccino — đào tạo margin 20%|
|Sản phẩm/SKU|Đúng DEMO ở trên|
|Nguồn giá thành|Run vừa chạy bước 18:07/10,10 hộp,58.300 VND/hộp|
|Kênh bán|DEMO_DIRECT|
|Ngày định giá|08/10/2026|
|Tiền tệ bán|VND|
|Thuế bán hàng|Áp dụng thuế theo quy tắc|
|Mã khu vực áp dụng thuế|VN|
|Mã loại giao dịch|Trống|
|Mã loại tỷ giá|SPOT có thể nhập như mẫu, không dùng vì cùng tiền|
|Phương pháp|Biên lợi nhuận mục tiêu (MARGIN)|
|Biên lợi nhuận mục tiêu (%)|20|
|Markup/lợi nhuận cố định/giá tối thiểu|Để trống|
|Hiệu lực kịch bản|Có thể trống; không thay Ngày định giá|

Bấm **Lưu Nháp**, sau đó **Tính giá bán**. Nếu lỗi vẫn Nháp, sửa nguồn/form theo thông báo; không cần tạo lại mã ngay. Thành công Đã tính, ghi mã Scenario.

Giải tay trước khi đọc UI:

```text
P = (58300 + 1000) / (1/1.1 − 0.05 − 0.20)
P = 89972.41379310 VND/hộp
```

| Cấu thành giá | VND/hộp |
|---|---:|
|Giá khách trả|89.972,41379310|
|Hoa hồng 5%|−4.498,62068966|
|Phí thanh toán|−1.000|
|Thuế 10% trên cơ sở trước thuế|−8.179,31034483|
|Doanh thu thuần sau phí/thuế|76.294,48275861|
|Giá vốn|−58.300|
|Lợi nhuận|17.994,48275861|
|Biên lợi nhuận thực tế|20%|

Lợi nhuận/P=20%; không lấy 58.300×1,2 hoặc lấy P×10% để trừ thuế. Số học sau quantize 8 chữ số lẻ có thể lệch nhỏ ở phép chia tự làm tay; đối soát đúng số đã lưu.

Mở **Nguồn và diễn giải đã lưu**: đúng Run bước 18, margin `CUSTOMER_GROSS_PRICE`, hai loại phí, thuế VAT, không FX. Kiểm tra tổng giá−phí−thuế−vốn−profit=0.

- [ ] Đã tính; giá 89.972,41379310; giá vốn đơn vị 58.300; margin 20%.
- [ ] Phí cố định 1.000 cho 1 hộp, không phải cho 10 hộp của Run.

## Bước 22 — So sánh và bảo toàn lịch sử

**Vì sao cần:** xem chênh lệch trên cùng cơ sở và chứng minh thay đổi giả định không viết lại kết quả cũ. **Tiếp theo:** hoàn tất phiếu học; chọn bài mở rộng ở chương 08 hoặc xử lý sai khác theo chương 10.

Từ Scenario học viên chọn **Nhân bản thành kịch bản mới**, mã `TRAIN_CAPPUCCINO_25_01`, margin 25, cùng Run/ngày/kênh. Lưu Nháp/Tính giá bán; kỳ vọng 97.358,20895522 VND, margin 25%.

Mở **So sánh kịch bản**, lọc Product/SKU, chọn hai bản 20/25, đặt bản 20 làm **Kịch bản mốc**, bấm **So sánh kịch bản**. Chênh giá 7.385,79516212 VND; margin+5 điểm phần trăm. Không tự kết luận giá cao hơn là phương án kinh doanh tốt nhất.

Nếu bộ mẫu future đã chuẩn bị:

| Kiểm tra | Kỳ vọng |
|---|---|
|Mở Run 07/10 cũ|Vẫn 583.000/58.300; nguồn/biểu thức giữ nguyên|
|Tạo Run mới 01/11,10 Hộp, cơ sở 1 Hộp|647.000/64.700 vì cà phê 120.000/kg, máy 144.000/h, người 72.000/h|
|DEMO_PRICING_FUTURE ngày 01/11, dùng Run 07/10 cũ|92.526,00506044; giá vốn vẫn 58.300|
|Scenario mới 01/11 chọn Run tương lai 64.700|102.511,94827101; không phải Golden Pricing future giữ vốn cũ|

- [ ] Bản cũ không đổi; chạy lại tạo Run mới, nhân bản tạo Scenario mới.
- [ ] Hiểu nguồn Costing/ngày Pricing là hai input độc lập.
- [ ] Có thể giải thích con số từ nguồn, không chỉ đọc giá cuối.

## Khi không ra Golden

Kiểm tra theo thứ tự: ngày 07/10/08/10 →10 Hộp, không KG →basis bao bì 1 Hộp →đúng một nguồn hiệu lực →giá/rate cũ →Formula/Scheme v1 →thuế/phí/kênh →margin 20 đúng ô. Đừng đổi số input để “làm cho khớp” tổng; tìm trace chỉ ra nguồn sai khác. [Chương 10](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md) giải thích mã lỗi.

## Phụ lục cho người chuẩn bị môi trường đào tạo

Các lệnh hiện có là `seed_costing_demo`, `verify_costing_demo`, `verify_pricing_demo`; **không có** `seed_pricing_demo`. Lệnh verify có thể tạo dữ liệu/Run/Scenario; không phải chỉ đọc. Task viết tài liệu này **không chạy chúng trên database doanh nghiệp**.

Chỉ người phụ trách dùng khi đã xác nhận kết nối đúng database đào tạo/development/test/staging có schema sẵn:

```powershell
python manage.py seed_costing_demo
python manage.py verify_costing_demo --report artifacts/costing-demo-report.json
python manage.py verify_pricing_demo --report artifacts/pricing-demo-report.json
```

Cơ chế bảo vệ hiện chặn môi trường production. Lệnh không tạo/sửa schema; không tạo công ty hay người dùng. Bộ mẫu không ghi đè bản đã bị sửa khác định nghĩa: nếu báo xung đột dữ liệu thì đối chiếu, không xóa dữ liệu hàng loạt để chạy lại. Chương này giữ thao tác terminal ở phụ lục kỹ thuật, người học chỉ làm UI ở trên.

Nguồn: [seed Costing](../../apps/costing/demo_data.py), [đối soát Costing](../../apps/costing/demo_verification.py), [DEMO Pricing](../../apps/pricing/demo_scenario.py), [guard môi trường](../../config/command_safety.py). Số liệu/Golden trong tài liệu được đối chiếu source và kiểm thử cô lập; chưa có tuyên bố học viên đã hoàn tất UAT trên production.
