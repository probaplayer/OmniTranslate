# Path Picker — Design

## Bối cảnh

Every path-shaped input in this app (`LoadTextFile.path`, `SaveTextFile.path`,
and the new `RecordChapter.source_path`/`output_path` from the Glossary &
Chapter Consistency spec) is a plain text box today — the user has to type
or paste an absolute path by hand. The user wants a "Browse…" popup to
pick a folder instead.

This started as part of a larger "Embedding Provider" design (letting a
RAG feature choose between a local, cached embedding model and one served
by LM Studio); that whole feature was dropped once the actual RAG
requirement turned out not to need embeddings at all (see
`2026-09-10-glossary-chapter-consistency-design.md`). This piece — the
picker itself — has independent value regardless and survives on its own.

**Browser constraint, established during brainstorming:** a browser
cannot open a native OS folder-picker dialog and hand back a real absolute
filesystem path (`<input type="file">` deliberately withholds the full
path for security; the File System Access API returns opaque handles, not
path strings). Since every path in this app is a path *on the machine
running the FastAPI backend* (a local, single-user tool — backend and
browser are the same machine in normal use), the only way to give the
user a real "browse and pick a path" experience is a small, custom,
backend-driven directory browser: an API that lists a directory's
subfolders, and a modal in the canvas UI that walks it.

## Mục tiêu

1. A general-purpose "Browse…" folder picker, usable on any path-shaped
   node input, not built specifically for one node.
2. Applied to `LoadTextFile.path`, `SaveTextFile.path`, and (once that
   spec ships) `RecordChapter.source_path`/`output_path`.

## Kiến trúc tổng quan

```
server/
  main.py                  (Modify: add `GET /api/browse-directory`)
  nodes/
    utility.py              (Modify: mark LoadTextFile.path and
                             SaveTextFile.path as path-widget fields)
web/
  canvas.html               (Modify: load path_picker.js, modal CSS)
  js/
    path_picker.js           (Create: openPathPicker(initialPath, onSelect)
                              — fetches /api/browse-directory, renders a
                              breadcrumb + folder-list modal)
    inspector_panel.js        (Modify: a STRING field whose spec carries
                               `widget: "path"` gets a "Browse…" button)
```

### Backend — `GET /api/browse-directory`

- Query param `path` (optional). Empty/omitted → return the Windows drive
  list as pseudo-entries (`os.listdrives()` on Python ≥ 3.12, else probe
  `A:` through `Z:` with `Path(f"{letter}:/").exists()` — confirm the
  running Python's version during planning and pick accordingly), with
  `parent: null`.
- Non-empty `path` → `Path(path)` must exist and be a directory, else
  `HTTPException(400, "Path does not exist or is not a directory")`
  (mirrors `_workspace_http_error`'s "clear detail message" convention
  in `server/main.py`). List only subdirectories (this is a folder
  picker, not a file picker), sorted by name. A subdirectory that raises
  `PermissionError` on stat is skipped, not fatal to the whole listing
  (mirrors `workspace.list_workspaces`' "skip what fails validation"
  precedent). Response:
  `{"path": "<normalized path>", "parent": "<parent path or null>", "entries": [{"name": "...", "path": "..."}]}`.
- **Security note, stated explicitly for review, not silently assumed:**
  this endpoint lets any client that can reach the server enumerate the
  entire filesystem the server process can read. This is *not* a new
  trust boundary — `LoadTextFile`/`SaveTextFile` already accept and act on
  arbitrary absolute paths with zero restriction, consistent with this
  app's established local single-user trust model — but it makes
  filesystem structure discoverable through a UI affordance rather than
  requiring the caller to already know a path, which is worth a deliberate
  sign-off rather than an implicit one.

### Frontend — `web/js/path_picker.js` (new)

`openPathPicker(initialPath, onSelect)` opens a modal, fetches
`/api/browse-directory?path=...` starting from `initialPath` (or the
drive list if blank/nonexistent), renders a breadcrumb and the folder
list, double-click navigates in, an "Up" action (when `parent` is
non-null) goes up, a "Chọn thư mục này" button calls
`onSelect(currentPath)` and closes the modal, "Hủy" just closes it.

### `inspector_panel.js` change

In the existing STRING-field render loop (`renderInspector`, the one
that currently only checks `inputType !== "STRING"`), also read
`spec[1]?.widget`. When it is `"path"`, append a small "Browse…" button
next to the textarea:
```js
openPathPicker(field.value, (chosen) => {
  field.value = chosen;
  node.properties[name] = chosen;
  markActiveDirty();
});
```
This is additive to the existing textarea, not a replacement — the user
can still type/paste a path by hand.

### Marking the existing path fields

`LoadTextFile.path` and `SaveTextFile.path` (`server/nodes/utility.py`)
both get `{"default": "", "widget": "path"}` instead of `{"default": ""}`.
This is the only change to those two nodes.

## Xử lý lỗi

- Nonexistent/inaccessible `path` query param → `HTTPException(400, ...)`
  with a clear message, per above.
- A subfolder that raises `PermissionError` during listing is silently
  skipped from the results, not fatal to the request.

## Phụ thuộc & thứ tự triển khai

Independent of the other two sub-projects at the file level. The
Glossary & Chapter Consistency spec's `RecordChapter` node adds
`widget: "path"` flags to its own two fields regardless of whether this
spec has shipped yet — the flag is simply inert (a plain textarea) until
this ships. The Agent Template Library spec's own "Chọn agent…" picker
is a **separate**, purpose-built modal (language tabs → genre list, not
a folder browser) and does not depend on this spec; if useful during
implementation, its button can be wired through the same generic
`widget`-flag mechanism established here (e.g. `widget: "agent_template"`)
rather than duplicating the button-rendering code in
`inspector_panel.js` — a call this project's established "share one
implementation, don't duplicate" norm favors, but not a hard requirement
if that spec ships first.

## Ngoài phạm vi

- Any restriction/sandboxing of `GET /api/browse-directory` beyond what
  `LoadTextFile`/`SaveTextFile` already imply about this app's trust
  model.
- A file picker (as opposed to a folder picker) — every current use case
  is "point at a folder" or "point at a path to read/write a whole file
  by name you already know", not "browse and pick an existing file".
