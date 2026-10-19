# Ma trận khả năng nghiệp vụ

Đối chiếu source ngày 09/10/2026. `[HỆ THỐNG HIỆN TẠI]` mô tả khả năng hiện có; ví dụ ở cột Business Example là `[VÍ DỤ NGHIỆP VỤ]` nếu không ghi `[DEMO]`. Đây là đánh giá khả năng phần mềm, không xác nhận rằng mọi cấu hình minh họa đã có dữ liệu hoặc đã chạy thử.

| Support Level | Cách hiểu |
|---|---|
| NATIVE | Có màn hình/thao tác hoặc bộ máy thực thi trực tiếp cho khả năng được nêu; vẫn cần dữ liệu hợp lệ |
| CONFIGURABLE | Có thể mô hình hóa bằng các phần tử, input, công thức, phương án hoặc quy tắc đã hỗ trợ; cần người dùng thiết kế và kiểm thử |
| PARTIAL | Có một phần dữ liệu/thao tác, còn thiếu bước hoặc bộ máy để hoàn thành toàn bộ nhu cầu |
| NOT SUPPORTED | Chưa có thao tác/bộ máy thực hiện nhu cầu được nêu; lưu được mã/metadata không thay đổi kết luận này |

Đọc từng dòng theo đúng phạm vi của nó. Ví dụ quản lý giá mua là NATIVE, nhưng tự chọn giá rẻ nhất và Costing mua bằng ngoại tệ chưa được hỗ trợ. Một khoản tổng tiền nhập tay là CONFIGURABLE, còn quản lý chuyến giao hàng/phân bổ cước không vì vậy thành khả năng có sẵn.

## 1. Danh mục, sản xuất và nền giá vốn

