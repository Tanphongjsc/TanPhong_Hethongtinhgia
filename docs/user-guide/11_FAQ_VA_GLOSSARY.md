# 11. Câu hỏi thường gặp, thuật ngữ và tác vụ vận hành

**[HỆ THỐNG HIỆN TẠI]** Câu trả lời phản ánh source đã kiểm tra ngày 09/10/2026. Với lỗi cụ thể đọc [chương 10](10_LOI_THUONG_GAP_VA_CACH_XU_LY.md); với giới hạn đọc [GAP_REGISTER](GAP_REGISTER.md).

## Câu hỏi thường gặp

### 1. Phần mềm giúp tôi làm gì?

Quản lý dữ liệu cấu thành sản xuất, chạy giá thành, giải giá bán theo mục tiêu và so sánh kịch bản. Nó không thay thế hệ thống kho, kế toán giao dịch hay quản lý bán hàng đầy đủ.

### 2. Tôi nên bắt đầu từ đâu?

Đọc 01–03, sau đó học bài Cappuccino 09 bằng bộ mẫu đã chuẩn bị. Tra 12 khi chưa rõ một field; tránh bắt đầu bằng việc nhập công thức tùy ý.

### 3. Vì sao mở hệ thống thấy danh mục thay vì dashboard?

Trang gốc dẫn trực tiếp tới Phần tử chi phí. Menu thực có 28 mục; không có bảng chỉ số tổng quan phải tìm thêm.

### 4. Tôi có thể khởi tạo database rỗng hoàn toàn chỉ bằng UI không?

Chưa. Một số nguồn mới lưu Nháp chưa có thao tác đưa vào hiệu lực; dữ liệu kỳ chi phí chung chưa có form. Chương 03 chỉ điểm dừng; nhờ người phụ trách chuẩn bị môi trường đúng quy trình.

### 5. Item, Product và SKU khác nhau thế nào?

Item là vật tư/hàng hóa dùng cho giá mua và thành phần. Product là sản phẩm nghiệp vụ gốc. SKU là quy cách/biến thể bán thuộc Product. Tạo Product không tự tạo Item hoặc SKU.

### 6. Nhóm chi phí của CE có phải CostPool không?

Không. Nhóm chi phí của CE phân loại biến. CostPool chứa số liệu chi phí kỳ phục vụ phân bổ; hiện không có bảng thành viên tự gom các CE.

### 7. Tạo CE mới có tự làm tổng chi phí tăng không?

Không. Cần dòng Scheme có nguồn và công thức đầu ra sử dụng biến ấy. Tên CE hay line_type SUBTOTAL không tự tạo phép cộng.

### 8. Mã bị đổi thành chữ hoa có phải lỗi?

Đa số mã được trim/uppercase để ổn định tham chiếu. Tên/mô tả được trim; mã tiền, enum và mã kỹ thuật không dịch sang tiếng Việt. Tra 12 về ngoại lệ.

### 9. Trường tùy chọn có nên nhập 0 không?

Không mặc nhiên. Trống và 0 khác nhau. Ví dụ phí có fixed_amount 0 vẫn cần currency; nhập cả rate/fixed trống thì lỗi. Item nhập số đo 0 vẫn có thể kích hoạt yêu cầu đơn vị.

### 10. Số tiền 125.000 nhập thế nào?

Nhập `125000`, không chèn dấu nghìn. Số lẻ dùng dấu chấm khi nhập và trong Formula. Hiển thị dùng định dạng Việt Nam; không đổi độ chính xác database.

### 11. Tại sao danh mục có ở list nhưng không ở dropdown tạo mới?

Danh mục có thể ngừng hoạt động, sai Product/nhóm/đại lượng hoặc không phù hợp ngữ cảnh. Form sửa thường giữ chính tham chiếu cũ đã ngừng; điều đó không cho chọn mọi bản ngừng khác.

### 12. Inactive có xóa lịch sử không?

Không. Ngừng hoạt động chủ yếu ngăn dùng trong cấu hình mới. Run/Scenario đã lưu vẫn có nguồn snapshot; engine mới còn kiểm tra master hoạt động.

### 13. Đặt đơn vị cơ sở KG có tự đổi G→KG không?

