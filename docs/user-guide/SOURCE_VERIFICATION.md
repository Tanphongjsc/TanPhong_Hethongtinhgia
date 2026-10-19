# Biên bản đối chiếu tài liệu với source

Ngày kiểm chứng: **09/10/2026**. Mốc source Git: **`f4e0030`**. Phạm vi thay đổi: bộ hướng dẫn mới; không sửa code nghiệp vụ, giao diện, cấu hình chạy, schema hoặc migration.

**Kết luận: USER MANUAL READY** cho hành vi hiện có đã đối chiếu. Đây là kết luận về tài liệu, không phải xác nhận đã triển khai production, đã chạy DEMO trên database doanh nghiệp hoặc đã hoàn thành nghiệm thu bằng trình duyệt. Những chức năng còn thiếu được ghi riêng trong [GAP_REGISTER](GAP_REGISTER.md).

## 1. Phương pháp và nguồn kiểm chứng

Entry point thực tế là [docs/00_AI_CONTEXT.md](../00_AI_CONTEXT.md); repository không có thư mục `docs/ai/`. Đã dùng các bản Markdown canonical: [phạm vi](../01_REQUIREMENTS_SCOPE.md), [nghiệp vụ](../02_BUSINESS_DOMAIN.md), [kiến trúc](../03_SYSTEM_ARCHITECTURE.md), [engineering](../04_ENGINEERING_GUIDE.md), [QA](../05_QA_TESTING.md) và [spec giao diện](../FRONTEND_IMPLEMENTATION_SPEC.md). Khi mô tả cũ khác implementation, hành vi source và tests hiện tại được ưu tiên.

Đối chiếu theo chuỗi: **URL → view → form → validator/service/selector → model → template → test**. Không lấy riêng `blank`, `null` hoặc model default để kết luận một ô form bắt buộc hay đã được điền. Kiểm kê lớp form và trường cơ sở kết hợp kiểm tra các trường được sinh lúc chạy; các queryset được kiểm tra từ source, không gọi database doanh nghiệp để lấy lựa chọn.

| Nhóm | Nguồn chính và nội dung đối chiếu |
|---|---|
| Model và kiến trúc chạy | [models.py](../../apps/core/models.py), [settings.py](../../config/settings.py), [urls.py](../../config/urls.py), [navigation.py](../../apps/master_data/navigation.py), [context_processors.py](../../apps/master_data/context_processors.py): mapping hiện có, menu thật, truy cập trực tiếp và route |
| Danh mục | [forms](../../apps/master_data/forms.py), [services](../../apps/master_data/services.py), [selectors](../../apps/master_data/selectors.py), [validators](../../apps/master_data/validators.py), [views](../../apps/master_data/views.py), [templates](../../templates/master_data): trường, chuẩn hóa, dropdown, lỗi, tìm/lọc, bảng và thao tác |
| Vật tư, sản phẩm, SKU | [forms](../../apps/product/forms.py), [services](../../apps/product/services.py), [selectors](../../apps/product/selectors.py), [validators](../../apps/product/validators.py), [views](../../apps/product/views.py), [templates](../../templates/product): quan hệ, active, đơn vị, số đo và mã |
| BOM, bao bì, nguồn lực, quy trình, phân bổ | [apps/bom](../../apps/bom), [templates/bom](../../templates/bom): các nhóm forms/services/selectors/validators/views/urls/constants tương ứng; version, clone, dòng, khóa sửa và giới hạn UI |
| Công thức | [forms](../../apps/formula_engine/forms.py), [services](../../apps/formula_engine/services.py), [validator](../../apps/formula_engine/validator.py), [tests](../../apps/formula_engine/tests.py), [templates](../../templates/formula_engine): cú pháp, kiểu/đơn vị, phụ thuộc, test, activation và nhãn nút |
| Phương án | [forms](../../apps/costing/forms.py), [services](../../apps/costing/services.py), [configuration](../../apps/costing/configuration.py), [templates](../../templates/costing): dòng/nguồn, một OUTPUT, validation, version và activation |
| Lần tính giá thành | [run_forms](../../apps/costing/run_forms.py), [run_services](../../apps/costing/run_services.py), [runner](../../apps/costing/engine/runner.py), [resolvers](../../apps/costing/engine/resolvers): nguồn hiệu lực, Decimal, scaling, MANUAL, trạng thái, lưu kết quả và rerun |
| Giá bán | [forms](../../apps/pricing/forms.py), [scenario_forms](../../apps/pricing/scenario_forms.py), [services](../../apps/pricing/services.py), [scenario_services](../../apps/pricing/scenario_services.py), [resolver](../../apps/pricing/engine/resolvers.py), [solver](../../apps/pricing/engine/solver.py), [comparison](../../apps/pricing/comparison.py), [templates](../../templates/pricing): phí/thuế/FX, mục tiêu, waterfall, snapshot, so sánh |
| Bộ mẫu | [demo_data](../../apps/costing/demo_data.py), [demo_verification](../../apps/costing/demo_verification.py), [demo_scenario](../../apps/pricing/demo_scenario.py), [command guard](../../config/command_safety.py): mã thật, ngày, giá, lượng, Golden và tác dụng ghi dữ liệu của lệnh verify |
| UI dùng chung | [layouts](../../templates/layouts), [components](../../templates/components), [static/js](../../static/js): sidebar, tìm kiếm, phân trang, trạng thái, toast, HTMX và tương tác cục bộ |