| Capability | Business Example | System Module | Support Level | Configuration Required | Current Limitation |
|---|---|---|---|---|---|
| Từ điển phần tử chi phí | Nguyên liệu, điện, cước vật tư | Phần tử chi phí | NATIVE | Mã/loại giá trị/tiền tệ/đơn vị/phạm vi/làm tròn | Tạo phần tử không tự tạo nguồn hoặc phép tính |
| Product và nhiều SKU | Một công thức cà phê, nhiều quy cách hộp | Sản phẩm, SKU | NATIVE | Product; đơn vị bán; lượng tịnh và đơn vị lượng tịnh | Không tự tạo BOM, bao bì, Item hoặc gán phương án |
| Nguyên liệu, bao bì, hàng hóa mua bán | Cà phê, đường, sachet, hàng thương mại | Vật tư / Hàng hóa | NATIVE | Item type và đơn vị cơ sở | Không có nhập/xuất/tồn hoặc tự tạo giá mua |
| Danh mục nhiều tiền tệ/đơn vị | VND, USD; kg, g, phút, giờ | Tiền tệ, Nhóm đơn vị tính, Đơn vị tính | NATIVE | Danh mục và đại lượng đúng | Danh mục không tự tạo FX/quy đổi |
| Quy đổi lượng trực tiếp/nghịch đảo theo ngày | 200g thành0,2kg; phút thành giờ | Quy đổi đơn vị tính, Costing | NATIVE | Đúng một cặp hiệu lực, factor, Item nếu cần | Không nối chuỗi hoặc tự ưu tiên quy đổi riêng hơn chung |
| Giá mua theo ngày/ngưỡng lượng | Giá cà phê tháng10 và tháng11 | Giá nhà cung cấp | NATIVE | Supplier/Item/đơn vị giá/tiền tệ/min_qty/ngày | Không version table; sửa ghi đè row nguồn; overlap chưa chặn lúc nhập |
| Nguồn báo giá mới dùng ngay hoàn toàn qua UI | Lưu Nháp rồi đưa vào nguồn tính | Giá nhà cung cấp | PARTIAL | Nguồn hợp lệ EFFECTIVE | UI chưa có thao tác chuyển EFFECTIVE |
| Chọn nhà cung cấp/bậc giá tối ưu | Rẻ nhất hoặc bậc cao nhất trong nhiều giá | Costing price resolver | NOT SUPPORTED | — | Cần đúng một giá đủ điều kiện; nhiều giá gây AMBIGUOUS_PRICE |
| BOM có thu hồi và hao hụt | Điều chỉnh lượng dùng do yield/scrap | BOM / Công thức sản xuất, MATERIAL_COST | NATIVE | Product/BOM phiên bản hiệu lực/lines/giá/quy đổi | Lượng=`qty×scale/yield/(1−scrap)`; không actual-consumption |
| Sản xuất Cappuccino mẫu | [DEMO]10hộp tổng583.000VND | BOM, Bao bì, Routing, Formula, Costing | NATIVE | Nguồn DEMO hiệu lực đã chuẩn bị; Run10Hộp/VND/07-10-2026/cơ sở bao bì1Hộp | Golden cho phạm vi VND hỗ trợ; không xác nhận mọi ngành đã UAT |
| Bao bì theo SKU và ngày | 20sachet+1hộp trên cơ sở1hộp | Cấu hình bao bì, gán SKU, PACKAGING_COST | NATIVE | Assignment chính duy nhất, version hiệu lực; cơ sở nhập trên Run | Không suy ra output basis từ cấu hình |
| Cây bao bì tự mở rộng | Sachet→hộp→thùng→pallet | Cấu hình bao bì | PARTIAL | Nhập sẵn lượng dòng trên một cơ sở rõ ràng | Cấp/cha/units_per_parent được lưu; không tự nhân cây |
| Chọn bao bì thị trường/mẫu in | Hộp nội địa khác hộp xuất khẩu | Bao bì | PARTIAL | Có metadata market/artwork | Run chưa có bộ chọn; dòng có điều kiện bị chặn |
| BOM nhiều cấp/bán thành phẩm | Giá thành bột nền tự chuyển sang thành phẩm | Item/BOM | PARTIAL | Có Item SEMI_FINISHED và dòng BOM | Không recursive roll-up; chỉ định Item không tự lấy giá thành Product khác |
| Nguyên liệu tùy chọn/thay thế | Chọn nhà cung cấp A hoặc vật tư B | BOM | PARTIAL | Lưu optional/substitute_group | Engine chặn vì chưa có quy tắc chọn thành phần |
| BOM/quy trình riêng từng SKU cùng Product | Cùng Product nhưng công thức khác quy cách | BOM, Quy trình sản xuất | PARTIAL | Header hiện gắn Product | Lọc SKU chỉ tìm Product tương ứng; không có assignment BOM/Routing→SKU |
| Thời gian máy/nhân công chuẩn | Setup một lần + thời gian theo sản lượng | Routing, Nguồn lực, RESOURCE_COST | NATIVE | Operation/timeUoM/primary resource/basis hoặc batch/rate | Một nguồn lực chính mỗi công đoạn; không tự chọn rate_type |
| Máy và lao động đồng thời trong một công đoạn | Hai nguồn lực cho cùng bước đóng gói | Routing | PARTIAL | Có thể mô hình công đoạn riêng nếu đúng thực tế | Không OperationResource nhiều nguồn lực; không tự chia chung thời gian |
| Nhiều loại tariff nguồn lực cùng ngày | Ca ngày/ca đêm hoặc STANDARD/ACTUAL | Đơn giá nguồn lực | PARTIAL | rate_type text được lưu | Run không có lựa chọn loại rate; nhiều rate hiệu lực bị chặn |
| Phân bổ chi phí theo công suất bình thường | [DEMO]530.000VND/100hộp | CostPool, AllocationRule, CostPoolPeriod | NATIVE | NORMAL_CAPACITY, kỳ EFFECTIVE, tiền/đơn vị/công suất dương; usage≤capacity | Số liệu kỳ phải được chuẩn bị; không UI nhập kỳ |
| Nhập số liệu kỳ chi phí chung | Tiền điện/tháng và công suất kỳ | CostPoolPeriod | PARTIAL | Model và engine đã có | Chưa có UI/service nhập kỳ cho người vận hành |
| Phân bổ theo giờ máy/giờ công/kg/chuyến/pallet-ngày | Activity-based costing | Quy tắc phân bổ | PARTIAL | Các mã cơ sở có thể lưu | Chỉ NORMAL_CAPACITY có execution; chưa có dữ liệu mẫu số/hợp đồng các driver khác |
| Tự gom phần tử thành nhóm chi phí | Cộng điện+khấu hao+lương vào pool | CostPool | NOT SUPPORTED | — | Không CostPoolMember hoặc liên kết pool→CE để tự gom |
| Tổng tiền chi phí bổ sung được xác định trước | Điện hoặc phí gia công cho đúng Run | CE+MANUAL+Formula+Scheme | CONFIGURABLE | MONEY/cùng tiền/không UoM; MANUAL; formula có test; OUTPUT MANUFACTURING | Người dùng tự tính và kiểm soát căn cứ, phạm vi, tránh cộng lặp |
| Hàng thương mại không tự sản xuất | Quản lý danh mục/giá mua và chính sách bán | Item/SupplierPrice/Channel/Pricing | PARTIAL | Pricing cần Run LOCKED hợp lệ đã có; danh mục không tự tạo nguồn giá vốn | Chưa có engine hoặc adapter giá vốn thương mại/nhập kho riêng; không đổi scope giả thành MANUFACTURING để tạo Run |
| Giá vốn mua tự động có landed cost | Hàng nhập khẩu gồm mua+cước+thuế hải quan | Costing LANDED | NOT SUPPORTED | — | Row scope LANDED bị Run chặn; Costing FX/thuế mua chưa có |
| Actual costing/variance | Tiêu hao thực tế khác định mức | Costing Run | NOT SUPPORTED | — | UI chỉ STANDARD/PLANNED cùng execution chuẩn; không actual consumption/variance |
| Tính hàng loạt nhiều SKU | Roll-up toàn danh mục theo kỳ | Costing | NOT SUPPORTED | — | Chạy đồng bộ một Run; không queue/bulk progress |

