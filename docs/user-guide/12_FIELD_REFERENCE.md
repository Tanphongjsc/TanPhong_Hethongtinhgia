# 12. Tham chiếu trường nhập và trường kết quả

**[HỆ THỐNG HIỆN TẠI]** Tra chương này khi chưa biết chọn gì trên form. Đọc chương thao tác [Danh mục](04_HUONG_DAN_DANH_MUC.md), [Sản xuất](05_HUONG_DAN_SAN_XUAT.md), [Công thức/giá thành](06_HUONG_DAN_FORMULA_VA_COSTING.md) hoặc [Giá bán](07_HUONG_DAN_PRICING.md) trước khi nhập lần đầu.

Phạm vi: **39 lớp form cụ thể**, **319 định nghĩa trường người dùng nhìn thấy**: 95 danh mục +104 sản xuất +49 công thức/giá thành +71 giá bán. Số này tính một trường cho mỗi form, không nhân hai lần tạo/sửa; gồm hai biến thể ngày/thời điểm của form kết thúc hiệu lực. Hai mẫu trường động (đầu vào test công thức, đầu vào MANUAL của Run) mô tả riêng, không thể đếm thành một số cố định. Khóa UUID chống gửi trùng của Run là trường ẩn, không tính vào 319. Một màn hình có thể ghép nhiều form.

“Bắt buộc/Có” không có nghĩa checkbox phải tích. “Điều kiện/Có*” là cần khi thỏa điều kiện, dù Django có thể khai báo field optional. “Giá trị hiện có” chỉ là initial của form sửa, không phải default cho bản mới. Mã technical trong bảng dùng để đối chiếu cấu hình, không đổi thành mã tiếng Việt.

Các form tạo/sửa dùng cùng quy tắc kiểu dữ liệu trừ khác biệt được nêu. Trường readonly/disabled không vượt qua được bằng cách gửi POST khác; giới hạn bất biến vẫn được kiểm tra phía backend. ID/ngày ghi nhận được tự tạo. Không nhập dấu phân cách nghìn vào số: nhập `125000`, không nhập `125.000` để biểu diễn một trăm hai mươi lăm nghìn. Số lẻ nhập dấu chấm; ngày chọn bằng date picker, hiển thị ngày/tháng/năm. Trong biểu thức Formula, luôn dùng dấu chấm thập phân.

## Mục lục nhóm trường

- Danh mục: CostElement, Currency, UomCategory, Uom, UomConversion, Supplier, SupplierPrice, ProductCategory, Item, Product, Sku.
- Sản xuất: Recipe/header/version/line; PackagingConfig/header/version/line/assignment; WorkCenter; Resource; ResourceRate; Routing/header/version/operation; CostPool; AllocationRule.
- Công thức/giá thành: Formula/header/version/test; CostingScheme/header/version/line; Run và input động.
- Giá bán: Channel; ChannelFeeRule; TaxRule; FxRate; Scenario; ClosePeriod.
- Cuối chương: trường tự động, kết quả chỉ đọc, enum/trạng thái và lựa chọn theo tình huống.

## Danh mục: quy ước chung

Đối chiếu `ModelForm` thực tế và model ngày 09/10/2026; 11 schema, 95 trường tạo mới và 95 vị trí trường chỉnh sửa. `Có` là bắt buộc; `Không` có thể để trống; `Điều kiện` có thể là field optional ở Django nhưng validator bắt buộc trong tình huống nêu. Checkbox được bỏ tích, không cần nhập chữ Có/Không. ID, ngày tạo/cập nhật do hệ thống ghi; không phải input form. Các trường dropdown mới chỉ chọn bản đang hoạt động; sửa được giữ chính tham chiếu cũ đã ngừng hoạt động, không chọn bản ngừng hoạt động khác. Chữ “Có” trong Editable không vượt qua kiểm tra tham chiếu/nghiệp vụ.

Chuỗi mã thông thường trim + uppercase; tên/text trim. Tiền tệ, nhóm đơn vị và đơn vị có mã duy nhất trong bảng; các mã còn lại duy nhất trong bộ dữ liệu doanh nghiệp. Mã vạch giữ hoa/thường. Đại lượng của Phần tử chi phí không tự uppercase; Mã đại lượng của Nhóm đơn vị tính có uppercase. Số thập phân nhập bằng dấu chấm. Đơn vị và tiền tệ chỉ ghi liên kết, không tự quy đổi.


### Phần tử chi phí — CostElementForm

Menu **DỮ LIỆU DANH MỤC → Phần tử chi phí**. Nguồn: [form](../../apps/master_data/forms.py), [validator](../../apps/master_data/validators.py), [model](../../apps/core/models.py), [service](../../apps/master_data/services.py), [template](../../templates/master_data/partials/cost_element_form_content.html). Nút **Lưu phần tử chi phí**. Conditional fields luôn hiện, backend kiểm tra sau lưu.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm chi phí | group | Gom biến chi phí; dropdown | Không | Có | Trống | Chọn nhóm hợp lệ | CostElementGroup đang hoạt động; chưa có CRUD nhóm trong UI | Nhóm nguyên liệu đã thiết lập |
| Mã | code | Mã biến; text ≤120 | Có | Có | Trống | Trim/uppercase; duy nhất; nên ổn định để công thức tham chiếu | Không | TRANSPORT_COST |
| Tên | name | Tên hiển thị; text ≤255 | Có | Có | Trống | Không rỗng sau trim | Không | Chi phí vận chuyển |
| Mô tả | description | Giải thích cách dùng; textarea | Không | Có | Trống | Trim; trống lưu null | Không | Chi phí trên một lô tính |
| Loại giá trị | value_type | Kiểu biến; dropdown | Có | Có | Không explicit initial; UI mục đầu MONEY | Chỉ MONEY/NUMBER/PERCENT/QUANTITY/BOOLEAN/TEXT | Tiền tệ/Số/Tỷ lệ phần trăm/Số lượng/Có / Không/Văn bản | Tiền tệ (MONEY) |
| Đại lượng | dimension_code | Mã đại lượng; text ≤50 | Không | Có | Trống | Nếu cùng nhập default_uom, phải khớp category.dimension_code; không tự uppercase | Mã của nhóm đơn vị đã chọn | MONEY hoặc MASS |
| Nguồn dữ liệu | default_source_mode | Nguồn mặc định của biến; dropdown | Có | Có | Không explicit initial; UI mục đầu SYSTEM | Chỉ SYSTEM/MANUAL/LOOKUP/FORMULA/EXTERNAL; không bảo đảm tất cả thực thi được ở Scheme | Hệ thống/Nhập thủ công/Tra cứu/Công thức/Nguồn bên ngoài | Nhập thủ công (MANUAL) |
| Tiền tệ | currency_code | Đồng tiền của biến; dropdown | Điều kiện: MONEY | Có | Trống | MONEY thiếu tiền tệ bị chặn | Currency đang hoạt động, mã — tên | VND |
| Đơn vị tính mặc định | default_uom | Đơn vị của biến; dropdown | Điều kiện: QUANTITY | Có | Trống | QUANTITY thiếu đơn vị bị chặn; đại lượng nếu có phải khớp | Uom đang hoạt động, mã — tên | KG |
| Số chữ số làm tròn | rounding_scale | Độ lẻ khi làm tròn; integer | Có | Có | 6 | 0–12 | Không | 6 |
| Phương pháp làm tròn | rounding_mode | Hướng làm tròn; dropdown | Có | Có | Không explicit initial; UI mục đầu HALF_UP | HALF_UP/HALF_EVEN/UP/DOWN/CEILING/FLOOR | Làm tròn nửa lên/nửa về số chẵn/ra xa 0/về 0/về dương vô cùng/về âm vô cùng | HALF_UP |
| Phạm vi kế toán | accounting_scope | Phân loại kế toán; dropdown | Có | Có | Không explicit initial; UI mục đầu INVENTORY_COST | Chỉ INVENTORY_COST/COMMERCIAL_COST/PRICING_ONLY/ANALYTICS | Chi phí hàng tồn kho/Chi phí thương mại/Chỉ dùng cho giá bán/Phân tích | Chi phí thương mại |
| Phạm vi chi phí | cost_scope | Mục đích chi phí; dropdown | Có | Có | Không explicit initial; UI mục đầu MANUFACTURING | Chỉ MANUFACTURING/LANDED/COST_TO_SERVE/CHANNEL/PRICING/ANALYTICS | Sản xuất/Chi phí đến kho/Chi phí phục vụ/Kênh bán/Giá bán/Phân tích | Chi phí phục vụ |
| Dữ liệu nhạy cảm | is_sensitive | Cờ thận trọng khi chia sẻ; checkbox | Không | Có trong runtime hiện tại | Không tích | Boolean; không tạo phân quyền theo nhân viên | Không | Tích nếu dữ liệu nhạy cảm |
| Đang hoạt động | is_active | Cho dùng trong cấu hình mới; checkbox | Không | Có | Tích | Boolean; ngừng bản đang active có xác nhận | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm chi phí | group | Gom biến chi phí; dropdown | Không | Có | Giá trị hiện có | Chọn nhóm hợp lệ | CostElementGroup đang hoạt động; chưa có CRUD nhóm trong UI | Nhóm nguyên liệu đã thiết lập |
| Mã | code | Mã biến; text ≤120 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất; nên ổn định để công thức tham chiếu | Không | TRANSPORT_COST |
| Tên | name | Tên hiển thị; text ≤255 | Có | Có | Giá trị hiện có | Không rỗng sau trim | Không | Chi phí vận chuyển |
| Mô tả | description | Giải thích cách dùng; textarea | Không | Có | Giá trị hiện có | Trim; trống lưu null | Không | Chi phí trên một lô tính |
| Loại giá trị | value_type | Kiểu biến; dropdown | Có | Có | Giá trị hiện có | Chỉ MONEY/NUMBER/PERCENT/QUANTITY/BOOLEAN/TEXT | Tiền tệ/Số/Tỷ lệ phần trăm/Số lượng/Có / Không/Văn bản | Tiền tệ (MONEY) |
| Đại lượng | dimension_code | Mã đại lượng; text ≤50 | Không | Có | Giá trị hiện có | Nếu cùng nhập default_uom, phải khớp category.dimension_code; không tự uppercase | Mã của nhóm đơn vị đã chọn | MONEY hoặc MASS |
| Nguồn dữ liệu | default_source_mode | Nguồn mặc định của biến; dropdown | Có | Có | Giá trị hiện có | Chỉ SYSTEM/MANUAL/LOOKUP/FORMULA/EXTERNAL; không bảo đảm tất cả thực thi được ở Scheme | Hệ thống/Nhập thủ công/Tra cứu/Công thức/Nguồn bên ngoài | Nhập thủ công (MANUAL) |
| Tiền tệ | currency_code | Đồng tiền của biến; dropdown | Điều kiện: MONEY | Có | Giá trị hiện có | MONEY thiếu tiền tệ bị chặn | Currency đang hoạt động, mã — tên | VND |
| Đơn vị tính mặc định | default_uom | Đơn vị của biến; dropdown | Điều kiện: QUANTITY | Có | Giá trị hiện có | QUANTITY thiếu đơn vị bị chặn; đại lượng nếu có phải khớp | Uom đang hoạt động, mã — tên | KG |
| Số chữ số làm tròn | rounding_scale | Độ lẻ khi làm tròn; integer | Có | Có | Giá trị hiện có | 0–12 | Không | 6 |
| Phương pháp làm tròn | rounding_mode | Hướng làm tròn; dropdown | Có | Có | Giá trị hiện có | HALF_UP/HALF_EVEN/UP/DOWN/CEILING/FLOOR | Làm tròn nửa lên/nửa về số chẵn/ra xa 0/về 0/về dương vô cùng/về âm vô cùng | HALF_UP |
| Phạm vi kế toán | accounting_scope | Phân loại kế toán; dropdown | Có | Có | Giá trị hiện có | Chỉ INVENTORY_COST/COMMERCIAL_COST/PRICING_ONLY/ANALYTICS | Chi phí hàng tồn kho/Chi phí thương mại/Chỉ dùng cho giá bán/Phân tích | Chi phí thương mại |
| Phạm vi chi phí | cost_scope | Mục đích chi phí; dropdown | Có | Có | Giá trị hiện có | Chỉ MANUFACTURING/LANDED/COST_TO_SERVE/CHANNEL/PRICING/ANALYTICS | Sản xuất/Chi phí đến kho/Chi phí phục vụ/Kênh bán/Giá bán/Phân tích | Chi phí phục vụ |
| Dữ liệu nhạy cảm | is_sensitive | Cờ thận trọng khi chia sẻ; checkbox | Không | Có trong runtime hiện tại | Giá trị hiện có | Boolean; không tạo phân quyền theo nhân viên | Không | Tích nếu dữ liệu nhạy cảm |
| Đang hoạt động | is_active | Cho dùng trong cấu hình mới; checkbox | Không | Có | Giá trị hiện có | Boolean; ngừng bản đang active có xác nhận | Không | Tích |

### Tiền tệ — CurrencyForm

Nguồn: [form](../../apps/master_data/forms.py), [validator](../../apps/master_data/validators.py), [model](../../apps/core/models.py), [ghi](../../apps/master_data/services.py). Menu **Tiền tệ**, nút **Lưu tiền tệ**.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã tiền tệ | code | Định danh đồng tiền; text 3 ký tự | Có | Có | Trống | Đúng 3 ký tự; trim/uppercase; duy nhất, không giới hạn ISO | Không | VND |
| Tên | name | Tên tiền; text ≤100 | Có | Có | Trống | Không rỗng | Không | Việt Nam đồng |
| Số chữ số thập phân | decimal_places | Số lẻ danh mục tiền; integer | Có | Có | 2 | 0–8; không tự đổi commercial rounding | Không | 0 |
| Đang hoạt động | is_active | Trạng thái sử dụng; checkbox | Không | Có | Tích | Boolean | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã tiền tệ | code | Định danh đồng tiền; text 3 ký tự | Có | Chỉ đọc (disabled) | Giá trị hiện có | Giữ nguyên mã; không đổi kể cả gửi giá trị khác | Không | VND |
| Tên | name | Tên tiền; text ≤100 | Có | Có | Giá trị hiện có | Không rỗng | Không | Việt Nam đồng |
| Số chữ số thập phân | decimal_places | Số lẻ danh mục tiền; integer | Có | Có | Giá trị hiện có | 0–8; không tự đổi commercial rounding | Không | 0 |
| Đang hoạt động | is_active | Trạng thái sử dụng; checkbox | Không | Có | Giá trị hiện có | Boolean | Không | Tích |

### Nhóm đơn vị tính — UomCategoryForm

Nguồn: [form](../../apps/master_data/forms.py), [validator](../../apps/master_data/validators.py), [model](../../apps/core/models.py). Menu **Nhóm đơn vị tính**, nút **Lưu nhóm đơn vị tính**.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã nhóm | code | Định danh nhóm đo; text ≤50 | Có | Có | Trống | Trim/uppercase; duy nhất | Không | MASS |
| Tên | name | Tên nhóm; text ≤150 | Có | Có | Trống | Không rỗng | Không | Khối lượng |
| Mã đại lượng | dimension_code | Loại đại lượng; text ≤50 | Có | Có | Trống | Trim/uppercase; không có enum dropdown | Nhập mã đúng theo nhu cầu đơn vị | MASS; LENGTH; TIME; COUNT |
| Mô tả | description | Giải thích nhóm; textarea | Không | Có | Trống | Trim; trống null | Không | Các đơn vị khối lượng |
| Đang hoạt động | is_active | Trạng thái dùng nhóm; checkbox | Không | Có | Tích | Boolean | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã nhóm | code | Định danh nhóm đo; text ≤50 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất | Không | MASS |
| Tên | name | Tên nhóm; text ≤150 | Có | Có | Giá trị hiện có | Không rỗng | Không | Khối lượng |
| Mã đại lượng | dimension_code | Loại đại lượng; text ≤50 | Có | Có | Giá trị hiện có | Trim/uppercase; không có enum dropdown | Nhập mã đúng theo nhu cầu đơn vị | MASS; LENGTH; TIME; COUNT |
| Mô tả | description | Giải thích nhóm; textarea | Không | Có | Giá trị hiện có | Trim; trống null | Không | Các đơn vị khối lượng |
| Đang hoạt động | is_active | Trạng thái dùng nhóm; checkbox | Không | Có | Giá trị hiện có | Boolean | Không | Tích |

### Đơn vị tính — UomForm

Nguồn: [form](../../apps/master_data/forms.py), [validator](../../apps/master_data/validators.py), [model](../../apps/core/models.py), [service kiểm tra đổi nhóm](../../apps/master_data/services.py). Menu **Đơn vị tính**, nút **Lưu đơn vị tính**.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm đơn vị tính | category | Nhóm đo của đơn vị; dropdown | Có | Có | Trống | Phải tồn tại, đang hoạt động | UomCategory, mã — tên | MASS — Khối lượng |
| Mã đơn vị | code | Định danh đơn vị; text ≤50 | Có | Có | Trống | Trim/uppercase; duy nhất | Không | KG |
| Tên | name | Tên đơn vị; text ≤150 | Có | Có | Trống | Không rỗng | Không | Kilôgam |
| Ký hiệu | symbol | Ký hiệu hiển thị; text ≤30 | Có | Có | Trống | Không rỗng; trim, giữ hoa/thường | Không | kg |
| Độ chính xác | precision | Số lẻ cấu hình; integer | Có | Có | 6 | 0–12 | Không | 6 |
| Đơn vị cơ sở | is_base | Cờ cơ sở trong nhóm; checkbox | Không | Có | Không tích | Không có quy tắc duy nhất một base trong nhóm | Không | Tích cho KG |
| Đang hoạt động | is_active | Trạng thái sử dụng; checkbox | Không | Có | Tích | Boolean | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu. Đổi nhóm bị chặn nếu làm quy đổi chung đang có khác nhóm; điều chỉnh quy đổi trước.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm đơn vị tính | category | Nhóm đo của đơn vị; dropdown | Có | Có | Giá trị hiện có | Phải tồn tại, đang hoạt động | UomCategory, mã — tên | MASS — Khối lượng |
| Mã đơn vị | code | Định danh đơn vị; text ≤50 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất | Không | KG |
| Tên | name | Tên đơn vị; text ≤150 | Có | Có | Giá trị hiện có | Không rỗng | Không | Kilôgam |
| Ký hiệu | symbol | Ký hiệu hiển thị; text ≤30 | Có | Có | Giá trị hiện có | Không rỗng; trim, giữ hoa/thường | Không | kg |
| Độ chính xác | precision | Số lẻ cấu hình; integer | Có | Có | Giá trị hiện có | 0–12 | Không | 6 |
| Đơn vị cơ sở | is_base | Cờ cơ sở trong nhóm; checkbox | Không | Có | Giá trị hiện có | Không có quy tắc duy nhất một base trong nhóm | Không | Tích cho KG |
| Đang hoạt động | is_active | Trạng thái sử dụng; checkbox | Không | Có | Giá trị hiện có | Boolean | Không | Tích |

### Quy đổi đơn vị tính — UomConversionForm

Nguồn: [form](../../apps/master_data/forms.py), [validator](../../apps/master_data/validators.py), [model](../../apps/core/models.py), [resolver](../../apps/costing/engine/resolvers/uom.py). Menu **Quy đổi đơn vị tính**, nút **Lưu quy đổi đơn vị tính**. Không có version/status/is_active input. Bản dùng chung xem được nhưng không chỉnh sửa ở đây.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Đơn vị nguồn | from_uom | Đơn vị số lượng gốc; dropdown | Có | Có | Trống | Khác đơn vị đích | Uom đang hoạt động, mã — tên | G |
| Đơn vị đích | to_uom | Đơn vị sau nhân hệ số; dropdown | Có | Có | Trống | Nếu Item trống, cùng category với nguồn | Uom đang hoạt động, mã — tên | KG |
| Hệ số quy đổi | factor | Đích = nguồn × hệ số; Decimal(24,12) | Có | Có | Trống | Hữu hạn, >0, ≤12 chữ số thập phân | Không | 0.001 |
| Vật tư / Hàng hóa | item | Phạm vi quy đổi riêng; dropdown | Không; cần nếu khác nhóm | Có | Trống = chung | Item hợp lệ; không có ưu tiên bản riêng ở Costing | Item đang hoạt động, mã — tên | RM_COFFEE cho quy cách riêng |
| Hiệu lực từ ngày | effective_from | Ngày bắt đầu; date | Có | Có | Ngày hiện tại theo múi giờ ứng dụng | Ngày hợp lệ | Không | 2026-01-01 |
| Hiệu lực đến ngày | effective_to | Ngày cuối; date | Không | Có | Trống = vô hạn | Nếu nhập: > effective_from; Costing gồm cả ngày cuối | Không | 2026-06-30 |
| Nguồn tham chiếu | source_reference | Căn cứ quy đổi; textarea | Không | Có | Trống | Trim; trống null | Không | Quy cách bao 25kg |

#### Form chỉnh sửa

Chỉ sửa bản thuộc phạm vi dữ liệu hiện tại; bản dùng chung chỉ xem. Giá trị hiện có là initial; cùng validation như tạo; giữ được chính tham chiếu cũ ngừng hoạt động.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Đơn vị nguồn | from_uom | Đơn vị số lượng gốc; dropdown | Có | Có | Giá trị hiện có | Khác đơn vị đích | Uom đang hoạt động, mã — tên | G |
| Đơn vị đích | to_uom | Đơn vị sau nhân hệ số; dropdown | Có | Có | Giá trị hiện có | Nếu Item trống, cùng category với nguồn | Uom đang hoạt động, mã — tên | KG |
| Hệ số quy đổi | factor | Đích = nguồn × hệ số; Decimal(24,12) | Có | Có | Giá trị hiện có | Hữu hạn, >0, ≤12 chữ số thập phân | Không | 0.001 |
| Vật tư / Hàng hóa | item | Phạm vi quy đổi riêng; dropdown | Không; cần nếu khác nhóm | Có | Giá trị hiện có | Item hợp lệ; không có ưu tiên bản riêng ở Costing | Item đang hoạt động, mã — tên | RM_COFFEE cho quy cách riêng |
| Hiệu lực từ ngày | effective_from | Ngày bắt đầu; date | Có | Có | Giá trị hiện có | Ngày hợp lệ | Không | 2026-01-01 |
| Hiệu lực đến ngày | effective_to | Ngày cuối; date | Không | Có | Giá trị hiện có | Nếu nhập: > effective_from; Costing gồm cả ngày cuối | Không | 2026-06-30 |
| Nguồn tham chiếu | source_reference | Căn cứ quy đổi; textarea | Không | Có | Giá trị hiện có | Trim; trống null | Không | Quy cách bao 25kg |

### Nhóm sản phẩm — ProductCategoryForm

Nguồn: [form](../../apps/product/forms.py), [validator](../../apps/product/validators.py), [model](../../apps/core/models.py), [service giữ parent](../../apps/product/services.py). Menu **Nhóm sản phẩm**, nút **Lưu nhóm sản phẩm**. Không có nhóm cha input; giữ giá trị cũ khi sửa.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã | code | Mã nhóm hàng; text ≤100 | Có | Có | Trống | Trim/uppercase; duy nhất | Không | COFFEE |
| Tên nhóm sản phẩm | name | Tên nhóm; text ≤255 | Có | Có | Trống | Không rỗng | Không | Cà phê |
| Mô tả | description | Mô tả nhóm; textarea | Không | Có | Trống | Trim; trống null | Không | Nhóm cà phê hòa tan |
| Đang hoạt động | is_active | Trạng thái nhóm; checkbox | Không | Có | Tích | Boolean | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã | code | Mã nhóm hàng; text ≤100 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất | Không | COFFEE |
| Tên nhóm sản phẩm | name | Tên nhóm; text ≤255 | Có | Có | Giá trị hiện có | Không rỗng | Không | Cà phê |
| Mô tả | description | Mô tả nhóm; textarea | Không | Có | Giá trị hiện có | Trim; trống null | Không | Nhóm cà phê hòa tan |
| Đang hoạt động | is_active | Trạng thái nhóm; checkbox | Không | Có | Giá trị hiện có | Boolean | Không | Tích |

### Vật tư / Hàng hóa — ItemForm

