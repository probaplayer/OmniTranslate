# Agent Template Library — Design

## Bối cảnh

`agent.md` is the system prompt/style-guide fed to the LLM on every
translation call (`LoadAgentFile` → `Translate.agent_instructions`).
Today it's purely per-workspace: `create_workspace` seeds it with one
generic default (`_DEFAULT_AGENT_FILE` in `server/workspace.py`:
"Dịch sang tiếng Việt, giữ văn phong tự nhiên, nhất quán tên riêng/thuật
ngữ."), and from then on it's hand-written from scratch, per workspace,
every time.

The user wants a library of pre-written instruction sets for common novel
genres (each genre × target language is its own file, since a genre's
conventions — forms of address, register, recurring terminology patterns
— differ by target language too, not just by genre), so starting a new
workspace means *picking* a starting point instead of writing one from
nothing. This does **not** replace the per-workspace `agent.md` — a
workspace can still load a shared template as a starting point, tweak it,
and save its own customized copy locally, exactly as today, without
touching the shared template or affecting any other workspace.

## Mục tiêu

1. A shared, non-workspace-specific library of agent templates,
   organized by target language then genre:
   `agents/<lang>/<genre>.md` (e.g. `agents/vn/tien-hiep.md`).
2. `LoadAgentFile` can load either a shared template (by id) or the
   workspace's own local `agent.md` (today's exact behavior) — a single
   field, one or the other, no automatic priority logic between the two.
   Defaulting to the workspace's own file, so an existing saved graph
   that predates this feature keeps behaving identically without any
   migration.
3. `SaveAgentFile` is unchanged — it already writes to the workspace's
   own `agent.md`, which is exactly the "save my customization
   locally, don't touch the shared template" behavior the user wants.
4. A "Chọn agent…" picker: language tabs, then a genre list for the
   selected language, plus an explicit "workspace của tôi" option —
   picking any of these fills `LoadAgentFile`'s field with the right
   value and closes the picker.
