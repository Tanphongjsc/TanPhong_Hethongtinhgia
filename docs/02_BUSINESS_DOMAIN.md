> **Quyết định hiện tại 08/10/2026:** không Approval/Maker-Checker/business Audit Log.
> Các quy trình duyệt/actor audit nhân sự lịch sử đã superseded; giữ versioning,
> hiệu lực, lịch sử giá/đơn giá, manual inputs, snapshot và explain/technical trace.
> Pricing Foundation quản lý Channel/Fee/Tax/FX; Pricing Scenario hiện tính giá từ
> persisted Costing Run. Margin chia giá khách trả gồm thuế, markup chia giá vốn;
> phí trên giá khách trả, thuế song song trên giá trước thuế chung. Policy chi tiết,
> phạm vi hỗ trợ và ví dụ Golden: [PRICING_SCENARIO.md](PRICING_SCENARIO.md).
> Ví dụ công thức giản lược phía dưới không thay thế contract execution hiện tại.
> Scenario Comparison chỉ đọc 2–5 kết quả đã lưu cùng SKU (hoặc cùng Product không SKU),
> cùng output UoM/cơ sở giá. Delta Decimal, không so tiền khác currency trực tiếp.
> Không tính lại giá hoặc dùng current Fee/Tax/FX. [SCENARIO_COMPARISON.md](SCENARIO_COMPARISON.md).
>
> **Kiến trúc hiện tại 07/10/2026:** single-company, no-auth. Các giả định multi-tenant,
> user role/membership/organization selection bên dưới đã superseded cho runtime
> hiện tại. Organization chỉ còn là DB compatibility layer.
> Xem [SINGLE_COMPANY_NO_AUTH.md](SINGLE_COMPANY_NO_AUTH.md).

**TÀI LIỆU NGHIỆP VỤ CHUYÊN SÂU  
HỆ THỐNG TÍNH GIÁ THÀNH – GIÁ BÁN – LỢI NHUẬN  
**cho cà phê hòa tan, gia vị, cacao hòa tan và nông sản

*Phiên bản nghiệp vụ đề xuất: 1.0 \| Ngày: 17/09/2026*

Mục tiêu của tài liệu là chuyển cách tính giá hiện đang thực hiện bằng nhiều bảng Excel riêng lẻ thành một mô hình nghiệp vụ có cấu trúc, có thể mở rộng cho nhiều sản phẩm, quy cách đóng gói và nhiều kênh bán: bán buôn, bán lẻ, website, Shopee, TikTok Shop, Lazada, xuất khẩu và các kênh khác.

# 1. Tóm tắt điều hành

Qua kiểm tra ba workbook mẫu được cung cấp, cách tính hiện tại đã chứa khá nhiều thành phần quan trọng của một mô hình giá thành thực tế: máy móc/nhà xưởng, khấu hao, nguyên liệu, bao bì, vận chuyển, nhân công, chi phí xuất khẩu và lợi nhuận. Tuy nhiên, các khoản mục đang nằm rải rác theo từng sản phẩm và nhiều công thức được nhập trực tiếp trong ô Excel. Điều này phù hợp để tính nhanh một báo giá nhưng khó mở rộng khi số SKU, quy cách, nhà cung cấp, kênh bán và chính sách phí tăng lên.

Định hướng nên là xây dựng một 'Cost & Pricing Engine' tách thành ba lớp: (1) Giá thành sản xuất; (2) Chi phí đưa sản phẩm tới từng kênh/thị trường; (3) Giá bán và lợi nhuận mục tiêu. Không nên gộp tất cả thành một con số 'giá thành' duy nhất.

| **Lớp**          | **Mục đích**                              | **Đầu ra chính**                                                                           |
|------------------|-------------------------------------------|--------------------------------------------------------------------------------------------|
| 1\. Product Cost | Tính chi phí sản xuất và giá vốn sản phẩm | Giá thành chuẩn, giá thành thực tế, giá/kg, giá/gói, giá/thùng                             |
| 2\. Channel Cost | Tính chi phí theo kênh bán                | Phí sàn, thanh toán, affiliate, đóng gói đơn, logistics, marketing phân bổ, thuế liên quan |
| 3\. Pricing      | Tính giá bán theo mục tiêu                | Giá sàn, giá niêm yết, giá khuyến mại, lợi nhuận/đơn, biên lợi nhuận                       |

# 2. Phạm vi sản phẩm và thị trường

