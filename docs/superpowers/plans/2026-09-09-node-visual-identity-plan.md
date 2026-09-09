# Node Visual Identity & LM Studio Example Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every node type a consistent icon/color identity shown in
the palette, on the node's canvas card, and in the inspector; add a
custom-drawn status footer to node cards; finish the top bar/palette/log
console to match the provided mockup; and ship a ready-to-run example
workspace demonstrating LM Studio-based translation.

**Architecture:** A single `NODE_TYPE_META` lookup table (icon + color per
node type) lives in `nodegen.js` as a plain global, consumed by
`node_palette.js` and `inspector_panel.js` the same way `t()` and
`appendLogEntry` are already consumed globally across this project's
script-tag-only frontend. Node cards get custom-drawn header/footer rows
via litegraph's real `onDrawForeground`/`slot_start_y` hooks (verified
against the vendored `litegraph.js` source during design, not assumed).
Run status moves from a raw `node.bgcolor` tint to a dedicated
non-serialized `_runStatus`/`_runStatusAt` pair read by the new footer.

**Tech Stack:** Vanilla JS (no build step, no framework — unchanged
project convention), litegraph.js (vendored, unchanged file), Node.js
(only for the one-off example-workspace-building script in Task 8, which
requires the real `litegraph.js` under its confirmed CommonJS export).

**Spec:** [docs/superpowers/specs/2026-09-09-node-visual-identity-design.md](../specs/2026-09-09-node-visual-identity-design.md)

## Global Constraints

- No changes to `server/` or `translation_core/` anywhere in this plan.
- No new REST/WebSocket endpoints.
- `node.properties` remains the single source of truth for a node's
  literal input values — the new `_runStatus`/`_runStatusAt` fields must
  NOT be part of `node.properties` (that object is sent verbatim to the
  backend as execution input).
- Before relying on `_runStatus`/`_runStatusAt` being safe from
  `graph.serialize()`, the implementer of Task 2 must read
  `LGraphNode.prototype.serialize` in the actual vendored `web/js/
  litegraph.js` (around line 2627) and confirm it only serializes a
  fixed, named set of fields, never a `for...in` sweep — this is a
  concrete, checkable fact, not an assumption to carry forward.
- No automated frontend tests for this plan (matches this project's
  established convention) — every task ends with a manual-verification
  checklist instead.
- The example workspace's `graph.json` (Task 8) must be built by running
  a real script against the actual vendored `litegraph.js` (confirmed
  Node-loadable via its own `if (typeof exports != "undefined")` export
  block) — never hand-typed JSON — since litegraph's serialized
  node/link shapes are intricate enough that a hand-typed mistake could
  silently corrupt the file or crash on load.
- The mockup's per-node content-preview line, palette footer stats
  (node count/tokens/cost), and toolbar `appName` subtitle are explicitly
  out of scope — do not add them.

---

## File Structure

```
web/
  js/
    i18n.js               (Task 1: new keys — brand, palette, paletteHint,
                            nodeTypeLabels, nodeTypeDescs, st* status words,
                            plus 2 new helper functions)
    nodegen.js               (Task 2: NODE_TYPE_META table, custom node
                              card draw, slot_start_y, run-status fields)
    canvas_app.js               (Task 3: NODE_WIDTH bump, replace
                                 colorForEvent/bgcolor with _runStatus)
    node_palette.js                (Task 5: header/hint text, icon+desc
                                    per item)
    inspector_panel.js                (Task 6: icon+type+title header
                                       block)
    log_console.js                       (Task 7: count badge, empty
                                          state, colored message text)
  canvas.html                             (Task 4: brand mark markup,
                                           palette/inspector-header/
                                           log-badge CSS + markup)
workspaces/
  vi-du-lm-studio/                          (Task 8: new example
                                             workspace — git-ignored
                                             runtime data, not committed)
```

Task order: 1 (i18n foundation) → 2 (nodegen.js, the core rendering
change) → 3 (canvas_app.js, depends on nodegen.js's `_runStatus` field
name) → 4 (canvas.html CSS/markup, needed by Tasks 5-7) → 5, 6, 7 (palette/
inspector/log, each independent of one another, all depend on Tasks 1-4)
→ 8 (example workspace, depends on Task 2's `registerDynamicNodeTypes`
being in its final form) → 9 (end-to-end verification).

---

### Task 1: i18n additions

**Files:**
- Modify: `web/js/i18n.js`

**Interfaces:**
- Produces: `nodeTypeLabel(type: string) -> string` and
  `nodeTypeDesc(type: string) -> string` — new global helper functions,
  called by Tasks 2 (node card header row), 5 (palette item), and 6
  (inspector header). Both fall back to returning `type` itself
  (`nodeTypeLabel`) or `""` (`nodeTypeDesc`) if the type isn't in the
  table, so a future node type nobody remembered to add here never
  crashes the UI.
- Produces: new flat `t()` keys `brand`, `palette`, `paletteHint`,
  `stIdle`, `stRunning`, `stDone`, `stError` — used by Tasks 2, 4, 5.

- [ ] **Step 1: Add the new flat keys to both language tables**

In `web/js/i18n.js`, in the `vi` object, right after the existing
`backToWorkspaces: "← Workspaces",` line, add:

```js
    brand: "DỊCH XƯỞNG",
```

