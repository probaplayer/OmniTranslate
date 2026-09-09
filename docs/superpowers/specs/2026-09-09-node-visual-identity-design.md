# Node Visual Identity & LM Studio Example Workflow — Design

## Bối cảnh

Sub-project Canvas UI Redesign (merged) reskinned the app's chrome (colors,
fonts, inspector panel, log console, minimap, batch panel) to match a
provided mockup, but three things from the mockup were explicitly out of
scope at the time: a per-node-type icon/color identity system (both in the
node palette and on the canvas itself), the top bar's brand mark, and a
ready-to-run example workflow. This spec covers all three, following up
directly on that work.

The user confirmed, via a short brainstorming exchange in this same
session:
- "sc-interp" (a term with no match anywhere in the mockup's actual source)
  meant the mockup's icon+color badge shown per node type.
- Node cards on the canvas should get the **full custom-drawn treatment**
  matching the mockup — not just a colored title, but a colored
  identifier, a type-label row, and a status footer — verified technically
  feasible by reading litegraph.js's actual rendering internals (not
  assumed).
- The mockup's "preview text" row inside each node card is explicitly cut
  from scope: our 10 node types are too heterogeneous for one generic
  "preview" field to make sense (Translate has no single obvious text
  property; Provider's is a URL; LoadTextFile's is a path).

## Mục tiêu

1. Give every node type a consistent icon + color identity, shown in the
   node palette, on the node's canvas card, and in the inspector panel's
   header — matching the mockup's visual language.
2. Add a status footer (colored dot + localized status text + meta) to
   each node card, replacing the current all-or-nothing `node.bgcolor`
   status coloring with something closer to the mockup's dedicated footer
   row.
3. Restyle the top bar with the "DỊCH XƯỞNG" brand mark, and the node
   palette with a header + hint text, matching the mockup.
4. Finish the log console to match the mockup exactly: a running count
   badge next to the title, the (currently defined but unused)
   empty-state message, and per-event-type colored message text.
5. Ship a ready-to-run example workspace demonstrating a full LM
   Studio-based translation pipeline, so a user can open the app and see
   a working example immediately.

## Kiến trúc tổng quan

```
web/
  js/
    nodegen.js          (Modify: per-type icon/color/label table, custom
                          onDrawForeground, slot_start_y, footer geometry)
    node_palette.js      (Modify: header/hint text, icon+color badge per item)
    inspector_panel.js    (Modify: icon+type+title header block)
    log_console.js         (Modify: count badge, empty state, colored
                             message text)
    canvas_app.js            (Modify: brand mark data hookup, run-status
                               field instead of raw node.bgcolor, node
                               width bump)
    i18n.js                    (Modify: new keys — brand, appName,
                                 palette header/hint, per-type labels/
                                 descriptions, status words)
  canvas.html                    (Modify: brand mark markup, palette
                                   header/hint containers, log count-badge
                                   container)
  index.html                       (unchanged)
workspaces/
  <new example workspace>            (Create: config.json, graph.json,
                                       agent.md, chapters/chuong-1.txt —
                                       git-ignored runtime data, not
                                       committed to the repo, exactly like
                                       every other workspace)
```

No backend or `translation_core` changes. No new node types. No new
REST/WebSocket endpoints.

## Thành phần chi tiết

### 1. Node type → icon/color/label table

A single source of truth, `NODE_TYPE_META`, defined once in `nodegen.js`
as a plain global object (`const NODE_TYPE_META = {...}`, keyed by node
type name) — consistent with this project's existing no-build-step,
global-script convention (`t()`, `appendLogEntry`, `buildExecutionPayload`
are all globals other files call directly by name, not passed as
parameters). `node_palette.js` and `inspector_panel.js` reference
`NODE_TYPE_META[meta.type]` directly, since `nodegen.js` already loads
before both of them in `canvas.html`'s script order.

| Node | Icon | Color |
|---|---|---|
| LoadTextFile | `▤` | `#7ea6c9` |
| SaveTextFile | `⤓` | `#9b8fc4` |
| TextPreview | `◐` | `#8d949e` |
| Note | `✎` | `#8d949e` |
| Provider | `✦` | `#7fb98a` |
| LoadAgentFile | `◈` | `#d9a44c` |
| SaveAgentFile | `◆` | `#d9a44c` |
| RAGQuery | `◎` | `#c98a7e` |
| SaveToRAG | `◉` | `#c98a7e` |
| Translate | `⇄` | `#7fb98a` |