| **Nhóm sản phẩm** | **Ví dụ**                            | **Đặc điểm cần mô hình hóa**                           |
|-------------------|--------------------------------------|--------------------------------------------------------|
| Cà phê hòa tan    | 3in1, Cappuccino, Cappuccino + Choco | BOM nhiều thành phần, nhiều lớp bao bì, nhiều quy cách |
| Gia vị tổng hợp   | Gia vị pha trộn                      | Tỷ lệ phối trộn, hao hụt, nhiều nguyên liệu            |
| Cacao hòa tan     | Cacao 3in1                           | Tương tự cà phê, có thể dùng bán thành phẩm            |
| Nông sản khác     | Hạt, bột, nguyên liệu chế biến       | Có thể mua thành phẩm, sơ chế hoặc sản xuất            |

| **Kênh**  | **Ví dụ**            | **Logic giá cần có**                                                  |
|-----------|----------------------|-----------------------------------------------------------------------|
| Bán buôn  | Đại lý/NPP/khách B2B | Chiết khấu theo sản lượng, MOQ, công nợ, vận chuyển                   |
| Bán lẻ    | Cửa hàng/website     | Giá niêm yết, khuyến mại, giao hàng                                   |
| TMĐT      | Shopee/TikTok/Lazada | Commission, transaction fee, order fee, affiliate, voucher, logistics |
| Xuất khẩu | FOB/CIF/EXW          | Tỷ giá, bao bì xuất khẩu, vận chuyển, chứng từ, phí xuất khẩu         |

# 3. Phân tích các file Excel hiện tại

Các workbook mẫu thể hiện một mô hình tính giá thủ công nhưng có nền tảng tốt. Các sheet chính gồm:

| **Sheet hiện tại**          | **Nghiệp vụ đang thể hiện**                             | **Nhận xét để đưa vào hệ thống**                             |
|-----------------------------|---------------------------------------------------------|--------------------------------------------------------------|
| GIÁ MÁY MÓC NHÀ XƯỞNG       | Giá máy, phụ phí/chi phí liên quan, khấu hao, công suất | Tách thành Tài sản + Work Center + Capacity + Depreciation   |
| GIÁ NGUYÊN LIỆU             | Nhà cung cấp, số lượng, đơn giá, VAT, tổng thanh toán   | Tách Purchase Price, Tax, Freight/Landed Cost và lịch sử giá |
| GIÁ BAO BÌ                  | Trục in, túi, thùng carton, số lượng, đơn giá           | Bao bì phải là vật tư/BOM có quy cách và đơn vị đo chuẩn     |
| GIÁ VẬN CHUYỂN              | Các chuyến vận chuyển và quy đổi về đơn vị kg           | Cần engine phân bổ theo kg/kiện/container/giá trị            |
| GIÁ NHÂN CÔNG               | Công đứng máy, công phụ, đóng gói hoàn thiện            | Nên tính theo Work Center/giờ/công/đơn vị sản phẩm           |
| GIÁ SANCHET / SANCHET+CHOCO | Tổng hợp chi phí thành phần và lợi nhuận                | Nên trở thành Cost Sheet của SKU/packaging version           |
| Quotation Details           | Các phương án đóng gói                                  | Nên chuyển thành Product Variant/Packaging Configuration     |
| CAFE 3 TRON 1               | Giá thành + chi phí + lợi nhuận + tỷ giá + container    | Đây chính là Pricing Scenario, không nên hard-code trong SKU |

# 4. Những vấn đề của mô hình Excel hiện tại cần khắc phục

- Một SKU đang đồng thời chứa thông tin sản phẩm, quy cách, giá nguyên liệu, tỷ giá và chính sách lợi nhuận. Khi một yếu tố thay đổi sẽ khó biết thay đổi ảnh hưởng tới SKU nào.

- Đơn vị đo chưa được chuẩn hóa tuyệt đối: kg, gói, thùng, container, chai/lọ, công đóng gói và đơn vị mua có thể khác nhau.

- VAT đang xuất hiện trong một số công thức mua hàng nhưng chưa tách rõ 'giá trước thuế', 'thuế được khấu trừ' và 'chi phí thực tính vào giá thành'.

- Khấu hao đang tính theo số tháng cố định và sản lượng giả định. Hệ thống mới phải cho phép cấu hình thời gian sử dụng, giá trị khấu hao, công suất bình thường và tiêu thức phân bổ.

- Chi phí vận chuyển đang quy đổi theo một số mốc kg cụ thể. Cần một cơ chế phân bổ tổng quát.

- Lợi nhuận đang được cộng trực tiếp vào giá thành. Cần tách 'cost' và 'margin' để có thể thay đổi mục tiêu lợi nhuận theo từng kênh.

- Phí sàn, affiliate, voucher, phí thanh toán và thuế thương mại điện tử chưa nằm trong mô hình cơ bản.

- Công thức Excel phụ thuộc vào vị trí ô. Hệ thống nên dùng mã nghiệp vụ và rule có hiệu lực theo thời gian.