## 2. Kênh bán, giá bán và xuất khẩu

| Capability | Business Example | System Module | Support Level | Configuration Required | Current Limitation |
|---|---|---|---|---|---|
| Giá bán trực tiếp | Bán trực tiếp không thu phí kênh | Kênh bán, Kịch bản giá bán | NATIVE | Base Run LOCKED, channel, mục tiêu, thuế chọn rõ | Không có phí phù hợp thì cảnh báo và phí0; không đồng nghĩa tự miễn thuế |
| Giá đại lý/nhà phân phối | Kênh đại lý có margin/markup khác | Channel, Scenario | NATIVE | Kênh và các scenario riêng trên cùng giá vốn | Không danh mục từng khách hàng/hợp đồng hạn mức công nợ |
| Cộng tỷ lệ trên giá vốn | Cost-plus theo markup20% | Scenario MARKUP | NATIVE | Run có giá vốn>0, target_markup nhập20 | Markup khác margin; phí/thuế vẫn ảnh hưởng giá cần đạt |
| Giá theo biên lợi nhuận mục tiêu | Lợi nhuận20%giá khách trả | Scenario MARGIN | NATIVE | target_margin nhập20; phí/thuế khả thi | Margin=lợi nhuận/giá khách trả, không phải doanh thu thuần |
| Giá theo lợi nhuận đơn vị | Lãi10.000VND trên mỗi hộp | PROFIT_PER_UNIT | NATIVE | Target tiền theo currency Scenario, một đơn vị output Run | Không phân bổ theo đơn hàng/nhiều SKU |
| Giá sàn cho Scenario | Ít nhất80.000VND/hộp | Scenario.minimum_price | NATIVE | Giá tối thiểu≥0 | Giá sàn có thể làm actual margin/markup cao hơn mục tiêu |
| Phí thương mại điện tử/marketplace | Hoa hồng%+phí cố định+sàn/trần | ChannelFeeRule, Pricing engine | NATIVE | Fee EFFECTIVE, LIST_PRICE, phí đã gồm thuế, refund0; scope/priority | Fixed theo một đơn vị output Costing, không theo đơn hàng; không API nền tảng |
| Phí theo SKU/nhóm/chung | Cùng fee_type chọn phí SKU thay phí chung | Fee selector | NATIVE | Scope SKU>category>general rồi priorityDESC | Hòa cùng hạng bị chặn; khác fee_type cộng nhau; không áp policy này cho giá mua/rate |
| Chiết khấu thương mại/khuyến mại tổng quát | Mã giảm giá, mua X tặng Y | Pricing | PARTIAL | Có thể tạo scenario mục tiêu khác hoặc fee hợp lệ cho khoản thật sự là phí | Không coupon/promotion engine, không hỗ trợ fee âm để giả giảm giá |
| Giá theo ngưỡng số lượng đơn bán | Giá10thùng khác100thùng tự chọn | Pricing | NOT SUPPORTED | — | Không quantity-tier selector cho Scenario; phải lập cấu hình/mục tiêu riêng thủ công |
| Thuế bán hàng tỷ lệ/cố định | Thuế phù hợp khu vực/nhóm hàng/giao dịch | TaxRule, Scenario | NATIVE | Tax mode REQUIRED, rule EFFECTIVE; SELLING_PRICE/LIST_PRICE; recovery0 | Thuế trên cơ sở trước thuế chung; không tự tư vấn mức thuế pháp lý |
| Bỏ thuế bán hàng có chủ đích | Kịch bản thuộc trường hợp không áp thuế đã xác định | Scenario tax_mode NONE | NATIVE | Người lập chọn rõ NONE | Có cảnh báo; không fallback NONE khi thiếu TaxRule |
| Thuế inclusive hoặc exclusive | Giá niêm yết đã gồm hoặc chưa gồm thuế | TaxRule.inclusive | NATIVE | Toàn bộ thuế được chọn cùng kiểu inclusion | Không hỗ trợ trộn inclusive/exclusive trong một giá niêm yết |
| Thuế chồng thuế/thuế trên phí/hoàn thuế | Thuế A làm cơ sở thuế B | Pricing | NOT SUPPORTED | — | Các thuế chạy song song trên cơ sở chung; recovery/refund/fee tax chưa đủ contract |
| Bán ngoại tệ/nhạy FX | Giá vốn VND, bán USD | FX+Scenario | NATIVE | Tỷ giá direct VND→USD, đúng rate_type, hiệu lực0hngày định giá | Không tự nghịch đảo/nối chuỗi/API hoặc lấy tỷ giá hiện tại cho lịch sử |
| Định giá xuất khẩu đơn giản | Bán USD theo margin và thuế cấu hình rõ | Channel+FX+Scenario | CONFIGURABLE | Run LOCKED; currency USD; direct FX; fee/tax phù hợp | Chỉ phần định giá; không tạo chứng từ xuất khẩu/Incoterm/customs/landed cost |
| Tính toàn bộ giá xuất khẩu theo Incoterm | EXW/FOB/CIF cùng cước, bảo hiểm, hải quan | Logistics/export costing | NOT SUPPORTED | — | Không Incoterm selector hoặc engine landed/cost-to-serve |
| So sánh trực tiếp/đại lý/marketplace | Đối chiếu2–5kịch bản cùng SKU | So sánh kịch bản | NATIVE | Scenario CALCULATED, snapshot/hash hợp lệ, cùng output basis | Khác currency hiển thị riêng, không trừ tiền/quy đổi lại; không xuất chart/file |
| So sánh khác SKU | Hộp20gói với túi500g | So sánh kịch bản | NOT SUPPORTED | — | Cần cùng SKU, hoặc cùng Product khi mọi scenario không SKU; không tự chuẩn hóa khác quy cách |

