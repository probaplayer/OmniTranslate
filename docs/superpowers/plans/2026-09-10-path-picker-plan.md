# Path Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user pick a filesystem folder through a UI popup instead
of typing/pasting an absolute path by hand, for every path-shaped node
input in the canvas app.

**Architecture:** A new backend endpoint (`GET /api/browse-directory`)
lists a directory's subfolders (or, with no path given, the Windows drive
list); a new frontend module (`path_picker.js`) drives a small modal
against that endpoint; `inspector_panel.js` grows a generic mechanism —
any STRING input whose spec carries `widget: "path"` gets a "Browse…"
button next to its existing textarea, wired to the modal. `LoadTextFile.path`
and `SaveTextFile.path` are the first two fields to carry that flag.

**Tech Stack:** FastAPI (backend endpoint), vanilla JS/DOM (frontend
modal, no framework — matches every other UI module in `web/js/`),
`pathlib`/`os.listdrives()` (Python 3.14, confirmed via `python --version`
against this project's venv — well past the 3.12 floor `os.listdrives()`
needs).

**Spec:** `docs/superpowers/specs/2026-09-10-path-picker-design.md`

## Global Constraints

- No new Python dependency — everything needed (`os.listdrives`, `pathlib`)
  is in the standard library.
- `GET /api/browse-directory` follows this codebase's existing error
  convention: a client-caused failure (bad path) is a 400 with a clear
  `detail` message, matching `_workspace_http_error`'s style in
  `server/main.py` — not a bespoke shape.
- A subfolder that can't be stat'd (permission error) is skipped from the
  listing, never a fatal error for the whole request — matches
  `workspace.list_workspaces()`'s established "skip what fails, don't
  crash the batch" precedent.
- The "Browse…" button is additive to the existing textarea in
  `inspector_panel.js` — the user can still type/paste a path by hand;
  nothing about existing STRING-field rendering changes for fields
  without the `widget: "path"` flag.

---

### Task 1: `GET /api/browse-directory` endpoint