# 5. Mô hình nghiệp vụ chuẩn đề xuất

Nên phân biệt ít nhất 6 khái niệm:

| **Khái niệm**             | **Ý nghĩa**                                                           |
|---------------------------|-----------------------------------------------------------------------|
| Standard Cost             | Giá thành chuẩn dùng để lập kế hoạch/báo giá                          |
| Actual Manufacturing Cost | Giá thành thực tế sau sản xuất                                        |
| Landed Cost               | Chi phí để đưa nguyên liệu/hàng hóa về địa điểm sử dụng hoặc kho      |
| Channel Cost              | Chi phí phát sinh do kênh bán                                         |
| Full Cost                 | Chi phí sản xuất + chi phí thương mại/khai thác theo phạm vi quản trị |
| Selling Price             | Giá bán sau khi áp dụng margin, discount, tax và chính sách kênh      |

Theo Thông tư 200, chi phí sản xuất được tập hợp theo nguyên liệu trực tiếp, nhân công trực tiếp và chi phí sản xuất chung; chi phí bán hàng và quản lý doanh nghiệp không phải là thành phần của giá gốc thành phẩm. Vì vậy hệ thống cần có 'giá thành sản xuất' riêng với 'full commercial cost' để vừa phục vụ kế toán vừa phục vụ quản trị giá bán.

# 6. Cấu trúc giá thành sản xuất

Công thức quản trị đề xuất:

**Manufacturing Cost = Direct Material + Direct Labor + Manufacturing Overhead + Direct Processing Cost – Cost Recoveries**

- Direct Material: nguyên liệu theo BOM/Recipe.

- Direct Packaging: bao bì trực tiếp theo SKU/quy cách.

- Direct Labor: lao động trực tiếp.

- Machine/Work Center Cost: máy, điện, khấu hao, bảo trì và chi phí vận hành phân bổ.

- Manufacturing Overhead: chi phí sản xuất chung.

- Yield/Scrap: hao hụt, phế liệu, tỷ lệ thu hồi.

- Subcontracting: gia công ngoài nếu có.

Thông tư 200 cũng quy định chi phí sản xuất chung cố định được phân bổ theo công suất bình thường; phần không phân bổ do sản lượng thấp hơn công suất bình thường được xử lý vào chi phí kỳ, thay vì đẩy toàn bộ vào tồn kho. Đây là một quy tắc cần được hệ thống hóa thay vì để người dùng tự điều chỉnh Excel.

# 7. BOM/Recipe và định mức

Mỗi sản phẩm nên có một hoặc nhiều phiên bản BOM có thời gian hiệu lực. Ví dụ Cappuccino + Choco:

| **Cấp** | **Thành phần** | **ĐVT** | **Định mức** | **Ghi chú**       |
|---------|----------------|---------|--------------|-------------------|
| 1       | Cà phê hòa tan | kg      | x            | Nguyên liệu       |
| 1       | Bột kem        | kg      | x            | Nguyên liệu       |
| 1       | Đường          | kg      | x            | Nguyên liệu       |
| 1       | Cacao/Choco    | kg      | x            | Nguyên liệu       |
| 1       | Túi sachet     | cái     | 1            | Bao bì cấp 1      |
| 1       | Gói choco      | cái     | 1            | Bao bì/thành phần |
| 1       | Túi ngoài      | cái     | x            | Bao bì            |
| 1       | Thùng carton   | thùng   | x            | Bao bì vận chuyển |

BOM cần hỗ trợ: hao hụt %, yield %, phụ phẩm/by-product, scrap, phiên bản, quy cách đóng gói và nhiều cấp BOM.

# 8. Landed Cost – giá nhập thực tế của nguyên liệu

Đây là phần nên nâng cấp đáng kể so với Excel hiện tại.

**Landed Cost = Purchase Price + Freight + Insurance + Customs/Duties + Handling + Other Direct Acquisition Cost – Recoverable Tax**

- Giá mua từ nhà cung cấp.

- Cước vận chuyển về kho/nhà máy.

- Bảo hiểm nếu có.

- Thuế nhập khẩu, phí thông quan và chi phí liên quan nếu có.

- Chi phí bốc dỡ/handling trực tiếp.

- VAT được khấu trừ không nên tự động cộng vào cost đối với trường hợp doanh nghiệp được khấu trừ; quy tắc thuế phải là cấu hình.

# 9. Chi phí nhân công và công đoạn sản xuất

