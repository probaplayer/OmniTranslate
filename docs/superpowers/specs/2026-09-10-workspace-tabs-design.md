# Workspace Tabs & Chapter Text Input — Design

## Bối cảnh

The app currently has two pages: `index.html` (a workspace picker/creator)
and `canvas.html` (the node-graph editor for one workspace, identified by
a `?workspace=` query param). Switching workspaces means navigating back
to `index.html`, and creating a workspace requires filling in a name
upfront before you can start building a graph.

The user wants this replaced with a browser-tab-style interface living
entirely on `canvas.html`: multiple workspaces open as tabs, a way to
start a brand-new workspace without naming it first (name only asked at
first save), and `index.html` retired entirely.

A small, independent second feature is bundled into the same
implementation plan (not architecturally related, just convenient to ship
together): a new node type for pasting a full chapter's raw text so it
can feed directly into `Translate`'s `source_text` input, as an
alternative to `LoadTextFile`.

## Mục tiêu

1. Multiple workspaces open as tabs on `canvas.html`, switching between
   them instantly with no page reload and no loss of in-progress
   (unsaved) edits in the tabs you switch away from.
2. A "+" button starts a brand-new, unsaved/untitled workspace tab
   immediately — no name required until the first save.
3. Ctrl+S (and the existing Save button) saves the active tab; if it has
   never been saved, this is the moment it asks for a name, creates the
   workspace on the backend, and saves the graph into it.
4. A way to open an existing on-disk workspace as a new tab, without
   `index.html`.
5. The set of open tabs (and which is active) survives a page
   reload/browser restart.
6. `index.html` and `web/js/workspace_picker.js` are deleted entirely —
   `canvas.html` becomes the app's only page.
7. A new `TextInput` node for pasting a full chapter's text, output-able
   into `Translate`'s `source_text`.

## Kiến trúc tổng quan

```
web/
  canvas.html                 (Modify: tab bar markup/CSS, remove
                               "← Workspaces" link, root becomes the
                               single entry point)
  index.html                  (Delete)
  js/
    workspace_picker.js       (Delete)
    workspace_tabs.js         (Create: tab state, tab bar rendering,
                               open/close/switch/create/save-prompt logic)
    canvas_app.js              (Modify: canvas/graph setup becomes
                                 tab-aware — one LGraphCanvas, N LGraph
                                 instances; Ctrl+S wiring; save button
                                 delegates to the active tab)
    i18n.js                     (Modify: new keys for tab UI strings)
server/
  main.py                        (Modify: add `GET /` → redirect to
                                   `/canvas.html`)
  nodes/
    utility.py                     (Modify: add `TextInput` node)
tests/
  test_utility_nodes.py              (Modify: add TextInput test)
```

No changes to `translation_core/`, the executor, the websocket protocol,
or workspace filesystem layout (`create_workspace`/`open_workspace`/
`save_graph`/`delete_workspace` are reused exactly as they are — this is
a frontend orchestration change plus one new backend node, not a backend
redesign).

## Thành phần chi tiết

### 1. Tab state model (`workspace_tabs.js`)

One shared `LGraphCanvas` (already exists in `canvas_app.js`). A tab is:

```js
{
  id: "<client-generated, e.g. `t${Date.now()}${Math.random()}`>",
  workspaceName: "<string> | null",   // null = never saved
  graph: LGraph instance,
  dirty: boolean,                      // true once the graph changes
                                        // since last save/load
}
```

Switching the active tab calls the real, verified litegraph API
`canvas.setGraph(tab.graph)` (confirmed in the vendored `litegraph.js`:
`LGraphCanvas.prototype.setGraph` cleanly detaches the canvas from the
old graph and attaches it to the new one — no data loss, no destructive
side effect on the graph being switched away from). This is why
unsaved edits in a background tab survive switching: the `LGraph` object
itself just sits in memory, un-rendered, until its tab is reselected.