## 3. Vận chuyển, kho và khoản khác

| Capability | Business Example | System Module | Support Level | Configuration Required | Current Limitation |
|---|---|---|---|---|---|
| Nhập tổng cước thuộc chi phí sản xuất đã xác định | Vận chuyển vật tư20.000VND cho một Run | CE MONEY+MANUAL+Formula | CONFIGURABLE | Tổng tiền/cùng currency; phân loại MANUFACTURING phù hợp; formula test+scheme mới | Không phải landed/cost-to-serve; không tự tìm giá cước hoặc phân bổ chuyến |
| Công thức tiền×số thường | Tổng phí theo hệ số số thường đã quy ước | Formula | CONFIGURABLE | Một biến MONEY và scalar NUMBER/PERCENT; quy ước đơn vị ở tên/mô tả | Không kiểm chứng tấn/km trong scalar; không hỗ trợ MONEY×QUANTITY có đơn vị |
| Quản lý hãng vận chuyển/tuyến/tariff | Chọn xe, tuyến, nhà vận chuyển | Logistics | NOT SUPPORTED | — | Không màn hình/model nghiệp vụ giao nhận hoặc bộ chọn cước |
| Tự tính khối lượng/thể tích tính cước | Max khối lượng thực/khối lượng quy đổi | Freight engine | NOT SUPPORTED | — | Item/bao bì có số đo nhưng không tự tạo chargeable weight/CBM pricing |
| Phân bổ cước một chuyến cho nhiều SKU | Theo kg/thể tích/giá trị đơn hàng | Allocation/Logistics | NOT SUPPORTED | — | Chưa có shipment dataset/mẫu số; không lấy denominator từ một Run |
| Ghi nhận kho bãi, handling, bốc xếp đã tính sẵn | Tổng tiền kho thuộc đúng phạm vi sản xuất | MANUAL+Formula | CONFIGURABLE | Tổng MONEY/căn cứ rõ/phân loại hợp lệ/không cộng lặp | Không quản lý giao dịch kho, ngày lưu, pallet hoặc cost-to-serve riêng |
| Tính kho theo pallet-ngày, handling theo chuyến | 5pallet×10ngày×tariff | Warehouse/Allocation | NOT SUPPORTED | — | PALLET_DAY/SHIPMENT lưu được trong allocation nhưng chưa execution |
| Tính hải quan/thuế nhập khẩu tự động | Giá CIF×thuế suất, phí thông quan | Customs/landed costing | NOT SUPPORTED | — | Không dữ liệu tờ khai/cơ sở hải quan/contract thuế mua/landed |
| Nhập khoản bảo hiểm/chi phí khác đã xác định | Tổng phí có căn cứ cho kịch bản chi phí phù hợp | MANUAL+Formula | CONFIGURABLE | Chỉ hợp lệ khi thuộc MANUFACTURING hiện hỗ trợ; kế toán tự xác định tổng/cơ sở | Không tạo bảo hiểm hàng hóa hoặc biến hệ thống thành engine CIF; các khoản ngoài phạm vi chưa thực thi |
| Theo dõi dịch vụ vận chuyển/kho là ngành kinh doanh | Cost-to-serve từng khách/chuyến | Costing COST_TO_SERVE | NOT SUPPORTED | — | Scope lưu trong metadata nhưng Run chặn; không dịch vụ/chuyến/khách dataset |
| Khấu hao thiết bị/lương/chấm công tự tính | Tính khấu hao máy tháng và payroll | Nguồn lực | NOT SUPPORTED | — | Resource/Rate chỉ lưu nguồn lực và đơn giá; tổng tiền/rate tính trước có thể dùng nếu đúng nghiệp vụ |

