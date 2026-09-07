# Translation & RAG Core — Design Spec (Sub-project B)

Date: 2026-09-07
Status: Approved for planning

## Bối cảnh dự án lớn

Xem lại 4 sub-project đã chốt (spec Sub-project A:
`docs/superpowers/specs/2026-08-28-node-graph-engine-design.md`):

- **A** — Node-graph engine lõi + Web UI (đã hoàn thành, merge vào `master`).
- **B (spec này)** — Translation & RAG core: quản lý context xuyên suốt
  novel, gọi LLM để dịch trực tiếp bằng API key/endpoint tự cấu hình.
  Không có UI, không phụ thuộc FastAPI/web — là 1 Python package thuần để
  Sub-project C import và wrap thành node.
- **C** — Tích hợp B vào A: các node thật (Text, Provider, RAG, Agent File,
  Translate...) ráp thành workflow trên canvas.
- **D** — MCP server để Claude/Codex/OpenCode điều khiển workspace từ ngoài.

## Ghi chú UI (không thuộc phạm vi spec này)

Trong lúc brainstorm B, có phản hồi về UI của A: muốn vào thẳng canvas
("world map") thay vì màn hình chọn/tạo workspace, lưu bằng Ctrl+S ra 1
file JSON. Đây là thay đổi luồng UI của Sub-project A (đã merge), không
thuộc phạm vi B. Ghi lại ở đây để cân nhắc khi làm A2 hoặc revisit A.

## Mục tiêu Sub-project B

Cung cấp 3 khối chức năng độc lập, mỗi khối có interface rõ ràng để C gọi
vào từ bên trong node, không có logic gì phụ thuộc web/canvas:

1. **Provider abstraction** — gọi LLM để dịch, cấu hình hoàn toàn từ bên
   ngoài (base_url/api_key/model), không hardcode 1 hãng cụ thể trong code.
2. **RAG store** — lưu & truy vấn ngữ nghĩa các chương đã dịch trước đó, để
   giữ nhất quán cốt truyện/văn phong/thuật ngữ khi dịch chương mới.
3. **Agent file loader** — đọc/ghi 1 file text chứa hướng dẫn dịch (văn
   phong, ngôn ngữ đích, glossary tên riêng/thuật ngữ) — không tách bảng
   glossary riêng, tất cả gộp trong 1 file do người dùng (hoặc 1 node
   khác ở C) chỉnh sửa.

Và 1 hàm lõi ghép 3 khối trên lại: `translate_chunk()`.

## Kiến trúc tổng quan

```
translation_core/                (package Python thuần, không FastAPI)
  providers/
    base.py            # LLMProvider (ABC) + ProviderError
    openai_compatible.py  # OpenAICompatibleProvider(base_url, api_key, model)
    factory.py           # create_provider(ProviderConfig) -> LLMProvider
  rag/
    store.py              # RAGStore (chromadb-backed)
  agent_file.py            # load_agent_file() / save_agent_file()
  translate.py              # translate_chunk()
```

Sub-project C sau này sẽ `from translation_core import ...` bên trong các
node Python của nó (`server/nodes/translate.py` chẳng hạn), y hệt cách
`server/nodes/utility.py` dùng `server/node_registry.py` ở Sub-project A.
B không biết gì về "workspace"/FastAPI/websocket — mọi đường dẫn file
(agent file, thư mục lưu RAG index) đều do caller (node ở C) truyền vào.

## Thành phần chi tiết

### 1. Provider abstraction

```python
class LLMProvider(ABC):
    def complete(self, messages: list[dict], **kwargs) -> str: ...

class ProviderError(Exception):
    pass
```

`messages` theo format chat chuẩn: `[{"role": "system"|"user"|"assistant",
"content": str}, ...]`.

**Implementation đầu tiên: `OpenAICompatibleProvider(base_url, api_key,
model)`** — gọi `POST {base_url}/chat/completions` theo format OpenAI
chat-completions. Lý do chọn implementation này trước: OpenAI, **LM
Studio**, Ollama, DeepSeek, OpenRouter... đều expose cùng 1 format API
này, chỉ khác `base_url`/`model` — nên 1 implementation phủ được gần hết
nhu cầu thực tế ngay từ B, bao gồm cả yêu cầu "kết nối LM Studio" (LM
Studio chạy 1 server local expose `http://localhost:1234/v1`, `api_key`
có thể là chuỗi bất kỳ vì LM Studio không kiểm tra).