Không. Cần UoM Conversion trực tiếp hoặc nghịch đảo hợp lệ. Mã KG/G không phải quy tắc tính hard-code.

### 14. Quy đổi qua chuỗi G→KG→Tấn được không?

Resolver hiện không nối chuỗi. Cần đúng cặp trực tiếp/nghịch đảo cho phép đổi đang dùng; không tạo nhiều nguồn cùng phù hợp.

### 15. Quy đổi riêng Item có được ưu tiên hơn quy đổi chung?

Không tự ưu tiên. Cả hai cùng phù hợp có thể gây AMBIGUOUS_CONVERSION; kiểm tra phạm vi và kỳ.

### 16. Hai nhà cung cấp cùng giá Item thì phần mềm chọn rẻ nhất?

Không. Cần một giá đủ điều kiện. Nhiều giá phù hợp gây lỗi mơ hồ; Run chưa có input chọn Supplier ưu tiên.

### 17. Min_qty chọn bậc giá cao nhất tự động?

Không. Ngưỡng được kiểm tra nhưng không có chính sách tự chọn bậc tốt nhất; nếu nhiều mức cùng đủ điều kiện vẫn có thể mơ hồ.

### 18. Giá mua có thuế hoặc USD tính trong Run VND được không?

Hiện Costing chặn thuế mua chưa hỗ trợ và khác tiền tệ nguồn. TaxRule/FX của Pricing không tự áp vào Costing.

### 19. BOM có phải luôn cho 1 sản phẩm?

Không. output_qty/output_uom của RecipeVersion xác định cơ sở. Run scale lượng cần theo cơ sở thực, yield và scrap.

### 20. Hao hụt 5% có lấy qty×1,05 không?

Quy tắc hiện tại là `qty×scale/yield_rate/(1−scrap_rate)`. Nếu scrap 0.05, chia 0.95; không tự đổi thành nhân 1.05.

### 21. PackagingVersion không có sản lượng chuẩn thì nhập ở đâu?

Nhập Sản lượng cơ sở đóng gói và Đơn vị cơ sở đóng gói trên Run khi Scheme dùng PACKAGING_COST. Với DEMO là 1 Hộp. Giá trị được lưu vào context/snapshot lần tính.

### 22. Có cấp cha trong bao bì thì engine tự nhân cây?

Chưa. Lượng dòng phải đã quy về cơ sở đóng gói; không nhân thêm units_per_parent lần nữa. Cây cấp là thông tin mô tả hiện tại.

### 23. Setup được nhân bao nhiêu lần?

Một lần cho mỗi Run. Run_time scale theo quantity_basis/quantity_uom công đoạn; nếu thiếu basis thì dùng batch_size/batch_uom phiên bản.

### 24. Một công đoạn gán máy và hai người được không?

Hiện một primary_resource tùy chọn trên RoutingOperation, chưa có Operation Resource nhiều dòng. Có thể tách công đoạn khi đúng nghiệp vụ, không giả là đồng thời đa nguồn lực đã hỗ trợ.

### 25. Rate_type STANDARD/ACTUAL có quyết định giá thắng?

Không. Resolver hiện không lọc rate_type; hai rate hiệu lực cùng Resource/ngày vẫn gây mơ hồ.

### 26. Basis MACHINE_HOUR có trong form thì chạy phân bổ được?

Chưa. Engine hiện chỉ NORMAL_CAPACITY. Lưu được code không đồng nghĩa có nguồn driver/thuật toán thực thi.

### 27. Amount của CostPool nhập ở đâu?

Trong số liệu CostPoolPeriod đã chuẩn bị ngoài UI; CostPool form không có amount kỳ. Bài DEMO đã có 530.000/công suất 100 hộp.

### 28. Run vượt công suất bình thường xử lý thế nào?

Resolver hiện chặn. Không tự tăng capacity để qua lỗi; kiểm tra đúng đơn vị/kỳ hoặc ghi yêu cầu chính sách xử lý vượt công suất.

### 29. Formula `$` và `@` khác gì?

`$MÃ` là CostElement; `@MÃ` là Formula. Chúng phân biệt hai không gian mã; công thức lồng vẫn phải có phụ thuộc đúng kiểu/ngày.

