# Tiến độ — Overhaul node dịch thuật (Path Picker / Glossary / Agent Templates)

Ghi lại trạng thái thật của 3 sub-project bắt nguồn từ buổi brainstorm ngày
2026-09-10 (thay thế RAG bằng Chroma bằng glossary.json + chapters.json,
thêm popup chọn đường dẫn, thêm thư viện agent mẫu theo thể loại). Cập nhật
lần cuối: 2026-09-14.

**Cả 3 sub-project đã xong và đã merge vào `master` (đã push lên GitHub).**

## ✅ Đã xong — đã merge vào `master`

### 1. Path Picker
- Spec: `docs/superpowers/specs/2026-09-10-path-picker-design.md`
- Plan: `docs/superpowers/plans/2026-09-10-path-picker-plan.md`
- 4 task kế hoạch + 1 fix wave (ad-hoc) sau final review — tất cả đã review
  sạch, merge thường (không squash) vào master.
- Có: `GET /api/browse-directory`, modal `web/js/path_picker.js`, nút
  "Duyệt..." (`widget: "path"`) trên `LoadTextFile.path`/`SaveTextFile.path`.

### 2. Glossary & Chapter Consistency
- Spec: `docs/superpowers/specs/2026-09-10-glossary-chapter-consistency-design.md`
- Plan: `docs/superpowers/plans/2026-09-10-glossary-chapter-consistency-plan.md`
- 9 task kế hoạch + Task 8 bị viết lại giữa chừng (workspace ví dụ
  `vi-du-lm-studio` hoá ra chưa từng được track git — đã xoá, thay bằng
  `templates/lm-studio-glossary-workflow.json` track thật) + 1 fix wave
  (2 vòng) sau final review sửa lỗi **nghiêm trọng**: `ExtractGlossary` từng
  làm hỏng văn bản không liên quan khi tự sửa thuật ngữ trùng lặp (đã fix +
  có test tái hiện đúng lỗi).
- Squash-merge vào master (để commit tạm add-nhầm-rồi-revert workspace ví dụ
  cũ không nằm vĩnh viễn trong lịch sử — không lộ secret gì, chỉ dọn sạch).
- Có: `glossary.json`/`chapters.json`, node `LoadGlossary`/`SaveGlossary`/
  `LookupGlossary`/`RecordChapter`/`ExtractGlossary`/`EvaluateAndFixChapters`,
  bỏ hẳn `chromadb`/`sentence-transformers`.

**Trạng thái test trên `master` hiện tại: xanh (tất cả pass).**

### 3. Agent Template Library
- Spec: `docs/superpowers/specs/2026-09-10-agent-template-library-design.md`
- Plan: `docs/superpowers/plans/2026-09-10-agent-template-library-plan.md`
- 6 task kế hoạch + 1 fix wave (ad-hoc) sau final review — tất cả đã review
  sạch. Final whole-branch review bị ngắt do rate-limit 2 lần trước khi gọi
  thành công lần 3 (rất kỹ: brute-force toàn bộ 1,114,112 Unicode codepoint
  vào regex validate slug để xác nhận không có cách nào path-traversal
  thoát ra ngoài `agents/`; chạy thật `litegraph.js` trong Node để chứng
  minh graph cũ (chưa có field `template`) khi load lại vẫn gửi đúng
  `template: "workspace"`, không bao giờ rơi vào trường hợp chuỗi rỗng).
- Merge thường (không squash) vào master.
- Có: `agents/vn|en/*.md` (7 thể loại × 2 ngôn ngữ), `server/agent_templates.py`,
  `GET /api/agent-templates`, `LoadAgentFile` thêm field `template` (mặc định
  `"workspace"`, hành vi cũ giữ nguyên 100%; `SaveAgentFile` không đổi gì),
  modal "Chọn agent..." sống chung an toàn với nút "Duyệt..." của Path Picker
  trong cùng 1 vòng lặp render (đã merge, xác nhận auto-merge sạch, không
  conflict).

**Trạng thái test trên `master` hiện tại: xanh (168/168 pass).**

## Ghi chú khác (không khẩn, không chặn merge)

- Nhánh `master` vừa có thêm 1 commit `e4fdbe4` ("docs: add CLAUDE.md and
  rebrand app as OmniTranslate Studio") — việc này nằm ngoài luồng làm việc
  của 3 sub-project trên, được thực hiện độc lập (không phải do quá trình
  chạy 3 plan này tạo ra).
- Follow-up đã ghi nhận nhưng cố ý chưa làm (không chặn merge của plan
  tương ứng):
  - Glossary plan: gộp logic build "khối thuật ngữ đã xác lập" trong
    `translate_chunk` và `EvaluateAndFixChapters._critique` thành 1 hàm
    dùng chung (hiện đang y hệt nhau nhưng là 2 bản copy riêng — rủi ro
    lệch nhau về sau).
  - Từ trước các plan này: node `TextInput` vẫn chưa có icon/label riêng
    trong `NODE_TYPE_META`/`NODE_TYPE_LABELS`/`NODE_TYPE_DESCS` (hiện dùng
    fallback màu xám).