| **Đối tượng**      | **Đơn vị cost**          | **Ví dụ**               |
|--------------------|--------------------------|-------------------------|
| Công nhân trộn     | đồng/giờ hoặc đồng/kg    | Theo giờ máy/trộn       |
| Đóng gói           | đồng/gói hoặc đồng/thùng | Dán túi, đóng thùng     |
| Vận hành máy       | đồng/giờ máy             | Gắn với Work Center     |
| QC/kiểm nghiệm     | đồng/lô hoặc %           | Phân bổ theo batch      |
| Vệ sinh/chuyển đổi | đồng/batch               | Phân bổ cho lô sản xuất |

Hệ thống nên cho phép chọn tiêu thức: giờ công, giờ máy, kg sản xuất, số batch, số đơn vị hoặc tỷ lệ doanh thu.

# 10. Khấu hao, công suất và Work Center

Trong file hiện tại, máy đóng gói, hệ thống máy trộn và vít tải được cộng giá trị và chia theo 24 tháng rồi phân bổ theo sản lượng. Mô hình mới nên chuyển thành danh mục tài sản/work center với các trường: nguyên giá, ngày bắt đầu sử dụng, thời gian khấu hao, công suất thiết kế, công suất bình thường, sản lượng thực tế, chi phí bảo trì và tiêu thức phân bổ.

**Machine Cost per Unit = Allocable Machine Cost / Normal Capacity**

# 11. Giá thành theo nhiều quy cách đóng gói

Một công thức sản phẩm có thể sinh ra nhiều SKU:

| **Product**       | **Packaging**  | **Quy cách** | **Đầu ra** |
|-------------------|----------------|--------------|------------|
| Cà phê 3in1       | Sachet         | 18g x 50     | SKU A      |
| Cà phê Cappuccino | Sachet + Choco | 25g + choco  | SKU B      |
| Cà phê Cappuccino | Sachet         | 25g          | SKU C      |
| Cacao             | Sachet         | 20g x 20     | SKU D      |
| Gia vị            | Túi            | 500g         | SKU E      |

Điểm quan trọng: công thức sản phẩm (Recipe) và cấu hình bao bì (Packaging Configuration) nên là hai đối tượng độc lập, sau đó kết hợp thành SKU.

# 12. Từ giá thành sang giá bán

**Commercial Cost = Manufacturing Cost + Channel-specific Costs + Selling/Distribution Costs**

**Required Selling Price = (Fixed Cost per Unit + Target Profit per Unit) / (1 – Variable Cost Rate)**

Không nên đơn giản dùng 'Giá bán = Giá thành + 20%' vì phí kênh có thể tính theo % doanh thu. Nếu phí sàn, affiliate và chiết khấu đều là tỷ lệ trên giá bán, giá bán phải được giải ngược từ mục tiêu lợi nhuận.

# 13. Ma trận chi phí theo kênh bán

| **Khoản chi phí**     | **Bán buôn** | **Bán lẻ** | **TMĐT** | **Xuất khẩu** |
|-----------------------|--------------|------------|----------|---------------|
| Giá thành sản xuất    | Có           | Có         | Có       | Có            |
| Chiết khấu thương mại | Có           | Có         | Có       | Có            |
| Phí sàn               | Không        | Không      | Có       | Không         |
| Phí thanh toán        | Có thể       | Có thể     | Có       | Có thể        |
| Affiliate             | Có thể       | Có thể     | Có       | Có thể        |
| Voucher/khuyến mại    | Có           | Có         | Có       | Có            |
| Fulfillment/logistics | Có           | Có         | Có       | Có            |
| Thuế theo mô hình bán | Có           | Có         | Có       | Có            |
| Tỷ giá                | Có thể       | Không      | Có thể   | Có            |

# 14. Phí sàn thương mại điện tử – thiết kế theo Rule Engine

Phí sàn không nên được lưu như một con số cố định trong SKU. Phải có bảng chính sách phí theo nền tảng, ngành hàng, loại người bán, chương trình, thời gian hiệu lực và cơ sở tính phí.

| **Field**         | **Ví dụ**                                                   |
|-------------------|-------------------------------------------------------------|
| Platform          | Shopee / TikTok Shop / Lazada                               |
| Seller Type       | Marketplace / Mall / Shop thường                            |
| Category          | Food & Beverage / cấp ngành hàng                            |
| Fee Type          | Commission / Transaction / Order / Affiliate                |
| Rate              | x%                                                          |
| Fixed Amount      | x đồng/đơn                                                  |
| Base              | Product price / customer payment / payout / eligible amount |
| Cap/Floor         | Mức trần/sàn nếu có                                         |
| Tax Inclusive     | Yes/No                                                      |
| Effective From/To | Ngày hiệu lực                                               |

