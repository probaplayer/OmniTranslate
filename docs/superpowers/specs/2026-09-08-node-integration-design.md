# Node Integration — Design Spec (Sub-project C)

Date: 2026-09-08
Status: Approved for planning

## Bối cảnh dự án lớn

4 sub-project đã chốt (xem spec Sub-project A:
`docs/superpowers/specs/2026-08-28-node-graph-engine-design.md`, và spec
Sub-project B: `docs/superpowers/specs/2026-09-07-translation-rag-core-design.md`):

- **A** — Node-graph engine lõi + Web UI (đã hoàn thành, merge vào `master`).
- **B** — Translation & RAG core: `translation_core/` package thuần Python
  (đã hoàn thành, merge vào `master`) — Provider abstraction, RAGStore,
  agent file loader, `translate_chunk()`.
- **C (spec này)** — Tích hợp B vào A: node thật (Provider, RAG, Agent
  File, Translate) đăng ký vào node registry của A, ráp được trên canvas.
- **D** — MCP server để Claude/Codex/OpenCode điều khiển workspace từ ngoài.

## Ghi chú UI (không thuộc phạm vi spec này)

Phản hồi về UI của A (vào thẳng canvas thay vì màn chọn workspace, lưu
bằng Ctrl+S) đã ghi trong spec B, vẫn để dành cho A2/revisit A — không xử
lý ở đây.

## Mục tiêu Sub-project C

Thêm 6 node mới, đăng ký cùng cách các node tiện ích của A đã làm
(`server/nodes/utility.py` → registry), gọi thẳng vào các hàm/class đã có
sẵn của `translation_core` (B) — không viết lại logic dịch/RAG, chỉ viết
lớp "adapter" node mỏng.

## Kiến trúc tổng quan

```
server/nodes/translate.py   # 6 node class mới, import từ translation_core
server/executor.py            # +NEEDS_WORKSPACE mechanism (mở rộng, không phá node cũ)
server/main.py                  # ws_run truyền workspace_name vào run_graph()
server/workspace.py               # +get_workspace_path() helper; create_workspace() seed agent.md rỗng
```

Không có package/module mới ở tầng backend ngoài 1 file node — mọi logic
dịch/RAG/provider đã nằm sẵn trong `translation_core` (B), C chỉ gọi vào.

## Thành phần chi tiết

### 1. Node mới (`server/nodes/translate.py`)

Tất cả subclass `NodeBase` (từ A), dùng convention `INPUT_TYPES`/
`RETURN_TYPES`/`execute()` y hệt node cũ:

- **`Provider`** — `CATEGORY = "Translation"`.
  - `INPUT_TYPES`: required `base_url` (STRING), `api_key` (STRING),
    `model` (STRING).
  - `RETURN_TYPES = ("PROVIDER",)`.
  - `execute(self, base_url, api_key, model)`: gọi
    `translation_core.create_provider(translation_core.ProviderConfig(
    type="openai_compatible", base_url=base_url, api_key=api_key,
    model=model))`, trả về `(provider,)` — giá trị runtime là 1 instance
    `LLMProvider` thật, không phải string (executor truyền object Python
    nguyên vẹn giữa các node, không serialize qua JSON).

- **`LoadAgentFile`** — `CATEGORY = "Translation"`, `NEEDS_WORKSPACE = True`.
  - `INPUT_TYPES`: rỗng (không có input nào từ canvas).
  - `RETURN_TYPES = ("STRING",)`.
  - `execute(self, workspace_name)`: gọi
    `translation_core.load_agent_file(workspace.get_workspace_path(
    workspace_name, "agent.md"))`, trả về `(content,)`. Nếu file không
    tồn tại, để `FileNotFoundError` lọt ra — executor tự bắt và biến
    thành `node_error` như mọi node khác (không cần xử lý riêng).

- **`SaveAgentFile`** — `CATEGORY = "Translation"`, `NEEDS_WORKSPACE = True`.
  - `INPUT_TYPES`: required `text` (STRING).
  - `RETURN_TYPES = ()`.
  - `execute(self, workspace_name, text)`: gọi
    `translation_core.save_agent_file(workspace.get_workspace_path(
    workspace_name, "agent.md"), text)`, trả về `()`.