Nguồn: [form](../../apps/product/forms.py), [validator](../../apps/product/validators.py), [model](../../apps/core/models.py), [dịch vụ giữ metadata](../../apps/product/services.py). Menu **Vật tư / Hàng hóa**, nút **Lưu vật tư / hàng hóa**. Trọng lượng/kích thước luôn hiện; không có phép quy đổi tự động hoặc hidden-field UI.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm sản phẩm | category | Phân loại Item; dropdown | Không | Có | Trống | Chọn nhóm hợp lệ | ProductCategory đang hoạt động, mã — tên | COFFEE |
| Mã | code | Định danh Item; text ≤120 | Có | Có | Trống | Trim/uppercase; duy nhất | Không | RM_COFFEE |
| Tên | name | Tên Item; text ≤255 | Có | Có | Trống | Không rỗng | Không | Cà phê hòa tan |
| Loại vật tư / hàng hóa | item_type | Phân loại công dụng; dropdown | Có | Có | Không explicit initial; UI mục đầu RAW_MATERIAL | RAW_MATERIAL/PACKAGING/SEMI_FINISHED/FINISHED_GOOD/SERVICE/BY_PRODUCT | Nguyên liệu/Bao bì/Bán thành phẩm/Thành phẩm/Dịch vụ/Phụ phẩm | Nguyên liệu |
| Đơn vị cơ sở | base_uom | Đơn vị chuẩn của Item; dropdown | Có | Có | Trống | Đơn vị hợp lệ; không tự tạo quy đổi | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg) |
| Đơn vị mua | purchase_uom | Đơn vị thường mua; dropdown | Không | Có | Trống | Đơn vị hợp lệ, không bắt buộc cùng nhóm với base tại form | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg) |
| Đơn vị sản xuất | production_uom | Đơn vị trong sản xuất; dropdown | Không | Có | Trống | Đơn vị hợp lệ; không tự quy đổi | Uom đang hoạt động, tên (ký hiệu) | Gam (g) |
| Mã nhóm thuế | tax_class_code | Nhãn phân loại thuế; text ≤100 | Không | Có | Trống | Trim; trống null, không tự chọn TaxRule | Nhập trực tiếp | FOOD |
| Khối lượng tịnh | net_weight | Trọng lượng chưa bao bì; Decimal(24,8) | Không | Có | Trống | Hữu hạn ≥0; cả 0 cũng cần weight_uom | Đơn vị trọng lượng nếu nhập | 1 |
| Khối lượng tổng | gross_weight | Trọng lượng gồm bao bì; Decimal(24,8) | Không | Có | Trống | Hữu hạn ≥0; ≥net_weight nếu cả hai có | Đơn vị trọng lượng nếu nhập | 1.05 |
| Đơn vị trọng lượng | weight_uom | Đơn vị số đo khối lượng; dropdown | Điều kiện: có net/gross | Có | Trống | Phải thuộc category.dimension_code MASS nếu chọn hoặc có số đo | Uom đại lượng MASS đang hoạt động | Kilôgam (kg) |
| Chiều dài | length | Số đo dài; Decimal(24,8) | Không | Có | Trống | Hữu hạn ≥0; nhập cả 0 cần dimension_uom | Đơn vị kích thước nếu nhập | 20 |
| Chiều rộng | width | Số đo rộng; Decimal(24,8) | Không | Có | Trống | Hữu hạn ≥0 | Đơn vị kích thước nếu nhập | 10 |
| Chiều cao | height | Số đo cao; Decimal(24,8) | Không | Có | Trống | Hữu hạn ≥0 | Đơn vị kích thước nếu nhập | 5 |
| Đơn vị kích thước | dimension_uom | Đơn vị dài/rộng/cao; dropdown | Điều kiện: có length/width/height | Có | Trống | Phải thuộc category.dimension_code LENGTH nếu chọn hoặc có số đo | Uom đại lượng LENGTH đang hoạt động | Centimét (cm) |
| Theo dõi tồn kho | is_stock_item | Cờ phân loại hàng tồn kho; checkbox | Không | Có | Tích | Boolean; không cung cấp quản lý giao dịch tồn kho | Không | Tích cho nguyên liệu |
| Đang hoạt động | is_active | Trạng thái sử dụng; checkbox | Không | Có | Tích | Boolean | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm sản phẩm | category | Phân loại Item; dropdown | Không | Có | Giá trị hiện có | Chọn nhóm hợp lệ | ProductCategory đang hoạt động, mã — tên | COFFEE |
| Mã | code | Định danh Item; text ≤120 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất | Không | RM_COFFEE |
| Tên | name | Tên Item; text ≤255 | Có | Có | Giá trị hiện có | Không rỗng | Không | Cà phê hòa tan |
| Loại vật tư / hàng hóa | item_type | Phân loại công dụng; dropdown | Có | Có | Giá trị hiện có | RAW_MATERIAL/PACKAGING/SEMI_FINISHED/FINISHED_GOOD/SERVICE/BY_PRODUCT | Nguyên liệu/Bao bì/Bán thành phẩm/Thành phẩm/Dịch vụ/Phụ phẩm | Nguyên liệu |
| Đơn vị cơ sở | base_uom | Đơn vị chuẩn của Item; dropdown | Có | Có | Giá trị hiện có | Đơn vị hợp lệ; không tự tạo quy đổi | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg) |
| Đơn vị mua | purchase_uom | Đơn vị thường mua; dropdown | Không | Có | Giá trị hiện có | Đơn vị hợp lệ, không bắt buộc cùng nhóm với base tại form | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg) |
| Đơn vị sản xuất | production_uom | Đơn vị trong sản xuất; dropdown | Không | Có | Giá trị hiện có | Đơn vị hợp lệ; không tự quy đổi | Uom đang hoạt động, tên (ký hiệu) | Gam (g) |
| Mã nhóm thuế | tax_class_code | Nhãn phân loại thuế; text ≤100 | Không | Có | Giá trị hiện có | Trim; trống null, không tự chọn TaxRule | Nhập trực tiếp | FOOD |
| Khối lượng tịnh | net_weight | Trọng lượng chưa bao bì; Decimal(24,8) | Không | Có | Giá trị hiện có | Hữu hạn ≥0; cả 0 cũng cần weight_uom | Đơn vị trọng lượng nếu nhập | 1 |
| Khối lượng tổng | gross_weight | Trọng lượng gồm bao bì; Decimal(24,8) | Không | Có | Giá trị hiện có | Hữu hạn ≥0; ≥net_weight nếu cả hai có | Đơn vị trọng lượng nếu nhập | 1.05 |
| Đơn vị trọng lượng | weight_uom | Đơn vị số đo khối lượng; dropdown | Điều kiện: có net/gross | Có | Giá trị hiện có | Phải thuộc category.dimension_code MASS nếu chọn hoặc có số đo | Uom đại lượng MASS đang hoạt động | Kilôgam (kg) |
| Chiều dài | length | Số đo dài; Decimal(24,8) | Không | Có | Giá trị hiện có | Hữu hạn ≥0; nhập cả 0 cần dimension_uom | Đơn vị kích thước nếu nhập | 20 |
| Chiều rộng | width | Số đo rộng; Decimal(24,8) | Không | Có | Giá trị hiện có | Hữu hạn ≥0 | Đơn vị kích thước nếu nhập | 10 |
| Chiều cao | height | Số đo cao; Decimal(24,8) | Không | Có | Giá trị hiện có | Hữu hạn ≥0 | Đơn vị kích thước nếu nhập | 5 |
| Đơn vị kích thước | dimension_uom | Đơn vị dài/rộng/cao; dropdown | Điều kiện: có length/width/height | Có | Giá trị hiện có | Phải thuộc category.dimension_code LENGTH nếu chọn hoặc có số đo | Uom đại lượng LENGTH đang hoạt động | Centimét (cm) |
| Theo dõi tồn kho | is_stock_item | Cờ phân loại hàng tồn kho; checkbox | Không | Có | Giá trị hiện có | Boolean; không cung cấp quản lý giao dịch tồn kho | Không | Tích cho nguyên liệu |
| Đang hoạt động | is_active | Trạng thái sử dụng; checkbox | Không | Có | Giá trị hiện có | Boolean | Không | Tích |

### Sản phẩm — ProductForm

Nguồn: [form](../../apps/product/forms.py), [validator](../../apps/product/validators.py), [model](../../apps/core/models.py), [service](../../apps/product/services.py). Menu **Sản phẩm**, nút **Lưu sản phẩm**. Không tự tạo Item/SKU/BOM.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm sản phẩm | category | Phân loại Product; dropdown | Không | Có | Trống | Tham chiếu hợp lệ | ProductCategory đang hoạt động | COFFEE |
| Mã sản phẩm | code | Mã sản phẩm gốc; text ≤120 | Có | Có | Trống | Trim/uppercase; duy nhất | Không | CAPPUCCINO |
| Tên sản phẩm | name | Tên sản phẩm gốc; text ≤255 | Có | Có | Trống | Không rỗng | Không | Cappuccino |
| Mô tả | description | Diễn giải sản phẩm; textarea | Không | Có | Trống | Trim; trống null | Không | Cà phê hòa tan Cappuccino |
| Đơn vị tính giá thành | costing_uom | Đơn vị cơ sở tính cost; dropdown | Có | Có | Trống | Tham chiếu hợp lệ, không bắt buộc MASS | Uom đang hoạt động, tên (ký hiệu) | Hộp (hộp) |
| Vật tư / Hàng hóa đầu ra | output_item | Liên kết đầu ra tới Item; dropdown | Không | Có | Trống | Item hợp lệ, không tự tạo Item | Item đang hoạt động | FG_CAPPUCCINO |
| Mã nhóm thuế | tax_class_code | Nhãn thuế của Product; text ≤100 | Không | Có | Trống | Trim; trống null; không tự chọn TaxRule | Nhập trực tiếp | FOOD |
| Đang hoạt động | is_active | Trạng thái sản phẩm; checkbox | Không | Có | Tích | Boolean | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhóm sản phẩm | category | Phân loại Product; dropdown | Không | Có | Giá trị hiện có | Tham chiếu hợp lệ | ProductCategory đang hoạt động | COFFEE |
| Mã sản phẩm | code | Mã sản phẩm gốc; text ≤120 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất | Không | CAPPUCCINO |
| Tên sản phẩm | name | Tên sản phẩm gốc; text ≤255 | Có | Có | Giá trị hiện có | Không rỗng | Không | Cappuccino |
| Mô tả | description | Diễn giải sản phẩm; textarea | Không | Có | Giá trị hiện có | Trim; trống null | Không | Cà phê hòa tan Cappuccino |
| Đơn vị tính giá thành | costing_uom | Đơn vị cơ sở tính cost; dropdown | Có | Có | Giá trị hiện có | Tham chiếu hợp lệ, không bắt buộc MASS | Uom đang hoạt động, tên (ký hiệu) | Hộp (hộp) |
| Vật tư / Hàng hóa đầu ra | output_item | Liên kết đầu ra tới Item; dropdown | Không | Có | Giá trị hiện có | Item hợp lệ, không tự tạo Item | Item đang hoạt động | FG_CAPPUCCINO |
| Mã nhóm thuế | tax_class_code | Nhãn thuế của Product; text ≤100 | Không | Có | Giá trị hiện có | Trim; trống null; không tự chọn TaxRule | Nhập trực tiếp | FOOD |
| Đang hoạt động | is_active | Trạng thái sản phẩm; checkbox | Không | Có | Giá trị hiện có | Boolean | Không | Tích |

### SKU — SkuForm

Nguồn: [form](../../apps/product/forms.py), [validator](../../apps/product/validators.py), [model](../../apps/core/models.py), [service giữ attributes](../../apps/product/services.py). Menu **SKU**, nút **Lưu SKU**. Không tự lấy sell_item từ Product; không có phụ thuộc dropdown Product→Item; gán bao bì riêng ở Cấu hình bao bì.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Sản phẩm | product | Sản phẩm gốc của SKU; dropdown | Có | Có | Trống | Product hợp lệ | Product đang hoạt động, mã — tên | CAPPUCCINO |
| Mã SKU | code | Mã quy cách bán; text ≤150 | Có | Có | Trống | Trim/uppercase; duy nhất | Không | CAP_BOX20 |
| Tên SKU | name | Tên quy cách bán; text ≤255 | Có | Có | Trống | Không rỗng | Không | Cappuccino hộp 20 gói |
| Mã vạch | barcode | Định danh vạch; text ≤100 | Không | Có | Trống | Trim giữ hoa/thường; nếu có duy nhất; nhiều bản được null | Không | 8930000000001 |
| Đơn vị bán | sales_uom | Đơn vị một mã bán; dropdown | Có | Có | Trống | Đơn vị hợp lệ | Uom đang hoạt động, tên (ký hiệu) | Hộp (hộp) |
| Lượng tịnh | net_quantity | Lượng trên một đơn vị bán; Decimal(24,8) | Có | Có | Trống | Hữu hạn >0; 0 và số âm không hợp lệ | Diễn giải cùng net_quantity_uom | 0.5 |
| Đơn vị lượng tịnh | net_quantity_uom | Đơn vị của lượng tịnh; dropdown | Có | Có | Trống | Không giới hạn MASS, không tự kiểm tra conversion trên master form | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg), lít hoặc cái |
| Vật tư / Hàng hóa bán | sell_item | Item bán tương ứng; dropdown | Không | Có | Trống | Item hợp lệ, không tự tạo Item | Item đang hoạt động | FG_CAP_BOX20 |
| Đang hoạt động | is_active | Trạng thái SKU; checkbox | Không | Có | Tích | Boolean | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Sản phẩm | product | Sản phẩm gốc của SKU; dropdown | Có | Có | Giá trị hiện có | Product hợp lệ | Product đang hoạt động, mã — tên | CAPPUCCINO |
| Mã SKU | code | Mã quy cách bán; text ≤150 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất | Không | CAP_BOX20 |
| Tên SKU | name | Tên quy cách bán; text ≤255 | Có | Có | Giá trị hiện có | Không rỗng | Không | Cappuccino hộp 20 gói |
| Mã vạch | barcode | Định danh vạch; text ≤100 | Không | Có | Giá trị hiện có | Trim giữ hoa/thường; nếu có duy nhất; nhiều bản được null | Không | 8930000000001 |
| Đơn vị bán | sales_uom | Đơn vị một mã bán; dropdown | Có | Có | Giá trị hiện có | Đơn vị hợp lệ | Uom đang hoạt động, tên (ký hiệu) | Hộp (hộp) |
| Lượng tịnh | net_quantity | Lượng trên một đơn vị bán; Decimal(24,8) | Có | Có | Giá trị hiện có | Hữu hạn >0; 0 và số âm không hợp lệ | Diễn giải cùng net_quantity_uom | 0.5 |
| Đơn vị lượng tịnh | net_quantity_uom | Đơn vị của lượng tịnh; dropdown | Có | Có | Giá trị hiện có | Không giới hạn MASS, không tự kiểm tra conversion trên master form | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg), lít hoặc cái |
| Vật tư / Hàng hóa bán | sell_item | Item bán tương ứng; dropdown | Không | Có | Giá trị hiện có | Item hợp lệ, không tự tạo Item | Item đang hoạt động | FG_CAP_BOX20 |
| Đang hoạt động | is_active | Trạng thái SKU; checkbox | Không | Có | Giá trị hiện có | Boolean | Không | Tích |

### Nhà cung cấp — SupplierForm

Nguồn: [form](../../apps/master_data/forms.py), [validator](../../apps/master_data/validators.py), [model](../../apps/core/models.py), [service](../../apps/master_data/services.py). Menu **Nhà cung cấp**, nút **Lưu nhà cung cấp**. Không có địa chỉ/email/điện thoại/country input.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã nhà cung cấp | code | Mã đối tác mua; text ≤120 | Có | Có | Trống | Trim/uppercase; duy nhất | Không | SUP_COFFEE |
| Tên nhà cung cấp | name | Tên đối tác; text ≤255 | Có | Có | Trống | Không rỗng | Không | Nhà cung cấp cà phê |
| Mã số thuế | tax_code | Thông tin mã số thuế; text ≤100 | Không | Có | Trống | Trim; trống null; không kiểm tra cấu trúc pháp lý | Nhập trực tiếp | MST_MINH_HOA |
| Tiền tệ mặc định | default_currency_code | Đồng tiền giao dịch thường dùng; dropdown | Không | Có | Trống | Tiền tệ hợp lệ; không tự điền SupplierPrice | Currency đang hoạt động, mã — tên | VND |
| Điều khoản thanh toán | payment_terms | Thỏa thuận thanh toán; textarea | Không | Có | Trống | Trim; trống null | Nhập trực tiếp | Thanh toán trong 30 ngày |
| Đang hoạt động | is_active | Trạng thái nhà cung cấp; checkbox | Không | Có | Tích | Boolean; ngừng có thể loại giá khỏi nguồn Run mới | Không | Tích |

#### Form chỉnh sửa

Giá trị hiện có là initial; cùng kiểu/validation như tạo. Giữ được chính tham chiếu cũ ngừng hoạt động; không chọn mới bản ngừng khác. Ngừng bản đang hoạt động cần Xác nhận và lưu.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Mã nhà cung cấp | code | Mã đối tác mua; text ≤120 | Có | Có | Giá trị hiện có | Trim/uppercase; duy nhất | Không | SUP_COFFEE |
| Tên nhà cung cấp | name | Tên đối tác; text ≤255 | Có | Có | Giá trị hiện có | Không rỗng | Không | Nhà cung cấp cà phê |
| Mã số thuế | tax_code | Thông tin mã số thuế; text ≤100 | Không | Có | Giá trị hiện có | Trim; trống null; không kiểm tra cấu trúc pháp lý | Nhập trực tiếp | MST_MINH_HOA |
| Tiền tệ mặc định | default_currency_code | Đồng tiền giao dịch thường dùng; dropdown | Không | Có | Giá trị hiện có | Tiền tệ hợp lệ; không tự điền SupplierPrice | Currency đang hoạt động, mã — tên | VND |
| Điều khoản thanh toán | payment_terms | Thỏa thuận thanh toán; textarea | Không | Có | Giá trị hiện có | Trim; trống null | Nhập trực tiếp | Thanh toán trong 30 ngày |
| Đang hoạt động | is_active | Trạng thái nhà cung cấp; checkbox | Không | Có | Giá trị hiện có | Boolean; ngừng có thể loại giá khỏi nguồn Run mới | Không | Tích |

### Giá nhà cung cấp — SupplierPriceForm

Nguồn: [form](../../apps/master_data/forms.py), [validator](../../apps/master_data/validators.py), [model](../../apps/core/models.py), [service](../../apps/master_data/services.py), [resolver giá](../../apps/costing/engine/resolvers/prices.py). Menu **Giá nhà cung cấp**, nút **Lưu giá nhà cung cấp**. Tạo mới luôn DRAFT; sửa giữ status/created_at; status không phải input. Nhóm Thuế luôn hiện, không đổi validation required theo checkbox đã gồm thuế.

#### Form tạo mới

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhà cung cấp | supplier | Đối tác báo giá; dropdown | Có | Có | Trống | Tham chiếu hợp lệ | Supplier đang hoạt động, mã — tên | SUP_COFFEE |
| Vật tư / Hàng hóa | item | Item được báo giá; dropdown | Có | Có | Trống | Tham chiếu hợp lệ | Item đang hoạt động, mã — tên | RM_COFFEE |
| Đơn vị tính | price_uom | Đơn vị trên báo giá; dropdown | Có | Có | Trống | Không tự quy đổi, không bị giới hạn vào purchase_uom của Item | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg) |
| Tiền tệ | currency_code | Đồng tiền báo giá; dropdown | Có | Có | Trống | Không tự lấy mặc định từ Supplier | Currency đang hoạt động, mã — tên | VND |
| Số lượng tối thiểu | min_qty | Ngưỡng số lượng theo price_uom; Decimal(24,8) | Có | Có | 0 | Hữu hạn ≥0; default không có nghĩa được để trống | Không | 0 |
| Đơn giá | unit_price | Tiền trên một price_uom; Decimal(24,8) | Có | Có | Trống | Hữu hạn ≥0; giá 0 được lưu | Kết hợp currency_code + price_uom | 100000 |
| Đơn giá đã gồm thuế | tax_inclusive | Mô tả giá gộp; checkbox | Không | Có | Không tích | Boolean; nếu tích Costing hiện báo UNSUPPORTED_TAX | Không | Không tích cho nguồn giá chưa thuế |
| Tỷ lệ thuế | tax_rate | Tỷ lệ của báo giá; Decimal(12,8) | Không | Có | Trống | Hữu hạn 0–1; nhập phân số, không nhập phần trăm nguyên; khác 0 chưa được Costing hỗ trợ | Không | 0.1 = 10% |
| Tỷ lệ thuế được khấu trừ | tax_recoverable_ratio | Phần thuế được khấu trừ; Decimal(12,8) | Có | Có | 1 | Hữu hạn 0–1; phải giữ/nhập giá trị khi lưu, chưa có xử lý thuế mua trong engine | Không | 1 |
| Hiệu lực từ ngày | effective_from | Ngày bắt đầu giá; date | Có | Có | Ngày hiện tại theo múi giờ ứng dụng | Ngày hợp lệ | Không | 2026-01-01 |
| Hiệu lực đến ngày | effective_to | Ngày cuối giá; date | Không | Có | Trống = vô hạn | Nếu nhập phải >start; Costing gồm cả ngày cuối | Không | 2026-06-30 |
| Nguồn dữ liệu | source_type | Loại nguồn khai báo; text ≤50 | Không | Có | Trống | Trim; trống null; text tự do, không enum | Nhập trực tiếp | Báo giá |
| Tham chiếu / Số báo giá | source_reference | Căn cứ giá; textarea | Không | Có | Trống | Trim; trống null | Nhập trực tiếp | BG-2026-101 |

#### Form chỉnh sửa

Sửa chính bản giá đang mở; giữ status/ngày tạo, không tạo version và không sửa giá kỳ khác. Các trường đều sửa được bất kể status; giữ được chính tham chiếu cũ ngừng hoạt động. Không có nút đổi status.

| Field UI | Model field | Ý nghĩa / Kiểu dữ liệu | Required | Editable | Default | Validation | Dependency / Nguồn lựa chọn | Example |
|---|---|---|---|---|---|---|---|---|
| Nhà cung cấp | supplier | Đối tác báo giá; dropdown | Có | Có | Giá trị hiện có | Tham chiếu hợp lệ | Supplier đang hoạt động, mã — tên | SUP_COFFEE |
| Vật tư / Hàng hóa | item | Item được báo giá; dropdown | Có | Có | Giá trị hiện có | Tham chiếu hợp lệ | Item đang hoạt động, mã — tên | RM_COFFEE |
| Đơn vị tính | price_uom | Đơn vị trên báo giá; dropdown | Có | Có | Giá trị hiện có | Không tự quy đổi, không bị giới hạn vào purchase_uom của Item | Uom đang hoạt động, tên (ký hiệu) | Kilôgam (kg) |
| Tiền tệ | currency_code | Đồng tiền báo giá; dropdown | Có | Có | Giá trị hiện có | Không tự lấy mặc định từ Supplier | Currency đang hoạt động, mã — tên | VND |
| Số lượng tối thiểu | min_qty | Ngưỡng số lượng theo price_uom; Decimal(24,8) | Có | Có | Giá trị hiện có | Hữu hạn ≥0; default không có nghĩa được để trống | Không | 0 |
| Đơn giá | unit_price | Tiền trên một price_uom; Decimal(24,8) | Có | Có | Giá trị hiện có | Hữu hạn ≥0; giá 0 được lưu | Kết hợp currency_code + price_uom | 100000 |
| Đơn giá đã gồm thuế | tax_inclusive | Mô tả giá gộp; checkbox | Không | Có | Giá trị hiện có | Boolean; nếu tích Costing hiện báo UNSUPPORTED_TAX | Không | Không tích cho nguồn giá chưa thuế |
| Tỷ lệ thuế | tax_rate | Tỷ lệ của báo giá; Decimal(12,8) | Không | Có | Giá trị hiện có | Hữu hạn 0–1; nhập phân số, không nhập phần trăm nguyên; khác 0 chưa được Costing hỗ trợ | Không | 0.1 = 10% |
| Tỷ lệ thuế được khấu trừ | tax_recoverable_ratio | Phần thuế được khấu trừ; Decimal(12,8) | Có | Có | Giá trị hiện có | Hữu hạn 0–1; phải giữ/nhập giá trị khi lưu, chưa có xử lý thuế mua trong engine | Không | 1 |
| Hiệu lực từ ngày | effective_from | Ngày bắt đầu giá; date | Có | Có | Giá trị hiện có | Ngày hợp lệ | Không | 2026-01-01 |
| Hiệu lực đến ngày | effective_to | Ngày cuối giá; date | Không | Có | Giá trị hiện có | Nếu nhập phải >start; Costing gồm cả ngày cuối | Không | 2026-06-30 |
| Nguồn dữ liệu | source_type | Loại nguồn khai báo; text ≤50 | Không | Có | Giá trị hiện có | Trim; trống null; text tự do, không enum | Nhập trực tiếp | Báo giá |
| Tham chiếu / Số báo giá | source_reference | Căn cứ giá; textarea | Không | Có | Giá trị hiện có | Trim; trống null | Nhập trực tiếp | BG-2026-101 |

