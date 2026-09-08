# Canvas UI Redesign — Design Spec

Date: 2026-09-08
Status: Approved for planning

## Bối cảnh

Trong lúc brainstorm Sub-project B, bạn đưa ra 1 mockup UI chi tiết
(`template_translation_workflow/Translation Workflow.dc.html`, xem qua
`.thumbnail`) và muốn canvas hiện tại của Sub-project A (litegraph.js)
được đổi giao diện/tương tác theo phong cách đó. Quyết định phạm vi đã
chốt lúc đó (ghi trong memory `pending_ui_redesign.md`) và xác nhận lại
khi brainstorm spec này:

- **Giữ nguyên 6 node nguyên tử** của Sub-project C (`Provider`,
  `LoadAgentFile`, `SaveAgentFile`, `RAGQuery`, `SaveToRAG`, `Translate`)
  — KHÔNG gộp lại thành 5 node tổng hợp như mockup.
- **Đổi mô hình sửa thuộc tính node**: từ widget ngay trên thân node
  sang 1 panel "Chi tiết node" cố định bên phải — đây là thay đổi kiến
  trúc lớn nhất, không phải chỉ đổi màu.
- 4 tính năng "chrome" phụ đều được chọn: log console, minimap, panel
  chạy hàng loạt (chỉ UI shell, chưa có backend), nút chuyển ngôn ngữ
  VI/EN.

Đây không phải sub-project mới trong 4 sub-project ban đầu (A/B/C/D) —
là 1 lần cải tiến UI của Sub-project A đã merge, phạm vi thuần frontend.

## Mục tiêu

Đổi giao diện + mô hình tương tác của `web/canvas.html` và
`web/index.html` theo đúng bảng màu/font/bố cục của mockup, đồng thời
thêm panel sửa thuộc tính bên phải, log console, minimap, panel batch
(UI shell), và chuyển ngôn ngữ VI/EN — mà KHÔNG đổi bất kỳ gì ở backend
(`server/`) hay ở `translation_core/`.

## Kiến trúc tổng quan

```
web/
  css/
    style.css                # viết lại: token màu/font theo mockup, layout 3 cột mới
  js/
    litegraph.js               # không đổi (vendor)
    nodegen.js                   # sửa: bỏ addWidget cho input STRING (panel phải đảm nhận việc sửa)
    node_palette.js                # sửa nhỏ: dùng token màu/i18n mới, không đổi logic kéo-thả
    inspector_panel.js               # MỚI: panel phải — hiện form sửa dựa trên INPUT_TYPES() của node đang chọn
    log_console.js                     # MỚI: panel log dưới canvas, nhận event từ canvas_app.js
    minimap.js                           # MỚI: canvas nhỏ vẽ vị trí node + khung nhìn hiện tại
    batch_panel.js                         # MỚI: panel UI shell (chưa chạy được thật)
    i18n.js                                  # MỚI: bảng chuỗi vi/en + hàm t()/applyTranslations()
    canvas_app.js                              # sửa: nối inspector/log/minimap vào vòng đời hiện có
  canvas.html                                    # sửa: layout 3 cột mới (palette | canvas+log+minimap | inspector)
  index.html                                       # sửa: áp token màu mới + data-i18n
```

Không file nào ở `server/` hay `translation_core/` bị đổi.

## Thành phần chi tiết

### 1. Token màu/font (`web/css/style.css`)

Thay toàn bộ `:root` hiện tại bằng bảng màu lấy trực tiếp từ mockup:
nền `#101216`, panel `#14161b`/`#16181d`/`#1a1d23`/`#1c1f25`, viền
`#24282f`/`#2a2f37`/`#23272e`, chữ chính `#e9e7e2`, chữ phụ
`#9aa1ab`/`#767d88`/`#6f7681`, accent `#d9a44c` (hover `#efc57e`), màu
trạng thái idle `#6b7280`/running=accent/done `#7fb98a`/error `#d97070`.
Font `Space Grotesk` (UI) + `IBM Plex Mono` (nhãn, số liệu) — nạp qua
Google Fonts `<link>` (đã có sẵn tiền lệ dùng CDN font ở dự án khác
trong repo này). Áp dụng nhất quán cho `index.html` (giữ layout picker
hiện tại, chỉ đổi token) và `canvas.html` (layout mới, xem mục 8).

### 2. Panel "Chi tiết node" (`web/js/inspector_panel.js`) — thay đổi chính

