# 08. Các kịch bản tính giá trong thực tế

Chương này có 20 bài, mỗi bài cùng 18 điểm để người học tự xác định dữ liệu, phép tính và mức hỗ trợ. Các số tiền/tỷ lệ là số đào tạo, không phải báo giá thị trường hoặc hướng dẫn thuế. **[DEMO]** dùng bộ Cappuccino có thật trong source; **[VÍ DỤ NGHIỆP VỤ]** là giả định mở rộng, không phải dữ liệu đã có trong database của bạn.

**Điều kiện chung:** Không sửa bản DEMO đã chốt. Với bài cần BOM/bao bì/quy trình/giá/rate mới, tạo bản Nháp hoặc bản sao có mã `TRAIN_…`, rồi dừng tại điểm thiếu thao tác đưa nguồn vào hiệu lực. Người vận hành kỹ thuật phải chuẩn bị nguồn hợp lệ ngoài UI theo quy trình dữ liệu hiện hành; tài liệu không giả định có nút kích hoạt cho mọi module. Bài chạy đầy đủ bằng UI dùng nguồn DEMO đã chuẩn bị. Xem [GAP_REGISTER](GAP_REGISTER.md) và [thứ tự khởi tạo](03_THU_TU_KHOI_TAO_DU_LIEU.md).

Phân loại: **NATIVE** = bộ tính đã thực thi; **CONFIGURABLE** = dùng cấu hình/biến/công thức đã hỗ trợ; **PARTIAL** = chỉ thực hiện một phần hoặc cần chuẩn bị ngoài UI; **NOT SUPPORTED** = chưa có đường thực thi đúng bài toán. Chọn mức cho phạm vi mô tả, không suy ra hệ thống có nghiệp vụ ngành đầy đủ.

## Cơ sở nghiệp vụ từ nguồn bên ngoài