## 4. Kiểm soát cấu hình và lịch sử

| Capability | Business Example | System Module | Support Level | Configuration Required | Current Limitation |
|---|---|---|---|---|---|
| Formula/phiên bản/test/activate | Thay công thức có kiểm thử đạt | Thiết lập công thức | NATIVE | TypedCE/biểu thức/ngày/≥1testallpass | Preview phụ thuộc newest khác dated execution; không LOOKUP/EXTERNAL |
| Scheme/clone/validate/activate | Phương án chuẩn và phương án có input khác | Phương án tính giá thành | NATIVE | Dòng nguồn đủ/đúng types/no cycles/date | Không assignmentProduct/SKU; activation không kiểm tra tất cả giá/rate runtime |
| Hoàn thành nguồn sản xuất mới chỉ bằng UI | Nháp BOM→hiệu lực→Run | Manufacturing lifecycle | PARTIAL | Nguồn EFFECTIVE được chuẩn bị | Thiếu thao tác kích hoạt upstream và UI nhập CostPoolPeriod |
| Input nhập tay có kiểu/giới hạn | Tổng phí đã xác định cho từng Run | Scheme MANUAL, RunForm | NATIVE | Dòng MANUAL/min/max nếu có | Mỗi dòng bắt buộc kể cả editableFalse; không sửa SYSTEM sau tính |
| Sửa đè kết quả Run/Scenario đã chốt | Điều chỉnh thủ công sau khi xem kết quả | Overrides | NOT SUPPORTED | — | Run tạo mới; Scenario nhân bản mới; metadata override không có workflow thực thi |
| Lưu nguồn/giá/biểu thức/diễn giải lịch sử | Xem giá vốn cũ sau khi giá mua đổi | Snapshot/Trace | NATIVE | Run LOCKED hoặc Scenario CALCULATED | Xem dữ liệu đã lưu; chưa replay ngoại tuyến snapshot |
| Chạy lại với dữ liệu hiện tại | Tính lại ngày cũ sau sửa nguồn | Run rerun | NATIVE | Form mới, nguồn hợp lệ tại ngày được chọn | Tạo record mới và resolve nguồn hiện tại, không đổi Run gốc |
| Tự tái tính Scenario khi phí/FX đổi | Scenario cũ cập nhật theo giá mới | Pricing history | NOT SUPPORTED | — | CALCULATED giữ snapshot; nhân bản để tính nguồn mới |
| Đóng kỳ Pricing tương lai | Phí cũ hết trước kỳ mới | Pricing Kết thúc hiệu lực | NATIVE | Bản EFFECTIVE chưa có end; end trong tương lai và sau start | Chỉ đổi end; không sửa amount/scope/quá khứ; không áp cho versionCosting |
| Ngăn overlap mọi nguồn ngay khi nhập | Không bao giờ có hai nguồn hiệu lực | Upstream CRUD/Selectors | PARTIAL | Người vận hành kiểm tra ngày/scope | Nhiều CRUD cho lưu; Costing fail khi mơ hồ, Pricing có ranking riêng nhưng tie vẫn lỗi |
| Xem nhật ký thao tác nhân sự/duyệt | Ai sửa/ai duyệt trước sau | Business Audit/Approval | NOT SUPPORTED | — | Đã bỏ khỏi runtime; version/history/trace vẫn còn |

