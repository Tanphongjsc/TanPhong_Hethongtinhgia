# Design system — Giá thành & giá bán

Modern enterprise, data-dense, light theme. Tập trung vào dữ liệu và hành động hiện có, giữ toàn bộ thuật ngữ nghiệp vụ tiếng Việt.

## Token triển khai

Nguồn duy nhất cho tokens/styles: `static/src/tailwind.css`; Tailwind 4.3.3 build sang `static/css/app.css`. Không chỉnh generated CSS. Component/pattern dùng tiền tố `ui-`, giữ utility layout khi cần; không xây generic component framework.

| Nhóm | Quy ước |
|---|---|
| Primary | Indigo 600 `#4f46e5`; hover Indigo 700 `#4338ca`; soft Indigo 50 `#eef2ff` |
| Neutral | Slate 50/100 background; Slate 200 border; Slate 800 body `#1e293b`; Slate 600 secondary `#475569`; Slate 900 heading |
| Semantic | Emerald success, Amber warning, Red danger, Blue info; chữ/biểu tượng đi cùng màu |
| Font | Inter variable, Latin + Vietnamese WOFF2 local; fallback Segoe UI/system sans |
| Page heading | 24px/32px, weight 650, tracking nhẹ |
| Section heading | 16px/24px, weight 650 |
| Body/table | Body 15px, table 14px/22px, header 13px/20px; tiền và số có tabular-nums |
| Label/helper | Label 14px/20px, helper 13px/20px; helper Slate 600; error Red 700 |
| Financial metric | 24–28px, weight 650, tabular numbers; không tính thêm dữ liệu |
| Code | Consolas/Liberation Mono/system monospace, 13px; ô soạn công thức 14px |
| Spacing | Cơ sở 4px; control gap 8px; nhóm 16px; section 24px |
| Radius | Control/panel 8px; badge pill; không rounded lớn đại trà |
| Shadow | Panel border chính; shadow nhỏ cho menu, modal, drawer, tooltip |
| Focus | Indigo outline/ring rõ, offset; không xóa focus mà thiếu thay thế |
| Motion | 150–200ms; hover/opacity/local overlays; respect prefers-reduced-motion |
| Z-index | Table header 10; topbar 30; sidebar/overlay 40; dialog 50; toast 60; tooltip 70 |
| Width | Table/detail tận dụng workspace; form tối đa khoảng 64rem |
| Density | Gọn khoảng 44px/row; Thoáng khoảng 52px/row; localStorage, không DB |

## Navigation

Sidebar giữ nhóm/thứ tự/menu/routes và 240px expanded/72px collapsed. Expanded: icon + nhãn 14px/22px, weight 500, Slate 700; tiêu đề nhóm 12px/18px, Slate 600. Nhãn dài được xuống dòng, không cắt chữ. Collapsed: icon + tooltip, mọi đích vẫn truy cập được. Mobile overlay dưới 992px, Escape/focus trap/inert giữ nguyên. Topbar gọn chứa toggle, breadcrumb/context và density control. Không global search giả hoặc UI tài khoản/công ty.

Chỉ animate width/padding khi người dùng chủ động toggle sidebar. Lần render đầu và thay đổi breakpoint phải có layout đúng ngay, không trượt nội dung dưới sidebar.

## Button và thao tác

Primary chỉ cho hành động chính; secondary cho thao tác hỗ trợ; ghost cho hành động nhẹ; danger cho xóa/ngừng khi phù hợp. Row action dùng Lucide + accessible label/tooltip, giữ confirmation và request attributes. Size sm/md; transition nhẹ; disabled/loading rõ.

## Form

Label giữ nguyên, dấu * theo `field.field.required`, helper/error liên kết input. Không đổi defaults/choices/readonly hoặc required. Section rõ, hai cột desktop/một cột mobile; mô tả dài trải rộng. Submit lỗi native/HTMX đưa focus tới ô lỗi đầu tiên. Long/complex workflow vẫn là full page; không chuyển container làm thay đổi flow.

## Table

Header neutral, text trái/số phải/code monospace, trạng thái semantic; hover không đổi kích thước. Search/filter/sort/pagination giữ nguyên server-side và query URL. Chỉ scroll vùng bảng, không ẩn cột. Comparison có sticky identifier để giữ ngữ cảnh. Density thay padding/chiều cao; không đổi số dòng mỗi trang.

## Detail, metrics và trace

Metadata dùng description list; KPI chỉ dùng tổng/đơn vị/result_fields đã có. Waterfall dùng row hierarchy từ dữ liệu đã lưu, không tính phần trăm/độ rộng biểu đồ trong JS. Snapshot/trace vẫn đầy đủ và đúng nguồn; disclosure chỉ điều khiển hiển thị.

## States và accessibility

Empty state có icon nhỏ, mô tả hiện có và CTA hiện có. Loading contextual ở filter/table/action, aria-busy không khóa cả trang. Toast giữ nội dung, severity, đóng tay; lỗi không biến mất quá nhanh. Modal/drawer giữ focus trap và trả focus; tooltip hỗ trợ keyboard. Label, th/scope, aria-current và focus-visible được giữ.

## Local assets và production

Lucide static chỉ build tập SVG được dùng thành sprite; không tải icon JavaScript runtime. Inter chỉ copy hai subset Latin/Vietnamese cần dùng và license. Build vẫn `npm ci`, `npm run build`; WhiteNoise/collectstatic xử lý đường dẫn tương đối/hash. Không CDN, không đổi Render start command.

Tham chiếu cách đóng gói: [Lucide static](https://lucide.dev/guide/static), [Fontsource Inter](https://fontsource.org/fonts/inter). Đây là nguồn tài nguyên thiết kế, không là dependency runtime bên ngoài.
