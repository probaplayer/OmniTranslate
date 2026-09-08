# Canvas UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin `web/index.html`/`web/canvas.html` to match a provided
mockup's colors/fonts/layout, replace on-node litegraph widgets with a
right-side inspector panel for editing node properties, and add a log
console, a hand-drawn minimap, a batch-run panel (UI shell only), and a
VI/EN language toggle — with zero backend or `translation_core` changes.

**Architecture:** Each new piece of UI chrome is its own small JS module
(`inspector_panel.js`, `log_console.js`, `minimap.js`, `batch_panel.js`,
`i18n.js`) wired into the existing `canvas_app.js` lifecycle, following
the same pattern `node_palette.js` already uses (`init*(...)` called from
`canvas_app.js`'s `init()`). Node property editing moves from
`nodegen.js`'s on-node widgets to the inspector panel, both reading/
writing the same `node.properties` object litegraph already
serializes/restores — no change to save/load or execution payload
building.

**Tech Stack:** Vanilla JS (no framework, no build step — unchanged
project convention), litegraph.js (vendored, unchanged), Google Fonts
(Space Grotesk + IBM Plex Mono, loaded via `<link>`), `localStorage` for
language preference.

**Spec:** [docs/superpowers/specs/2026-09-08-canvas-ui-redesign-design.md](../specs/2026-09-08-canvas-ui-redesign-design.md)

## Global Constraints

- No changes to `server/` or `translation_core/` anywhere in this plan.
- Keep Sub-project C's 6 node types (`Provider`, `LoadAgentFile`,
  `SaveAgentFile`, `RAGQuery`, `SaveToRAG`, `Translate`) exactly as they
  are — this plan only changes how their properties are edited, not what
  properties they have.
- `node.properties` remains the single source of truth for a node's
  literal input values — `buildExecutionPayload()` in `nodegen.js`
  already reads from there and must not need to change because of this
  plan.
- No automated tests for this plan (frontend-only, matches the existing
  project convention) — every task ends with a manual browser-verification
  step instead.
- The batch-run panel is a UI shell only — its "Start" action must show a
  clear "not available yet" message, never pretend to run anything.
- No new REST/WebSocket endpoints — the single-node "Run this node"
  feature reuses the existing `/ws/run/{workspace}` endpoint with a
  smaller graph payload, nothing new on the backend.

---

## File Structure

```
web/
  css/style.css                (Task 1: new color/font tokens)
  index.html                     (Tasks 1, 2: fonts, i18n attributes)
  canvas.html                      (Tasks 1, 2, 3: fonts, i18n, new layout/containers)
  js/
    workspace_picker.js              (Task 2: use t() for messages)
    canvas_app.js                      (Tasks 2, 5, 6, 7, 8: i18n + wire new modules)
    nodegen.js                           (Task 4: remove on-node widgets)
    node_palette.js                        (unchanged)
    i18n.js                                  (Task 2: NEW)
    inspector_panel.js                         (Task 5: NEW)
    log_console.js                               (Task 6: NEW)
    minimap.js                                     (Task 7: NEW)
    batch_panel.js                                   (Task 8: NEW)
```

---

### Task 1: Color/font tokens

**Files:**
- Modify: `web/css/style.css`
- Modify: `web/index.html`
- Modify: `web/canvas.html`

**Interfaces:**
- Produces: CSS custom properties on `:root` — `--bg`, `--bg-elevated`,
  `--bg-surface`, `--bg-input`, `--bg-hover`, `--border`, `--border-soft`,
  `--text`, `--text-muted`, `--text-dim`, `--text-faint`, `--accent`,
  `--accent-hover`, `--accent-text`, `--danger`, `--success`,
  `--status-idle`, `--radius`, `--font-ui`, `--font-mono`. Every later
  task's CSS (Tasks 3, 5-8) uses these exact token names — do not rename
  any of them.

- [ ] **Step 1: Replace `web/css/style.css`'s `:root` block and the two
  places that hardcoded a color/font**

Replace:

```css
:root {
  --bg: #1e1f26;
  --bg-elevated: #262832;
  --bg-hover: #2f313d;
  --border: #3a3d4a;
  --text: #e8e8ec;
  --text-muted: #9a9cae;
  --accent: #6c8cff;
  --accent-hover: #86a0ff;
  --danger: #ff6b6b;
  --success: #4caf82;
  --radius: 8px;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}
```

with:

```css
:root {
  --bg: #101216;
  --bg-elevated: #14161b;
  --bg-surface: #1a1d23;
  --bg-input: #1c1f25;
  --bg-hover: #1e2229;
  --border: #2a2f37;
  --border-soft: #23272e;
  --text: #e9e7e2;
  --text-muted: #9aa1ab;
  --text-dim: #767d88;
  --text-faint: #6f7681;
  --accent: #d9a44c;
  --accent-hover: #efc57e;
  --accent-text: #16181d;
  --danger: #d97070;
  --success: #7fb98a;
  --status-idle: #6b7280;
  --radius: 8px;
  --font-ui: "Space Grotesk", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", "Consolas", monospace;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-ui);
}
```

Then, further down in the same file, change:

```css
.picker input {
  flex: 1;
  min-width: 140px;
  background: var(--bg);
```

to:

```css
.picker input {
  flex: 1;
  min-width: 140px;
  background: var(--bg-input);
```

and change:

```css
.picker button,
#toolbar button {
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: #10111a;
```

to:

```css
.picker button,
#toolbar button {
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: var(--accent-text);
```

Nothing else in `style.css` changes — every other rule already
references the token names above and picks up the new values
automatically.

