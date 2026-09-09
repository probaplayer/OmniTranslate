# Workspace Tabs & Chapter Text Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `index.html` workspace picker with a browser-tab-style
multi-workspace interface built directly into `canvas.html`, where a new
workspace starts unnamed and is only created on the backend at first save;
plus a small independent new node for pasting a full chapter's raw text.

**Architecture:** One shared `LGraphCanvas` instance; `workspace_tabs.js`
owns an array of `{id, workspaceName, graph, dirty}` tab objects and
switches the active one via litegraph's own `canvas.setGraph(graph)`
(confirmed in the vendored source to cleanly detach/reattach with no data
loss). Every other module that used to receive a `graph` reference once at
init time (`inspector_panel.js`, `minimap.js`, `node_palette.js`) is
changed to call `getActiveGraph()` fresh every time it needs one, instead
of caching a stale reference — this eliminates an entire class of
"forgot to update this panel on tab switch" bugs rather than requiring a
notify-every-module-on-switch mechanism.

**Tech Stack:** Vanilla JS (no build step, litegraph.js vendored,
unchanged), FastAPI backend (one new node class, one new route — no
`translation_core`/executor/websocket-protocol changes).

**Spec:** [docs/superpowers/specs/2026-09-10-workspace-tabs-design.md](../specs/2026-09-10-workspace-tabs-design.md)

## Global Constraints

- No changes to `translation_core/`, `server/executor.py`, or the
  websocket protocol (`/ws/run/{name}`'s message shapes are unchanged).
- Workspace name validation on the client must match the backend exactly:
  `^[A-Za-z0-9_-]+$` (from `server/workspace.py`'s `_NAME_PATTERN`).
- No automated frontend tests (matches this project's established
  convention) — every frontend task ends with a manual-verification
  checklist instead. The one new backend node gets a real `pytest` test,
  matching `tests/test_utility_nodes.py`'s existing convention.
- `LGraph.prototype.change()`/`on_change` is documented in the vendored
  `litegraph.js` itself as "Called when something visually changed (not
  the graph!)" and is NOT reliably triggered by this app's own property
  edits (verified: `inspector_panel.js`'s textarea `input` handler writes
  `node.properties[name]` directly with no hook call at all) — dirty-tab
  tracking must use explicit `markActiveDirty()` calls at every mutation
  point this app's own code performs, with `graph.on_change` wired only
  as a supplementary catch-all for litegraph-internal mutations (node
  drag, wire connect/disconnect).
- `LGraphCanvas.prototype.clear()` (called by `setGraph()` unless
  `skip_clear`) resets `this.selected_nodes = {}` directly — it does NOT
  invoke `onNodeDeselected`. Every tab switch must explicitly clear
  `inspector_panel.js`'s own `inspectorSelectedNode` state, or a stale
  node reference from the previous tab's graph would linger.
- `LGraphCanvas`'s constructor safely accepts `null`/no graph (confirmed:
  `if (graph) { graph.attachCanvas(this); }` — no error, no crash);
  `canvas.setGraph(graph)` is the correct, real, verified API for
  attaching/reattaching a graph after construction.
- `index.html` and `web/js/workspace_picker.js` are deleted outright once
  the new flow is confirmed working (last task, not first) — never left
  as orphaned dead code.

---

## File Structure

```
server/
  main.py                     (Task 2: add GET / -> redirect to /canvas.html)
  nodes/
    utility.py                  (Task 1: add TextInput node)
tests/
  test_utility_nodes.py           (Task 1: add TextInput test)
web/
  canvas.html                       (Task 7: tab bar markup/CSS, remove
                                     "← Workspaces" link; Task 8: open-
                                     workspace dropdown markup/CSS)
  index.html                          (Task 10: delete)
  js/
    workspace_picker.js                 (Task 10: delete)
    workspace_tabs.js                     (Task 3: create — tab data
                                           model, single-tab bootstrap;
                                           Task 7: tab bar rendering +
                                           blank-tab/close; Task 8: open-
                                           existing-workspace dropdown;
                                           Task 9: localStorage persistence)
    canvas_app.js                           (Task 3: refactor to delegate
                                             graph/workspace-name access
                                             to workspace_tabs.js)
    inspector_panel.js                        (Task 4: consume
                                                getActiveGraph()/
                                                getActiveWorkspaceName()
                                                live, add dirty-marking,
                                                add clearInspectorSelection)
    minimap.js                                  (Task 5: consume
                                                 getActiveGraph() live)
    node_palette.js                               (Task 6: consume
                                                   getActiveGraph() live
                                                   in the drop handler,
                                                   add dirty-marking)
    i18n.js                                         (Tasks 3, 7, 8: new
                                                     keys as each task
                                                     needs them)
```

Task order: 1, 2 (independent backend work, can run first) → 3
(foundational tab data model + `canvas_app.js` refactor — leaves
`inspector_panel.js`/`minimap.js`/`node_palette.js` temporarily
incompatible, by design, fixed in the next 3 tasks) → 4, 5, 6 (bring each
of those three files up to date, one at a time, restoring full app
function) → 7 (visible tab bar UI, multi-tab arrives) → 8 (open an
existing workspace as a tab) → 9 (persist tabs across reload) → 10
(delete the now-fully-superseded `index.html`/`workspace_picker.js`) →
11 (end-to-end verification).

---

### Task 1: `TextInput` node

**Files:**
- Modify: `server/nodes/utility.py`
- Modify: `tests/test_utility_nodes.py`

**Interfaces:**
- Produces: a new registered node type `"TextInput"` (category
  `"Utility"`), `RETURN_TYPES = ("STRING",)`, discoverable via the
  existing `GET /api/nodes` — no other task depends on this directly
  (it needs zero frontend changes, since the inspector panel/palette
  already render any registered node type generically from `/api/nodes`
  metadata).

- [ ] **Step 1: Add the node**

In `server/nodes/utility.py`, add this class after the existing `Note`
class (at the end of the file):

```python
@register_node("TextInput")
class TextInput(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, text: str) -> tuple:
        return (text,)
```

- [ ] **Step 2: Add the test**

In `tests/test_utility_nodes.py`, add this test after
`test_note_does_not_raise` (following the file's existing flat-function
convention exactly):

```python
def test_text_input_returns_the_pasted_text():
    node = get_node_class("TextInput")()
    result = node.execute(text="toàn bộ nội dung chương")
    assert result == ("toàn bộ nội dung chương",)
```

- [ ] **Step 3: Run the test**

Run: `D:\VsCode\MCPToolTranslaterNovel\.venv\Scripts\python.exe -m pytest tests/test_utility_nodes.py -v`
Expected: 5 passed (the 4 existing ones plus this new one).

- [ ] **Step 4: Manual verification**

Start the server, `curl http://127.0.0.1:8000/api/nodes` and confirm a
`"TextInput"` entry appears with `"category": "Utility"`,
`"return_types": ["STRING"]`, and `"input_types": {"required": {"text":
["STRING", {"default": ""}]}}`.

- [ ] **Step 5: Commit**

```bash
git add server/nodes/utility.py tests/test_utility_nodes.py
git commit -m "feat: add TextInput node for pasting a full chapter's raw text"
```

---

### Task 2: `GET /` redirect to `/canvas.html`

**Files:**
- Modify: `server/main.py`

**Interfaces:**
- Produces: `GET /` now returns a redirect instead of serving
  `index.html` — this is what makes deleting `index.html` in Task 10 not
  break bare-root visits. No other task depends on this route directly.

- [ ] **Step 1: Add the redirect route**

Change the import block:

```python
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
```

to:

```python
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
```