5. Initial templates: `tien-hiep` (tiên hiệp / huyền huyễn / dị giới),
   `ngon-tinh` (ngôn tình / đô thị), `kiem-hiep` (kiếm hiệp / võ hiệp),
   `hoc-duong` (học đường), `hai-huoc` (hài hước), `fantasy` (Western
   fantasy, distinct from `tien-hiep`'s Eastern-cultivation conventions),
   and `general` (a genre-neutral fallback for when the novel doesn't
   fit any of the above) — each written for **both** `vn` and `en` as
   the target language, 14 files total.

## Kiến trúc tổng quan

```
agents/                      (Create: the shared template library,
                              checked into git — developer-authored
                              content, not user data)
  vn/
    tien-hiep.md
    ngon-tinh.md
    kiem-hiep.md
    hoc-duong.md
    hai-huoc.md
    fantasy.md
    general.md
  en/
    tien-hiep.md
    ngon-tinh.md
    kiem-hiep.md
    hoc-duong.md
    hai-huoc.md
    fantasy.md
    general.md
server/
  agent_templates.py         (Create: AGENTS_ROOT, list_templates(),
                              resolve_template_path())
  main.py                     (Modify: add `GET /api/agent-templates`)
  nodes/
    translate.py               (Modify: LoadAgentFile gains an optional
                                `template` field; SaveAgentFile: no change)
web/
  canvas.html                  (Modify: load agent_template_picker.js,
                                modal CSS — can share styling with the
                                path-picker modal, doesn't need to share
                                its code)
  js/
    agent_template_picker.js    (Create: openAgentTemplatePicker(onSelect)
                                 — fetches /api/agent-templates, renders
                                 language tabs + genre list + a
                                 "workspace của tôi" option)
    inspector_panel.js           (Modify: `LoadAgentFile`'s `template`
                                  field, flagged `widget: "agent_template"`,
                                  gets a "Chọn agent…" button — reuses the
                                  same button-next-to-textarea convention
                                  the path-picker sub-project establishes,
                                  wired to open this different modal
                                  instead)
```

### `server/agent_templates.py`

```python
AGENTS_ROOT = Path(__file__).resolve().parent.parent / "agents"
_SLUG_PATTERN = re.compile(r"[a-z0-9_-]+")

def list_templates() -> dict[str, list[str]]:
    """{"vn": ["tien-hiep", ...], "en": [...]} — scans AGENTS_ROOT's
    immediate subdirectories for *.md files, sorted."""
    ...

def resolve_template_path(template: str) -> Path:
    """template is "<lang>/<genre>" (e.g. "vn/tien-hiep"). Splits on "/",
    requires exactly two parts, validates both against _SLUG_PATTERN
    (same allowlist-regex approach as workspace.py's _NAME_PATTERN — no
    path traversal via a crafted template value), joins under AGENTS_ROOT,
    and requires the resulting file to exist. Raises ValueError for a
    malformed template string, FileNotFoundError for a well-formed one
    naming a file that doesn't exist — mirrors load_agent_file's own
    FileNotFoundError-on-missing precedent."""
    ...
```

### `LoadAgentFile` (the only node this spec touches)

```python
@register_node("LoadAgentFile")
class LoadAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {"template": ("STRING", {"default": "workspace", "widget": "agent_template"})},
        }

    def execute(self, workspace_name, template="workspace"):
        if template == "workspace":
            path = workspace.get_workspace_path(workspace_name, "agent.md")
        else:
            path = agent_templates.resolve_template_path(template)
        return (load_agent_file(path),)
```

The `template="workspace"` Python-level default (not just the
`INPUT_TYPES` default) matters: the existing test
`test_load_agent_file_node_reads_seeded_file` calls
`node.execute(workspace_name="novel-a")` with no `template` argument at
all, and must keep passing unchanged.

**To verify while planning, not assumed here:** whether litegraph's
`LGraphNode.prototype.configure` — the routine that restores a node from
a saved graph — merges saved `properties` onto the fresh
constructor-initialized defaults (in which case an old saved
`LoadAgentFile` node, whose serialized `properties` has no `template`
key at all, ends up with `template: "workspace"` from the constructor,
exactly as intended) or instead replaces `properties` wholesale (in
which case a different mechanism would be needed to backfill the
default for old saves). Read the real `web/js/litegraph.js` source for
`configure` before relying on this, the same way this project has
verified every other litegraph mechanic it depended on.

### Backend — `GET /api/agent-templates`

Returns `list_templates()`'s dict directly, `{"vn": [...], "en": [...]}`
— one call gives the picker its whole tree, no per-tab fetch needed.

### Frontend — `web/js/agent_template_picker.js` (new)

`openAgentTemplatePicker(onSelect)`: fetches `/api/agent-templates`,
renders a modal with an always-visible first row "◆ Tùy chỉnh riêng cho
workspace này" (clicking it calls `onSelect("workspace")` and closes),
then a language tab strip (`vn`/`en`, from the response's top-level
keys) and, below it, the genre list for whichever tab is active
(clicking a genre calls `onSelect(f"{lang}/{genre}")` and closes).

### `inspector_panel.js` change

Same convention the path-picker sub-project establishes: read
`spec[1]?.widget` for a STRING field, and for `"agent_template"` (as
opposed to `"path"`) append a "Chọn agent…" button instead of "Browse…",
wired to `openAgentTemplatePicker` instead of `openPathPicker`. Written
so it works whether or not that sub-project has shipped yet — see its
spec's "Phụ thuộc & thứ tự triển khai".

## Nội dung 14 template — cấu trúc bắt buộc & 1 ví dụ đầy đủ

Every template file, regardless of genre or language, has the same four
sections, in this order — so a translator (or this app's future
maintainer) always knows where to look for a given kind of guidance:

1. **Văn phong** — register, sentence rhythm, how literal vs. how
   localized to be.
2. **Xưng hô** — pronoun/address-term conventions between the character
   relationships this genre features most (master–disciple, siblings,
   enemies, colleagues, classmates, etc., as relevant to the genre).
3. **Thuật ngữ đặc trưng** — the genre's recurring terminology pattern
   (cultivation realms for `tien-hiep`, martial-arts schools/techniques
   for `kiem-hiep`, school ranks/clubs for `hoc-duong`, and so on) and
   how to handle it consistently (Hán Việt vs. dịch nghĩa, when each
   applies).
4. **Lưu ý khác** — anything genre-specific that doesn't fit the above
   (e.g. `hai-huoc`'s wordplay/pun handling, `fantasy`'s invented-language
   proper nouns, `general`'s "when in doubt, stay literal and flag it"
   fallback stance).

Every `en`-language file's target-language instruction — the fact that
it's translating **into English**, not Vietnamese — lives inside the
file's own prose (its "Văn phong" section states the target language
explicitly), per the brainstorming decision to keep language selection
inside content rather than as a separate structured field.

**Worked example — `agents/vn/tien-hiep.md`** (this is real, final
content, not a placeholder; the plan reproduces it verbatim and writes
the remaining 13 files to the same structural standard):

