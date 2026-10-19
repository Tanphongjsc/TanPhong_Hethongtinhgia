# Ma trận phụ thuộc và ảnh hưởng dữ liệu

[Mục lục](README.md) · [Thứ tự khởi tạo](03_THU_TU_KHOI_TAO_DU_LIEU.md) · [Field Reference](12_FIELD_REFERENCE.md) · [Lỗi thường gặp](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md)

**[HỆ THỐNG HIỆN TẠI]** Đối chiếu source 09/10/2026. “Bắt buộc có trước” bên dưới là điều kiện để tạo qua form hoặc dùng thao tác tương ứng. “Nên có / điều kiện” bao gồm trường tùy chọn và dữ liệu cần khi thực thi. Một bản Nháp lưu thành công không tự đủ điều kiện làm nguồn của engine. Các quan hệ trong bảng là quan hệ thật; không có gán Scheme vào Product/SKU hoặc nhóm chi phí vào Phần tử chi phí ngầm.

## 1. Chuỗi nghiệp vụ

```text
Tiền tệ                    Nhóm đơn vị tính → Đơn vị tính
   ├─ Phần tử chi phí ←─────────────┤
   ├─ Nhà cung cấp                 ├─ Item ← Nhóm sản phẩm
   └─ Giá nhà cung cấp ← Item ─────┤
                                  ├─ Product → SKU
                                  └─ Quy đổi đơn vị chung/riêng

Product → BOM → phiên bản → thành phần Item ────→ MATERIAL_COST
Product → Bao bì → phiên bản → dòng Item ──────→ PACKAGING_COST
SKU ─────→ gán cấu hình bao bì chính theo ngày ─→ PACKAGING_COST
Trung tâm → Nguồn lực → Đơn giá ─┐
Product → Routing → công đoạn ───┴──────────────→ RESOURCE_COST
Nhóm chi phí → Quy tắc + Số liệu kỳ ───────────→ ALLOCATION:<mã>

Phần tử chi phí → Công thức + mẫu kiểm thử → phiên bản hiệu lực
Các nguồn + Công thức → Phương án/phiên bản/dòng → hiệu lực
Product + SKU khi cần + ngày/lượng/đơn vị/tiền → Lần tính Đã khóa

Lần tính Đã khóa + Kênh + phí/thuế/FX khi cần → Kịch bản Đã tính
2–5 Kịch bản cùng hàng/cơ sở → So sánh (chỉ đọc snapshot)
```

Mũi tên từ Nguồn lực về Trung tâm là tùy chọn khi tạo nguồn lực chung. Các nhánh MATERIAL/PACKAGING/RESOURCE/ALLOCATION chỉ bắt buộc nếu phương án thực sự sử dụng nguồn đó. Phần tử chi phí/Công thức có thể chuẩn bị độc lập với Product. Nhóm sản phẩm của Item không tự thành nhóm Product dùng khi chọn phí.

## 2. Danh mục nền tảng và sản phẩm