Danh sách đầy đủ **tất cả route và lớp form**, có liên kết file/dòng source, nằm ở [chương 02](02_BAN_DO_CHUC_NANG_VA_NGHIEP_VU.md). Bảng trường ở [chương 12](12_FIELD_REFERENCE.md) tách tạo/sửa và giải thích trường động; chương 04–07 dẫn nguồn cho từng nhóm nghiệp vụ.

## 2. Quy ước đếm và độ phủ

Các số sau không dùng để phóng đại số màn hình độc lập. Một thiết kế có thể được dùng chung bởi nhiều địa chỉ; một trang có thể ghép form header và form version.

| Hạng mục | Số lượng | Cách tính |
|---|---:|---|
| Phân hệ/menu nghiệp vụ | 28 | 1 lần tính +11 danh mục +8 sản xuất +2 công thức/phương án +6 giá bán; đúng các đích trong sidebar |
| Nhóm menu | 5 | Tổng quan; Dữ liệu danh mục; Sản xuất; Công thức & Quy tắc; Giá bán |
| Route trong kiểm kê | 163 | 152 đích nghiệp vụ nhận GET, 4 endpoint lựa chọn phụ thuộc, 4 hành động chỉ POST, 1 root redirect, 2 health probe |
| Đích nghiệp vụ nhận GET | 152 | Gồm list/detail/form/version/panel/trace và token catalogue; **không phải 152 thiết kế UI khác nhau** |
| Địa chỉ tạo/sửa/tạo lần tính mới | 74 | URL name kết thúc `_create`, `_edit`, `_rerun`; không nhân thành 74 lớp form |
| Lớp form được kiểm kê | 43 | 39 lớp cụ thể và 4 lớp nền không phải form độc lập |
| Form cụ thể | 39 | 37 lớp tạo/sửa/chạy và 2 lớp kiểm thử/đóng kỳ; cùng lớp dùng lại ở tạo và sửa |
| Định nghĩa trường nhìn thấy | 319 | 95 danh mục +104 sản xuất +49 công thức/giá thành +71 giá bán; không nhân đôi create/edit |
| Mẫu trường có số lượng thay đổi | 2 | Biến lá trong kiểm thử Formula; đầu vào MANUAL theo Scheme của Run |
| Hàng tham chiếu phụ thuộc/ảnh hưởng | 112 | Toàn bộ các bảng chương 13; gồm quan hệ tạo dữ liệu, nguồn thực thi, dropdown, ảnh hưởng xuôi và tra ngược; không phải 112 FK duy nhất |
| Hàng hướng dẫn lỗi | 131 | Các bảng danh mục/sản xuất/công thức/phương án/Costing/Pricing/Comparison ở chương 10; một hàng có thể gom nhiều mã/thông báo liên quan |
| Kịch bản nghiệp vụ | 20 | Mỗi bài đủ 18 điểm, tổng 360 điểm hướng dẫn |
| Bước thực hành Cappuccino | 22 | Đúng dữ liệu mẫu hiện có; bước 1–17 kiểm tra nguồn đã chuẩn bị, 18–22 thao tác tính/xem/so sánh |
| FAQ / thuật ngữ | 53 / 59 | Các câu hỏi và bảng glossary chương 11 |
| Tác vụ “muốn làm gì” | 26 | Bảng dẫn menu/hành động chương 11, ngoài các checklist vận hành |
| Năng lực được phân loại | 69 | NATIVE 30; CONFIGURABLE 6; PARTIAL 14; NOT SUPPORTED 19; chương 01 có thêm bản đồ áp dụng cho 11 ngành/mô hình |
| Nhu cầu/giới hạn trong gap register | 45 | Tách các nhu cầu còn thiếu thành hàng có hành vi hiện tại, workaround và đề xuất |
| File tài liệu mới | 18 | Sổ tay tổng hợp; README; 14 chương; gap register; biên bản này |