Ví dụ cập nhật 2026 cho thấy chính sách phí có thể thay đổi khá nhanh. TikTok Shop công bố phí giao dịch 6% cho đơn tạo từ 09/05/2026 và phí xử lý đơn 3.000 đồng/đơn; phí hoa hồng nền tảng khác nhau theo ngành hàng và loại seller. Shopee cũng có cơ chế phí Affiliate riêng và mức phí được khấu trừ qua đối soát. Do đó hệ thống phải quản lý lịch sử chính sách thay vì hard-code.

# 15. Affiliate, Voucher và khuyến mại

| **Khoản**             | **Cách mô hình hóa**                              |
|-----------------------|---------------------------------------------------|
| Affiliate commission  | % trên base được xác định bởi chương trình        |
| Voucher shop          | Chi phí người bán chịu / giảm doanh thu thực nhận |
| Voucher platform      | Tách phần nền tảng tài trợ và phần seller tài trợ |
| Free shipping subsidy | Phần seller thực chịu                             |
| Flash sale            | Giá bán thực tế trong chương trình                |
| Ads                   | CPC/CPM/CPS hoặc ngân sách phân bổ                |
| KOL/KOC               | Fixed fee + commission nếu có                     |

Nên cho phép tính hai góc nhìn: 'unit economics của đơn hàng' và 'P&L của kênh'. Ads có thể phân bổ theo đơn, doanh thu hoặc chiến dịch.

# 16. Thuế – nguyên tắc thiết kế

Thuế phải được thiết kế thành một module riêng, vì nghĩa vụ thuế phụ thuộc vào loại hình người bán, phương pháp thuế, loại giao dịch và thời điểm pháp lý. Không nên đóng cứng thuế suất vào sản phẩm.

- VAT đầu vào: cần phân biệt được khấu trừ và không khấu trừ.

- VAT đầu ra: theo loại hàng hóa và phương pháp kê khai áp dụng.

- Thuế trên phí dịch vụ nền tảng: phải xử lý theo tình trạng đăng ký thuế và chính sách nền tảng.

- Hộ/cá nhân kinh doanh trên nền tảng: cần hỗ trợ logic khấu trừ/nộp thay theo quy định hiện hành.

- Thuế xuất khẩu/nhập khẩu: cấu hình theo loại hàng, quốc gia và Incoterms nếu có.

- Tất cả tax rules phải có Effective Date và nguồn pháp lý để audit.

Nghị định 117/2025/NĐ-CP có hiệu lực từ 01/07/2025 và quy định quản lý thuế đối với hoạt động kinh doanh trên nền tảng TMĐT/nền tảng số của hộ, cá nhân. Vì vậy module thuế cần được thiết kế để cập nhật chính sách theo thời gian.

# 17. Mô hình dữ liệu cốt lõi cho phần mềm

| **Entity**              | **Vai trò**                    |
|-------------------------|--------------------------------|
| Product                 | Sản phẩm gốc                   |
| SKU                     | Mã bán hàng cụ thể             |
| UOM                     | Đơn vị đo và quy đổi           |
| BOM/Recipe              | Công thức sản xuất             |
| BOM Version             | Phiên bản có hiệu lực          |
| Packaging Configuration | Cấu hình bao bì                |
| Material                | Nguyên liệu/bao bì             |
| Supplier                | Nhà cung cấp                   |
| Purchase Price          | Lịch sử giá mua                |
| Landed Cost Rule        | Quy tắc cộng chi phí nhập      |
| Work Center             | Công đoạn/máy                  |
| Labor Rate              | Đơn giá nhân công              |
| Overhead Pool           | Nhóm chi phí chung             |
| Cost Allocation Rule    | Quy tắc phân bổ                |
| Channel                 | Kênh bán                       |
| Channel Fee Rule        | Quy tắc phí kênh               |
| Tax Rule                | Quy tắc thuế                   |
| Price List              | Bảng giá                       |
| Promotion               | Khuyến mại                     |
| Pricing Scenario        | Kịch bản tính giá              |
| Cost Snapshot           | Kết quả tính giá tại thời điểm |
| Actual Cost             | Giá thành thực tế              |

# 18. Kiến trúc Pricing Scenario

Người dùng không sửa công thức trong SKU. Người dùng tạo một Scenario:

| **Thông tin**          | **Ví dụ**              |
|------------------------|------------------------|
| Product/SKU            | Cappuccino 25g + Choco |
| Cost Date              | 17/09/2026             |
| Material Price Version | Giá mua tháng 09/2026  |
| BOM Version            | BOM-2026-09            |
| Channel                | TikTok Shop            |
| Seller Type            | Marketplace            |
| Promotion              | Affiliate 10%          |
| Tax Profile            | Doanh nghiệp           |
| Target Margin          | 15%                    |
| Currency               | VND                    |

Kết quả Scenario phải lưu thành snapshot để báo giá đã phát hành không bị thay đổi khi giá nguyên liệu hoặc phí sàn thay đổi.