### 30. Có viết Python/SQL/LOOKUP trong Formula được không?

Không. DSL chỉ có operators/hàm được cho phép; không eval Python/SQL. LOOKUP/EXTERNAL có metadata nhưng chưa có đường thực thi tương ứng.

### 31. Test Formula có tự lấy giá BOM không?

Không. Test nhận các input người nhập theo đồ thị biến. Các resolver giá mua/BOM chạy trong CostingRun, không trong mẫu test scalar.

### 32. Công thức kiểm tra hợp lệ sao chưa kích hoạt được?

Cần ngày bắt đầu, header hoạt động, phụ thuộc EFFECTIVE và ít nhất một bộ test đang dùng đạt. VALID chỉ là kiểm tra cấu trúc/kiểu, không thay mọi điều kiện kích hoạt.

### 33. Scheme đã kích hoạt có đảm bảo mọi Run chạy được?

Không. Kiểm tra cấu hình không tra đủ giá/rate/kỳ của từng ngày chạy. Dùng checklist 06 và 13 trước Run.

### 34. Tổng Run có phải tổng tất cả dòng?

Không. Lấy đúng OUTPUT của Scheme. SUBTOTAL/OUTPUT đã chứa các dòng trước; cộng mọi dòng sẽ bị lặp.

### 35. Sửa giá hôm nay có đổi Run đã khóa?

Không. Run đọc kết quả/snapshot đã lưu. Tạo lần tính mới tra nguồn lại theo ngày đã chọn; giá mới hoặc sửa nguồn cũ có thể ảnh hưởng lần mới.

### 36. Rerun có phải phát lại snapshot cũ?

Không. Rerun điền lại yêu cầu và tạo record mới, resolver đọc các nguồn hiện tại theo ngày. Chưa có replay ngoại tuyến chỉ từ snapshot.

### 37. Tại sao ngày đúng mà bản Nháp không được chọn?

Badge hiệu lực theo ngày và status bản ghi là hai thông tin. Resolver cần status EFFECTIVE đồng thời khoảng ngày đúng, nguồn duy nhất/header hoạt động.

### 38. Ngày kết thúc được tính hay không?

Costing bao gồm ngày cuối:31/10 dùng giá cũ. Pricing phí/thuế/FX loại trừ mốc cuối: kết thúc bản cũ 01/11, bắt đầu bản mới 01/11 thì chỉ bản mới dùng ngày 01/11. Xem 03/07.

### 39. Giá vốn Pricing có lấy tổng 583.000 không?

Lấy per_unit 58.300 của Run 10 hộp đã khóa; một đơn vị bán là đơn vị đầu ra Run. Không tự đổi Hộp sang Thùng.

### 40. Margin 20% và markup 20% có giống nhau?

Không. Không phí/thuế, vốn 100: markup 20% ra 120, margin 20% ra 125. Trong hệ thống margin=lợi nhuận/giá khách trả sau phí/thuế; markup=lợi nhuận/giá vốn.

### 41. Phí fixed 1.000 áp cho Run 10 hộp hay 1 hộp?

Pricing áp cho 1 đơn vị đầu ra Costing, tức 1 hộp trong DEMO. Chưa có context đơn hàng để tự chia fixed theo số hộp/đơn.

### 42. Hai quy tắc phí cùng loại được cộng không?

Chọn một quy tắc thắng: SKU>nhóm>chung kênh, rồi priority lớn nhất. Hòa thì lỗi; các loại phí khác nhau được cộng.

### 43. Thuế 10% trên P 110 là 11?

Với mô hình P đã gồm thuế 10%, cơ sở trước thuế 100 và thuế 10. Nhiều loại thuế dùng chung cơ sở trước thuế, cộng song song, không thuế chồng thuế.

### 44. Không có TaxRule thì engine coi thuế 0?

Nếu REQUIRED thì báo thiếu thuế. Muốn giả định không thuế phải chọn NONE rõ ràng; quyết định thuế thực tế do doanh nghiệp xác nhận.

### 45. FX bắt đầu 09:00 sao chưa được dùng cho ngày đó?