Then add this route right after the `app = FastAPI()` line (and its
following `WEB_DIR = ...`/`_ALLOWED_ORIGINS = ...` lines — insert the new
route among the other `@app.get(...)` handlers, e.g. right before
`@app.get("/api/health")`):

```python
@app.get("/")
def root():
    return RedirectResponse(url="/canvas.html")
```

This must be registered before the `app.mount("/", StaticFiles(...))`
line at the bottom of the file (it already is, since all `@app.get`
routes are declared above that mount) — Starlette checks explicitly
registered routes before falling through to a mount for the same path.

- [ ] **Step 2: Manual verification**

Start the server, `curl -i http://127.0.0.1:8000/` and confirm a `307`
(or `302`) response with `location: /canvas.html`. Confirm
`http://127.0.0.1:8000/api/health` and the other existing routes are
unaffected (`curl http://127.0.0.1:8000/api/health` still returns
`{"status":"ok"}`).

- [ ] **Step 3: Run the full pytest suite**

Run: `D:\VsCode\MCPToolTranslaterNovel\.venv\Scripts\python.exe -m pytest -q`
Expected: all passing (130 + the new `TextInput` test from Task 1 = 131),
confirming this route addition didn't break anything existing.

- [ ] **Step 4: Commit**

```bash
git add server/main.py
git commit -m "feat: redirect bare / to /canvas.html"
```

---

### Task 3: Tab data model core + `canvas_app.js` refactor

**Files:**
- Create: `web/js/workspace_tabs.js`
- Modify: `web/js/canvas_app.js`
- Modify: `web/canvas.html` (one script tag added)
- Modify: `web/js/i18n.js` (new keys)

**Interfaces:**
- Consumes: `LGraph`, `LGraphCanvas` (litegraph globals), `t(key)` (i18n),
  `setStatus(text, kind)` (defined in `canvas_app.js`, called by
  `workspace_tabs.js` — both are plain global scripts, no import needed).
- Produces: globals `getActiveGraph() -> LGraph | null`,
  `getActiveWorkspaceName() -> string | null`, `markActiveDirty() ->
  void`, `saveActiveTab() -> Promise<void>`, `initWorkspaceTabs() ->
  Promise<void>`, `createTabForGraph(workspaceName, graph) -> tab
  object`, `activateTab(tab) -> void`. These are consumed by Tasks 4, 5,
  6 (`getActiveGraph`/`markActiveDirty`), by `canvas_app.js` itself
  (`saveActiveTab`, `initWorkspaceTabs`), and by Task 7+ (which extends
  this same file with the visible tab bar).
- Calls (defensively, since it doesn't exist yet until Task 4):
  `clearInspectorSelection()` — guarded with `if (typeof
  clearInspectorSelection === "function")`, the same forward-reference
  pattern already used successfully elsewhere in this project (e.g.
  `inspector_panel.js`'s pre-existing guarded call to `appendLogEntry`
  before `log_console.js` existed in an earlier plan).

**IMPORTANT — expected temporary breakage:** after this task,
`inspector_panel.js`, `minimap.js`, and `node_palette.js` still expect
their OLD call signatures (`initInspectorPanel(nodeMetadataList, graph,
canvas, workspaceName)`, `initMinimap(graph, canvas, canvasEl)`,
`initNodePalette(nodeMetadataList, graph, canvas, canvasEl)`), but this
task's `canvas_app.js` calls them with the NEW signatures those files
will adopt in Tasks 4-6. **This will throw a JS error in the browser
console and those three panels will not work correctly until Tasks 4-6
land** — this is expected and matches a precedent already established in
this project's history (widgets were removed in one task and replaced by
the inspector panel in the very next task, with the same kind of
documented gap). This task's own verification is scoped accordingly:
confirm the tab data model itself works at the console level, not that
the whole page renders perfectly.

- [ ] **Step 1: Create `web/js/workspace_tabs.js`**

```js
let tabs = [];
let activeTabId = null;

function makeTabId() {
  return `t${Date.now()}${Math.random().toString(36).slice(2)}`;
}

function getActiveTab() {
  return tabs.find((tab) => tab.id === activeTabId) || null;
}

function getActiveGraph() {
  const tab = getActiveTab();
  return tab ? tab.graph : null;
}

function getActiveWorkspaceName() {
  const tab = getActiveTab();
  return tab ? tab.workspaceName : null;
}

function markActiveDirty() {
  const tab = getActiveTab();
  if (tab) tab.dirty = true;
}

function createTabForGraph(workspaceName, graph) {
  graph.on_change = () => markActiveDirty();
  graph.start();
  const tab = { id: makeTabId(), workspaceName, graph, dirty: false };
  tabs.push(tab);
  return tab;
}

function activateTab(tab) {
  activeTabId = tab.id;
  canvas.setGraph(tab.graph);
  if (typeof clearInspectorSelection === "function") clearInspectorSelection();
  canvas.setDirtyCanvas(true, true);
}

async function saveActiveTab() {
  const tab = getActiveTab();
  if (!tab) return;

  if (tab.workspaceName === null) {
    let name = window.prompt(t("promptWorkspaceName"));
    if (name === null) return;
    name = name.trim();
    if (!/^[A-Za-z0-9_-]+$/.test(name)) {
      setStatus(t("statusInvalidWorkspaceName"), "error");
      return;
    }
    const createResponse = await fetch("/api/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, source_lang: "", target_lang: "" }),
    });
    if (!createResponse.ok) {
      let detail = t("createWorkspaceGenericError");
      try {
        const body = await createResponse.json();
        detail = body.detail || detail;
      } catch {
        // response body wasn't JSON -- keep the generic message
      }
      setStatus(detail, "error");
      return;
    }
    tab.workspaceName = name;
  }

  const saveResponse = await fetch(
    `/api/workspaces/${encodeURIComponent(tab.workspaceName)}/graph`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tab.graph.serialize()),
    }
  );
  if (!saveResponse.ok) {
    setStatus(`${t("statusSaveError")}${saveResponse.status}`, "error");
    return;
  }
  tab.dirty = false;
  setStatus(t("statusSaved"), "ok");
}

async function initWorkspaceTabs() {
  const params = new URLSearchParams(window.location.search);
  const initialWorkspaceName = params.get("workspace");

  let graph;
  if (initialWorkspaceName) {
    const response = await fetch(`/api/workspaces/${encodeURIComponent(initialWorkspaceName)}`);
    graph = new LGraph();
    if (response.ok) {
      const savedGraph = await response.json();
      if (savedGraph.nodes && savedGraph.nodes.length) {
        graph.configure(savedGraph);
        for (const node of graph._nodes) {
          const minHeight = node.computeSize()[1];
          if (node.size[1] < minHeight) node.size[1] = minHeight;
        }
      }
    } else {
      setStatus(`${t("statusLoadWorkspaceError")}${response.status}`, "error");
    }
    const tab = createTabForGraph(initialWorkspaceName, graph);
    activateTab(tab);
  } else {
    graph = new LGraph();
    const tab = createTabForGraph(null, graph);
    activateTab(tab);
  }
}
```

Note: `graph.start()` (inside `createTabForGraph`) launches litegraph's
own per-frame `requestAnimationFrame` execution loop
(`LGraph.prototype.start`, confirmed in the vendored source) — this is
harmless for this app since none of our dynamically-registered node
classes implement `onExecute` (our actual execution model is the
separate REST/WebSocket-driven `run_graph`, not litegraph's built-in
per-frame stepping), so each open tab running its own idle loop costs
nothing meaningful. Deliberately not adding stop/restart-on-switch
machinery for a performance concern that doesn't exist in practice here
(YAGNI) — every tab's graph keeps ticking an effectively-empty loop
whether it's the active one or not, exactly as the single graph did
before this change.