### Trường chỉ đọc / tự sinh nhìn thấy ngoài form

Ngày tạo/cập nhật trên chi tiết Product/Category/Item/SKU/Supplier; ngày tạo trên chi tiết SupplierPrice; ngày tạo/cập nhật trong ngăn **Thông tin bản ghi** của CostElement do hệ thống ghi. Currency/UomCategory/Uom/Conversion detail không hiển thị đầy đủ timestamp của model. SupplierPrice hiển thị trạng thái bản ghi và trạng thái theo hôm nay; trạng thái ngày là computed, không lưu thay status. Những thông tin này không phải ô nhập. Không expose JSON attributes/metadata, nhóm cha hoặc compatibility fields.

## Nhóm trường sản xuất

**[HỆ THỐNG HIỆN TẠI]** 15 form cụ thể, 104 trường riêng biệt, 30 bảng tạo/sửa. Checkbox không bắt buộc đánh dấu nghĩa là có thể bỏ chọn. Trường điều kiện vẫn hiện trên form; backend kiểm tra khi lưu. Dropdown Routing đổi theo Trung tâm bằng HTMX.

Tạo mới BOM/Bao bì/Quy trình gồm thông tin header **và** form phiên bản đầu trên cùng màn hình. Bảng phiên bản bên dưới áp dụng cả phần nhúng đó. Sửa header chỉ sửa header; muốn sửa phiên bản phải mở thao tác riêng. Mỗi bảng sửa có cùng trường với bảng tạo nhưng dùng giá trị đang lưu và điều kiện khóa khác.

Khi chọn mới danh mục, chỉ dùng bản hoạt động; khi sửa giữ tham chiếu cũ đã ngừng để bảo toàn lịch sử. Giữ được trên form không bảo đảm engine chấp nhận nguồn đã ngừng hoạt động. Ngày kết thúc sản xuất/Costing bao gồm chính ngày ấy. Nhập ngày không thay Nháp thành Đang hiệu lực.

## BOM / Thông tin định mức

Nguồn: [apps/bom/forms.py](../../apps/bom/forms.py) → `RecipeForm`, model `Recipe`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu định mức nguyên vật liệu**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản phẩm | `Recipe.product` | Sản phẩm đầu ra mà cấu hình này phục vụ | Danh mục chọn | Có | Có | Trống | Chọn Sản phẩm đang hoạt động; giữ tham chiếu cũ khi đã ngừng. BOM/Quy trình khóa Sản phẩm nếu có phiên bản chốt; Bao bì khóa thêm khi đã gán SKU. | Product đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SP_CAPPUCCINO |
| Mã định mức | `Recipe.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên định mức | `Recipe.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Mô tả | `Recipe.description` | Diễn giải mục đích hoặc phạm vi sử dụng | Văn bản | Không | Có | Trống | Tùy chọn; không dùng nội dung mô tả làm quy tắc tính. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Mẻ sản xuất tiêu chuẩn |
| Đang hoạt động | `Recipe.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Được chọn | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

### Form chỉnh sửa

Trang: `/bom/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản phẩm | `Recipe.product` | Sản phẩm đầu ra mà cấu hình này phục vụ | Danh mục chọn | Có | Khóa nếu có bản chốt | Giá trị đã lưu | Chọn Sản phẩm đang hoạt động; giữ tham chiếu cũ khi đã ngừng. BOM/Quy trình khóa Sản phẩm nếu có phiên bản chốt; Bao bì khóa thêm khi đã gán SKU. | Product đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SP_CAPPUCCINO |
| Mã định mức | `Recipe.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên định mức | `Recipe.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Mô tả | `Recipe.description` | Diễn giải mục đích hoặc phạm vi sử dụng | Văn bản | Không | Có | Giá trị đã lưu | Tùy chọn; không dùng nội dung mô tả làm quy tắc tính. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Mẻ sản xuất tiêu chuẩn |
| Đang hoạt động | `Recipe.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Giá trị đã lưu | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

## BOM / Phiên bản

Nguồn: [apps/bom/forms.py](../../apps/bom/forms.py) → `RecipeVersionForm`, model `RecipeVersion`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu phiên bản định mức**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/{id}/versions/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản lượng chuẩn | `RecipeVersion.output_qty` | Sản lượng làm cơ sở cho toàn bộ dòng định mức | Số thập phân (24,8) | Có | Có | Trống | Phải > 0; cùng Đơn vị tính đầu ra xác định cơ sở quy mô. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đơn vị tính đầu ra | `RecipeVersion.output_uom` | Đơn vị của Sản lượng chuẩn | Danh mục chọn | Có | Có | Trống | Đơn vị hoạt động; không tự bằng đơn vị của SKU hoặc vật tư đầu vào. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Tỷ lệ thu hồi (%) | `RecipeVersion.yield_rate` | Tỷ lệ thu hồi sản xuất dùng riêng với hao hụt dòng | Số phần trăm; ≤ 6 số lẻ | Có | Có | 100% (tỷ lệ lưu 1) | UI > 0 và ≤ 100%; tối đa 6 chữ số lẻ; lưu tỷ lệ chia 100 chính xác. | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 98 |
| Hiệu lực từ ngày | `RecipeVersion.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có điều kiện: khi đã nhập ngày kết thúc | Có | Trống | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `RecipeVersion.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Trống | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Lý do thay đổi | `RecipeVersion.change_reason` | Lý do tạo hoặc sửa phiên bản | Văn bản | Không | Có | Trống | Tùy chọn; sao chép giữ nội dung nguồn nếu không sửa; nên mô tả thay đổi thực tế. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Đổi định mức từ tháng 11 |

### Form chỉnh sửa

Trang: `/bom/{id}/versions/{v}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản lượng chuẩn | `RecipeVersion.output_qty` | Sản lượng làm cơ sở cho toàn bộ dòng định mức | Số thập phân (24,8) | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Phải > 0; cùng Đơn vị tính đầu ra xác định cơ sở quy mô. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đơn vị tính đầu ra | `RecipeVersion.output_uom` | Đơn vị của Sản lượng chuẩn | Danh mục chọn | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Đơn vị hoạt động; không tự bằng đơn vị của SKU hoặc vật tư đầu vào. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Tỷ lệ thu hồi (%) | `RecipeVersion.yield_rate` | Tỷ lệ thu hồi sản xuất dùng riêng với hao hụt dòng | Số phần trăm; ≤ 6 số lẻ | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | UI > 0 và ≤ 100%; tối đa 6 chữ số lẻ; lưu tỷ lệ chia 100 chính xác. | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 98 |
| Hiệu lực từ ngày | `RecipeVersion.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có điều kiện: khi đã nhập ngày kết thúc | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `RecipeVersion.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Lý do thay đổi | `RecipeVersion.change_reason` | Lý do tạo hoặc sửa phiên bản | Văn bản | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn; sao chép giữ nội dung nguồn nếu không sửa; nên mô tả thay đổi thực tế. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Đổi định mức từ tháng 11 |

### Tạo phiên bản từ bản nguồn

Thao tác **Tạo phiên bản mới từ phiên bản N** mở cùng form tạo phiên bản, điền các trường cấu hình/ngày/lý do từ nguồn. Có thể sửa trước khi lưu. Số phiên bản tự tăng, trạng thái luôn Nháp; sao chép toàn bộ dòng/công đoạn, không chỉ trang đang xem; nguồn không đổi. Không sao chép trạng thái đã chốt, actor hoặc hash. Bao bì không nhân bản liên kết SKU vì liên kết thuộc header. Nếu không chọn nguồn thì bản mới chưa có dòng/công đoạn.

## BOM / Thành phần

Nguồn: [apps/bom/forms.py](../../apps/bom/forms.py) → `RecipeLineForm`, model `RecipeLine`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu thành phần**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/{id}/versions/{v}/lines/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vật tư / Hàng hóa | `RecipeLine.component_item` | Vật tư đầu vào của dòng BOM | Danh mục chọn | Có | Có nếu phiên bản cha còn sửa được | Trống | Vật tư hoạt động; mọi loại Item được chọn; cho phép lặp vật tư nhiều dòng, engine cộng từng dòng. | Item đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | RM_COFFEE |
| Số lượng | `RecipeLine.qty` | Lượng vật tư của dòng trên cơ sở cấu hình | Số thập phân (24,8) | Có | Có nếu phiên bản cha còn sửa được | Trống | Phải > 0; không tự nhân hao hụt/cấp cha ở form. BOM theo Sản lượng chuẩn; Bao bì theo cơ sở do người chạy khai báo. | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 0.08333333 |
| Đơn vị tính | `RecipeLine.uom` | Đơn vị của lượng vật tư trên dòng | Danh mục chọn | Có | Có nếu phiên bản cha còn sửa được | Trống | Đơn vị hoạt động; khác đơn vị gốc vật tư cần quy đổi trực tiếp hai chiều phù hợp ngày bắt đầu phiên bản hoặc hôm nay. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | g |
| Tỷ lệ hao hụt (%) | `RecipeLine.scrap_rate` | Hao hụt riêng của dòng nguyên liệu | Số phần trăm; ≤ 6 số lẻ | Có | Có nếu phiên bản cha còn sửa được | 0% | UI ≥ 0 và < 100%; tối đa 6 chữ số lẻ; lưu tỷ lệ chia 100; engine chia nhu cầu cho (1 − hao hụt). | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 2 |
| Mã công đoạn | `RecipeLine.operation_code` | Mã công đoạn mô tả dòng BOM hoặc công đoạn Routing | Văn bản ≤ 100 ký tự | Không | Có nếu phiên bản cha còn sửa được | Trống | BOM: tùy chọn, bỏ khoảng trắng, giữ case, không FK Routing. Routing: bắt buộc, trim/chữ hoa; mã có thể lặp ở thứ tự khác. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | TRON |
| Nhóm thay thế | `RecipeLine.substitute_group` | Tên nhóm thay thế được ghi trên dòng BOM | Văn bản ≤ 100 ký tự | Không | Có nếu phiên bản cha còn sửa được | Trống | Văn bản tùy chọn, trim; chưa có engine chọn vật tư thay thế, có giá trị sẽ chặn Costing hiện tại. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Trống để tính theo cấu hình hỗ trợ |
| Thành phần tùy chọn | `RecipeLine.is_optional` | Đánh dấu thành phần có thể lựa chọn | Ô chọn Có/Không | Không | Có nếu phiên bản cha còn sửa được | Không chọn | Form cho lưu; nếu chọn thì Costing hiện tại chặn vì chưa có quy tắc chọn thành phần. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Không chọn |
| Thứ tự | `RecipeLine.display_order` | Thứ tự hiển thị dòng thành phần | Số nguyên | Có | Có nếu phiên bản cha còn sửa được | 0 | Số nguyên trong [−2147483648,2147483647]; có thể âm hoặc trùng; không tự tăng +10. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 10 |
| Ghi chú | `RecipeLine.notes` | Ghi chú bổ sung cho dòng hoặc công đoạn | Văn bản | Không | Có nếu phiên bản cha còn sửa được | Trống | Văn bản tùy chọn; không thực thi như công thức. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Kiểm tra cân trước khi trộn |

### Form chỉnh sửa

Trang: `/bom/{id}/versions/{v}/lines/{line}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vật tư / Hàng hóa | `RecipeLine.component_item` | Vật tư đầu vào của dòng BOM | Danh mục chọn | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Vật tư hoạt động; mọi loại Item được chọn; cho phép lặp vật tư nhiều dòng, engine cộng từng dòng. | Item đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | RM_COFFEE |
| Số lượng | `RecipeLine.qty` | Lượng vật tư của dòng trên cơ sở cấu hình | Số thập phân (24,8) | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Phải > 0; không tự nhân hao hụt/cấp cha ở form. BOM theo Sản lượng chuẩn; Bao bì theo cơ sở do người chạy khai báo. | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 0.08333333 |
| Đơn vị tính | `RecipeLine.uom` | Đơn vị của lượng vật tư trên dòng | Danh mục chọn | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Đơn vị hoạt động; khác đơn vị gốc vật tư cần quy đổi trực tiếp hai chiều phù hợp ngày bắt đầu phiên bản hoặc hôm nay. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | g |
| Tỷ lệ hao hụt (%) | `RecipeLine.scrap_rate` | Hao hụt riêng của dòng nguyên liệu | Số phần trăm; ≤ 6 số lẻ | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | UI ≥ 0 và < 100%; tối đa 6 chữ số lẻ; lưu tỷ lệ chia 100; engine chia nhu cầu cho (1 − hao hụt). | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 2 |
| Mã công đoạn | `RecipeLine.operation_code` | Mã công đoạn mô tả dòng BOM hoặc công đoạn Routing | Văn bản ≤ 100 ký tự | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | BOM: tùy chọn, bỏ khoảng trắng, giữ case, không FK Routing. Routing: bắt buộc, trim/chữ hoa; mã có thể lặp ở thứ tự khác. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | TRON |
| Nhóm thay thế | `RecipeLine.substitute_group` | Tên nhóm thay thế được ghi trên dòng BOM | Văn bản ≤ 100 ký tự | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Văn bản tùy chọn, trim; chưa có engine chọn vật tư thay thế, có giá trị sẽ chặn Costing hiện tại. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Trống để tính theo cấu hình hỗ trợ |
| Thành phần tùy chọn | `RecipeLine.is_optional` | Đánh dấu thành phần có thể lựa chọn | Ô chọn Có/Không | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Form cho lưu; nếu chọn thì Costing hiện tại chặn vì chưa có quy tắc chọn thành phần. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Không chọn |
| Thứ tự | `RecipeLine.display_order` | Thứ tự hiển thị dòng thành phần | Số nguyên | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Số nguyên trong [−2147483648,2147483647]; có thể âm hoặc trùng; không tự tăng +10. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 10 |
| Ghi chú | `RecipeLine.notes` | Ghi chú bổ sung cho dòng hoặc công đoạn | Văn bản | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Văn bản tùy chọn; không thực thi như công thức. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Kiểm tra cân trước khi trộn |

## Bao bì / Thông tin cấu hình

Nguồn: [apps/bom/packaging_forms.py](../../apps/bom/packaging_forms.py) → `PackagingConfigForm`, model `PackagingConfig`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu cấu hình bao bì**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/packaging/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản phẩm | `PackagingConfig.product` | Sản phẩm đầu ra mà cấu hình này phục vụ | Danh mục chọn | Có | Có | Trống | Chọn Sản phẩm đang hoạt động; giữ tham chiếu cũ khi đã ngừng. BOM/Quy trình khóa Sản phẩm nếu có phiên bản chốt; Bao bì khóa thêm khi đã gán SKU. | Product đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SP_CAPPUCCINO |
| Mã cấu hình | `PackagingConfig.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên cấu hình | `PackagingConfig.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Mô tả | `PackagingConfig.description` | Diễn giải mục đích hoặc phạm vi sử dụng | Văn bản | Không | Có | Trống | Tùy chọn; không dùng nội dung mô tả làm quy tắc tính. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Mẻ sản xuất tiêu chuẩn |
| Đang hoạt động | `PackagingConfig.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Được chọn | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

### Form chỉnh sửa

Trang: `/bom/packaging/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản phẩm | `PackagingConfig.product` | Sản phẩm đầu ra mà cấu hình này phục vụ | Danh mục chọn | Có | Khóa nếu có bản chốt hoặc đã gán SKU | Giá trị đã lưu | Chọn Sản phẩm đang hoạt động; giữ tham chiếu cũ khi đã ngừng. BOM/Quy trình khóa Sản phẩm nếu có phiên bản chốt; Bao bì khóa thêm khi đã gán SKU. | Product đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SP_CAPPUCCINO |
| Mã cấu hình | `PackagingConfig.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên cấu hình | `PackagingConfig.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Mô tả | `PackagingConfig.description` | Diễn giải mục đích hoặc phạm vi sử dụng | Văn bản | Không | Có | Giá trị đã lưu | Tùy chọn; không dùng nội dung mô tả làm quy tắc tính. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Mẻ sản xuất tiêu chuẩn |
| Đang hoạt động | `PackagingConfig.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Giá trị đã lưu | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

## Bao bì / Phiên bản

Nguồn: [apps/bom/packaging_forms.py](../../apps/bom/packaging_forms.py) → `PackagingVersionForm`, model `PackagingConfigVersion`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu phiên bản bao bì**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/packaging/{id}/versions/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hiệu lực từ ngày | `PackagingConfigVersion.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có điều kiện: khi đã nhập ngày kết thúc | Có | Trống | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `PackagingConfigVersion.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Trống | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Khối lượng tổng | `PackagingConfigVersion.gross_weight` | Khối lượng tổng của quy cách bao bì | Số thập phân (24,8) | Không | Có | Trống | Nếu nhập phải ≥ 0 và có Đơn vị trọng lượng thuộc MASS; số 0 vẫn cần đơn vị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 0.55 |
| Đơn vị trọng lượng | `PackagingConfigVersion.weight_uom` | Đơn vị đo Khối lượng tổng | Danh mục chọn | Có điều kiện: khi có Khối lượng tổng | Có | Trống | Chỉ đơn vị hoạt động thuộc đại lượng MASS; bắt buộc khi nhập Khối lượng tổng. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Chiều dài | `PackagingConfigVersion.length` | Chiều dài của quy cách | Số thập phân (24,8) | Không | Có | Trống | Nếu nhập phải ≥ 0; cần Đơn vị kích thước thuộc LENGTH. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 30 |
| Chiều rộng | `PackagingConfigVersion.width` | Chiều rộng của quy cách | Số thập phân (24,8) | Không | Có | Trống | Nếu nhập phải ≥ 0; cần Đơn vị kích thước thuộc LENGTH. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 20 |
| Chiều cao | `PackagingConfigVersion.height` | Chiều cao của quy cách | Số thập phân (24,8) | Không | Có | Trống | Nếu nhập phải ≥ 0; cần Đơn vị kích thước thuộc LENGTH. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 15 |
| Đơn vị kích thước | `PackagingConfigVersion.dimension_uom` | Đơn vị dùng chung cho chiều dài/rộng/cao | Danh mục chọn | Có điều kiện: khi có ít nhất một kích thước | Có | Trống | Chỉ đơn vị hoạt động thuộc LENGTH; bắt buộc khi nhập bất kỳ kích thước nào. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | cm |
| Lý do thay đổi | `PackagingConfigVersion.change_reason` | Lý do tạo hoặc sửa phiên bản | Văn bản | Không | Có | Trống | Tùy chọn; sao chép giữ nội dung nguồn nếu không sửa; nên mô tả thay đổi thực tế. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Đổi định mức từ tháng 11 |

### Form chỉnh sửa

Trang: `/bom/packaging/{id}/versions/{v}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hiệu lực từ ngày | `PackagingConfigVersion.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có điều kiện: khi đã nhập ngày kết thúc | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `PackagingConfigVersion.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Khối lượng tổng | `PackagingConfigVersion.gross_weight` | Khối lượng tổng của quy cách bao bì | Số thập phân (24,8) | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Nếu nhập phải ≥ 0 và có Đơn vị trọng lượng thuộc MASS; số 0 vẫn cần đơn vị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 0.55 |
| Đơn vị trọng lượng | `PackagingConfigVersion.weight_uom` | Đơn vị đo Khối lượng tổng | Danh mục chọn | Có điều kiện: khi có Khối lượng tổng | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Chỉ đơn vị hoạt động thuộc đại lượng MASS; bắt buộc khi nhập Khối lượng tổng. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Chiều dài | `PackagingConfigVersion.length` | Chiều dài của quy cách | Số thập phân (24,8) | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Nếu nhập phải ≥ 0; cần Đơn vị kích thước thuộc LENGTH. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 30 |
| Chiều rộng | `PackagingConfigVersion.width` | Chiều rộng của quy cách | Số thập phân (24,8) | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Nếu nhập phải ≥ 0; cần Đơn vị kích thước thuộc LENGTH. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 20 |
| Chiều cao | `PackagingConfigVersion.height` | Chiều cao của quy cách | Số thập phân (24,8) | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Nếu nhập phải ≥ 0; cần Đơn vị kích thước thuộc LENGTH. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 15 |
| Đơn vị kích thước | `PackagingConfigVersion.dimension_uom` | Đơn vị dùng chung cho chiều dài/rộng/cao | Danh mục chọn | Có điều kiện: khi có ít nhất một kích thước | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Chỉ đơn vị hoạt động thuộc LENGTH; bắt buộc khi nhập bất kỳ kích thước nào. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | cm |
| Lý do thay đổi | `PackagingConfigVersion.change_reason` | Lý do tạo hoặc sửa phiên bản | Văn bản | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn; sao chép giữ nội dung nguồn nếu không sửa; nên mô tả thay đổi thực tế. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Đổi định mức từ tháng 11 |

### Tạo phiên bản từ bản nguồn

Thao tác **Tạo phiên bản mới từ phiên bản N** mở cùng form tạo phiên bản, điền các trường cấu hình/ngày/lý do từ nguồn. Có thể sửa trước khi lưu. Số phiên bản tự tăng, trạng thái luôn Nháp; sao chép toàn bộ dòng/công đoạn, không chỉ trang đang xem; nguồn không đổi. Không sao chép trạng thái đã chốt, actor hoặc hash. Bao bì không nhân bản liên kết SKU vì liên kết thuộc header. Nếu không chọn nguồn thì bản mới chưa có dòng/công đoạn.

## Bao bì / Thành phần

Nguồn: [apps/bom/packaging_forms.py](../../apps/bom/packaging_forms.py) → `PackagingLineForm`, model `PackagingLine`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu thành phần bao bì**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/packaging/{id}/versions/{v}/lines/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vật tư bao bì | `PackagingLine.packaging_item` | Vật tư dùng để đóng gói | Danh mục chọn | Có | Có nếu phiên bản cha còn sửa được | Trống | Vật tư hoạt động; ưu tiên loại Bao bì trong dropdown, vẫn cho các loại khác; cho phép vật tư lặp. | Item đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | PK_SACHET |
| Cấp đóng gói | `PackagingLine.level_code` | Cấp đóng gói của dòng | Lựa chọn mã có sẵn | Có | Có nếu phiên bản cha còn sửa được | Không đặt default dữ liệu; dropdown ban đầu là lựa chọn đầu | Chọn PRIMARY/SECONDARY/TERTIARY/PALLET/CONTAINER; nhãn Việt ở bảng lựa chọn bên dưới. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Cấp 1 · Bao bì trực tiếp |
| Số lượng | `PackagingLine.qty` | Lượng vật tư của dòng trên cơ sở cấu hình | Số thập phân (24,8) | Có | Có nếu phiên bản cha còn sửa được | Trống | Phải > 0; không tự nhân hao hụt/cấp cha ở form. BOM theo Sản lượng chuẩn; Bao bì theo cơ sở do người chạy khai báo. | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 0.08333333 |
| Đơn vị tính | `PackagingLine.uom` | Đơn vị của lượng vật tư trên dòng | Danh mục chọn | Có | Có nếu phiên bản cha còn sửa được | Trống | Đơn vị hoạt động; khác đơn vị gốc vật tư cần quy đổi trực tiếp hai chiều phù hợp ngày bắt đầu phiên bản hoặc hôm nay. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | g |
| Số đơn vị trong cấp cha | `PackagingLine.units_per_parent` | Số đơn vị nhỏ trong một cấp cha | Số thập phân (24,8) | Không | Có nếu phiên bản cha còn sửa được | Trống | Nếu nhập phải > 0; không bắt buộc số nguyên; chỉ mô tả, không tự nhân quantity. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 20 |
| Cấp cha | `PackagingLine.parent_level_code` | Cấp cha mô tả cấu trúc đóng gói | Văn bản ≤ 30 ký tự | Không | Có nếu phiên bản cha còn sửa được | Trống | Dropdown cấp đã biết hoặc Không có cấp cha; DB là văn bản, giữ giá trị cũ/legacy. Không FK dòng, không kiểm tra cây/chu trình. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Cấp 2 · Bao bì nhóm |
| Mã thị trường | `PackagingLine.market_code` | Mã thị trường gắn với dòng bao bì | Văn bản ≤ 50 ký tự | Không | Có nếu phiên bản cha còn sửa được | Trống | Trim; form lưu được, engine bao bì chưa có bộ chọn thị trường và chặn nếu có giá trị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Trống cho khả năng tính hiện tại |
| Mã mẫu thiết kế | `PackagingLine.artwork_code` | Mã mẫu thiết kế/in của dòng bao bì | Văn bản ≤ 120 ký tự | Không | Có nếu phiên bản cha còn sửa được | Trống | Trim; form lưu được, engine chưa có bộ chọn mẫu in và chặn nếu có giá trị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Trống cho khả năng tính hiện tại |
| Thứ tự | `PackagingLine.display_order` | Thứ tự hiển thị dòng thành phần | Số nguyên | Có | Có nếu phiên bản cha còn sửa được | 0 | Số nguyên trong [−2147483648,2147483647]; có thể âm hoặc trùng; không tự tăng +10. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 10 |
| Ghi chú | `PackagingLine.notes` | Ghi chú bổ sung cho dòng hoặc công đoạn | Văn bản | Không | Có nếu phiên bản cha còn sửa được | Trống | Văn bản tùy chọn; không thực thi như công thức. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Kiểm tra cân trước khi trộn |

### Form chỉnh sửa

Trang: `/bom/packaging/{id}/versions/{v}/lines/{line}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vật tư bao bì | `PackagingLine.packaging_item` | Vật tư dùng để đóng gói | Danh mục chọn | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Vật tư hoạt động; ưu tiên loại Bao bì trong dropdown, vẫn cho các loại khác; cho phép vật tư lặp. | Item đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | PK_SACHET |
| Cấp đóng gói | `PackagingLine.level_code` | Cấp đóng gói của dòng | Lựa chọn mã có sẵn | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Chọn PRIMARY/SECONDARY/TERTIARY/PALLET/CONTAINER; nhãn Việt ở bảng lựa chọn bên dưới. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Cấp 1 · Bao bì trực tiếp |
| Số lượng | `PackagingLine.qty` | Lượng vật tư của dòng trên cơ sở cấu hình | Số thập phân (24,8) | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Phải > 0; không tự nhân hao hụt/cấp cha ở form. BOM theo Sản lượng chuẩn; Bao bì theo cơ sở do người chạy khai báo. | Cơ sở sản lượng/đơn vị của phiên bản hoặc Run | 0.08333333 |
| Đơn vị tính | `PackagingLine.uom` | Đơn vị của lượng vật tư trên dòng | Danh mục chọn | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Đơn vị hoạt động; khác đơn vị gốc vật tư cần quy đổi trực tiếp hai chiều phù hợp ngày bắt đầu phiên bản hoặc hôm nay. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | g |
| Số đơn vị trong cấp cha | `PackagingLine.units_per_parent` | Số đơn vị nhỏ trong một cấp cha | Số thập phân (24,8) | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Nếu nhập phải > 0; không bắt buộc số nguyên; chỉ mô tả, không tự nhân quantity. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 20 |
| Cấp cha | `PackagingLine.parent_level_code` | Cấp cha mô tả cấu trúc đóng gói | Văn bản ≤ 30 ký tự | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Dropdown cấp đã biết hoặc Không có cấp cha; DB là văn bản, giữ giá trị cũ/legacy. Không FK dòng, không kiểm tra cây/chu trình. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Cấp 2 · Bao bì nhóm |
| Mã thị trường | `PackagingLine.market_code` | Mã thị trường gắn với dòng bao bì | Văn bản ≤ 50 ký tự | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Trim; form lưu được, engine bao bì chưa có bộ chọn thị trường và chặn nếu có giá trị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Trống cho khả năng tính hiện tại |
| Mã mẫu thiết kế | `PackagingLine.artwork_code` | Mã mẫu thiết kế/in của dòng bao bì | Văn bản ≤ 120 ký tự | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Trim; form lưu được, engine chưa có bộ chọn mẫu in và chặn nếu có giá trị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Trống cho khả năng tính hiện tại |
| Thứ tự | `PackagingLine.display_order` | Thứ tự hiển thị dòng thành phần | Số nguyên | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Số nguyên trong [−2147483648,2147483647]; có thể âm hoặc trùng; không tự tăng +10. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 10 |
| Ghi chú | `PackagingLine.notes` | Ghi chú bổ sung cho dòng hoặc công đoạn | Văn bản | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Văn bản tùy chọn; không thực thi như công thức. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Kiểm tra cân trước khi trộn |

