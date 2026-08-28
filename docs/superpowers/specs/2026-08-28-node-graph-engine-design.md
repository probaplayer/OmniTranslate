# Node-Graph Engine + Web UI — Design Spec (Sub-project A)

Date: 2026-08-28
Status: Approved for planning

## Bối cảnh dự án lớn

Mục tiêu cuối cùng: một tool quản lý tiến trình dịch light novel/web novel, dùng
RAG để giữ context xuyên suốt cả bộ truyện, với giao diện dạng node-graph
(giống ComfyUI) để người dùng tự ráp pipeline dịch/review, và một MCP server
để các coding agent (Claude, Codex, OpenCode...) có thể điều khiển workspace
từ bên ngoài, hoặc dịch trực tiếp bằng API key riêng không qua MCP.

Dự án được chia thành 4 sub-project độc lập, mỗi cái có spec/plan riêng:

- **A (spec này)** — Node-graph engine lõi + Web UI, chạy được với node tiện
  ích thật (không AI) để chứng minh vòng đời workspace/graph hoạt động.
- **B** — Translation & RAG core (không cần UI): quản lý context novel,
  chunk/embedding, vector store, retrieval, gọi thẳng API key LLM để dịch.
- **C** — Tích hợp B vào A: các node thật (Load Novel, Build RAG Context,
  Translate Chunk, Review/Diff, Auto-continue-to-final).
- **D** — MCP server để Claude/Codex/OpenCode điều khiển workspace từ ngoài.

Spec này chỉ đặc tả **Sub-project A**.

## Mục tiêu Sub-project A

Xây dựng nền tảng node-graph engine + web UI để sau này cắm node dịch/RAG
thật vào (Sub-project C), gồm 2 giai đoạn:

- **A1**: engine lõi — registry node, executor DAG, web UI canvas, quản lý
  workspace, node tiện ích thật (không AI).
- **A2**: khả năng lặp (Loop Group) + hệ thống template.

## Kiến trúc tổng quan

Mô hình theo đúng ComfyUI: Python backend phục vụ frontend tĩnh dùng
litegraph.js vẽ canvas, không cần build step (không React/webpack).

```
run.bat
  → tạo/kích hoạt venv, cài requirements lần đầu
  → khởi động Python server (FastAPI/aiohttp + uvicorn)
  → mở trình duyệt tới http://localhost:<port>

Browser (litegraph.js canvas, thuần HTML/JS)
  ↔ REST API: workspace CRUD, node registry, save/load graph, template CRUD
  ↔ WebSocket: queue execution, nhận event node_started/completed/error

Python backend
  - Workspace manager (filesystem-based)
  - Node registry (base class + node implementations)
  - Graph executor (topological sort + Loop Group)
```

## Thành phần chi tiết

### 1. Workspace manager
- Màn hình chọn/tạo workspace hiện ra trước khi vào canvas.
- Mỗi workspace = 1 thư mục riêng dưới `workspaces/<name>/`:
  ```
  workspaces/<name>/
    config.json       # tên, ngôn ngữ nguồn/đích, thời điểm tạo/sửa
    graph.json         # graph hiện tại của workspace
    chapters/           # input thô
    output/             # kết quả node ghi ra
  ```
- API: list workspaces, create, open (trả về graph.json), delete.

### 2. Node registry & base class
- Mỗi node là 1 class Python định nghĩa (theo đúng convention ComfyUI để dễ
  mở rộng sau này ở Sub-project C):
  - `INPUT_TYPES()` — khai báo input (tên, kiểu, optional/required, default).
  - `RETURN_TYPES` — kiểu output.
  - `CATEGORY` — nhóm hiển thị trong sidebar (vd: "Utility", "Flow").
  - `execute(**inputs)` — logic thực thi, trả tuple theo `RETURN_TYPES`.
- Backend expose registry qua REST API để frontend build node palette động
  (không hardcode danh sách node ở frontend).

### 3. Node tiện ích MVP (A1, thật, không AI)
- `Load Text File` — đọc 1 file text, trả nội dung string.
- `Save Text File` — ghi string ra file.
- `Text Preview` — hiển thị nội dung string trong canvas (không có output).
- `Note/Comment` — ghi chú tự do trên canvas, không tham gia execution.

### 4. Graph executor
- Nhận graph JSON (node + link), validate:
  - Phát hiện cycle không hợp lệ (Loop Group không tính là cycle, xử lý
    riêng — xem mục 5).
  - Phát hiện input required còn thiếu → chặn chạy, báo lỗi rõ ràng trước
    khi execute bất kỳ node nào.
- Topological sort rồi chạy tuần tự từng node.
- Không cache kết quả giữa các lần chạy ở A1 (YAGNI — thêm sau nếu cần).
- Lỗi ở 1 node: dừng các node phía sau phụ thuộc vào nó (đánh dấu "skipped"),
  các nhánh độc lập khác trong cùng graph vẫn tiếp tục chạy bình thường.
