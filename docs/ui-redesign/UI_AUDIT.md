# Audit UI trước redesign

Audit source/template ngày 16/10/2026; baseline và phạm vi đóng băng tại [UI_BASELINE](UI_BASELINE.md).

| Màn hình / component | Vấn đề trước thay đổi | Mức độ | Hướng sửa trình bày |
|---|---|---|---|
| Sidebar | Thu gọn chỉ còn nút DM, toàn bộ liên kết nghiệp vụ bị ẩn | High | Giữ 28 liên kết ở rail icon, tooltip và active state; giữ width 240/72px để tương thích kiểm thử |
| App shell | Topbar lặp tên chung; breadcrumb/context ở ngoài topbar, hierarchy yếu | Medium | Topbar breadcrumb gọn; page header rõ; content có min-width 0 và vùng bảng riêng |
| Primary/secondary actions | Utility strings lặp lại, row links và nút mỗi module khác nhau | High | Button tokens chung; icon actions Lucide giữ accessible name và text sr-only |
| Table | Header/row padding không thống nhất; numeric/code chưa tạo nhịp quét rõ | High | 13px/tabular numbers, divider nhẹ, hover, density, overflow và sticky header phù hợp |
| Form | Widget styles phân tán; lỗi/readonly chưa nổi rõ; section hierarchy còn thô | High | Input/label/helper/error tokens; field section hai cột; focus lỗi đầu tiên |
| Filter/search | Input và select khác chiều cao/padding; search thiếu cue thị giác | Medium | Control tokens, icon search, toolbar đồng nhất; không sửa debounce/query |
| Detail danh mục/sản xuất | Nhiều block cùng trọng lượng; link thao tác không có hierarchy | Medium | Description list, section header, action styles và data panel |
| Formula Studio | Editor, palette, validation và thử tính khó phân biệt | High | Workspace chia vùng rõ, code typography, trạng thái/error panel; giữ nguyên editor/input/action |
| Costing Run | Tổng/đơn vị trình bày giống trường metadata thường | High | Financial metric hierarchy; breakdown/table và nguồn/trace rõ |
| Pricing Scenario | Summary nhiều số đồng trọng lượng; waterfall như bảng thường | High | Metric grid từ result_fields có sẵn, waterfall row hierarchy, nguồn disclosure |
| Comparison | Mốc và cột kịch bản chưa nổi rõ; bảng rộng khó giữ ngữ cảnh | Medium | Sticky chỉ tiêu/header trong vùng scroll; baseline tinh tế; không tính delta mới |
| Modal/drawer | Border/radius đơn giản; close action bằng dấu ×, focus cue chưa thống nhất | Medium | Lucide close, overlay/shadow nhẹ, focus trap giữ nguyên, reduced motion |
| Empty/loading/toast | Trạng thái trống/tải chưa có visual identity thống nhất | Medium | Icon/skeleton/spinner contextual; toast có semantic tone và nút đóng |
| Responsive | Một số hàng action/toolbar không có min-width rõ; bảng dễ tạo page overflow | High | Responsive container/toolbar; bảng scroll, không giấu cột nghiệp vụ |
| Accessibility | Icon actions cần tên/tooltip; lỗi sau swap chưa đưa focus đúng chỗ | High | Giữ label association, accessible text; keyboard tooltip, focus error và motion preference |

Không dùng audit này để sửa business gap. Những giới hạn như hiệu lực nguồn upstream, phân bổ, FX Costing hay giá nhập tay giữ nguyên.

## Reference screens

1. **Vật tư / Hàng hóa — list:** nhiều cột quan hệ, code, trạng thái và thao tác; kiểm tra density/scroll/filter/pagination.
2. **Vật tư / Hàng hóa — form:** 17 trường, nhiều section, số đo và dropdown; kiểm tra required/helper/error và desktop/mobile layout.
3. **Costing Run + Pricing Scenario — detail:** tổng lô/đơn vị và waterfall nguồn đã lưu; kiểm tra hierarchy tài chính mà không tạo thêm metric.

Sau khi các pattern này ổn, rollout lần lượt danh mục → sản xuất → công thức/phương án → Run → Pricing/Comparison. Không thiết kế mỗi trang theo một hệ riêng.