## 5. Nguồn và cách áp dụng ma trận

Các nhóm NATIVE ở đây được xác nhận từ route/form/service và engine hiện tại, không suy ra từ tên cột trong DB. Các nhóm CONFIGURABLE cần kiểm thử nghiệp vụ trước sử dụng. Những thiếu hụt và đề xuất được ghi ở [GAP_REGISTER](GAP_REGISTER.md); thao tác ở [chương06](06_HUONG_DAN_FORMULA_VA_COSTING.md), [chương07](07_HUONG_DAN_PRICING.md); ví dụ thực tế ở [chương08](08_KICH_BAN_THUC_TE.md).

Nguồn: [core models](../../apps/core/models.py), [danh mục](../../apps/master_data/forms.py), [sản phẩm](../../apps/product/forms.py), [sản xuất](../../apps/bom/routing_forms.py), [Costing registry](../../apps/costing/engine/registry.py), [Costing runner](../../apps/costing/engine/runner.py), [manufacturing resolver](../../apps/costing/engine/resolvers/manufacturing.py), [phân bổ](../../apps/costing/engine/resolvers/allocation.py), [Pricing forms](../../apps/pricing/scenario_forms.py), [Pricing resolver](../../apps/pricing/engine/resolvers.py), [Pricing solver](../../apps/pricing/engine/solver.py), [Scenario services](../../apps/pricing/scenario_services.py), [Comparison](../../apps/pricing/comparison.py).