**Files:**
- Modify: `server/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `GET /api/browse-directory?path=<optional>` →
  `{"path": str | null, "parent": str | null, "entries": [{"name": str, "path": str}]}`.
  `path` is `null` only for the no-query-param "drive list" case.
  A nonexistent or non-directory `path` → HTTP 400 with a `detail` string.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_api.py` (it already imports `TestClient`/`app` at the
top of the file — no new imports needed beyond what's already there):

```python
def test_browse_directory_lists_subdirectories(tmp_path):
    (tmp_path / "chapters").mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "notes.txt").write_text("not a directory")

    client = TestClient(app)
    response = client.get("/api/browse-directory", params={"path": str(tmp_path)})

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == str(tmp_path)
    names = {e["name"] for e in body["entries"]}
    assert names == {"chapters", "output"}


def test_browse_directory_reports_parent_for_going_up(tmp_path):
    child = tmp_path / "chapters"
    child.mkdir()

    client = TestClient(app)
    response = client.get("/api/browse-directory", params={"path": str(child)})

    assert response.json()["parent"] == str(tmp_path)


def test_browse_directory_rejects_nonexistent_path(tmp_path):
    client = TestClient(app)
    response = client.get(
        "/api/browse-directory", params={"path": str(tmp_path / "missing")}
    )

    assert response.status_code == 400


def test_browse_directory_rejects_a_file_path(tmp_path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello")

    client = TestClient(app)
    response = client.get("/api/browse-directory", params={"path": str(file_path)})

    assert response.status_code == 400


def test_browse_directory_empty_path_returns_drive_list():
    client = TestClient(app)
    response = client.get("/api/browse-directory")

    assert response.status_code == 200
    body = response.json()
    assert body["path"] is None
    assert body["parent"] is None
    assert len(body["entries"]) > 0  # at least the drive these tests run from


def test_browse_directory_skips_permission_denied_subfolder(tmp_path, monkeypatch):
    (tmp_path / "ok").mkdir()
    (tmp_path / "locked").mkdir()

    real_is_dir = Path.is_dir

    def flaky_is_dir(self):
        if self.name == "locked":
            raise PermissionError("denied")
        return real_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", flaky_is_dir)

    client = TestClient(app)
    response = client.get("/api/browse-directory", params={"path": str(tmp_path)})

    assert response.status_code == 200
    names = {e["name"] for e in response.json()["entries"]}
    assert names == {"ok"}
```

`tests/test_api.py` needs `from pathlib import Path` for the last test —
check whether it's already imported at the top of the file before adding
it a second time.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py -k browse_directory -v`
Expected: every one FAILs (404, since the route doesn't exist yet).

- [ ] **Step 3: Implement the endpoint**

In `server/main.py`, `os.listdrives()` alone covers the drive-list case —
no `string`/manual `A:`–`Z:` probe needed (confirmed against this
project's venv: `python --version` → 3.14.3, well past the 3.12 floor
`os.listdrives()` requires). Add near the top with the other imports:

```python
import os
```

Add the route (anywhere among the other `@app.get(...)` routes — e.g.
right after `get_workspace_graph`, before the `PUT`):

```python
@app.get("/api/browse-directory")
def browse_directory(path: str = ""):
    if not path:
        entries = [
            {"name": drive.rstrip("\\/"), "path": drive}
            for drive in os.listdrives()
        ]
        return {"path": None, "parent": None, "entries": entries}

    target = Path(path)
    if not target.is_dir():
        raise HTTPException(
            status_code=400, detail="Path does not exist or is not a directory"
        )

    entries = []
    try:
        children = sorted(target.iterdir(), key=lambda p: p.name.lower())
    except PermissionError:
        children = []
    for child in children:
        try:
            if child.is_dir():
                entries.append({"name": child.name, "path": str(child)})
        except PermissionError:
            continue

    # A drive root is its own parent in pathlib (Path("C:/").parent == Path("C:/")) --
    # without this check, "Up" from a drive root would loop on itself forever
    # instead of surfacing the drive list.
    parent = str(target.parent) if target.parent != target else None
    return {"path": str(target), "parent": parent, "entries": entries}
```

`Path` and `HTTPException` are already imported at the top of
`server/main.py` — no new import needed for those.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py -k browse_directory -v`
Expected: all 6 PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: all pre-existing tests still pass (this task only adds a new
route; nothing existing is touched).

- [ ] **Step 6: Commit**

```bash
git add server/main.py tests/test_api.py
git commit -m "feat: add GET /api/browse-directory for the path picker"
```

---

### Task 2: Path picker modal (`web/js/path_picker.js`)

**Files:**
- Create: `web/js/path_picker.js`
- Modify: `web/canvas.html`
- Modify: `web/js/i18n.js`

**Interfaces:**
- Consumes: `GET /api/browse-directory` (Task 1).
- Produces: `openPathPicker(initialPath, onSelect)` — a global function,
  called by Task 3's `inspector_panel.js` change. `onSelect` is called
  with exactly one argument, the chosen absolute path string, only when
  the user confirms a selection (never called on cancel).

- [ ] **Step 1: Add the i18n keys**

In `web/js/i18n.js`, add to the `vi` object (anywhere among the existing
keys, e.g. right after `noOtherWorkspaces`):

```js
    pathPickerSelect: "Chọn thư mục này",
    pathPickerCancel: "Hủy",
    pathPickerDrives: "Ổ đĩa",
```

And to the `en` object, in the same relative position:

```js
    pathPickerSelect: "Select this folder",
    pathPickerCancel: "Cancel",
    pathPickerDrives: "Drives",
```

- [ ] **Step 2: Write `web/js/path_picker.js`**

```js
let pathPickerState = null;

function openPathPicker(initialPath, onSelect) {
  closePathPicker();

  const overlay = document.createElement("div");
  overlay.id = "path-picker-overlay";
  overlay.className = "path-picker-overlay";

  const modal = document.createElement("div");
  modal.className = "path-picker-modal";

  const breadcrumb = document.createElement("div");
  breadcrumb.className = "path-picker-breadcrumb";
  modal.appendChild(breadcrumb);

  const list = document.createElement("div");
  list.className = "path-picker-list";
  modal.appendChild(list);

  const actions = document.createElement("div");
  actions.className = "path-picker-actions";
  const selectButton = document.createElement("button");
  selectButton.textContent = t("pathPickerSelect");
  const cancelButton = document.createElement("button");
  cancelButton.textContent = t("pathPickerCancel");
  actions.appendChild(selectButton);
  actions.appendChild(cancelButton);
  modal.appendChild(actions);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  pathPickerState = { currentPath: null, onSelect };

  cancelButton.addEventListener("click", closePathPicker);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closePathPicker();
  });
  selectButton.addEventListener("click", () => {
    if (pathPickerState && pathPickerState.currentPath) {
      pathPickerState.onSelect(pathPickerState.currentPath);
    }
    closePathPicker();
  });

  loadPathPickerDirectory(initialPath || "");
}

function closePathPicker() {
  const overlay = document.getElementById("path-picker-overlay");
  if (overlay) overlay.remove();
  pathPickerState = null;
}

async function loadPathPickerDirectory(path) {
  const response = await fetch(`/api/browse-directory?path=${encodeURIComponent(path)}`);
  if (!response.ok) {
    // The starting path (e.g. an old, now-deleted folder already in the
    // field) may not exist any more -- fall back to the drive list
    // instead of leaving the modal stuck on a failed request.
    if (path !== "") {
      await loadPathPickerDirectory("");
    }
    return;
  }
  const data = await response.json();
  renderPathPicker(data);
}

function renderPathPicker(data) {
  if (!pathPickerState) return;
  pathPickerState.currentPath = data.path;

  const overlay = document.getElementById("path-picker-overlay");
  if (!overlay) return;

  const breadcrumb = overlay.querySelector(".path-picker-breadcrumb");
  breadcrumb.textContent = data.path || t("pathPickerDrives");

  const list = overlay.querySelector(".path-picker-list");
  list.innerHTML = "";

  if (data.parent !== null) {
    const upItem = document.createElement("div");
    upItem.className = "path-picker-item";
    upItem.textContent = "..";
    upItem.addEventListener("click", () => loadPathPickerDirectory(data.parent));
    list.appendChild(upItem);
  }

  for (const entry of data.entries) {
    const item = document.createElement("div");
    item.className = "path-picker-item";
    item.textContent = entry.name;
    item.addEventListener("dblclick", () => loadPathPickerDirectory(entry.path));
    item.addEventListener("click", () => {
      pathPickerState.currentPath = entry.path;
      list
        .querySelectorAll(".path-picker-item.selected")
        .forEach((el) => el.classList.remove("selected"));
      item.classList.add("selected");
    });
    list.appendChild(item);
  }
}
```

Single-click on an entry selects it (highlights it, sets it as the
current pick) without navigating into it; double-click navigates into it.
"Chọn thư mục này" always uses whatever `pathPickerState.currentPath`
currently is — either the directory being browsed (if no specific entry
was clicked) or a specific single-clicked entry.

- [ ] **Step 3: Add the modal CSS and script tag to `web/canvas.html`**

Add this block to the `<style>` section (anywhere after the
`#open-workspace-menu`-related rules is a natural place, since it's the
other absolutely-positioned popup in this file):

```css
    .path-picker-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 100;
    }
    .path-picker-modal {
      width: 420px;
      max-height: 70vh;
      display: flex;
      flex-direction: column;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 9px;
      padding: 14px;
      box-sizing: border-box;
    }
    .path-picker-breadcrumb {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-faint);
      margin-bottom: 8px;
      word-break: break-all;
    }
    .path-picker-list {
      flex: 1;
      overflow-y: auto;
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-bottom: 10px;
    }
    .path-picker-item {
      padding: 7px 10px;
      font-size: 12.5px;
      color: var(--text);
      cursor: pointer;
    }
    .path-picker-item:hover { background: var(--bg-hover); }
    .path-picker-item.selected { background: var(--bg-hover); color: var(--accent); }
    .path-picker-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
    .path-picker-actions button {
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 12px;
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
    }
    .path-picker-actions button:hover { border-color: var(--accent); color: var(--accent); }
```

Add the script tag right before `inspector_panel.js`'s own tag (so
`openPathPicker` exists by the time Task 3's button handler can call
it):