- [ ] **Step 2: Refactor `web/js/canvas_app.js`**

Replace the entire file content with:

```js
const canvasEl = document.getElementById("graph-canvas");

// NODE_TITLE_COLOR/LINK_COLOR must be set before LGraphCanvas is
// constructed: its constructor copies them into instance properties
// (node_title_color/default_link_color) once, at construction time, and
// the renderer reads those cached copies rather than the LiteGraph
// globals afterward -- setting these after `new LGraphCanvas(...)` would
// silently have no visual effect.
LiteGraph.NODE_DEFAULT_BGCOLOR = "#1a1d23";
LiteGraph.NODE_DEFAULT_COLOR = "#2a2f37";
LiteGraph.NODE_TITLE_COLOR = "#9aa1ab";
LiteGraph.LINK_COLOR = "#d9a44c";
LiteGraph.NODE_WIDTH = 200;

// No graph is attached yet -- LGraphCanvas's constructor explicitly
// tolerates this (`if (graph) { graph.attachCanvas(this); }`, verified
// in the vendored source). workspace_tabs.js's initWorkspaceTabs()
// attaches the first real graph via canvas.setGraph(...).
const canvas = new LGraphCanvas(canvasEl, null);
canvas.clear_background_color = "#101216";

// The <canvas> element's drawing-buffer resolution defaults to 300x150 and
// does not track its CSS/flex-layout size on its own -- without this, nodes
// are drawn into (and clipped by) that tiny buffer while it's stretched to
// fill the page, making them invisible or misplaced relative to real mouse
// coordinates.
function syncCanvasSize() {
  canvas.resize(canvasEl.clientWidth, canvasEl.clientHeight);
}
syncCanvasSize();
window.addEventListener("resize", syncCanvasSize);
if (window.ResizeObserver) {
  new ResizeObserver(syncCanvasSize).observe(document.getElementById("canvas-area"));
}

function setStatus(text, kind = "info") {
  const statusEl = document.getElementById("status");
  statusEl.textContent = text;
  statusEl.className = `status-${kind}`;
}

let nodeMetadataList = null;

async function init() {
  const nodesResponse = await fetch("/api/nodes");
  if (!nodesResponse.ok) {
    setStatus(`${t("statusLoadNodesError")}${nodesResponse.status}`, "error");
    return;
  }
  nodeMetadataList = await nodesResponse.json();
  registerDynamicNodeTypes(nodeMetadataList);
  initNodePalette(nodeMetadataList, canvas, canvasEl);
  initInspectorPanel(nodeMetadataList, canvas);
  initLogConsole();
  initMinimap(canvas, canvasEl);
  initBatchPanel();

  await initWorkspaceTabs();
}

function runGraph() {
  const activeGraph = getActiveGraph();
  const activeWorkspaceName = getActiveWorkspaceName();
  if (!activeGraph) return;
  if (!activeWorkspaceName) {
    setStatus(t("statusSaveBeforeRun"), "error");
    return;
  }

  const payload = buildExecutionPayload(activeGraph);
  const ws = new WebSocket(`ws://${location.host}/ws/run/${encodeURIComponent(activeWorkspaceName)}`);

  ws.onopen = () => ws.send(JSON.stringify({ graph: payload }));

  ws.onerror = () => setStatus(t("statusWsError"), "error");

  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    appendLogEntry(event);
    if (event.event === "run_finished") {
      setStatus(t("statusRunFinished"), "ok");
      return;
    }
    if (event.event === "validation_error") {
      setStatus(`${t("statusValidationError")}${event.message}`, "error");
      return;
    }
    if (event.event === "runtime_error") {
      setStatus(`${t("statusRuntimeError")}${event.message}`, "error");
      return;
    }
    const node = activeGraph.getNodeById(Number(event.node_id));
    if (node) {
      if (event.event === "node_started") node._runStatus = "running";
      else if (event.event === "node_completed") node._runStatus = "done";
      else node._runStatus = "error";
      node._runStatusAt = Date.now();
      activeGraph.setDirtyCanvas(true, true);
    }
    setStatus(`${event.event}: node ${event.node_id}`);
  };
}

document.getElementById("run-button").addEventListener("click", runGraph);
document.getElementById("save-button").addEventListener("click", saveActiveTab);
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    saveActiveTab();
  }
});

function switchLang(lang) {
  setLang(lang);
  renderInspector();
  if (nodeMetadataList) initNodePalette(nodeMetadataList, canvas, canvasEl);
  renderLogEmptyState();
  const activeGraph = getActiveGraph();
  if (activeGraph) activeGraph.setDirtyCanvas(true, true);
}

document.getElementById("lang-vi-button").addEventListener("click", () => switchLang("vi"));
document.getElementById("lang-en-button").addEventListener("click", () => switchLang("en"));

init();
```

Key changes from the current file: no more module-level `graph`/
`workspaceName` constants; `saveGraph()` is gone, replaced by
`saveActiveTab()` from `workspace_tabs.js`; `runGraph()` now reads
`getActiveGraph()`/`getActiveWorkspaceName()` fresh on every call and
refuses to run if the active tab has never been saved (surfacing
`statusSaveBeforeRun` instead of attempting a websocket call against a
workspace name that doesn't exist on disk — `NEEDS_WORKSPACE` nodes would
otherwise create an orphaned directory, the exact failure mode
`server/main.py`'s own `ws_run` handler comment already warns about); a
new `keydown` listener implements Ctrl+S/Cmd+S.

- [ ] **Step 3: Add the new script tag to `web/canvas.html`**

Add this line right before the existing `<script src="/js/canvas_app.js"></script>` line:

```html
<script src="/js/workspace_tabs.js"></script>
```

(`workspace_tabs.js` must load before `canvas_app.js`, since
`canvas_app.js`'s `init()` calls `initWorkspaceTabs()` — but
`workspace_tabs.js`'s own top-level code doesn't touch `canvas`/
`setStatus`/`t` until its FUNCTIONS are called later, by which time
`canvas_app.js`'s own top-level `const canvas = ...` line has already
run, since that happens before `init()` is invoked at the very bottom of
that same script.)

- [ ] **Step 4: Add the new i18n keys**

In `web/js/i18n.js`, add to the `vi` object (anywhere after
`batchUnavailable`, before the closing `},`):

```js
    promptWorkspaceName: "Đặt tên cho workspace:",
    statusInvalidWorkspaceName: "Tên workspace không hợp lệ — chỉ dùng chữ, số, - và _",
    statusSaveBeforeRun: "Hãy lưu workspace trước khi chạy",
```

And to the `en` object (same relative position):

```js
    promptWorkspaceName: "Name this workspace:",
    statusInvalidWorkspaceName: "Invalid workspace name — letters, digits, - and _ only",
    statusSaveBeforeRun: "Save the workspace before running",