| Khi tạo | Bắt buộc có trước | Nên có / điều kiện | Được dùng sau bởi |
| --- | --- | --- | --- |
| Tiền tệ | Không cần danh mục nghiệp vụ khác | Thống nhất mã 3 ký tự và số lẻ | CE tiền, giá mua/rate/kỳ, Run, kênh, fee/tax/FX/Scenario |
| Nhóm đơn vị tính | Không cần danh mục khác | Đại lượng đúng | Đơn vị tính; kiểm tra số đo/kiểu/thời gian |
| Đơn vị tính | Nhóm đơn vị tính | Đại lượng và ký hiệu đúng; hoạt động | Item/Product/SKU, Conversion, BOM/Pack/Routing/Rate/PoolPeriod, CE/Run |
| Phần tử chi phí | Mã/tên và kiểu giá trị | Tiền tệ nếu MONEY; đơn vị nếu QUANTITY; nhóm phần tử tùy chọn | Biến Formula, SchemeLine và kết quả Run |
| Nhóm phần tử chi phí | Không có form CRUD hiện tại | Dropdown tùy chọn ở CE; có thể để trống | Phân nhóm từ điển CE; khác Nhóm chi phí chung |
| Nhóm sản phẩm | Mã/tên | UI danh sách phẳng; nhóm cha chưa có editor | Item.category, Product.category, Fee theo nhóm Product |
| Vật tư / Hàng hóa | Đơn vị cơ sở | Nhóm, đơn vị mua/sản xuất; đơn vị MASS/LENGTH khi có số đo | Giá mua, BOM/Pack lines, Conversion riêng; Product.output_item/SKU.sell_item nếu chọn |
| Nhà cung cấp | Mã/tên | Tiền tệ mặc định tùy chọn; không cần Item trước | Giá nhà cung cấp |
| Quy đổi đơn vị chung | Hai đơn vị khác nhau cùng nhóm | Hệ số dương, ngày/phạm vi đúng, nguồn duy nhất | Validation BOM/Pack; quy đổi lượng/giá/thời gian của Run |
| Quy đổi riêng theo Item | Hai đơn vị khác nhau và Item | Cần Item khi khác nhóm; không tự tạo từ số đo | Các chuyển đổi có căn cứ theo vật tư |
| Sản phẩm | Đơn vị tính giá thành | Nhóm sản phẩm; Item đầu ra tùy chọn | SKU, BOM/Pack/Routing, Run, Pricing qua Run |
| SKU | Product; Đơn vị bán; Lượng tịnh > 0; Đơn vị lượng tịnh | Item bán, barcode tùy chọn | Gán bao bì; Run; Fee riêng SKU; Pricing/Compare |
| Giá nhà cung cấp | Supplier, Item, UoM giá, Currency; ngày bắt đầu | Giá/min_qty không âm; quy đổi; metadata thuế/nguồn | MATERIAL_COST/PACKAGING_COST; gián tiếp Pricing qua Run |

Product không bắt buộc SKU. Product và SKU không bắt buộc gắn Item. Mỗi vật tư có đơn vị riêng ở BOM/bao bì/giá; thay đơn vị mua trên Item không tự thay đơn vị ở những bản ghi ấy. Quy đổi chỉ một cặp trực tiếp hoặc nghịch đảo phù hợp; không tự nối chuỗi. Cho lưu nhiều nguồn quy đổi không có nghĩa engine ưu tiên Item-specific hơn general.

## 3. Sản xuất: header, phiên bản, dòng và liên kết

| Khi tạo / dùng | Bắt buộc có trước | Nên có / điều kiện | Được dùng sau bởi |
| --- | --- | --- | --- |
| Header BOM | Product; mã/tên | Mô tả; hoạt động | RecipeVersion và MATERIAL_COST |
| Phiên bản BOM | Header; sản lượng chuẩn > 0; UoM đầu ra; thu hồi `(0,100%]` | Ngày bắt đầu nếu có kết thúc; đủ dòng để tính | Nhu cầu vật tư theo quy mô, thu hồi và hao hụt |
| Thành phần BOM | Phiên bản còn sửa; Item; qty > 0; UoM; hao hụt `[0,100%)`; thứ tự | Quy đổi nếu khác UoM gốc; công đoạn/ghi chú tùy chọn | Giá nguyên liệu; tùy chọn/nhóm thay thế hiện bị engine chặn |
| Header bao bì | Product; mã/tên | Mô tả; hoạt động | Phiên bản và liên kết SKU |
| Phiên bản bao bì | Header | Số đo ≥ 0; MASS/LENGTH UoM khi nhập số đo; ngày/lý do | Dòng bao bì; không chứa output quantity/UoM |
| Thành phần bao bì | Phiên bản còn sửa; Item; cấp; qty > 0; UoM; thứ tự | Quy đổi; cấp cha/số đơn vị cha chỉ mô tả | PACKAGING_COST; market/artwork có giá trị hiện bị chặn |
| Gán SKU–bao bì | Config và SKU cùng Product; ngày bắt đầu | Cấu hình chính; ngày kết thúc; tránh nhiều chính cùng kỳ | Chọn Config identity, sau đó chọn version theo ngày Run |
| Trung tâm sản xuất | Mã/tên | Công suất/công suất bình thường ≥ 0; UoM nếu có giá trị | Resource và RoutingOperation |
| Nguồn lực | Mã/tên; loại MACHINE/LABOR/WORK_CENTER/SERVICE | Trung tâm tùy chọn; công suất + đơn vị khi nhập | ResourceRate và Nguồn lực chính công đoạn |
| Đơn giá nguồn lực | Resource; rate_type; amount ≥ 0; Currency; per_uom; start | End/source; quy đổi thời gian; trạng thái hiệu lực khi tính | RESOURCE_COST |
| Header quy trình | Product; mã/tên | Hoạt động | RoutingVersion |
| Phiên bản quy trình | Header | Batch_size > 0 cùng batch_uom nếu nhập; ngày/lý do | Công đoạn; cơ sở lô dự phòng khi tính |
| Công đoạn | Phiên bản còn sửa; thứ tự dương/duy nhất; code/name; setup/run ≥ 0 | Center/resource tùy chọn trên form; TIME UoM nếu time khác 0; cặp cơ sở lượng | RESOURCE_COST; thực thi thời gian khác 0 cần Resource và cơ sở rõ |
| Nhóm chi phí chung | Mã/tên; loại nhóm | Mô tả; hoạt động | AllocationRule và CostPoolPeriod |
| Quy tắc phân bổ | Pool; code/name; basis; priority32bit; start | Basis_uom; formula_code text; end | Nguồn Scheme SYSTEM `ALLOCATION:<code>` |
| Số liệu kỳ nhóm chi phí (`CostPoolPeriod`) | Không có form UI | Engine cần tiền/currency, capacity > 0/UoM, kỳ/trạng thái hợp lệ | ALLOCATION theo công suất bình thường |
| Lịch công suất (`CapacityCalendar`) | Chưa có module/form/model trong source đã kiểm tra | Không tự tạo từ công suất header | Chưa có nguồn lịch công suất để tích hợp phân bổ |