## Bao bì / Liên kết SKU

Nguồn: [apps/bom/packaging_forms.py](../../apps/bom/packaging_forms.py) → `PackagingAssignmentForm`, model `SkuPackagingAssignment`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu liên kết SKU**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/packaging/{id}/skus/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SKU | `SkuPackagingAssignment.sku` | SKU bán hàng sử dụng cấu hình bao bì | Danh mục chọn | Có | Có | Trống | SKU hoạt động thuộc đúng Sản phẩm cấu hình; không lặp SKU+cấu hình+ngày bắt đầu. Assignment trỏ cấu hình, không trỏ version. | Sku đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SKU_CAPPUCCINO_BOX20 |
| Hiệu lực từ ngày | `SkuPackagingAssignment.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có | Có | Ngày hôm nay | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `SkuPackagingAssignment.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Trống | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Cấu hình chính | `SkuPackagingAssignment.is_primary` | Đánh dấu liên kết là cấu hình chính của SKU | Ô chọn Có/Không | Không | Có | Được chọn | Không tự bảo đảm duy nhất; Costing tìm đúng một liên kết chính tại ngày tính. | SKU và cấu hình thuộc cùng Sản phẩm; ngày liên kết | Chọn |

### Form chỉnh sửa

Trang: `/bom/packaging/{id}/skus/{assignment}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SKU | `SkuPackagingAssignment.sku` | SKU bán hàng sử dụng cấu hình bao bì | Danh mục chọn | Có | Có | Giá trị đã lưu | SKU hoạt động thuộc đúng Sản phẩm cấu hình; không lặp SKU+cấu hình+ngày bắt đầu. Assignment trỏ cấu hình, không trỏ version. | Sku đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SKU_CAPPUCCINO_BOX20 |
| Hiệu lực từ ngày | `SkuPackagingAssignment.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có | Có | Giá trị đã lưu | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `SkuPackagingAssignment.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Giá trị đã lưu | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Cấu hình chính | `SkuPackagingAssignment.is_primary` | Đánh dấu liên kết là cấu hình chính của SKU | Ô chọn Có/Không | Không | Có | Giá trị đã lưu | Không tự bảo đảm duy nhất; Costing tìm đúng một liên kết chính tại ngày tính. | SKU và cấu hình thuộc cùng Sản phẩm; ngày liên kết | Chọn |

Sửa cập nhật trực tiếp bản ghi, không tạo phiên bản. Không áp khóa phiên bản BOM lên form này. Đơn giá/quy tắc giữ trạng thái đang lưu; UI chưa có thao tác đưa bản mới Nháp vào hiệu lực. Liên kết SKU không có trường trạng thái riêng. Khi thay kỳ cần thêm bản ghi kỳ mới; Quy tắc phân bổ dùng mã mới để không trùng mã.

## Trung tâm sản xuất

Nguồn: [apps/bom/resource_forms.py](../../apps/bom/resource_forms.py) → `WorkCenterForm`, model `WorkCenter`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu trung tâm sản xuất**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/work-centers/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mã trung tâm sản xuất | `WorkCenter.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên trung tâm | `WorkCenter.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Mã địa điểm | `WorkCenter.site_code` | Mã địa điểm của trung tâm | Văn bản ≤ 100 ký tự | Không | Có | Trống | Trim; văn bản tùy chọn, không FK danh mục địa điểm. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | XUONG_A |
| Công suất | `WorkCenter.capacity_value` | Công suất được mô tả trên trung tâm/nguồn lực | Số thập phân (24,8) | Không | Có | Trống | Nếu nhập phải ≥ 0; cần Đơn vị công suất; không tự suy thời gian hoặc tạo số liệu kỳ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 120 |
| Đơn vị công suất | `WorkCenter.capacity_uom` | Đơn vị của các giá trị công suất | Danh mục chọn | Có điều kiện: khi có giá trị công suất | Có | Trống | Bắt buộc khi có Công suất hoặc Công suất bình thường; không giới hạn sẵn đại lượng TIME. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Công suất bình thường | `WorkCenter.normal_capacity_value` | Công suất bình thường mô tả của trung tâm | Số thập phân (24,8) | Không | Có | Trống | Nếu nhập phải ≥ 0 và có Đơn vị công suất; không bắt buộc nhỏ hơn Công suất; không tự thành CostPoolPeriod. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đang hoạt động | `WorkCenter.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Được chọn | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

### Form chỉnh sửa

Trang: `/bom/work-centers/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mã trung tâm sản xuất | `WorkCenter.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên trung tâm | `WorkCenter.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Mã địa điểm | `WorkCenter.site_code` | Mã địa điểm của trung tâm | Văn bản ≤ 100 ký tự | Không | Có | Giá trị đã lưu | Trim; văn bản tùy chọn, không FK danh mục địa điểm. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | XUONG_A |
| Công suất | `WorkCenter.capacity_value` | Công suất được mô tả trên trung tâm/nguồn lực | Số thập phân (24,8) | Không | Có | Giá trị đã lưu | Nếu nhập phải ≥ 0; cần Đơn vị công suất; không tự suy thời gian hoặc tạo số liệu kỳ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 120 |
| Đơn vị công suất | `WorkCenter.capacity_uom` | Đơn vị của các giá trị công suất | Danh mục chọn | Có điều kiện: khi có giá trị công suất | Có | Giá trị đã lưu | Bắt buộc khi có Công suất hoặc Công suất bình thường; không giới hạn sẵn đại lượng TIME. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Công suất bình thường | `WorkCenter.normal_capacity_value` | Công suất bình thường mô tả của trung tâm | Số thập phân (24,8) | Không | Có | Giá trị đã lưu | Nếu nhập phải ≥ 0 và có Đơn vị công suất; không bắt buộc nhỏ hơn Công suất; không tự thành CostPoolPeriod. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đang hoạt động | `WorkCenter.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Giá trị đã lưu | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

## Nguồn lực

Nguồn: [apps/bom/resource_forms.py](../../apps/bom/resource_forms.py) → `ResourceForm`, model `Resource`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu nguồn lực sản xuất**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/resources/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mã nguồn lực | `Resource.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên nguồn lực | `Resource.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Loại nguồn lực | `Resource.resource_type` | Phân loại nguồn lực | Lựa chọn mã có sẵn | Có | Có | Không đặt default dữ liệu; dropdown ban đầu là lựa chọn đầu | Chọn MACHINE/LABOR/WORK_CENTER/SERVICE; không có ENERGY/FACILITY trong lựa chọn. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Máy móc |
| Trung tâm sản xuất | `Resource.work_center` | Trung tâm mà nguồn lực/công đoạn thuộc về | Danh mục chọn | Không | Có | Trống | Tùy chọn. Routing chọn trung tâm sẽ tải lại Nguồn lực chính; cho nguồn lực cùng trung tâm hoặc dùng chung. | WorkCenter đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | WC_TRON |
| Công suất | `Resource.capacity_value` | Công suất được mô tả trên trung tâm/nguồn lực | Số thập phân (24,8) | Không | Có | Trống | Nếu nhập phải ≥ 0; cần Đơn vị công suất; không tự suy thời gian hoặc tạo số liệu kỳ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 120 |
| Đơn vị công suất | `Resource.capacity_uom` | Đơn vị của các giá trị công suất | Danh mục chọn | Có điều kiện: khi có giá trị công suất | Có | Trống | Bắt buộc khi có Công suất hoặc Công suất bình thường; không giới hạn sẵn đại lượng TIME. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Đang hoạt động | `Resource.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Được chọn | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

### Form chỉnh sửa

Trang: `/bom/resources/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mã nguồn lực | `Resource.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên nguồn lực | `Resource.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Loại nguồn lực | `Resource.resource_type` | Phân loại nguồn lực | Lựa chọn mã có sẵn | Có | Có | Giá trị đã lưu | Chọn MACHINE/LABOR/WORK_CENTER/SERVICE; không có ENERGY/FACILITY trong lựa chọn. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Máy móc |
| Trung tâm sản xuất | `Resource.work_center` | Trung tâm mà nguồn lực/công đoạn thuộc về | Danh mục chọn | Không | Có | Giá trị đã lưu | Tùy chọn. Routing chọn trung tâm sẽ tải lại Nguồn lực chính; cho nguồn lực cùng trung tâm hoặc dùng chung. | WorkCenter đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | WC_TRON |
| Công suất | `Resource.capacity_value` | Công suất được mô tả trên trung tâm/nguồn lực | Số thập phân (24,8) | Không | Có | Giá trị đã lưu | Nếu nhập phải ≥ 0; cần Đơn vị công suất; không tự suy thời gian hoặc tạo số liệu kỳ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 120 |
| Đơn vị công suất | `Resource.capacity_uom` | Đơn vị của các giá trị công suất | Danh mục chọn | Có điều kiện: khi có giá trị công suất | Có | Giá trị đã lưu | Bắt buộc khi có Công suất hoặc Công suất bình thường; không giới hạn sẵn đại lượng TIME. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Đang hoạt động | `Resource.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Giá trị đã lưu | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

## Đơn giá nguồn lực

Nguồn: [apps/bom/resource_forms.py](../../apps/bom/resource_forms.py) → `ResourceRateForm`, model `ResourceRate`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu đơn giá nguồn lực**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/resource-rates/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nguồn lực | `ResourceRate.resource` | Nguồn lực được áp dụng mức giá này | Danh mục chọn | Có | Có | Trống; chọn sẵn nếu vào từ Thêm đơn giá ở Nguồn lực | Nguồn lực hoạt động; quan hệ trung tâm hợp lệ. Từ Thêm đơn giá ở chi tiết có thể chọn sẵn. | Resource đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | MAY_TRON |
| Mã loại đơn giá | `ResourceRate.rate_type` | Mã nghiệp vụ phân loại đơn giá | Văn bản ≤ 50 ký tự | Có | Có | Trống | Văn bản tự nhập, trim, giữ case; không enum/FK. Engine chưa chọn theo loại này: nhiều rate hiệu lực gây mơ hồ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | STANDARD |
| Đơn giá | `ResourceRate.amount` | Tiền phải trả trên một Đơn vị tính giá | Số thập phân (24,8) | Có | Có | Trống | Phải ≥ 0; giá 0 hợp lệ. Không tự quy đổi tiền; tiền tệ rate phải cùng Run trong resolver hiện tại. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 120000 |
| Tiền tệ | `ResourceRate.currency_code` | Tiền tệ của mức đơn giá | Danh mục chọn | Có | Có | Trống | Chọn Tiền tệ đang hoạt động; không tự lấy từ nguồn lực. Model FK currency_code; cột DB cũng currency_code. | Tiền tệ đã có và hoạt động | VND |
| Đơn vị tính giá | `ResourceRate.per_uom` | Một đơn vị sử dụng ứng với Đơn giá | Danh mục chọn | Có | Có | Trống | Đơn vị hoạt động; form không ép TIME. Khi tính công đoạn cần quy đổi được với đơn vị thời gian. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | Giờ |
| Hiệu lực từ ngày | `ResourceRate.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có | Có | Ngày hôm nay | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `ResourceRate.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Trống | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Nguồn dữ liệu / Tham chiếu | `ResourceRate.source_reference` | Nguồn bảng đơn giá hoặc căn cứ nhập | Văn bản | Không | Có | Trống | Văn bản tùy chọn, trim; không phải đường dẫn bắt buộc hoặc tệp đính kèm. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Bảng giá tháng 10/2026 |

### Form chỉnh sửa

Trang: `/bom/resource-rates/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nguồn lực | `ResourceRate.resource` | Nguồn lực được áp dụng mức giá này | Danh mục chọn | Có | Có | Giá trị đã lưu | Nguồn lực hoạt động; quan hệ trung tâm hợp lệ. Từ Thêm đơn giá ở chi tiết có thể chọn sẵn. | Resource đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | MAY_TRON |
| Mã loại đơn giá | `ResourceRate.rate_type` | Mã nghiệp vụ phân loại đơn giá | Văn bản ≤ 50 ký tự | Có | Có | Giá trị đã lưu | Văn bản tự nhập, trim, giữ case; không enum/FK. Engine chưa chọn theo loại này: nhiều rate hiệu lực gây mơ hồ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | STANDARD |
| Đơn giá | `ResourceRate.amount` | Tiền phải trả trên một Đơn vị tính giá | Số thập phân (24,8) | Có | Có | Giá trị đã lưu | Phải ≥ 0; giá 0 hợp lệ. Không tự quy đổi tiền; tiền tệ rate phải cùng Run trong resolver hiện tại. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 120000 |
| Tiền tệ | `ResourceRate.currency_code` | Tiền tệ của mức đơn giá | Danh mục chọn | Có | Có | Giá trị đã lưu | Chọn Tiền tệ đang hoạt động; không tự lấy từ nguồn lực. Model FK currency_code; cột DB cũng currency_code. | Tiền tệ đã có và hoạt động | VND |
| Đơn vị tính giá | `ResourceRate.per_uom` | Một đơn vị sử dụng ứng với Đơn giá | Danh mục chọn | Có | Có | Giá trị đã lưu | Đơn vị hoạt động; form không ép TIME. Khi tính công đoạn cần quy đổi được với đơn vị thời gian. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | Giờ |
| Hiệu lực từ ngày | `ResourceRate.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có | Có | Giá trị đã lưu | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `ResourceRate.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Giá trị đã lưu | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Nguồn dữ liệu / Tham chiếu | `ResourceRate.source_reference` | Nguồn bảng đơn giá hoặc căn cứ nhập | Văn bản | Không | Có | Giá trị đã lưu | Văn bản tùy chọn, trim; không phải đường dẫn bắt buộc hoặc tệp đính kèm. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Bảng giá tháng 10/2026 |

Sửa cập nhật trực tiếp bản ghi, không tạo phiên bản. Không áp khóa phiên bản BOM lên form này. Đơn giá/quy tắc giữ trạng thái đang lưu; UI chưa có thao tác đưa bản mới Nháp vào hiệu lực. Liên kết SKU không có trường trạng thái riêng. Khi thay kỳ cần thêm bản ghi kỳ mới; Quy tắc phân bổ dùng mã mới để không trùng mã.

## Quy trình / Thông tin

Nguồn: [apps/bom/routing_forms.py](../../apps/bom/routing_forms.py) → `RoutingForm`, model `Routing`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu quy trình sản xuất**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/routings/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản phẩm | `Routing.product` | Sản phẩm đầu ra mà cấu hình này phục vụ | Danh mục chọn | Có | Có | Trống | Chọn Sản phẩm đang hoạt động; giữ tham chiếu cũ khi đã ngừng. BOM/Quy trình khóa Sản phẩm nếu có phiên bản chốt; Bao bì khóa thêm khi đã gán SKU. | Product đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SP_CAPPUCCINO |
| Mã quy trình | `Routing.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên quy trình | `Routing.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Đang hoạt động | `Routing.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Được chọn | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

### Form chỉnh sửa

Trang: `/bom/routings/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản phẩm | `Routing.product` | Sản phẩm đầu ra mà cấu hình này phục vụ | Danh mục chọn | Có | Khóa nếu có bản chốt | Giá trị đã lưu | Chọn Sản phẩm đang hoạt động; giữ tham chiếu cũ khi đã ngừng. BOM/Quy trình khóa Sản phẩm nếu có phiên bản chốt; Bao bì khóa thêm khi đã gán SKU. | Product đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | SP_CAPPUCCINO |
| Mã quy trình | `Routing.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên quy trình | `Routing.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Đang hoạt động | `Routing.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Giá trị đã lưu | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

## Quy trình / Phiên bản

Nguồn: [apps/bom/routing_forms.py](../../apps/bom/routing_forms.py) → `RoutingVersionForm`, model `RoutingVersion`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu phiên bản quy trình**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/routings/{id}/versions/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản lượng lô chuẩn | `RoutingVersion.batch_size` | Sản lượng lô dùng làm cơ sở chung của quy trình | Số thập phân (24,8) | Có điều kiện: khi đã chọn Đơn vị tính sản lượng lô | Có | Trống | Tùy chọn cặp với batch_uom; nếu nhập phải > 0; chọn unit mà thiếu lượng cũng lỗi. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đơn vị tính sản lượng lô | `RoutingVersion.batch_uom` | Đơn vị của Sản lượng lô chuẩn | Danh mục chọn | Có điều kiện: khi nhập Sản lượng lô chuẩn | Có | Trống | Tùy chọn nhưng bắt buộc cùng cặp batch_size; đơn vị hoạt động. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Hiệu lực từ ngày | `RoutingVersion.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có điều kiện: khi đã nhập ngày kết thúc | Có | Trống | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `RoutingVersion.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Trống | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Lý do thay đổi | `RoutingVersion.change_reason` | Lý do tạo hoặc sửa phiên bản | Văn bản | Không | Có | Trống | Tùy chọn; sao chép giữ nội dung nguồn nếu không sửa; nên mô tả thay đổi thực tế. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Đổi định mức từ tháng 11 |

### Form chỉnh sửa

Trang: `/bom/routings/{id}/versions/{v}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sản lượng lô chuẩn | `RoutingVersion.batch_size` | Sản lượng lô dùng làm cơ sở chung của quy trình | Số thập phân (24,8) | Có điều kiện: khi đã chọn Đơn vị tính sản lượng lô | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn cặp với batch_uom; nếu nhập phải > 0; chọn unit mà thiếu lượng cũng lỗi. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đơn vị tính sản lượng lô | `RoutingVersion.batch_uom` | Đơn vị của Sản lượng lô chuẩn | Danh mục chọn | Có điều kiện: khi nhập Sản lượng lô chuẩn | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn nhưng bắt buộc cùng cặp batch_size; đơn vị hoạt động. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Hiệu lực từ ngày | `RoutingVersion.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có điều kiện: khi đã nhập ngày kết thúc | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `RoutingVersion.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |
| Lý do thay đổi | `RoutingVersion.change_reason` | Lý do tạo hoặc sửa phiên bản | Văn bản | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn; sao chép giữ nội dung nguồn nếu không sửa; nên mô tả thay đổi thực tế. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Đổi định mức từ tháng 11 |

### Tạo phiên bản từ bản nguồn

Thao tác **Tạo phiên bản mới từ phiên bản N** mở cùng form tạo phiên bản, điền các trường cấu hình/ngày/lý do từ nguồn. Có thể sửa trước khi lưu. Số phiên bản tự tăng, trạng thái luôn Nháp; sao chép toàn bộ dòng/công đoạn, không chỉ trang đang xem; nguồn không đổi. Không sao chép trạng thái đã chốt, actor hoặc hash. Bao bì không nhân bản liên kết SKU vì liên kết thuộc header. Nếu không chọn nguồn thì bản mới chưa có dòng/công đoạn.

## Quy trình / Công đoạn