**Chi tiết 319 trường:** kiểm kê có 316 trường cơ sở nhìn thấy sau khi bỏ trường ẩn `RunForm.idempotency_key`; thêm `TestForm.expected` và hai biến thể ngày/thời điểm của `ClosePeriodForm` thành 319. Không gộp biến lá Formula hoặc ô MANUAL sinh động vào một con số cố định. Filter/search/sort/pagination và các thao tác không có ô nhập riêng cũng được mô tả trong chương 12.

## 3. Những claim đã chỉnh sau lượt kiểm tra thứ hai

| Cách hiểu dễ sai | Kết luận đúng theo source được dùng trong tài liệu |
|---|---|
| Có thể thiết lập toàn bộ từ database rỗng qua UI | Chưa thể: nguồn sản xuất/giá mua/rate/allocation mới ở Nháp thiếu action hiệu lực; CostPoolPeriod chưa có form. Bài DEMO nêu rõ điều kiện chuẩn bị |
| BOM hoặc Routing thuộc SKU | Header thuộc Product. Bao bì có liên kết SKU riêng; lọc theo SKU không tự tạo quan hệ BOM/Routing–SKU |
| Product có `base_uom` | Trường thực tế là `costing_uom`; SKU dùng `sales_uom`, `net_quantity`, `net_quantity_uom` |
| Có OperationResource hoặc CostPoolMember | Chưa có entity/CRUD tương ứng trong source; RoutingOperation có một `primary_resource`, pool không tự gom CostElement |
| Có lịch công suất nhập được | Không có mapping `CapacityCalendar`; dữ liệu công suất phân bổ hiện nằm trong `CostPoolPeriod`, chưa có UI nhập |
| PackagingVersion tự có lượng đầu ra | Không có output basis ở version; người chạy nhập sản lượng/đơn vị cơ sở đóng gói trên Run và lưu trong context/snapshot |
| Engine nhân cây bao bì | Hiện tính phẳng; lượng dòng phải quy về cơ sở đã nhập; không nhân thêm `units_per_parent` |
| Hao hụt chỉ cộng phần trăm; setup scale như run | Nguyên liệu = qty × scale ÷ yield ÷ (1−scrap). Setup một lần mỗi Run; run scale theo operation basis hoặc version batch |
| Driver lưu được là driver chạy được | Allocation engine chỉ NORMAL_CAPACITY. MACHINE_HOUR, PALLET_DAY và các mã khác không được mô tả thành chức năng phân bổ hoàn chỉnh |
| Giá mua 0 bị cấm hoặc field có default được để trống | SupplierPrice cho đơn giá/min_qty ≥0. min_qty và tax_recoverable_ratio bắt buộc dù form gợi ý 0/1 |
| Mọi tỷ lệ đều nhập theo cùng một cách | Pricing và các form % nhập phần trăm; SupplierPrice dùng phần số 0–1; ô MANUAL PERCENT trên Run theo phần số. Ví dụ chỉ đúng theo từng form |
| Phí/thuế có tỷ lệ hoàn/khấu trừ mặc định trống | Form tạo mới hiển thị 0 theo model default nhưng vẫn required; engine hiện chỉ xử lý giá trị 0 này |
| Form Scenario kiểm tra hash snapshot của Run | Form kiểm tra Run LOCKED, kết quả/giá vốn/sản lượng/dòng và đúng phạm vi. Không khẳng định form tự xác minh hash snapshot Run; Comparison có kiểm tra snapshot Scenario riêng |
| Run có các cột `value_money`, `value_quantity` | CostingRunLine dùng `amount`, `number_value`, `percent_value`, `quantity`, `boolean_value`, `text_value` |
| Input/source trace đều là cột của Run | `input_snapshot_jsonb` và `source_trace_jsonb` ở CostingRunLine; Run có `version_snapshot_jsonb`. Phân biệt trong phụ lục kỹ thuật |
| Ngày kết thúc giống nhau ở mọi module | Nguồn Costing bao gồm ngày cuối; Pricing dùng [start,end). Pricing FX tra tại 00:00 ngày định giá giờ Việt Nam |
| Engine chọn giá rẻ nhất/bậc cao nhất/rate_type hoặc quy đổi riêng ưu tiên | Không có những policy đó. Giá/rate/quy đổi cần nguồn phù hợp duy nhất; nhiều nguồn gây lỗi mơ hồ |
| Tạo lần tính mới là phát lại dữ liệu đã snapshot | Rerun tạo record mới và resolve nguồn hiện tại theo ngày yêu cầu. Đọc lịch sử có; replay ngoại tuyến chưa có |
| Margin lấy doanh thu chưa thuế làm mẫu số | Policy hiện tại là lợi nhuận/giá khách trả; markup là lợi nhuận/giá vốn. Phí cố định trên một đơn vị đầu ra Run |
| Pricing lỗi chuyển FAILED hoặc tính lại bản đã tính cập nhật nguồn | Lỗi giữ DRAFT và chẩn đoán. CALCULATED chỉ đọc; calculate lặp trả snapshot cũ; muốn thử dùng bản mới |
| `minimum_price` là ô nhập giá khuyến mại | Chỉ nâng sàn, không ép giá xuống. Bài giá 80.000 là tính tay ngoài hệ thống, NOT SUPPORTED cho nhập giá cố định |
| Có `seed_pricing_demo`, verify chỉ đọc | Lệnh thực là `seed_costing_demo`, `verify_costing_demo`, `verify_pricing_demo`; lệnh verify có thể tạo dữ liệu/Run/Scenario |
| Golden Pricing tương lai tự dùng giá vốn tương lai | `DEMO_PRICING_FUTURE` giữ giá vốn 58.300 và đổi phí/thuế. Dùng giá vốn 64.700 là bài kết hợp riêng, không thay Golden |
| Nút Formula/Scenario dùng nhãn tự đặt | Đã sửa theo template: Kiểm thử; Lưu bộ kiểm thử; Lưu Nháp; Tính giá bán; Nguồn và diễn giải đã lưu; So sánh kịch bản |
| Cước/kho/xuất khẩu là bộ tính chuyên biệt đã có | Chỉ tổng MANUAL đúng scope hoặc phí đã quy về đơn vị bán có thể cấu hình. Không khai có engine logistics/landed/WMS/customs |
| Tổng giá vốn hàng thương mại có thể đổi scope thành MANUFACTURING để chạy | Không làm vậy. Danh mục và chính sách bán có một phần; chưa có engine/adapter nguồn giá vốn thương mại riêng. Capability này là PARTIAL |