SKU assignment không trỏ version. BOM/Routing không có FK gán riêng SKU. Mỗi công đoạn có một primary_resource, không có bảng nhiều nguồn lực. Quy tắc không có target Product/SKU/Resource hoặc dòng phân bổ. Pool không có danh sách thành viên CostElement. Không suy ra các quan hệ đó từ tên module.

## 4. Công thức, phương án và thực thi

| Khi tạo / thực hiện | Bắt buộc có trước | Nên có / điều kiện | Được dùng sau bởi |
| --- | --- | --- | --- |
| Công thức và phiên bản đầu | Mã/tên, biểu thức hợp lệ, CE/Formula được tham chiếu đã có | Phần tử kết quả tùy chọn; ngày cần trước activation | Formula dependencies, Scheme FORMULA line |
| Bộ kiểm thử đã lưu | Formula đã lưu; kế hoạch hợp lệ; đủ biến có kiểu | Tên/kết quả mong đợi bắt buộc khi lưu; khi chỉ thử có thể trống | Kích hoạt Formula; tái dùng ở các version cùng Formula |
| Kích hoạt FormulaVersion | Header active, start, kiểm tra kiểu/đơn vị/vòng, ít nhất một test active và tất cả đạt | Dependencies EFFECTIVE duy nhất đúng ngày; tối đa 200 test active | Dropdown FormulaVersion của Scheme; tính theo ngày |
| Header/phiên bản Scheme | Mã/tên và các thông tin form | Chưa tự gán Product/SKU/currency/quantity | SchemeLine, activation, Run |
| Dòng SYSTEM | CE đúng kiểu/đơn vị; mã registry | ALLOCATION cần Rule hiệu lực; chỉ mã đã đăng ký | Nguồn tính theo context của Run |
| Dòng FORMULA | FormulaVersion cụ thể EFFECTIVE/VALID, active, kiểu/ngày phù hợp | Mỗi CE lá cần đúng một dòng cung cấp nguồn | Tính theo graph phụ thuộc |
| Dòng MANUAL | Nhãn/mã/type của dòng; CE nếu cần kiểu có đơn vị | Nếu không CE, INFO→TEXT, dòng khác→NUMBER; min/max nếu dùng | Các trường bắt buộc sinh trên RunForm |
| Kích hoạt SchemeVersion | Start; active; nguồn/type/ref hợp lệ; đủ biến lá; không vòng/nguồn chưa hỗ trợ | Kiểm tra chưa xác nhận toàn bộ giá/rate/kỳ ngày chạy | Có thể chọn trên Run đúng ngày |
| Run | Product; Scheme có duy nhất EFFECTIVE version tại ngày; quantity > 0; active UoM/Currency | SKU cho bao bì; cơ sở đóng gói; MANUAL inputs; các nguồn cần dùng | Kết quả/snapshot/trace; Run LOCKED làm giá vốn Pricing |
| Xem chi tiết/trace/snapshot cũ | Run và kết quả đã lưu | Không cần nguồn danh mục hôm nay còn hiệu lực | Đọc/đối chiếu lịch sử, không recost |
| Tính lại từ Run | Run nguồn; context mới và nguồn hiện tại phù hợp | Phương án/ngày/manual hiện tại; tạo record mới | Run mới liên kết bản cũ, không thay kết quả cũ |