Pricing tra FX tại 00:00 ngày định giá giờ Việt Nam. Cần nguồn đã hiệu lực lúc đó; không fallback “mới nhất trong ngày”.

### 46. Nhập tỷ giá USD→VND có tự đảo để bán USD?

Không. Cần đúng chiều đổi từ tiền đầu vào sang tiền bán và đúng rate_type. Không nối chuỗi qua tiền trung gian.

### 47. Muốn bán 80.000 thì nhập Giá bán tối thiểu 80.000?

Ô này chỉ nâng giá thấp đến sàn. Nếu engine giải ra 89.972 thì vẫn 89.972. Nhập giá bán cố định và xem margin thực tế chưa hỗ trợ; đọc kịch bản 14.

### 48. Tính Scenario đã CALCULATED lần nữa có cập nhật phí mới?

Không. Trả snapshot cũ. Muốn thử policy/ngày/giá vốn mới dùng Nhân bản thành kịch bản mới, mã mới rồi tính.

### 49. So sánh VND với USD có tự quy đổi chênh lệch?

Không. Tiền khác thì hiện riêng, không delta tiền. Có thể chủ động tính Scenario cùng tiền bán với giả định FX rõ ràng rồi so sánh.

### 50. Tại sao chỉ so sánh 2–5 bản và cùng SKU?

Để giữ phạm vi/basis/đơn vị/policy tương thích; comparison đọc snapshot, không chuẩn hóa quy cách khác nhau. Chọn dữ liệu phù hợp thay vì đổi tên để ép so sánh.

### 51. Có tính cước/kho/hải quan trực tiếp được không?

Chưa có engine chuyên biệt. Có thể nhập tổng tiền đã xác định đúng scope hoặc phí trên đơn vị bán khi đúng chính sách; không gọi là bộ tự đo driver/phân bổ chuyến hàng. Xem bài 15–17 và matrix 14.

### 52. Dữ liệu thay đổi trong khi đang nhập thì làm gì?

Nếu form báo tham chiếu không còn hợp lệ, tải lại form/chọn lại master và kiểm tra UI phụ thuộc đã tải xong. Không nhấn submit liên tục khi đang xử lý.

### 53. Khi lỗi cần ghi gì để người hỗ trợ tìm đúng?

Tên trang, mã Product/SKU/Scheme, ngày/lượng/đơn vị/tiền, mã Run/Scenario, thông báo và Mã tham chiếu. Đọc trace trước; không gửi secret/thông tin kết nối cơ sở dữ liệu.

## Bảng “muốn làm gì thì vào đâu?”