```

- [ ] **Step 5: Manual verification**

Run `node --check web/js/workspace_tabs.js` and `node --check web/js/canvas_app.js`.
Start the server, open the canvas page for an existing workspace
(`?workspace=<name>`). Open the browser console: confirm `getActiveGraph()`
returns an `LGraph` instance and `getActiveWorkspaceName()` returns the
expected name. Expect visible breakage in the palette/inspector/minimap
(per this task's own note above) — do not treat that as a failure of
this task specifically; confirm instead that the console errors are
exactly about `initNodePalette`/`initInspectorPanel`/`initMinimap` being
called with unexpected arguments (i.e., the OLD versions of those three
files receiving the NEW call signature), not some other unrelated
failure. Confirm the full pytest suite is unaffected (this is a
frontend-only task): `D:\VsCode\MCPToolTranslaterNovel\.venv\Scripts\python.exe -m pytest -q`.

- [ ] **Step 6: Commit**

```bash
git add web/js/workspace_tabs.js web/js/canvas_app.js web/canvas.html web/js/i18n.js
git commit -m "feat: introduce tab-aware graph state, refactor canvas_app.js to delegate to it"
```

---

### Task 4: `inspector_panel.js` — consume live accessors, dirty-marking, selection reset

**Files:**
- Modify: `web/js/inspector_panel.js`

**Interfaces:**
- Consumes: `getActiveGraph()`, `getActiveWorkspaceName()`,
  `markActiveDirty()` (Task 3).
- Produces: `initInspectorPanel(nodeMetadataList, canvas)` (signature
  changed — no more `graph`/`workspaceName` params), `clearInspectorSelection()`
  (consumed by Task 3's `activateTab`, guarded there since it didn't
  exist until now — no change needed on that side, the guard already
  accounts for this).

- [ ] **Step 1: Replace the entire file content**

```js
let inspectorNodeMetadata = {};
let inspectorSelectedNode = null;

function initInspectorPanel(nodeMetadataList, canvas) {
  inspectorNodeMetadata = {};
  for (const meta of nodeMetadataList) {
    inspectorNodeMetadata[meta.type] = meta;
  }

  canvas.onNodeSelected = (node) => {
    inspectorSelectedNode = node;
    renderInspector();
  };
  canvas.onNodeDeselected = () => {
    inspectorSelectedNode = null;
    renderInspector();
  };

  renderInspector();
}

function clearInspectorSelection() {
  inspectorSelectedNode = null;
  renderInspector();
}

function renderInspector() {
  const panel = document.getElementById("inspector-panel");
  if (!panel) return;
  panel.innerHTML = "";

  if (!inspectorSelectedNode) {
    const empty = document.createElement("p");
    empty.className = "inspector-empty";
    empty.textContent = t("inspectorEmpty");
    panel.appendChild(empty);
    return;
  }

  const node = inspectorSelectedNode;
  const meta = inspectorNodeMetadata[node.constructor.nodeType] || {
    input_types: { required: {}, optional: {} },
  };
  const typeMeta = NODE_TYPE_META[node.constructor.nodeType] || NODE_TYPE_META_FALLBACK;

  const header = document.createElement("div");
  header.className = "inspector-header";

  const headerIcon = document.createElement("span");
  headerIcon.className = "inspector-header-icon";
  headerIcon.style.color = typeMeta.color;
  headerIcon.textContent = typeMeta.icon;
  header.appendChild(headerIcon);

  const headerText = document.createElement("div");
  const headerType = document.createElement("div");
  headerType.className = "inspector-header-type";
  headerType.style.color = typeMeta.color;
  headerType.textContent = nodeTypeLabel(node.constructor.nodeType);
  const headerTitle = document.createElement("div");
  headerTitle.className = "inspector-header-title";
  headerTitle.textContent = node.title || node.constructor.nodeType;
  headerText.appendChild(headerType);
  headerText.appendChild(headerTitle);
  header.appendChild(headerText);

  panel.appendChild(header);

  appendInspectorLabel(panel, t("nodeName"));
  const titleInput = document.createElement("input");
  titleInput.className = "inspector-input";
  titleInput.value = node.title || node.constructor.nodeType;
  titleInput.addEventListener("change", () => {
    node.title = titleInput.value;
    markActiveDirty();
    const activeGraph = getActiveGraph();
    if (activeGraph) activeGraph.setDirtyCanvas(true, true);
    renderInspector();
  });
  panel.appendChild(titleInput);

  const linked = linkedInputNames(node);
  const allInputs = Object.assign(
    {},
    meta.input_types.required || {},
    meta.input_types.optional || {}
  );

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

  const actions = document.createElement("div");
  actions.className = "inspector-actions";

  const runButton = document.createElement("button");
  runButton.textContent = t("runNode");
  runButton.addEventListener("click", () => runSingleNode(node));
  actions.appendChild(runButton);

  const deleteButton = document.createElement("button");
  deleteButton.className = "inspector-delete";
  deleteButton.textContent = t("delete");
  deleteButton.addEventListener("click", () => {
    const activeGraph = getActiveGraph();
    if (activeGraph) activeGraph.remove(node);
    markActiveDirty();
    inspectorSelectedNode = null;
    renderInspector();
  });
  actions.appendChild(deleteButton);

  panel.appendChild(actions);
}

function appendInspectorLabel(panel, text) {
  const label = document.createElement("div");
  label.className = "inspector-label";
  label.textContent = text;
  panel.appendChild(label);
}