### Dữ liệu cần thêm theo nguồn của phương án

| Nguồn SYSTEM | Điều kiện engine thực sự cần | Không được giả định |
| --- | --- | --- |
| MATERIAL_COST | Một BOMVersion EFFECTIVE của Product đúng ngày, header active, đủ dòng; Item/UoM active; giá và quy đổi duy nhất; không optional/substitute | Bản mới nhất tự được dùng; giá rẻ nhất được chọn; bán thành phẩm tự roll-up nhiều cấp |
| PACKAGING_COST | SKU; một primary assignment đúng ngày/cùng Product/config active; một EFFECTIVE version có dòng; explicit packaging_quantity/UoM; giá/quy đổi | Cơ sở mặc định 1 SKU; units_per_parent tự nhân; chọn market/artwork |
| RESOURCE_COST | Một RoutingVersion EFFECTIVE đúng Product/date; công đoạn; nonzero time cần Resource+TIME; center khớp; runtime có cơ sở op hoặc batch; một rate EFFECTIVE/time conversion | Tự chọn rate_type; tự suy thời gian từ capacity; setup nhân theo sản lượng |
| RUN_QUANTITY | CE kiểu QUANTITY/UoM; quy đổi từ context Product/SKU đúng | Tự tạo kiểu tiền/đơn vị phái sinh hoặc tự tính giá bán |
| ALLOCATION:<code> | Rule EFFECTIVE đúng mã/ngày, Pool active; NORMAL_CAPACITY, formula_code/conditions trống; một kỳ EFFECTIVE, tiền không âm/cùng Currency; capacity dương/đơn vị; lượng không vượt capacity | Mọi basis trong dropdown thực thi được; WorkCenter capacity tự thành số liệu kỳ; priority tự chọn Rule khác mã |

**[CHƯA HỖ TRỢ]** Source mode LOOKUP/EXTERNAL và mã SYSTEM chưa đăng ký không trở thành khả năng thực thi chỉ vì form có cấu hình. Formula DSL không tự truy cập database/mạng hoặc tạo FX/quy đổi đơn vị; phải có nguồn typed tương thích. Không hứa công thức tổng quát Tiền × Số lượng nếu engine không hỗ trợ đại lượng phái sinh ấy.

## 5. Pricing và phân tích