| Muốn làm | Menu / thao tác | Kiểm tra trước / sau |
|---|---|---|
| Thêm vật tư | Vật tư / Hàng hóa → Thêm mới | Có nhóm/UoM; mã/type/đơn vị đúng |
| Đổi tên vật tư | Chi tiết → Chỉnh sửa | Run cũ giữ nhãn đã lưu |
| Dừng chọn master mới | Chỉnh sửa → bỏ Đang hoạt động | Xem downstream; xác nhận nếu hiện |
| Đổi giá mua cho kỳ mới | Giá nhà cung cấp → Thêm mới | Ngày không mơ hồ; nguồn mới Nháp chưa có UI hiệu lực |
| Đổi currency code | Không đổi khóa chính đang dùng | Tạo mã tiền đúng, không sửa ID tham chiếu |
| Thêm đơn vị | Nhóm đơn vị trước → Đơn vị tính | Đại lượng/precision đúng |
| Dùng đơn vị khác | Quy đổi đơn vị tính | Một cặp phù hợp theo ngày/Item |
| Thêm sản phẩm | Nhóm sản phẩm/UoM → Sản phẩm | Không tự sinh Item/SKU |
| Thêm quy cách | SKU → chọn Product | Lượng tịnh và đơn vị bán rõ |
| Đổi công thức sản xuất | BOM → Tạo phiên bản mới | Bản cũ giữ; không chồng kỳ |
| Đổi thành phần bao bì | Bao bì → phiên bản Nháp → dòng | Basis Run/assignment SKU đúng |
| Gán bao bì SKU | Bao bì → liên kết SKU | Cùng Product, assignment chính duy nhất |
| Thêm máy | Trung tâm → Nguồn lực → Rate | Rate hiệu lực duy nhất/đúng UoM |
| Đổi thời gian công đoạn | Routing → phiên bản mới | Setup/run/basis không trộn |
| Thay pool amount | Chuẩn bị dữ liệu kỳ ngoài UI | Chưa có form CostPoolPeriod |
| Thêm biến tính | CE → Formula/Scheme | Cần nguồn thực thi và OUTPUT dùng biến |
| Kiểm tra Formula | Thiết lập công thức → phiên bản | Kiểm tra công thức/ Kiểm thử/ Lưu bộ kiểm thử |
| Chốt Formula/Scheme hợp lệ | Kích hoạt theo module | Ngày/phụ thuộc/test/cấu hình đạt |
| Chạy giá thành | Lần tính giá thành → Chạy tính giá | Preflight chương 06/13 |
| Tìm số nguyên liệu từ đâu | Run → Nguồn dữ liệu / Diễn giải | Lượng/quy đổi/giá/Item/Supplier |
| Thử ngày/giá mới | Run → Tạo lần tính mới | Chọn lại nguồn theo ngày, giữ bản cũ |
| Đổi phí/thuế tương lai | Đóng kỳ đủ điều kiện rồi thêm bản mới | Pricing kết thúc loại trừ ngày cuối, không sửa kỳ cũ |
| Định giá | Kịch bản giá bán → Lưu Nháp → Tính giá bán | Run đã khóa, mục tiêu/thuế/FX đúng |
| Thử margin khác | Nhân bản thành kịch bản mới | Mã mới, chỉ một mục tiêu |
| So sánh kênh | So sánh kịch bản |2–5 bản, cùng SKU/basis, đặt mốc |
| Giải thích số cũ | Mở snapshot/trace đã lưu | Không dùng master hôm nay thay bằng chứng cũ |

## Thuật ngữ nghiệp vụ và mã kỹ thuật