- Mỗi lần chạy stream qua WebSocket các event: `node_started`,
  `node_completed` (kèm output/log rút gọn), `node_error` (kèm message),
  `run_finished`.

### 5. Loop Group (A2)
- Người dùng chọn 1 cụm node trên canvas → "Group into Loop" → cụm này co
  lại thành 1 node duy nhất (`Loop Group`) trên graph cha.
- Bên trong Loop Group có 2 node đặc biệt: `Loop Item In` (phát ra từng phần
  tử của list input) và `Loop Collect Out` (gom output từng lần lặp thành 1
  list).
- Executor chạy: với mỗi phần tử trong list đầu vào của Loop Group, chạy lại
  toàn bộ subgraph bên trong 1 lần, dùng `Loop Item In` làm giá trị hiện tại;
  gom kết quả `Loop Collect Out` thành list trả về node `Loop Group` ở graph
  cha.
- Lỗi trong 1 lần lặp: dừng toàn bộ Loop Group tại vòng lặp lỗi đó (không
  chạy tiếp các phần tử còn lại), báo rõ đang lỗi ở phần tử thứ mấy.

### 6. Template system (A2)
- Lưu 1 graph hiện tại thành template có tên (khác với workspace — template
  không gắn với data cụ thể, chỉ là cấu trúc graph để tái dùng).
- Template lưu ở `templates/<name>.json`, dùng chung cho mọi workspace.
- Kèm sẵn 2-3 template mẫu khi cài đặt lần đầu:
  - "Dịch 1 chương" — Load Text File → (placeholder node dịch) → Save Text
    File → Text Preview.
  - "Dịch cả bộ qua Loop" — Load Text File (danh sách chương) → Loop Group
    (chứa pipeline dịch 1 chương) → Save Text File.
  - Ghi chú: các template này dùng node tiện ích MVP để minh họa cấu trúc;
    khi Sub-project C xong sẽ có thêm template dùng node dịch/RAG thật.

## Data flow (chạy 1 lần)

1. Mở `run.bat` → server khởi động → browser mở tới `localhost:<port>`.
2. Chọn hoặc tạo workspace → canvas nạp `graph.json` của workspace đó.
3. Người dùng chỉnh graph (thêm node, nối dây) hoặc nạp từ template.
4. Nhấn "Run" → frontend gửi graph hiện tại qua WebSocket.
5. Backend validate → topo sort → chạy từng node → stream event realtime.
6. Frontend tô màu node theo trạng thái (đang chạy/xong/lỗi), cập nhật panel
   preview/log.
7. Xong: người dùng có thể lưu graph vào workspace và/hoặc lưu thành
   template mới.

## Error handling

- Validate graph trước khi chạy (cycle, input thiếu) — chặn sớm, không chạy
  dở dang.
- Lỗi runtime của 1 node — bắt exception, gắn vào event `node_error`, đánh
  dấu các node phụ thuộc là "skipped", không crash toàn bộ server.
- `graph.json`/`config.json` hỏng hoặc sai schema khi load — trả lỗi rõ ràng
  qua API, không crash server, không xóa file gốc.

## Testing

- Backend: pytest cho graph executor (topo sort đúng thứ tự, lan truyền lỗi
  dừng đúng nhánh, Loop Group lặp đúng số lần và gom kết quả đúng).
- Integration: workspace mẫu `Load Text File → Loop Group → Save Text File`
  chạy end-to-end trên vài file giả lập, assert nội dung file output.
- Frontend: kiểm thử thủ công qua browser ở giai đoạn này (chưa cần
  Playwright/E2E tự động).

## Ngoài phạm vi (out of scope) của spec này

- Bất kỳ logic gọi AI/LLM thật nào (dịch, review) — thuộc Sub-project B/C.
- RAG/embedding/vector store — thuộc Sub-project B.
- MCP server — thuộc Sub-project D.
- Cache kết quả node giữa các lần chạy — có thể thêm sau nếu cần, không bắt
  buộc cho A.
- Auth/multi-user — tool chạy local single-user qua `run.bat`.

## Cấu trúc thư mục dự kiến

```
MCPToolTranslaterNovel/
  run.bat
  requirements.txt
  server/
    main.py              # entrypoint FastAPI/aiohttp + websocket
    executor.py           # graph executor + Loop Group
    node_registry.py      # base class + registry
    nodes/
      utility.py           # Load/Save Text File, Text Preview, Note
      flow.py                # Loop Item In / Loop Collect Out
    workspace.py           # workspace CRUD (filesystem)
    templates.py            # template CRUD
  web/
    index.html
    js/
      litegraph.js (vendored hoặc npm-installed rồi copy build)
      app.js               # kết nối API/WebSocket, custom node rendering
    css/
  workspaces/               # tạo runtime, không commit data thật
  templates/
    single-chapter.json
    full-novel-loop.json
  docs/superpowers/specs/
    2026-08-28-node-graph-engine-design.md
```