| Khi tạo / thực hiện | Bắt buộc có trước | Nên có / điều kiện | Được dùng sau bởi |
| --- | --- | --- | --- |
| Kênh bán | Mã/tên/loại | Default Currency tùy chọn; market/seller/platform text | Fee và Scenario; không tự đồng bộ biểu phí |
| Quy tắc phí | Channel; fee_type/fee_base text; tỷ lệ hoặc fixed; dates/status | Currency nếu fixed/floor/cap; category/SKU cùng nhóm khi cùng chọn; tax inclusion/ratio/priority | Fee candidates; Scenario engine chọn theo type/specificity/priority |
| Quy tắc thuế | Jurisdiction/type/base text; rate hoặc fixed; dates/status | Currency nếu fixed; tax_class/seller/transaction scope; inclusion/recoverable/priority | Tax candidates của Scenario REQUIRED |
| Tỷ giá | Hai Currency khác nhau; rate > 0; rate_type/source_name; effective_at/status | valid_to; nguồn tham chiếu; đúng chiều/loại/thời điểm | Giá vốn/fee/tax tiền khác Currency bán |
| Kết thúc hiệu lực Fee/Tax/FX | Bản EFFECTIVE chưa có end | End tương lai và sau start; không thay giá/phạm vi/status | Nối chính sách kỳ mới theo khoảng nửa mở |
| Scenario Nháp | Product; SKU nếu chọn; đúng base Run LOCKED, per_unit hợp lệ và có lines; Channel/Currency active; pricing_date | Một mục tiêu đúng method; thuế REQUIRED cần jurisdiction; FX type khi đổi tiền; min price | Tính giá bán |
| Tính giá bán | Scenario Nháp và context hợp lệ; giá vốn đã lưu | Fee có thể không có (cảnh báo); REQUIRED tax phải có; FX cần đúng nguồn khi tiền khác | CALCULATED snapshot/hash/waterfall/trace; lỗi giữ DRAFT |
| Nhân bản Scenario | Scenario nguồn; mã mới/đầu vào hợp lệ | Chọn nguồn Costing mới nếu đổi giá vốn | Scenario mới, không đổi bản đã tính |
| So sánh kịch bản | 2–5 Scenario CALCULATED, base Run LOCKED, snapshot schema/hash hợp lệ | Chọn Product để tải candidates; cùng SKU hoặc cùng Product không SKU; cùng output UoM/basis; baseline | Chênh kết quả đã lưu; không tính hay resolve nguồn mới |

Phí theo nhóm dùng **Product.category**, không phải category của vật tư. Phí cùng type chọn SKU > category > chung, rồi priority lớn hơn; hòa lỗi. Thuế cùng type chọn số phạm vi cụ thể rồi priority; hòa lỗi. FX không có winner theo ưu tiên: thiếu hoặc nhiều cùng phù hợp đều lỗi. Tỷ lệ phần trăm không có tiền tệ để “đổi”; chỉ số tiền vốn/phí/thuế cần FX khi khác tiền bán.

## 6. Các dropdown và điều kiện trên form

| Tôi chọn / nhập | UI / backend thay đổi gì? | Vì sao danh sách có thể trống? |
| --- | --- | --- |
| Nhóm đơn vị khi tạo UoM | Liên kết UoM tới đại lượng; validation đo lường/Formula/Conversion dùng quan hệ này | Nhóm chưa có hoặc ngừng hoạt động khi chọn mới |
| Item và UoM trên BOM/Pack | Backend kiểm tra quy đổi trực tiếp nếu khác base_uom | Thiếu cặp hoặc sai ngày/phạm vi; dropdown không tự tạo conversion |
| Số đo Item/Pack; công suất | Đơn vị tương ứng bắt buộc khi có giá trị | Thiếu UoM đúng đại lượng hoặc chưa chọn |
| SKU khi gán Packaging | Chỉ SKU cùng Product của Config; ngày liên kết riêng | Chưa có SKU cùng Product đang hoạt động |
| Trung tâm ở công đoạn | HTMX tải lại Nguồn lực chính: cùng trung tâm hoặc nguồn lực chung; server kiểm tra lại | Resource ở trung tâm khác/ngừng; tham chiếu cũ vẫn có thể được giữ |
| Product ở Run | HTMX tải SKU của Product | Product/SKU ngừng hoặc SKU thuộc Product khác |
| Ngày/Scheme ở Run | Chọn Scheme có phiên bản EFFECTIVE ngày ấy; cần duy nhất; sinh các đầu vào MANUAL | 0 hoặc >1 version phù hợp; Scheme ngừng |
| Scheme dùng PACKAGING_COST | Hai trường cơ sở đóng gói bắt buộc | Cần SKU và explicit basis, không có default từ PackagingVersion |
| Product/SKU ở Scenario | HTMX tải SKU và base Run đúng phạm vi | Chưa có Run LOCKED/per_unit/lines; chọn SKU thì không lấy Run Product-level và ngược lại |
| Channel ở Scenario | Gợi ý Currency/jurisdiction từ Channel khi ô chưa có giá trị; vẫn sửa được | Channel ngừng hoặc default trống; không tự tải phí nền tảng |
| Method ở Scenario | Chỉ mục tiêu đúng method hợp lệ; ba trường vẫn hiện, backend chặn nhập nhiều mục tiêu | Chưa nhập mục tiêu cần hoặc chưa xóa mục tiêu phương pháp cũ |
| Product ở Compare | Candidates chỉ tải sau Product; SKU filter theo Product | Chưa có Scenario đủ trạng thái/snapshot hoặc bộ lọc đang loại hết |

