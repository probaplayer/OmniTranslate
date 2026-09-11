# OmniTranslate Studio

Trình chỉnh sửa quy trình dịch dạng node-graph (kiểu ComfyUI) chạy trên LLM, dùng
để dịch **novel, manga và video** theo từng chương/cảnh — kèm bộ nhớ thuật ngữ
(glossary) giúp giữ nhất quán tên riêng và cách xưng hô xuyên suốt tác phẩm.

Bạn kéo-thả các node (đọc chương, tra glossary, gọi LLM, trích thuật ngữ mới,
lưu kết quả...) thành một đồ thị, lưu theo từng workspace, rồi chạy. Danh sách
node do backend định nghĩa và frontend tự sinh giao diện tương ứng — không cần
sửa frontend khi thêm node mới.

## Tính năng

- Canvas kéo-thả để tự xây quy trình dịch theo ý muốn, không cố định pipeline
- Glossary: tự trích thuật ngữ mới sau mỗi lần dịch, phát hiện xung đột với bản
  dịch cũ, và tự động rà soát/sửa lại các chương liên quan khi thuật ngữ đổi
- Dùng được với bất kỳ provider nào tương thích chuẩn OpenAI `chat/completions`
  (LM Studio chạy local, OpenAI, ...)
- Theo dõi tiến trình chạy graph theo thời gian thực (WebSocket), từng node báo
  trạng thái running/done/error ngay trên canvas
- Nhiều workspace độc lập — mỗi truyện/dự án một workspace riêng, không lẫn dữ
  liệu
- Giao diện hỗ trợ song ngữ Việt/Anh, chuyển đổi trực tiếp không cần tải lại
  trang

## Yêu cầu

- Python 3.10+
- Windows để dùng `run.bat`; các hệ điều hành khác chạy `uvicorn` thủ công vẫn
  hoạt động bình thường

## Bắt đầu nhanh

**Windows:**

```
run.bat
```

Script này tự tạo `.venv`, cài `requirements.txt`, rồi mở trình duyệt khi
server sẵn sàng tại `http://127.0.0.1:8000`.

**Thủ công (mọi hệ điều hành):**

```
python -m venv .venv
.venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Sau đó mở `http://127.0.0.1:8000` trong trình duyệt.

## Cách dùng

1. Tạo một workspace mới (mỗi workspace ứng với một tác phẩm/dự án dịch).
2. Kéo node từ thư viện bên trái vào canvas và nối lại thành quy trình, ví dụ:
   `LoadTextFile → LookupGlossary → Translate → ExtractGlossary → SaveTextFile`.
3. Điền các trường bắt buộc (URL/model của provider, đường dẫn file, ...).
4. Nhấn **Chạy toàn bộ** để thực thi và theo dõi log ở panel bên dưới.

Có sẵn một workflow mẫu trong [`templates/`](templates/README.md) — xem file
đó để biết cách nạp vào workspace.

## Kiểm thử

```
pytest
```

Chạy một file/test cụ thể: `pytest tests/test_workspace.py::test_create_and_list_workspace`.

## Cấu trúc dự án

- `server/` — backend FastAPI: node registry, executor thực thi graph, quản lý
  workspace, WebSocket chạy graph theo thời gian thực.
- `translation_core/` — logic dịch thuần Python, độc lập framework (provider
  LLM, glossary, chapter tracking).
- `web/` — frontend thuần JS trên nền `litegraph.js` (không build step).
- `templates/` — workflow mẫu, có track trong git (khác `workspaces/`).
- `workspaces/` — dữ liệu người dùng theo từng dự án (gitignored).

Xem [`CLAUDE.md`](CLAUDE.md) để biết chi tiết kiến trúc sâu hơn.