**Bỏ widget trên thân node**: `nodegen.js`'s `registerDynamicNodeTypes`
không còn gọi `this.addWidget(...)` cho input STRING — chỉ giữ
`this.addInput(...)` (để nối dây) và khởi tạo `this.properties[name]`
như cũ. `node.properties` vẫn là nguồn dữ liệu duy nhất (không đổi gì ở
`buildExecutionPayload`), nên save/load workflow (`graph.serialize()`/
`configure()`) hoạt động y nguyên.

**Panel phải** lắng nghe lựa chọn node qua 2 hook có sẵn của
`LGraphCanvas` (đã verify trực tiếp trong `web/js/litegraph.js`):
`canvas.onNodeSelected(node)` và `canvas.onNodeDeselected(node)`. Khi 1
node được chọn:
- Hiện tiêu đề node + input để đổi tên (`node.title`).
- Với mỗi input trong `INPUT_TYPES()` của node có type `"STRING"` VÀ
  chưa được nối dây (dùng lại logic `linkedInputNames()` đã có trong
  `nodegen.js`) → hiện 1 ô nhập text, giá trị hiện tại lấy từ
  `node.properties[name]`, khi đổi thì ghi thẳng lại vào
  `node.properties[name]` và gọi `graph.setDirtyCanvas(true, true)`.
- Input type khác `"STRING"` (`PROVIDER`, `RAG_EXAMPLES`) hoặc đã nối
  dây → không hiện trong panel (chỉ nhận qua dây, đúng như thiết kế
  node hiện tại).