Danh mục chọn mới thường chỉ bản hoạt động; nhiều form sửa giữ tham chiếu cũ ngừng để xem lịch sử. Run/Scenario tạo mới yêu cầu master phù hợp đang hoạt động. Đọc lịch sử snapshot không bắt buộc mọi master còn hoạt động. Không suy từ một dropdown cũ giữ giá trị rằng engine sẽ chấp nhận giá trị ấy cho lần tính mới.

## 7. Ảnh hưởng xuôi khi sửa dữ liệu

| Tôi thay đổi | Run/Scenario cũ đã lưu | Dùng mới chịu ảnh hưởng ở đâu? | Kiểm tra tiếp theo |
| --- | --- | --- | --- |
| Currency/UoM tên/ký hiệu | Snapshot và kết quả cũ giữ | Dropdown và mô tả danh mục hiện tại | Không coi đổi tên là đổi số hay factor |
| UoM group/đại lượng, Conversion factor/kỳ | Run cũ giữ nguồn/hệ số | Lượng/giá/thời gian quy đổi ở Run mới | Kiểu, cặp trực tiếp và tính duy nhất theo ngày |
| CE mã/type/currency/UoM | Snapshot cũ giữ kết quả | Formula/Scheme mới hoặc lần kiểm tra có thể mất biến/type mismatch | Revalidate đúng dependency và tests |
| Item metadata/UoM hoặc trạng thái | Kết quả cũ không tính lại | Nguồn Run mới; đơn vị dòng/giá không tự đổi | BOM/Pack/Price conversions; tránh sửa nghĩa Item lịch sử |
| Product category | Pricing đã tính giữ phí cũ | Phí theo nhóm của Scenario mới | Kiểm tra phí category và SKU override |
| SKU net quantity/UoM | Run/Scenario cũ không tính lại | Scaling vật tư/thời gian cho Run mới | Sales/net dimension và conversion |
| Supplier hoặc SupplierPrice | Run cũ giữ giá; Scenario cũ giữ giá vốn | MATERIAL/PACKAGING Run mới đúng ngày; có thể bị loại/mơ hồ | Giá/thuế/currency/min_qty/date/status |
| BOMVersion/Line | Snapshot Run cũ giữ | MATERIAL_COST khi version được chọn đủ điều kiện | Thu hồi/hao hụt/UoM; không optional/substitute |
| PackagingVersion/Line/Assignment | Snapshot cũ giữ | Cấu hình chọn theo SKU/ngày, quantity trên basis | Một primary, một version; basis rõ; không market/artwork |
| Center/Resource | Snapshot cũ giữ | Eligibility/consistency của Routing/Rate mới | Active, trung tâm khớp; capacity không tự ghi kỳ |
| ResourceRate | Giá/thời gian cũ giữ | RESOURCE_COST lần tính mới tại ngày phù hợp | Một rate bất kể type; currency/time unit |
| RoutingVersion/Operation | Snapshot cũ giữ | RESOURCE_COST mới | Setup một lần; runtime basis; nguồn lực chính |
| Pool/AllocationRule/Period | Snapshot cũ giữ | ALLOCATION theo mã và kỳ | New Rule code cần Scheme version tham chiếu mới; đủ denominator |
| FormulaVersion | Scheme FK cụ thể không tự chuyển; Run cũ giữ công thức | Scheme mới chọn version; Formula identity refs resolve theo ngày khi thực thi | Tests/dependency/effective date; không dùng preview để khôi phục lịch sử |
| SchemeVersion/Line | Run cũ giữ cấu hình/trace | Run mới theo ngày/nguồn chọn | Hiệu lực duy nhất và MANUAL inputs |
| Run mới | Run/Scenario cũ giữ | Chỉ Scenario mới chọn base_run mới dùng giá vốn mới | Không tự chuyển Scenario cũ sang Run mới |
| Channel/Fee/Tax/FX | Scenario CALCULATED giữ snapshot/nguồn | Scenario mới hoặc Nháp chưa tính tra chính sách ngày định giá | Scope/priority/FX và ngày nửa mở |
| Margin/markup/mục tiêu Scenario | CALCULATED không sửa | Nhân bản và tính kịch bản mới | So sánh đúng cùng cơ sở, không giả fixed price |