| Thuật ngữ | Nghĩa trong hệ thống |
|---|---|
| CostElement / CE | Phần tử chi phí hoặc biến nghiệp vụ có kiểu |
| Value type | MONEY/NUMBER/PERCENT/QUANTITY/BOOLEAN/TEXT; chi phối input và tính toán |
| Dimension | Đại lượng, ví dụ MASS/TIME/COUNT; khác mã UoM |
| UoM | Đơn vị tính có nhóm đại lượng và precision |
| Conversion factor | Lượng đích=lượng nguồn×factor; có kỳ và phạm vi Item |
| Currency | Mã tiền và số chữ số hiển thị, không phải tỷ giá |
| Item | Vật tư/hàng hóa cho BOM/giá mua/bao bì |
| Product | Sản phẩm gốc |
| SKU | Quy cách/biến thể bán cụ thể thuộc Product |
| Net quantity | Lượng tịnh của SKU với đơn vị; không phải số SKU trong Run |
| SupplierPrice | Báo giá có đơn vị/tiền/ngày chứ không chỉ current_price |
| Recipe / BOM | Định mức đầu vào theo lượng đầu ra chuẩn |
| Recipe line | Một Item/qty/UoM/scrap trong phiên bản BOM |
| Yield rate | Hệ số thu hồi; engine chia lượng cần cho hệ số này |
| Scrap rate | Hao hụt; engine chia cho 1−scrap |
| Packaging config | Cấu hình thành phần bao bì |
| Packaging assignment | Liên kết SKU và cấu hình theo ngày/is_primary |
| Packaging basis | Sản lượng/đơn vị mà qty dòng bao bì đáp ứng; nhập ở Run |
| Work center | Nơi thực hiện công đoạn |
| Resource | Máy/người/nguồn lực dùng trong công đoạn |
| Resource rate | Tiền trên đơn vị sử dụng, hiệu lực theo ngày |
| Routing | Quy trình và các công đoạn theo thứ tự |
| Operation | Công đoạn với workcenter/primary_resource/thời gian/basis |
| Setup time | Thời gian chuẩn bị tính một lần mỗi Run |
| Run time | Thời gian chạy scale theo basis/batch |
| Quantity basis | Sản lượng tương ứng run_time; không mặc định 1 |
| Cost pool | Nhóm chi phí và số liệu kỳ cho phân bổ |
| Normal capacity | Công suất bình thường làm mẫu số phân bổ hiện hỗ trợ |
| Allocation rule | Quy tắc cấu hình; không phải nút chạy phân bổ |
| Driver | Tiêu thức phân bổ; lưu được code chưa chắc engine đã dùng |
| Formula / DSL | Biểu thức an toàn được parser/typechecker kiểm tra |
| Formula dependency | Biến/công thức phụ thuộc phải đủ kiểu/nguồn/hiệu lực |
| Costing scheme | Phương án cấu hình dòng/nguồn/công thức/đầu ra |
| SYSTEM | Nguồn resolver đã đăng ký, không tự nhập dữ liệu tùy ý |
| MANUAL | Input thủ công trước Run, không sửa kết quả đã khóa |
| FORMULA | Nguồn tính biểu thức |
| INPUT / SUBTOTAL / OUTPUT | Dòng đầu vào/tổng phụ/đầu ra; không cộng lặp tất cả |
| Costing run | Một lần thực thi với ngày/sản lượng/cấu hình nguồn |
| Per-unit cost | OUTPUT chia quantity nhập; đơn vị là quantity_uom |
| Version | Nội dung cấu hình riêng trong cùng header |
| Effective date | Khoảng ngày nguồn được xem xét; khác status |
| Snapshot | Bản chụp dữ liệu và kết quả đã dùng/đã lưu |
| Explain trace | Diễn giải từng bước tạo số, nguồn và làm tròn |
| Hash | Dấu nhận diện nội dung để kiểm tra tính nhất quán, không ô nhập |
| Rerun | Run mới từ yêu cầu cũ và nguồn hiện tại theo ngày |
| Channel | Kênh bán/phạm vi áp dụng phí, không tự kết nối sàn |
| Fee base | Cơ sở phí; hiện LIST_PRICE là giá khách trả |
| Fee floor/cap | Sàn/trần số tiền của từng quy tắc phí |
| Tax inclusive/exclusive | Thuế đã gồm/chưa gồm giá niêm yết; giá khách trả vẫn gồm thuế |
| FX | Tỷ giá đúng chiều và loại tại 00:00 ngày định giá |
| Margin | Lợi nhuận/giá khách trả trong policy hiện tại |
| Markup | Lợi nhuận/giá vốn |
| Price waterfall | Cấu thành giá: giá−phí−thuế−vốn=lợi nhuận |
| Pricing scenario | Giả định đã lưu, lấy vốn đơn vị từ Run đã khóa |
| Baseline | Kịch bản mốc của so sánh |
| Percentage point | Điểm phần trăm;25%−20%=5 điểm, khác 5% tương đối |
| Landed cost | Chi phí đến kho; chưa có đường Costing execution cho scope LANDED |
| Cost to serve | Chi phí phục vụ khách/kênh; chưa có engine chuyên biệt hiện nay |
| Contribution margin | Số dư đảm phí trừ biến phí; khác profit trừ full cost trong Scenario |

## Nhịp kiểm tra vận hành gợi ý

**Trước mỗi Run:** ngày, sản lượng/basis, một nguồn hiệu lực, UoM/tiền tệ, Scheme/Formula, đầu vào thủ công. **Trước mỗi Scenario:** nguồn Run, kênh/ngày, phí/thuế/FX, đúng mục tiêu. **Khi đổi kỳ:** nguồn cũ/mới không mơ hồ và quy tắc ngày đúng module. **Cuối buổi học:** lưu mã Run/Scenario, đối chiếu Golden/trace; không xóa lịch sử để “dọn mẫu”.

### Hằng ngày, hằng tuần và khi kết thúc kỳ

Đây là **[VÍ DỤ NGHIỆP VỤ]** về tổ chức công việc. Hệ thống chưa có lịch nhắc tự động; người vận hành tự kiểm tra trên các danh sách và chi tiết.