# 19. Ví dụ công thức tính giá online

Giả sử:

| **Thành phần**      | **Giá trị minh họa** |
|---------------------|----------------------|
| Manufacturing cost  | 30.000 đ             |
| Fulfillment cố định | 3.000 đ/đơn          |
| Commission          | 12% doanh thu        |
| Transaction fee     | 6% doanh thu         |
| Affiliate           | 5% doanh thu         |
| Other variable cost | 2% doanh thu         |
| Target profit       | 10.000 đ/đơn         |

Tổng tỷ lệ biến phí = 25%. Khi đó giá bán tối thiểu theo mô hình đơn giản:

**P = (30.000 + 3.000 + 10.000) / (1 – 0,25) = 57.333 đ**

Con số trên chỉ là ví dụ nghiệp vụ; hệ thống thực tế phải tính thêm voucher, VAT, phần seller chịu của logistics, chi phí đóng gói đơn, hoàn hàng và các quy tắc cụ thể của từng nền tảng.

# 20. Giá bán nhiều tầng

| **Tầng giá**       | **Công thức/logic**                              |
|--------------------|--------------------------------------------------|
| Cost floor         | Không thấp hơn chi phí cần thiết theo chính sách |
| Wholesale price    | Cost + margin B2B – discount theo volume         |
| Retail price       | Cost + channel cost + target margin              |
| Online list price  | Giá niêm yết trước voucher                       |
| Campaign price     | Giá trong chương trình                           |
| Net realized price | Doanh thu thực nhận sau seller-funded deductions |
| Export price       | Theo Incoterm + logistics + FX + target margin   |

# 21. Phương pháp tính giá thành thực tế

Phần mềm nên hỗ trợ ít nhất: giản đơn, hệ số/tỷ lệ, phân bước và theo đơn hàng/lô khi nghiệp vụ thực tế yêu cầu. MISA hiện cũng hỗ trợ các nhóm phương pháp này, trong khi FAST cung cấp các báo cáo tập hợp/phân bổ chi phí, thẻ giá thành và so sánh định mức với thực tế. Đây là những điểm tham chiếu hữu ích để thiết kế nghiệp vụ.

| **Phương pháp** | **Khi dùng**                                              |
|-----------------|-----------------------------------------------------------|
| Giản đơn        | Một dòng sản phẩm hoặc xác định rõ chi phí theo sản phẩm  |
| Hệ số/tỷ lệ     | Nhiều sản phẩm cùng quy trình, khó tách chi phí trực tiếp |
| Phân bước       | Bán thành phẩm giai đoạn 1 trở thành đầu vào giai đoạn 2  |
| Đơn hàng/lô     | Sản xuất theo đơn hàng hoặc batch riêng                   |

# 22. Định mức – thực tế – chênh lệch

Một chức năng rất quan trọng là Variance Analysis:

| **Chênh lệch**             | **Ý nghĩa**                          |
|----------------------------|--------------------------------------|
| Material Price Variance    | Giá mua thực tế khác giá chuẩn       |
| Material Usage Variance    | Tiêu hao thực tế khác BOM            |
| Labor Rate Variance        | Đơn giá lao động khác chuẩn          |
| Labor Efficiency Variance  | Thời gian thực tế khác định mức      |
| Overhead Spending Variance | Chi phí chung thực tế khác ngân sách |
| Yield Variance             | Sản lượng thu hồi khác định mức      |
| Channel Fee Variance       | Phí thực tế khác rule/giả định       |
| Margin Variance            | Biên lợi nhuận thực tế khác mục tiêu |

# 23. Báo cáo quản trị cần có

- Cost Sheet theo SKU.

- Cost breakdown theo nguyên liệu/bao bì/nhân công/overhead.

- Bảng giá thành định mức.

- Bảng giá thành thực tế.

- So sánh định mức – thực tế.

- Giá thành theo kg/gói/thùng/container.

- Landed cost theo lô nhập.

- Unit economics theo kênh.

- Lợi nhuận theo SKU × Channel.

- Lợi nhuận theo đơn hàng.

- Chi phí sàn theo nền tảng.

- Chi phí affiliate theo chiến dịch.

- P&L theo kênh bán.

- Price waterfall: List Price → Discount → Platform Fee → Affiliate → Logistics → Tax → Net Revenue → Cost → Profit.

- Báo cáo lịch sử thay đổi giá và rule.

# 24. Price Waterfall – báo cáo quan trọng nhất cho TMĐT