Nguồn: [apps/bom/routing_forms.py](../../apps/bom/routing_forms.py) → `RoutingOperationForm`, model `RoutingOperation`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu công đoạn**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/routings/{id}/versions/{v}/operations/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Thứ tự công đoạn | `RoutingOperation.sequence_no` | Thứ tự thực hiện công đoạn | Số nguyên | Có | Có nếu phiên bản cha còn sửa được | Thứ tự lớn nhất +10; đầu tiên 10 | Số nguyên [1,2147483647], duy nhất trong phiên bản; gợi ý max+10, bảng luôn sắp theo thứ tự. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 10 |
| Mã công đoạn | `RoutingOperation.operation_code` | Mã công đoạn mô tả dòng BOM hoặc công đoạn Routing | Văn bản ≤ 100 ký tự | Có | Có nếu phiên bản cha còn sửa được | Trống | BOM: tùy chọn, bỏ khoảng trắng, giữ case, không FK Routing. Routing: bắt buộc, trim/chữ hoa; mã có thể lặp ở thứ tự khác. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | TRON |
| Tên công đoạn | `RoutingOperation.operation_name` | Tên công việc của công đoạn | Văn bản ≤ 255 ký tự | Có | Có nếu phiên bản cha còn sửa được | Trống | Trim; phải có giá trị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Phối trộn |
| Trung tâm sản xuất | `RoutingOperation.work_center` | Trung tâm mà nguồn lực/công đoạn thuộc về | Danh mục chọn | Không | Có nếu phiên bản cha còn sửa được | Trống | Tùy chọn. Routing chọn trung tâm sẽ tải lại Nguồn lực chính; cho nguồn lực cùng trung tâm hoặc dùng chung. | WorkCenter đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | WC_TRON |
| Nguồn lực chính | `RoutingOperation.primary_resource` | Một nguồn lực chính dùng cho công đoạn | Danh mục chọn | Không | Có nếu phiên bản cha còn sửa được | Trống | Form tùy chọn; thực thi thời gian khác 0 cần có. Thuộc trung tâm được chọn hoặc dùng chung; nguồn lực có trung tâm cần công đoạn cùng trung tâm khi tính. | Resource đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | MAY_TRON |
| Thời gian thiết lập | `RoutingOperation.setup_time` | Thời gian chuẩn bị tính một lần cho mỗi Run | Số thập phân (24,8) | Có | Có nếu phiên bản cha còn sửa được | 0 | Bắt buộc có số, mặc định 0; ≥ 0; khác 0 cần TIME UoM. Không tự nhân với sản lượng. | TIME UoM; nguồn lực/đơn giá/cơ sở khi tính Run | 15 |
| Thời gian chạy | `RoutingOperation.run_time` | Thời gian chạy cho một sản lượng cơ sở | Số thập phân (24,8) | Có | Có nếu phiên bản cha còn sửa được | 0 | Bắt buộc có số, mặc định 0; ≥ 0; khác 0 cần TIME UoM. Khi tính dùng cơ sở công đoạn hoặc lô. | TIME UoM; nguồn lực/đơn giá/cơ sở khi tính Run | 30 |
| Đơn vị thời gian | `RoutingOperation.time_uom` | Đơn vị chung của hai thời gian | Danh mục chọn | Có điều kiện: khi một thời gian khác 0 | Có nếu phiên bản cha còn sửa được | Trống | Tùy chọn khi cả hai thời gian 0; khác 0 bắt buộc. Dropdown chỉ đại lượng TIME. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | Phút |
| Sản lượng cơ sở | `RoutingOperation.quantity_basis` | Sản lượng riêng mà thời gian chạy công đoạn ứng với | Số thập phân (24,8) | Có điều kiện: khi đã chọn Đơn vị tính sản lượng cơ sở | Có nếu phiên bản cha còn sửa được | Trống | Tùy chọn cặp quantity_uom; > 0 khi nhập; nếu trống engine dùng cơ sở lô. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đơn vị tính sản lượng cơ sở | `RoutingOperation.quantity_uom` | Đơn vị của Sản lượng cơ sở công đoạn | Danh mục chọn | Có điều kiện: khi nhập Sản lượng cơ sở | Có nếu phiên bản cha còn sửa được | Trống | Bắt buộc khi nhập quantity_basis; chọn unit mà thiếu lượng cũng lỗi. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Ghi chú | `RoutingOperation.notes` | Ghi chú bổ sung cho dòng hoặc công đoạn | Văn bản | Không | Có nếu phiên bản cha còn sửa được | Trống | Văn bản tùy chọn; không thực thi như công thức. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Kiểm tra cân trước khi trộn |

### Form chỉnh sửa

Trang: `/bom/routings/{id}/versions/{v}/operations/{op}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Thứ tự công đoạn | `RoutingOperation.sequence_no` | Thứ tự thực hiện công đoạn | Số nguyên | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Số nguyên [1,2147483647], duy nhất trong phiên bản; gợi ý max+10, bảng luôn sắp theo thứ tự. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 10 |
| Mã công đoạn | `RoutingOperation.operation_code` | Mã công đoạn mô tả dòng BOM hoặc công đoạn Routing | Văn bản ≤ 100 ký tự | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | BOM: tùy chọn, bỏ khoảng trắng, giữ case, không FK Routing. Routing: bắt buộc, trim/chữ hoa; mã có thể lặp ở thứ tự khác. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | TRON |
| Tên công đoạn | `RoutingOperation.operation_name` | Tên công việc của công đoạn | Văn bản ≤ 255 ký tự | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Trim; phải có giá trị. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Phối trộn |
| Trung tâm sản xuất | `RoutingOperation.work_center` | Trung tâm mà nguồn lực/công đoạn thuộc về | Danh mục chọn | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn. Routing chọn trung tâm sẽ tải lại Nguồn lực chính; cho nguồn lực cùng trung tâm hoặc dùng chung. | WorkCenter đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | WC_TRON |
| Nguồn lực chính | `RoutingOperation.primary_resource` | Một nguồn lực chính dùng cho công đoạn | Danh mục chọn | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Form tùy chọn; thực thi thời gian khác 0 cần có. Thuộc trung tâm được chọn hoặc dùng chung; nguồn lực có trung tâm cần công đoạn cùng trung tâm khi tính. | Resource đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | MAY_TRON |
| Thời gian thiết lập | `RoutingOperation.setup_time` | Thời gian chuẩn bị tính một lần cho mỗi Run | Số thập phân (24,8) | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Bắt buộc có số, mặc định 0; ≥ 0; khác 0 cần TIME UoM. Không tự nhân với sản lượng. | TIME UoM; nguồn lực/đơn giá/cơ sở khi tính Run | 15 |
| Thời gian chạy | `RoutingOperation.run_time` | Thời gian chạy cho một sản lượng cơ sở | Số thập phân (24,8) | Có | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Bắt buộc có số, mặc định 0; ≥ 0; khác 0 cần TIME UoM. Khi tính dùng cơ sở công đoạn hoặc lô. | TIME UoM; nguồn lực/đơn giá/cơ sở khi tính Run | 30 |
| Đơn vị thời gian | `RoutingOperation.time_uom` | Đơn vị chung của hai thời gian | Danh mục chọn | Có điều kiện: khi một thời gian khác 0 | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn khi cả hai thời gian 0; khác 0 bắt buộc. Dropdown chỉ đại lượng TIME. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | Phút |
| Sản lượng cơ sở | `RoutingOperation.quantity_basis` | Sản lượng riêng mà thời gian chạy công đoạn ứng với | Số thập phân (24,8) | Có điều kiện: khi đã chọn Đơn vị tính sản lượng cơ sở | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Tùy chọn cặp quantity_uom; > 0 khi nhập; nếu trống engine dùng cơ sở lô. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Đơn vị tính sản lượng cơ sở | `RoutingOperation.quantity_uom` | Đơn vị của Sản lượng cơ sở công đoạn | Danh mục chọn | Có điều kiện: khi nhập Sản lượng cơ sở | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Bắt buộc khi nhập quantity_basis; chọn unit mà thiếu lượng cũng lỗi. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | kg |
| Ghi chú | `RoutingOperation.notes` | Ghi chú bổ sung cho dòng hoặc công đoạn | Văn bản | Không | Có nếu DRAFT/IN_REVIEW; bản chốt chỉ đọc | Giá trị đã lưu | Văn bản tùy chọn; không thực thi như công thức. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Kiểm tra cân trước khi trộn |

## Nhóm chi phí chung

Nguồn: [apps/bom/overhead_forms.py](../../apps/bom/overhead_forms.py) → `CostPoolForm`, model `CostPool`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu nhóm chi phí chung**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/cost-pools/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mã nhóm chi phí | `CostPool.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên nhóm chi phí | `CostPool.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Loại nhóm chi phí | `CostPool.pool_type` | Loại nhóm tập hợp chi phí chung | Lựa chọn mã có sẵn | Có | Có | Trống | Chọn FACTORY_FIXED/FACTORY_VARIABLE/QA/WAREHOUSE/EXPORT/OTHER; không tự thêm tiền hay CE vào nhóm. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chi phí cố định nhà máy |
| Mô tả | `CostPool.description` | Diễn giải mục đích hoặc phạm vi sử dụng | Văn bản | Không | Có | Trống | Tùy chọn; không dùng nội dung mô tả làm quy tắc tính. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Mẻ sản xuất tiêu chuẩn |
| Đang hoạt động | `CostPool.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Được chọn | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

### Form chỉnh sửa

Trang: `/bom/cost-pools/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mã nhóm chi phí | `CostPool.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên nhóm chi phí | `CostPool.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Loại nhóm chi phí | `CostPool.pool_type` | Loại nhóm tập hợp chi phí chung | Lựa chọn mã có sẵn | Có | Có | Giá trị đã lưu | Chọn FACTORY_FIXED/FACTORY_VARIABLE/QA/WAREHOUSE/EXPORT/OTHER; không tự thêm tiền hay CE vào nhóm. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chi phí cố định nhà máy |
| Mô tả | `CostPool.description` | Diễn giải mục đích hoặc phạm vi sử dụng | Văn bản | Không | Có | Giá trị đã lưu | Tùy chọn; không dùng nội dung mô tả làm quy tắc tính. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Mẻ sản xuất tiêu chuẩn |
| Đang hoạt động | `CostPool.is_active` | Cho biết danh mục/header còn sử dụng | Ô chọn Có/Không | Không | Có | Giá trị đã lưu | Bỏ chọn khi đang hoạt động cần Xác nhận và lưu; không đổi trạng thái phiên bản hoặc xóa lịch sử. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Chọn |

## Quy tắc phân bổ

Nguồn: [apps/bom/overhead_forms.py](../../apps/bom/overhead_forms.py) → `AllocationRuleForm`, model `AllocationRule`; validators/services/views cùng nhóm; [kiểu/mặc định model](../../apps/core/models.py). Menu **Sản xuất**. Nút **Lưu quy tắc phân bổ**; **Hủy** không lưu.

### Form tạo mới

Trang: `/bom/allocation-rules/create/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nhóm chi phí | `AllocationRule.pool` | Nhóm chi phí mà quy tắc phân bổ sử dụng | Danh mục chọn | Có | Có | Trống; chọn sẵn nếu vào từ chi tiết Nhóm chi phí | Nhóm đang hoạt động; từ chi tiết nhóm chọn sẵn được. Quy tắc không có target Product/SKU riêng. | CostPool đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | POOL_FACTORY |
| Mã quy tắc | `AllocationRule.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên quy tắc | `AllocationRule.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Trống | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Tiêu thức phân bổ | `AllocationRule.basis_type` | Tiêu thức để chia chi phí chung | Lựa chọn mã có sẵn | Có | Có | Trống | Chọn một trong 10 mã dưới đây. Lưu cấu hình không bảo đảm thực thi; engine chỉ NORMAL_CAPACITY đủ điều kiện. | Nhóm chi phí; số liệu kỳ khi thực thi | Công suất bình thường |
| Đơn vị tiêu thức | `AllocationRule.basis_uom` | Đơn vị cơ sở phân bổ nếu khai báo | Danh mục chọn | Không | Có | Trống | Form tùy chọn, không ép chiều đo theo basis. NORMAL_CAPACITY nếu có phải trùng đơn vị công suất kỳ. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | Hộp |
| Mã công thức tham chiếu | `AllocationRule.formula_code` | Mã công thức tham chiếu của quy tắc | Văn bản ≤ 120 ký tự | Không | Có | Trống | Trim, giữ case; text không FK, không kiểm tra công thức tồn tại. Engine phân bổ hiện tại chặn khi có giá trị. | Không có FK; chỉ là mã text | Trống cho NORMAL_CAPACITY hiện tại |
| Mức ưu tiên | `AllocationRule.priority` | Mức ưu tiên được lưu trên quy tắc | Số nguyên | Có | Có | 100 | Số nguyên [−2147483648,2147483647]; cho số âm; chưa là chính sách chọn nhiều quy tắc trong Run. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Hiệu lực từ ngày | `AllocationRule.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có | Có | Ngày hôm nay | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `AllocationRule.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Trống | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |

### Form chỉnh sửa

Trang: `/bom/allocation-rules/{id}/edit/`.

| Field UI | Model field | Ý nghĩa | Kiểu | Required | Editable | Default / Giá trị mở form | Validation | Dependency / Nguồn chọn | Example |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nhóm chi phí | `AllocationRule.pool` | Nhóm chi phí mà quy tắc phân bổ sử dụng | Danh mục chọn | Có | Có | Giá trị đã lưu | Nhóm đang hoạt động; từ chi tiết nhóm chọn sẵn được. Quy tắc không có target Product/SKU riêng. | CostPool đã có; chọn mới chỉ bản hoạt động; giữ tham chiếu cũ ngừng hoạt động | POOL_FACTORY |
| Mã quy tắc | `AllocationRule.code` | Mã nhận biết bản ghi trong module | Văn bản ≤ 120 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối, chuyển chữ hoa; không trùng mã trong module, kể cả khác nhóm của Quy tắc phân bổ. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | BOM_CAPPUCCINO |
| Tên quy tắc | `AllocationRule.name` | Tên nghiệp vụ để tìm và nhận diện bản ghi | Văn bản ≤ 255 ký tự | Có | Có | Giá trị đã lưu | Bỏ khoảng trắng đầu/cuối; không được rỗng. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | Định mức Cappuccino |
| Tiêu thức phân bổ | `AllocationRule.basis_type` | Tiêu thức để chia chi phí chung | Lựa chọn mã có sẵn | Có | Có | Giá trị đã lưu | Chọn một trong 10 mã dưới đây. Lưu cấu hình không bảo đảm thực thi; engine chỉ NORMAL_CAPACITY đủ điều kiện. | Nhóm chi phí; số liệu kỳ khi thực thi | Công suất bình thường |
| Đơn vị tiêu thức | `AllocationRule.basis_uom` | Đơn vị cơ sở phân bổ nếu khai báo | Danh mục chọn | Không | Có | Giá trị đã lưu | Form tùy chọn, không ép chiều đo theo basis. NORMAL_CAPACITY nếu có phải trùng đơn vị công suất kỳ. | Đơn vị tính đã có và hoạt động; xem điều kiện đại lượng/cặp ở Validation | Hộp |
| Mã công thức tham chiếu | `AllocationRule.formula_code` | Mã công thức tham chiếu của quy tắc | Văn bản ≤ 120 ký tự | Không | Có | Giá trị đã lưu | Trim, giữ case; text không FK, không kiểm tra công thức tồn tại. Engine phân bổ hiện tại chặn khi có giá trị. | Không có FK; chỉ là mã text | Trống cho NORMAL_CAPACITY hiện tại |
| Mức ưu tiên | `AllocationRule.priority` | Mức ưu tiên được lưu trên quy tắc | Số nguyên | Có | Có | Giá trị đã lưu | Số nguyên [−2147483648,2147483647]; cho số âm; chưa là chính sách chọn nhiều quy tắc trong Run. | Không có lựa chọn danh mục riêng; theo cấu hình đang mở | 100 |
| Hiệu lực từ ngày | `AllocationRule.effective_from` | Ngày bắt đầu áp dụng dữ liệu này | Ngày | Có | Có | Giá trị đã lưu | Phiên bản có thể trống nếu không có ngày kết thúc; Rate/Rule/Assignment bắt buộc. Nhập ngày không tự đưa Nháp vào hiệu lực. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-01 |
| Hiệu lực đến ngày | `AllocationRule.effective_to` | Ngày cuối cùng được tính trong khoảng nguồn sản xuất/Costing | Ngày | Không | Có | Giá trị đã lưu | Không bắt buộc; nếu nhập phải có bắt đầu và phải sau bắt đầu; bao gồm ngày kết thúc. Form không kiểm tra chồng khoảng. | Cặp ngày; trạng thái bản ghi được quản lý độc lập | 2026-10-31 |

Sửa cập nhật trực tiếp bản ghi, không tạo phiên bản. Không áp khóa phiên bản BOM lên form này. Đơn giá/quy tắc giữ trạng thái đang lưu; UI chưa có thao tác đưa bản mới Nháp vào hiệu lực. Liên kết SKU không có trường trạng thái riêng. Khi thay kỳ cần thêm bản ghi kỳ mới; Quy tắc phân bổ dùng mã mới để không trùng mã.

## Bảng lựa chọn trên UI

| Trường | Stored code → nhãn UI |
| --- | --- |
| Loại nguồn lực | MACHINE → Máy móc; LABOR → Nhân công; WORK_CENTER → Trung tâm sản xuất; SERVICE → Dịch vụ |
| Cấp đóng gói / cấp cha gợi ý | PRIMARY → Cấp 1 · Bao bì trực tiếp; SECONDARY → Cấp 2 · Bao bì nhóm; TERTIARY → Cấp 3 · Bao bì vận chuyển; PALLET → Kiện trên pallet; CONTAINER → Công-ten-nơ |
| Loại nhóm chi phí | FACTORY_FIXED → Chi phí cố định nhà máy; FACTORY_VARIABLE → Chi phí biến đổi nhà máy; QA → Đảm bảo chất lượng; WAREHOUSE → Kho vận; EXPORT → Xuất khẩu; OTHER → Khác |
| Tiêu thức phân bổ | NORMAL_CAPACITY → Công suất bình thường; MACHINE_HOUR → Giờ máy; LABOR_HOUR → Giờ lao động; KG → Khối lượng (kg); UNIT → Số đơn vị; BATCH → Số lô; PALLET_DAY → Ngày lưu pallet; SHIPMENT → Số chuyến hàng; VALUE → Giá trị; CUSTOM → Tùy chỉnh |
| Trạng thái chỉ xem/lọc | DRAFT → Nháp; IN_REVIEW → Chờ duyệt; APPROVED → Đã duyệt; EFFECTIVE → Đang hiệu lực; RETIRED → Ngừng hiệu lực |

## Trường không nhập trong form

Số phiên bản, trạng thái phiên bản/đơn giá/quy tắc, dấu thời gian, hash và các actor là thông tin tự tạo/giữ nguyên hoặc chỉ xem, không phải trường cần nhập. Status không nằm trong allow-list nhận POST. Hiệu lực theo ngày là giá trị tính để hiển thị; không phải trạng thái do người dùng sửa. Điều kiện bổ sung của Quy tắc được giữ nguyên và chỉ báo có/không trên chi tiết; raw JSON không có form. Bao bì không có output_qty/output_uom/yield/scrap; nguồn lực không có mô tả hoặc thông số khấu hao; Nhóm chi phí không có số tiền kỳ trong form.

## Xác nhận và form không nhập dữ liệu mới

Xóa thành phần BOM, thành phần bao bì, công đoạn: mở đường dẫn `remove/`, xem dòng cần xóa, chọn **Hủy** hoặc **Xác nhận xóa**. Không có trường nghiệp vụ mới; chỉ cho phiên bản còn sửa. Ngừng hoạt động header/danh mục: bỏ **Đang hoạt động** trong form sửa, nhấn nút lưu rồi **Xác nhận và lưu**. Không có form xóa header/version/rate/rule/assignment.


## Nhóm trường công thức và giá thành

Đối chiếu source 09/10/2026, không kết nối DB. Các đường dẫn nguồn dưới đây tính từ repository root; root cần đổi link khi ghép vào docs. `Có*` là bắt buộc tùy điều kiện; checkbox không yêu cầu phải đánh dấu. Trống là không khai báo initial/default riêng, không ngầm bằng 0. Ví dụ mã ngoài DEMO là cấu hình minh họa cần tạo trước.

Nguồn: `apps/core/models.py`, `apps/formula_engine/{forms,services,selectors,urls,views}.py`, `apps/costing/{forms,validators,services,selectors,run_forms,run_services,run_selectors,run_views,urls}.py`, templates Formula/Costing/shared reference filters/pagination.

## Thiết lập công thức — Form tạo mới

Menu: CÔNG THỨC & QUY TẮC → Thiết lập công thức → + Thêm công thức. Route `/formula-engine/formulas/create/`. Form kết hợp FormulaForm+VersionForm; nút Kiểm tra công thức / Lưu công thức / Hủy. Mẫu test xuất hiện sau khi có plan hợp lệ.

| Field UI | Model field | Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã công thức | Formula.code | Text≤120 | Có | Có | Trống | Trim/uppercase; ASCII chữ đầu, sau chữ/số/_; không TRUE/FALSE/AND/OR/NOT; unique | Chưa trùng mã công thức | DEMO_DIRECT_FORMULA |
| Tên công thức | Formula.name | Text≤255 | Có | Có | Trống | Không trắng | Không | Tổng chi phí trực tiếp |
| Mô tả | Formula.description | Textarea | Không | Có | Trống | Trim; rỗng lưu NULL | Không | Tổng cho sản lượng của Run |
| Phần tử chi phí kết quả | Formula.output_element | Chọn CE | Không | Có | Trống | CE hoạt động; output tương thích kiểu/đơn vị/tiền tệ | Phần tử chi phí | DEMO_DIRECT_COST |
| Đang hoạt động | Formula.is_active | Checkbox | Không | Có | Có | Boolean | Activation cần hoạt động | Chọn |
| Biểu thức | FormulaVersion.expression | Textarea | Có | Có | Trống | Parser/type/unit/dependency/cycle; giới hạn mặc định8000ký tự | Các CE/Formula tham chiếu | $DEMO_MATERIAL_COST + $DEMO_PACKAGING_COST + $DEMO_RESOURCE_COST |
| Hiệu lực từ ngày | FormulaVersion.effective_from | Date | Không* | Có | Trống | Có* khi nhập end hoặc kích hoạt | Dependency EFFECTIVE theo ngày khi activation | 01/10/2026 |
| Hiệu lực đến ngày | FormulaVersion.effective_to | Date | Không | Có | Trống | >start; Costing bao gồm ngày cuối | Ngày bắt đầu | 31/10/2026 |
| Lý do thay đổi | FormulaVersion.change_reason | Textarea | Không | Có | Trống | Rỗng→NULL | Không | Công thức chi phí trực tiếp |

## Thiết lập công thức — Form chỉnh sửa thông tin

Route `/formula-engine/formulas/<id>/edit/`, nút Lưu công thức tính/Hủy. Chỉnh thông tin, không chỉnh expression ở đây.

| Field UI | Model field | Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã công thức | Formula.code | Text≤120 | Có | Không | Giá trị cũ | Giữ định danh; legacy casing giữ nguyên | Formula hiện có | DEMO_DIRECT_FORMULA |
| Tên công thức | Formula.name | Text≤255 | Có | Có | Giá trị cũ | Không trắng | Không | Tổng trực tiếp kỳ mới |
| Mô tả | Formula.description | Textarea | Không | Có | Giá trị cũ | Trim/rỗng→NULL | Không | Bổ sung mô tả |
| Phần tử chi phí kết quả | Formula.output_element | Chọn CE | Không | Không | Giá trị cũ | Giữ định danh kể cả đã có inactive reference | CE hiện có | DEMO_DIRECT_COST |
| Đang hoạt động | Formula.is_active | Checkbox | Không | Có | Giá trị cũ | Ngừng hoạt động ngăn source mới/activation | Không thay Run lịch sử | Chọn |

## Phiên bản Formula — Form tạo mới / chỉnh sửa

Tạo: `/formula-engine/formulas/<id>/versions/create/`, prefill bốn ô từ **bản mới nhất**, lưu số max+1 ở DRAFT; không clone testcase. Sửa: `/formula-engine/formulas/<id>/versions/<version_id>/edit/`, chỉ DRAFT/IN_REVIEW. Cả hai dùng cùng bốn field sau; nút Kiểm tra công thức/Lưu công thức/ Kiểm thử khi có plan/Hủy.

| Field UI | Model field | Kiểu | Required | Editable tạo/sửa | Default tạo | Default sửa | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|---|
| Biểu thức | FormulaVersion.expression | Textarea | Có | Có / Có nếu editable status | Expression bản mới nhất | Expression đang sửa | Parser/type/unit/dependency/cycle/limits | CE và Formula hoạt động | @DEMO_DIRECT_FORMULA + $DEMO_OVERHEAD_COST |
| Hiệu lực từ ngày | FormulaVersion.effective_from | Date | Không* | Có / Có nếu editable status | Ngày bản mới nhất | Ngày đang sửa | Có* nếu end hoặc activation | Dependency theo ngày | 01/11/2026 |
| Hiệu lực đến ngày | FormulaVersion.effective_to | Date | Không | Có / Có nếu editable status | Ngày bản mới nhất | Ngày đang sửa | >start | Ngày bắt đầu | Để trống |
| Lý do thay đổi | FormulaVersion.change_reason | Textarea | Không | Có / Có nếu editable status | Lý do bản mới nhất | Lý do đang sửa | Rỗng→NULL | Không | Áp dụng kỳ mới |