function runSingleNode(node) {
  const activeGraph = getActiveGraph();
  const activeWorkspaceName = getActiveWorkspaceName();
  if (!activeGraph) return;
  if (!activeWorkspaceName) {
    setStatus(t("statusSaveBeforeRun"), "error");
    return;
  }

  const payload = buildExecutionPayload(activeGraph);
  const nodeId = String(node.id);

  const ancestorIds = new Set([nodeId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const link of payload.links) {
      if (ancestorIds.has(link.to_node) && !ancestorIds.has(link.from_node)) {
        ancestorIds.add(link.from_node);
        changed = true;
      }
    }
  }

  const isolatedNodes = payload.nodes.filter((n) => ancestorIds.has(n.id));
  const isolatedLinks = payload.links.filter(
    (link) => ancestorIds.has(link.from_node) && ancestorIds.has(link.to_node)
  );

  const ws = new WebSocket(
    `ws://${location.host}/ws/run/${encodeURIComponent(activeWorkspaceName)}`
  );
  ws.onopen = () => {
    ws.send(JSON.stringify({ graph: { nodes: isolatedNodes, links: isolatedLinks } }));
  };
  ws.onerror = () => setStatus(t("statusWsError"), "error");
  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    appendLogEntry(event);
    if (event.event === "run_finished") {
      setStatus(t("statusRunFinished"), "ok");
      ws.close();
    }
  };
}
```

Changes from the current file: `inspectorGraph`/`inspectorWorkspaceName`
module variables removed entirely, replaced everywhere by fresh
`getActiveGraph()`/`getActiveWorkspaceName()` calls; `markActiveDirty()`
added at the 3 real mutation points (title change, property edit,
delete); `runSingleNode` now refuses to run (with a clear status message)
if the active tab has never been saved, matching `canvas_app.js`'s
`runGraph()`'s same new behavior from Task 3; new `clearInspectorSelection()`
export.

- [ ] **Step 2: Manual verification**

Start the server, open the canvas page. Confirm the inspector panel now
works exactly as before (select a node, edit its title/properties, run
it, delete it) for the single tab that exists at this point in the plan
(no visible tab bar yet). Confirm editing a node's title or a property
textarea, then checking `getActiveTab().dirty` in the console, returns
`true`. Confirm `node --check web/js/inspector_panel.js` passes.

- [ ] **Step 3: Commit**

```bash
git add web/js/inspector_panel.js
git commit -m "feat: make inspector panel read the active tab's graph live instead of a cached reference"
```

---

### Task 5: `minimap.js` — consume live accessor

**Files:**
- Modify: `web/js/minimap.js`

**Interfaces:**
- Consumes: `getActiveGraph()` (Task 3).
- Produces: `initMinimap(canvas, canvasEl)` (signature changed — no more
  `graph` param).

- [ ] **Step 1: Replace the entire file content**

```js
function initMinimap(canvas, canvasEl) {
  const minimapEl = document.getElementById("minimap");
  if (!minimapEl) return;
  const ctx = minimapEl.getContext("2d");

  function computeWorldBounds(graph) {
    const nodes = graph._nodes;
    if (!nodes.length) return { minX: 0, minY: 0, maxX: 1000, maxY: 1000 };
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const node of nodes) {
      minX = Math.min(minX, node.pos[0]);
      minY = Math.min(minY, node.pos[1]);
      maxX = Math.max(maxX, node.pos[0] + node.size[0]);
      maxY = Math.max(maxY, node.pos[1] + node.size[1]);
    }
    const pad = 100;
    return { minX: minX - pad, minY: minY - pad, maxX: maxX + pad, maxY: maxY + pad };
  }

  function draw() {
    const graph = getActiveGraph();
    const w = minimapEl.width;
    const h = minimapEl.height;
    ctx.clearRect(0, 0, w, h);
    if (!graph) return;

    const bounds = computeWorldBounds(graph);
    const worldW = Math.max(bounds.maxX - bounds.minX, 1);
    const worldH = Math.max(bounds.maxY - bounds.minY, 1);
    const scaleX = w / worldW;
    const scaleY = h / worldH;

    ctx.fillStyle = "#3a3f4a";
    for (const node of graph._nodes) {
      const x = (node.pos[0] - bounds.minX) * scaleX;
      const y = (node.pos[1] - bounds.minY) * scaleY;
      const nw = Math.max(node.size[0] * scaleX, 2);
      const nh = Math.max(node.size[1] * scaleY, 2);
      ctx.fillRect(x, y, nw, nh);
    }

    const viewX = (-canvas.ds.offset[0] - bounds.minX) * scaleX;
    const viewY = (-canvas.ds.offset[1] - bounds.minY) * scaleY;
    const viewW = (canvasEl.clientWidth / canvas.ds.scale) * scaleX;
    const viewH = (canvasEl.clientHeight / canvas.ds.scale) * scaleY;
    ctx.strokeStyle = "#d9a44c";
    ctx.lineWidth = 1;
    ctx.strokeRect(viewX, viewY, viewW, viewH);
  }

  minimapEl.addEventListener("click", (event) => {
    const graph = getActiveGraph();
    if (!graph) return;
    const rect = minimapEl.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    const bounds = computeWorldBounds(graph);
    const worldW = Math.max(bounds.maxX - bounds.minX, 1);
    const worldH = Math.max(bounds.maxY - bounds.minY, 1);
    const worldX = bounds.minX + (clickX / minimapEl.width) * worldW;
    const worldY = bounds.minY + (clickY / minimapEl.height) * worldH;

    canvas.ds.offset[0] = -worldX + canvasEl.clientWidth / (2 * canvas.ds.scale);
    canvas.ds.offset[1] = -worldY + canvasEl.clientHeight / (2 * canvas.ds.scale);
    canvas.setDirtyCanvas(true, true);
  });

  setInterval(draw, 200);
  draw();
}
```

Changes: `graph` is no longer a captured parameter — `computeWorldBounds`
now takes it as an argument, and both `draw()` and the click handler call
`getActiveGraph()` fresh (the existing `setInterval(draw, 200)` means the
minimap picks up a tab switch within 200ms automatically, with zero extra
wiring). `canvas`/`canvasEl` are unchanged (they never differ across
tabs — one shared canvas).

- [ ] **Step 2: Manual verification**

Start the server, open the canvas page, confirm the minimap renders the
current tab's nodes and the click-to-navigate still works exactly as
before. Confirm `node --check web/js/minimap.js` passes.

- [ ] **Step 3: Commit**

```bash
git add web/js/minimap.js
git commit -m "feat: make minimap read the active tab's graph live instead of a cached reference"
```

---

### Task 6: `node_palette.js` — consume live accessor in the drop handler

**Files:**
- Modify: `web/js/node_palette.js`

**Interfaces:**
- Consumes: `getActiveGraph()`, `markActiveDirty()` (Task 3).
- Produces: `initNodePalette(nodeMetadataList, canvas, canvasEl)`
  (signature changed — no more `graph` param).

- [ ] **Step 1: Update the function signature and the drop handler**

Change:

```js
function initNodePalette(nodeMetadataList, graph, canvas, canvasEl) {
```

to:

```js
function initNodePalette(nodeMetadataList, canvas, canvasEl) {
```

Then change the drop handler:

```js
    canvasEl.addEventListener("drop", (event) => {
      event.preventDefault();
      const nodeTypeKey = event.dataTransfer.getData("text/plain");
      if (!nodeTypeKey) return;

      const node = LiteGraph.createNode(nodeTypeKey);
      if (!node) return;

      const rect = canvasEl.getBoundingClientRect();
      const canvasPos = [event.clientX - rect.left, event.clientY - rect.top];
      node.pos = canvas.convertCanvasToOffset(canvasPos);

      graph.add(node);
      graph.setDirtyCanvas(true, true);
    });
```

to:

```js
    canvasEl.addEventListener("drop", (event) => {
      event.preventDefault();
      const nodeTypeKey = event.dataTransfer.getData("text/plain");
      if (!nodeTypeKey) return;

      const activeGraph = getActiveGraph();
      if (!activeGraph) return;

      const node = LiteGraph.createNode(nodeTypeKey);
      if (!node) return;

      const rect = canvasEl.getBoundingClientRect();
      const canvasPos = [event.clientX - rect.left, event.clientY - rect.top];
      node.pos = canvas.convertCanvasToOffset(canvasPos);

      activeGraph.add(node);
      markActiveDirty();
      activeGraph.setDirtyCanvas(true, true);
    });
```

The rest of the file (palette-building loop, `dragstart` handler, the
`canvasEl.dataset.paletteDropWired` idempotency guard from the prior
plan) is unchanged — this guard is exactly what makes this drop handler
safe to leave wired permanently across tab switches: it's registered
once, and now reads the CURRENT active graph on every drop rather than
a graph captured at wire-time, which is what actually fixes the "latent
trap" a prior review flagged about this exact function.

- [ ] **Step 2: Manual verification**

Start the server, open the canvas page. Confirm dragging a node from the
palette onto the canvas still creates it correctly, and `getActiveTab().dirty`
is `true` afterward. This task, combined with Tasks 4-5, restores the app
to full working order for the single implicit tab that exists at this
point in the plan (no visible tab bar yet — that's Task 7). Run the full
end-to-end interaction once here: select a node, edit a property, save
(this will prompt for a name the first time, since the initial tab from
`?workspace=` already has a name, but if you test with a bare
`canvas.html` with no `?workspace=` param, the prompt appears), run it.

- [ ] **Step 3: Commit**

```bash
git add web/js/node_palette.js
git commit -m "feat: make the palette's drop handler read the active tab's graph live"
```

---

### Task 7: Visible tab bar — pills, new blank tab, close, remove nav link

**Files:**
- Modify: `web/canvas.html` (tab bar markup/CSS, remove "← Workspaces" link)
- Modify: `web/js/workspace_tabs.js` (add rendering + blank-tab/close;
  modify `activateTab`/`saveActiveTab` to re-render the bar)
- Modify: `web/js/i18n.js` (new keys)

**Interfaces:**
- Produces: `renderTabBar()`, `switchToTab(id)`, `closeTab(id)`,
  `createBlankTab()` — all in `workspace_tabs.js`, wired to new DOM in
  `canvas.html`.

- [ ] **Step 1: Add the tab bar markup to `web/canvas.html`**

Change:

```html
      <div id="toolbar">
        <span data-i18n="brand" style="font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--accent); margin-right: 4px;">DỊCH XƯỞNG</span>
        <a href="/index.html" data-i18n="backToWorkspaces">&larr; Workspaces</a>
        <button id="batch-toggle-button" data-i18n="batchToggleButton">Hàng loạt</button>
        <button id="run-button" data-i18n="runAllButton">Run</button>
        <button id="save-button" data-i18n="saveButton">Save</button>
        <span id="status" class="status-info"></span>
        <span style="flex: 1;"></span>
        <button id="lang-vi-button">VI</button>
        <button id="lang-en-button">EN</button>
      </div>
      <div id="canvas-area">
```

to:

```html
      <div id="toolbar">
        <span data-i18n="brand" style="font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--accent); margin-right: 4px;">DỊCH XƯỞNG</span>
        <button id="batch-toggle-button" data-i18n="batchToggleButton">Hàng loạt</button>
        <button id="run-button" data-i18n="runAllButton">Run</button>
        <button id="save-button" data-i18n="saveButton">Save</button>
        <span id="status" class="status-info"></span>
        <span style="flex: 1;"></span>
        <button id="lang-vi-button">VI</button>
        <button id="lang-en-button">EN</button>
      </div>
      <div id="workspace-tabs">
        <button id="new-tab-button" data-i18n-title="newTabButton" title="+ Workspace mới">+</button>
      </div>
      <div id="canvas-area">
```

(The "← Workspaces" `<a>` is removed entirely, per spec goal 6.)

- [ ] **Step 2: Add the tab bar CSS**

Add this block right after the existing `#toolbar a:hover { color: var(--text); }` rule:

```css
    #workspace-tabs {
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--bg-elevated);
      border-bottom: 1px solid var(--border-soft);
      padding: 6px 12px;
      overflow-x: auto;
    }
    .workspace-tab {
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 5px 8px 5px 10px;
      font-size: 12px;
      color: var(--text-muted);
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .workspace-tab.active {
      border-color: var(--accent);
      color: var(--text);
      background: var(--bg-hover);
    }
    .workspace-tab-dirty-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent);
      flex-shrink: 0;
    }
    .workspace-tab-close {
      background: transparent;
      border: none;
      color: var(--text-faint);
      cursor: pointer;
      font-size: 13px;
      line-height: 1;
      padding: 0 2px;
    }
    .workspace-tab-close:hover { color: var(--danger); }
    #new-tab-button {
      background: transparent;
      border: 1px dashed var(--border);
      border-radius: 6px;
      color: var(--text-faint);
      cursor: pointer;
      font-size: 12px;
      padding: 5px 10px;
      flex-shrink: 0;
    }
    #new-tab-button:hover { border-color: var(--accent); color: var(--accent); }
```

- [ ] **Step 3: Add tab bar functions to `web/js/workspace_tabs.js`**

Add these new functions anywhere after `createTabForGraph` (e.g. right
after it):

```js
function renderTabBar() {
  const bar = document.getElementById("workspace-tabs");
  if (!bar) return;
  bar.querySelectorAll(".workspace-tab").forEach((el) => el.remove());

  const newTabButton = document.getElementById("new-tab-button");
  for (const tab of tabs) {
    const pill = document.createElement("div");
    pill.className = "workspace-tab" + (tab.id === activeTabId ? " active" : "");
    pill.addEventListener("click", () => switchToTab(tab.id));

    if (tab.dirty) {
      const dot = document.createElement("span");
      dot.className = "workspace-tab-dirty-dot";
      pill.appendChild(dot);
    }

    const label = document.createElement("span");
    label.textContent = tab.workspaceName || t("untitledWorkspace");
    pill.appendChild(label);

    const closeButton = document.createElement("button");
    closeButton.className = "workspace-tab-close";
    closeButton.textContent = "×";
    closeButton.addEventListener("click", (event) => {
      event.stopPropagation();
      closeTab(tab.id);
    });
    pill.appendChild(closeButton);

    bar.insertBefore(pill, newTabButton);
  }
}

function switchToTab(id) {
  const tab = tabs.find((t) => t.id === id);
  if (!tab) return;
  activateTab(tab);
}

function closeTab(id) {
  const tab = tabs.find((t) => t.id === id);
  if (!tab) return;
  if (tab.dirty && !window.confirm(t("confirmDiscardTab"))) return;

  const index = tabs.indexOf(tab);
  tabs.splice(index, 1);

  if (tabs.length === 0) {
    activateTab(createTabForGraph(null, new LGraph()));
  } else if (tab.id === activeTabId) {
    const neighbor = tabs[index] || tabs[index - 1];
    activateTab(neighbor);
  } else {
    renderTabBar();
  }
}

function createBlankTab() {
  activateTab(createTabForGraph(null, new LGraph()));
}

document.getElementById("new-tab-button").addEventListener("click", createBlankTab);
```

- [ ] **Step 4: Wire `renderTabBar()` into `activateTab` and `saveActiveTab`**

In the SAME file, change:

```js
function activateTab(tab) {
  activeTabId = tab.id;
  canvas.setGraph(tab.graph);
  if (typeof clearInspectorSelection === "function") clearInspectorSelection();
  canvas.setDirtyCanvas(true, true);
}
```

to:

```js
function activateTab(tab) {
  activeTabId = tab.id;
  canvas.setGraph(tab.graph);
  if (typeof clearInspectorSelection === "function") clearInspectorSelection();
  canvas.setDirtyCanvas(true, true);
  renderTabBar();
}
```

And change the end of `saveActiveTab` from:

```js
  tab.dirty = false;
  setStatus(t("statusSaved"), "ok");
}
```

to:

```js
  tab.dirty = false;
  setStatus(t("statusSaved"), "ok");
  renderTabBar();
}
```

(`renderTabBar` is defined earlier in the same file by Step 3 above, so
by the time `activateTab`/`saveActiveTab` actually run — at page-load
time, well after the whole script has finished loading — the function
exists; no forward-reference issue.)

- [ ] **Step 5: Add the new i18n keys**

In `web/js/i18n.js`, add to the `vi` object:

```js
    newTabButton: "+ Workspace mới",
    untitledWorkspace: "Chưa lưu",
    confirmDiscardTab: "Đóng workspace này? Các thay đổi chưa lưu sẽ mất.",
```

And to the `en` object:

```js
    newTabButton: "+ New workspace",
    untitledWorkspace: "Untitled",
    confirmDiscardTab: "Close this workspace? Unsaved changes will be lost.",
```

- [ ] **Step 6: Manual verification**

Start the server, open the canvas page. Confirm: the "← Workspaces" link
is gone; one tab pill shows (named, if `?workspace=` was in the URL, or
"Chưa lưu" if not); clicking "+" creates a new "Chưa lưu" tab and
switches to it with a blank canvas; editing something in either tab shows
a dirty dot on its pill; switching back to the first tab shows its
previous state exactly as left (including any unsaved edits); saving the
untitled tab prompts for a name, then that tab's pill updates to show
the real name; closing a dirty tab prompts for confirmation; closing the
last remaining tab always leaves exactly one (fresh blank) tab, never
zero. Confirm Ctrl+S saves the active tab (prompting for a name if
needed).

- [ ] **Step 7: Commit**

```bash
git add web/canvas.html web/js/workspace_tabs.js web/js/i18n.js
git commit -m "feat: add visible tab bar with blank-tab creation and closing, remove workspace nav link"
```

---

### Task 8: "Mở workspace..." — open an existing workspace as a new tab

**Files:**
- Modify: `web/canvas.html` (button + dropdown markup/CSS)
- Modify: `web/js/workspace_tabs.js` (dropdown logic + `openWorkspaceAsTab`)
- Modify: `web/js/i18n.js` (new keys)

**Interfaces:**
- Produces: `openWorkspaceAsTab(name)` — also usable later by Task 9's
  persistence-restore logic (which duplicates the same
  fetch-and-configure steps for multiple remembered tabs at once, so it
  does not call this one-at-a-time version directly, but follows the
  identical pattern).

- [ ] **Step 1: Add the button and dropdown container to `web/canvas.html`**

Change:

```html
      <div id="workspace-tabs">
        <button id="new-tab-button" data-i18n-title="newTabButton" title="+ Workspace mới">+</button>
      </div>
```

to:

```html
      <div id="workspace-tabs">
        <button id="new-tab-button" data-i18n-title="newTabButton" title="+ Workspace mới">+</button>
        <div style="position: relative;">
          <button id="open-workspace-button" data-i18n="openWorkspaceButton">Mở workspace...</button>
        </div>
      </div>
```

- [ ] **Step 2: Add the dropdown CSS**

Add this right after the `#new-tab-button:hover` rule:

```css
    #open-workspace-button {
      background: transparent;
      border: 1px dashed var(--border);
      border-radius: 6px;
      color: var(--text-faint);
      cursor: pointer;
      font-size: 12px;
      padding: 5px 10px;
      flex-shrink: 0;
    }
    #open-workspace-button:hover { border-color: var(--accent); color: var(--accent); }
    #open-workspace-menu {
      position: absolute;
      top: calc(100% + 4px);
      left: 0;
      min-width: 180px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 4px;
      box-shadow: 0 12px 28px rgba(0,0,0,0.4);
      z-index: 10;
    }
    .open-workspace-menu-item {
      padding: 7px 10px;
      font-size: 12.5px;
      color: var(--text);
      border-radius: 5px;
      cursor: pointer;
    }
    .open-workspace-menu-item:hover { background: var(--bg-hover); }
    .open-workspace-menu-empty {
      padding: 7px 10px;
      font-size: 11.5px;
      color: var(--text-faint);
    }
```

- [ ] **Step 3: Add the dropdown logic and `openWorkspaceAsTab` to `web/js/workspace_tabs.js`**

Add these functions after `createBlankTab`'s definition (before the
`document.getElementById("new-tab-button")...` wiring line, or after —
placement relative to that one line doesn't matter):

```js
async function openWorkspaceAsTab(name) {
  const existing = tabs.find((t) => t.workspaceName === name);
  if (existing) {
    switchToTab(existing.id);
    return;
  }
  const response = await fetch(`/api/workspaces/${encodeURIComponent(name)}`);
  const graph = new LGraph();
  if (response.ok) {
    const savedGraph = await response.json();
    if (savedGraph.nodes && savedGraph.nodes.length) {
      graph.configure(savedGraph);
      for (const node of graph._nodes) {
        const minHeight = node.computeSize()[1];
        if (node.size[1] < minHeight) node.size[1] = minHeight;
      }
    }
  } else {
    setStatus(`${t("statusLoadWorkspaceError")}${response.status}`, "error");
    return;
  }
  activateTab(createTabForGraph(name, graph));
}

async function toggleOpenWorkspaceMenu() {
  const existingMenu = document.getElementById("open-workspace-menu");
  if (existingMenu) {
    existingMenu.remove();
    return;
  }
  const response = await fetch("/api/workspaces");
  const data = await response.json();
  const openNames = new Set(tabs.map((t) => t.workspaceName).filter(Boolean));
  const available = data.workspaces.filter((name) => !openNames.has(name));

  const menu = document.createElement("div");
  menu.id = "open-workspace-menu";
  if (available.length === 0) {
    const empty = document.createElement("div");
    empty.className = "open-workspace-menu-empty";
    empty.textContent = t("noOtherWorkspaces");
    menu.appendChild(empty);
  } else {
    for (const name of available) {
      const item = document.createElement("div");
      item.className = "open-workspace-menu-item";
      item.textContent = name;
      item.addEventListener("click", () => {
        menu.remove();
        openWorkspaceAsTab(name);
      });
      menu.appendChild(item);
    }
  }
  document.getElementById("open-workspace-button").parentElement.appendChild(menu);
}

document.getElementById("open-workspace-button").addEventListener("click", toggleOpenWorkspaceMenu);
```

- [ ] **Step 4: Add the new i18n keys**

In `web/js/i18n.js`, add to the `vi` object:

```js
    openWorkspaceButton: "Mở workspace...",
    noOtherWorkspaces: "Không có workspace nào khác",
```

And to the `en` object:

```js
    openWorkspaceButton: "Open workspace...",
    noOtherWorkspaces: "No other workspaces",
```

- [ ] **Step 5: Manual verification**

Create at least 2 saved workspaces (via the existing tab-save flow).
Click "Mở workspace..." — confirm a dropdown lists on-disk workspaces
NOT already open as a tab. Click one — confirm it opens as a new tab with
its saved graph, and becomes active. Click "Mở workspace..." again while
that workspace's tab is now open — confirm it no longer appears in the
list. With zero other workspaces available, confirm the dropdown shows
"Không có workspace nào khác" instead of an empty list.

- [ ] **Step 6: Commit**

```bash
git add web/canvas.html web/js/workspace_tabs.js web/js/i18n.js
git commit -m "feat: add a way to open an existing workspace as a new tab"
```

---

### Task 9: Persist open tabs across page reload

**Files:**
- Modify: `web/js/workspace_tabs.js`

**Interfaces:**
- Produces: `persistTabState()` — called from every function that
  changes which tabs are open or active.
- Consumes: nothing new — this task only adds `localStorage` read/write
  around the existing tab-mutating functions and replaces
  `initWorkspaceTabs`'s body.

- [ ] **Step 1: Add the persistence constants and function**

Add near the top of `web/js/workspace_tabs.js` (after the `let tabs =
[]; let activeTabId = null;` lines):

```js
const TABS_STORAGE_KEY = "openWorkspaceTabs";
const ACTIVE_STORAGE_KEY = "activeWorkspaceTab";

function persistTabState() {
  const names = tabs.map((tab) => tab.workspaceName).filter(Boolean);
  localStorage.setItem(TABS_STORAGE_KEY, JSON.stringify(names));
  const activeTab = getActiveTab();
  if (activeTab && activeTab.workspaceName) {
    localStorage.setItem(ACTIVE_STORAGE_KEY, activeTab.workspaceName);
  } else {
    localStorage.removeItem(ACTIVE_STORAGE_KEY);
  }
}
```

- [ ] **Step 2: Call `persistTabState()` wherever tab state changes**

Add a `persistTabState();` call at the end of `activateTab`, right after
`renderTabBar();`. Add one at the end of `saveActiveTab`, right after its
own `renderTabBar();` call. Add one inside `closeTab`, at the very end
(after all three branches of its `if`/`else if`/`else`).

- [ ] **Step 3: Replace `initWorkspaceTabs()`'s body to restore from `localStorage`**

Replace the entire `initWorkspaceTabs` function with:

```js
async function initWorkspaceTabs() {
  const params = new URLSearchParams(window.location.search);
  const urlWorkspaceName = params.get("workspace");

  let remembered = [];
  try {
    remembered = JSON.parse(localStorage.getItem(TABS_STORAGE_KEY) || "[]");
  } catch {
    remembered = [];
  }
  const namesToOpen = [...remembered];
  if (urlWorkspaceName && !namesToOpen.includes(urlWorkspaceName)) {
    namesToOpen.push(urlWorkspaceName);
  }
  const activeName = urlWorkspaceName || localStorage.getItem(ACTIVE_STORAGE_KEY);

  const createdTabs = [];
  for (const name of namesToOpen) {
    const response = await fetch(`/api/workspaces/${encodeURIComponent(name)}`);
    if (!response.ok) continue; // a remembered workspace that no longer exists -- skip it silently
    const graph = new LGraph();
    const savedGraph = await response.json();
    if (savedGraph.nodes && savedGraph.nodes.length) {
      graph.configure(savedGraph);
      for (const node of graph._nodes) {
        const minHeight = node.computeSize()[1];
        if (node.size[1] < minHeight) node.size[1] = minHeight;
      }
    }
    createdTabs.push(createTabForGraph(name, graph));
  }

  let tabToActivate = createdTabs.find((tab) => tab.workspaceName === activeName);
  if (!tabToActivate) tabToActivate = createdTabs[0];
  if (!tabToActivate) tabToActivate = createTabForGraph(null, new LGraph());

  activateTab(tabToActivate);
}
```

(`activateTab` already calls `renderTabBar()` and, after this task's
Step 2, `persistTabState()` — so the very first render/persist happens
automatically as part of activation, no separate call needed here.)

- [ ] **Step 4: Manual verification**

Open 2-3 workspaces as tabs (mix of ones with real content). Reload the
page (F5). Confirm all the same tabs reappear, with the same one active,
each freshly loaded from disk (so any UNSAVED edit from before the
reload is gone — expected, matches the already-agreed behavior). Open a
brand-new untitled tab, do NOT save it, reload — confirm it's gone (also
expected). Manually delete one of the remembered workspaces' directories
on disk (or via `DELETE /api/workspaces/{name}`) while it's NOT the
active tab, reload — confirm the page loads fine with that one simply
missing, no error shown to the user.

- [ ] **Step 5: Commit**

```bash
git add web/js/workspace_tabs.js
git commit -m "feat: persist open tabs and the active tab across page reloads"
```

---

### Task 10: Delete `index.html` and `workspace_picker.js`

**Files:**
- Delete: `web/index.html`
- Delete: `web/js/workspace_picker.js`

**Interfaces:**
- None — this is a pure removal, safe now that `canvas.html` fully
  replaces everything these two files did (workspace listing → "Mở
  workspace..." dropdown; workspace creation → the first-save naming
  prompt; `/` → redirects to `/canvas.html` since Task 2).

- [ ] **Step 1: Confirm nothing else references these files**

```bash
grep -rn "index.html\|workspace_picker" web/ server/ --include="*.html" --include="*.js" --include="*.py"
```

Expected: no matches (Task 2's redirect targets `/canvas.html`, not
`index.html`; no other file links to either).

- [ ] **Step 2: Delete the files**

```bash
git rm web/index.html web/js/workspace_picker.js
```

- [ ] **Step 3: Manual verification**

Start the server, visit `http://127.0.0.1:8000/` — confirm it redirects
to `/canvas.html` and loads correctly with the tab bar. Visit
`http://127.0.0.1:8000/index.html` directly — confirm a `404` (StaticFiles
correctly reports the file is gone, no stale cached copy served).

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove index.html and workspace_picker.js, fully superseded by workspace tabs"
```

---

### Task 11: End-to-end verification

**Files:**
- None created/modified — verification only.

- [ ] **Step 1: Check for browser automation tooling**

Search your available tools for anything like "browser_navigate" /
"playwright" (`mcp__MCP_DOCKER__browser_*` has been available and used
successfully in this project's recent history, though it runs in a
network-isolated container — reach the host via its LAN IP or
`host.docker.internal` on a server bound to `0.0.0.0` if `localhost`
doesn't work directly). If available, use it for the steps below; if
not, do them via real server + real websocket-client verification plus
careful code tracing, and say so explicitly.

- [ ] **Step 2: Full walkthrough**

- Visit `/` — confirm redirect to `/canvas.html`, one tab present.
- Create a new blank tab via "+", build a small graph (e.g.
  `TextInput` → `SaveTextFile`, using the new node from Task 1 pasted
  directly into the inspector's textarea instead of `LoadTextFile`),
  confirm it shows unsaved/dirty.
- Try clicking "Run" on the unsaved tab — confirm it refuses with the
  "save first" message instead of attempting a websocket call.
- Press Ctrl+S — confirm the name prompt appears, enter a valid name,
  confirm the tab adopts it and the dirty dot clears.
- Click "Run" again — confirm it now actually runs (check the log
  console and the destination file).
- Open a second, pre-existing workspace via "Mở workspace...".
- Switch between the two tabs repeatedly — confirm each tab's graph,
  inspector selection, and minimap all show the correct tab's content
  every time, with no stale data from the other tab ever appearing
  (this is the single most important cross-cutting check for this whole
  plan).
- Edit something in the background (non-active) tab's graph without
  switching to it first... — actually, confirm this the other way:
  switch to tab A, edit it, switch to tab B, switch BACK to tab A,
  confirm the edit is still there (proves in-memory state survives a
  switch away and back).
- Close a dirty tab — confirm the discard confirmation appears; cancel
  it, confirm the tab is NOT closed; confirm again, confirm it IS closed.
- Reload the page — confirm the remaining tabs and active tab are
  restored correctly.
- Switch language (VI/EN) — confirm the tab bar's own text (untitled
  label, button titles) updates too, not just the pre-existing chrome.
- Run the full pytest suite: `D:\VsCode\MCPToolTranslaterNovel\.venv\Scripts\python.exe -m pytest -q` from the repo root (expect 131 passed — 130 from before this plan plus the new `TextInput` test).

- [ ] **Step 3: Report results**

No commit for this task. Write up exactly what you verified and how, and
be explicit about anything that genuinely required a real browser and
could not be confirmed in this environment.

---

## Self-Review Notes

- **Spec coverage:** goal 1 (multi-tab, no reload, no data loss) → Tasks
  3, 7 (verified via litegraph's real `setGraph`); goal 2 (+ button,
  blank/unsaved tab) → Task 7; goal 3 (Ctrl+S + first-save naming) →
  Tasks 3, 7; goal 4 (open existing workspace) → Task 8; goal 5
  (persistence) → Task 9; goal 6 (delete index.html/picker) → Task 10;
  goal 7 (TextInput node) → Task 1. Every spec goal maps to a task. The
  spec's two explicitly-flagged open questions (dirty-tracking mechanism,
  cross-module graph-reference staleness) are both resolved concretely
  in Global Constraints and Task 3-6, backed by direct reads of the
  vendored `litegraph.js` source rather than assumptions.
- **Placeholder scan:** no TBD/TODO. Task 3's documented "expected
  temporary breakage" of Tasks 4-6's target files is a designed,
  precedented interim state (matching this project's own prior plan),
  not a plan gap — its own verification step is scoped accordingly.
- **Type consistency:** `getActiveGraph()`/`getActiveWorkspaceName()`/
  `markActiveDirty()` (Task 3) are called with the exact same names and
  no arguments everywhere they're used (Tasks 4, 5, 6). `initInspectorPanel`/
  `initMinimap`/`initNodePalette`'s NEW signatures (dropping `graph`) are
  used consistently between Task 3's `canvas_app.js` call sites and
  Tasks 4/5/6's own function definitions — verified no mismatch (e.g.
  Task 3 calls `initMinimap(canvas, canvasEl)` with 2 args; Task 5's
  `initMinimap(canvas, canvasEl)` definition also takes exactly 2).
  `clearInspectorSelection()` (Task 4) matches the exact name Task 3's
  guarded call already uses. `renderTabBar`/`switchToTab`/`closeTab`/
  `createBlankTab`/`openWorkspaceAsTab` (Tasks 7-8) are all defined and
  called with consistent names/arities across the tasks that add calls
  to them.

---

Plan complete and saved to `docs/superpowers/plans/2026-09-10-workspace-tabs-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