Lỗi HTTP (timeout, status khác 2xx, response không parse được) → raise
`ProviderError` với message rõ ràng — không để exception thô (httpx's
`HTTPStatusError`, `TimeoutException`...) lọt ra ngoài, để C's node sau
này bắt và biến thành `node_error` event theo đúng convention của A.

**Factory:** `create_provider(config: ProviderConfig) -> LLMProvider`, với
`ProviderConfig` là dataclass `{type: str, base_url: str, api_key: str,
model: str}`. `type` hiện chỉ nhận `"openai_compatible"`; thêm loại khác
(Anthropic, Gemini — API format khác hẳn) là việc mở rộng sau này bằng
cách thêm 1 nhánh trong factory + 1 class provider mới, không đổi gì ở
`LLMProvider`/`translate_chunk()`.

### 2. RAG store

Dựa trên **ChromaDB** (persistent, lưu xuống đĩa) + embedding **local**
qua `sentence-transformers` (model multilingual mặc định:
`paraphrase-multilingual-MiniLM-L12-v2`, hỗ trợ ~50 ngôn ngữ — phù hợp vì
nguồn truyện thường là tiếng Nhật/Trung/Hàn, đích là tiếng Việt).

Đơn vị lưu trữ là **1 chương** (không tách chunk nhỏ hơn trong v1 này —
YAGNI, tránh bài toán khó "map chunk nguồn ↔ chunk dịch không đối xứng
1:1"). Mỗi entry gồm: `chapter_id`, `source_text` (dùng để embed — model
sẽ tự cắt bớt nếu chương quá dài hơn max sequence length, chấp nhận được
cho mục đích tìm chương *tương tự về mặt chủ đề*, không phải tìm chính
xác), `translated_text` (lưu nguyên vẹn làm metadata, không embed).

```python
class RAGStore:
    def __init__(self, persist_directory: str | Path): ...
    def add_chapter(self, chapter_id: str, source_text: str, translated_text: str) -> None: ...
    def query(self, text: str, top_k: int = 3) -> list[RAGExample]: ...

@dataclass
class RAGExample:
    chapter_id: str
    source_text: str
    translated_text: str
    distance: float
```

`persist_directory` do caller truyền vào (ví dụ node ở C sẽ trỏ vào
`workspaces/<name>/rag_index/`) — B không tự quyết định đường dẫn.

### 3. Agent file loader

Chỉ 2 hàm thuần, không có class:

```python
def load_agent_file(path: str | Path) -> str: ...
def save_agent_file(path: str | Path, content: str) -> None: ...
```

File là text/markdown tự do — không parse cấu trúc gì đặc biệt (không
frontmatter, không schema). Toàn bộ nội dung file trở thành system prompt
khi dịch. Việc "1 node cập nhật lại file agent (thêm thuật ngữ mới, đổi
văn phong...)" là logic của Sub-project C; B chỉ cần đọc/ghi file đúng.
Nếu file không tồn tại khi `load_agent_file` được gọi, raise
`FileNotFoundError` (lỗi Python chuẩn, rõ ràng) — caller ở C quyết định
xử lý (báo lỗi hay tạo file rỗng).

### 4. `translate_chunk()` — hàm lõi ghép mọi thứ lại

```python
def translate_chunk(
    provider: LLMProvider,
    agent_instructions: str,
    rag_examples: list[RAGExample],
    source_text: str,
) -> str:
```

Ghép `agent_instructions` + các `rag_examples` (định dạng thành đoạn văn
bản "Ví dụ dịch trước đó tham khảo văn phong/thuật ngữ") thành system
prompt; `source_text` là user message. Gọi `provider.complete(messages)`
và trả về chuỗi kết quả. Không tự động cập nhật RAG store hay agent file —
đó là quyết định của node gọi nó (ví dụ node "Translate" ở C có thể tự
gọi `rag_store.add_chapter(...)` sau khi dịch xong).