| **Bước**                | **Giá trị**                     |
|-------------------------|---------------------------------|
| List Price              | Giá niêm yết                    |
| – Seller Discount       | Voucher/discount người bán chịu |
| – Platform Commission   | Hoa hồng nền tảng               |
| – Transaction Fee       | Phí thanh toán/giao dịch        |
| – Affiliate             | Hoa hồng affiliate              |
| – Order/Fulfillment Fee | Phí cố định theo đơn            |
| – Seller Logistics      | Phần vận chuyển người bán chịu  |
| – Other Channel Costs   | Chi phí kênh khác               |
| = Net Revenue           | Doanh thu thực nhận quản trị    |
| – Manufacturing Cost    | Giá thành sản xuất              |
| – Other Variable Cost   | Chi phí biến đổi khác           |
| = Contribution Profit   | Lợi nhuận đóng góp              |

# 25. Quy trình nghiệp vụ end-to-end

1.  Khai báo danh mục sản phẩm, SKU và đơn vị đo.

2.  Khai báo nguyên liệu, bao bì, nhà cung cấp và lịch sử giá mua.

3.  Khai báo BOM/Recipe và phiên bản.

4.  Khai báo máy móc, Work Center, nhân công và chi phí sản xuất chung.

5.  Khai báo công suất bình thường và quy tắc phân bổ.

6.  Tính Standard Cost.

7.  Ghi nhận sản xuất thực tế và Actual Cost.

8.  Khai báo kênh bán và fee rules.

9.  Khai báo tax rules.

10. Tạo Pricing Scenario.

11. Tính giá bán mục tiêu theo margin hoặc lợi nhuận/đơn.

12. Phê duyệt và khóa Price Snapshot.

13. Theo dõi thực tế bán hàng và phân tích variance.

# 26. Quy tắc thiết kế phần mềm

- Không hard-code tỷ lệ phí vào sản phẩm.

- Mọi tỷ lệ phải có ngày hiệu lực.

- Mọi giá phải có currency và UOM.

- Mọi BOM phải có version.

- Mọi giá mua phải có nguồn và thời điểm.

- Mọi pricing scenario phải có snapshot.

- Tách cost accounting khỏi commercial pricing.

- Cho phép một SKU có nhiều price list theo kênh.

- Cho phép nhiều công thức tính giá trên cùng dữ liệu.

- Có audit log cho thay đổi BOM, cost và fee rule.

- Có quyền phê duyệt giá.

- Có API/import Excel để nhập dữ liệu lớn.

# 27. Gợi ý kiến trúc hệ thống

| **Module**         | **Chức năng**                                  |
|--------------------|------------------------------------------------|
| Master Data        | Product, SKU, UOM, Supplier, Customer, Channel |
| Recipe/BOM         | Công thức, định mức, phiên bản                 |
| Purchasing Cost    | Giá mua, landed cost                           |
| Manufacturing Cost | Labor, machine, overhead, actual production    |
| Cost Engine        | Tính standard/actual cost                      |
| Channel Engine     | Fee/commission/affiliate/logistics             |
| Tax Engine         | VAT/withholding/other tax rules                |
| Pricing Engine     | Tính giá theo margin/profit target             |
| Promotion          | Voucher, campaign, discount                    |
| Quotation          | Báo giá B2B/B2C/export                         |
| Analytics          | P&L, unit economics, variance                  |
| Audit & Approval   | Phê duyệt và lịch sử                           |

# 28. So sánh với các phần mềm tham chiếu

| **Hệ thống tham chiếu** | **Điểm nên học hỏi**                                                                       |
|-------------------------|--------------------------------------------------------------------------------------------|
| MISA AMIS               | Định mức theo BOM, giá thành định mức, nhiều phương pháp tính giá thành, báo cáo đối chiếu |
| FAST Accounting         | Tập hợp/phân bổ chi phí, thẻ giá thành, báo cáo định mức và thực tế                        |
| Odoo Manufacturing      | Tách planned/MO cost và real cost; cost theo BOM, operation, work center                   |

MISA mô tả giá thành định mức theo BOM hoặc nhập trực tiếp và cho phép khai báo chi phí nhân công/chi phí sản xuất chung; FAST cung cấp các báo cáo đối chiếu và so sánh nguyên vật liệu định mức – thực tế; Odoo phân biệt chi phí dự kiến của lệnh sản xuất với chi phí thực tế và tính đến component, operation và work center. Ba cách tiếp cận này phù hợp để làm benchmark nghiệp vụ, nhưng hệ thống của công ty nên bổ sung lớp Channel Pricing/Marketplace Fee mà phần mềm giá thành sản xuất thuần túy thường không phải trọng tâm.

# 29. Lộ trình triển khai phần mềm