## Kiểm thử / thử tính / lưu testcase

UI ở Studio (trước khi lưu chỉ thử) và trang phiên bản sau lưu. Root formula theo phiên bản đang xem; dependency preview theo bản mới nhất. Nút Kiểm thử (`action=test`), Lưu bộ kiểm thử (`action=save_test`), Chạy bộ kiểm thử đã lưu (`action=run_cases`), Ngừng sử dụng (`tests/<case_id>/deactivate/`, POST). Không có form sửa testcase, không có ô tolerance.

| Field UI | Model field | Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Tên phần tử · MÃ (mỗi input số) | FormulaTestCase.input_context[CODE], form input_CODE | Decimal≤64digits | Có | Có | Trống | Số hữu hạn; limits engine; loại/đơn vị theo CE | Leaf CE MONEY/NUMBER/PERCENT/QUANTITY | 260000; PERCENT0.1=10% |
| Tên phần tử · MÃ (Boolean) | input_context[CODE], input_CODE | Chọn Chọn giá trị/Có/Không | Có | Có | Chọn giá trị | TRUE/FALSE→bool | CE BOOLEAN | Có |
| Tên phần tử · MÃ (Text) | input_context[CODE], input_CODE | Text≤8000 | Có | Có | Trống | strip=False; giới hạn engine | CE TEXT | Nội địa |
| Kết quả mong đợi | expected_value_numeric hoặc expected_value_text; form expected | Theo output | Không* | Có | Trống | Có* khi save_test; số tối đa24digits/8dp; Boolean lưu TRUE/FALSE; Text rỗng chưa expose | Kiểu output của plan | 530000 |
| Tên bộ kiểm thử | FormulaTestCase.name; form test_name | Text≤255 | Không* | Có | Trống | Có* khi save_test; tên trim | Formula đã lưu để lưu case | DEMO_GOLDEN_10_BOX |

`tolerance=0` và `is_active=True` do hệ thống đặt cho testcase mới, không phải ô UI. Các mẫu đang hoạt động hiển thị tên/kết quả/sai số đã lưu; Ngừng sử dụng đặt inactive. Kết quả runtime/trace không lưu vào bảng định nghĩa Formula. Studio trước khi lưu không hiển thị Tên bộ kiểm thử hoặc nút Lưu bộ kiểm thử; nó chỉ hiển thị các input và Kết quả mong đợi khi plan hợp lệ.

Ví dụ dữ liệu lưu kỹ thuật (không phải ô JSON trên UI):

```json
{"DEMO_MATERIAL_COST":"260000","DEMO_PACKAGING_COST":"150000","DEMO_RESOURCE_COST":"120000"}
```

Đây là `FormulaTestCase.input_context` cho DEMO_DIRECT_FORMULA; expected numeric là `530000`, tolerance là0. Input BOOLEAN lưu JSON Boolean; các numeric lưu chuỗi để giữ Decimal chính xác. Ví dụ phần `context.request.manual` cho phương án minh họa có một dòng MANUAL mang mã FREIGHT_TOTAL là `{"FREIGHT_TOTAL":"20000"}`; người dùng nhập20000 ở ô nhãn dòng, không nhập JSON.

## Phương án — Form tạo mới

Route `/costing/schemes/create/`, SchemeForm+SchemeVersionForm(prefix initial); nút Lưu phương án tính giá thành/Hủy. Lưu header+initialDRAFT atomically.

| Field UI | Model field | Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã phương án | CostingScheme.code | Text≤120 | Có | Có | Trống | Trim/uppercase; unique; không ép grammar Formula | Không | DEMO_COSTING_SCHEME |
| Tên phương án | name | Text≤255 | Có | Có | Trống | Không trắng | Không | Giá thành Cappuccino mẫu |
| Mã mục đích | purpose | Text≤100 | Có | Có | Trống | Text nghiệp vụ tự do; không phải enum thực thi | Không | STANDARD_COST |
| Mã phạm vi áp dụng | context_scope | Text≤100 | Có | Có | GENERAL | Text nghiệp vụ; không phải SKU assignment | Không | SKU |
| Mô tả | description | Textarea | Không | Có | Trống | Trim/rỗng→NULL | Không | Phương án cho bài mẫu |
| Đang hoạt động | is_active | Checkbox | Không | Có | Có | Boolean | Cần hoạt động để activate/run | Chọn |
| Hiệu lực từ ngày | CostingSchemeVersion.effective_from; initial-effective_from | Date | Không* | Có | Trống | Có* nếu nhập end hoặc activation | Formula theo ngày bắt đầu | 01/10/2026 |
| Hiệu lực đến ngày | effective_to; initial-effective_to | Date | Không | Có | Trống | >start; inclusive ngày cuối | Ngày bắt đầu | 31/10/2026 |
| Lý do thay đổi | change_reason; initial-change_reason | Textarea | Không | Có | Trống | Trim/rỗng→NULL | Không | Dữ liệu ban đầu |

## Phương án — Form chỉnh sửa thông tin

Route `/costing/schemes/<id>/edit/`; nút Lưu phương án tính giá thành/Hủy; không có ba field version ở form này. Bảng sáu field đầy đủ:

| Field UI | Model field | Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã phương án | code | Text≤120 | Có | Chỉ khi chưa có bản chốt | Giá trị cũ | Unique; fixed sau có version ngoàiDRAFT/IN_REVIEW | Version statuses | DEMO_COSTING_SCHEME |
| Tên phương án | name | Text≤255 | Có | Có | Giá trị cũ | Không trắng | Không | Giá thành Cappuccino |
| Mã mục đích | purpose | Text≤100 | Có | Chỉ khi chưa có bản chốt | Giá trị cũ | Fixed sau có bản chốt | Version statuses | STANDARD_COST |
| Mã phạm vi áp dụng | context_scope | Text≤100 | Có | Chỉ khi chưa có bản chốt | Giá trị cũ | Fixed sau có bản chốt | Version statuses | SKU |
| Mô tả | description | Textarea | Không | Có | Giá trị cũ | Trim/rỗng→NULL | Không | Bổ sung mô tả |
| Đang hoạt động | is_active | Checkbox | Không | Có | Giá trị cũ | Boolean; Run mới cần active | Không thay snapshot cũ | Chọn |

## Phiên bản phương án — Form tạo mới / chỉnh sửa

Tạo `/costing/schemes/<id>/versions/create/?source=<version_id>`; khi có source clone đúng toàn bộ dòng/references/conditions, prefill ba ô. Không có source thì version mới rỗng, không clone tự động. Sửa `/versions/<version_id>/edit/`, chỉ DRAFT/IN_REVIEW; giữ version_no. Nút Lưu phiên bản phương án/Hủy.

| Field UI | Model field | Kiểu | Required | Editable tạo/sửa | Default tạo | Default sửa | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|---|
| Hiệu lực từ ngày | CostingSchemeVersion.effective_from | Date | Không* | Có / Có nếu editable status | Source nếu clone, nếu không trống | Giá trị cũ | Có* nếu end hoặc activation | Formula validity theo ngày | 01/11/2026 |
| Hiệu lực đến ngày | effective_to | Date | Không | Có / Có nếu editable status | Source nếu clone, nếu không trống | Giá trị cũ | >start; activation config kiểm tra formula end | Ngày bắt đầu | Để trống |
| Lý do thay đổi | change_reason | Textarea | Không | Có / Có nếu editable status | Source nếu clone, nếu không trống | Giá trị cũ | Trim/rỗng→NULL | Không | Thêm input cước |

## Thành phần phương án — Form tạo mới

Route `/costing/schemes/<id>/versions/<version_id>/lines/create/`. Cần version DRAFT/IN_REVIEW. Nút + Thêm thành phần / Lưu thành phần / Hủy. Chỉ field nguồn tương ứng source_mode hiện ra; các field reference khác không phải ô người dùng nhập cùng lúc.

| Field UI | Model field | Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã dòng | CostingSchemeLine.line_code | Text≤120 | Có | Có | Trống | Trim/uppercase; unique trong version | Version | DEMO_MATERIAL_COST |
| Nhãn hiển thị | label | Text≤255 | Có | Có | Trống | Không trắng | Không | Chi phí nguyên vật liệu |
| Loại dòng | line_type | Select | Có | Có | INPUT | INPUT/CALCULATION/SUBTOTAL/OUTPUT/INFO | OUTPUT có điều kiện Run riêng | INPUT |
| Phần tử chi phí | cost_element | Select CE | Không* | Có | Trống | CE active khi chọn mới; SYSTEM/OUTPUT cần CE; tương thích formula | CE | DEMO_MATERIAL_COST |
| Nguồn dữ liệu | source_mode | Select | Có | Có | MANUAL | SYSTEM/MANUAL/LOOKUP/FORMULA/EXTERNAL | Quyết định ô nguồn | SYSTEM |
| Mã bộ lấy dữ liệu hệ thống | system_resolver_code | Text≤120 | Có* SYSTEM | Có khi SYSTEM | Trống | Registry check ở validate/activate/run; trim, không tựuppercase | CE đúng type; rule nếu ALLOCATION | MATERIAL_COST |
| Bảng quy tắc | rule_table | Select RuleTable | Có* LOOKUP | Có khi LOOKUP | Trống | Active khi chọn mới; Draft lưu được nhưng activation chặn | RuleTable hiện có; chưa có UI module | Không dùng cho Run |
| Phiên bản công thức | formula_version | Select FormulaVersion | Có* FORMULA | Có khi FORMULA | Trống | EFFECTIVE/VALID/active/phù hợp CE/date/type/unit | FormulaVersion exact | DEMO_DIRECT_FORMULA v1 |
| Mã kết nối dữ liệu bên ngoài | external_adapter_code | Text≤120 | Có* EXTERNAL | Có khi EXTERNAL | Trống | Draft lưu được; activation/run chặn | Chưa adapter | Không dùng cho Run |
| Cho phép điều chỉnh giá trị | editable | Checkbox | Không | Có | Không | Metadata, không phải override runtime | MANUAL vẫn nhập dù false | Bỏ chọn |
| Giá trị điều chỉnh tối thiểu | min_override_value | Decimal24,8 | Không | Có | Trống | Min≤max; không mặc định cấm số âm; MANUAL enforce | Dòng MANUAL numeric | 0 |
| Giá trị điều chỉnh tối đa | max_override_value | Decimal24,8 | Không | Có | Trống | Max≥min; MANUAL enforce | Min nếu có | 1000000 |
| Điều chỉnh cần lý do | override_requires_reason | Checkbox | Không | Có | Có | Lưu metadata; Run không có field lý do override | Không có thao tác override | Chọn |
| Phạm vi hiển thị | visibility_scope | Select | Có | Có | INTERNAL (model/first choice) | INTERNAL/SCREEN/QUOTE/REPORT/ALL; không hide result rows hiện tại | Không | INTERNAL |
| Phạm vi chi phí | cost_scope | Select | Có | Có | MANUFACTURING | MANUFACTURING/LANDED/COST_TO_SERVE/CHANNEL/PRICING/ANALYTICS; Run chỉ2scope | OUTPUT phải MANUFACTURING | MANUFACTURING |
| Thứ tự hiển thị | display_order | Integer | Có | Có | max(maxExisting,0)+10, cap2147483647 | −2147483648..2147483647, unique; không phải thứ tự tính | Version | 10 |
| Số chữ số làm tròn | rounding_scale | Integer | Không | Có | Trống | 0..12; trống dùng CE, không CE dùng8 | CE rounding_mode/scale | 6 |
| Ghi chú | notes | Textarea | Không | Có | Trống | Trim/rỗng→NULL | Không | Tổng cho Run |

## Thành phần phương án — Form chỉnh sửa

Route `.../lines/<line_id>/edit/`, cùng18field và validation của tạo mới; default là giá trị cũ. Tất cả18field sửa được khi versionDRAFT/IN_REVIEW, source conditional như trên. APPROVED/EFFECTIVE/RETIRED không sửa. Mã dòng/thứ tự vẫn kiểm tra unique nhưng bỏ qua chính dòng đang sửa. Reference inactive/legacy hiện có được giữ để xem/sửa, không tự đổi sang bản mới; validate/activate vẫn báo reference không hợp lệ. Đổi nguồn rồi lưu chỉ giữ ref nguồn mới. `condition_jsonb` giữ nguyên, không expose; condition nonempty ngănactivation. Xóa dùng GET confirmation/POST Xác nhận xóa, không có field nghiệp vụ riêng.

## Lần tính — Form tạo mới / tạo từ Run cũ

Tạo `/costing/runs/create/`; tạo từ cũ `/costing/runs/<uuid>/rerun/`. Không có form edit Run. Rerun có cùng11field dưới đây, prefill từ context.request cũ; chọn lại sources theo ngày; manual prefill theo line_code còn khớp; UUID mới. Nút Chạy tính giá/Hủy.

| Field UI | Model field | Kiểu | Required | Editable tạo/rerun | Default tạo | Default rerun | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|---|
| Sản phẩm | CostingRun.product | Select Product | Có | Có/Có | Trống | Product yêu cầu cũ nếu còn active | Active; nguồn nội bộ | Product | DEMO_CAPPUCCINO |
| SKU | CostingRun.sku | Select Sku | Không* | Có/Có | Trống | SKU yêu cầu cũ nếu hợp lệ | SKU active thuộc Product; packaging cần SKU khi execute | Product | DEMO_CAPPUCCINO_BOX20 |
| Phương án tính giá thành | scheme_version được resolve từ form scheme | Select Scheme | Có | Có/Có | Trống | Scheme gốc nếu còn eligible | Active + đúng1versionEFFECTIVE theo ngày | SchemeVersion/date | DEMO_COSTING_SCHEME |
| Ngày tính giá | effective_at + context.request.costing_date | Date | Có | Có/Có | Hôm nay | Ngày Run cũ | Date hợp lệ; lưu0h timezone | Mọi effective-datedsource | 07/10/2026 |
| Sản lượng cần tính | quantity | Decimal24,8 | Có | Có/Có | 1 | Lượng cũ | >0; khôngfloat; service<1e16 | Basis/output conversions | 10 |
| Đơn vị sản lượng | quantity_uom | Select Uom | Có | Có/Có | Trống | Uom cũ nếu active | Uom/categoryactive | UoM conversion theo nguồn | Hộp DEMO_BOX_UOM |
| Tiền tệ kết quả | result_currency_code | Select Currency | Có | Có/Có | Trống | Currency cũ nếu active | Active; CE/prices/rates/period cùngcurrency, chưaFX | Currency | VND |
| Loại lần tính | run_type | Select | Có | Có/Có | STANDARD | Loại cũ | STANDARD/PLANNED; chung execution hiện tại | Không | Giá thành chuẩn |
| Sản lượng cơ sở đóng gói | context.request.packaging_quantity | Decimal24,8 | Có* PACKAGING_COST | Có/Có khi hiện | Trống | Cơ sở cũ | >0 nếu nhập; bắt buộc có resolverpackaging | Scheme lines | 1 |
| Đơn vị cơ sở đóng gói | context.request.packaging_uom | Select Uom | Có* PACKAGING_COST | Có/Có khi hiện | Trống | Uom cơ sở cũ | Active/categoryactive | Packagingbasis + conversions | Hộp |
| Ghi chú | context.notes / context.request.notes | Textarea≤3000 | Không | Có/Có | Trống | Ghi chú cũ | Max3000 | Không | Đối soát10hộp |

### Các ô MANUAL sinh động trên cùng form

| Field UI | Model field | Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Nhãn dòng (MÃ_DÒNG), MONEY/NUMBER/QUANTITY | context.request.manual[line_code], RunLine typedvalue, form manual_<linePK> | Decimal24,8 | Có mỗi dòng MANUAL | Có khi tạo/rerun | Tạo trống; rerun giá trị cũ theo code | Kiểu CE; min/max nếu có; engine limits/rounding/storage | Version đúng ngày; CE hoặc NUMBER fallback | 120000 |
| Nhãn dòng (MÃ_DÒNG), PERCENT | Như trên; RunLine.percent_value | Decimal18,10 | Có | Có | Như trên | Tỷ lệ thập phân, min/max, không tự /100 | CE PERCENT | 0.1=10% |
| Nhãn dòng (MÃ_DÒNG), BOOLEAN | Như trên; RunLine.boolean_value | Select Có/Không | Có | Có | Không khai báo initial, browser firstchoiceCó; rerun giá trị cũ | true/false→bool; không field reason | CE BOOLEAN | Không |
| Nhãn dòng (MÃ_DÒNG), TEXT | Như trên; RunLine.text_value | Text≤4000 | Có | Có | Tạo trống; rerun giá trị cũ | Required/max4000 | CE TEXT hoặc INFO không CE | Giá mua theo hợp đồng |

Mọi MANUAL phải nhập, kể cả editable=False. Không CE: INFO→TEXT, loại khác→NUMBER. Engine yêu cầu keyset manual khớp chính xác các mã dòng MANUAL; input thay SYSTEM không phải thao tác có sẵn. Decimal sau làm tròn tiền/số/số lượng phải lưu chính xác8dp, PERCENT10dp; không tự truncate.

### Hidden/technical không đưa vào bảng field nhập nghiệp vụ

RunForm `idempotency_key` là UUID hidden do hệ thống tạo; `csrfmiddlewaretoken` hidden. Các nút Formula gửi action hidden-by-button; không phải model field người dùng nhập. `version_no/status/hash/actors/timestamps`, Formula AST/dependencies, Run snapshots/trace/lock time tự quản lý, không có ô UI. Không hướng dẫn nhập rawJSON.

## Form tìm kiếm/lọc/sắp xếp/phân trang (template fields)

Mọi bộ lọc GET tùy chọn; empty=không lọc; Lọc/Đặt lại; Mỗi trang25mặc định hoặc50/100; Trước/Sau. Sort theo header/selector whitelist; `page` nằm trên link phântrang, không phải ô nhập. Mỗi trang và sort có thể là control/hidden queryparameter; không lưu vào model.

| Màn hình | Field UI / query parameter | Kiểu/default | Validation/dependency/example |
|---|---|---|---|
| Formula list | Tìm kiếm `q` | Search/trống | code/name/description; ví dụ DEMO_DIRECT |
| Formula list | Trạng thái phiên bản mới nhất `status` | Select/trống | DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/RETIRED; áp dụng newestversion |
| Formula list | Kiểm tra đã lưu `validation` | Select/trống | NOT_VALIDATED/VALID/INVALID |
| Formula list | Kiểu đầu ra đã khai báo `value_type` | Select/trống | MONEY/NUMBER/PERCENT/QUANTITY/BOOLEAN/TEXT; lọc output_element, không inferredtype |
| Formula list | Trạng thái công thức `active` | Select/trống | true/false; headeractive |
| Formula list | Hiệu lực theo ngày `effective` | Select/trống | UNDATED/FUTURE/EFFECTIVE/EXPIRED theo newestversion |
| Formula list | Sắp xếp `sort` | Whitelist/code mặc định | code/name/version/updated_at; `-` đảo chiều |
| Formula versions | Tìm kiếm `q` trong shared template | Search/trống | Selector không áp dụng q ở versionlist; ghi rõ không có tìm theo nội dung expression |
| Formula versions | Sắp xếp `sort` | Whitelist/−version | version/effective_from/created_at; UI không render statusfilter dù selector chấpnhận statusquery |
| Token palette | Tìm biến dữ liệu `q` | Search/trống | CE/Formula code/name; mỗi nhóm≤60; không GET save |
| Scheme list | Tìm kiếm `q` | Search/trống | code/name/description/purpose/context_scope; DEMO_COSTING |
| Scheme list | Mục đích `purpose` | Select/trống | Distincttextcodes có sẵn; STANDARD_COST |
| Scheme list | Phạm vi áp dụng `context_scope` | Select/trống | Distincttextcodes có sẵn; SKU |
| Scheme list | Trạng thái phiên bản mới nhất `status` | Select/trống | Versionstatuses |
| Scheme list | Hiệu lực theo ngày `effective` | Select/trống | Date statuses theo newestversion |
| Scheme list | Trạng thái phương án `active` | Select/trống | true/false |
| Scheme list | Sắp xếp `sort` | Whitelist/code | code/name/version/effective_from/updated_at |
| Scheme versions | Tìm kiếm `q` trong shared template | Search/trống | Selector không áp dụng q cho versionlist |
| Scheme versions | Trạng thái `status` | Select/trống | DRAFT/IN_REVIEW/APPROVED/EFFECTIVE/RETIRED |
| Scheme versions | Hiệu lực theo ngày `effective` | Select/trống | UNDATED/FUTURE/EFFECTIVE/EXPIRED |
| Scheme versions | Sắp xếp `sort` | Whitelist/−version | version/effective_from/created_at |
| Scheme lines | Mỗi trang `per_page`, links `page` |25,1 | Không search/filter; luôn display_order |
| Run list | Tìm kiếm `q` | Search/trống | run_no và storednames Product/SKU/Scheme; DEMO_CAPPUCCINO |
| Run list | Sản phẩm `product` | Select/trống | ID, all scopedmasters để lọc history, không chỉactive |
| Run list | SKU `sku` | Select/trống | ID, không phải dependent SKU createcontrol |
| Run list | Phương án `scheme` | Select/trống | ID, lọc scheme_version.scheme |
| Run list | Trạng thái `status` | Select/trống | DRAFT/CALCULATED/IN_REVIEW/APPROVED/LOCKED/FAILED/SUPERSEDED; không có UI transition cho mọi lựa chọn |
| Run list | Từ ngày `date_from` | Date/trống | inclusive ngày bắtđầu; sai ISOdate→emptyresults |
| Run list | Đến ngày `date_to` | Date/trống | inclusive ngày cuối (query<0hngày kế); sai→emptyresults |
| Run list | Sắp xếp `sort` | Whitelist/−created_at | costing_date/created_at/total_cost/run_no |
| Run lines | Mỗi trang `per_page`, links `page` |25,1 | Không search/filter; luôn display_order |
| Tất cả list/version/lines | Mỗi trang `per_page`, links `page` |25,1 |25/50/100; giá trịsortkhông hợp lệ fallback; badpage dùng Paginator.get_page |

Không biến GET dependent endpoints `catalogue`, `lines/sources`, `runs/options` thành module hoặc form nhập dữ liệu mới. Chúng cập nhật field nguồn/SKU/Scheme/packaging/manual cho form hiện tại. Activations có confirmation bằng modal, không thêm field nghiệp vụ; Xác nhận kích hoạt POST.


## Giá bán — quy ước form

Nguồn: [forms](../../apps/pricing/forms.py), [ScenarioForm](../../apps/pricing/scenario_forms.py), [validator](../../apps/pricing/validators.py), [validator kịch bản](../../apps/pricing/scenario_validators.py), [services](../../apps/pricing/services.py). Tỷ lệ nhập theo %, ví dụ `5` là 5%; DB lưu `0.05`. Decimal nhập bằng dấu chấm. `Có*` là bắt buộc có điều kiện; không mặc định tùy ý bằng 0.

Các trường mục tiêu vẫn hiện cùng lúc; backend yêu cầu chỉ điền đúng phương pháp. Các trường phạm vi phí/thuế cũng luôn hiện. SKU, nguồn giá thành, tiền tệ bán và khu vực thuế của kịch bản nằm ở vùng tải lại theo Product/SKU/Channel. Kênh và master mới phải hoạt động; sửa quy tắc Nháp được giữ chính tham chiếu cũ ngừng hoạt động. Scenario chỉ chọn master hoạt động.

### Kênh bán — tạo mới (ChannelForm)