- **`RAGQuery`** — `CATEGORY = "Translation"`, `NEEDS_WORKSPACE = True`.
  - `INPUT_TYPES`: required `text` (STRING), optional `top_k` (STRING,
    default "3" — theo đúng convention widget text hiện tại của A, node
    tự `int()` hoá trước khi gọi).
  - `RETURN_TYPES = ("RAG_EXAMPLES",)`.
  - `execute(self, workspace_name, text, top_k="3")`: tạo
    `translation_core.RAGStore(workspace.get_workspace_path(
    workspace_name, "rag_index"))`, gọi `.query(text, top_k=int(top_k))`,
    trả về `(examples,)` — runtime value là `list[RAGExample]` thật.

- **`SaveToRAG`** — `CATEGORY = "Translation"`, `NEEDS_WORKSPACE = True`.
  - `INPUT_TYPES`: required `chapter_id` (STRING), `source_text` (STRING),
    `translated_text` (STRING).
  - `RETURN_TYPES = ()`.
  - `execute(self, workspace_name, chapter_id, source_text,
    translated_text)`: tạo `RAGStore` như trên, gọi
    `.add_chapter(chapter_id, source_text, translated_text)`.

- **`Translate`** — `CATEGORY = "Translation"` (không cần `NEEDS_WORKSPACE`
  — mọi thứ nó cần đã tới qua dây nối).
  - `INPUT_TYPES`: required `provider` (PROVIDER), `agent_instructions`
    (STRING), `source_text` (STRING); optional `rag_examples`
    (RAG_EXAMPLES).
  - `RETURN_TYPES = ("STRING",)`.
  - `execute(self, provider, agent_instructions, source_text,
    rag_examples=None)`: gọi
    `translation_core.translate_chunk(provider, agent_instructions,
    rag_examples or [], source_text)`, trả về `(result,)`.

### 2. Slot type mới: `PROVIDER`, `RAG_EXAMPLES`

Chỉ 2 type mới, dùng cho giá trị không phải text thuần (Python object thật
— instance `LLMProvider`, `list[RAGExample]`). `nodegen.js` không cần đổi
gì — nó đã tự tạo input slot theo đúng tên type khai báo trong
`INPUT_TYPES`/`RETURN_TYPES` (chỉ vẽ widget text khi type là `"STRING"`,
type khác chỉ có slot nối dây) — 2 type mới này tự động chỉ nhận nối dây,
không có widget, đúng ý muốn (không ai gõ tay 1 list RAGExample).

### 3. Mở rộng executor: cơ chế `NEEDS_WORKSPACE`

`server/executor.py`'s `run_graph()` thêm tham số
`workspace_name: str | None = None`. Khi khởi tạo node để chạy:

```python
node_cls = get_node_class(node["type"])
extra_kwargs = {}
if getattr(node_cls, "NEEDS_WORKSPACE", False):
    extra_kwargs["workspace_name"] = workspace_name
result = node_cls().execute(**kwargs, **extra_kwargs)
```

`NodeBase` (A) thêm class attribute mặc định `NEEDS_WORKSPACE = False`.
Node cũ (`LoadTextFile` v.v.) không khai báo cờ này nên không đổi hành vi.
`workspace_name` KHÔNG xuất hiện trong `INPUT_TYPES()` — nó không phải là
1 input canvas, chỉ là context được executor bơm vào lúc chạy.

`server/main.py`'s `ws_run(websocket, workspace_name)` (đã có sẵn
`workspace_name` từ URL, hiện chưa dùng tới) truyền thẳng vào
`run_graph(graph["nodes"], graph["links"], on_event=on_event,
workspace_name=workspace_name)`.

### 4. `server/workspace.py`: helper đường dẫn con

Thêm hàm public:

```python
def get_workspace_path(name: str, *parts: str) -> Path:
    return _workspace_dir(name).joinpath(*parts)
```

Tái dùng `_workspace_dir()` sẵn có (đã validate tên chống path-traversal
từ Task 5 của A) — node mới không tự ráp đường dẫn tay, luôn qua hàm này.