| **Giai đoạn** | **Phạm vi**                       | **Kết quả**                      |
|---------------|-----------------------------------|----------------------------------|
| Phase 1       | Master data + BOM + Standard Cost | Tính giá thành sản xuất          |
| Phase 2       | Actual production + variance      | So sánh định mức/thực tế         |
| Phase 3       | Wholesale/Retail pricing          | Bảng giá theo kênh               |
| Phase 4       | Shopee/TikTok/Lazada fee engine   | Unit economics TMĐT              |
| Phase 5       | Tax + Promotion + Affiliate       | Net realized price               |
| Phase 6       | Dashboard + API + automation      | Hệ thống quản trị giá hoàn chỉnh |

# 30. Kết luận và kiến nghị

Các file Excel hiện tại không nên bị bỏ đi; chúng nên được xem là 'business rules thực tế' của công ty và là dữ liệu đầu vào để chuẩn hóa. Kiến trúc phù hợp nhất là xây dựng một hệ thống tính giá theo hướng cấu hình: sản phẩm → BOM → chi phí sản xuất → cost snapshot → kênh bán → fee/tax rules → pricing scenario → giá bán → lợi nhuận thực tế.

Đặc biệt, không nên xây dựng một màn hình 'nhập giá và cộng các khoản chi phí'. Nên xây dựng một engine có thể trả lời đồng thời các câu hỏi: sản phẩm này thực sự tốn bao nhiêu để sản xuất; mỗi kênh làm phát sinh thêm bao nhiêu chi phí; giá bán thấp nhất là bao nhiêu; muốn đạt lợi nhuận X đồng hoặc Y% thì phải niêm yết bao nhiêu; và sau khi bán thực tế thì lợi nhuận có đúng như kế hoạch hay không.

# Phụ lục A – Bộ dữ liệu tối thiểu cần chuẩn hóa từ Excel

| **Nhóm**   | **Trường dữ liệu cần có**                                    |
|------------|--------------------------------------------------------------|
| Product    | Product Code, Name, Category, Base UOM                       |
| SKU        | SKU Code, Product, Variant, Net Weight, Packaging            |
| Material   | Material Code, Name, Type, UOM, Tax Profile                  |
| Supplier   | Supplier Code, Name, Currency, Payment Terms                 |
| Price      | Effective Date, Supplier, Material, Qty Break, Unit Price    |
| BOM        | BOM Code, Version, Effective From/To, Component, Qty, Scrap% |
| Packaging  | Pack Type, Units/Pack, Packs/Carton, Cartons/Container       |
| Production | Work Center, Operation, Setup Time, Run Time, Capacity       |
| Labor      | Labor Type, Rate, Effective Date                             |
| Overhead   | Cost Pool, Amount, Allocation Base                           |
| Channel    | Channel, Seller Type, Category                               |
| Fee Rule   | Fee Type, Rate, Fixed, Base, Cap, Effective Date             |
| Tax        | Tax Type, Rate, Base, Method, Effective Date                 |
| Price List | Channel, Customer Group, Currency, Validity                  |

# Phụ lục B – Danh sách nguồn tham khảo nghiệp vụ đã rà soát

- Thông tư 200/2014/TT-BTC – hướng dẫn chế độ kế toán doanh nghiệp, phần TK 154/TK 155 và tập hợp chi phí sản xuất.

- Thông tư 25/2014/TT-BTC – phương pháp định giá chung hàng hóa, dịch vụ.

- Nghị định 117/2025/NĐ-CP – quản lý thuế đối với hoạt động kinh doanh trên nền tảng TMĐT/nền tảng số của hộ, cá nhân.

- MISA AMIS – Giá thành định mức sản phẩm; Khai báo định mức giá thành; Báo cáo giá thành.

- FAST Accounting – Giá thành sản xuất và các báo cáo tập hợp/phân bổ/đối chiếu.

- Odoo Manufacturing – Manufacturing Order Costs.

- Shopee – Affiliate Service Fee và thông tin thuế liên quan.

- TikTok Shop – Platform Commission Fee, Transaction Fee, Order Processing Fee và thông tin thuế trên phí nền tảng.

# Phụ lục C – Lưu ý kiểm soát nghiệp vụ

- Các mức phí sàn trong tài liệu chỉ là ví dụ/ảnh chụp theo thời điểm; phần mềm phải đọc được biểu phí có ngày hiệu lực và cho phép cập nhật.

- Các quy tắc thuế phải được kế toán/đơn vị tư vấn thuế xác nhận trước khi đưa vào production.

- Không dùng cùng một 'giá thành' cho cả kế toán tài chính và quyết định giá bán quản trị; hai lớp cần liên kết nhưng phải tách biệt.

- Đối với nông sản có nhiều công đoạn, nên thiết kế BOM đa cấp và sản phẩm trung gian/bán thành phẩm ngay từ đầu.