```html
  <script src="/js/path_picker.js"></script>
  <script src="/js/inspector_panel.js"></script>
```

- [ ] **Step 4: Manual verification**

Start the server, open the canvas page, run in the browser console:
`openPathPicker("", (chosen) => console.log("picked:", chosen))`. Confirm
the modal shows the drive list, double-clicking a drive navigates into
it, single-clicking an entry highlights it, "Chọn thư mục này" logs the
picked path and closes the modal, "Hủy" closes it without logging
anything.

- [ ] **Step 5: Commit**

```bash
git add web/js/path_picker.js web/canvas.html web/js/i18n.js
git commit -m "feat: add the path picker modal"
```

---

### Task 3: Wire the "Browse…" button into the inspector, mark the two existing path fields

**Files:**
- Modify: `web/js/inspector_panel.js`
- Modify: `server/nodes/utility.py`
- Modify: `web/js/i18n.js`

**Interfaces:**
- Consumes: `openPathPicker(initialPath, onSelect)` (Task 2).
- Produces: nothing new for later tasks — this is the last task that
  changes shared code; Task 4 is verification only.

- [ ] **Step 1: Add the i18n key**

In `web/js/i18n.js`, add to `vi`: `browseButton: "Duyệt...",` and to
`en`: `browseButton: "Browse...",` (same relative position as Task 2's
keys).

- [ ] **Step 2: Change the STRING-field loop in `web/js/inspector_panel.js`**

The current loop (lines 89–103 as of this plan being written — re-read
the file first, since Task 2 did not touch this file and the line
numbers should still match) is:

```js
  for (const [name, spec] of Object.entries(allInputs)) {
    const inputType = spec[0];
    if (inputType !== "STRING" || linked.has(name)) continue;

    appendInspectorLabel(panel, name);
    const field = document.createElement("textarea");
    field.className = "inspector-input";
    field.rows = 3;
    field.value = node.properties[name] || "";
    field.addEventListener("input", () => {
      node.properties[name] = field.value;
      markActiveDirty();
    });
    panel.appendChild(field);
  }
```