Tạo dữ liệu mới không tự khiến lịch sử đổi. Ngược lại, sửa trực tiếp giá mua/rate/quy tắc/gán SKU có thể đổi nguồn cho **Run mới**, dù Run cũ ổn định nhờ snapshot. Đó là lý do nên thêm kỳ/bản mới và giữ bản cũ; không khẳng định tất cả bảng nguồn có khóa bất biến. BOM/Pack/Routing/Formula/Scheme có khóa phiên bản chốt; Rate/AllocationRule/Assignment không áp cùng cơ chế.

## 8. Tra ngược khi không tạo hoặc không tính được

| Tôi không làm được | Kiểm tra trước | Kiểm tra tiếp | Module cần mở |
| --- | --- | --- | --- |
| Tạo UoM | Nhóm đơn vị có/active | Mã, ký hiệu, precision | Nhóm đơn vị tính → Đơn vị tính |
| Tạo CE | Type đã chọn | MONEY cần Currency; QUANTITY cần UoM; nhóm CE có thể trống | Tiền tệ/Đơn vị tính → Phần tử chi phí |
| Tạo Item/Product/SKU | FK bắt buộc tồn tại | Active, cùng Product cho SKU, net quantity > 0, đơn vị số đo | Danh mục tương ứng |
| Tạo SupplierPrice | Supplier/Item/Currency/UoM | Giá/min_qty/tax/date; lưu Nháp không tự hiệu lực | Giá nhà cung cấp |
| Lưu BOM/Pack line hoặc clone | Phiên bản còn sửa, Item/UoM hợp lệ | Direct conversion đúng ngày version mới | BOM/Pack → Quy đổi đơn vị |
| Gán SKU | SKU cùng Product Config | Ngày hợp lệ, không trùng khóa | Packaging → Gán SKU |
| Lưu Operation | Order dương/duy nhất; code/name | Time≥0/TIME; quantity pair; Resource center | Routing → Công đoạn; Resource |
| Kích hoạt Formula | Header active/start | Type/unit, dependency EFFECTIVE duy nhất, test active/all pass | Thiết lập công thức |
| Kích hoạt Scheme | Start/header/lines | Nguồn registered, đủ leaf providers, type/dependency/cycle | Phương án tính giá thành |
| Chọn Scheme trong Run | Ngày tính | Active + exactly one EFFECTIVE version | Scheme và Ngày tính giá |
| Run thiếu Material | BOM Product/date/status | Item/Price/Conversion | BOM → Giá mua → Quy đổi |
| Run thiếu Packaging | SKU/primary assignment/date | EFFECTIVE version/lines, Run basis, Price/Conversion | Bao bì → Run → Giá mua/Quy đổi |
| Run thiếu Resource | Routing/date/status | Nonzero op Resource/TIME/basis; rate duy nhất/tiền/unit | Routing → Nguồn lực → Rate/Quy đổi |
| Run thiếu Allocation | Mã Rule/Scheme nguồn | NORMAL_CAPACITY; period/denominator/unit/currency | Quy tắc/Nhóm chi phí; period chưa có UI |
| Scenario không có base Run | Product/SKU chính xác | LOCKED, per_unit hợp lệ, có lines | Lần tính giá thành |
| Scenario tính lỗi | Tax mode/context, method target | Fee/tax basis/scope/priority, Currency/FX | Scenario → Fee/Tax/FX |
| Compare không có lựa chọn | Product/filter | CALCULATED, base LOCKED, snapshot/hash | Kịch bản giá bán → So sánh |
| Compare bị từ chối | 2–5 lựa chọn | Cùng SKU hoặc Product không SKU, cùng UoM/basis | Chọn lại tập kịch bản |