Đường dẫn `/pricing/channels/create/`.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã kênh bán | Channel.code | Định danh kênh/kịch bản; Text ≤120 ký tự | Có | Có | Trống | Trim + uppercase; duy nhất trong bộ dữ liệu | Không | TRAIN_DIRECT |
| Tên kênh bán | Channel.name | Tên dễ nhận diện; Text ≤255 ký tự | Có | Có | Trống | Trim; không rỗng | Không | Bán trực tiếp đào tạo |
| Loại kênh bán | Channel.channel_type | Phân loại kênh; Danh sách mã | Có | Có | Trống | Chọn B2B/RETAIL/ECOMMERCE/EXPORT/D2C/OTHER; không tự sinh phí | Danh sách loại kênh | D2C — Bán trực tiếp |
| Mã nền tảng | Channel.platform_code | Mã nền tảng do doanh nghiệp đặt; Text ≤100 ký tự | Không | Có | Trống | Trim + uppercase; không kết nối API sàn | Không | TRAIN_MARKET |
| Mã thị trường | Channel.market_code | Mã thị trường; gợi ý khu vực thuế; Text ≤50 ký tự | Không | Có | Trống | Trim + uppercase; mã phải thống nhất với TaxRule | Scenario.jurisdiction_code | VN |
| Mã loại người bán | Channel.seller_type | Mã phạm vi người bán; Text ≤100 ký tự | Không | Có | Trống | Trim + uppercase; không tự xác minh tư cách người bán | Mã loại người bán của Channel khi tra thuế | Trống nếu áp dụng chung |
| Tiền tệ mặc định | Channel.default_currency_code | Đồng tiền bán gợi ý; Dropdown tham chiếu | Không | Có | Trống | Có thể trống; Currency phải hoạt động khi chọn mới | Currency | VND |
| Đang hoạt động | Channel.is_active | Cho phép chọn kênh trong kịch bản mới; Checkbox | Không | Có | Tích | Checkbox; bỏ tích ngừng lựa chọn mới | Scenario | Tích |

### Kênh bán — chỉnh sửa (ChannelForm)

Đường dẫn `/pricing/channels/<id>/edit/`.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã kênh bán | Channel.code | Định danh kênh/kịch bản; Text ≤120 ký tự | Có | Có | Giá trị hiện có | Trim + uppercase; duy nhất trong bộ dữ liệu | Không | TRAIN_DIRECT |
| Tên kênh bán | Channel.name | Tên dễ nhận diện; Text ≤255 ký tự | Có | Có | Giá trị hiện có | Trim; không rỗng | Không | Bán trực tiếp đào tạo |
| Loại kênh bán | Channel.channel_type | Phân loại kênh; Danh sách mã | Có | Có | Giá trị hiện có | Chọn B2B/RETAIL/ECOMMERCE/EXPORT/D2C/OTHER; không tự sinh phí | Danh sách loại kênh | D2C — Bán trực tiếp |
| Mã nền tảng | Channel.platform_code | Mã nền tảng do doanh nghiệp đặt; Text ≤100 ký tự | Không | Có | Giá trị hiện có | Trim + uppercase; không kết nối API sàn | Không | TRAIN_MARKET |
| Mã thị trường | Channel.market_code | Mã thị trường; gợi ý khu vực thuế; Text ≤50 ký tự | Không | Có | Giá trị hiện có | Trim + uppercase; mã phải thống nhất với TaxRule | Scenario.jurisdiction_code | VN |
| Mã loại người bán | Channel.seller_type | Mã phạm vi người bán; Text ≤100 ký tự | Không | Có | Giá trị hiện có | Trim + uppercase; không tự xác minh tư cách người bán | Mã loại người bán của Channel khi tra thuế | Trống nếu áp dụng chung |
| Tiền tệ mặc định | Channel.default_currency_code | Đồng tiền bán gợi ý; Dropdown tham chiếu | Không | Có | Giá trị hiện có | Có thể trống; Currency phải hoạt động khi chọn mới | Currency | VND |
| Đang hoạt động | Channel.is_active | Cho phép chọn kênh trong kịch bản mới; Checkbox | Không | Có | Giá trị hiện có | Checkbox; bỏ tích ngừng lựa chọn mới | Scenario | Tích |

### Quy tắc phí kênh — tạo mới (ChannelFeeRuleForm)

Đường dẫn `/pricing/channel-fee-rules/create/`.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Kênh bán | ChannelFeeRule.channel | Kênh chịu phí hoặc định giá; Dropdown tham chiếu | Có | Có | Trống | Phải hoạt động khi chọn mới | Kênh bán | TRAIN_DIRECT |
| Nhóm sản phẩm | ChannelFeeRule.product_category | Giới hạn nhóm được áp dụng; Dropdown tham chiếu | Không | Có | Trống | Trống = mọi nhóm; nếu chọn SKU thì phải khớp nhóm | Nhóm sản phẩm hoạt động | DEMO_COFFEE |
| SKU | ChannelFeeRule.sku | Giới hạn SKU; Dropdown tham chiếu | Không | Có | Trống | Trống = phạm vi chung; phải thuộc Product/nhóm liên quan | SKU hoạt động | DEMO_CAPPUCCINO_BOX20 |
| Mã loại phí | ChannelFeeRule.fee_type | Mã nhóm phí dùng để chọn một quy tắc thắng; Text ≤80 ký tự | Có | Có | Trống | Trim + uppercase; mã tự đặt; các mã khác nhau cộng lại | Các quy tắc cùng fee_type | COMMISSION |
| Mã cơ sở tính phí | ChannelFeeRule.fee_base | Cơ sở phí; Text ≤80 ký tự | Có | Có | Trống | Lưu mã nghiệp vụ; bộ tính hiện chỉ LIST_PRICE trên giá khách trả | Giá khách trả | LIST_PRICE |
| Tỷ lệ (%) | ChannelFeeRule.rate | Phần tỷ lệ của khoản thu; Decimal(9,6) | Không | Có | Trống | Nhập 0–100%; DB chia 100; phải có rate hoặc fixed_amount | Giá tính theo cơ sở | 5 |
| Số tiền cố định | ChannelFeeRule.fixed_amount | Khoản tiền cố định trên một đơn vị bán; Decimal(24,8) | Không | Có | Trống | ≥0; có giá trị kể cả 0 cần tiền tệ | Currency | 1000 |
| Tiền tệ | ChannelFeeRule.currency_code | Đồng tiền của số tiền; Dropdown tham chiếu | Có* | Có | Trống | Có tiền cố định/sàn/trần phải chọn; khi định giá là bắt buộc | Currency hoạt động; FX nếu khác đồng tiền bán | VND |
| Giá trị trần | ChannelFeeRule.cap_amount | Trần phí riêng cho quy tắc; Decimal(24,8) | Không | Có | Trống | ≥0 và ≥sàn; có giá trị cần tiền tệ | Phí thô trước sàn/trần | 10000 |
| Giá trị sàn | ChannelFeeRule.floor_amount | Sàn phí riêng cho quy tắc; Decimal(24,8) | Không | Có | Trống | ≥0; có giá trị cần tiền tệ | Phí thô trước sàn/trần | 500 |
| Tỷ lệ được hoàn (%) | ChannelFeeRule.refundable_ratio | Tỷ lệ phí được hoàn; Decimal(9,6) | Có | Có | 0 từ default model khi mở form | Bắt buộc 0–100%; bộ tính hiện chỉ chấp nhận 0 | Chính sách phí | 0 |
| Thuế trong phí | ChannelFeeRule.tax_inclusive | Khoản phí đã gồm hay chưa gồm thuế; Chọn Có/Không rõ ràng | Có | Có | Trống | Phải chọn rõ; phí có giá trị cần True khi thực thi hiện tại | Chính sách thuế trên phí | Giá đã bao gồm thuế |
| Mức ưu tiên | ChannelFeeRule.priority | Ưu tiên nguồn cùng loại và độ cụ thể; Số nguyên | Có | Có | 100 | Số nguyên −2147483648…2147483647; lớn hơn thắng | Nguồn cùng loại/phạm vi | 100 |
| Hiệu lực từ ngày | ChannelFeeRule.effective_from | Ngày bắt đầu được dùng; Ngày | Có | Có | Ngày hôm nay | Bắt buộc; ngày này được bao gồm | Ngày định giá | 01/10/2026 |
| Hiệu lực đến ngày | ChannelFeeRule.effective_to | Ngày ngừng được dùng; Ngày | Không | Có | Trống | > effective_from; ngày này không bao gồm; trống = chưa giới hạn | Ngày bắt đầu | 01/11/2026 |
| Nguồn tham chiếu | ChannelFeeRule.source_reference | Chứng từ/diễn giải để đối chiếu; Textarea | Không | Có | Trống | Tùy chọn; trim; không phải dữ liệu bộ tính tự tải | Nguồn do người nhập kiểm chứng | Bảng phí đào tạo tháng 10 |
| Trạng thái | ChannelFeeRule.status | Nháp hoặc đưa vào hiệu lực trực tiếp; Danh sách mã | Có | Có | Nháp | Chỉ DRAFT/EFFECTIVE khi lưu; bản đã chốt không sửa form | Lịch áp dụng | EFFECTIVE — Đang hiệu lực |

### Quy tắc phí kênh — chỉnh sửa (ChannelFeeRuleForm)

Đường dẫn `/pricing/channel-fee-rules/<id>/edit/`. Chỉ Nháp được chỉnh sửa; bản đã chốt chỉ đọc.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Kênh bán | ChannelFeeRule.channel | Kênh chịu phí hoặc định giá; Dropdown tham chiếu | Có | Có; chỉ Nháp | Giá trị hiện có | Phải hoạt động khi chọn mới | Kênh bán | TRAIN_DIRECT |
| Nhóm sản phẩm | ChannelFeeRule.product_category | Giới hạn nhóm được áp dụng; Dropdown tham chiếu | Không | Có; chỉ Nháp | Giá trị hiện có | Trống = mọi nhóm; nếu chọn SKU thì phải khớp nhóm | Nhóm sản phẩm hoạt động | DEMO_COFFEE |
| SKU | ChannelFeeRule.sku | Giới hạn SKU; Dropdown tham chiếu | Không | Có; chỉ Nháp | Giá trị hiện có | Trống = phạm vi chung; phải thuộc Product/nhóm liên quan | SKU hoạt động | DEMO_CAPPUCCINO_BOX20 |
| Mã loại phí | ChannelFeeRule.fee_type | Mã nhóm phí dùng để chọn một quy tắc thắng; Text ≤80 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Trim + uppercase; mã tự đặt; các mã khác nhau cộng lại | Các quy tắc cùng fee_type | COMMISSION |
| Mã cơ sở tính phí | ChannelFeeRule.fee_base | Cơ sở phí; Text ≤80 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Lưu mã nghiệp vụ; bộ tính hiện chỉ LIST_PRICE trên giá khách trả | Giá khách trả | LIST_PRICE |
| Tỷ lệ (%) | ChannelFeeRule.rate | Phần tỷ lệ của khoản thu; Decimal(9,6) | Không | Có; chỉ Nháp | Giá trị hiện có | Nhập 0–100%; DB chia 100; phải có rate hoặc fixed_amount | Giá tính theo cơ sở | 5 |
| Số tiền cố định | ChannelFeeRule.fixed_amount | Khoản tiền cố định trên một đơn vị bán; Decimal(24,8) | Không | Có; chỉ Nháp | Giá trị hiện có | ≥0; có giá trị kể cả 0 cần tiền tệ | Currency | 1000 |
| Tiền tệ | ChannelFeeRule.currency_code | Đồng tiền của số tiền; Dropdown tham chiếu | Có* | Có; chỉ Nháp | Giá trị hiện có | Có tiền cố định/sàn/trần phải chọn; khi định giá là bắt buộc | Currency hoạt động; FX nếu khác đồng tiền bán | VND |
| Giá trị trần | ChannelFeeRule.cap_amount | Trần phí riêng cho quy tắc; Decimal(24,8) | Không | Có; chỉ Nháp | Giá trị hiện có | ≥0 và ≥sàn; có giá trị cần tiền tệ | Phí thô trước sàn/trần | 10000 |
| Giá trị sàn | ChannelFeeRule.floor_amount | Sàn phí riêng cho quy tắc; Decimal(24,8) | Không | Có; chỉ Nháp | Giá trị hiện có | ≥0; có giá trị cần tiền tệ | Phí thô trước sàn/trần | 500 |
| Tỷ lệ được hoàn (%) | ChannelFeeRule.refundable_ratio | Tỷ lệ phí được hoàn; Decimal(9,6) | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc 0–100%; bộ tính hiện chỉ chấp nhận 0 | Chính sách phí | 0 |
| Thuế trong phí | ChannelFeeRule.tax_inclusive | Khoản phí đã gồm hay chưa gồm thuế; Chọn Có/Không rõ ràng | Có | Có; chỉ Nháp | Giá trị hiện có | Phải chọn rõ; phí có giá trị cần True khi thực thi hiện tại | Chính sách thuế trên phí | Giá đã bao gồm thuế |
| Mức ưu tiên | ChannelFeeRule.priority | Ưu tiên nguồn cùng loại và độ cụ thể; Số nguyên | Có | Có; chỉ Nháp | Giá trị hiện có | Số nguyên −2147483648…2147483647; lớn hơn thắng | Nguồn cùng loại/phạm vi | 100 |
| Hiệu lực từ ngày | ChannelFeeRule.effective_from | Ngày bắt đầu được dùng; Ngày | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc; ngày này được bao gồm | Ngày định giá | 01/10/2026 |
| Hiệu lực đến ngày | ChannelFeeRule.effective_to | Ngày ngừng được dùng; Ngày | Không | Có; chỉ Nháp | Giá trị hiện có | > effective_from; ngày này không bao gồm; trống = chưa giới hạn | Ngày bắt đầu | 01/11/2026 |
| Nguồn tham chiếu | ChannelFeeRule.source_reference | Chứng từ/diễn giải để đối chiếu; Textarea | Không | Có; chỉ Nháp | Giá trị hiện có | Tùy chọn; trim; không phải dữ liệu bộ tính tự tải | Nguồn do người nhập kiểm chứng | Bảng phí đào tạo tháng 10 |
| Trạng thái | ChannelFeeRule.status | Nháp hoặc đưa vào hiệu lực trực tiếp; Danh sách mã | Có | Có; chỉ Nháp | Giá trị hiện có | Chỉ DRAFT/EFFECTIVE khi lưu; bản đã chốt không sửa form | Lịch áp dụng | EFFECTIVE — Đang hiệu lực |

### Quy tắc thuế — tạo mới (TaxRuleForm)

Đường dẫn `/pricing/tax-rules/create/`.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã khu vực áp dụng | TaxRule.jurisdiction_code | Mã khu vực áp dụng thuế; Text ≤80 ký tự | Có | Có | Trống | Trim + uppercase; khớp khu vực của Scenario | Kênh/kịch bản | VN |
| Mã loại thuế | TaxRule.tax_type | Mã loại thuế để chọn quy tắc thắng; Text ≤80 ký tự | Có | Có | Trống | Trim + uppercase; loại khác nhau cộng song song | Các quy tắc cùng tax_type | VAT |
| Mã nhóm thuế | TaxRule.tax_class_code | Phạm vi nhóm thuế sản phẩm; Text ≤100 ký tự | Không | Có | Trống | Trống = chung; Product.tax_class_code khi khớp | Product | Trống |
| Mã loại người bán | TaxRule.seller_type | Mã phạm vi người bán; Text ≤100 ký tự | Không | Có | Trống | Trim + uppercase; không tự xác minh tư cách người bán | Mã loại người bán của Channel khi tra thuế | Trống nếu áp dụng chung |
| Mã loại giao dịch | TaxRule.transaction_type | Mã phạm vi giao dịch; Text ≤100 ký tự | Không | Có | Trống | Trim + uppercase; khớp đúng mã trong Scenario/TaxRule | Quy tắc thuế/kịch bản | Trống nếu áp dụng chung |
| Thuế suất (%) | TaxRule.rate | Phần tỷ lệ của khoản thu; Decimal(9,6) | Không | Có | Trống | Nhập 0–100%; DB chia 100; phải có rate hoặc fixed_amount | Giá tính theo cơ sở | 5 |
| Số tiền cố định | TaxRule.fixed_amount | Khoản tiền cố định trên một đơn vị bán; Decimal(24,8) | Không | Có | Trống | ≥0; có giá trị kể cả 0 cần tiền tệ | Currency | 1000 |
| Tiền tệ | TaxRule.currency_code | Đồng tiền của số tiền; Dropdown tham chiếu | Có* | Có | Trống | Có tiền cố định/sàn/trần phải chọn; khi định giá là bắt buộc | Currency hoạt động; FX nếu khác đồng tiền bán | VND |
| Mã cơ sở tính thuế | TaxRule.tax_base | Cơ sở tính thuế; Text ≤100 ký tự | Có | Có | Trống | Bộ tính hỗ trợ SELLING_PRICE/LIST_PRICE trên cơ sở trước thuế chung | Giá trước thuế | SELLING_PRICE |
| Tỷ lệ được khấu trừ (%) | TaxRule.recoverable_ratio | Tỷ lệ thuế được khấu trừ; Decimal(9,6) | Có | Có | 0 từ default model khi mở form | Bắt buộc 0–100%; Pricing hiện chỉ chấp nhận 0 | Chính sách thuế bán | 0 |
| Thuế trong giá | TaxRule.inclusive | Thuế đã gồm trong giá niêm yết hay chưa; Chọn Có/Không rõ ràng | Có | Có | Trống | Phải chọn rõ; không trộn hai kiểu trong một Scenario | Các quy tắc thuế đã chọn | Giá đã bao gồm thuế |
| Mức ưu tiên | TaxRule.priority | Ưu tiên nguồn cùng loại và độ cụ thể; Số nguyên | Có | Có | 100 | Số nguyên −2147483648…2147483647; lớn hơn thắng | Nguồn cùng loại/phạm vi | 100 |
| Hiệu lực từ ngày | TaxRule.effective_from | Ngày bắt đầu được dùng; Ngày | Có | Có | Ngày hôm nay | Bắt buộc; ngày này được bao gồm | Ngày định giá | 01/10/2026 |
| Hiệu lực đến ngày | TaxRule.effective_to | Ngày ngừng được dùng; Ngày | Không | Có | Trống | > effective_from; ngày này không bao gồm; trống = chưa giới hạn | Ngày bắt đầu | 01/11/2026 |
| Nguồn tham chiếu | TaxRule.source_reference | Chứng từ/diễn giải để đối chiếu; Textarea | Không | Có | Trống | Tùy chọn; trim; không phải dữ liệu bộ tính tự tải | Nguồn do người nhập kiểm chứng | Bảng phí đào tạo tháng 10 |
| Trạng thái | TaxRule.status | Nháp hoặc đưa vào hiệu lực trực tiếp; Danh sách mã | Có | Có | Nháp | Chỉ DRAFT/EFFECTIVE khi lưu; bản đã chốt không sửa form | Lịch áp dụng | EFFECTIVE — Đang hiệu lực |

### Quy tắc thuế — chỉnh sửa (TaxRuleForm)

Đường dẫn `/pricing/tax-rules/<id>/edit/`. Chỉ Nháp được chỉnh sửa; bản đã chốt chỉ đọc.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã khu vực áp dụng | TaxRule.jurisdiction_code | Mã khu vực áp dụng thuế; Text ≤80 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Trim + uppercase; khớp khu vực của Scenario | Kênh/kịch bản | VN |
| Mã loại thuế | TaxRule.tax_type | Mã loại thuế để chọn quy tắc thắng; Text ≤80 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Trim + uppercase; loại khác nhau cộng song song | Các quy tắc cùng tax_type | VAT |
| Mã nhóm thuế | TaxRule.tax_class_code | Phạm vi nhóm thuế sản phẩm; Text ≤100 ký tự | Không | Có; chỉ Nháp | Giá trị hiện có | Trống = chung; Product.tax_class_code khi khớp | Product | Trống |
| Mã loại người bán | TaxRule.seller_type | Mã phạm vi người bán; Text ≤100 ký tự | Không | Có; chỉ Nháp | Giá trị hiện có | Trim + uppercase; không tự xác minh tư cách người bán | Mã loại người bán của Channel khi tra thuế | Trống nếu áp dụng chung |
| Mã loại giao dịch | TaxRule.transaction_type | Mã phạm vi giao dịch; Text ≤100 ký tự | Không | Có; chỉ Nháp | Giá trị hiện có | Trim + uppercase; khớp đúng mã trong Scenario/TaxRule | Quy tắc thuế/kịch bản | Trống nếu áp dụng chung |
| Thuế suất (%) | TaxRule.rate | Phần tỷ lệ của khoản thu; Decimal(9,6) | Không | Có; chỉ Nháp | Giá trị hiện có | Nhập 0–100%; DB chia 100; phải có rate hoặc fixed_amount | Giá tính theo cơ sở | 5 |
| Số tiền cố định | TaxRule.fixed_amount | Khoản tiền cố định trên một đơn vị bán; Decimal(24,8) | Không | Có; chỉ Nháp | Giá trị hiện có | ≥0; có giá trị kể cả 0 cần tiền tệ | Currency | 1000 |
| Tiền tệ | TaxRule.currency_code | Đồng tiền của số tiền; Dropdown tham chiếu | Có* | Có; chỉ Nháp | Giá trị hiện có | Có tiền cố định/sàn/trần phải chọn; khi định giá là bắt buộc | Currency hoạt động; FX nếu khác đồng tiền bán | VND |
| Mã cơ sở tính thuế | TaxRule.tax_base | Cơ sở tính thuế; Text ≤100 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Bộ tính hỗ trợ SELLING_PRICE/LIST_PRICE trên cơ sở trước thuế chung | Giá trước thuế | SELLING_PRICE |
| Tỷ lệ được khấu trừ (%) | TaxRule.recoverable_ratio | Tỷ lệ thuế được khấu trừ; Decimal(9,6) | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc 0–100%; Pricing hiện chỉ chấp nhận 0 | Chính sách thuế bán | 0 |
| Thuế trong giá | TaxRule.inclusive | Thuế đã gồm trong giá niêm yết hay chưa; Chọn Có/Không rõ ràng | Có | Có; chỉ Nháp | Giá trị hiện có | Phải chọn rõ; không trộn hai kiểu trong một Scenario | Các quy tắc thuế đã chọn | Giá đã bao gồm thuế |
| Mức ưu tiên | TaxRule.priority | Ưu tiên nguồn cùng loại và độ cụ thể; Số nguyên | Có | Có; chỉ Nháp | Giá trị hiện có | Số nguyên −2147483648…2147483647; lớn hơn thắng | Nguồn cùng loại/phạm vi | 100 |
| Hiệu lực từ ngày | TaxRule.effective_from | Ngày bắt đầu được dùng; Ngày | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc; ngày này được bao gồm | Ngày định giá | 01/10/2026 |
| Hiệu lực đến ngày | TaxRule.effective_to | Ngày ngừng được dùng; Ngày | Không | Có; chỉ Nháp | Giá trị hiện có | > effective_from; ngày này không bao gồm; trống = chưa giới hạn | Ngày bắt đầu | 01/11/2026 |
| Nguồn tham chiếu | TaxRule.source_reference | Chứng từ/diễn giải để đối chiếu; Textarea | Không | Có; chỉ Nháp | Giá trị hiện có | Tùy chọn; trim; không phải dữ liệu bộ tính tự tải | Nguồn do người nhập kiểm chứng | Bảng phí đào tạo tháng 10 |
| Trạng thái | TaxRule.status | Nháp hoặc đưa vào hiệu lực trực tiếp; Danh sách mã | Có | Có; chỉ Nháp | Giá trị hiện có | Chỉ DRAFT/EFFECTIVE khi lưu; bản đã chốt không sửa form | Lịch áp dụng | EFFECTIVE — Đang hiệu lực |

### Tỷ giá — tạo mới (FxRateForm)