- Nút "Chạy node này": ráp 1 payload tạm chỉ chứa node đang chọn
  (`{nodes: [nodeData], links: []}`) và gửi qua đúng
  `/ws/run/{workspace}` hiện có — không cần đổi gì ở backend. Nếu node
  có input bắt buộc chỉ nhận qua dây (vd `Translate`'s `provider`), lệnh
  chạy riêng sẽ báo lỗi thiếu input rõ ràng (giới hạn đã biết, chấp
  nhận được — không phải bug).
- Nút "Xoá": gọi `graph.remove(node)`.
- Khi không chọn node nào: hiện text gợi ý ("Chọn 1 node trên canvas để
  xem chi tiết").

### 3. Log console (`web/js/log_console.js`)

Panel thu gọn được ở dưới canvas. `canvas_app.js`'s `runGraph()`'s
`ws.onmessage` (nguồn sự kiện duy nhất, không đổi) gọi thêm 1 dòng
`appendLogEntry(event)` cho mỗi event nhận được. `log_console.js` chỉ
lo hiển thị: mỗi dòng gồm giờ:phút:giây + tên node + nội dung rút gọn,
có nút "Xoá log" và nút thu gọn/mở rộng panel.

### 4. Minimap (`web/js/minimap.js`)

litegraph.js không có sẵn minimap — tự vẽ. 1 `<canvas>` nhỏ (~176×112px,
theo mockup) vẽ: hình chữ nhật nhỏ cho từng node (từ `graph._nodes[i].pos`
và `.size`, co giãn theo bounding-box tổng của tất cả node), và 1 khung
viền sáng hơn thể hiện vùng đang nhìn thấy trên canvas chính (tính từ
`canvas.ds.offset`/`canvas.ds.scale` và kích thước canvas chính). Vẽ lại
định kỳ bằng `setInterval` (vd mỗi 200ms) — không cần móc vào vòng lặp
render nội bộ của litegraph. Bấm vào minimap sẽ đổi `canvas.ds.offset`
tương ứng rồi `canvas.setDirtyCanvas(true, true)` để nhảy tới vị trí đó.

### 5. Panel "Chạy hàng loạt" (`web/js/batch_panel.js`) — chỉ UI shell

Toggle mở/đóng từ nút trên toolbar, hiện đúng bố cục mockup (Từ
chương/Đến chương/Chạy song song + nút "Bắt đầu"). Nút "Bắt đầu" khi
bấm chỉ hiện thông báo rõ ràng (vd trong `log_console.js` hoặc 1 dòng
text trong panel): "Cần Sub-project A2 (Loop Group) — chưa khả dụng." —
không giả vờ chạy được gì.

### 6. Chuyển ngôn ngữ VI/EN (`web/js/i18n.js`)

```js
const STR = { vi: { ... }, en: { ... } };
function currentLang() { return localStorage.getItem("lang") || "vi"; }
function t(key) { return (STR[currentLang()] || STR.vi)[key] || key; }
function setLang(lang) { localStorage.setItem("lang", lang); applyTranslations(); }
function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}
```

Mọi chuỗi hiển thị tĩnh trong `index.html`/`canvas.html` chuyển sang
`data-i18n="key"` thay vì viết cứng tiếng Việt; chuỗi do JS tự tạo
(`workspace_picker.js`, `node_palette.js`, `inspector_panel.js`,
`log_console.js`, `batch_panel.js`, các message lỗi trong
`canvas_app.js`) gọi `t(key)` khi set `textContent`. `applyTranslations()`
chạy lúc tải trang và mỗi khi bấm nút đổi ngôn ngữ. Danh sách key cụ thể
(khoảng 25-30 chuỗi) sẽ liệt kê đầy đủ ở plan, không liệt kê hết ở spec
này.

### 7. Chạy 1 node riêng lẻ (phần của mục 2)

Đã mô tả trong mục 2 — dùng lại nguyên `/ws/run/{workspace}` với payload
chỉ chứa 1 node, không cần thay đổi executor/backend.

### 8. Layout mới của `canvas.html`

Grid 3 cột giống mockup: palette trái (~212-220px, giữ nguyên
`node_palette.js` hiện có, chỉ đổi style) | cột giữa (toolbar + canvas +
minimap ở góc dưới trái + log console thu gọn ở dưới) | panel phải
(~344px, `inspector_panel.js`). Thanh toolbar trên cùng: tên workspace,
nút mở panel batch, nút "Chạy toàn bộ" (hành vi y hệt nút Run hiện tại,
đổi tên qua i18n), nút chuyển VI/EN.

## Data flow (khi chọn và sửa 1 node)

1. Người dùng click chọn node trên canvas → litegraph gọi
   `canvas.onNodeSelected(node)`.
2. `inspector_panel.js` đọc `INPUT_TYPES()` của `node.constructor` (đã
   có sẵn cách lấy qua registry/metadata tương tự `nodegen.js`), lọc ra
   input STRING chưa nối dây, render form.
3. Người dùng sửa 1 ô → ghi vào `node.properties[name]`, gọi
   `graph.setDirtyCanvas(true, true)` để node trên canvas re-render (nếu
   node có hiện giá trị gì đó trên thân, ví dụ chấm trạng thái không đổi
   theo input nên không ảnh hưởng hiển thị, chỉ là để chắc chắn litegraph
   biết có thay đổi).
4. Bấm "Lưu" (nút Save toolbar hiện có) → `graph.serialize()` gửi lên
   `PUT /api/workspaces/{name}/graph` như cũ — properties đã sửa được
   lưu đúng vì cơ chế lưu trữ không đổi.

## Error handling

Không có cơ chế lỗi mới — mọi lỗi (chạy 1 node riêng thiếu input, panel
batch chưa khả dụng) hiển thị rõ ràng bằng text tĩnh hoặc tái dùng đúng
convention `setStatus()`/log console đã có, không có gì âm thầm thất
bại.

## Testing

Không có test tự động cho phần này (đúng convention frontend của dự án)
— verify bằng browser thật (Playwright qua MCP tool nếu có trong session
thực thi, fallback đọc DOM/console log thủ công nếu không có) sau từng
nhóm task: chọn node → sửa qua panel phải → chạy → lưu → tải lại đúng dữ
liệu; kéo-thả từ palette vẫn hoạt động; log console nhận đúng sự kiện;
minimap vẽ đúng vị trí node; nút VI/EN đổi đúng toàn bộ chuỗi hiển thị;
panel batch hiện đúng, nút Bắt đầu hiện thông báo rõ ràng thay vì chạy
ngầm gì đó.

## Ngoài phạm vi (out of scope)

- Bất kỳ thay đổi nào ở `server/` hoặc `translation_core/`.
- Chạy hàng loạt thật (thuộc Sub-project A2 — Loop Group).
- Gộp 6 node nguyên tử thành node tổng hợp như mockup.
- Preview/chip chi tiết trên thân node như mockup (giữ thân node gọn:
  tiêu đề + chấm trạng thái + cổng nối) — có thể bổ sung sau nếu cần,
  không phải MVP của lần redesign này.
- Lưu/tải template workflow (Sub-project A2).

## Cấu trúc thư mục dự kiến (thay đổi so với hiện tại)

```
web/
  css/style.css                (viết lại)
  js/
    nodegen.js                   (sửa: bỏ addWidget cho STRING)
    node_palette.js                (sửa nhỏ: style/i18n)
    inspector_panel.js               (MỚI)
    log_console.js                     (MỚI)
    minimap.js                           (MỚI)
    batch_panel.js                         (MỚI)
    i18n.js                                  (MỚI)
    canvas_app.js                              (sửa: nối các module mới)
  canvas.html                                    (sửa: layout 3 cột mới)
  index.html                                       (sửa: token màu + data-i18n)
```