```markdown
# Hướng dẫn dịch — Tiên hiệp / Huyền huyễn / Dị giới

Dịch sang tiếng Việt. Thể loại tiên hiệp/huyền huyễn/dị giới (tu tiên,
pháp thuật, dị thế giới) — giữ đúng các quy ước sau.

## Văn phong

- Giọng văn trang trọng, cổ trang vừa phải — không dùng từ lóng/teencode,
  không hiện đại hóa lời thoại.
- Câu văn có thể dài, nhiều tính từ miêu tả cảnh vật/tu vi — không cắt
  ngắn thô bạo, giữ nhịp điệu và không khí của nguyên tác.
- Thuật ngữ tu luyện dịch nhất quán xuyên suốt — nếu workspace có
  glossary.json, luôn ưu tiên thuật ngữ đã có trong đó.

## Xưng hô

- Sư đồ (thầy trò): đệ tử xưng "đệ tử"/"con", gọi thầy là
  "sư phụ"/"sư tôn"; không dùng "thầy/em" trung tính.
- Đồng môn: xưng hô theo thứ bậc nhập môn — "sư huynh/sư tỷ/sư đệ/sư
  muội", không dùng "anh/chị/em" hiện đại.
- Trưởng bối/vãn bối không cùng môn phái: "tiền bối"/"vãn bối", tránh
  "ông/bà/cháu".
- Kẻ thù/địch nhân: xưng hô lạnh lùng, cộc lốc — "ngươi/ta", không dùng
  "bạn/tôi".

## Thuật ngữ đặc trưng

- Giữ nguyên hệ thống cảnh giới tu luyện của tác phẩm (ví dụ: Luyện Khí,
  Trúc Cơ, Kim Đan, Nguyên Anh, Hóa Thần...) — không tự ý đổi tên hay
  dịch nghĩa đen sang tiếng Anh/tiếng khác.
- Tên công pháp, pháp bảo, linh thú: giữ Hán Việt nếu bản gốc dùng Hán
  tự, trừ khi cái tên mang ý nghĩa quan trọng với cốt truyện và cần dịch
  nghĩa để người đọc hiểu được dụng ý.
- Đơn vị đo tu vi/thời gian tu luyện (năm, kiếp, tuổi thọ...) giữ nguyên
  logic của nguyên tác, không quy đổi sang đơn vị hiện đại.

## Lưu ý khác

- Không thêm chú thích/giải thích ngoài lề kiểu "(ND: ...)" trong bản
  dịch — nếu cần giải thích, đó là việc của agent.md/glossary, không
  phải của bản dịch.
- Giữ nguyên các thán từ, khẩu quyết, tên chiêu thức khi nhân vật hô lớn
  lúc thi triển — dịch sát nghĩa nhưng không thoát ý làm mất khí thế.
```
```

## Xử lý lỗi

- `template` không phải `"workspace"` và không đúng dạng `"<lang>/<genre>"`
  (thiếu hoặc thừa dấu `/`, hoặc `lang`/`genre` chứa ký tự ngoài
  allowlist) → `ValueError`, propagates như một lỗi node bình thường.
- `template` đúng dạng nhưng file không tồn tại (`agents/<lang>/<genre>.md`
  không có) → `FileNotFoundError`, cùng cách xử lý với `LoadAgentFile`
  hiện tại khi `workspace/agent.md` bị xoá tay.

## Testing

- `tests/test_agent_templates.py`: `resolve_template_path` accepts a
  well-formed existing template, rejects a malformed string (no `/`, or
  invalid characters — including an attempted path-traversal payload
  like `"../../etc"`), and raises `FileNotFoundError` for a well-formed
  but nonexistent template; `list_templates()` against a temporary
  `AGENTS_ROOT` (monkeypatched, mirroring `test_translate_nodes.py`'s
  `isolated_workspaces_root` fixture pattern) returns the right
  `{lang: [genres]}` shape.
- `tests/test_translate_nodes.py`: existing `LoadAgentFile` tests
  continue to pass unchanged (proving the default keeps today's exact
  behavior); a new test loads a real shared template by id and asserts
  its content came back instead of the workspace's own file.
- `tests/test_integration.py` (if it exercises `LoadAgentFile` — check
  during planning): confirm it isn't relying on `LoadAgentFile.execute`
  accepting only `workspace_name` positionally in a way this optional
  addition would break.

## Phụ thuộc & thứ tự triển khai

Independent of the Glossary & Chapter Consistency spec (touches a
different node — `LoadAgentFile`, not anything that spec changes) and of
the Path Picker spec (a different, purpose-built modal — see that spec's
note on the two being independently shippable, with an optional shared
`widget`-flag convention if convenient).

## Ngoài phạm vi

- A structured `target_lang` field anywhere in the node graph — the
  brainstorming decision was explicitly to keep target-language selection
  inside each template's own prose content, not as separate structured
  data (see "Mục tiêu" §5 and the worked example above).
- Automatic "priority" logic between a workspace's own `agent.md` and a
  shared template — explicitly rejected during brainstorming in favor of
  a plain either/or field with a fixed default.
- More than the 7 initial genres — additional ones are just more files
  under the same `agents/<lang>/` structure, added later on request, not
  designed for speculatively now.