## 4. Kiểm thử và đối soát đã thực hiện

### Kiểm tra Django

```powershell
.\env\Scripts\python.exe manage.py check
```

**PASS:** System check identified no issues (0 silenced). Dùng virtual environment hiện có của dự án.

### Kiểm thử tự động liên quan đến tài liệu

Chạy script test hiện có với PostgreSQL 17 cô lập ở `127.0.0.1:55432`, settings test và test database riêng:

```powershell
.\scripts\test.ps1 apps.costing.test_demo apps.costing.test_run_resolvers apps.formula_engine.tests apps.pricing.test_scenario_solver apps.pricing.test_scenarios apps.pricing.test_comparison --verbosity=1
```

**PASS: 111 tests, 10,100 giây**, test database được hủy và PostgreSQL test đã dừng sau khi chạy. Đây là bộ targeted cho Golden, resolver, Formula, Pricing solver/Scenario/snapshot/Comparison; **không tuyên bố chạy lại toàn bộ regression suite**. Log phiên làm việc nằm ở `artifacts/manual-audit/documentation-tests.log` (artifact cục bộ, không cần cho người đọc bộ tài liệu).

Không chạy seed/verify trên database Supabase của doanh nghiệp. Test fixtures trong database cô lập không làm thay đổi schema nghiệp vụ hiện hành.

### Đối soát số học độc lập

Giải bằng Decimal với công thức đóng độc lập, sau đó so với solver thuần hiện có; không gọi Django/database. **14 trường hợp đều PASS**, giá quantize 8 chữ số lẻ và `giá−phí−thuế−vốn−lợi nhuận=0`.

| Trường hợp đào tạo | Giá khách trả trên một đơn vị |
|---|---:|
| Không phí/thuế, margin 20%, vốn 58.300 VND | 72.875 VND |
| Đại lý: markup 25%, phí 2%, thuế 10% | 81.965,74642127 VND |
| Sàn: phí 12%+2.000, thuế 10%, margin 20% | 102.361,11111111 VND |
| FX 0.00004 VND→USD, không phí/thuế | 2,915 USD |
| FX 0.000038, cùng vốn VND | 2,76925 USD |
| Kho/bốc xếp đã quy phí cố định 12.000 VND/đơn vị | 87.875 VND |
| Handling xuất khẩu đã quy phí cố định 0,144 USD/đơn vị | 3,095 USD |
| Golden: phí 5%+1.000, thuế 10%, margin 20% | 89.972,41379310 VND |
| Chính sách tương lai: phí 6%+1.000, thuế 11%, vốn cũ | 92.526,00506044 VND |
| Chính sách tương lai và vốn mới 64.700 | 102.511,94827101 VND |
| Golden policies, margin 10% | 78.119,76047904 VND |
| Golden policies, margin 15% | 83.628,20512821 VND |
| Golden policies, margin 20% — đối soát bài độ nhạy | 89.972,41379310 VND |
| Golden policies, margin 25% | 97.358,20895522 VND |