`dirty` is set `true` by hooking the same events `canvas_app.js` already
uses to know something changed (litegraph fires `graph.onNodeAdded`/
`onNodeRemoved`/etc., but the simplest reliable signal already available
in this codebase is: mark dirty whenever `graph.change()` fires, which
litegraph already calls internally on most graph mutations — verify this
against the vendored source during planning; if `graph.change` doesn't
cover node property edits made through the inspector panel, also mark
dirty explicitly from `inspector_panel.js`'s property-edit handlers).
`dirty` resets to `false` immediately after a successful save or a fresh
load.

### 2. Tab bar (`canvas.html` markup/CSS + `workspace_tabs.js` rendering)

A new `<div id="workspace-tabs">` strip, placed between `#toolbar` and
`#app-layout` (full width, one row). Contents, left to right:

- One pill per open tab: `{workspaceName || t("untitledWorkspace")}`,
  a small dot indicator when `dirty`, and a "×" close button. Clicking
  the pill body (not the ×) makes it active. The active tab's pill is
  visually distinguished (accent border/background, matching this app's
  existing `--accent` token).
- `+` button: creates a new tab with `workspaceName: null`, an empty
  `new LGraph()`, `dirty: false`, and makes it active.
- `Mở workspace...` button opening a small dropdown listing on-disk
  workspaces (via the existing `GET /api/workspaces`) that are NOT
  already open in a tab; clicking one fetches its graph (`GET
  /api/workspaces/{name}`), creates a tab for it, `graph.configure(...)`
  its saved data in, and makes it active.

The "← Workspaces" link is removed from `#toolbar` entirely (spec goal
6) — `#toolbar` keeps the brand mark, Run/Save/Batch buttons, status
line, and VI/EN toggle exactly as they are today.

### 3. Save flow (Ctrl+S + Save button)

`canvas_app.js`'s existing `saveGraph()` is refactored to operate on
"the active tab" instead of the module-level `workspaceName`/`graph`
constants it currently closes over. New flow:

1. If the active tab's `workspaceName` is not `null`: `PUT
   /api/workspaces/{name}/graph` with `activeTab.graph.serialize()`,
   exactly as today. On success, clear `dirty`.
2. If it IS `null` (never saved): prompt for a name (a plain
   `window.prompt(t("promptWorkspaceName"))` — no new modal component
   needed for this MVP), validate it client-side against the same
   allowlist pattern the backend enforces (`^[A-Za-z0-9_-]+$`, matching
   `server/workspace.py`'s `_NAME_PATTERN` — reject and re-prompt with an
   inline error if it doesn't match, without a wasted round-trip to the
   server for an input that can never succeed), then `POST
   /api/workspaces` with that name, then `PUT .../graph` with the
   current graph, then set `activeTab.workspaceName` = that name and
   clear `dirty`. If the name collides with an existing workspace (409
   from the backend), show the error and re-prompt rather than silently
   failing.

`document.addEventListener("keydown", ...)` adds the Ctrl+S (and Cmd+S
for consistency, though this app has no stated macOS requirement — cheap
to include) binding, calling `event.preventDefault()` to suppress the
browser's native save-page dialog, then invoking the same save function
the Save button uses.

### 4. Persistence across reload (`localStorage`)

Key `"openTabs"`: a JSON array of `{workspaceName}` objects for every tab
whose `workspaceName` is not `null` (an unsaved tab has nothing to
reload, so it's correctly excluded — matching the already-agreed
behavior: closing the browser loses untitled tabs). Key
`"activeWorkspaceName"`: which one was active. Both updated whenever the
tab set or active tab changes.

On page load, `workspace_tabs.js` reads `"openTabs"`, and for each
entry, fetches that workspace's graph and creates a tab exactly as the
"Mở workspace..." flow does, restoring the previously-active one as
active. If the list is empty (first-ever visit, or nothing was open),
create a single blank, untitled tab — the page is never left with zero
tabs.

If a remembered workspace no longer exists on disk (deleted through some
other means since last visit), skip it silently rather than erroring the
whole restore — the same tolerant pattern `list_workspaces()` already
uses for invalid directory names.

### 5. Closing a tab

Clicking a tab's "×": if `!dirty`, remove it immediately (detach nothing
special — the `LGraph` object is simply dropped, garbage collected). If
`dirty`, show a plain `window.confirm(t("confirmDiscardTab"))`; proceed
only on OK. If the closed tab was active, activate the tab to its left
(or right, if it was leftmost), or create a fresh blank tab if it was the
only one open — the tab bar is never left empty.

### 6. `index.html` / `workspace_picker.js` removal, root redirect

Both files are deleted outright (not left as dead, unlinked code — this
project's established convention). `server/main.py` gains one new route,
registered alongside the other `@app.get(...)` handlers and before the
existing `app.mount("/", StaticFiles(...))` line (mount order matters:
routes registered earlier win for an exact path match):

```python
from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse(url="/canvas.html")
```

`canvas.html` no longer requires a `?workspace=` query param to be
useful — it's meaningful to visit bare (shows whatever tabs
`localStorage` remembers, or one blank tab). A `?workspace=name` param,
if present on load, is still honored as "also open/activate this
workspace" (useful for a future feature — e.g. a shareable/bookmarkable
link into a specific workspace — even though nothing generates such a
link yet); if the query param names a workspace not already open, it's
opened and activated in addition to whatever `localStorage` restores.

### 7. `TextInput` node (independent of the tab work)

New node in `server/nodes/utility.py`, alongside `LoadTextFile`/
`SaveTextFile`/`TextPreview`/`Note`:

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

This needs zero frontend changes: `node_palette.js`/`nodegen.js`/
`inspector_panel.js` all already drive themselves off `/api/nodes`'s
metadata generically, and the existing `NODE_TYPE_META` icon/color table
(from the prior Node Visual Identity plan) falls back to a neutral
icon/color for any type it doesn't recognize — a new i18n label/
description entry is a nice-to-have polish item, not a requirement, since
the fallback path already works correctly. The inspector panel already
renders any unlinked STRING input as an editable multi-line textarea, so
pasting a full chapter's text works immediately.

## Data flow

Tab switch: `workspace_tabs.js` calls `canvas.setGraph(tab.graph)` →
litegraph's own `attachCanvas`/`detachCanvas` handles the rest → existing
`initInspectorPanel`/`initMinimap` etc. already read `graph`/`canvas` by
reference at call time inside their own functions (not by a stale closed-
over binding) — **verify this during planning**: if any of them cached
the `graph` reference at `init()` time instead of reading `window`/module-
level `graph` fresh, switching tabs would leave them pointed at the old
graph. This is the single most important cross-cutting correctness check
for this whole feature, since `graph`/`canvas` currently exist as
module-level `const`s in `canvas_app.js` that other files (`inspector_
panel.js`, `log_console.js`, `minimap.js`, `node_palette.js`,
`batch_panel.js`) receive as function parameters at `init()` time and may
have stored in their own module-level variables (`inspectorGraph`, etc.)
— those will need to be updated on every tab switch, not just left as
whatever `init()` first passed them.

Save: user action (Ctrl+S / button) → active tab has a name? → PUT
graph : prompt name → POST workspace → PUT graph → tab adopts name.

Load: page load → read `localStorage` → for each remembered tab, GET
workspace graph → `graph.configure(...)` → tab created → restore active
tab → (if `?workspace=` param present and not already open) open it too.

## Error handling

- Save-time name collision (409) or invalid name (400) — shown inline
  near the prompt, re-prompt, don't lose the in-memory graph.
- A remembered tab whose workspace was deleted out-of-band — skipped
  silently on restore (see §4).
- Closing the last tab always leaves exactly one (fresh blank) tab —
  never zero.
- Ctrl+S while there are zero unsaved changes on an already-named tab
  still round-trips a `PUT` (matches today's Save button behavior
  exactly — no new "nothing to save" special case, keeping this
  consistent with existing behavior rather than adding a new state to
  track).

## Testing

Backend: a new `pytest` test for `TextInput` in `tests/
test_utility_nodes.py`, following the existing flat-function convention
(`get_node_class("TextInput")().execute(text="...")` asserted against
the expected tuple). No backend test needed for the `GET /` redirect
beyond a simple existing-pattern check if the test suite already covers
routing (optional, low-value — a manual check is enough since this is a
one-line redirect).

Frontend: no automated tests (matches this project's established
convention for all prior frontend work) — manual/live-server
verification per the implementation plan's own task-level checklists,
including the specific cross-cutting check flagged in "Data flow" above
(every module that received `graph`/`canvas` at init time must observe a
tab switch correctly, not just the modules obviously related to tabs).

## Ngoài phạm vi

- Renaming a workspace after it's been saved (out of scope — matches
  today's behavior, where a workspace's name is fixed at creation).
- Reordering tabs by drag-and-drop.
- A workspace being open in two tabs simultaneously (not prevented, but
  not a designed-for use case — if it happens, "Mở workspace..." simply
  omits already-open ones, so a user can't trivially do this by accident
  through the provided UI).
- Any change to `translation_core/`, the executor, or the websocket
  protocol.
- A rich/custom save-name dialog — a plain `window.prompt()` is
  sufficient for this MVP.
- i18n labels/description for the new `TextInput` node type beyond the
  fallback icon/color/label the existing system already provides —
  cheap to add later, not required for correctness.

## Cấu trúc thư mục dự kiến

(See Kiến trúc tổng quan above.)