Right after `batchUnavailable: "Cần Sub-project A2 (Loop Group) — chưa khả dụng.",` (the last key before the object's closing `},`), add:

```js
    palette: "Thư viện node",
    paletteHint: "Kéo vào canvas để thêm.",
    stIdle: "Chờ",
    stRunning: "Đang chạy",
    stDone: "Xong",
    stError: "Lỗi",
```

In the `en` object, right after `backToWorkspaces: "← Workspaces",`, add:

```js
    brand: "DICH XUONG",
```

Right after `batchUnavailable: "Requires Sub-project A2 (Loop Group) — not available yet.",` (the last key before that object's closing `},`), add:

```js
    palette: "Node library",
    paletteHint: "Drag onto the canvas to add.",
    stIdle: "Idle",
    stRunning: "Running",
    stDone: "Done",
    stError: "Error",
```

- [ ] **Step 2: Add the `nodeTypeLabels`/`nodeTypeDescs` nested tables and two helper functions**

Add this new block right after the closing `};` of the `STR` object
(i.e., right after the existing `};` that follows the `en: {...}` block,
before `function currentLang() {`):

```js
const NODE_TYPE_LABELS = {
  vi: {
    LoadTextFile: "ĐỌC FILE", SaveTextFile: "GHI FILE", TextPreview: "XEM TRƯỚC",
    Note: "GHI CHÚ", Provider: "NGUỒN MODEL", LoadAgentFile: "ĐỌC AGENT",
    SaveAgentFile: "GHI AGENT", RAGQuery: "TRUY VẤN RAG", SaveToRAG: "LƯU RAG",
    Translate: "DỊCH",
  },
  en: {
    LoadTextFile: "LOAD FILE", SaveTextFile: "SAVE FILE", TextPreview: "PREVIEW",
    Note: "NOTE", Provider: "MODEL SOURCE", LoadAgentFile: "LOAD AGENT",
    SaveAgentFile: "SAVE AGENT", RAGQuery: "RAG QUERY", SaveToRAG: "SAVE TO RAG",
    Translate: "TRANSLATE",
  },
};

const NODE_TYPE_DESCS = {
  vi: {
    LoadTextFile: "Đọc file text", SaveTextFile: "Ghi file text",
    TextPreview: "Xem trước nội dung", Note: "Ghi chú tự do",
    Provider: "Kết nối API/LM Studio", LoadAgentFile: "Đọc file agent",
    SaveAgentFile: "Ghi file agent", RAGQuery: "Truy vấn RAG",
    SaveToRAG: "Lưu vào RAG", Translate: "Dịch văn bản",
  },
  en: {
    LoadTextFile: "Read a text file", SaveTextFile: "Write a text file",
    TextPreview: "Preview text content", Note: "Freeform note",
    Provider: "API or LM Studio connection", LoadAgentFile: "Read the agent file",
    SaveAgentFile: "Write the agent file", RAGQuery: "Query the RAG store",
    SaveToRAG: "Save into the RAG store", Translate: "Translate text",
  },
};

function nodeTypeLabel(type) {
  const table = NODE_TYPE_LABELS[currentLang()] || NODE_TYPE_LABELS.vi;
  return table[type] || type;
}

function nodeTypeDesc(type) {
  const table = NODE_TYPE_DESCS[currentLang()] || NODE_TYPE_DESCS.vi;
  return table[type] || "";
}
```

(`nodeTypeLabel`/`nodeTypeDesc` call `currentLang()`, which is declared
right below this block in the same file — this is safe because both are
plain function declarations, hoisted before any of them actually run.)

- [ ] **Step 3: Manual verification**

Run `node --check web/js/i18n.js` to confirm no syntax errors. Then start
the server (`python -m uvicorn server.main:app --host 127.0.0.1 --port
8000`), open the browser console on `canvas.html`, and confirm
`nodeTypeLabel("Provider")` returns `"NGUỒN MODEL"` and
`nodeTypeDesc("Translate")` returns `"Dịch văn bản"` (or the English
equivalents after `setLang("en")`), and that an unknown type like
`nodeTypeLabel("Nope")` returns `"Nope"` unchanged. If no browser tool is
available, verify by reading the code path instead and say so explicitly.

- [ ] **Step 4: Commit**

```bash
git add web/js/i18n.js
git commit -m "feat: add i18n keys and helpers for node type labels/descriptions"
```

---

### Task 2: Node type icon/color table + custom-drawn node cards

**Files:**
- Modify: `web/js/nodegen.js`

**Interfaces:**
- Consumes: `nodeTypeLabel(type)` and `t(key)` from Task 1's `i18n.js`
  (loaded before `nodegen.js` in `canvas.html`'s existing script order).
- Produces: global `NODE_TYPE_META` object (`{ [typeName]: { icon,
  color } }`) — consumed by Task 5 (`node_palette.js`) and Task 6
  (`inspector_panel.js`). Every `DynamicNode` instance gets a
  `this._runStatus` (`"idle" | "running" | "done" | "error"`) and
  `this._runStatusAt` (`number | null`, a `Date.now()` timestamp) field —
  consumed by Task 3 (`canvas_app.js`'s websocket handler sets them).

- [ ] **Step 1: Add the type metadata table and status-color/key lookups**

At the very top of `web/js/nodegen.js`, before the existing
`function registerDynamicNodeTypes(nodeMetadataList) {` line, add:

```js
const NODE_TYPE_META = {
  LoadTextFile: { icon: "▤", color: "#7ea6c9" },
  SaveTextFile: { icon: "⤓", color: "#9b8fc4" },
  TextPreview: { icon: "◐", color: "#8d949e" },
  Note: { icon: "✎", color: "#8d949e" },
  Provider: { icon: "✦", color: "#7fb98a" },
  LoadAgentFile: { icon: "◈", color: "#d9a44c" },
  SaveAgentFile: { icon: "◆", color: "#d9a44c" },
  RAGQuery: { icon: "◎", color: "#c98a7e" },
  SaveToRAG: { icon: "◉", color: "#c98a7e" },
  Translate: { icon: "⇄", color: "#7fb98a" },
};
const NODE_TYPE_META_FALLBACK = { icon: "●", color: "#767d88" };

const NODE_HEADER_HEIGHT = 20;
const NODE_FOOTER_HEIGHT = 22;

const RUN_STATUS_COLOR = {
  idle: "#6b7280",
  running: "#d9a44c",
  done: "#7fb98a",
  error: "#d97070",
};
const RUN_STATUS_KEY = {
  idle: "stIdle",
  running: "stRunning",
  done: "stDone",
  error: "stError",
};

function formatClockTime(ms) {
  const d = new Date(ms);
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
}
```

- [ ] **Step 2: Set `slot_start_y`, `boxcolor`, and the run-status fields in `DynamicNode`**

Change:

```js
function registerDynamicNodeTypes(nodeMetadataList) {
  for (const meta of nodeMetadataList) {
    function DynamicNode() {
      const required = meta.input_types.required || {};
      const optional = meta.input_types.optional || {};
      const allInputs = Object.assign({}, required, optional);

      this.properties = {};
      for (const [inputName, spec] of Object.entries(allInputs)) {
        const inputType = spec[0];
        const config = spec[1] || {};
        this.addInput(inputName, inputType);
        this.properties[inputName] = config.default || "";
      }

      meta.return_names.forEach((name, idx) => {
        this.addOutput(name, meta.return_types[idx]);
      });
    }

    DynamicNode.title = meta.type;
    DynamicNode.category = meta.category;
    DynamicNode.nodeType = meta.type;
    LiteGraph.registerNodeType(`${meta.category}/${meta.type}`, DynamicNode);
  }
}
```

to:

```js
function registerDynamicNodeTypes(nodeMetadataList) {
  for (const meta of nodeMetadataList) {
    const typeMeta = NODE_TYPE_META[meta.type] || NODE_TYPE_META_FALLBACK;

    function DynamicNode() {
      const required = meta.input_types.required || {};
      const optional = meta.input_types.optional || {};
      const allInputs = Object.assign({}, required, optional);

      this.properties = {};
      for (const [inputName, spec] of Object.entries(allInputs)) {
        const inputType = spec[0];
        const config = spec[1] || {};
        this.addInput(inputName, inputType);
        this.properties[inputName] = config.default || "";
      }

      meta.return_names.forEach((name, idx) => {
        this.addOutput(name, meta.return_types[idx]);
      });

      this.boxcolor = typeMeta.color;
      this._runStatus = "idle";
      this._runStatusAt = null;
      this.size[1] += NODE_FOOTER_HEIGHT;
    }

    DynamicNode.title = meta.type;
    DynamicNode.category = meta.category;
    DynamicNode.nodeType = meta.type;
    DynamicNode.slot_start_y = NODE_HEADER_HEIGHT;

    DynamicNode.prototype.onDrawForeground = function (ctx) {
      if (this.flags.collapsed) return;
      const tm = NODE_TYPE_META[this.constructor.nodeType] || NODE_TYPE_META_FALLBACK;
      const w = this.size[0];
      const h = this.size[1];

      ctx.save();

      // Header row: icon + uppercase type label, in the type's color.
      ctx.fillStyle = tm.color;
      ctx.font = "10px 'IBM Plex Mono', monospace";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(`${tm.icon} ${nodeTypeLabel(this.constructor.nodeType)}`, 8, NODE_HEADER_HEIGHT / 2);

      // Footer row: separator + status dot + status text + timestamp meta.
      const footerY = h - NODE_FOOTER_HEIGHT;
      ctx.strokeStyle = "rgba(255,255,255,0.06)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, footerY);
      ctx.lineTo(w, footerY);
      ctx.stroke();

      const dotY = footerY + NODE_FOOTER_HEIGHT / 2;
      const statusColor = RUN_STATUS_COLOR[this._runStatus] || RUN_STATUS_COLOR.idle;
      ctx.fillStyle = statusColor;
      ctx.beginPath();
      ctx.arc(10, dotY, 3, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = statusColor;
      ctx.font = "10px 'IBM Plex Mono', monospace";
      ctx.textAlign = "left";
      ctx.fillText(t(RUN_STATUS_KEY[this._runStatus] || RUN_STATUS_KEY.idle), 18, dotY);

      if (this._runStatusAt && (this._runStatus === "done" || this._runStatus === "error")) {
        ctx.fillStyle = "#6f7681";
        ctx.textAlign = "right";
        ctx.fillText(formatClockTime(this._runStatusAt), w - 8, dotY);
      }

      ctx.restore();
    };

    LiteGraph.registerNodeType(`${meta.category}/${meta.type}`, DynamicNode);
  }
}
```

Note: `typeMeta` is computed once per `meta` (outside the `DynamicNode`
function, at registration time — same scope level as `DynamicNode.title
= meta.type` etc.), then closed over by the constructor. This avoids
repeating the `NODE_TYPE_META[...] || NODE_TYPE_META_FALLBACK` lookup on
every single node instantiation — it only needs to happen once per
registered type, not once per node dropped on the canvas. The
`onDrawForeground` function re-derives it via
`NODE_TYPE_META[this.constructor.nodeType]` instead of closing over
`typeMeta` directly, because `onDrawForeground` is assigned to
`DynamicNode.prototype` (shared across all instances of this one type,
defined once outside any per-instance closure) — this is intentional and
correct, not a duplicate lookup path: the closed-over `typeMeta` in the
constructor and the prototype-level lookup in `onDrawForeground` both
resolve to the exact same value for any given type, just computed at two
different times (construction vs. draw) since they're two independent
functions.

- [ ] **Step 2b: Verify the run-status fields are actually safe from serialization**

Read `LGraphNode.prototype.serialize` in `web/js/litegraph.js` (around
line 2627). Confirm it builds its output object by explicitly listing
field names (`id`, `type`, `pos`, `size`, `flags`, `order`, `mode`, then
conditionally `inputs`, `outputs`, `title`, `properties`,
`widgets_values`) rather than iterating over all of the node instance's
own properties. If this is confirmed (it should be, based on the design
research already done for this spec), no further action is needed —
`_runStatus`/`_runStatusAt` will never appear in a saved `graph.json` or
in `buildExecutionPayload()`'s output, since neither reads arbitrary
instance fields. If you find this is NOT true (i.e., serialize really
does sweep all instance properties), STOP and report this as a blocking
finding — the design in this task would need to change (e.g., prefixing
with a JS `Symbol` instead of a string key, or storing status in a
side-table keyed by node id instead of on the node instance).

- [ ] **Step 3: Manual verification**

Run `node --check web/js/nodegen.js`. Start the server, open the canvas
page, drag a `Provider` node onto the canvas. If a browser tool is
available: confirm the node's title-bar circle (top-left) is green, a
green "✦ NGUỒN MODEL" label appears just below the title bar, ports are
visibly shifted down to make room for it, and a footer row with a gray
"Chờ" (idle) dot+text appears at the bottom of the card. Run the graph
(via the existing "Run" button, once Task 3 is also done — if testing
Task 2 in isolation before Task 3 lands, the footer will still render
correctly with the default idle state; the running/done/error color
transitions specifically require Task 3's wiring, so full status-color
verification is deferred to Task 3's own verification step, not
re-tested here). If no browser tool is available, verify via careful
code reading: confirm `computeSize()` in `litegraph.js` reads
`this.constructor.slot_start_y` (already true, unchanged by this task)
and that `this.size[1] += NODE_FOOTER_HEIGHT` executes after
`addInput`/`addOutput` (which is when `this.size` is first populated),
and say explicitly that visual rendering wasn't confirmed live.

- [ ] **Step 4: Commit**

```bash
git add web/js/nodegen.js
git commit -m "feat: add per-node-type icon/color identity and custom-drawn status footer"
```

---

### Task 3: Wire run-status into the websocket handler, widen nodes

**Files:**
- Modify: `web/js/canvas_app.js`

**Interfaces:**
- Consumes: `_runStatus`/`_runStatusAt` fields from Task 2's `nodegen.js`
  (set here, read by `nodegen.js`'s `onDrawForeground`).

- [ ] **Step 1: Bump the default node width**

Change:

```js
LiteGraph.NODE_DEFAULT_BGCOLOR = "#1a1d23";
LiteGraph.NODE_DEFAULT_COLOR = "#2a2f37";
LiteGraph.NODE_TITLE_COLOR = "#9aa1ab";
LiteGraph.LINK_COLOR = "#d9a44c";
```

to:

```js
LiteGraph.NODE_DEFAULT_BGCOLOR = "#1a1d23";
LiteGraph.NODE_DEFAULT_COLOR = "#2a2f37";
LiteGraph.NODE_TITLE_COLOR = "#9aa1ab";
LiteGraph.LINK_COLOR = "#d9a44c";
LiteGraph.NODE_WIDTH = 200;
```

(`NODE_WIDTH` is read live by `computeSize()` on every node, not cached
at construction time like `NODE_TITLE_COLOR`/`LINK_COLOR` are — so unlike
those two, its exact position in this block doesn't matter for
correctness, but keeping it here preserves this project's existing
convention of grouping all `LiteGraph.*` global config together in one
place.)

- [ ] **Step 2: Replace `colorForEvent`/`node.bgcolor` with `_runStatus`/`_runStatusAt`**

Delete the `colorForEvent` function entirely:

```js
// Mirrors the --accent/--success/--danger tokens in style.css. Canvas 2D
// fill/stroke colors can't reference CSS custom properties directly, so
// these are kept as literal hex matching those tokens' values.
function colorForEvent(eventName) {
  if (eventName === "node_started") return "#d9a44c";
  if (eventName === "node_completed") return "#7fb98a";
  return "#d97070";
}
```

Then, in `runGraph()`'s `ws.onmessage` handler, change:

```js
    const node = graph.getNodeById(Number(event.node_id));
    if (node) {
      node.bgcolor = colorForEvent(event.event);
      graph.setDirtyCanvas(true, true);
    }
    setStatus(`${event.event}: node ${event.node_id}`);
```

to:

```js
    const node = graph.getNodeById(Number(event.node_id));
    if (node) {
      if (event.event === "node_started") node._runStatus = "running";
      else if (event.event === "node_completed") node._runStatus = "done";
      else node._runStatus = "error";
      node._runStatusAt = Date.now();
      graph.setDirtyCanvas(true, true);
    }
    setStatus(`${event.event}: node ${event.node_id}`);
```

- [ ] **Step 3: Manual verification**

Start the server, build a small `LoadTextFile → SaveTextFile` graph with
real file paths (via the inspector panel), click "Run". If a browser
tool is available: confirm each node's footer dot/text transitions
gray→gold ("Chờ"→"Đang chạy") then to green ("Xong") with a timestamp
appearing on the right, and that node BODY color no longer changes (no
more whole-node color tint — only the footer changes). If no browser
tool is available, verify by reading the code path (confirm
`_runStatus`/`_runStatusAt` are set exactly as specified, and that no
code anywhere still references the deleted `colorForEvent` — `grep -rn
colorForEvent web/js/` should return nothing) and say so explicitly.

- [ ] **Step 4: Commit**

```bash
git add web/js/canvas_app.js
git commit -m "feat: track run status per-node outside properties, widen default node size"
```

---

### Task 4: Top bar brand mark + palette/inspector-header/log-badge CSS and markup

**Files:**
- Modify: `web/canvas.html`

**Interfaces:**
- Produces: CSS classes `.palette-header`, `.palette-hint`,
  `.palette-item-icon`, `.palette-item-body`, `.palette-item-name`,
  `.palette-item-desc` (consumed by Task 5); `.inspector-header`,
  `.inspector-header-icon`, `.inspector-header-type`,
  `.inspector-header-title` (consumed by Task 6); DOM element
  `#log-count-badge` (consumed by Task 7). This task only adds
  structure/CSS — the elements are inert until Tasks 5-7 populate them.

- [ ] **Step 1: Add the brand mark to the toolbar**

Change:

```html
      <div id="toolbar">
        <a href="/index.html" data-i18n="backToWorkspaces">&larr; Workspaces</a>
```

to:

```html
      <div id="toolbar">
        <span data-i18n="brand" style="font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--accent); margin-right: 4px;">DỊCH XƯỞNG</span>
        <a href="/index.html" data-i18n="backToWorkspaces">&larr; Workspaces</a>
```

- [ ] **Step 2: Add palette header/hint/item CSS**

Change the existing `.palette-item` rule and its neighbors:

```css
    .palette-category:first-child { margin-top: 0; }
    .palette-item {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      cursor: grab;
      font-size: 0.9rem;
      margin-bottom: 6px;
      padding: 8px 10px;
      user-select: none;
    }
    .palette-item:hover { background: var(--bg-hover); border-color: var(--accent); }
    .palette-item:active { cursor: grabbing; }
```

to:

```css
    .palette-category:first-child { margin-top: 0; }
    .palette-header {
      padding: 14px 14px 8px;
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--text-faint);
    }
    .palette-hint {
      padding: 0 14px 10px;
      font-size: 11.5px;
      color: var(--text-faint);
      line-height: 1.5;
    }
    .palette-item {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      cursor: grab;
      display: flex;
      gap: 8px;
      align-items: flex-start;
      font-size: 0.9rem;
      margin-bottom: 6px;
      padding: 8px 10px;
      user-select: none;
    }
    .palette-item:hover { background: var(--bg-hover); border-color: var(--accent); }
    .palette-item:active { cursor: grabbing; }
    .palette-item-icon { font-size: 14px; flex-shrink: 0; width: 16px; text-align: center; }
    .palette-item-body { min-width: 0; }
    .palette-item-name { font-size: 12.5px; font-weight: 500; color: var(--text); }
    .palette-item-desc { font-size: 10.5px; color: var(--text-faint); line-height: 1.35; margin-top: 2px; }
```

- [ ] **Step 3: Add inspector-header CSS**

Right after the existing `.inspector-empty { ... }` rule, add:

```css
    .inspector-header {
      display: flex;
      gap: 9px;
      align-items: center;
      padding-bottom: 12px;
      margin-bottom: 4px;
      border-bottom: 1px solid var(--border-soft);
    }
    .inspector-header-icon { font-size: 18px; }
    .inspector-header-type {
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }
    .inspector-header-title { font-size: 13px; font-weight: 600; margin-top: 2px; }
```

- [ ] **Step 4: Add the log count badge markup and CSS**

Change:

```html
        <div id="log-console-header">
          <span data-i18n="logTitle">Log chạy</span>
          <span style="flex: 1;"></span>
```

to:

```html
        <div id="log-console-header">
          <span data-i18n="logTitle">Log chạy</span>
          <span id="log-count-badge" class="log-count-badge">0</span>
          <span style="flex: 1;"></span>
```

Add this CSS right after the existing `.log-time { color: var(--text-faint); }` rule:

```css
    .log-count-badge {
      font-family: var(--font-mono);
      font-size: 9.5px;
      background: var(--bg-input);
      color: var(--text-faint);
      border-radius: 8px;
      padding: 1px 6px;
    }
```

- [ ] **Step 5: Manual verification**

Start the server, load the canvas page. Confirm the "DỊCH XƯỞNG" brand
mark appears at the left of the toolbar in gold mono uppercase text, and
a "0" badge appears next to "Log chạy". The palette header/hint and
inspector header will still look unchanged until Tasks 5/6 populate
them — that's expected at this point in the plan, not a bug. If no
browser tool is available, verify via curl that the new markup/CSS
exists in the served HTML and say so explicitly.

- [ ] **Step 6: Commit**

```bash
git add web/canvas.html
git commit -m "feat: add brand mark and palette/inspector-header/log-badge styling"
```

---

### Task 5: Node palette header, hint, and per-item icon/description

**Files:**
- Modify: `web/js/node_palette.js`

**Interfaces:**
- Consumes: `NODE_TYPE_META` (Task 2), `nodeTypeDesc(type)`/`t(key)`
  (Task 1), `.palette-header`/`.palette-hint`/`.palette-item-icon`/
  `.palette-item-body`/`.palette-item-name`/`.palette-item-desc` CSS
  classes (Task 4).

- [ ] **Step 1: Add the header/hint and per-item icon+description**

Change:

```js
  paletteEl.innerHTML = "";
  for (const [category, metas] of Object.entries(byCategory)) {
    const heading = document.createElement("div");
    heading.className = "palette-category";
    heading.textContent = category;
    paletteEl.appendChild(heading);

    for (const meta of metas) {
      const nodeTypeKey = `${meta.category}/${meta.type}`;
      const item = document.createElement("div");
      item.className = "palette-item";
      item.textContent = meta.type;
      item.draggable = true;
      item.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", nodeTypeKey);
        event.dataTransfer.effectAllowed = "copy";
      });
      paletteEl.appendChild(item);
    }
  }
```

to:

```js
  paletteEl.innerHTML = "";

  const header = document.createElement("div");
  header.className = "palette-header";
  header.setAttribute("data-i18n", "palette");
  header.textContent = t("palette");
  paletteEl.appendChild(header);

  const hint = document.createElement("div");
  hint.className = "palette-hint";
  hint.setAttribute("data-i18n", "paletteHint");
  hint.textContent = t("paletteHint");
  paletteEl.appendChild(hint);

  for (const [category, metas] of Object.entries(byCategory)) {
    const heading = document.createElement("div");
    heading.className = "palette-category";
    heading.textContent = category;
    paletteEl.appendChild(heading);

    for (const meta of metas) {
      const nodeTypeKey = `${meta.category}/${meta.type}`;
      const typeMeta = NODE_TYPE_META[meta.type] || NODE_TYPE_META_FALLBACK;

      const item = document.createElement("div");
      item.className = "palette-item";
      item.draggable = true;

      const icon = document.createElement("span");
      icon.className = "palette-item-icon";
      icon.style.color = typeMeta.color;
      icon.textContent = typeMeta.icon;
      item.appendChild(icon);

      const body = document.createElement("div");
      body.className = "palette-item-body";
      const name = document.createElement("div");
      name.className = "palette-item-name";
      name.textContent = meta.type;
      const desc = document.createElement("div");
      desc.className = "palette-item-desc";
      desc.textContent = nodeTypeDesc(meta.type);
      body.appendChild(name);
      body.appendChild(desc);
      item.appendChild(body);

      item.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", nodeTypeKey);
        event.dataTransfer.effectAllowed = "copy";
      });
      paletteEl.appendChild(item);
    }
  }
```

Note: the header/hint are given `data-i18n` attributes and their initial
`textContent` set directly via `t(...)` — this is consistent with how
every other `data-i18n`-tagged element in this project works (the
attribute lets a later `setLang()`/`applyTranslations()` call update it,
while the initial render still needs its own `t(...)` call here since
`initNodePalette` runs from `canvas_app.js`'s `init()`, which is async
and could in principle run after or before the very first
`applyTranslations()` pass — setting the text directly here removes any
ordering ambiguity).

- [ ] **Step 2: Manual verification**

Start the server, load the canvas page. Confirm the left panel now shows
"Thư viện node" as a header, "Kéo vào canvas để thêm." as a hint, and
each palette item shows a colored icon glyph plus a description line
below its name (e.g., LoadTextFile shows a blue "▤" and "Đọc file text").
Click "EN" and confirm the header/hint/descriptions switch language.
Confirm drag-and-drop from the palette to the canvas still creates the
correct node type. If no browser tool is available, verify via curl/DOM
structure inspection and say so explicitly.

- [ ] **Step 3: Commit**

```bash
git add web/js/node_palette.js
git commit -m "feat: add header, hint, and per-item icon/description to the node palette"
```

---

### Task 6: Inspector panel icon/type/title header

**Files:**
- Modify: `web/js/inspector_panel.js`

**Interfaces:**
- Consumes: `NODE_TYPE_META` (Task 2), `nodeTypeLabel(type)` (Task 1),
  `.inspector-header`/`.inspector-header-icon`/`.inspector-header-type`/
  `.inspector-header-title` CSS classes (Task 4).

- [ ] **Step 1: Add the header block to `renderInspector()`**

Change:

```js
  const node = inspectorSelectedNode;
  const meta = inspectorNodeMetadata[node.constructor.nodeType] || {
    input_types: { required: {}, optional: {} },
  };

  appendInspectorLabel(panel, t("nodeName"));
```

to:

```js
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
```

This header is a read-only display, built fresh on every `renderInspector()`
call — it does not need to listen for the title input's `change` event to
stay in sync, because `renderInspector()` already re-runs (and rebuilds
this header from `node.title`) any time the title changes: the existing
title `<input>`'s `change` handler already calls
`inspectorGraph.setDirtyCanvas(true, true)`, not `renderInspector()`, so
without a further change here the header's title line WOULD go stale
after an edit. Fix this by also calling `renderInspector()` from the
title input's `change` handler. Change:

```js
  const titleInput = document.createElement("input");
  titleInput.className = "inspector-input";
  titleInput.value = node.title || node.constructor.nodeType;
  titleInput.addEventListener("change", () => {
    node.title = titleInput.value;
    inspectorGraph.setDirtyCanvas(true, true);
  });
```

to:

```js
  const titleInput = document.createElement("input");
  titleInput.className = "inspector-input";
  titleInput.value = node.title || node.constructor.nodeType;
  titleInput.addEventListener("change", () => {
    node.title = titleInput.value;
    inspectorGraph.setDirtyCanvas(true, true);
    renderInspector();
  });
```

- [ ] **Step 2: Manual verification**

Start the server, select a `Translate` node on the canvas. Confirm the
inspector panel now shows a green "⇄" icon, "DỊCH" as the type label, and
the node's title beneath it, above the existing editable "Tên node"
field. Edit the title field and confirm the header's title line updates
immediately to match (this also exercises the `renderInspector()` re-run
without breaking the input's own focus — since the whole panel gets
rebuilt on `change`, not on every keystroke, the input losing focus after
a `change` event, which only fires on blur/Enter, is expected browser
behavior and not a regression). If no browser tool is available, verify
via code tracing and say so explicitly.

- [ ] **Step 3: Commit**

```bash
git add web/js/inspector_panel.js
git commit -m "feat: add icon/type/title header to the inspector panel"
```

---

### Task 7: Log console count badge, empty state, colored messages

**Files:**
- Modify: `web/js/log_console.js`

**Interfaces:**
- Consumes: `.log-count-badge` element `#log-count-badge` (Task 4),
  `t("logEmpty")` (already existed before this plan).
- Produces: `appendLogEntry`/`clearLog`/`initLogConsole` keep their exact
  existing signatures — no other file needs to change to consume this
  task's behavior.

- [ ] **Step 1: Rewrite `log_console.js` to add the badge, empty state, and colored messages**

Replace the entire file content with:

```js
let logOpen = true;

const LOG_MESSAGE_COLOR = {
  node_started: "#d9a44c",
  node_completed: "#7fb98a",
  node_error: "#d97070",
  validation_error: "#d97070",
  runtime_error: "#d97070",
  run_finished: "#7fb98a",
};

function updateLogCountBadge() {
  const badge = document.getElementById("log-count-badge");
  const body = document.getElementById("log-console-body");
  if (!badge || !body) return;
  badge.textContent = String(body.querySelectorAll(".log-entry").length);
}

function renderLogEmptyState() {
  const body = document.getElementById("log-console-body");
  if (!body) return;
  if (body.querySelector(".log-entry")) return;
  if (body.querySelector(".log-empty")) return;
  const empty = document.createElement("div");
  empty.className = "log-empty";
  empty.style.padding = "14px 12px";
  empty.style.fontSize = "11.5px";
  empty.style.color = "#5d646e";
  empty.textContent = t("logEmpty");
  body.appendChild(empty);
}

function appendLogEntry(event) {
  const body = document.getElementById("log-console-body");
  if (!body) return;

  const existingEmpty = body.querySelector(".log-empty");
  if (existingEmpty) existingEmpty.remove();

  const now = new Date();
  const time = [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");

  const row = document.createElement("div");
  row.className = "log-entry";

  const timeEl = document.createElement("span");
  timeEl.className = "log-time";
  timeEl.textContent = time;

  const sourceEl = document.createElement("span");
  sourceEl.textContent = event.node_id ? `node ${event.node_id}` : "run";

  const messageEl = document.createElement("span");
  messageEl.textContent = event.message || event.event;
  const color = LOG_MESSAGE_COLOR[event.event];
  if (color) messageEl.style.color = color;

  row.appendChild(timeEl);
  row.appendChild(sourceEl);
  row.appendChild(messageEl);
  body.appendChild(row);
  body.scrollTop = body.scrollHeight;

  updateLogCountBadge();
}

function clearLog() {
  const body = document.getElementById("log-console-body");
  if (body) body.innerHTML = "";
  renderLogEmptyState();
  updateLogCountBadge();
}

function initLogConsole() {
  const header = document.getElementById("log-console-header");
  const body = document.getElementById("log-console-body");
  const clearButton = document.getElementById("clear-log-button");

  header.addEventListener("click", (event) => {
    if (event.target === clearButton) return;
    logOpen = !logOpen;
    body.style.display = logOpen ? "block" : "none";
  });

  clearButton.addEventListener("click", (event) => {
    event.stopPropagation();
    clearLog();
  });

  renderLogEmptyState();
  updateLogCountBadge();
}
```

- [ ] **Step 2: Manual verification**

Start the server, load the canvas page. Confirm the log console shows
"Chưa có gì." (the empty state) and a "0" badge on load. Run a graph and
confirm: the empty message disappears on the first entry, the badge
count increases with each entry, `node_started` messages appear in gold,
`node_completed`/`run_finished` in green, and any error message in red.
Click "Xoá log" and confirm the empty state reappears and the badge
resets to "0". If no browser tool is available, verify via code tracing
plus a real websocket run against the actual server (this part doesn't
need a browser — confirm via the browser-independent websocket-client
approach already used successfully in the prior plan's Task 9 and its
ad-hoc fix) and say explicitly whether the visual empty-state/badge
rendering itself was confirmed live.

- [ ] **Step 3: Commit**

```bash
git add web/js/log_console.js
git commit -m "feat: add count badge, empty state, and colored messages to the log console"
```

---

### Task 8: LM Studio example workspace

**Files:**
- Create (runtime data, not committed to git — `workspaces/` is
  git-ignored): `workspaces/vi-du-lm-studio/chapters/chuong-1.txt`,
  `workspaces/vi-du-lm-studio/agent.md` (overwriting the default seeded
  file), `workspaces/vi-du-lm-studio/graph.json` (overwriting the default
  empty graph).
- Create (scratch, delete after use — do not commit): a one-off Node.js
  script, e.g. `scripts/build-lm-studio-example.js` or a file in this
  project's scratchpad directory, whichever you have write access to.

**Interfaces:**
- Consumes: `registerDynamicNodeTypes` from Task 2's final `nodegen.js`
  (the script requires this file directly, so it must reflect every
  change from Tasks 1-7 before this task runs — this is why Task 8 is
  ordered last among the content tasks).
- Produces: nothing consumed by later tasks — this is a leaf task.

- [ ] **Step 1: Create the workspace via the running app's own API**

Start the server (`python -m uvicorn server.main:app --host 127.0.0.1
--port 8000`). Create the workspace through the real endpoint, exactly as
the picker page's own form would:

```bash
curl -X POST http://127.0.0.1:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "vi-du-lm-studio", "source_lang": "zh", "target_lang": "vi"}'
```

Expected: `200 OK` (or the app's success status — check
`server/main.py`'s workspace-creation route if unsure of the exact
response shape; the point is that `workspaces/vi-du-lm-studio/` now
exists with the default `config.json`/`graph.json`/`agent.md`/
`chapters/`/`output/` layout, created by the real `create_workspace()`
function, not hand-built).

- [ ] **Step 2: Write the sample chapter and agent instructions**

Create `workspaces/vi-du-lm-studio/chapters/chuong-1.txt`:

```
第一章 hồi khởi đầu

Trời vừa hửng sáng, sương mù còn vương trên đỉnh núi. Một thiếu niên áo vải bạc màu đứng lặng trước cổng tông môn, tay nắm chặt thanh kiếm gỗ đã sờn.

"Nếu ngươi thật sự muốn học kiếm," lão nhân đứng sau lưng nói, giọng trầm như đá, "thì phải quên đi mọi thứ ngươi từng biết về kiếm."

Thiếu niên không quay đầu lại. Gió núi thổi qua, mang theo mùi hương của cỏ dại và đất ẩm.

"Con hiểu," cậu đáp, "nhưng con sẽ không quên tại sao con cầm kiếm."
```

(This is placeholder prose written for this example, not copied from any
real novel — it exists only to give the pipeline realistic-looking input
text to translate.)

Overwrite `workspaces/vi-du-lm-studio/agent.md` with:

```markdown
# Hướng dẫn dịch — Ví dụ LM Studio

Dịch từ tiếng Trung sang tiếng Việt. Giữ văn phong tự sự, trang trọng,
phù hợp thể loại tiên hiệp/kiếm hiệp. Giữ nguyên tên riêng nhân vật và
địa danh (phiên âm Hán-Việt nếu có).

## Glossary mẫu

| Gốc | Dịch |
|---|---|
| 长老 | Trưởng lão |
| 宗门 | Tông môn |
| 剑 | Kiếm |

Không thêm, không bớt nội dung. Giữ nguyên ngắt đoạn của bản gốc.
```

- [ ] **Step 3: Write and run the graph-building script**

Create a scratch file (e.g.
`C:\Users\BUI HUYNH NGOC ANH\.claude\...\scratchpad\build-lm-studio-example.js`
— use this session's actual scratchpad path, not the project directory,
since this script is not meant to be committed) with this content,
substituting `<REPO_ROOT>` for this project's real absolute path:

```js
global.LiteGraph = require("<REPO_ROOT>/web/js/litegraph.js").LiteGraph;
const { LGraph } = require("<REPO_ROOT>/web/js/litegraph.js");
require("<REPO_ROOT>/web/js/nodegen.js");
const fs = require("fs");
const http = require("http");

http.get("http://127.0.0.1:8000/api/nodes", (res) => {
  let body = "";
  res.on("data", (chunk) => (body += chunk));
  res.on("end", () => {
    const nodeMetadataList = JSON.parse(body);
    registerDynamicNodeTypes(nodeMetadataList);

    const graph = new LGraph();

    const loadText = LiteGraph.createNode("Utility/LoadTextFile");
    loadText.pos = [60, 200];
    loadText.properties.path = "<REPO_ROOT>/workspaces/vi-du-lm-studio/chapters/chuong-1.txt";
    graph.add(loadText);

    const provider = LiteGraph.createNode("Translation/Provider");
    provider.pos = [380, 60];
    provider.properties.base_url = "http://localhost:1234/v1";
    provider.properties.api_key = "";
    provider.properties.model = "local-model";
    graph.add(provider);

    const note = LiteGraph.createNode("Utility/Note");
    note.pos = [380, 260];
    note.properties.text =
      "Đổi 'model' ở node Provider thành đúng tên model bạn đã load trong LM Studio, nếu LM Studio yêu cầu tên chính xác.";
    graph.add(note);

    const loadAgent = LiteGraph.createNode("Translation/LoadAgentFile");
    loadAgent.pos = [380, 420];
    graph.add(loadAgent);

    const ragQuery = LiteGraph.createNode("Translation/RAGQuery");
    ragQuery.pos = [700, 420];
    ragQuery.properties.top_k = "3";
    graph.add(ragQuery);

    const translate = LiteGraph.createNode("Translation/Translate");
    translate.pos = [700, 200];
    graph.add(translate);

    const saveText = LiteGraph.createNode("Utility/SaveTextFile");
    saveText.pos = [1020, 200];
    saveText.properties.path = "<REPO_ROOT>/workspaces/vi-du-lm-studio/output/chuong-1-vi.txt";
    graph.add(saveText);

    loadText.connect(0, ragQuery, 0);
    loadText.connect(0, translate, 2);
    provider.connect(0, translate, 0);
    loadAgent.connect(0, translate, 1);
    ragQuery.connect(0, translate, 3);
    translate.connect(0, saveText, 0);

    fs.writeFileSync(
      "<REPO_ROOT>/workspaces/vi-du-lm-studio/graph.json",
      JSON.stringify(graph.serialize(), null, 2)
    );
    console.log("wrote graph.json:", JSON.stringify(graph.serialize()).length, "bytes");
  });
});
```

The slot indices in the script above are already derived from the real
`INPUT_TYPES()` order in `server/nodes/translate.py` and `server/nodes/
utility.py` (not guessed): `Translate`'s required inputs are declared
`provider`, `agent_instructions`, `source_text` (slots 0, 1, 2) with
optional `rag_examples` (slot 3, since optional inputs are appended
after required ones in the same `allInputs` merge order `nodegen.js`
already uses — `Object.assign({}, required, optional)`); `RAGQuery`'s
required `text` is slot 0; `SaveTextFile`'s required `text`/`path` are
slots 0/1. The node-type keys are also already correct:
`LoadTextFile`/`SaveTextFile` are declared `CATEGORY = "Utility"` in
`server/nodes/utility.py`, hence `"Utility/LoadTextFile"`/`"Utility/
SaveTextFile"`, not `"Translation/..."`. Before running the script,
re-confirm all of this yourself against the real `/api/nodes` response
and the two source files — this plan's derivation could still be wrong,
and the whole point of building this via the real library (per the
Global Constraints) is so a mistake here fails loudly (a thrown error
from `connect()` on a bad slot index, or a broken graph on load) rather
than silently producing a corrupt file.

Run it: `node <path-to-script>.js` (with the local server still running,
so the `http.get("http://127.0.0.1:8000/api/nodes")` call succeeds).
Expected output: `wrote graph.json: <N> bytes` with no thrown errors.

- [ ] **Step 4: Verify the generated workspace**

```bash
curl http://127.0.0.1:8000/api/workspaces/vi-du-lm-studio
```

Expected: a JSON object with `"nodes"` (6 entries) and `"links"` (5
entries, matching the corrected connections from Step 3) that parses
without error — confirming `open_workspace()`'s own validation (checked
in `server/workspace.py`: must be a dict with both `nodes` and `links`
keys) accepts the file. If a browser tool is available, additionally
open `http://127.0.0.1:8000/canvas.html?workspace=vi-du-lm-studio` and
confirm the graph renders with 6 visibly distinct, non-overlapping,
correctly-connected node cards.

Then attempt an actual run over the real websocket endpoint (matching
the approach already used successfully in the prior plan's Task 9 and
ad-hoc fix — a Python `websockets` client, or any WS client available in
this environment):

```
ws://127.0.0.1:8000/ws/run/vi-du-lm-studio
```

sending the isolated-run-shaped payload `buildExecutionPayload` would
produce for this graph (or, more simply, the full graph's own
`{nodes, links}` shape built the same way `runGraph()` in
`canvas_app.js` does, adapted to a script). If LM Studio is actually
running locally on port 1234 with a model loaded, expect a full
`run_finished` and a real translated `output/chuong-1-vi.txt`. If LM
Studio is NOT running (likely, in this environment), expect the run to
proceed through `LoadTextFile`/`LoadAgentFile`/`RAGQuery` successfully
and then fail at `Provider`/`Translate` with a connection error — this
is the correct, expected behavior for an environment without LM Studio
installed, not a defect in the example workspace. State clearly in your
report which of these two outcomes actually happened.

- [ ] **Step 5: Delete the scratch script**

```bash
rm <path-to-script>.js
```

(Or leave it in the scratchpad directory if that's session-local and
never touches the repo — either way, do not commit it.)

- [ ] **Step 6: No commit for workspace content**

`workspaces/` is git-ignored (confirmed in this repo's `.gitignore`), so
there is nothing to `git add`/commit for this task — the workspace exists
on disk for the user to open, exactly like any other workspace they'd
create themselves. Report the final file layout you created instead of a
commit SHA.

---

### Task 9: End-to-end verification

**Files:**
- None created/modified — verification only.

- [ ] **Step 1: Check for browser automation tooling**

Search your available tools for anything like "browser_navigate" /
"playwright". If available, use it for the steps below; if not, do them
via the same real-server/real-websocket/code-tracing approach used
throughout Tasks 1-8, and say so explicitly in your report.

- [ ] **Step 2: Full walkthrough**

Start the server, open the canvas page for an existing workspace (or the
new `vi-du-lm-studio` one). Confirm together, as one coherent page:
- The "DỊCH XƯỞNG" brand mark, palette header/hint, and per-item
  icon/description all render correctly.
- Dragging each of the 10 node types onto the canvas shows the correct
  icon-colored title-bar dot, the correct type-label row below the title
  bar (with ports visibly shifted down to make room), and an idle-state
  footer.
- Selecting a node shows the matching icon/type/title header in the
  inspector panel.
- Running a graph transitions each node's footer through
  running→done/error with a timestamp, without any longer changing the
  node's overall body color.
- The log console's count badge and empty-state message behave
  correctly, and messages are colored by event type.
- Switching language (VI/EN) updates the brand mark, palette text, node
  type labels (both on-canvas and in the inspector), and status words,
  everywhere at once.
- The full pytest suite still passes: `python -m pytest -q` from the
  repo root (expect 130 passed — this plan makes no backend changes, so
  this is a sanity check, not the primary verification for this plan).

- [ ] **Step 3: Report results**

No commit for this task. Write up exactly what you verified and how,
and be explicit about anything that genuinely required a real browser
and could not be confirmed in this environment.

---

## Self-Review Notes

- **Spec coverage:** §1 (icon/color table) → Task 2; §2 (custom node
  card draw geometry) → Task 2; §3 (run-status wiring) → Task 3; §4
  (brand mark) → Task 4; §5 (palette) → Tasks 4+5; §6 (inspector header)
  → Tasks 4+6; §7 (log console) → Task 7; §8 (example workspace) → Task
  8. Every spec section maps to a task. Out-of-scope items (preview line,
  palette footer stats, appName subtitle, click-to-add, backend changes)
  are correctly absent from every task.
- **Type consistency:** `NODE_TYPE_META`/`NODE_TYPE_META_FALLBACK`
  (Task 2) are referenced identically by name in Tasks 5 and 6.
  `nodeTypeLabel`/`nodeTypeDesc` (Task 1) are called with the same
  single-`type`-string signature everywhere they're used (Tasks 2, 5,
  6). `_runStatus`/`_runStatusAt` (Task 2) are set with the exact same
  field names in Task 3 and read with the same names in Task 2's own
  `onDrawForeground`. `RUN_STATUS_COLOR`/`RUN_STATUS_KEY` (Task 2) are
  also reused verbatim (as `LOG_MESSAGE_COLOR`, a separately-named but
  parallel table with the same hex values) in Task 7 — deliberately not
  shared as one cross-file constant, consistent with this project's
  existing convention of small, single-responsibility files over
  cross-file shared-constant modules (matching the plan's own File
  Structure decision to keep `nodegen.js` and `log_console.js` each
  self-contained).
- **Placeholder scan:** no TBD/TODO. Task 8's script has one deliberately
  flagged placeholder (illustrative slot indices) that the task's own
  text explicitly instructs the implementer to verify and correct against
  real source — not a plan gap, a designed verification step, matching
  this project's established "verify against real source, don't assume"
  discipline used throughout every prior plan.

---

Plan complete and saved to `docs/superpowers/plans/2026-09-09-node-visual-identity-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