Đường dẫn `/pricing/fx-rates/create/`.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã loại tỷ giá | FxRate.rate_type | Mã loại tỷ giá được tra; Text ≤50 ký tự | Có | Có | Trống | Trim + uppercase; khớp chính xác Scenario.fx_rate_type | Kịch bản khi đổi tiền | SPOT |
| Tiền tệ nguồn | FxRate.from_currency_code | Đồng tiền đầu vào; Dropdown tham chiếu | Có | Có | Trống | Bắt buộc; khác tiền đích | Currency hoạt động | VND |
| Tiền tệ đích | FxRate.to_currency_code | Đồng tiền sau quy đổi; Dropdown tham chiếu | Có | Có | Trống | Bắt buộc; khác tiền nguồn | Currency hoạt động | USD |
| Tỷ giá | FxRate.rate | Số tiền đích cho 1 tiền nguồn; Decimal(24,12) | Có | Có | Trống | >0; tối đa 12 số lẻ; không tự nghịch đảo | Chiều nguồn → đích | 0.00004 |
| Hiệu lực từ thời điểm | FxRate.effective_at | Thời điểm tỷ giá bắt đầu; Ngày + giờ | Có | Có | Thời điểm hiện tại | Tra tại 00:00 ngày định giá giờ Việt Nam | Ngày định giá | 01/10/2026 00:00 |
| Hiệu lực đến thời điểm | FxRate.valid_to | Thời điểm tỷ giá kết thúc; Ngày + giờ | Không | Có | Trống | >effective_at; không bao gồm mốc này; trống = chưa giới hạn | Thời điểm bắt đầu | 01/11/2026 00:00 |
| Tên nguồn dữ liệu | FxRate.source_name | Tên nguồn tỷ giá; Text ≤150 ký tự | Có | Có | Trống | Bắt buộc; trim; tự nhập, không tự lấy trực tuyến | Chứng từ đã kiểm chứng | Tỷ giá đào tạo |
| Nguồn tham chiếu | FxRate.source_reference | Chứng từ/diễn giải để đối chiếu; Textarea | Không | Có | Trống | Tùy chọn; trim; không phải dữ liệu bộ tính tự tải | Nguồn do người nhập kiểm chứng | Bảng phí đào tạo tháng 10 |
| Trạng thái | FxRate.status | Nháp hoặc đưa vào hiệu lực trực tiếp; Danh sách mã | Có | Có | Nháp | Chỉ DRAFT/EFFECTIVE khi lưu; bản đã chốt không sửa form | Lịch áp dụng | EFFECTIVE — Đang hiệu lực |

### Tỷ giá — chỉnh sửa (FxRateForm)

Đường dẫn `/pricing/fx-rates/<id>/edit/`. Chỉ Nháp được chỉnh sửa; bản đã chốt chỉ đọc.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã loại tỷ giá | FxRate.rate_type | Mã loại tỷ giá được tra; Text ≤50 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Trim + uppercase; khớp chính xác Scenario.fx_rate_type | Kịch bản khi đổi tiền | SPOT |
| Tiền tệ nguồn | FxRate.from_currency_code | Đồng tiền đầu vào; Dropdown tham chiếu | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc; khác tiền đích | Currency hoạt động | VND |
| Tiền tệ đích | FxRate.to_currency_code | Đồng tiền sau quy đổi; Dropdown tham chiếu | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc; khác tiền nguồn | Currency hoạt động | USD |
| Tỷ giá | FxRate.rate | Số tiền đích cho 1 tiền nguồn; Decimal(24,12) | Có | Có; chỉ Nháp | Giá trị hiện có | >0; tối đa 12 số lẻ; không tự nghịch đảo | Chiều nguồn → đích | 0.00004 |
| Hiệu lực từ thời điểm | FxRate.effective_at | Thời điểm tỷ giá bắt đầu; Ngày + giờ | Có | Có; chỉ Nháp | Giá trị hiện có | Tra tại 00:00 ngày định giá giờ Việt Nam | Ngày định giá | 01/10/2026 00:00 |
| Hiệu lực đến thời điểm | FxRate.valid_to | Thời điểm tỷ giá kết thúc; Ngày + giờ | Không | Có; chỉ Nháp | Giá trị hiện có | >effective_at; không bao gồm mốc này; trống = chưa giới hạn | Thời điểm bắt đầu | 01/11/2026 00:00 |
| Tên nguồn dữ liệu | FxRate.source_name | Tên nguồn tỷ giá; Text ≤150 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc; trim; tự nhập, không tự lấy trực tuyến | Chứng từ đã kiểm chứng | Tỷ giá đào tạo |
| Nguồn tham chiếu | FxRate.source_reference | Chứng từ/diễn giải để đối chiếu; Textarea | Không | Có; chỉ Nháp | Giá trị hiện có | Tùy chọn; trim; không phải dữ liệu bộ tính tự tải | Nguồn do người nhập kiểm chứng | Bảng phí đào tạo tháng 10 |
| Trạng thái | FxRate.status | Nháp hoặc đưa vào hiệu lực trực tiếp; Danh sách mã | Có | Có; chỉ Nháp | Giá trị hiện có | Chỉ DRAFT/EFFECTIVE khi lưu; bản đã chốt không sửa form | Lịch áp dụng | EFFECTIVE — Đang hiệu lực |

### Kịch bản giá bán — tạo mới (ScenarioForm)

Đường dẫn `/pricing/scenarios/create/`. Scenario CALCULATED chỉ xem/nhân bản; nút lưu là **Lưu Nháp**.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã kịch bản | PriceScenario.code | Định danh kịch bản lịch sử; Text ≤120 ký tự | Có | Có | Trống | Trim + uppercase; duy nhất; nhân bản cần mã mới | Không | TRAIN_PRICE_20 |
| Tên kịch bản | PriceScenario.name | Tên giả định dễ so sánh; Text ≤255 ký tự | Có | Có | Trống | Trim; không rỗng | Không | Bán trực tiếp mục tiêu 20% |
| Sản phẩm | PriceScenario.base_run.product (scope form) | Sản phẩm đang định giá; Dropdown tham chiếu | Có | Có | Trống | Bắt buộc hoạt động; phải khớp nguồn | Product; tải lại SKU/Run qua HTMX | DEMO_CAPPUCCINO |
| SKU | PriceScenario.base_run.sku (scope form) | SKU đang định giá; Dropdown tham chiếu | Không | Có | Trống | Tùy chọn; thuộc Product; nguồn phải cùng SKU hoặc cùng không có SKU | SKU hoạt động của Product | DEMO_CAPPUCCINO_BOX20 |
| Nguồn giá thành | PriceScenario.base_run | Giá vốn một đơn vị đã khóa; Dropdown tham chiếu | Có | Có | Trống | LOCKED; full_cost≥0, quantity>0, có dòng kết quả và per_unit dạng chuỗi Decimal hữu hạn≥0; đúng Product/SKU | Run; 100 nguồn gần nhất + nguồn cũ được chọn đúng phạm vi | Run ngày 07/10/2026: 58.300 VND/hộp |
| Kênh bán | PriceScenario.channel | Kênh chịu phí hoặc định giá; Dropdown tham chiếu | Có | Có | Trống | Phải hoạt động khi chọn mới | Kênh bán | TRAIN_DIRECT |
| Ngày định giá | PriceScenario.scenario_context_jsonb.pricing_date | Ngày tra phí/thuế/FX; Ngày | Có | Có | Ngày hôm nay | Bắt buộc; độc lập với valid_from/valid_to | Nguồn phù hợp theo ngày | 08/10/2026 |
| Phương pháp định giá | PriceScenario.pricing_method | Loại mục tiêu cần giải; Danh sách mã | Có | Có | Không initial riêng; UI mục đầu MARGIN | MARGIN/MARKUP/PROFIT_PER_UNIT; chỉ một mục tiêu tương ứng | Ba trường mục tiêu | MARGIN — Biên lợi nhuận mục tiêu |
| Biên lợi nhuận mục tiêu (%) | PriceScenario.target_margin | Lợi nhuận / giá khách trả; Decimal(18,8) | Có* | Có | Trống | Có* khi MARGIN; −100% ≤ giá trị <100%; các mục tiêu khác trống | Giá sau phí/thuế | 20 |
| Tỷ lệ cộng trên giá vốn (%) | PriceScenario.target_markup | Lợi nhuận / giá vốn; Decimal(18,8) | Có* | Có | Trống | Có* khi MARKUP; ≥−100%; giá vốn phải >0 khi tính | Giá vốn sau FX | 25 |
| Lợi nhuận mục tiêu trên một đơn vị | PriceScenario.target_profit_per_unit | Số tiền lợi nhuận một đơn vị; Decimal(24,8) | Có* | Có | Trống | Có* khi PROFIT_PER_UNIT; có thể âm; đồng tiền bán | Tiền tệ bán | 15000 |
| Giá bán tối thiểu | PriceScenario.minimum_price | Sàn giá khách trả; Decimal(24,8) | Không | Có | Trống | ≥0; chỉ nâng giá rồi tính lại margin, không phải giá bán tùy ý | Kết quả giải mục tiêu | 90000 |
| Tiền tệ bán | PriceScenario.currency_code | Đồng tiền của số tiền; Dropdown tham chiếu | Có | Có | Gợi ý từ kênh khi chưa nhập | Bắt buộc; Currency hoạt động; nếu khác tiền nguồn cần FX khi tính | Currency hoạt động; FX nếu khác đồng tiền bán | VND |
| Thuế bán hàng | PriceScenario.scenario_context_jsonb.tax_mode | Có tra thuế bán hay không; Danh sách mã | Có | Có | Áp dụng thuế theo quy tắc | REQUIRED cần quy tắc; NONE bỏ thuế một cách rõ ràng | TaxRule | REQUIRED — Áp dụng thuế theo quy tắc |
| Mã khu vực áp dụng thuế | PriceScenario.scenario_context_jsonb.jurisdiction_code | Khu vực dùng để tra thuế; Text ≤80 ký tự | Có* | Có | Gợi ý từ kênh khi chưa nhập | Có* nếu REQUIRED; trim + uppercase; gợi ý từ market_code khi trống | Channel.market_code / TaxRule | VN |
| Mã loại giao dịch | PriceScenario.scenario_context_jsonb.transaction_type | Giao dịch để chọn thuế cụ thể; Text ≤100 ký tự | Không | Có | Trống | Tùy chọn; trim + uppercase | TaxRule.transaction_type | Trống nếu chung |
| Mã loại tỷ giá | PriceScenario.scenario_context_jsonb.fx_rate_type | Loại tỷ giá khi đổi tiền; Text ≤50 ký tự | Có* | Có | Trống | Có* khi cần FX; đúng chiều; không fallback loại khác | FxRate tại 00:00 ngày định giá | SPOT |
| Hiệu lực từ ngày | PriceScenario.valid_from | Ngày áp dụng dự kiến của kịch bản; Ngày | Không | Có | Trống | Tùy chọn; không dùng thay pricing_date | valid_to | 08/10/2026 |
| Hiệu lực đến ngày | PriceScenario.valid_to | Ngày hết áp dụng dự kiến; Ngày | Không | Có | Trống | ≥valid_from nếu có cả hai; bằng nhau được chấp nhận | valid_from | 31/10/2026 |

### Kịch bản giá bán — chỉnh sửa (ScenarioForm)

Đường dẫn `/pricing/scenarios/<id>/edit/`. Chỉ Nháp được chỉnh sửa; bản đã chốt chỉ đọc. Scenario CALCULATED chỉ xem/nhân bản; nút lưu là **Lưu Nháp**.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Mã kịch bản | PriceScenario.code | Định danh kịch bản lịch sử; Text ≤120 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Trim + uppercase; duy nhất; nhân bản cần mã mới | Không | TRAIN_PRICE_20 |
| Tên kịch bản | PriceScenario.name | Tên giả định dễ so sánh; Text ≤255 ký tự | Có | Có; chỉ Nháp | Giá trị hiện có | Trim; không rỗng | Không | Bán trực tiếp mục tiêu 20% |
| Sản phẩm | PriceScenario.base_run.product (scope form) | Sản phẩm đang định giá; Dropdown tham chiếu | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc hoạt động; phải khớp nguồn | Product; tải lại SKU/Run qua HTMX | DEMO_CAPPUCCINO |
| SKU | PriceScenario.base_run.sku (scope form) | SKU đang định giá; Dropdown tham chiếu | Không | Có; chỉ Nháp | Giá trị hiện có | Tùy chọn; thuộc Product; nguồn phải cùng SKU hoặc cùng không có SKU | SKU hoạt động của Product | DEMO_CAPPUCCINO_BOX20 |
| Nguồn giá thành | PriceScenario.base_run | Giá vốn một đơn vị đã khóa; Dropdown tham chiếu | Có | Có; chỉ Nháp | Giá trị hiện có | LOCKED; full_cost≥0, quantity>0, có dòng kết quả và per_unit dạng chuỗi Decimal hữu hạn≥0; đúng Product/SKU | Run; 100 nguồn gần nhất + nguồn cũ được chọn đúng phạm vi | Run ngày 07/10/2026: 58.300 VND/hộp |
| Kênh bán | PriceScenario.channel | Kênh chịu phí hoặc định giá; Dropdown tham chiếu | Có | Có; chỉ Nháp | Giá trị hiện có | Phải hoạt động khi chọn mới | Kênh bán | TRAIN_DIRECT |
| Ngày định giá | PriceScenario.scenario_context_jsonb.pricing_date | Ngày tra phí/thuế/FX; Ngày | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc; độc lập với valid_from/valid_to | Nguồn phù hợp theo ngày | 08/10/2026 |
| Phương pháp định giá | PriceScenario.pricing_method | Loại mục tiêu cần giải; Danh sách mã | Có | Có; chỉ Nháp | Giá trị hiện có | MARGIN/MARKUP/PROFIT_PER_UNIT; chỉ một mục tiêu tương ứng | Ba trường mục tiêu | MARGIN — Biên lợi nhuận mục tiêu |
| Biên lợi nhuận mục tiêu (%) | PriceScenario.target_margin | Lợi nhuận / giá khách trả; Decimal(18,8) | Có* | Có; chỉ Nháp | Giá trị hiện có | Có* khi MARGIN; −100% ≤ giá trị <100%; các mục tiêu khác trống | Giá sau phí/thuế | 20 |
| Tỷ lệ cộng trên giá vốn (%) | PriceScenario.target_markup | Lợi nhuận / giá vốn; Decimal(18,8) | Có* | Có; chỉ Nháp | Giá trị hiện có | Có* khi MARKUP; ≥−100%; giá vốn phải >0 khi tính | Giá vốn sau FX | 25 |
| Lợi nhuận mục tiêu trên một đơn vị | PriceScenario.target_profit_per_unit | Số tiền lợi nhuận một đơn vị; Decimal(24,8) | Có* | Có; chỉ Nháp | Giá trị hiện có | Có* khi PROFIT_PER_UNIT; có thể âm; đồng tiền bán | Tiền tệ bán | 15000 |
| Giá bán tối thiểu | PriceScenario.minimum_price | Sàn giá khách trả; Decimal(24,8) | Không | Có; chỉ Nháp | Giá trị hiện có | ≥0; chỉ nâng giá rồi tính lại margin, không phải giá bán tùy ý | Kết quả giải mục tiêu | 90000 |
| Tiền tệ bán | PriceScenario.currency_code | Đồng tiền của số tiền; Dropdown tham chiếu | Có | Có; chỉ Nháp | Giá trị hiện có | Bắt buộc; Currency hoạt động; nếu khác tiền nguồn cần FX khi tính | Currency hoạt động; FX nếu khác đồng tiền bán | VND |
| Thuế bán hàng | PriceScenario.scenario_context_jsonb.tax_mode | Có tra thuế bán hay không; Danh sách mã | Có | Có; chỉ Nháp | Giá trị hiện có | REQUIRED cần quy tắc; NONE bỏ thuế một cách rõ ràng | TaxRule | REQUIRED — Áp dụng thuế theo quy tắc |
| Mã khu vực áp dụng thuế | PriceScenario.scenario_context_jsonb.jurisdiction_code | Khu vực dùng để tra thuế; Text ≤80 ký tự | Có* | Có; chỉ Nháp | Giá trị hiện có | Có* nếu REQUIRED; trim + uppercase; gợi ý từ market_code khi trống | Channel.market_code / TaxRule | VN |
| Mã loại giao dịch | PriceScenario.scenario_context_jsonb.transaction_type | Giao dịch để chọn thuế cụ thể; Text ≤100 ký tự | Không | Có; chỉ Nháp | Giá trị hiện có | Tùy chọn; trim + uppercase | TaxRule.transaction_type | Trống nếu chung |
| Mã loại tỷ giá | PriceScenario.scenario_context_jsonb.fx_rate_type | Loại tỷ giá khi đổi tiền; Text ≤50 ký tự | Có* | Có; chỉ Nháp | Giá trị hiện có | Có* khi cần FX; đúng chiều; không fallback loại khác | FxRate tại 00:00 ngày định giá | SPOT |
| Hiệu lực từ ngày | PriceScenario.valid_from | Ngày áp dụng dự kiến của kịch bản; Ngày | Không | Có; chỉ Nháp | Giá trị hiện có | Tùy chọn; không dùng thay pricing_date | valid_to | 08/10/2026 |
| Hiệu lực đến ngày | PriceScenario.valid_to | Ngày hết áp dụng dự kiến; Ngày | Không | Có; chỉ Nháp | Giá trị hiện có | ≥valid_from nếu có cả hai; bằng nhau được chấp nhận | valid_from | 31/10/2026 |

### Kết thúc hiệu lực — ClosePeriodForm

Mở từ trang chi tiết bản EFFECTIVE chưa có ngày kết thúc; không sửa tỷ lệ/số tiền. Mốc kết thúc phải trong tương lai và sau bắt đầu. Form này không phải form tạo/sửa quy tắc.

| Field UI | Model field | Ý nghĩa / Kiểu | Required | Editable | Default | Validation | Dependency | Example |
|---|---|---|---|---|---|---|---|---|
| Ngày kết thúc hiệu lực | ChannelFeeRule.effective_to / TaxRule.effective_to | Dừng áp dụng từ ngày này; Date | Có | Chỉ lần đầu kết thúc | Trống | >hôm nay và >bắt đầu; bản EFFECTIVE, end đang trống | Phí hoặc thuế đã chốt | 01/11/2026 nếu còn trong tương lai |
| Thời điểm kết thúc hiệu lực | FxRate.valid_to | Dừng áp dụng từ thời điểm này; DateTime | Có | Chỉ lần đầu kết thúc | Trống | >hiện tại và >effective_at; bản EFFECTIVE, end trống | Tỷ giá đã chốt | 01/11/2026 00:00 nếu còn trong tương lai |

## Trường tự động, chỉ đọc và được tính

| Nơi hiển thị | Trường/nhóm kỹ thuật | Ý nghĩa | Ai nhập / có sửa được không? |
|---|---|---|---|
| Chi tiết danh mục | id, created_at, updated_at nếu có | Định danh và mốc ghi nhận | Hệ thống; không phải input nghiệp vụ |
| Phiên bản BOM/bao bì/quy trình/Formula/Scheme | version_no | Số phiên bản trong header | Service tạo tăng số; không tự nhập “version mới” vào mã header |
| Phiên bản | status, validation_status nếu có | Vòng đời và kết quả kiểm tra riêng | Các form không cung cấp chọn trạng thái tùy ý; đọc hướng dẫn module về thao tác thực có |
| Bộ lọc/chi tiết dữ liệu có ngày | effective status | So sánh ngày hiện tại với khoảng ngày | Tính khi hiển thị; không thay status lưu DB |
| Run | public_id, run_no, trace_id | Đường dẫn, mã lần tính, mã hỗ trợ | Tự sinh; lưu mã để trao đổi nội bộ |
| Run | run_status | Đã khóa hoặc Thất bại sau thực thi | Tự chuyển; không có nút sửa/khóa thủ công |
| Run | full_cost, manufacturing_cost, per_unit trong context | Tổng và giá thành theo một đơn vị sản lượng nhập | Bộ tính; không sửa sau khi đã khóa |
| Dòng Run | amount, number_value, percent_value, quantity, boolean_value, text_value | Giá trị đúng kiểu dòng | Bộ tính hoặc input MANUAL trước chạy; không nhập kết quả sau chạy |
| Dòng Run | input_snapshot_jsonb, source_trace_jsonb | Đầu vào và các bước tính của dòng | Chỉ đọc qua màn hình diễn giải; không sửa JSON |
| Run | version_snapshot_jsonb | Nguồn/phiên bản đã dùng cho toàn lần tính | Chỉ đọc qua màn hình snapshot; không sửa JSON |
| Kịch bản giá bán | status | Nháp/Đã tính | Lưu Nháp rồi Tính giá bán; lỗi tính vẫn Nháp |
| Kịch bản giá bán | gross_price, fees, tax, profit, actual_margin… trong output_snapshot_jsonb | Cấu thành giá và tỷ lệ thực tế đã giải | Bộ tính; không phải form nhập giá cố định |
| Kịch bản giá bán | hash và nguồn của snapshot | Dấu nhận diện nội dung lịch sử | Tự tạo; so sánh kiểm tra tính hợp lệ trước khi đọc |
| So sánh kịch bản | chênh lệch, điểm phần trăm | Độ lệch so với kịch bản mốc | Tính từ snapshot, không chạy lại engine; khác tiền tệ không trừ số tiền |

Các field tương thích lưu trong database nhưng không có input/UI không phải chức năng phải điền thêm. Metadata JSON không được đưa ra thành form nhân viên. Ngày hiện tại trên badge có thể thay đổi ngày mai; snapshot lịch sử giữ dữ liệu đã dùng.

## Mã trạng thái và cách đọc đúng

| Mã | Nhãn | Phạm vi cần chú ý |
|---|---|---|
| DRAFT | Nháp | Phiên bản mới, nguồn sản xuất/giá mua mới, cấu hình Pricing mới, Scenario chưa tính |
| IN_REVIEW | Chờ duyệt | Mã tương thích ở một số version/filter; không có quy trình gửi duyệt trong UI |
| APPROVED | Đã duyệt | Mã tương thích của version, thuộc nhóm bất biến; không tìm nút duyệt |
| EFFECTIVE | Đang hiệu lực | Trạng thái lưu nguồn/phiên bản; vẫn phải đúng ngày và duy nhất |
| RETIRED | Ngừng hiệu lực | Bản đã chốt không sửa trực tiếp khi module áp dụng bất biến |
| CALCULATED | Đã tính | Scenario có snapshot; Run chỉ đi qua bước nội bộ trước khi khóa |
| LOCKED | Đã khóa | Run thành công; không phải trạng thái người dùng chọn trên form version |
| FAILED | Thất bại | Run thực thi lỗi; Scenario lỗi giữ Nháp |
| SUPERSEDED | Đã thay thế | Có ở mã/filter tương thích; không suy ra thao tác thay thế đã được triển khai |
| VALID / INVALID / NOT_VALIDATED | Hợp lệ / Không hợp lệ / Chưa kiểm tra | Kết quả kiểm tra công thức; không đồng nghĩa EFFECTIVE |

## Chọn cấu hình nào trong tình huống nào?

| Muốn làm | Chọn / nhập | Không nhầm với |
|---|---|---|
| Nhập một tổng chi phí do kế toán xác định | CE MONEY, tiền tệ đúng, không UoM; Scheme MANUAL; OUTPUT cộng biến ấy | Không ghi tổng vào trường số lượng hoặc coi là bộ tự tính cước |
| Tính nguyên liệu từ định mức | Scheme SYSTEM + MATERIAL_COST | LOOKUP chưa phải nguồn thực thi giá mua |
| Tính bao bì | SYSTEM + PACKAGING_COST; SKU + cơ sở đóng gói | Phiên bản bao bì không tự chứa output_qty |
| Tính máy/nhân công | SYSTEM + RESOURCE_COST; công đoạn + primary_resource + TIME UoM | Không copy rate vào Routing |
| Phân bổ hiện có | SYSTEM + ALLOCATION:<mã_rule>, NORMAL_CAPACITY, dữ liệu kỳ sẵn | MACHINE_HOUR có trong dropdown nhưng bộ tính chưa hỗ trợ |
| Cộng các biến đã có | FORMULA với phiên bản đã kiểm tra | Đổi nhãn SUBTOTAL không tự tạo phép cộng |
| Margin 20% trong Scenario | Nhập 20 tại Biên lợi nhuận mục tiêu; phương pháp MARGIN | Input MANUAL kiểu PERCENT của Run lại nhập tỷ lệ 0.2, không nhập20 |
| Đặt phí5% và1.000 cố định | Có thể cùng quy tắc hoặc hai fee_type; rate5, fixed1000 | fixed là cho một đơn vị đầu ra, không cho đơn hàng10hộp |
| Không áp thuế trong giả định đào tạo | Scenario Thuế bán hàng = Không áp dụng thuế | Không bỏ thiếu TaxRule trong chế độ REQUIRED |
| Đổi VND sang USD | FX đúng VND→USD và rate_type, hiệu lực lúc00:00 | Không nhập tỷ giá USD→VND rồi kỳ vọng tự đảo |

Các ví dụ định dạng là dữ liệu đào tạo. Không dùng mã/ví dụ làm quy tắc pháp lý hay tự tạo thêm danh mục chưa được doanh nghiệp thống nhất.