Localized type labels and palette descriptions (new i18n keys,
`nodeTypeLabels`/`nodeTypeDescs`, nested objects keyed by node type name,
one per language):

| Node | VI label | VI mô tả | EN label | EN description |
|---|---|---|---|---|
| LoadTextFile | ĐỌC FILE | Đọc file text | LOAD FILE | Read a text file |
| SaveTextFile | GHI FILE | Ghi file text | SAVE FILE | Write a text file |
| TextPreview | XEM TRƯỚC | Xem trước nội dung | PREVIEW | Preview text content |
| Note | GHI CHÚ | Ghi chú tự do | NOTE | Freeform note |
| Provider | NGUỒN MODEL | Kết nối API/LM Studio | MODEL SOURCE | API or LM Studio connection |
| LoadAgentFile | ĐỌC AGENT | Đọc file agent | LOAD AGENT | Read the agent file |
| SaveAgentFile | GHI AGENT | Ghi file agent | SAVE AGENT | Write the agent file |
| RAGQuery | TRUY VẤN RAG | Truy vấn RAG | RAG QUERY | Query the RAG store |
| SaveToRAG | LƯU RAG | Lưu vào RAG | SAVE TO RAG | Save into the RAG store |
| Translate | DỊCH | Dịch văn bản | TRANSLATE | Translate text |

A node type not present in this table (there shouldn't be one, since it
covers every currently-registered type, but the code must not crash if a
future type is added and forgotten here) falls back to: icon `●`, color
`--text-faint` (`#767d88`), label = the raw type string, no description.

### 2. Custom node card rendering (`nodegen.js`)

Verified against the actual vendored `web/js/litegraph.js`, not assumed:

- **Identifier dot:** `this.boxcolor = meta.color` set once in the
  `DynamicNode` constructor. This is litegraph's existing small circle in
  the title bar (`ctx.fillStyle = node.boxcolor || ...` at the title-box
  draw step) — no custom drawing needed, and it does not touch the title
  bar's background fill or text color, so legibility is unaffected by
  this change.