Change it to:

```js
  for (const [name, spec] of Object.entries(allInputs)) {
    const inputType = spec[0];
    if (inputType !== "STRING" || linked.has(name)) continue;

    appendInspectorLabel(panel, name);
    const field = document.createElement("textarea");
    field.className = "inspector-input";
    field.rows = 3;
    field.value = node.properties[name] || "";
    field.addEventListener("input", () => {
      node.properties[name] = field.value;
      markActiveDirty();
    });
    panel.appendChild(field);

    const config = spec[1] || {};
    if (config.widget === "path") {
      const browseButton = document.createElement("button");
      browseButton.className = "inspector-browse-button";
      browseButton.textContent = t("browseButton");
      browseButton.addEventListener("click", () => {
        openPathPicker(field.value, (chosen) => {
          field.value = chosen;
          node.properties[name] = chosen;
          markActiveDirty();
        });
      });
      panel.appendChild(browseButton);
    }
  }
```

Every field without `widget: "path"` in its spec renders exactly as
before (`config.widget` is `undefined`, the `if` is skipped) — this is
purely additive.

- [ ] **Step 3: Add the button's CSS to `web/canvas.html`**

Add next to the existing `.inspector-input:focus` rule:

```css
    .inspector-browse-button {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text-faint);
      font-size: 11.5px;
      padding: 6px 8px;
      border-radius: 6px;
      cursor: pointer;
      margin-top: 4px;
      box-sizing: border-box;
    }
    .inspector-browse-button:hover { border-color: var(--accent); color: var(--accent); }
```

- [ ] **Step 4: Mark `LoadTextFile.path` and `SaveTextFile.path`**

In `server/nodes/utility.py`, change:

```python
    def INPUT_TYPES(cls):
        return {"required": {"path": ("STRING", {"default": ""})}}
```

(inside `LoadTextFile`) to:

```python
    def INPUT_TYPES(cls):
        return {"required": {"path": ("STRING", {"default": "", "widget": "path"})}}
```

And inside `SaveTextFile`, change:

```python
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": ""}),
                "path": ("STRING", {"default": ""}),
            }
        }
```

to:

```python
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": ""}),
                "path": ("STRING", {"default": "", "widget": "path"}),
            }
        }
```

- [ ] **Step 5: Confirm the backend test suite is unaffected**

Run: `pytest -q`
Expected: all pre-existing tests still pass. `widget` is an extra key in
the config dict that no existing test or runtime code inspects — nothing
should break. (There is no dedicated Python test for the `widget` key
itself: it is pure frontend-rendering metadata, consumed only by
`inspector_panel.js`; `list_node_metadata()` already returns whatever
`INPUT_TYPES()` returns verbatim, including this new key, with no
Python-side logic depending on its value.)

- [ ] **Step 6: Manual verification**

Start the server, open the canvas page. Drag a `LoadTextFile` node onto
the canvas, select it — confirm the `path` field's textarea now has a
"Duyệt..." button beneath it, clicking it opens the path picker, picking
a folder fills the textarea and marks the tab dirty. Repeat for
`SaveTextFile.path`. Select a node with an unflagged STRING field (e.g.
`Note.text`) — confirm it renders exactly as before, no button.

- [ ] **Step 7: Commit**

```bash
git add web/js/inspector_panel.js server/nodes/utility.py web/js/i18n.js web/canvas.html
git commit -m "feat: add a Browse button to path-flagged node inputs"
```

---

### Task 4: End-to-end verification

**Files:**
- None created/modified — verification only.

- [ ] **Step 1: Full walkthrough**

- Run the full pytest suite: `pytest -q` — expect all tests passing
  (the count grows by the 6 new `test_browse_directory_*` tests added in
  Task 1; confirm the exact new total against whatever the suite reported
  immediately before this plan started).
- In the browser: drag a `LoadTextFile` node, click "Duyệt...", navigate
  from the drive list into a real folder two levels deep, click "Chọn
  thư mục này" — confirm the field and `node.properties.path` both hold
  the exact folder path you navigated to.
- Click "Duyệt..." again on the same field — confirm the picker opens
  starting from the path already in the field (not the drive list),
  proving `initialPath` round-trips correctly.
- Click "Hủy" partway through browsing — confirm the field's value is
  unchanged from before the picker opened.
- Confirm a workspace's graph containing a `LoadTextFile`/`SaveTextFile`
  node with a path chosen this way saves and reloads correctly (Ctrl+S,
  reload the page, reselect the node, confirm the path field still shows
  the same value).

- [ ] **Step 2: Report results**

No commit for this task. Note anything that didn't work as described
above.