## Data flow (khi dịch 1 chương, do node ở C điều phối — minh họa)

1. Node đọc agent file hiện tại → `agent_instructions`.
2. Node query RAG store bằng nội dung chương cần dịch → `rag_examples`.
3. Node gọi `translate_chunk(provider, agent_instructions, rag_examples,
   source_text)` → nhận bản dịch.
4. Node (tùy chọn) gọi `rag_store.add_chapter(...)` để chương này trở
   thành ngữ cảnh cho các chương sau.
5. Node (tùy chọn, node riêng) tự phát hiện thuật ngữ mới và gọi
   `save_agent_file(...)` để cập nhật file agent.

## Error handling

- Lỗi gọi Provider (network, timeout, HTTP status lỗi, response không
  parse được) → `ProviderError` với message rõ ràng, không để exception
  thư viện HTTP (httpx) lọt ra ngoài package.
- `agent_file.load_agent_file` trên file không tồn tại → `FileNotFoundError`
  chuẩn của Python, không nuốt lỗi.
- `RAGStore` lỗi khi `persist_directory` không ghi được (quyền, đĩa đầy)
  → để lỗi filesystem gốc lọt ra (không cần custom exception riêng, không
  đáng để thêm 1 lớp trừu tượng cho trường hợp hiếm).
- Không retry tự động ở tầng B (không cần thiết cho MVP) — retry là quyết
  định của node gọi (C) nếu cần sau này.

## Testing

- **Provider**: test với `httpx.MockTransport` (built-in, không cần thêm
  dependency) giả lập response OpenAI-compatible thật + các case lỗi
  (timeout, status 500, JSON không hợp lệ) → assert raise `ProviderError`.
  Không gọi API thật/LM Studio thật trong test.
- **RAGStore**: test với ChromaDB thật, `persist_directory` là `tmp_path`,
  model embedding thật (sentence-transformers) — chấp nhận lần chạy test
  đầu tiên cần internet để tải model (~470MB), các lần sau dùng cache local.
  Test: thêm vài chương giả, query bằng văn bản tương tự 1 chương cụ thể,
  assert chương đó nằm trong top-K kết quả.
- **agent_file**: test đọc/ghi file thật qua `tmp_path`, test
  `FileNotFoundError` khi file không tồn tại.
- **translate_chunk**: test với 1 `LLMProvider` giả (fake class trong test,
  không mock) để assert system prompt được ghép đúng nội dung agent
  instructions + rag examples, và user message đúng là `source_text`.

## Ngoài phạm vi (out of scope) của spec này

- UI/web/node thật — thuộc Sub-project C.
- Anthropic/Gemini provider implementation — kiến trúc đã sẵn sàng mở
  rộng nhưng chưa cần xây ngay (YAGNI); thêm khi có nhu cầu thật.
- Tự động trích xuất thuật ngữ mới bằng LLM và ghi vào agent file — đây là
  logic node ở Sub-project C gọi `translate_chunk`/`save_agent_file`, B
  chỉ cung cấp primitive đọc/ghi file, không tự động hoá việc trích xuất.
- Chunk hoá nhỏ hơn cấp chương (sub-chapter chunking) cho RAG — MVP dùng
  1 entry/chương; nếu sau này chương quá dài làm embedding không hiệu quả,
  sẽ bổ sung chunking chi tiết hơn.
- MCP server, Loop Group, template system — thuộc các sub-project khác.

## Dependency mới cần thêm vào `requirements.txt`

- `chromadb` — vector store.
- `sentence-transformers` — embedding local (kéo theo `torch`, dung lượng
  cài đặt lớn hơn đáng kể so với A1's dependency hiện tại — chấp nhận
  được vì đây là tool desktop chạy local, không phải service nhẹ).

## Cấu trúc thư mục dự kiến

```
MCPToolTranslaterNovel/
  translation_core/
    __init__.py
    providers/
      __init__.py
      base.py
      openai_compatible.py
      factory.py
    rag/
      __init__.py
      store.py
    agent_file.py
    translate.py
  tests/
    test_providers.py
    test_rag_store.py
    test_agent_file.py
    test_translate.py
  requirements.txt          # thêm chromadb, sentence-transformers
```