- **Type-label row:** drawn via `onDrawForeground(ctx)`, in the space
  directly below the title bar and above the ports. Made possible by
  `DynamicNode.slot_start_y = HEADER_HEIGHT` (constant, `20`) — a real,
  documented litegraph class-level property that both
  `computeSize()` (`size[1] = (this.constructor.slot_start_y || 0) + rows
  * NODE_SLOT_HEIGHT`) and `getConnectionPos()` (`out[1] = this.pos[1] +
  (slot_number + 0.7) * NODE_SLOT_HEIGHT + (this.constructor.slot_start_y
  || 0)`) read — meaning both the node's auto-computed height and every
  input/output port's actual render position AND connection-hit-testing
  position shift consistently. Since `computeSize()` is invoked
  automatically by `addInput`/`addOutput` (already called during
  `DynamicNode`'s constructor), setting `slot_start_y` on the class before
  any instance is constructed is sufficient — no manual height patching
  needed for this row.
  - Content: `${icon} ${typeLabel}` (icon glyph + uppercase type label),
    drawn in the type's own color (not the muted text-faint color used
    elsewhere — this row's whole purpose is the type-color cue), at
    `10px "IBM Plex Mono"` (canvas 2D can't reference CSS custom
    properties, so the font stack is the literal string, matching
    `--font-mono`'s value), left-aligned with an 8px left margin,
    vertically centered within `[0, HEADER_HEIGHT]`.
- **Status footer row:** drawn via the same `onDrawForeground(ctx)`, at
  the bottom `FOOTER_HEIGHT` (constant, `22`) pixels of the node
  (`y` from `this.size[1] - FOOTER_HEIGHT` to `this.size[1]`). Since
  `computeSize()` does not know about this footer, the `DynamicNode`
  constructor must grow the auto-computed height by it explicitly, once,
  after the input/output loop finishes: `this.size[1] += FOOTER_HEIGHT;`.
  - Content: a subtle top separator line (`ctx.strokeStyle =
    "rgba(255,255,255,0.06)"`, full width), then a small filled circle
    (status color, see below) at the left, then the localized status word
    next to it, then (right-aligned) a meta string.
  - **Status color/text mapping** (new i18n keys `stIdle`/`stRunning`/
    `stDone`/`stError`, matching the mockup's exact Vietnamese wording
    "Chờ"/"Đang chạy"/"Xong"/"Lỗi"):
    | Status | Dot color | VI | EN |
    |---|---|---|---|
    | idle (default, before any run) | `--status-idle` (`#6b7280`) | Chờ | Idle |
    | running (`node_started`) | `--accent` (`#d9a44c`) | Đang chạy | Running |
    | done (`node_completed`) | `--success` (`#7fb98a`) | Xong | Done |
    | error (`node_error`) | `--danger` (`#d97070`) | Lỗi | Error |
  - **Meta string:** for `done`/`error`, the wall-clock time the status
    was last set (`HH:MM:SS`, reusing the exact formatting helper already
    written for `log_console.js`'s row timestamps — extract it to a
    shared small helper or duplicate the four-line snippet, whichever
    keeps `log_console.js` and `nodegen.js` each self-contained per the
    project's existing file-per-responsibility convention; duplicating
    four lines is preferred here over introducing a new shared-utility
    file for one helper). For `idle`/`running`, no meta text.

- **Run-status storage:** a new plain instance field,
  `this._runStatus = "idle"`, initialized in the `DynamicNode`
  constructor and updated by `canvas_app.js`'s websocket handler (see
  below) — deliberately NOT part of `node.properties` (which
  `buildExecutionPayload()` sends verbatim as literal node inputs to the
  backend; adding an untracked key there would corrupt real translation
  calls). Before relying on this being safe from
  `graph.serialize()`/`save_graph`, the implementer must read
  `LGraphNode.prototype.serialize` in the actual vendored
  `litegraph.js` (already located during this spec's own research at
  line ~2627) and confirm it only serializes a fixed, named set of
  fields (`id`, `type`, `pos`, `size`, `flags`, `order`, `mode`,
  `inputs`, `outputs`, `title`, `properties`, `widgets_values`) — never a
  `for...in` sweep over arbitrary instance properties — so a leading
  `_`-prefixed field is never picked up. This is a concrete, checkable
  fact, not an assumption to carry forward blindly.

- **Node width:** `LiteGraph.NODE_WIDTH` bumped from litegraph's default
  `140` to `200` in `canvas_app.js`'s existing palette-setup block
  (alongside the `NODE_DEFAULT_BGCOLOR`/etc. assignments already there),
  giving the new header/footer text rows enough horizontal room. This is
  a global minimum-width change (via `computeSize()`'s `Math.max(size[0],
  LiteGraph.NODE_WIDTH)`), affecting all nodes uniformly — consistent
  with the rest of this app's already-uniform node styling.

### 3. `canvas_app.js`: wiring run-status instead of raw bgcolor

Replace the current `colorForEvent`-driven `node.bgcolor` assignment
(used by both `runGraph`'s and — after this change, still only
`runGraph`'s — websocket handler; `inspector_panel.js`'s `runSingleNode`
already goes through the same handler pattern independently and is
unaffected in this pass) with:

```js
const node = graph.getNodeById(Number(event.node_id));
if (node) {
  if (event.event === "node_started") node._runStatus = "running";
  else if (event.event === "node_completed") node._runStatus = "done";
  else node._runStatus = "error";
  node._runStatusAt = Date.now();
  graph.setDirtyCanvas(true, true);
}
```

`colorForEvent` and the direct `node.bgcolor = ...` assignment are
removed — the footer row (drawn per-node inside `onDrawForeground`, which
already has access to `this._runStatus`/`this._runStatusAt`) is now the
only place run status is visually represented, replacing the previous
whole-node-background tint. `node.bgcolor` reverts to being left alone
(defaulting to `LiteGraph.NODE_DEFAULT_BGCOLOR`, already set to the dark
surface color from the prior plan's I4 fix), which is consistent with the
mockup's actual look — node bodies stay a uniform dark surface, with
status conveyed only through the footer, not a full background tint.

### 4. Top bar brand mark (`canvas.html` + `i18n.js`)

Add, as the first child of `#toolbar`, before the existing "← Workspaces"
link:

```html
<div style="display: flex; align-items: baseline; gap: 9px; margin-right: 8px;">
  <span style="font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--accent);" data-i18n="brand">DỊCH XƯỞNG</span>
</div>
```

New i18n keys: `brand` (VI: "DỊCH XƯỞNG", EN: "DICH XUONG" — matching the
mockup's own EN fallback exactly, since it's a proper-noun brand mark not
a translated phrase). The mockup's full `appName` subtitle ("Workflow
dịch truyện") is not added — the toolbar here has real functional buttons
competing for horizontal space (unlike the mockup's dedicated header row)
and the brand mark alone is enough to satisfy this task's request; adding
a second subtitle span is a trivial follow-up if wanted later, not
included now to avoid crowding.

### 5. Node palette (`canvas.html` CSS + `node_palette.js` + `i18n.js`)

- Add a header and hint text above the existing category/item list,
  matching the mockup's wording: new i18n keys `palette` ("Thư viện
  node" / "Node library") and `paletteHint` ("Kéo vào canvas hoặc bấm để
  thêm." / "Drag onto the canvas, or click to add."). Rendered as two
  `<div>`s inserted by `initNodePalette` before the category loop begins
  (matching the mockup's exact copy — note this hint also documents a
  click-to-add affordance the palette does NOT currently implement; since
  adding click-to-add is out of scope for this pass, the hint text is
  trimmed to just "Kéo vào canvas để thêm." / "Drag onto the canvas to
  add." — an intentional, minor wording deviation from the mockup to stay
  truthful about current functionality).
- Each palette item gets a small colored icon glyph (from
  `NODE_TYPE_META`) prepended, plus the localized description text
  beneath the type name (from `nodeTypeDescs`), replacing the current
  bare `item.textContent = meta.type`. New DOM structure per item:
  ```html
  <div class="palette-item" draggable="true">
    <span class="palette-item-icon" style="color: <type color>">▤</span>
    <div class="palette-item-body">
      <div class="palette-item-name">LoadTextFile</div>
      <div class="palette-item-desc">Đọc file text</div>
    </div>
  </div>
  ```
  New CSS rules in `canvas.html`'s existing `<style>` block:
  `.palette-item { display: flex; gap: 8px; align-items: flex-start; }`,
  `.palette-item-icon { font-size: 14px; flex-shrink: 0; width: 16px;
  text-align: center; }`, `.palette-item-desc { font-size: 10.5px; color:
  var(--text-faint); margin-top: 2px; }` (the existing `.palette-item`
  rule's padding/border/etc. stays; only `display`/`gap`/`align-items`
  are added to it).
- The footer stats block (node count / tokens / cost) from the mockup is
  **not** added — token/cost tracking doesn't exist anywhere in this
  project's backend (no per-run token accounting), and fabricating a
  fake "0" placeholder for a stat nobody can compute yet would be
  actively misleading. Out of scope, matching the project's established
  discipline of not building UI for data the backend can't produce.

### 6. Inspector panel header (`inspector_panel.js` + `canvas.html` CSS)

`renderInspector()`, right before the existing "Tên node" label/title
input block, gains a header matching the mockup's layout:

```html
<div class="inspector-header">
  <span class="inspector-header-icon" style="color: <type color>">✦</span>
  <div>
    <div class="inspector-header-type" style="color: <type color>">MODEL SOURCE</div>
    <div class="inspector-header-title"><!-- current node.title, read-only display here; the existing editable title input below is unchanged --></div>
  </div>
</div>
```

New CSS: `.inspector-header { display: flex; gap: 9px; align-items:
center; padding-bottom: 12px; margin-bottom: 4px; border-bottom: 1px
solid var(--border-soft); }`, `.inspector-header-icon { font-size: 18px;
}`, `.inspector-header-type { font-family: var(--font-mono); font-size:
10px; letter-spacing: 0.1em; text-transform: uppercase; }`,
`.inspector-header-title { font-size: 13px; font-weight: 600; margin-top:
2px; }`. This header is purely informational (type + current title
display) — the existing editable "Tên node" input immediately below it
is unchanged and remains the only way to rename the node, avoiding a
confusing two-places-to-edit-the-same-thing UI.

### 7. Log console (`log_console.js` + `canvas.html`)

Three changes, matching the mockup exactly:

- **Count badge:** a new `<span id="log-count-badge">` inserted into
  `#log-console-header` (in `canvas.html`) between the title and the
  spacer, styled `font-family: var(--font-mono); font-size: 9.5px;
  background: var(--bg-input); color: var(--text-faint); border-radius:
  8px; padding: 1px 6px;`. `appendLogEntry` and `clearLog` (in
  `log_console.js`) both update its `textContent` to the current number
  of `.log-entry` children in `#log-console-body` after their respective
  DOM mutation.
- **Empty state:** `initLogConsole()` renders the existing (currently
  unused) `logEmpty` i18n key into `#log-console-body` on load, and both
  `appendLogEntry` (remove it, if present, before appending the real
  row) and `clearLog` (re-render it after clearing) keep it in sync —
  matching the mockup's own logic of showing the empty message exactly
  when the log has zero entries.
- **Colored message text:** `appendLogEntry`'s `messageEl` gets a color
  based on `event.event`, reusing the same status-color mapping as the
  node footer (§2): `node_started` → `--accent`, `node_completed` →
  `--success`, `node_error`/`validation_error`/`runtime_error` →
  `--danger`, `run_finished` → `--success`, anything else → the existing
  default text color (no inline style).

### 8. Example workspace: LM Studio translation pipeline

A new workspace, name `vi-du-lm-studio` (passes the existing
`^[A-Za-z0-9_-]+$` name-validation allowlist), created via the app's
existing `POST /api/workspaces` endpoint (so it goes through the exact
same `create_workspace()` code path — and therefore the exact same
`config.json`/directory layout — as any workspace a real user creates;
this spec does not hand-craft workspace directory structure by hand).

After creation, three files are overwritten/added to seed a working
example:

- `workspaces/vi-du-lm-studio/chapters/chuong-1.txt` — a short (3-5
  paragraph) sample chapter of Chinese web-novel-style text (public-
  domain-style placeholder prose, not copied from any real copyrighted
  novel), used as the input to `LoadTextFile`.
- `workspaces/vi-du-lm-studio/agent.md` — replacing the default seeded
  file, with a short, concrete translation-instructions document (target
  language Vietnamese, tone guidance, an example glossary entry format)
  that plausibly matches what `Translate`'s `agent_instructions` input
  expects (per `translation_core.translate_chunk`'s existing contract —
  no format change to that contract, just realistic example content).
- `workspaces/vi-du-lm-studio/graph.json` — the actual wired pipeline:
  `LoadTextFile → Provider → Translate ← LoadAgentFile`, `Translate ←
  RAGQuery ← LoadTextFile's own text` (RAGQuery's `text` input wired from
  `LoadTextFile`'s output, so the query text matches what's being
  translated), `Translate → SaveTextFile`. Node literal properties:
  - `LoadTextFile.path` = the absolute path to `chuong-1.txt` above.
  - `Provider.base_url` = `http://localhost:1234/v1` (LM Studio's default
    local server URL), `Provider.api_key` = `""` (LM Studio doesn't
    require one), `Provider.model` = `local-model` (LM Studio accepts
    any non-empty string as the model identifier when only one model is
    loaded; documented as such in a `Note` node placed near `Provider` on
    the canvas explaining to swap in the exact loaded model's name if LM
    Studio requires it).
  - `RAGQuery.top_k` = `"3"` (default, fine on an empty/fresh RAG index —
    `RAGStore.query` on an empty ChromaDB collection returns an empty
    list, not an error; confirmed by reading `translation_core/rag/
    store.py`, not assumed).
  - `SaveTextFile.path` = `workspaces/vi-du-lm-studio/output/chuong-1-vi.txt`.

  **Build method:** hand-authoring this JSON directly is explicitly
  disallowed for this task — litegraph's serialized node/link shapes
  (confirmed by reading `LGraphNode.prototype.serialize`/`configure` and
  `LLink.prototype.serialize`/`configure` in the vendored `litegraph.js`
  during this spec's own research) are intricate enough that a
  hand-typed mistake could silently corrupt the file or crash on load.
  Instead: write a one-off Node.js script (scratch file, not committed —
  save it under the project's scratchpad convention or delete it after
  use) that:
  1. `const { LiteGraph, LGraph } = require("<path>/web/js/litegraph.js")`
     — confirmed exported via the file's own `if (typeof exports !=
     "undefined")` block; this loads and runs the real library under
     plain Node with no DOM/canvas dependency, since graph
     construction/serialization touches no rendering code.
  2. Fetch `/api/nodes` from a running local instance of this app (`python
     -m uvicorn server.main:app`) to get the real node metadata list —
     the same data the browser uses.
  3. Set `global.LiteGraph = LiteGraph;` then `require("<path>/web/js/
     nodegen.js")` (which references a bare `LiteGraph` identifier,
     resolved via Node's implicit global lookup — the implementer must
     confirm this actually works when run, not just assume it does) to
     register the exact same dynamic node classes the browser would.
  4. `const graph = new LGraph();`, then `LiteGraph.createNode(...)` for
     each of the six nodes, set `.pos`, set `.properties[...]` literal
     values, `graph.add(node)`, and `node_a.connect(output_slot_index,
     node_b, input_slot_index)` for each wire (using the real
     `LGraphNode.prototype.connect` method, not hand-built link objects).
  5. `require("fs").writeFileSync(<path>, JSON.stringify(graph
     .serialize(), null, 2))` to `workspaces/vi-du-lm-studio/graph.json`.
  6. Verify by actually opening the workspace through the running
     server's `GET /api/workspaces/vi-du-lm-studio` endpoint (or loading
     it in the app if a browser tool is available) and confirming it
     parses and the graph looks structurally right (six nodes, four
     links, positions non-overlapping).

## Data flow

Unchanged from the merged Canvas UI Redesign plan — this spec only
changes *how nodes are drawn* and *how the palette/inspector/log/toolbar
present themselves*, plus adds one new workspace's worth of static
content. No change to `buildExecutionPayload()`, the `/ws/run/{workspace}`
protocol, or any backend code.

## Error handling

- A node type missing from `NODE_TYPE_META` falls back to a neutral
  icon/color rather than crashing (see §1).
- The example workspace's `Provider.model` value is a placeholder the
  user must adjust to their actual loaded LM Studio model if it isn't
  called `local-model` — documented via an on-canvas `Note` node, not
  silently assumed correct.
- Everything else follows the existing project convention: no automated
  frontend tests, manual/live-server verification per change, explicit
  reporting of anything that couldn't be confirmed without a real
  browser.

## Testing

No automated tests (frontend-only, matches this project's established
convention). Manual verification per component: node cards render with
correct icon/color/footer (traced via code + the same kind of Node.js
numeric/logic verification already used successfully for the minimap and
ancestor-closure work in the prior plan, since no browser tool exists in
this environment); palette/inspector/log console changes verified via
DOM structure inspection and curl where a live server suffices; the
example workspace verified by actually running its pipeline end-to-end
over a real `/ws/run/vi-du-lm-studio` websocket connection (this part
does NOT require a browser — it's the same kind of real-backend,
real-websocket verification already used successfully throughout the
prior plan) — though it will only fully complete if LM Studio is
actually running locally; if it isn't, the implementer should confirm
the graph loads and validates (reaches the `Provider`/`Translate` step)
rather than requiring an actual successful LLM call, and note this
explicitly in their report.

## Ngoài phạm vi

- The mockup's per-node content preview line (see Bối cảnh — explicitly
  cut).
- The mockup's palette footer stats (node count/tokens/cost) — no backend
  data to back it.
- The mockup's `appName` toolbar subtitle.
- Click-to-add from the palette (only drag-and-drop, matching current
  behavior).
- Any change to `buildExecutionPayload`, the websocket protocol, or any
  backend/`translation_core` code.
- A general "import template" feature — the example workspace is a real,
  immediately-usable workspace, not a template-loading mechanism (that
  remains Sub-project A2's job, as decided earlier in this project).

## Cấu trúc thư mục dự kiến

(See Kiến trúc tổng quan above — no new files beyond the one example
workspace's runtime data, which is git-ignored like every other
workspace.)