- [ ] **Step 2: Add Google Fonts loading to `web/index.html`'s `<head>`**

Insert right after the existing `<link rel="stylesheet" href="/css/style.css" />` line:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

- [ ] **Step 3: Add the same Google Fonts loading to `web/canvas.html`'s `<head>`**

Insert right after the existing `<link rel="stylesheet" href="/css/litegraph.css" />` line (before `style.css`'s own link):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

- [ ] **Step 4: Manual verification**

Run: `python -m uvicorn server.main:app --reload`, open
`http://127.0.0.1:8000/` and `http://127.0.0.1:8000/canvas.html?workspace=<any-existing-workspace>`.

Expected: both pages now show a near-black background (`#101216`), gold
buttons (`#d9a44c`), and text rendered in Space Grotesk (check via
browser dev tools' computed font-family, or just note the font looks
different from the previous generic sans-serif). Existing functionality
(workspace list, node drag-and-drop, save/run) is unaffected — this task
only changes colors/fonts.

- [ ] **Step 5: Commit**

```bash
git add web/css/style.css web/index.html web/canvas.html
git commit -m "feat: reskin UI with mockup's color palette and fonts"
```

---

### Task 2: i18n (VI/EN) + retrofit existing text

**Files:**
- Create: `web/js/i18n.js`
- Modify: `web/index.html`
- Modify: `web/js/workspace_picker.js`
- Modify: `web/canvas.html`
- Modify: `web/js/canvas_app.js`

**Interfaces:**
- Produces: `t(key: string) -> string` (returns the translated string for
  the current language, or the key itself if missing); `setLang(lang:
  "vi" | "en") -> void` (persists to `localStorage` and re-applies);
  `applyTranslations() -> void` (walks `[data-i18n]`/
  `[data-i18n-placeholder]` elements and sets their text/placeholder).
  Tasks 5-8 call `t(key)` using keys already defined in this task's `STR`
  table — see the full key list in Step 1, it covers every string those
  later tasks need, so they don't add new keys.

- [ ] **Step 1: Create `web/js/i18n.js`**

```js
const STR = {
  vi: {
    pickerTitle: "Chọn workspace",
    createWorkspaceTitle: "Tạo workspace mới",
    namePlaceholder: "Tên workspace (vd: truyen-a)",
    sourceLangPlaceholder: "Ngôn ngữ nguồn (vd: ja)",
    targetLangPlaceholder: "Ngôn ngữ đích (vd: vi)",
    createButton: "Tạo",
    nameHint:
      "Tên workspace chỉ được chứa chữ cái, chữ số, dấu gạch ngang (-) và gạch dưới (_) — không có dấu cách hay ký tự đặc biệt.",
    loadWorkspacesError: "Không thể tải danh sách workspace — kiểm tra server có đang chạy không.",
    createWorkspaceGenericError: "Không tạo được workspace",
    createWorkspaceServerError: "Không tạo được workspace — kiểm tra server.",
    backToWorkspaces: "← Workspaces",
    runAllButton: "Chạy toàn bộ",
    saveButton: "Lưu",
    batchToggleButton: "Hàng loạt",
    statusLoadNodesError: "Lỗi tải danh sách node: ",
    statusLoadWorkspaceError: "Lỗi tải workspace: ",
    statusSaveError: "Lỗi lưu: ",
    statusSaved: "Đã lưu",
    statusWsError: "Lỗi kết nối WebSocket",
    statusRunFinished: "Hoàn tất",
    statusValidationError: "Lỗi: ",
    statusRuntimeError: "Lỗi thực thi: ",
    inspectorEmpty: "Chọn 1 node trên canvas để xem chi tiết.",
    nodeName: "Tên node",
    runNode: "Chạy node này",
    delete: "Xoá",
    logTitle: "Log chạy",
    clearLog: "Xoá log",
    logEmpty: "Chưa có gì.",
    batchTitle: "Chạy hàng loạt chương",
    batchFrom: "Từ chương",
    batchTo: "Đến chương",
    batchConcurrency: "Chạy song song",
    batchStart: "Bắt đầu",
    batchUnavailable: "Cần Sub-project A2 (Loop Group) — chưa khả dụng.",
  },
  en: {
    pickerTitle: "Select workspace",
    createWorkspaceTitle: "Create new workspace",
    namePlaceholder: "Workspace name (e.g. novel-a)",
    sourceLangPlaceholder: "Source language (e.g. ja)",
    targetLangPlaceholder: "Target language (e.g. vi)",
    createButton: "Create",
    nameHint:
      "Workspace name may only contain letters, digits, hyphen (-) and underscore (_) — no spaces or special characters.",
    loadWorkspacesError: "Could not load the workspace list — check that the server is running.",
    createWorkspaceGenericError: "Could not create workspace",
    createWorkspaceServerError: "Could not create workspace — check the server.",
    backToWorkspaces: "← Workspaces",
    runAllButton: "Run all",
    saveButton: "Save",
    batchToggleButton: "Batch",
    statusLoadNodesError: "Failed to load node list: ",
    statusLoadWorkspaceError: "Failed to load workspace: ",
    statusSaveError: "Save failed: ",
    statusSaved: "Saved",
    statusWsError: "WebSocket connection error",
    statusRunFinished: "Done",
    statusValidationError: "Error: ",
    statusRuntimeError: "Runtime error: ",
    inspectorEmpty: "Select a node on the canvas to inspect it.",
    nodeName: "Node name",
    runNode: "Run this node",
    delete: "Delete",
    logTitle: "Run log",
    clearLog: "Clear",
    logEmpty: "Nothing yet.",
    batchTitle: "Batch run chapters",
    batchFrom: "From chapter",
    batchTo: "To chapter",
    batchConcurrency: "Parallel runs",
    batchStart: "Start",
    batchUnavailable: "Requires Sub-project A2 (Loop Group) — not available yet.",
  },
};

function currentLang() {
  return localStorage.getItem("lang") || "vi";
}

function t(key) {
  const table = STR[currentLang()] || STR.vi;
  return table[key] || key;
}

function setLang(lang) {
  localStorage.setItem("lang", lang);
  applyTranslations();
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

applyTranslations();
```

Note: `applyTranslations()` is called directly at the bottom (not on a
`DOMContentLoaded` listener) because this script, like every other script
in this project, is loaded via a plain `<script>` tag placed near the end
of `<body>` — by the time it runs, every element above it in the HTML
already exists.

- [ ] **Step 2: Add `data-i18n`/`data-i18n-placeholder` attributes to `web/index.html`, and load `i18n.js` first**

Replace the `<body>` content with:

```html
<body>
  <main class="picker">
    <h1 data-i18n="pickerTitle">Chọn workspace</h1>
    <ul id="workspace-list" class="workspace-list"></ul>

    <h2 data-i18n="createWorkspaceTitle">Tạo workspace mới</h2>
    <form id="create-form">
      <!-- The hyphen in `pattern` is escaped so the character class stays
           valid when the browser compiles the pattern with the `v` flag: an
           unescaped trailing `-` fails to compile there, and a pattern that
           fails to compile is silently ignored entirely. Same character set
           as the backend's allowlist. -->
      <input
        id="new-name"
        data-i18n-placeholder="namePlaceholder"
        placeholder="Tên workspace (vd: truyen-a)"
        pattern="[A-Za-z0-9_\-]+"
        title="Chỉ dùng chữ cái, chữ số, dấu gạch ngang (-) và gạch dưới (_)"
        required
      />
      <input id="new-source-lang" data-i18n-placeholder="sourceLangPlaceholder" placeholder="Ngôn ngữ nguồn (vd: ja)" />
      <input id="new-target-lang" data-i18n-placeholder="targetLangPlaceholder" placeholder="Ngôn ngữ đích (vd: vi)" />
      <button type="submit" data-i18n="createButton">Tạo</button>
    </form>
    <p class="hint" data-i18n="nameHint">
      Tên workspace chỉ được chứa chữ cái, chữ số, dấu gạch ngang (-) và gạch
      dưới (_) — không có dấu cách hay ký tự đặc biệt.
    </p>
    <p id="picker-error" class="error"></p>
  </main>
  <script src="/js/i18n.js"></script>
  <script src="/js/workspace_picker.js"></script>
</body>
```

- [ ] **Step 3: Use `t()` for the 3 error messages in `web/js/workspace_picker.js`**

Change:

```js
  } catch (error) {
    const errorEl = document.getElementById("picker-error");
    errorEl.textContent = "Không thể tải danh sách workspace — kiểm tra server có đang chạy không.";
  }
```

to:

```js
  } catch (error) {
    const errorEl = document.getElementById("picker-error");
    errorEl.textContent = t("loadWorkspacesError");
  }
```

Change:

```js
        errorEl.textContent = body.detail || "Không tạo được workspace";
      } catch {
        errorEl.textContent = "Không tạo được workspace — kiểm tra server.";
```

to:

```js
        errorEl.textContent = body.detail || t("createWorkspaceGenericError");
      } catch {
        errorEl.textContent = t("createWorkspaceServerError");
```

Change the last `catch` block:

```js
  } catch (error) {
    errorEl.textContent = "Không tạo được workspace — kiểm tra server.";
  }
```

to:

```js
  } catch (error) {
    errorEl.textContent = t("createWorkspaceServerError");
  }
```

- [ ] **Step 4: Update `web/canvas.html`'s toolbar and script order**

Replace the `#toolbar` div and the closing script tags with:

```html
      <div id="toolbar">
        <a href="/index.html" data-i18n="backToWorkspaces">&larr; Workspaces</a>
        <button id="run-button" data-i18n="runAllButton">Run</button>
        <button id="save-button" data-i18n="saveButton">Save</button>
        <span id="status" class="status-info"></span>
        <span style="flex: 1;"></span>
        <button id="lang-vi-button">VI</button>
        <button id="lang-en-button">EN</button>
      </div>
```

and:

```html
  <script src="/js/i18n.js"></script>
  <script src="/js/litegraph.js"></script>
  <script src="/js/nodegen.js"></script>
  <script src="/js/node_palette.js"></script>
  <script src="/js/canvas_app.js"></script>
```

(`i18n.js` must load first so every later script can call `t()`
immediately.)

- [ ] **Step 5: Retrofit `web/js/canvas_app.js`'s status messages and wire the language buttons**

Change each of these lines:

```js
    setStatus(`Lỗi tải danh sách node: ${nodesResponse.status}`, "error");
```
→
```js
    setStatus(`${t("statusLoadNodesError")}${nodesResponse.status}`, "error");
```

```js
    setStatus(`Lỗi tải workspace: ${graphResponse.status}`, "error");
```
→
```js
    setStatus(`${t("statusLoadWorkspaceError")}${graphResponse.status}`, "error");
```

```js
    setStatus(`Lỗi lưu: ${response.status}`, "error");
```
→
```js
    setStatus(`${t("statusSaveError")}${response.status}`, "error");
```

```js
  setStatus("Đã lưu", "ok");
```
→
```js
  setStatus(t("statusSaved"), "ok");
```

```js
  ws.onerror = () => setStatus("Lỗi kết nối WebSocket", "error");
```
→
```js
  ws.onerror = () => setStatus(t("statusWsError"), "error");
```

```js
      setStatus("Hoàn tất", "ok");
```
→
```js
      setStatus(t("statusRunFinished"), "ok");
```

```js
      setStatus(`Lỗi: ${event.message}`, "error");
```
→
```js
      setStatus(`${t("statusValidationError")}${event.message}`, "error");
```

```js
      setStatus(`Lỗi thực thi: ${event.message}`, "error");
```
→
```js
      setStatus(`${t("statusRuntimeError")}${event.message}`, "error");
```

(The final generic `setStatus(\`${event.event}: node ${event.node_id}\`)`
line is left as-is — it's low-value debug text, not part of this task.)

Then, right after the existing two `addEventListener` lines at the bottom
of the file:

```js
document.getElementById("run-button").addEventListener("click", runGraph);
document.getElementById("save-button").addEventListener("click", saveGraph);
```

add:

```js
document.getElementById("lang-vi-button").addEventListener("click", () => setLang("vi"));
document.getElementById("lang-en-button").addEventListener("click", () => setLang("en"));
```

- [ ] **Step 6: Manual verification**

Reload `http://127.0.0.1:8000/` and the canvas page. Expected: all
Vietnamese text still shows correctly (default language). Click "EN" on
the canvas toolbar — every static label (toolbar buttons, back link)
switches to English. Reload the page — it stays in English (persisted via
`localStorage`). Navigate back to `/` — the picker page's text is also in
English now (same `localStorage` key). Click "VI" to switch back.

- [ ] **Step 7: Commit**

```bash
git add web/js/i18n.js web/index.html web/js/workspace_picker.js web/canvas.html web/js/canvas_app.js
git commit -m "feat: add VI/EN language toggle and retrofit existing UI text"
```

---

### Task 3: Layout restructure (inspector/log/minimap/batch containers)

**Files:**
- Modify: `web/canvas.html`

**Interfaces:**
- Produces: DOM containers `#inspector-panel` (aside, right column),
  `#log-console`/`#log-console-header`/`#log-console-body`/
  `#clear-log-button` (bottom of canvas column), `#minimap` (canvas
  element, absolutely positioned over the graph), `#batch-panel`/
  `#batch-from`/`#batch-to`/`#batch-concurrency`/`#batch-start-button`/
  `#batch-message` (hidden panel), `#batch-toggle-button` (toolbar). These
  are inert (no behavior) until Tasks 5-8 add their scripts — this task
  only adds structure/CSS.

- [ ] **Step 1: Replace `web/canvas.html`'s `<style>` block, body layout, and toolbar**

Replace the entire `<style>` block (the one starting with `body.canvas-page`)
with:

```html
  <style>
    body.canvas-page { max-width: none; margin: 0; height: 100vh; overflow: hidden; }

    #app-layout { display: flex; height: 100vh; }

    #node-palette {
      width: 212px;
      flex-shrink: 0;
      background: var(--bg-elevated);
      border-right: 1px solid var(--border-soft);
      overflow-y: auto;
      padding: 12px;
      box-sizing: border-box;
    }
    .palette-category {
      color: var(--text-faint);
      font-family: var(--font-mono);
      font-size: 0.7rem;
      letter-spacing: 0.05em;
      margin: 12px 0 4px;
      text-transform: uppercase;
    }
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

    #canvas-column { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    #toolbar {
      align-items: center;
      background: var(--bg-elevated);
      border-bottom: 1px solid var(--border-soft);
      display: flex;
      gap: 12px;
      padding: 8px 12px;
    }
    #toolbar a { color: var(--text-dim); text-decoration: none; }
    #toolbar a:hover { color: var(--text); }

    #canvas-area { position: relative; flex: 1; min-height: 0; }
    #graph-canvas { display: block; width: 100%; height: 100%; }

    #minimap {
      position: absolute;
      left: 14px;
      bottom: 14px;
      width: 176px;
      height: 112px;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 7px;
    }

    #log-console {
      border-top: 1px solid var(--border-soft);
      background: var(--bg-elevated);
      flex-shrink: 0;
    }
    #log-console-header {
      align-items: center;
      cursor: pointer;
      display: flex;
      gap: 8px;
      padding: 8px 12px;
    }
    #log-console-header span:first-child {
      color: var(--text-faint);
      font-family: var(--font-mono);
      font-size: 10px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    #log-console-body {
      max-height: 148px;
      overflow-y: auto;
      padding: 6px 0;
    }
    .log-entry {
      display: grid;
      grid-template-columns: 62px 100px 1fr;
      gap: 10px;
      padding: 3px 12px;
      font-family: var(--font-mono);
      font-size: 10.5px;
      line-height: 1.6;
    }
    .log-time { color: var(--text-faint); }

    #batch-panel {
      position: absolute;
      right: 14px;
      top: 14px;
      width: 268px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 9px;
      padding: 14px;
      box-sizing: border-box;
    }
    #batch-panel[hidden] { display: none; }
    #batch-panel label {
      color: var(--text-faint);
      display: block;
      font-size: 10px;
      letter-spacing: 0.1em;
      margin-bottom: 4px;
      text-transform: uppercase;
    }
    #batch-panel input {
      background: var(--bg-input);
      border: 1px solid var(--border);
      border-radius: 5px;
      color: var(--text);
      padding: 6px 8px;
      width: 100%;
      box-sizing: border-box;
      margin-bottom: 10px;
    }
    #batch-message {
      color: var(--text-muted);
      font-size: 11.5px;
      line-height: 1.5;
      margin-top: 8px;
    }

    #inspector-panel {
      width: 344px;
      flex-shrink: 0;
      background: var(--bg-elevated);
      border-left: 1px solid var(--border-soft);
      overflow-y: auto;
      padding: 14px 16px;
      box-sizing: border-box;
    }
    .inspector-empty {
      color: var(--text-dim);
      font-size: 12.5px;
      line-height: 1.6;
    }
    .inspector-label {
      color: var(--text-faint);
      font-size: 10px;
      letter-spacing: 0.12em;
      margin: 14px 0 5px;
      text-transform: uppercase;
    }
    .inspector-input {
      width: 100%;
      background: var(--bg-input);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
      padding: 8px 10px;
      font-size: 12.5px;
      box-sizing: border-box;
      font-family: inherit;
    }
    .inspector-input:focus { outline: none; border-color: var(--accent); }
    .inspector-actions {
      display: flex;
      gap: 7px;
      margin-top: 20px;
      padding-top: 14px;
      border-top: 1px solid var(--border-soft);
    }
    .inspector-actions button {
      flex: 1;
      background: var(--bg-input);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 12px;
      padding: 9px;
      border-radius: 6px;
      cursor: pointer;
    }
    .inspector-actions button:hover { border-color: var(--accent); color: var(--accent); }
    .inspector-delete:hover { border-color: var(--danger) !important; color: var(--danger) !important; }
  </style>
```

Then replace the `<body>` content with:

```html
<body class="canvas-page">
  <div id="app-layout">
    <aside id="node-palette"></aside>
    <div id="canvas-column">
      <div id="toolbar">
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
        <canvas id="graph-canvas"></canvas>
        <canvas id="minimap" width="176" height="112"></canvas>
        <div id="batch-panel" hidden>
          <div data-i18n="batchTitle" style="font-size: 12px; font-weight: 600; margin-bottom: 10px;">Chạy hàng loạt chương</div>
          <label data-i18n="batchFrom">Từ chương</label>
          <input id="batch-from" />
          <label data-i18n="batchTo">Đến chương</label>
          <input id="batch-to" />
          <label data-i18n="batchConcurrency">Chạy song song</label>
          <input id="batch-concurrency" type="number" min="1" max="6" value="1" />
          <button id="batch-start-button" data-i18n="batchStart" style="width: 100%; background: var(--accent); border: none; color: var(--accent-text); font-weight: 600; padding: 9px; border-radius: 6px; cursor: pointer;">Bắt đầu</button>
          <div id="batch-message"></div>
        </div>
      </div>
      <div id="log-console">
        <div id="log-console-header">
          <span data-i18n="logTitle">Log chạy</span>
          <span style="flex: 1;"></span>
          <button id="clear-log-button" data-i18n="clearLog" style="background: transparent; border: none; color: var(--text-faint); font-size: 11px; cursor: pointer;">Xoá log</button>
        </div>
        <div id="log-console-body"></div>
      </div>
    </div>
    <aside id="inspector-panel"></aside>
  </div>
  <script src="/js/i18n.js"></script>
  <script src="/js/litegraph.js"></script>
  <script src="/js/nodegen.js"></script>
  <script src="/js/node_palette.js"></script>
  <script src="/js/canvas_app.js"></script>
</body>
```

(Script tags for `inspector_panel.js`, `log_console.js`, `minimap.js`,
`batch_panel.js` are added by Tasks 5-8 respectively, alongside the code
that actually uses each container.)

- [ ] **Step 2: Update `canvas_app.js`'s canvas-resize logic for the new `#canvas-area` wrapper**

The existing `syncCanvasSize()` reads `canvasEl.clientWidth`/
`clientHeight` — since `#graph-canvas` is now inside `#canvas-area`
(`position: relative`) instead of directly in the flex column, and CSS
already gives it `width: 100%; height: 100%`, no code change is needed
here — verify this in the manual check below rather than editing
anything speculatively.

- [ ] **Step 3: Manual verification**

Reload the canvas page. Expected: a visible (but empty/non-functional)
panel on the right (~344px wide), an empty area at the bottom for the log
console header (showing "Log chạy" / "Xoá log", still non-functional), a
small dark rectangle in the bottom-left of the canvas (the minimap
container, blank for now), and clicking "Hàng loạt" in the toolbar does
nothing yet (no click handler until Task 8) — none of this is broken,
it's the expected mid-plan state. Confirm the graph canvas itself still
renders correctly, still resizes to fill its area, and dragging a node
from the palette still works (this task must not regress Task 1/2's
functionality or the pre-existing drag-and-drop).

- [ ] **Step 4: Commit**

```bash
git add web/canvas.html
git commit -m "feat: restructure canvas layout with inspector/log/minimap/batch containers"
```

---

### Task 4: Remove on-node widgets from `nodegen.js`

**Files:**
- Modify: `web/js/nodegen.js`

**Interfaces:**
- Consumes: nothing new.
- Produces: `registerDynamicNodeTypes` no longer creates litegraph
  widgets — `node.properties` is still initialized identically (same
  keys, same `config.default || ""` values), so `buildExecutionPayload`
  (unchanged) and Task 5's inspector panel (which reads/writes
  `node.properties` directly) both keep working against the exact same
  data shape as before.

- [ ] **Step 1: Remove the `addWidget` call**

Change:

```js
      this.properties = {};
      for (const [inputName, spec] of Object.entries(allInputs)) {
        const inputType = spec[0];
        const config = spec[1] || {};
        this.addInput(inputName, inputType);
        this.properties[inputName] = config.default || "";
        if (inputType === "STRING") {
          this.addWidget("text", inputName, this.properties[inputName], (value) => {
            this.properties[inputName] = value;
          });
        }
      }
```

to:

```js
      this.properties = {};
      for (const [inputName, spec] of Object.entries(allInputs)) {
        const inputType = spec[0];
        const config = spec[1] || {};
        this.addInput(inputName, inputType);
        this.properties[inputName] = config.default || "";
      }
```

(`linkedInputNames` and `buildExecutionPayload` below are untouched —
they already read from `node.properties`/`node.inputs`, never from
widgets.)

- [ ] **Step 2: Manual verification**

Reload the canvas page, drag a `LoadTextFile` node onto the canvas.
Expected: the node now shows only its title and input/output ports — no
text field on its body (this is intentional at this point in the plan;
Task 5 adds the replacement editing UI in the inspector panel). Confirm
dragging nodes, connecting wires, saving, and reloading the graph still
all work (properties round-trip through `graph.serialize()`/`configure()`
exactly as before, since that mechanism didn't change).

- [ ] **Step 3: Commit**

```bash
git add web/js/nodegen.js
git commit -m "feat: remove on-node widgets, node.properties remains the source of truth"
```

---

### Task 5: Inspector panel

**Files:**
- Create: `web/js/inspector_panel.js`
- Modify: `web/canvas.html`
- Modify: `web/js/canvas_app.js`

**Interfaces:**
- Consumes: `linkedInputNames(node)` and `buildExecutionPayload(graph)`
  from `nodegen.js` (Task 4, unchanged signatures); `t(key)` from `i18n.js`
  (Task 2); the node metadata list already fetched in `canvas_app.js`'s
  `init()` (`GET /api/nodes`'s response, an array of `{type, category,
  input_types, return_types, return_names}` objects — see
  `server/node_registry.py`'s `list_node_metadata()` for the exact shape,
  unchanged by this plan).
- Produces: `initInspectorPanel(nodeMetadataList, graph, canvas,
  workspaceName)` — called once from `canvas_app.js`'s `init()`, after
  `registerDynamicNodeTypes(nodeMetadataList)`.

- [ ] **Step 1: Create `web/js/inspector_panel.js`**

```js
let inspectorNodeMetadata = {};
let inspectorGraph = null;
let inspectorWorkspaceName = null;
let inspectorSelectedNode = null;

function initInspectorPanel(nodeMetadataList, graph, canvas, workspaceName) {
  inspectorGraph = graph;
  inspectorWorkspaceName = workspaceName;
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

  appendInspectorLabel(panel, t("nodeName"));
  const titleInput = document.createElement("input");
  titleInput.className = "inspector-input";
  titleInput.value = node.title || node.constructor.nodeType;
  titleInput.addEventListener("change", () => {
    node.title = titleInput.value;
    inspectorGraph.setDirtyCanvas(true, true);
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
    inspectorGraph.remove(node);
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
  const payload = buildExecutionPayload(inspectorGraph);
  const nodeId = String(node.id);
  const isolatedNodes = payload.nodes.filter((n) => n.id === nodeId);

  const ws = new WebSocket(
    `ws://${location.host}/ws/run/${encodeURIComponent(inspectorWorkspaceName)}`
  );
  ws.onopen = () => {
    ws.send(JSON.stringify({ graph: { nodes: isolatedNodes, links: [] } }));
  };
  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (typeof appendLogEntry === "function") appendLogEntry(event);
    if (event.event === "run_finished") ws.close();
  };
}
```

(`appendLogEntry` is guarded with a `typeof` check because Task 6, which
defines it, hasn't run yet at this point in the plan — this keeps Task 5
independently testable without a forward dependency on Task 6. Once
Task 6 lands, `appendLogEntry` exists globally and the guard is simply
always true.)

- [ ] **Step 2: Add the script tag to `web/canvas.html`**

Add this line right before the existing `<script src="/js/canvas_app.js"></script>`:

```html
  <script src="/js/inspector_panel.js"></script>
```

- [ ] **Step 3: Call `initInspectorPanel` from `web/js/canvas_app.js`'s `init()`**

Change:

```js
  const nodeMetadataList = await nodesResponse.json();
  registerDynamicNodeTypes(nodeMetadataList);
  initNodePalette(nodeMetadataList, graph, canvas, canvasEl);
```

to:

```js
  const nodeMetadataList = await nodesResponse.json();
  registerDynamicNodeTypes(nodeMetadataList);
  initNodePalette(nodeMetadataList, graph, canvas, canvasEl);
  initInspectorPanel(nodeMetadataList, graph, canvas, workspaceName);
```

- [ ] **Step 4: Manual verification**

Reload the canvas page. Expected: the right panel shows
"Chọn 1 node trên canvas để xem chi tiết." when nothing is selected.
Drag a `LoadTextFile` node onto the canvas and click it — the panel now
shows a "Tên node" field and a "path" field (its only STRING input),
both pre-filled with the current values. Type a new value into "path",
click elsewhere on the canvas to deselect, click the node again — the
value you typed is still there (confirms it's reading from
`node.properties`, not losing state). Click "Save" (toolbar), reload the
page, select the node again — the value survived a save/reload round
trip. Click "Chạy node này" with a `path` pointing at a real file on
disk — confirm (via Network tab or just that nothing errors) a
WebSocket connection opens and closes; a `Translate` node's "Chạy node
này" (whose `provider` input is never a literal STRING field, so it's
never editable here) should show a validation error in the browser
console or via the websocket response, since it has no literal value for
`provider` when run in isolation — this is the known, accepted
limitation from the spec, not a bug.

- [ ] **Step 5: Commit**

```bash
git add web/js/inspector_panel.js web/canvas.html web/js/canvas_app.js
git commit -m "feat: add right-side inspector panel for node property editing"
```

---

### Task 6: Log console

**Files:**
- Create: `web/js/log_console.js`
- Modify: `web/canvas.html`
- Modify: `web/js/canvas_app.js`

**Interfaces:**
- Consumes: `t(key)` from `i18n.js` (Task 2).
- Produces: `appendLogEntry(event: {event: string, node_id?: string,
  message?: string}) -> void` — called once per websocket event received.
  Task 5's `runSingleNode` already calls this (guarded), so once this
  task lands, single-node runs log too, with no further changes needed
  there.

- [ ] **Step 1: Create `web/js/log_console.js`**

```js
let logOpen = true;

function appendLogEntry(event) {
  const body = document.getElementById("log-console-body");
  if (!body) return;

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

  row.appendChild(timeEl);
  row.appendChild(sourceEl);
  row.appendChild(messageEl);
  body.appendChild(row);
  body.scrollTop = body.scrollHeight;
}

function clearLog() {
  const body = document.getElementById("log-console-body");
  if (body) body.innerHTML = "";
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
}
```

- [ ] **Step 2: Add the script tag to `web/canvas.html`**

Add this line right before the `<script src="/js/inspector_panel.js"></script>` line added in Task 5:

```html
  <script src="/js/log_console.js"></script>
```

- [ ] **Step 3: Call `initLogConsole()` and feed run events into `appendLogEntry` from `web/js/canvas_app.js`**

In `init()`, add a call after `initInspectorPanel(...)`:

```js
  initInspectorPanel(nodeMetadataList, graph, canvas, workspaceName);
  initLogConsole();
```

In `runGraph()`'s `ws.onmessage` handler, add `appendLogEntry(event);` as
the very first line inside the callback:

```js
  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    appendLogEntry(event);
    if (event.event === "run_finished") {
```

(Everything else in that handler is unchanged — this just adds logging
alongside the existing status/color-update behavior.)

- [ ] **Step 4: Manual verification**

Reload the canvas page, build a small graph (e.g. `LoadTextFile` →
`SaveTextFile` with real file paths), click "Run". Expected: the log
console at the bottom fills with timestamped lines for
`node_started`/`node_completed`/`run_finished` as the run progresses.
Click the log header to collapse/expand it — confirm it toggles. Click
"Xoá log" — confirm it clears without also toggling collapse (the
`stopPropagation()` call is what prevents that).

- [ ] **Step 5: Commit**

```bash
git add web/js/log_console.js web/canvas.html web/js/canvas_app.js
git commit -m "feat: add collapsible run log console"
```

---

### Task 7: Minimap

**Files:**
- Create: `web/js/minimap.js`
- Modify: `web/canvas.html`
- Modify: `web/js/canvas_app.js`

**Interfaces:**
- Consumes: `graph._nodes` (litegraph's internal node array — each
  element has `.pos: [x, y]` and `.size: [w, h]`); `canvas.ds.offset`/
  `canvas.ds.scale` (litegraph's pan/zoom state, already used elsewhere
  in this codebase — see `node_palette.js`'s use of
  `canvas.convertCanvasToOffset`).
- Produces: `initMinimap(graph, canvas, canvasEl) -> void`.

- [ ] **Step 1: Create `web/js/minimap.js`**

```js
function initMinimap(graph, canvas, canvasEl) {
  const minimapEl = document.getElementById("minimap");
  if (!minimapEl) return;
  const ctx = minimapEl.getContext("2d");

  function computeWorldBounds() {
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
    const w = minimapEl.width;
    const h = minimapEl.height;
    ctx.clearRect(0, 0, w, h);

    const bounds = computeWorldBounds();
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
    const rect = minimapEl.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    const bounds = computeWorldBounds();
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

Note on `canvas.ds.offset`'s sign: litegraph draws with
`ctx.translate(offset[0], offset[1])` after scaling, so a node at world
position `pos[0]` appears on screen at `(pos[0] + offset[0]) * scale`
(see `DragAndScale.prototype.convertOffsetToCanvas` in
`web/js/litegraph.js` if you need to double check this). The minimap
math above uses `-canvas.ds.offset[0]` to convert the current *screen
top-left* back into *world* coordinates for drawing the viewport
rectangle, and the click handler's assignment is the inverse of that.
Verify this visually in Step 3 below rather than trusting the formula
blindly — if the viewport rectangle or click-to-navigate ends up
inverted or offset, the sign or the pad math is the first thing to
recheck.

- [ ] **Step 2: Add the script tag to `web/canvas.html`**

Add this line right before the `<script src="/js/log_console.js"></script>` line added in Task 6:

```html
  <script src="/js/minimap.js"></script>
```

- [ ] **Step 3: Call `initMinimap` from `web/js/canvas_app.js`**

In `init()`, add after `initLogConsole();`:

```js
  initLogConsole();
  initMinimap(graph, canvas, canvasEl);
```

- [ ] **Step 4: Manual verification**

Reload the canvas page, add 2-3 nodes spread across the canvas (drag them
apart). Expected: the minimap in the bottom-left shows small rectangles
roughly matching their relative positions, and a gold-bordered rectangle
showing your current viewport. Pan/zoom the main canvas (drag empty space
to pan, scroll to zoom) — the gold rectangle in the minimap should move/
resize to track the real viewport within ~1 second (the 200ms redraw
interval). Click somewhere else in the minimap — the main canvas should
jump so that point is roughly centered. If the viewport rectangle or the
click-to-navigate is visibly wrong (inverted direction, way off-center),
fix the sign/offset math per the note in Step 1 and re-verify.

- [ ] **Step 5: Commit**

```bash
git add web/js/minimap.js web/canvas.html web/js/canvas_app.js
git commit -m "feat: add hand-drawn minimap with click-to-navigate"
```

---

### Task 8: Batch panel (UI shell)

**Files:**
- Create: `web/js/batch_panel.js`
- Modify: `web/js/canvas_app.js`

**Interfaces:**
- Consumes: `t(key)` from `i18n.js` (Task 2, including `batchUnavailable`,
  already defined there).
- Produces: `initBatchPanel() -> void`.

- [ ] **Step 1: Create `web/js/batch_panel.js`**

```js
function initBatchPanel() {
  const toggleButton = document.getElementById("batch-toggle-button");
  const panel = document.getElementById("batch-panel");
  const startButton = document.getElementById("batch-start-button");
  const messageEl = document.getElementById("batch-message");

  toggleButton.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
  });

  startButton.addEventListener("click", () => {
    messageEl.textContent = t("batchUnavailable");
  });
}
```

- [ ] **Step 2: Add the script tag to `web/canvas.html`**

Add this line right before the `<script src="/js/minimap.js"></script>` line added in Task 7:

```html
  <script src="/js/batch_panel.js"></script>
```

- [ ] **Step 3: Call `initBatchPanel()` from `web/js/canvas_app.js`**

In `init()`, add after `initMinimap(graph, canvas, canvasEl);`:

```js
  initMinimap(graph, canvas, canvasEl);
  initBatchPanel();
```

- [ ] **Step 4: Manual verification**

Reload the canvas page. Click "Hàng loạt" in the toolbar — the batch
panel (top-right) toggles open/closed. With it open, fill in some values
and click "Bắt đầu" — expected: a clear message appears in the panel
("Cần Sub-project A2 (Loop Group) — chưa khả dụng.") and nothing else
happens (no network request, no fake progress). Toggle the language to
English and click "Bắt đầu" again — the message is now in English.

- [ ] **Step 5: Commit**

```bash
git add web/js/batch_panel.js web/js/canvas_app.js
git commit -m "feat: add batch-run panel UI shell (not yet functional)"
```

---

### Task 9: End-to-end verification

**Files:**
- None created/modified — this task is verification only.

- [ ] **Step 1: Check for browser automation tooling**

Search your available tools for anything like "browser_navigate" /
"playwright". If available, use it for the steps below; if not, do them
manually via `curl`/reading files and clearly say so in your report
(consistent with how earlier tasks in this project have handled missing
browser tooling).

- [ ] **Step 2: Start the server and open the app**

Run `python -m uvicorn server.main:app --host 127.0.0.1 --port 8000` (or
`run.bat`). Open `http://127.0.0.1:8000/`.

- [ ] **Step 3: Full workflow walkthrough**

- Confirm the picker page shows the new dark/gold theme and correct
  Vietnamese text.
- Create a new workspace (or open an existing one).
- On the canvas: drag a `LoadTextFile` and a `SaveTextFile` node from the
  palette, connect them, and using the **inspector panel** (not any
  on-node widget — there shouldn't be one), set real file paths for both.
- Click a node to confirm the inspector panel updates; click empty canvas
  to confirm it shows the "no selection" message again.
- Save the graph, reload the page, confirm the graph and the property
  values you set persisted.
- Click "Run" (Chạy toàn bộ) — confirm the log console fills with events,
  node colors update on the canvas as before, and the destination file
  gets written with the source file's content.
- Add a third node, drag it far away, confirm the minimap shows all 3 and
  the viewport rectangle tracks panning/zooming; click in the minimap to
  jump the view.
- Open the batch panel, click "Bắt đầu", confirm the "not available"
  message appears.
- Click "EN", confirm the toolbar/inspector/log/batch text all switch to
  English; reload and confirm it stays in English; click "VI" to switch
  back.

- [ ] **Step 4: Report results**

No commit for this task. Write up what you did and observed — if using a
real browser, include screenshots or DOM snapshots where useful; if using
the curl/manual fallback, describe exactly what you checked and what you
could not verify (e.g. actual drag-and-drop mechanics, which need a real
browser) so the gap is explicit rather than silently assumed.

---

## Self-Review Notes

- **Spec coverage:** Token/font reskin (spec §1) → Task 1; inspector
  panel + widget removal (spec §2) → Tasks 4-5; log console (spec §3) →
  Task 6; minimap (spec §4) → Task 7; batch panel shell (spec §5) →
  Task 8; VI/EN toggle (spec §6) → Task 2; single-node run (spec §7) →
  part of Task 5; new 3-column layout (spec §8) → Task 3. Every spec
  section maps to a task. Out-of-scope items (backend changes, real
  batch execution, merging node types, on-node preview chips, template
  system) are correctly absent from every task.
- **Type consistency:** `t(key)`/`setLang`/`applyTranslations` (Task 2)
  are used identically in Tasks 5, 6, 8. `initInspectorPanel`/
  `initLogConsole`/`initMinimap`/`initBatchPanel` (Tasks 5-8) are each
  called exactly once from `canvas_app.js`'s `init()`, in the order they
  were added, matching how `initNodePalette` already works. `node.properties`
  and `linkedInputNames`/`buildExecutionPayload` (Task 4, unchanged) are
  read the same way in Task 5's inspector panel as they already are in
  `nodegen.js` itself.
- **Placeholder scan:** no TBD/TODO; every step has runnable code or an
  explicit manual-verification checklist, consistent with this project's
  established no-automated-frontend-tests convention.

---

Plan complete and saved to `docs/superpowers/plans/2026-09-08-canvas-ui-redesign-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