Gặp lỗi “có nhiều” thì kiểm tra nguồn trùng kỳ/phạm vi; thêm một nguồn nữa thường không giải quyết được. Gặp “không tìm thấy” thì kiểm tra trạng thái, ngày và active trước khi tạo bản ghi mới. Không tìm nút kích hoạt nguồn upstream chưa được triển khai; xem [GAP_REGISTER](GAP_REGISTER.md).

## 9. Checklist nối toàn bộ chuỗi

- [ ] Biết mỗi form cần FK nào và những FK nào thực sự tùy chọn.
- [ ] Đồng nhất đơn vị/tiền tệ của nguồn; có đúng cặp chuyển đổi trực tiếp khi cần.
- [ ] Mã trạng thái EFFECTIVE được kiểm tra độc lập với badge hiệu lực theo ngày và active header.
- [ ] Nguồn Costing cần duy nhất ở ngày tính; end bao gồm ngày ấy. Fee/Tax/FX Pricing end không bao gồm.
- [ ] Formula/Scheme activation đã đạt nhưng nguồn mua/sản xuất vẫn được kiểm tra riêng.
- [ ] Run Đã khóa đúng Product/SKU/basis trước khi chọn làm giá vốn.
- [ ] Scenario mới dùng chính sách đúng Ngày định giá; CALCULATED cũ không tự đổi.
- [ ] Compare chỉ đọc các kết quả cùng cơ sở; tiền khác currency không tự đổi để trừ.

## 10. Bằng chứng source

| Nhóm claim | Nguồn xác nhận |
| --- | --- |
| FK/required/default/conditional catalog | [core/models.py](../../apps/core/models.py), [master_data/forms.py](../../apps/master_data/forms.py), [master_data/validators.py](../../apps/master_data/validators.py), [product/forms.py](../../apps/product/forms.py), [product/validators.py](../../apps/product/validators.py) |
| Manufacturing fields/relations/status guards | Các `forms/validators/services/selectors/urls` trong [apps/bom](../../apps/bom/forms.py); chi tiết nguồn tại [chương 05](05_HUONG_DAN_SAN_XUAT.md) |
| Formula kiểm thử/activation | [forms.py](../../apps/formula_engine/forms.py), [services.py](../../apps/formula_engine/services.py), [engine.py](../../apps/formula_engine/engine.py) |
| Scheme provider/dependency/activation | [configuration.py](../../apps/costing/configuration.py), [services.py](../../apps/costing/services.py), [engine/registry.py](../../apps/costing/engine/registry.py) |
| Run dropdown/manual/packaging conditions | [run_forms.py](../../apps/costing/run_forms.py), [run_services.py](../../apps/costing/run_services.py) |
| Costing date/price/conversion/manufacturing/allocation | [common.py](../../apps/costing/engine/resolvers/common.py), [prices.py](../../apps/costing/engine/resolvers/prices.py), [uom.py](../../apps/costing/engine/resolvers/uom.py), [manufacturing.py](../../apps/costing/engine/resolvers/manufacturing.py), [allocation.py](../../apps/costing/engine/resolvers/allocation.py) |
| Pricing statuses/refs/close/halfopen selectors | [forms.py](../../apps/pricing/forms.py), [services.py](../../apps/pricing/services.py), [selectors.py](../../apps/pricing/selectors.py) |
| Scenario base locked/targets/dependent dropdown | [scenario_forms.py](../../apps/pricing/scenario_forms.py), [scenario_validators.py](../../apps/pricing/scenario_validators.py), [scenario_selectors.py](../../apps/pricing/scenario_selectors.py) |
| Compare snapshot/identity/basis | [comparison_selectors.py](../../apps/pricing/comparison_selectors.py), [comparison.py](../../apps/pricing/comparison.py) |

Matrix không biến mapping model ẩn thành module UI hoặc tính năng tự động. Các mục CostPoolPeriod/CostElementGroup chỉ rõ model có sẵn nhưng thiếu UI; CapacityCalendar là khả năng chưa có trong source đã kiểm tra. Không hướng dẫn người dùng tự ghi database.