Golden Costing trong fixtures/kiểm thử: nguyên liệu 260.000 +bao bì 150.000 +nguồn lực 120.000 +phân bổ 53.000 = **583.000 VND/10 hộp**, **58.300 VND/hộp**. Dữ liệu tương lai cho **647.000/10 hộp**. Mức thuế/phí/FX của mọi bài là giả định đào tạo, không phải giá thị trường hoặc thuế suất pháp lý.

### Kiểm tra cấu trúc bộ tài liệu

- Đủ 18 file, mỗi file một tiêu đề chính; UTF-8 hợp lệ, không conflict marker.
- Các lượt liên kết file/source tương đối được kiểm tra: đích tồn tại; số dòng source trong liên kết không vượt độ dài file.
- Tất cả 163 route và 43 lớp form trong kiểm kê có trong chương 02; nhãn trường cơ sở nhìn thấy có trong chương 12.
- Bảng Markdown có số cột nhất quán; 20 bài đủ 18 điểm/bài; lab đủ bước 1–22; FAQ vượt yêu cầu tối thiểu 30.
- Ma trận năng lực chỉ dùng bốn mức đã quy định; các ví dụ ngành tách khỏi hành vi source và dữ liệu DEMO.

Không thay đổi template/static nên **không cần chạy lại Tailwind build** trong task tài liệu. Không chụp screenshot hay thực hiện UAT bằng trình duyệt trong phiên này; hướng dẫn văn bản được đối chiếu template/view/form hiện tại. Kiểm tra liên kết không chứng minh toàn bộ anchor Markdown được mọi trình render hỗ trợ hoặc URL ngoài luôn truy cập được.

## 5. Phần còn giới hạn và cách đọc kết luận

Không còn claim nghiệp vụ chưa xác định mà tài liệu trình bày như tính năng đã hỗ trợ. Những điều source chưa định nghĩa được giữ thành gap: policy overlap/lựa chọn nguồn, nhiều nguồn lực/công đoạn, phân bổ ngoài NORMAL_CAPACITY, Logistics/landed/actual costing, giá bán nhập tay và replay snapshot ngoại tuyến.

**Chưa xác nhận trong phạm vi task này:** dữ liệu thực tế của doanh nghiệp có đủ/đúng schema và nguồn; trạng thái DEMO trên môi trường đang triển khai; giao diện trong trình duyệt cụ thể; mức thuế/phí/FX áp dụng cho hợp đồng thật. Những mục này là điều kiện vận hành/nghiệm thu dữ liệu, không bị mô tả là đã hoàn thành. Nếu source thay đổi sau mốc trên, kiểm tra lại chương 02/12 và các quy tắc tính trước khi tiếp tục dùng bản hướng dẫn.

Nguồn ngành được dẫn tại [chương 08](08_KICH_BAN_THUC_TE.md): Microsoft, OpenStax, Shopify, Amazon, DHL và ICC. Chúng dùng để nhận diện mô hình nghiệp vụ; không dùng để suy ra tính năng, biểu phí hoặc chính sách pháp lý của hệ thống.

## 6. Đề xuất sử dụng để đào tạo

Thứ tự: **01–03 → 09 → 04–07 theo vai trò → 10–11 → 08 → 12–14 khi tra cứu**. Người mới nên hoàn tất Golden và tự giải thích ít nhất một dòng nguyên liệu, nguồn lực, phân bổ và waterfall trước khi thử giả định mới.

Các điểm dễ nhầm nhất: Item/Product/SKU; đơn vị giá so với đơn vị đầu ra; tổng lô so với giá đơn vị; trạng thái so với ngày hiệu lực; setup so với run time; dòng INPUT/SUBTOTAL/OUTPUT; margin so với markup; ngày Costing so với ngày Pricing; xem lịch sử so với tạo lần tính mới.

Ưu tiên cải tiến sau này theo gap register: hoàn thiện thao tác hiệu lực upstream và nhập kỳ chi phí → chính sách nguồn/overlap rõ ràng → preflight kiểm tra nguồn trước Run → nhu cầu giá nhập tay/đa nguồn lực/driver mới nếu doanh nghiệp xác nhận. Không triển khai các đề xuất này trong task tài liệu.