**[INDUSTRY PATTERN]** Giá thành sản xuất thường tách nguyên vật liệu, công đoạn/nguồn lực và chi phí gián tiếp. Đây là cấu trúc đối chiếu, không chứng minh phần mềm có mọi chức năng quản trị sản xuất. [Microsoft: ước tính lệnh sản xuất](https://learn.microsoft.com/en-us/dynamics365/supply-chain/production-control/tasks/estimate-production-order).

**[INDUSTRY PATTERN]** Phân bổ theo hoạt động có thể dùng nhiều tiêu thức; trong hệ thống này chỉ NORMAL_CAPACITY được bộ tính thực thi. Lợi nhuận trên giá thành đầy đủ cũng khác số dư đảm phí chỉ trừ biến phí. [OpenStax: chi phí theo hoạt động](https://openstax.org/books/principles-managerial-accounting/pages/6-3-calculate-activity-based-product-costs), [OpenStax: số dư đảm phí](https://openstax.org/books/principles-managerial-accounting/pages/3-1-explain-contribution-margin-and-calculate-contribution-margin-per-unit-contribution-margin-ratio-and-total-contribution-margin).

**[INDUSTRY PATTERN]** Giá cộng trên vốn và biên lợi nhuận dùng mẫu số khác nhau; bán sỉ, bán lẻ và sàn có thể có cơ cấu chi phí riêng. Biểu phí sàn thay đổi; các tỷ lệ dưới đây tự đặt để học, không lấy từ bảng phí thực tế. [Shopify: xây dựng giá sản phẩm](https://help.shopify.com/en/manual/products/details/product-pricing/determine-pricing), [Shopify: bán sỉ và bán lẻ](https://www.shopify.com/blog/product-pricing-for-wholesale-and-retail), [Amazon: nhóm phí bán hàng](https://sell.amazon.com/pricing).

**[INDUSTRY PATTERN]** Cước có thể dựa vào trọng lượng thực/quy đổi theo thể tích; điều kiện giao hàng phân định chi phí, rủi ro và trách nhiệm vận chuyển/bảo hiểm/thủ tục. Phần mềm chưa tự xác định các cơ sở này. [DHL: khối lượng tính cước](https://www.dhl.com/us-en/home/global-forwarding/freight-forwarding-education-center/calculating-chargeable-weights.html), [ICC: Incoterms 2020](https://iccwbo.org/business-solutions/incoterms-rules/incoterms-2020/).

## 1. Giá thành sản xuất đầy đủ — Cappuccino

1. **Bối cảnh nghiệp vụ:** [DEMO] Sản xuất 10 hộp Cappuccino, mỗi hộp 20 gói, ngày 07/10/2026.
2. **Vấn đề cần giải quyết:** Biết tổng cho lô và giá thành một hộp; giải thích từng phần nguyên liệu/bao bì/nguồn lực/chung.
3. **Đầu vào:** Product/SKU, phương án, ngày, sản lượng 10 Hộp, VND; cơ sở bao bì 1 Hộp.
4. **Danh mục cần có:** VND; KG/G/HOUR/MINUTE/Cái/Hộp;4 Item; Supplier/4 giá; BOM/bao bì/assignment;2 nguồn lực/rate; Routing; Pool/kỳ/Rule;6 CE/2 Formula/Scheme.
5. **Thứ tự tạo:** Đơn vị/tiền → danh mục → nguồn sản xuất/giá → Formula → Scheme → Run. Dùng bộ đã chuẩn bị theo [bài thực hành](09_THUC_HANH_CAPPUCCINO_END_TO_END.md).
6. **Cấu hình:** SYSTEM MATERIAL_COST, PACKAGING_COST, RESOURCE_COST, ALLOCATION: DEMO_OVERHEAD_NORMAL; Formula trực tiếp rồi đầy đủ; đúng một OUTPUT.
7. **Công thức:** `FULL = MATERIAL + PACKAGING + RESOURCE + OVERHEAD`; `unit = FULL / quantity`.
8. **Màn hình:** DỮ LIỆU DANH MỤC; SẢN XUẤT; Thiết lập công thức; Phương án tính giá thành; Lần tính giá thành.
9. **Giá trị mẫu:** Cà phê 200 g/hộp×100.000/kg; đường 300 g×20.000/kg;20 sachet×500+1 hộp×5.000; máy 3 phút×120.000/giờ; người 6 phút×60.000/giờ; pool 530.000/công suất 100 hộp.
10. **Tính tay:** Nguyên liệu 260.000; bao bì 150.000; máy 60.000+người 60.000; trực tiếp 530.000; phân bổ 53.000; tổng 583.000; đơn vị 58.300.
11. **Kết quả mong đợi:** Run **Đã khóa**, tổng 583.000 VND,10 hộp,58.300 VND/hộp; không cộng thêm SUBTOTAL/OUTPUT vào tổng.
12. **Cách chạy:** Lần tính giá thành → + Chạy tính giá; chọn đúng mã DEMO, ngày 07/10, sản lượng 10/cơ sở 1, bấm **Chạy tính giá**. Ngày cố định, không thay bằng hôm nay.
13. **Đọc kết quả:** Tổng lô và đơn vị ở đầu;6 dòng gồm 4 input,1 subtotal,1 output. So đúng dòng FULL, không lấy tổng cả cột.
14. **Đọc diễn giải:** Mở **Nguồn dữ liệu / Diễn giải** ở MATERIAL để thấy 200 g→2 kg/10 hộp; ở RESOURCE thấy phút→giờ; OVERHEAD thấy 10/100; mở snapshot xem phiên bản 1.
15. **Lỗi:** Thiếu nguồn hiệu lực, nhiều báo giá, thiếu quy đổi, thiếu kỳ công suất hoặc cơ sở bao bì.
16. **Xử lý:** Đối chiếu từng nguồn tại 07/10; đúng một nguồn, tiền tệ VND; không đổi giá đã lưu trong Run cũ. Xem chương 10 nếu có mã lỗi.
17. **Ảnh hưởng thay input:** Run mới và Scenario lấy Run mới thay đổi; Run/Scenario cũ giữ bản chụp.
18. **Mức hỗ trợ:** **NATIVE** cho bộ máy và DEMO đã chuẩn bị; khởi tạo trống hoàn toàn qua UI là **PARTIAL**.

## 2. Lô 100 kg và 1.000 kg — tác động setup một lần

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Một máy cần 15 phút chuẩn bị,30 phút chạy cho 100 kg.
2. **Vấn đề cần giải quyết:** Lô lớn giảm chi phí setup trên kg thế nào, thay vì nhân setup theo sản lượng.
3. **Đầu vào:** Hai Run cùng ngày/Product, quantity 100 và 1000 KG; rate 120.000 VND/giờ; vật liệu 10.000/kg.
4. **Danh mục cần có:** Product đầu ra KG, Recipe theo KG, WorkCenter/Máy/Rate, Routing dùng MINUTE, chuyển MINUTE↔HOUR; CE/Scheme MATERIAL+RESOURCE.
5. **Thứ tự tạo:** Đơn vị → Product/Item/giá → BOM → máy/rate → Routing → Formula/Scheme. Không dùng pool DEMO công suất 100 hộp cho bài 1.000 kg.
6. **Cấu hình:** setup_time 15, run_time 30, quantity_basis 100, quantity_uom KG; Scheme không có PACKAGING/ALLOCATION để cô lập ảnh hưởng setup.
7. **Công thức:** `time_min = 15 + 30 × Q/100`; `resource = time_min/60 ×120000`; `total=Q×10000+resource`.
8. **Màn hình:** Quy trình sản xuất → phiên bản → công đoạn; Đơn giá nguồn lực; Phương án tính giá thành; Lần tính giá thành.
9. **Giá trị mẫu:** Q 100 và 1000; setup 15; run 30/100 kg; yield 1/scrap 0. Mọi dòng giá cùng VND.
10. **Tính tay:** Q 100:45 phút→90.000, tổng 1.090.000,10.900/kg. Q 1000:315 phút→630.000, tổng 10.630.000,10.630/kg.
11. **Kết quả mong đợi:** Setup đều 30.000/lần chạy; riêng phần chạy tăng 10 lần. Đơn vị giảm 270 VND/kg.
12. **Cách chạy:** Khi nguồn TRAIN đã được chuẩn bị EFFECTIVE, tạo Run 100, rồi **Tạo lần tính mới** đổi 1000. Không sửa Run 100.
13. **Đọc kết quả:** So total/quantity. Tổng lô lớn tăng, đơn giá giảm; không kết luận chỉ từ tổng lô.
14. **Đọc diễn giải:** RESOURCE phải cho setup 15 ở cả hai, run 30 và 300; basis 100 KG, conversion phút/giờ.
15. **Lỗi:** Thiếu quantity_basis/batch_size, thiếu TIME UoM, lấy basis 1, hoặc vượt công suất của rule không liên quan.
16. **Xử lý:** Sửa nguồn Nháp/bản mới; đặt basis 100 KG rõ ràng. Nếu quantity_basis trống thì batch_size/batch_uom phiên bản phải thể hiện 100 KG.
17. **Ảnh hưởng:** Thay setup/run/basis/rate ảnh hưởng RESOURCE và OUTPUT Run mới; Scenario nguồn mới đổi theo giá vốn.
18. **Mức hỗ trợ:** **NATIVE** cho setup một lần + scale run; **PARTIAL** cho chuẩn bị nguồn mới qua UI.

## 3. So sánh báo giá nhà cung cấp A/B

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Cà phê mua A 100.000/kg, B 110.000/kg; các yếu tố khác giống DEMO.
2. **Vấn đề cần giải quyết:** Đánh giá tăng giá vốn do nhà cung cấp mà không hiểu nhầm hệ thống tự chọn báo giá rẻ nhất.
3. **Đầu vào:**2 kg cà phê cho 10 hộp; hai giả định giá khác nhau; các báo giá phải ở kỳ tách biệt hoặc môi trường đào tạo tách biệt.
4. **Danh mục cần có:**2 Supplier hoạt động, Item cà phê,2 SupplierPrice VND/KG; nguồn còn lại của bài 1.
5. **Thứ tự tạo:** Supplier → giá có ngày riêng → xác nhận chỉ một giá đủ điều kiện mỗi ngày → Run A/Run B.
6. **Cấu hình:** Giá A 01/10–31/10, giá B từ 01/11 trong dữ liệu đào tạo riêng, chỉ đổi giá cà phê. Không thêm 2 giá cùng ngày rồi tìm ô chọn Supplier trong Run.
7. **Công thức:** `delta = 2kg × (110000−100000)`; giữ các khoản còn lại.
8. **Màn hình:** Nhà cung cấp; Giá nhà cung cấp; Lần tính giá thành; diễn giải dòng nguyên liệu.
9. **Giá trị mẫu:** A 100.000, B 110.000, min_qty 0, tax_rate 0/tax_inclusive False, trạng thái nguồn EFFECTIVE đã chuẩn bị.
10. **Tính tay:** A 583.000/lô; B 603.000/lô; chênh 20.000/lô=2.000/hộp.
11. **Kết quả mong đợi:** Nguồn giá và supplier trong trace khác; giá B 60.300/hộp. Không có màn hình so sánh Costing dạng ma trận tự động.
12. **Cách chạy:** Chạy hai ngày đã thiết kế ở môi trường đào tạo riêng; **không dùng kỳ future DEMO** vì DEMO đồng thời đổi cả rate và giá 120.000.
13. **Đọc kết quả:** Ghi tổng/đơn vị của 2 Run và chênh; sau đó có thể lập 2 Scenario cùng giả định để xem tác động giá bán.
14. **Đọc diễn giải:** MATERIAL: đúng Supplier, giá 100.000/110.000, nguồn và ngày. Nếu nguồn khác dự kiến, chưa được so số.
15. **Lỗi:** AMBIGUOUS_PRICE khi 2 Supplier cùng hiệu lực; min_qty cao hơn lượng dòng; thiếu chuyển UoM.
16. **Xử lý:** Tách các kỳ/nguồn hợp lệ; không nhập ưu tiên Supplier giả. Nếu cần chọn nhà cung cấp tùy ý cho cùng ngày, ghi yêu cầu phát triển, chưa có input đó.
17. **Ảnh hưởng:** SupplierPrice→nguyên liệu→Run mới→Scenario mới; snapshot cũ giữ Supplier A.
18. **Mức hỗ trợ:** **PARTIAL**: tính theo nguồn duy nhất hỗ trợ; bộ so sánh/chọn Supplier A/B cùng ngày chưa có.

## 4. Thay định mức đường

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Giảm đường 300 g còn 280 g trên cơ sở 1 hộp, giá 20.000/kg.
2. **Vấn đề cần giải quyết:** Định lượng lợi ích kinh tế của công thức mới và giữ lịch sử cũ.
3. **Đầu vào:**10 hộp, hai RecipeVersion khác lượng đường; các giá/nguồn lực/bao bì giống nhau.
4. **Danh mục cần có:** Recipe/2 version, Item đường, conversion G→KG, nguồn bài 1.
5. **Thứ tự tạo:** Mở version cũ → tạo version mới → sửa dòng đường → kiểm tra ngày/nguồn → chuẩn bị hiệu lực → Run mới.
6. **Cấu hình:** Version mới ở Nháp khi clone, qty 280 G; output_qty 1 BOX, yield 1, scrap 0. Không sửa trực tiếp version 1 đã chốt.
7. **Công thức:** `input = qty×Q/output_qty/yield/(1−scrap)`; bài này yield 1/scrap 0 nên giảm 20 g×10=0,2 kg.
8. **Màn hình:** BOM / Công thức sản xuất → phiên bản → dòng; Lần tính giá thành; Xem dữ liệu và phiên bản đã sử dụng.
9. **Giá trị mẫu:** Đường 300→280 G,10 BOX,20.000/KG; chỉ một phiên bản EFFECTIVE tại mỗi ngày.
10. **Tính tay:** Tiết kiệm 0,2×20.000=4.000; nguyên liệu 256.000; tổng 579.000;57.900/hộp.
11. **Kết quả mong đợi:** Run mới 57.900; run cũ 58.300. Yield<1/scrap>0 sẽ tăng lượng đầu vào theo công thức, không tự cộng phần trăm vào tiền.
12. **Cách chạy:** Sau chuẩn bị nguồn, chọn ngày thuộc version mới; dùng 10 hộp và cơ sở bao bì 1 hộp như cũ. Thiếu thao tác UI phát hành thì dừng, không tự sửa DB.
13. **Đọc kết quả:** MATERIAL giảm 4.000, các khoản khác không đổi. Nếu resource/packaging đổi, bài chưa cô lập đúng.
14. **Đọc diễn giải:** Dòng đường ghi qty 280, scale 10, yield 1, scrap 0, lượng 2,8 KG; snapshot chỉ tới version mới.
15. **Lỗi:** Hai version cùng ngày; version Nháp không chọn; yield 0 hoặc scrap 1; optional/substitution chưa được chọn.
16. **Xử lý:** Kiểm tra khoảng ngày gồm ngày cuối của Costing; dùng phiên bản mới đúng nguồn; bỏ cấu hình thay thế chưa hỗ trợ trong bài này.
17. **Ảnh hưởng:** BOM version→MATERIAL→OUTPUT→Scenario nguồn mới. Product/SKU không phải tạo lại chỉ vì đổi đường.
18. **Mức hỗ trợ:** **NATIVE** tính lượng/yield/scrap và lưu version; **PARTIAL** vòng đời đưa version sản xuất vào hiệu lực qua UI.

## 5. Hai SKU cùng sản phẩm, bao bì hộp thường/hộp quà

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Hai SKU đều 20 gói/0,5 kg; chỉ hộp giấy khác nhau.
2. **Vấn đề cần giải quyết:** Tách ảnh hưởng bao bì khỏi công thức cà phê và không gán nhầm cấu hình.
3. **Đầu vào:**10 hộp mỗi SKU; hộp thường 5.000, hộp quà 8.000/cái; sachet 20×500/hộp.
4. **Danh mục cần có:** Product chung,2 SKU,2 Item hộp/giá,2 PackagingConfig/version/assignment chính; Recipe/Routing chung.
5. **Thứ tự tạo:** Item hộp quà/giá → SKU quà → cấu hình bao bì → lines → assignment SKU → nguồn hiệu lực → Run.
6. **Cấu hình:** Mỗi SKU có đúng một assignment chính theo ngày; lines 20 sachet+1 hộp đúng Item; cơ sở Run 1 Hộp. Không đổi SKU thành 50 gói trong bài này vì BOM theo hộp cần xem lại cơ sở.
7. **Công thức:** `packaging = Q×(20×500+1×box_price)`.
8. **Màn hình:** SKU; Vật tư / Hàng hóa; Giá nhà cung cấp; Cấu hình bao bì → liên kết SKU; Lần tính giá thành.
9. **Giá trị mẫu:** SKU TRAIN_STANDARD/TRAIN_GIFT,10 BOX,1 BOX basis; hộp quà có mã loại PACKAGING.
10. **Tính tay:** Thường 150.000 bao bì, tổng 583.000; quà 180.000 bao bì, tổng 613.000; đơn vị 61.300, tăng 3.000/hộp.
11. **Kết quả mong đợi:** Chỉ PACKAGING_COST tăng 30.000. Không tự nhân quantity bằng units_per_parent thêm lần nữa.
12. **Cách chạy:** Chọn từng SKU trong hai Run cùng ngày và Q, luôn nhập basis 1 Hộp; nguồn nháp cần chuẩn bị trước.
13. **Đọc kết quả:** So dòng bao bì, tổng/đơn vị. Ma trận Pricing không so hai SKU khác nhau; bài này ghi so Costing thủ công.
14. **Đọc diễn giải:** Đúng assignment/config/item hộp; sachet 200 cái+hộp 10 cái; không xuất hiện giá Supplier trên BOM.
15. **Lỗi:** SKU khác Product của config; nhiều assignment chính; basis bỏ trống; market/artwork condition chưa hỗ trợ.
16. **Xử lý:** Gán đúng SKU, tách ngày; bỏ điều kiện chưa thực thi cho bài đào tạo; kiểm tra quantity các dòng đã quy về basis.
17. **Ảnh hưởng:** Item giá hộp/assignment/version→PACKAGING→Run mới; SKU khác cần Scenario riêng.
18. **Mức hỗ trợ:** **NATIVE** cấu hình phẳng và assignment; **PARTIAL** bootstrap/đa cấp tự tính/so sánh khác SKU.

## 6. Thay máy trong công đoạn

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Máy A 3 phút/hộp,120.000/giờ; máy B 1,5 phút/hộp,180.000/giờ.
2. **Vấn đề cần giải quyết:** Máy có đơn giá cao hơn vẫn có thể giảm chi phí nếu nhanh hơn.
3. **Đầu vào:**10 hộp, setup 0, hai giả định Routing; công đoạn nhân công giữ 6 phút/hộp.
4. **Danh mục cần có:** WorkCenter,2 Resource MACHINE/rate; Routing 2 version, thời gian MINUTE/HOUR; nguồn khác bài 1.
5. **Thứ tự tạo:** Máy B/rate → clone Routing → chọn B/run_time 1.5 → kiểm tra ngày → nguồn hiệu lực → Run.
6. **Cấu hình:** primary_resource B thuộc WorkCenter công đoạn; quantity_basis 1 BOX; vẫn chỉ một primary_resource cho mỗi operation.
7. **Công thức:** `machine = Q×run_min/60×rate`; không sao chép rate vào Routing.
8. **Màn hình:** Nguồn lực; Đơn giá nguồn lực; Quy trình sản xuất → phiên bản/công đoạn; Run.
9. **Giá trị mẫu:** A 3 min×120.000/h; B 1.5 min×180.000/h; Q 10; rate EFFECTIVE duy nhất.
10. **Tính tay:** A 60.000, B 45.000; RESOURCE từ 120.000 còn 105.000; tổng 568.000;56.800/hộp.
11. **Kết quả mong đợi:** Tiết kiệm 15.000/lô. Bài không mô phỏng lịch máy, downtime/OEE hoặc công suất hữu hạn.
12. **Cách chạy:** Run ở ngày có version B, cùng input số lượng; nếu version Nháp chưa có thao tác phát hành thì dừng và chuẩn bị nguồn.
13. **Đọc kết quả:** RESOURCE giảm 15.000; MATERIAL/PACKAGING/OVERHEAD không đổi.
14. **Đọc diễn giải:** Công đoạn 10 dùng B,15 phút=0,25 giờ×180.000; công đoạn 20 vẫn 60.000 nhân công.
15. **Lỗi:** Resource khác WorkCenter; nhiều Rate cùng ngày dù khác rate_type; thiếu Time UoM.
16. **Xử lý:** Chọn đúng center/resource; duy nhất giá phù hợp theo ngày; không dựa vào rate_type để né mơ hồ.
17. **Ảnh hưởng:** Rate/Resource/Routing→RESOURCE→Run/Scenario mới; các Run A đã khóa không đổi.
18. **Mức hỗ trợ:** **NATIVE** một nguồn lực chính/công đoạn; **PARTIAL** bài đổi nguồn mới và đa nguồn lực đồng thời.

## 7. Chi phí chung theo công suất bình thường

1. **Bối cảnh nghiệp vụ:** [DEMO] Pool 530.000 VND; normal_capacity 100 Hộp trong kỳ 01/10–31/12/2026.
2. **Vấn đề cần giải quyết:** Phân bổ theo công suất đã xác định, không mặc nhiên chia toàn pool cho từng Run.
3. **Đầu vào:** Q 10 hoặc 20 Hộp; amount 530.000; capacity 100; cùng currency VND.
4. **Danh mục cần có:** CostPool, CostPoolPeriod đã chuẩn bị, AllocationRule NORMAL_CAPACITY/UoM BOX, CE OVERHEAD, Scheme SYSTEM.
5. **Thứ tự tạo:** Pool → dữ liệu kỳ/công suất(ngoài UI) → Rule → Scheme Line → Run.
6. **Cấu hình:** `ALLOCATION:DEMO_OVERHEAD_NORMAL`; condition_jsonb rỗng, formula_code rỗng; status rule/kỳ EFFECTIVE.
7. **Công thức:** `allocation = period_amount × usage / normal_capacity`.
8. **Màn hình:** Nhóm chi phí chung; Quy tắc phân bổ; Phương án tính giá thành; Run. Không có màn nhập amount kỳ.
9. **Giá trị mẫu:** 530.000/100=5.300 VND/hộp; Q 10/20, không vượt capacity.
10. **Tính tay:** Q 10 phân bổ 53.000; Q 20 phân bổ 106.000. Trong DEMO setup 0, các khoản khác tuyến tính nên tổng Q 20=1.166.000, vẫn 58.300/hộp.
11. **Kết quả mong đợi:** Rate phân bổ 5.300/hộp. Run riêng không tự làm sổ theo dõi công suất đã tiêu thụ trong kỳ.
12. **Cách chạy:** Dùng DEMO đã có kỳ, chạy Q 10 và 20; dùng cơ sở bao bì 1 BOX. Tạo pool mới chỉ UI chưa đủ để chạy.
13. **Đọc kết quả:** Dòng OVERHEAD 53.000/106.000; OUTPUT bao gồm đúng một lần.
14. **Đọc diễn giải:** Pool/kỳ/amount/capacity/unit, usage 10/20 và rate 5.300; không đọc thành giờ máy.
15. **Lỗi:** thiếu kỳ/công suất; Q>100; chọn MACHINE_HOUR hoặc có condition/formula chưa hỗ trợ.
16. **Xử lý:** Kiểm tra kỳ đã chuẩn bị; chạy trong capacity; không đổi code basis thành NORMAL_CAPACITY nếu nghiệp vụ thực khác.
17. **Ảnh hưởng:** Amount/capacity/rule→OVERHEAD Run mới→Formula FULL→Pricing nguồn mới.
18. **Mức hỗ trợ:** **NATIVE** resolver NORMAL_CAPACITY; **PARTIAL** dữ liệu kỳ; **NOT SUPPORTED** chạy ABC/MACHINE_HOUR trực tiếp hiện nay.

## 8. Bán trực tiếp, không phí/thuế trong giả định

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Một hộp có giá vốn 58.300 VND, muốn margin 20% khi bán trực tiếp.
2. **Vấn đề cần giải quyết:** Tìm giá đáp ứng lợi nhuận, phân biệt margin với cộng 20% lên vốn.
3. **Đầu vào:** Run đã khóa có unit_cost 58.300; kênh riêng không phí; thuế NONE; mục tiêu MARGIN 20.
4. **Danh mục cần có:** Run Cappuccino, Currency VND, Channel `TRAIN_DIRECT_FREE` hoạt động; không cần FX.
5. **Thứ tự tạo:** Run → kênh → xác nhận không quy tắc phí hiệu lực → Scenario.
6. **Cấu hình:** Chọn Không áp dụng thuế để biểu diễn giả định, không suy ra nghĩa vụ thuế thực tế bằng 0. Không dùng DEMO_DIRECT vì kênh ấy có phí 5%+1.000.
7. **Công thức:** `P=C/(1−m)`; `profit=P−C`; margin `profit/P`.
8. **Màn hình:** Kênh bán → Kịch bản giá bán → chi tiết → Tính giá bán.
9. **Giá trị mẫu:** Nguồn Run 07/10, ngày định giá 08/10/2026, VND, MARGIN 20, các mục tiêu khác trống.
10. **Tính tay:** 58.300/0,8=72.875; lợi nhuận 14.575; markup 25%.
11. **Kết quả mong đợi:** Giá khách trả 72.875, phí 0, thuế 0, margin 20%; có thể có cảnh báo không tìm thấy phí vì bài này chủ đích không có phí.
12. **Cách chạy:** Tạo `TRAIN_PRICE_DIRECT`, chọn nguồn đúng SKU, bấm **Lưu Nháp → Tính giá bán**. Giá trị mục tiêu nhập 20, không 0.2.
13. **Đọc kết quả:** Cấu thành giá gồm giá khách trả, doanh thu thuần, vốn và lợi nhuận; không có khoản thuế tự sinh.
14. **Đọc diễn giải:** Nguồn và diễn giải đã lưu phải có policy margin trên giá khách trả, đúng Run, tax_mode NONE, danh sách phí trống.
15. **Lỗi:** Chọn nhầm kênh có phí; nhập thêm markup; thiếu Run đã khóa; REQUIRED nhưng thiếu thuế.
16. **Xử lý:** Kiểm tra từng field; chỉ một mục tiêu. Giữ NONE cho bài giả định, dùng chính sách thuế được xác nhận cho nghiệp vụ thật.
17. **Ảnh hưởng:** Thay giá vốn/kênh/mục tiêu chỉ có tác dụng với Scenario mới hoặc Nháp tính lần đầu.
18. **Mức hỗ trợ:** **NATIVE**. Không bao gồm quản lý đơn bán hàng, khách hàng hoặc thu tiền.

## 9. Bán đại lý — markup 25%, phí 2%, thuế giả định 10%

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Muốn lợi nhuận sau phí/thuế bằng 25% giá vốn khi bán qua đại lý.
2. **Vấn đề cần giải quyết:** Tránh lấy 58.300×1,25 làm giá khách trả rồi quên phí và thuế.
3. **Đầu vào:** C 58.300, markup 25%, fee 2% giá khách trả, thuế 10% trên giá trước thuế.
4. **Danh mục cần có:** Channel riêng `TRAIN_DISTRIBUTOR`, phí hiệu lực, TaxRule giả định phù hợp, Run đã khóa.
5. **Thứ tự tạo:** Kênh → phí 2%/thuế 10% → Scenario phương pháp MARKUP. Dùng khu vực riêng `TRAIN_VN` để không trùng các thuế DEMO.
6. **Cấu hình:** Fee `COMMISSION`, LIST_PRICE, rate 2, refund 0, đã gồm thuế; Tax SELLING_PRICE, rate 10, recovery 0, inclusive True; trạng thái EFFECTIVE.
7. **Công thức:** `P=(C×1,25)/(1/1,1−0,02)`; profit mục tiêu=`C×0,25`.
8. **Màn hình:** Kênh bán; Quy tắc phí kênh; Quy tắc thuế; Kịch bản giá bán; So sánh kịch bản.
9. **Giá trị mẫu:** Run 07/10, ngày 08/10, VND, target_markup 25; target_margin và profit để trống.
10. **Tính tay:** P 81.965,74642127; phí 1.639,31492843; thuế 7.451,43149284; lợi nhuận 14.575.
11. **Kết quả mong đợi:** Markup 25%; margin 17,78181818%, không phải 25% vì mẫu số khác.
12. **Cách chạy:** Tạo/lưu Nháp rồi Tính giá bán. Sau thành công dùng Nhân bản thành kịch bản mới nếu muốn đổi markup.
13. **Đọc kết quả:** So lợi nhuận với giá vốn để kiểm markup; giá khách trả đã bao gồm thuế. Không gọi tỷ lệ này là hoa hồng đại lý.
14. **Đọc diễn giải:** Đúng loại phí 2%, đúng TaxRule/khu vực; thuế dùng giá trước thuế chung; không VAT trên phí lần nữa.
15. **Lỗi:** Hai thuế VAT đồng hạng; fee_base chưa hỗ trợ; tax/refund không rõ; tiền tệ phí khác thiếu FX.
16. **Xử lý:** Dùng phạm vi đào tạo riêng, loại/phạm vi/ưu tiên duy nhất, khoản phí đã gồm thuế và refund 0.
17. **Ảnh hưởng:** Đổi phí hoặc markup làm Scenario mới thay đổi; nguồn giá vốn vẫn giữ 58.300 nếu chọn Run cũ.
18. **Mức hỗ trợ:** **NATIVE** phép tính và cấu hình kênh; **NOT SUPPORTED** hợp đồng đại lý/chiết khấu theo doanh số tích lũy.

## 10. Bán trên sàn — phí 12% cộng 2.000

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Kênh thương mại điện tử giả định có phí 12% và phí cố định 2.000 trên một hộp.
2. **Vấn đề cần giải quyết:** Bảo toàn margin 20% sau phí cao hơn bán trực tiếp.
3. **Đầu vào:** C 58.300, f 12%, fixed 2.000, thuế giả định 10%, margin 20%.
4. **Danh mục cần có:** Channel ECOMMERCE riêng, quy tắc phí và thuế hiệu lực; Run Cappuccino.
5. **Thứ tự tạo:** Kênh → fee LIST_PRICE → thuế khu vực đào tạo → Scenario.
6. **Cấu hình:** Có thể cùng một phí rate 12/fixed 2000, hoặc hai mã phí khác nhau; không tạo hai mã cùng loại cùng phạm vi/priority nếu muốn cộng.
7. **Công thức:** `P=(58300+2000)/(1/1,1−0,12−0,20)`; floor/cap để trống để cô lập bài.
8. **Màn hình:** Kênh bán; Quy tắc phí kênh; Quy tắc thuế; Kịch bản giá bán.
9. **Giá trị mẫu:** TRAIN_MARKET,08/10/2026, VND, MARGIN 20, refund 0, phí đã gồm thuế.
10. **Tính tay:** P 102.361,11111111; phí 14.283,33333333; thuế 9.305,55555556; lợi nhuận 20.472,22222222.
11. **Kết quả mong đợi:** Margin 20%; giá cao hơn bài 8. Đây không phải biểu phí Amazon/Shopee thực tế.
12. **Cách chạy:** Chọn Run cùng SKU; Lưu Nháp/Tính giá bán; thêm vào ma trận so sánh với bài 8/9.
13. **Đọc kết quả:** Phí cố định 2.000 là trên một đơn vị đầu ra, không phải chia 2.000 cho 10 hộp của nguồn Costing.
14. **Đọc diễn giải:** Kiểm tra fee basis giá khách trả, rate 0.12 lưu trong snapshot và fixed 2.000; kiểm tra phí thắng/phí bị loại.
15. **Lỗi:** Nhập 12 thành 0.12 trên form%; cộng trùng loại phí; refund>0; mẫu số không dương khi phí/margin quá cao.
16. **Xử lý:** Nhập 12; chia các loại phí đúng nghĩa; giảm giả định không khả thi hoặc báo mức hỗ trợ nếu cần xử lý hoàn hàng.
17. **Ảnh hưởng:** Đổi phí/kênh/mục tiêu đổi Scenario mới; không đổi giá thành sản xuất.
18. **Mức hỗ trợ:** **NATIVE** giải phí%/fixed/sàn/trần; **PARTIAL** kinh tế sàn tổng thể vì chưa có phí trên đơn hàng, settlement/hoàn hàng.

## 11. Xuất khẩu — định giá USD từ vốn VND

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Báo giá một hộp bằng USD, vốn 58.300 VND, margin 20%.
2. **Vấn đề cần giải quyết:** Chuyển đúng chiều tỷ giá trước khi giải giá, không coi USD/VND là VND/USD.
3. **Đầu vào:** FX VND→USD 0.00004, loại SPOT, có hiệu lực tại 00:00 ngày 08/10/2026; thuế NONE và không phí trong bài.
4. **Danh mục cần có:** Currency USD hoạt động, Channel EXPORT/USD, FX đúng chiều, Run VND đã khóa.
5. **Thứ tự tạo:** Currency → Channel → FX → Scenario chọn USD, fx_rate_type SPOT.
6. **Cấu hình:** Nguồn tỷ giá đào tạo bắt đầu trước/ngay 00:00; tax_mode NONE chỉ là giả định. Không kết luận mức thuế xuất khẩu thực tế.
7. **Công thức:** `C_USD=58300×0,00004`; `P=C_USD/(1−0,2)`.
8. **Màn hình:** Tiền tệ; Kênh bán; Tỷ giá; Kịch bản giá bán.
9. **Giá trị mẫu:** VND→USD 0.00004, ngày 08/10, target_margin 20; không phí cố định, không thuế.
10. **Tính tay:** C 2,332 USD; P 2,915 USD; lợi nhuận 0,583 USD.
11. **Kết quả mong đợi:** Snapshot có vốn VND gốc và FX; tiền tệ kết quả USD; Run VND cũ không thay đổi.
12. **Cách chạy:** Chọn nguồn DEMO 58.300, kênh riêng EXPORT, tiền USD, loại SPOT; Lưu Nháp/Tính giá bán.
13. **Đọc kết quả:** So cùng USD; không đọc 2,915 là 2.915 VND. UI có thể làm tròn hiển thị theo USD, dữ liệu tính vẫn giữ 8 số lẻ.
14. **Đọc diễn giải:** FX nguồn/đích/rate/type/thời điểm; phép đổi 58.300→2,332; policy 00:00 giờ Việt Nam.
15. **Lỗi:** MISSING_FX, AMBIGUOUS_FX; tỷ giá bắt đầu 09:00; chỉ có USD to VND; quên fx_rate_type.
16. **Xử lý:** Tạo đúng cặp/loại/kỳ duy nhất; không thêm hai chiều rồi kỳ vọng chọn tự động.
17. **Ảnh hưởng:** FX mới→Scenario mới bằng ngoại tệ; Costing không tự dùng FX này để đổi giá nguyên liệu.
18. **Mức hỗ trợ:** **NATIVE** FX trong Pricing; **PARTIAL** xuất khẩu đầy đủ vì thiếu Incoterms/customs/document/settlement.

## 12. Độ nhạy theo tỷ giá

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Vốn VND giữ nguyên, tỷ giá VND→USD thay 0.00004→0.000038.
2. **Vấn đề cần giải quyết:** Giá USD mục tiêu thay bao nhiêu khi một VND đổi ít USD hơn.
3. **Đầu vào:** C 58.300 VND, margin 20%, không phí/thuế, hai ngày định giá khác nhau.
4. **Danh mục cần có:** Currency/channel EXPORT, hai FX SPOT cùng chiều ở kỳ không chồng, cùng Run đã khóa.
5. **Thứ tự tạo:** FX kỳ A → FX kỳ B → Scenario A → nhân bản Scenario B đổi Ngày định giá.
6. **Cấu hình:** Giá vốn nguồn không đổi; chỉ đổi FX theo ngày. Không thêm hai FX cùng hiệu lực để giả lập lựa chọn.
7. **Công thức:** `P_USD=58300×FX/(1−0,2)`; delta B−A.
8. **Màn hình:** Tỷ giá; Kịch bản giá bán; So sánh kịch bản cùng USD.
9. **Giá trị mẫu:** A 08/10 FX 0.00004; B 01/11 FX 0.000038; rate_type SPOT; tax_mode NONE.
10. **Tính tay:** A 2,915; B 2,76925 USD; delta−0,14575 USD=−5%; vốn B 2,2154 USD.
11. **Kết quả mong đợi:** Margin cả hai 20%; tiền USD và lợi nhuận USD giảm 5%; không tự nói doanh nghiệp lỗ vì mục tiêu vẫn được giữ.
12. **Cách chạy:** Tính hai Scenario rồi chọn cả hai, đặt A làm Kịch bản mốc; bấm So sánh kịch bản.
13. **Đọc kết quả:** So giá/fees/profit USD và chênh margin 0 điểm phần trăm. Cần giữ SKU/basis/policy giống nhau.
14. **Đọc diễn giải:** Cùng Run, khác FX id/rate/instant; không vô tình đổi nguồn Costing sang Run tháng 11.
15. **Lỗi:** FX chồng kỳ; so USD với VND không có delta tiền; B trỏ Run mới nên thay 2 biến.
16. **Xử lý:** Tách kỳ, giữ cùng Run, cùng tiền tệ. Nếu khác tiền, chỉ đọc số tiền riêng, không mong comparison tự FX.
17. **Ảnh hưởng:** Thay FX không sửa Scenario A đã tính; nhân bản tính nguồn mới để thấy thay đổi.
18. **Mức hỗ trợ:** **NATIVE** mô phỏng qua nhiều Scenario/kỳ; **NOT SUPPORTED** hedge/tỷ giá forward tự động hoặc danh mục rủi ro FX.

## 13. Mục tiêu margin 10/15/20/25%

1. **Bối cảnh nghiệp vụ:** [DEMO + VÍ DỤ NGHIỆP VỤ] Giữ vốn 58.300, phí 5%+1.000, thuế 10%, thử 4 mức margin.
2. **Vấn đề cần giải quyết:** Nhìn giá phải tăng để đạt mục tiêu, không coi giá tối thiểu là giá tùy ý.
3. **Đầu vào:** Cùng Run/SKU/kênh/ngày/tiền tệ; chỉ target_margin thay đổi.
4. **Danh mục cần có:** Nguồn DEMO và kênh DEMO_DIRECT;4 Scenario mã riêng.
5. **Thứ tự tạo:** Scenario 10 → nhân bản 15 → nhân bản 20 → nhân bản 25; tính từng bản.
6. **Cấu hình:** MARGIN; các target khác trống; minimum_price trống; ngày 08/10/2026.
7. **Công thức:** `P=59300/(1/1,1−0,05−m)`.
8. **Màn hình:** Kịch bản giá bán; chi tiết/nhân bản; So sánh kịch bản.
9. **Giá trị mẫu:** m 10,15,20,25 nhập trên UI; lưu DB 0.10,0.15,0.20,0.25.
10. **Tính tay:** Lần lượt 78.119,76047904;83.628,20512821;89.972,41379310;97.358,20895522 VND.
11. **Kết quả mong đợi:** Biên lợi nhuận thực tế lần lượt 10/15/20/25%, trong độ làm tròn; chênh 15→20 là 5 điểm phần trăm, không phải 5% tương đối.
12. **Cách chạy:** Lưu Nháp/Tính giá bán mỗi Scenario; chọn 4 bản, kịch bản 20 làm mốc.
13. **Đọc kết quả:** So giá, phí, thuế, lợi nhuận và margin. Chọn mục tiêu cần cân nhắc thị trường, phần mềm không tự chọn giá tối ưu.
14. **Đọc diễn giải:** Cùng nguồn/kênh/phí/thuế; target/policy khác. Mọi reconciliation phải 0.
15. **Lỗi:** Nhân bản không đổi mã; điền nhiều mục tiêu; margin gần 100% làm mẫu số âm.
16. **Xử lý:** Mã riêng/đúng mục tiêu, kiểm tỷ lệ phí/thuế. Không sửa Scenario đã tính để thay margin.
17. **Ảnh hưởng:** Mục tiêu chỉ ảnh hưởng Pricing; Run nguồn/cấu trúc sản xuất không đổi.
18. **Mức hỗ trợ:** **NATIVE**. Đây là phân tích độ nhạy, không có engine tối ưu giá theo nhu cầu khách hàng.

## 14. Khuyến mại — muốn nhập giá khách trả 80.000

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Muốn bán 80.000 với vốn 58.300/phí 5%+1.000/thuế 10%.
2. **Vấn đề cần giải quyết:** Tính margin thực tế ở một giá chủ động, thay vì giải giá từ margin.
3. **Đầu vào:** Giá khách trả 80.000, C 58.300, fee 5%+1.000, thuế giả định 10%.
4. **Danh mục cần có:** Nguồn/thông số DEMO để đối chiếu; không có master Promotion/giá cố định Scenario.
5. **Thứ tự tạo:** Xem Scenario DEMO → lấy tham số đã lưu → tính ngoài phần mềm. Không tạo Scenario có ô giá mà UI không có.
6. **Cấu hình:** **[CHƯA HỖ TRỢ]** Không có phương pháp nhập giá bán cố định; minimum_price chỉ nâng sàn, không ép xuống 80.000.
7. **Công thức:** `profit=80000−(80000×5%+1000)−80000×10/110−58300`.
8. **Màn hình:** Kịch bản DEMO để đọc fee/tax/vốn; phép giá 80.000 dùng bảng tính đào tạo bên ngoài.
9. **Giá trị mẫu:** P 80.000; phí 5.000; thuế 7.272,72727273; vốn 58.300.
10. **Tính tay:** Lợi nhuận 9.427,27272727; margin 11,78409091%.
11. **Kết quả mong đợi:** **Kết quả tính tay**, không có Scenario đã tính 80.000 vì engine chưa hỗ trợ nhập giá cố định. MARGIN 20%+minimum 80.000 vẫn ra 89.972,41379310.
12. **Cách chạy:** Không có bước chạy đúng bài toán fixed price hiện nay; đừng giả lập bằng thay giá vốn. Có thể xem kịch bản mục tiêu và ghi so sánh bên ngoài.
13. **Đọc kết quả:** Phân biệt kết quả ngoài hệ thống và giá do engine giải mục tiêu; không ghi kết quả tính tay vào snapshot.
14. **Đọc diễn giải:** Snapshot DEMO chỉ chứng minh nguồn tham khảo; không là trace cho P 80.000.
15. **Lỗi:** Nhầm minimum_price thành manual price; sửa JSON để ép giá; lấy profit=P−C quên phí/thuế.
16. **Xử lý:** Dùng công thức ngoài/ghi rõ giả định; đưa giá cố định/xem trước lợi nhuận vào GAP_REGISTER, không sửa engine trong task tài liệu.
17. **Ảnh hưởng:** Giá khuyến mại giả định chỉ ảnh hưởng phân tích ngoài; không đổi Run/Scenario đã lưu.
18. **Mức hỗ trợ:** **NOT SUPPORTED** nhập giá bán cố định/khuyến mại; đọc nguồn để tính tay là **PARTIAL**.

## 15. Cước cố định, theo kg, theo tấn hoặc theo km

1. **Bối cảnh nghiệp vụ:** [INDUSTRY PATTERN + VÍ DỤ NGHIỆP VỤ] Nhà vận chuyển báo cước theo các cơ sở khác nhau. Đây là bốn phương án thay thế, không mặc nhiên cộng cả bốn.
2. **Vấn đề cần giải quyết:** Xác định đúng tổng cước và phần trên mỗi đơn vị trước khi đưa vào mô hình giá; không nhầm vận chuyển đầu vào với giao hàng bán ra.
3. **Đầu vào:** Báo giá cố định 200.000/chuyến; hoặc 1.500/kg×200 kg; hoặc 200.000/tấn×1,5 tấn; hoặc 5.000/km×100 km. Cần lượng tính cước đã được xác nhận bên ngoài.
4. **Danh mục cần có:** Nếu khoản cước được xác định thuộc chi phí sản xuất, cần CE MONEY/VND không UoM, Formula cộng tổng cước và Scheme có MANUAL; chưa có master hãng/tuyến/bảng cước.
5. **Thứ tự tạo:** Xác định bản chất khoản phí → tính tổng ngoài hệ thống → CE → Formula có test → phiên bản Scheme → Run nhập tổng. Cước giao bán ra không được tự đưa vào MANUFACTURING.
6. **Cấu hình:** Ví dụ có căn cứ chi phí đầu vào: biến `TRAIN_INBOUND_FREIGHT_TOTAL` MONEY, dòng MANUAL, OUTPUT cộng biến này. LANDED/COST_TO_SERVE không phải phạm vi Run đã thực thi được.
7. **Công thức:** Cước cố định=`F`; theo kg=`kg×VND/kg`; theo tấn=`tấn×VND/tấn`; theo km=`km×VND/km`. Tổng Run=`base_total+freight_total` nếu phân loại hợp lệ.
8. **Màn hình:** Phần tử chi phí; Thiết lập công thức; Phương án tính giá thành; Lần tính giá thành. Không có màn hình “Chạy tính cước”.
9. **Giá trị mẫu:** Bốn tổng lần lượt 200.000/300.000/300.000/500.000. Ví dụ riêng: cước đầu vào đã phân cho 10 hộp là 20.000, vốn lô 583.000.
10. **Tính tay:** Tổng sau khoản 20.000=603.000, đơn vị 60.300. Nếu cước 200.000 cho 100 hộp thì phân đơn giản 2.000/hộp; việc xác định tiêu thức này làm ngoài hệ thống.
11. **Kết quả mong đợi:** Với MANUAL hợp lệ, Run lưu 20.000 và OUTPUT 603.000. Không có trace tự lấy 200 kg/100 km, trừ khi người cấu hình tự khai báo scalar NUMBER và giải thích đơn vị.
12. **Cách chạy:** Clone Scheme, thêm dòng tiền và Formula đầu ra tương ứng, kiểm tra/kích hoạt đúng ngày rồi chạy 10 hộp với input 20.000; ghi căn cứ trong Ghi chú. Không thay đổi Scheme DEMO đã chốt.
13. **Đọc kết quả:** Khoản cước xuất hiện riêng; kiểm tra không nằm sẵn trong giá mua để tránh tính hai lần. Đơn vị 60.300 là kết quả giả định, không thay Golden 58.300.
14. **Đọc diễn giải:** Input MANUAL 20.000 và công thức cộng; trace không chứng thực cách xác định khối lượng tính cước bên ngoài.
15. **Lỗi:** Dùng MONEY/KG×QUANTITY như thể có engine đơn vị kép; chọn LANDED bị chặn; nhập cước mỗi hộp thành tổng; dùng float/nhập sai dấu nghìn.
16. **Xử lý:** Nhập tổng tiền đã xác định và phạm vi hợp lệ; nếu cần cước giao hàng, xử lý mô hình bán hàng riêng hoặc ghi gap, không đổi nhãn để vượt phạm vi.
17. **Ảnh hưởng:** Tổng cước→Run mới→giá vốn đơn vị→Scenario mới. Danh mục UoM không tự tạo biểu cước hoặc lựa chọn hãng.
18. **Mức hỗ trợ:** **CONFIGURABLE** tổng tiền MANUAL thuộc phạm vi thực thi; **PARTIAL** scalar quy ước; **NOT SUPPORTED** engine logistics/khối lượng tính cước/tuyến/phân bổ chuyến.

## 16. Lưu kho và bốc xếp

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Lô 100 hộp chịu 50 pallet-ngày×20.000 và bốc xếp 2.000/hộp.
2. **Vấn đề cần giải quyết:** Đưa chi phí phục vụ đã xác định vào giả định giá bán, không khai rằng phần mềm có bộ đo lưu kho.
3. **Đầu vào:** Lưu kho 1.000.000, handling 200.000,100 hộp; giá vốn một hộp 58.300; margin 20%; giả định không thuế/phí khác.
4. **Danh mục cần có:** Channel đào tạo riêng, Fee cố định tiền VND; Run 58.300. Không có phiếu nhập/xuất kho hay số ngày lưu kho trong luồng này.
5. **Thứ tự tạo:** Tính tiền kho/handling bên ngoài → chia cho 100 hộp → cấu hình hai loại phí cố định khác nhau → Scenario.
6. **Cấu hình:** `WAREHOUSING` fixed 10.000 và `HANDLING` fixed 2.000, LIST_PRICE, refund 0, phí đã gồm thuế, đúng kỳ và VND. Đây là cách biểu diễn khoản trừ trên đơn vị bán đã xác định.
7. **Công thức:** `fixed_per_unit=(50×20000+100×2000)/100=12000`; `P=(58300+12000)/0,8`.
8. **Màn hình:** Quy tắc phí kênh; Kịch bản giá bán; cấu thành giá và nguồn đã lưu.
9. **Giá trị mẫu:** C 58.300; tổng phí 12.000/hộp; target_margin 20; tax_mode NONE trong bài đào tạo.
10. **Tính tay:** P 87.875; phí 12.000; lợi nhuận 17.575; margin 20%.
11. **Kết quả mong đợi:** Waterfall có hai dòng phí, tổng 12.000; không tăng giá thành Run nguồn 58.300.
12. **Cách chạy:** Lưu hai quy tắc EFFECTIVE ở kênh riêng, tạo Scenario đúng kênh/ngày và tính. Không nhập 50 vào UoM hoặc mong CostPool basis PALLET_DAY tự chạy.
13. **Đọc kết quả:** Phí 12.000 cho một hộp, không 1.200.000 cho một hộp. Giữ rõ kết quả này là mô hình giá bán, không sổ kế toán kho.
14. **Đọc diễn giải:** Fee nguồn và số cố định; không có lịch sử pallet-ngày. Chứng từ chia phí bên ngoài phải được lưu theo quy trình doanh nghiệp.
15. **Lỗi:** Dùng cùng fee_type khiến chỉ một khoản thắng; lấy lô 10 hộp của Costing làm mẫu số thay 100 hộp của giả định kho; phí chưa gồm thuế.
16. **Xử lý:** Hai fee_type riêng; ghi rõ mẫu số 100 hộp; refund 0 và giá phí đã gồm thuế. Nếu cần tính theo dữ liệu kho thật, ghi gap.
17. **Ảnh hưởng:** Đổi ngày/số pallet/lượng giao ngoài hệ thống cần tạo chính sách phí/kịch bản mới; Run cũ không đổi.
18. **Mức hỗ trợ:** **PARTIAL**: Pricing thực thi tiền cố định đã quy về đơn vị; **NOT SUPPORTED** WMS/driver PALLET_DAY/tự lấy phí kho.

## 17. Xuất khẩu — thủ tục, bảo hiểm, handling

1. **Bối cảnh nghiệp vụ:** [INDUSTRY PATTERN + VÍ DỤ NGHIỆP VỤ] Doanh nghiệp xác định bên mình chịu một số khoản theo hợp đồng giao hàng; tài liệu không tự chọn Incoterms hay thuế suất.
2. **Vấn đề cần giải quyết:** Tránh bỏ chi phí ngoài giá vốn sản xuất và tránh tính bảo hiểm sai cơ sở.
3. **Đầu vào:** Thủ tục 3.000.000 VND; bảo hiểm 0,5% trị giá lô 20.000.000=100.000; handling 500.000; lô 1.000 hộp; FX VND→USD 0.00004.
4. **Danh mục cần có:** Channel EXPORT riêng, Currency USD/VND, FX SPOT,3 fee cố định đã quy về một hộp, nguồn Costing 58.300 VND.
5. **Thứ tự tạo:** Xác nhận trách nhiệm/chi phí ngoài phần mềm → chia theo 1.000 → đổi/hoặc cấu hình tiền VND và FX → fees → Scenario USD.
6. **Cấu hình:** Khoản bảo hiểm lấy từ trị giá lô bên ngoài rồi lưu fixed; không dùng fee rate 0.5% trên giá khách trả nếu hợp đồng dùng cơ sở 20 triệu khác. Thuế NONE chỉ để cô lập ví dụ.
7. **Công thức:** `extra=(3000000+100000+500000)/1000=3600VND/hộp`; `extraUSD=0,144`; `P=(2,332+0,144)/0,8`.
8. **Màn hình:** Tỷ giá; Kênh bán; Quy tắc phí kênh; Kịch bản giá bán.
9. **Giá trị mẫu:** C_USD 2,332; fee fixed USD 0,144; margin 20; không phí/thuế khác. Có thể tách ba mã phí để đọc nguồn rõ hơn.
10. **Tính tay:** P 3,095 USD; phí 0,144; lợi nhuận 0,619; margin 20%.
11. **Kết quả mong đợi:** Giá mục tiêu USD có khoản trừ đã nhập; chưa có chứng từ xuất khẩu, thuế hải quan hoặc trị giá tính thuế tự tính.
12. **Cách chạy:** Chọn nguồn VND, tiền bán USD, FX SPOT, kênh phí riêng và ngày phù hợp; Lưu Nháp/Tính giá bán.
13. **Đọc kết quả:** So bản không handling 2,915 với bản 3,095; chênh 0,18 USD gồm bù phí 0,144 và lợi nhuận mục tiêu trên giá mới.
14. **Đọc diễn giải:** Đúng FX và fee fixed; bảo hiểm không được diễn giải là 0,5% giá bán trong engine. Căn cứ 20 triệu là giả định bên ngoài.
15. **Lỗi:** Tính phí bảo hiểm hai lần; sai mẫu số 1.000; tiền phí khác USD mà thiếu FX; tưởng Channel EXPORT tự miễn thuế.
16. **Xử lý:** Kiểm tra hợp đồng, một cơ sở một lần; chọn chính sách thuế được xác nhận cho nghiệp vụ thật. Engine không quyết định nghĩa vụ pháp lý.
17. **Ảnh hưởng:** FX/phí/cơ sở phân chia đổi→Scenario mới; dữ liệu hợp đồng/chứng từ ngoài hệ thống vẫn cần quản lý riêng.
18. **Mức hỗ trợ:** **PARTIAL** qua tiền cố định; **NOT SUPPORTED** bộ Incoterms/customs/insurance tự động hoặc thuế theo khai báo.

## 18. So sánh các kênh bán

1. **Bối cảnh nghiệp vụ:** [VÍ DỤ NGHIỆP VỤ] Đặt ba kết quả bài 8/9/10 cạnh nhau cho cùng SKU.
2. **Vấn đề cần giải quyết:** So giá, phí, lợi nhuận và mục tiêu; không chọn “tốt nhất” chỉ vì giá cao nhất.
3. **Đầu vào:** Ba Scenario CALCULATED cùng Run/basis VND, ngày 08/10; mục tiêu direct margin 20, distributor markup 25, marketplace margin 20.
4. **Danh mục cần có:** Các kết quả đã tính ở bài 8–10; không cần thêm bảng “Comparison”.
5. **Thứ tự tạo:** Tính hoàn tất từng Scenario → mở So sánh kịch bản → lọc Product/SKU → chọn 2–5 bản → chọn mốc.
6. **Cấu hình:** Chọn direct làm Kịch bản mốc. Cùng SKU, đơn vị đầu ra và policy; không trộn SKU hộp quà ở bài 5.
7. **Công thức:** Chênh tiền=`candidate−baseline`; chênh margin theo điểm phần trăm. Phần trăm chênh chỉ có khi baseline khác 0.
8. **Màn hình:** GIÁ BÁN → So sánh kịch bản; nút Chọn/Bỏ chọn/So sánh kịch bản; link xem chi tiết từng Scenario.
9. **Giá trị mẫu:** Direct 72.875; distributor 81.965,74642127; marketplace 102.361,11111111 VND.
10. **Tính tay:** Giá tăng so direct 9.090,74642127 và 29.486,11111111; lợi nhuận direct 14.575, distributor 14.575, marketplace 20.472,22222222.
11. **Kết quả mong đợi:** Ma trận giữ số snapshot, không chạy lại engine. Distributor margin 17,78181818% thấp hơn 20% nhưng đúng markup 25%.
12. **Cách chạy:** Lọc Product, tích ba bản, chọn direct làm mốc, bấm So sánh. Giữ lựa chọn khi đổi trang; Đặt lại khi muốn bỏ giả định cũ.
13. **Đọc kết quả:** Đọc đồng thời chi phí kênh/mục tiêu/phí/thuế. Cần đánh giá sức mua, volume, rủi ro bên ngoài; phần mềm không có dự báo cầu.
14. **Đọc diễn giải:** Mở từng Scenario xác nhận cùng Run nguồn và đúng phí/thuế; ma trận không tạo trace phép tính mới.
15. **Lỗi:** Chọn 1 hoặc 6 bản; khác SKU/basis; snapshot không hợp lệ; khác tiền tệ nên không delta tiền.
16. **Xử lý:** Chọn 2–5 bản hợp lệ cùng phạm vi; muốn đối chiếu tiền phải chủ động tính cùng đồng tiền qua Scenario, không chuyển đổi trong comparison.
17. **Ảnh hưởng:** Lựa chọn/mốc chỉ đổi cách xem, không sửa Scenario/Run. Liên kết so sánh lưu điều kiện URL, không là bản snapshot mới.
18. **Mức hỗ trợ:** **NATIVE** so sánh snapshot Pricing; **NOT SUPPORTED** tự tối ưu kênh hoặc ma trận Costing nhiều SKU.

## 19. Đọc lại lịch sử sau khi đổi nguồn

1. **Bối cảnh nghiệp vụ:** [DEMO] Đã khóa Run 07/10 và tính Pricing 08/10; sau đó thêm giá/rate/phí/thuế tháng 11.
2. **Vấn đề cần giải quyết:** Giải thích kết quả cũ từ dữ liệu thực dùng, không bị giá mới làm thay đổi.
3. **Đầu vào:** Run 583.000/58.300; Pricing 89.972,41379310; các snapshot nguồn và trace đã lưu.
4. **Danh mục cần có:** Bộ DEMO cũ và future; giữ version cũ, không xóa/sửa nội dung đã chốt.
5. **Thứ tự tạo:** Tính cũ → lưu mã Run/Scenario → tạo kỳ nguồn mới → mở lại bản cũ → tùy chọn Tạo lần tính mới.
6. **Cấu hình:** Giá/rate Costing cũ kết thúc 31/10, mới từ 01/11; phí/thuế Pricing cũ kết thúc 01/11, mới từ 01/11.
7. **Công thức:** Kết quả cũ đọc giá trị đã lưu; không tra lại “giá hiện tại”. Rerun là phép chạy nguồn hiện tại theo ngày được chọn.
8. **Màn hình:** Lần tính giá thành → chi tiết → diễn giải/snapshot; Kịch bản giá bán → chi tiết → Nguồn và diễn giải đã lưu.
9. **Giá trị mẫu:** Run cũ 583.000; Run tương lai 647.000; Scenario cũ 89.972,41379310; Scenario tương lai DEMO 92.526,00506044 vẫn dùng giá vốn cũ 58.300.
10. **Tính tay:** So nguồn cũ: cà phê 100.000/rates 120.000+60.000 với nguồn tương lai 120.000/rates 144.000+72.000. Giữ tổng cũ 583.000 không cộng delta 64.000 vào bản cũ.
11. **Kết quả mong đợi:** Run/Scenario cũ bất biến; mở lại vẫn khớp; Run mới liên kết bản gốc nhưng có ID/key mới.
12. **Cách chạy:** Chỉ mở các bản cũ để kiểm tra; muốn chạy mới chọn Tạo lần tính mới, kiểm tra lại ngày/sản lượng rồi chạy. Scenario đã tính nhân bản thành bản mới.
13. **Đọc kết quả:** Ghi số/mã Run/ngày/Run nguồn của Scenario. Không trộn ngày định giá 08/10 với ngày tính giá thành 07/10.
14. **Đọc diễn giải:** Nguồn đã snapshot, số phiên bản/biểu thức/quy đổi/giá; không mở master hôm nay rồi coi là bằng chứng cho quá khứ.
15. **Lỗi:** Lấy Run tương lai làm nguồn rồi kỳ vọng giá cũ; dùng Rerun để “khôi phục” offline; comparison báo snapshot hỏng.
16. **Xử lý:** Mở đúng snapshot cũ; Rerun không phải replay offline. Snapshot không hợp lệ cần kiểm tra dữ liệu kỹ thuật, không sửa JSON bằng tay để qua kiểm tra.
17. **Ảnh hưởng:** Master mới chỉ ảnh hưởng chạy mới; history vẫn độc lập. Kết quả cũ không tự lấy tên/giá mới để viết lại.
18. **Mức hỗ trợ:** **NATIVE** đọc lịch sử và diễn giải; **NOT SUPPORTED** khôi phục/chạy lại ngoại tuyến chỉ từ snapshot.

## 20. Mô phỏng giá tương lai — tách hai trục thay đổi

1. **Bối cảnh nghiệp vụ:** [DEMO + VÍ DỤ NGHIỆP VỤ] Từ 01/11 phí hoa hồng 6%, phí fixed 1.000, thuế giả định 11%; giá vốn sản xuất có thể giữ 58.300 hoặc đổi 64.700.
2. **Vấn đề cần giải quyết:** Phân biệt thay phí chính sách bán với thay giá vốn sản xuất, không quy mọi chênh lệch cho FX.
3. **Đầu vào:** Hai Run đã khóa (07/10 và 01/11), kênh DEMO_DIRECT, m 20%, ngày định giá 01/11, VND.
4. **Danh mục cần có:** Giá/rate tương lai Costing; phí/thuế tương lai Pricing; scheme/formula nguồn như DEMO; không cần FX khi đều cùng VND.
5. **Thứ tự tạo:** Nguồn future → Run tương lai 647.000 → Scenario A giữ Run cũ → Scenario B chọn Run tương lai → so sánh.
6. **Cấu hình:** A là DEMO_PRICING_FUTURE dùng giá vốn 58.300; B là giả định mới mã TRAIN_BOTH_FUTURE dùng 64.700. Ngày định giá giống nhau 01/11.
7. **Công thức:** `P=(C+1000)/(1/1,11−0,06−0,20)`; C khác nhau, fee/tax giống nhau.
8. **Màn hình:** Giá nhà cung cấp; Đơn giá nguồn lực; Quy tắc phí kênh; Quy tắc thuế; Run; Scenario; Comparison.
9. **Giá trị mẫu:** A 58.300; B 64.700; hoa hồng 6%/fixed 1.000; thuế 11% giả định. Không có nguồn tương lai thì phải chuẩn bị trước, không tự lấy lại nguồn cũ để thay thế.
10. **Tính tay:** A 92.526,00506044; B 102.511,94827101 VND; delta 9.985,94321057. B: phí 7.150,71689626, thuế 10.158,84172055, profit 20.502,38965420.
11. **Kết quả mong đợi:** A đúng Golden Pricing future 92.526…, B là kết quả giả định kết hợp cả hai thay đổi; cả hai margin 20%.
12. **Cách chạy:** Dùng DEMO_PRICING_FUTURE đã tính để xem A; nhân bản mã mới, chọn Run tương lai 64.700, Lưu Nháp/Tính giá bán; chọn A/B trong Comparison.
13. **Đọc kết quả:** Đầu tiên xem Run nguồn, sau đó phí/thuế. Không thay số 64700 vào công thức A rồi nói Golden DEMO sai kết quả.
14. **Đọc diễn giải:** A/B cùng phí v2/thuế v2 nhưng khác Run/mã nguồn giá vốn. Run cũ/Scenario Golden 08/10 giữ nguyên.
15. **Lỗi:** Kỳ phí chồng nhau; dùng nhầm ngày 31/10; giá/rate future Nháp; quên tạo Run tương lai; ngày tương lai chỉ điền valid_from thay pricing_date.
16. **Xử lý:** Tra nguồn đúng date; Pricing end 01/11 loại trừ, Costing end 31/10 bao gồm; dùng Ngày định giá 01/11 để tra policy bán.
17. **Ảnh hưởng:** Giá/rate→Run tương lai; phí/thuế/FX→Scenario future; không có một thao tác tự chạy lại toàn bộ chuỗi.
18. **Mức hỗ trợ:** **NATIVE** mô phỏng bằng nguồn có kỳ và Scenario; **PARTIAL** chuẩn bị nguồn sản xuất; **NOT SUPPORTED** dự báo giá thị trường tự động.

## Bảng chọn bài và mức hỗ trợ

| Bài | Trọng tâm | Phần thực thi đã có | Giới hạn cần giữ |
|---|---|---|---|
|1| Giá thành đầy đủ | NATIVE | Dùng nguồn DEMO đã chuẩn bị |
|2| Lô và setup | NATIVE | Không coi là lập lịch/công suất hữu hạn |
|3| Nhà cung cấp A/B | PARTIAL | Không có input chọn Supplier tùy ý cùng ngày |
|4| Thay định mức | NATIVE | Chuẩn bị hiệu lực nguồn mới ngoài UI |
|5| Bao bì hai SKU | NATIVE | Phẳng; không so khác SKU trong Pricing comparison |
|6| Máy A/B | NATIVE | Một primary_resource mỗi công đoạn |
|7| Chi phí chung | NATIVE | Chỉ NORMAL_CAPACITY, kỳ ngoài UI |
|8–13| Kênh/mục tiêu/FX | NATIVE | Nguồn và chính sách đúng phạm vi bộ tính |
|14| Giá khuyến mại nhập tay | NOT SUPPORTED | Tính tay bên ngoài, không sửa snapshot |
|15| Vận chuyển | CONFIGURABLE / PARTIAL | Tổng tiền hợp lệ; không có logistics engine |
|16–17| Kho/handling/xuất khẩu | PARTIAL | Tự quy tiền về một đơn vị, không tự đo driver |
|18| So sánh kênh | NATIVE |2–5 snapshot, cùng phạm vi/basis |
|19| Lịch sử | NATIVE | Đọc snapshot, không replay offline |
|20| Tương lai | NATIVE | Nguồn có hiệu lực, không dự báo tự động |

## Nguồn và cách kiểm tra số

**[HỆ THỐNG HIỆN TẠI]** Quy tắc đã đối chiếu [bộ máy Costing](../../apps/costing/engine/runner.py), [resolvers sản xuất](../../apps/costing/engine/resolvers/manufacturing.py), [giá/rate](../../apps/costing/engine/resolvers/prices.py), [phân bổ](../../apps/costing/engine/resolvers/allocation.py), [solver Pricing](../../apps/pricing/engine/solver.py), [resolver Pricing](../../apps/pricing/engine/resolvers.py), [DEMO Costing](../../apps/costing/demo_data.py) và [DEMO Pricing](../../apps/pricing/demo_scenario.py).

Số Pricing 8–13/16–17/20 được kiểm tra bằng phép giải Decimal độc lập rồi đối chiếu solver thuần, không truy cập DB. Đây không phải lời xác nhận mọi dữ liệu TRAIN đã được tạo/chạy trên production. Golden DEMO và hành vi nguồn/snapshot còn được kiểm tra qua bộ 111 test trong [biên bản đối chiếu](SOURCE_VERIFICATION.md).