`create_workspace()` thêm 1 dòng seed file `agent.md` rỗng (kèm 1 dòng
comment gợi ý, ví dụ "# Hướng dẫn dịch\n\nDịch sang tiếng Việt...") ngay
khi tạo workspace mới, để `LoadAgentFile` không lỗi ngay lần chạy đầu.

## Data flow (workflow mẫu theo đúng mô tả ban đầu)

```
[LoadTextFile: path=chapters/ch5.txt] ──text──┐
                                                 ├──▶ [RAGQuery: top_k=3] ──rag_examples──┐
                                                 │                                          │
[LoadAgentFile] ──text───────────────────────────┼──▶ [Translate] ◀────────────────────────┘
                                                 │        ▲
[Provider: base_url=..., api_key=..., model=...] ─provider┘
                                                 │
                                                 ▼ (translated text)
                                    [SaveTextFile: path=output/ch5.txt]
                                    [SaveToRAG: chapter_id="ch5", source_text=<từ LoadTextFile>,
                                                translated_text=<từ Translate>]
```

## Error handling

Không có cơ chế mới — mọi lỗi (agent.md thiếu, Provider lỗi HTTP, RAG
index lỗi filesystem) đã tự động biến thành `ProviderError`/
`FileNotFoundError`/lỗi filesystem chuẩn (từ B), và executor của A đã bắt
mọi exception ở tầng node để phát `node_error` — không cần try/except gì
thêm trong 6 node mới ngoài những gì `translation_core` đã tự làm.

## Testing

- Mỗi node: pytest riêng, dùng `workspace.create_workspace()` với
  `WORKSPACES_ROOT` monkeypatch sang `tmp_path` (đúng pattern
  `tests/test_workspace.py` đã có), provider giả (fake `LLMProvider`
  subclass như B đã dùng, không mock, không gọi API thật).
- `RAGQuery`/`SaveToRAG`: dùng `RAGStore` thật (chromadb + embedding thật,
  chấp nhận chậm hơn theo đúng lý do đã ghi ở spec B).
- Executor: test `NEEDS_WORKSPACE` — 1 node giả có cờ này trong test,
  assert `workspace_name` tới đúng `execute()`; 1 node giả không có cờ,
  assert không nhận `workspace_name` (không phá node cũ).
- Kiểm thử cuối: chạy `run.bat` thật, kéo 6 node mới + node cũ ráp theo
  workflow mẫu trên canvas, dịch 1 đoạn ngắn qua LM Studio hoặc 1 endpoint
  giả lập, xác nhận file output + RAG index thật được tạo — theo đúng cách
  Task 9/10 của A đã verify (Playwright nếu có, fallback script trực
  tiếp).

## Ngoài phạm vi (out of scope) của spec này

- Hệ thống lưu/tải template workflow sẵn (thuộc Sub-project A2).
- Node tự động trích xuất thuật ngữ mới bằng LLM và cập nhật agent file —
  để dành giai đoạn sau, khi có nhu cầu thật.
- Anthropic/Gemini provider — B đã để sẵn kiến trúc mở rộng, C chỉ cần
  node `Provider` hiện tại (OpenAI-compatible) là đủ.
- Mã hoá/bảo vệ `api_key` trong `graph.json` — đã quyết định chấp nhận
  lưu plaintext cho MVP (local, single-user).
- MCP server (Sub-project D).

## Cấu trúc thư mục dự kiến (thay đổi so với A1/B)

```
MCPToolTranslaterNovel/
  server/
    executor.py            # sửa: +workspace_name param, +NEEDS_WORKSPACE check
    main.py                  # sửa: ws_run truyền workspace_name
    node_registry.py           # sửa: NodeBase +NEEDS_WORKSPACE = False
    workspace.py                 # sửa: +get_workspace_path(); create_workspace() seed agent.md
    nodes/
      translate.py                # MỚI: 6 node class
  tests/
    test_executor.py             # sửa: +test cho NEEDS_WORKSPACE
    test_workspace.py              # sửa: +test cho get_workspace_path(), agent.md seeding
    test_translate_nodes.py          # MỚI
```