| Thời điểm | Việc cần kiểm tra | Kết quả cần đạt |
|---|---|---|
| Trước lần tính đầu ngày | Báo giá, đơn giá nguồn lực, tỷ giá và thay đổi sản xuất đã nhận; ngày cần tính | Nguồn đúng tiền/đơn vị/kỳ; không lấy ngày hôm nay thay ngày nghiệp vụ |
| Sau mỗi lỗi tính | Mã Run/Scenario, thông báo, mã tham chiếu và nguồn được chọn | Sửa đúng nguồn hoặc ô nhập; giữ bản cũ và chạy/tạo bản mới theo module |
| Hằng tuần | Nguồn sắp hết kỳ, bản Nháp đang chờ chuẩn bị, quy đổi còn thiếu, SKU chưa có liên kết bao bì chính | Danh sách việc phải hoàn tất trước kỳ tiếp theo; không tự coi Nháp là hiệu lực |
| Hằng tháng hoặc trước khi đổi chính sách | Giá mua/rate/phí/thuế/FX cũ và mới; cơ sở công suất kỳ; một ví dụ tính tay | Hai kỳ nối đúng quy ước ngày của module; số liệu mới có căn cứ và đối soát |
| Sau thay đổi cấu hình | Test Formula, kiểm tra Scheme, một Run/Scenario đào tạo và diễn giải nguồn | Cấu hình mới tính đúng kỳ vọng; lịch sử trước thay đổi không bị viết lại |

### Khi nhận dữ liệu mới, làm ở đâu?

| Sự kiện | Thao tác | Điểm cần giữ |
|---|---|---|
| Nhà cung cấp gửi báo giá mới | Giá nhà cung cấp → thêm dòng có giá/đơn vị/tiền/ngày/tham chiếu mới | Lưu Nháp chưa đủ cho Costing; nguồn hiệu lực phải được chuẩn bị qua quy trình hiện có ngoài UI. Không ghi đè dòng cũ chỉ để lưu giá kỳ mới |
| Đơn giá máy hoặc nhân công đổi | Đơn giá nguồn lực → thêm bản theo ngày | Một rate phù hợp cho Resource/ngày; loại STANDARD/ACTUAL không tự giải quyết nguồn trùng |
| Định mức, bao bì hoặc thời gian sản xuất đổi | Tạo phiên bản mới ở module tương ứng, sửa thành phần/công đoạn, đối chiếu | Bản mới Nháp; không có nút phát hành upstream hoàn chỉnh. Giữ bản cũ và kiểm tra khoảng hiệu lực trước Run |
| Tỷ giá đổi | Tỷ giá → thêm nguồn đúng chiều/loại/thời điểm; kết thúc kỳ cũ nếu đủ điều kiện | Pricing xét tại 00:00 ngày định giá. Bản mới và bản cũ không cùng phù hợp; không tự đảo tỷ giá |
| Phí kênh hoặc thuế đổi | Nếu bản cũ EFFECTIVE chưa có end, dùng Kết thúc hiệu lực khi mốc mới còn trong tương lai; thêm quy tắc mới | Bản cũ kết thúc tại đúng ngày bắt đầu bản mới theo khoảng [start,end). Bản đã có end không đóng lại hoặc sửa lùi ngày qua UI |
| Muốn nhìn tác động của mọi thay đổi | Run: Tạo lần tính mới; Pricing: Nhân bản thành kịch bản mới rồi Tính giá bán | Pricing dùng Run đã chọn, không tự lấy giá vốn mới chỉ vì phí/thuế/FX đổi |

Nếu thiếu thao tác đưa nguồn vào hiệu lực hoặc đóng kỳ phù hợp, dừng tại giới hạn đã ghi ở [GAP_REGISTER](GAP_REGISTER.md). Không sửa trạng thái hay snapshot trực tiếp để làm kết quả mới khớp kỳ vọng.

Nguồn: các chương 04–07 và [Tham chiếu trường](12_FIELD_REFERENCE.md) dẫn form/service/selector/engine tương ứng. FAQ không bổ sung quy tắc ngoài source; khi đụng giới hạn, dùng [ma trận 14](14_BUSINESS_CAPABILITY_MATRIX.md) thay vì cố nhập mã chưa có resolver.
