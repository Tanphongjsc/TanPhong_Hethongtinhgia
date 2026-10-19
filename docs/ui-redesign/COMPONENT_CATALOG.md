# Component catalog

Các include Django hiện có cùng CSS `ui-*` tạo design system. Không tạo model, frontend framework hoặc business state mới. Mỗi component kế thừa tokens tại [DESIGN_SYSTEM](DESIGN_SYSTEM.md).

| Component / pattern | Mục đích | Variants / size | States | Quy tắc dùng | Không dùng khi |
|---|---|---|---|---|---|
| Button | Hành động trang/form | Primary, secondary, ghost, danger; sm/md | Default, hover, focus, active, disabled, loading | Một primary nổi bật; giữ href/type/form/name/value | Cần thay đổi workflow để đưa vào button |
| Icon / icon action | Navigation, thao tác hàng | Lucide SVG; 16/18/20px | Hover, focus, disabled, tooltip | Accessible name, tooltip; giữ text sr-only khi thay text action | Ý nghĩa hành động chưa đủ rõ để bỏ text |
| Input/select/textarea | Nhập trường hiện có | md; textarea nhiều dòng | Focus, error, disabled, readonly | Giữ name/type/value/choices/default, native select | Muốn thêm autocomplete hoặc dữ liệu mới |
| Checkbox/radio | Lựa chọn hiện có | Native control | Checked, focus, disabled/error | Label liên kết; accent Indigo | Không có trường tương ứng |
| Form field | Label/*/control/help/error | Một cột hoặc span hai cột | Required, optional, invalid | Dùng components/form_field; focus lỗi sau submit | Muốn đổi required semantics |
| Form sections | Nhóm trường | Grid responsive | Native/HTMX validation | Giữ section và thứ tự có nghĩa | Tách form làm mất POST payload |
| Search/filter | Bộ lọc server-side | Search icon/control/select/date | Loading, focus, empty | Debounce và hx attrs giữ nguyên | Không có filter backend |
| Table/table toolbar | Đọc dữ liệu nhiều cột | Gọn/Thoáng | Hover, sort, loading, empty | Số phải; scroll; không giấu cột | Dữ liệu thích hợp với description list đơn giản |
| Pagination | Chuyển trang và page size | Existing 25/50/100 | Current, hover/focus | Query/preserved IDs giữ nguyên | Dự định load toàn bộ vào JS |
| Panel/card | Ranh giới dữ liệu | Border, subtle background | Default | Một boundary hữu ích; không lồng nhiều card | Chỉ cần spacing/section divider |
| Metric | Số tài chính backend có sẵn | Normal/emphasis | Readonly | Giá trị/đơn vị đã có, không tự tính | KPI hoặc delta chưa tồn tại |
| Status/version badge | Trạng thái/phiên bản | Neutral/info/success/warning/danger | Readonly | Giữ stored code/display mapping | Tạo status hoặc workflow mới |
| Breadcrumb/page header | Vị trí và hành động chính | Responsive | Link focus, active context | Dùng breadcrumb context và primary action hiện có | Có nhu cầu thêm route |
| Tooltip | Giải nghĩa icon | Floating small | Hover/focus, Escape | Text ngắn, không thay accessible name | Nội dung cần đọc lâu/tương tác |
| Dropdown/action menu | Hành động hỗ trợ hiện có | Compact | Open/closed/focus | Native disclosure hoặc Alpine state hiện có | Chưa có action backend |
| Modal | Xác nhận/quick action | max-lg | Open/closed, focus trap, reduced motion | Giữ confirmation/form target | Form dài hoặc workflow dedicated |
| Drawer | Detail/chỉnh dòng theo ngữ cảnh | Contextual right panel | Open/closed, focus trap, errors | Giữ HTMX/editor target và submit | Chuyển drawer làm đổi navigation semantics |
| Toast | Feedback hiện có | Success/info/warning/error | Visible/dismissed | Nội dung nguyên trạng, đóng tay, timeout theo severity | Validation lỗi chỉ được báo bằng toast |
| Empty state | Không có dữ liệu/kết quả | Compact icon + text + optional CTA | Empty/filtered | CTA chỉ khi có URL/action hiện tại | Muốn tạo nghiệp vụ chưa có |
| Spinner/skeleton | Đang xử lý | Contextual small | Busy/idle, reduced motion | Không layout jump; aria-busy; không đổi request | Thay nội dung thật bằng loading vô thời hạn |
| Alert/error summary | Lỗi/cảnh báo/validation | Danger/warning/info | Persistent, focus links | Giữ nguyên message và trace reference | Che business error hoặc traceback |
| Section heading/description list | Nhóm metadata và nguồn | Compact | Readonly | Giữ labels/value/formatting | Có nhu cầu tính thêm metadata |
| Tabs/disclosure | Hiển thị vùng hiện có | Native details/Alpine local | Open/closed | Không giấu trường nghiệp vụ bắt buộc | Chưa cần tabs hoặc phải đổi request |

Component chưa có use case thực tế dùng pattern CSS thay vì tạo include rỗng. Primary workflow vẫn là Django rendering + HTMX; Alpine chỉ giữ state trình bày.
