# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**OmniTranslate Studio** — a node-based visual workflow editor (ComfyUI-style
graph canvas, built on the vendored `litegraph.js`) for translating
long-form content — novels, manga, and video — chapter-by-chapter (or
scene-by-scene) with an LLM. Users wire up nodes — load a chapter, look up
glossary terms, call an LLM provider, extract new glossary terms, save
output — into a graph, save it per-workspace, and run it. Node metadata is
defined once in Python and the frontend renders node UI dynamically from it
(no per-node frontend code). The current node set (`server/nodes/`) is
text-first (novel translation); manga/video are supported by the same
graph-and-node architecture but don't yet have dedicated node types (e.g. no
OCR/image node for manga, no subtitle/audio node for video) — adding one
follows the same "just `@register_node` it" path described below.

## Running the app

```
run.bat
```

Creates/activates `.venv`, installs `requirements.txt`, opens a browser once
`/api/health` responds, then runs `uvicorn server.main:app --host 127.0.0.1
--port 8000` in the foreground (Ctrl+C stops it). Must be run from the repo
root — `uvicorn` needs the repo root on `sys.path` to import the `server`
package, and `workspaces/` is resolved relative to the repo root.

To run manually instead: `python -m uvicorn server.main:app --host 127.0.0.1 --port 8000`.

## Tests

```
pytest
```

`pytest.ini` sets `pythonpath = .` and `testpaths = tests`, so `pytest` from
the repo root just works — no package install needed. Run a single file with
`pytest tests/test_workspace.py`, a single test with
`pytest tests/test_workspace.py::test_create_and_list_workspace`.

There is no separate JS test suite or lint/build step; `web/` is served
as-is by FastAPI's `StaticFiles`.

## Architecture

### Backend: node system (`server/`)

- `server/node_registry.py` — `NodeBase` is the contract every node type
  implements: `INPUT_TYPES()` classmethod (declares required/optional inputs
  with type + default), `RETURN_TYPES`/`RETURN_NAMES`, `NEEDS_WORKSPACE` flag,
  and `execute(**kwargs) -> tuple`. `@register_node("Name")` adds a class to
  a module-level `_REGISTRY` dict keyed by that name — this is the single
  source of truth for what node types exist. `list_node_metadata()` (backing
  `GET /api/nodes`) introspects the registry and is exactly what the frontend
  uses to build the node palette and dynamic node UI — **adding a node class
  with `@register_node` is sufficient to make it appear in the UI**, no
  frontend changes needed.
- `server/nodes/translate.py` and `server/nodes/utility.py` — the actual node
  implementations (`Provider`, `Translate`, `LoadGlossary`, `ExtractGlossary`,
  `EvaluateAndFixChapters`, `LoadTextFile`, etc.). They're thin wrappers
  around `translation_core` functions; nodes handle workspace-path resolution
  and I/O, `translation_core` holds the actual logic. Both modules must stay
  imported in `server/main.py` (`# noqa: F401`) purely for their
  `@register_node` side effects — that's what populates the registry at
  startup.
- `server/executor.py` — `run_graph(nodes, links, on_event, workspace_name)`
  topologically sorts the graph (`GraphValidationError` on cycles/unknown
  refs), validates required inputs are satisfied by a literal or a link
  (`validate_required_inputs`), then executes each node in order, resolving
  each input either from the node's own `inputs` dict or from an upstream
  node's output (matched by `RETURN_NAMES`). If a node throws, its
  dependents are transitively marked `skipped` rather than executed.
  `on_event` streams `node_started`/`node_completed`/`node_error`/
  `run_finished` events — `_truncate_outputs_for_event` caps long strings and
  replaces non-JSON-serializable outputs (e.g. an `LLMProvider` instance)
  with `type(value).__name__` **only in the emitted event**, never
  `repr()`/`str()`, since a node output can carry a plaintext secret
  (`Provider`'s output holds `api_key`) and the event is broadcast to any
  connected client.
- `server/workspace.py` — a workspace is a directory under `workspaces/<name>/`
  containing `graph.json`, `config.json`, `agent.md`, `glossary.json`,
  `chapters.json`, `chapters/`, `output/`. Names are validated against a
  strict `[A-Za-z0-9_-]+` allowlist (`_is_valid_workspace_name`) to block
  path traversal — always go through `get_workspace_path()` rather than
  constructing paths by hand. `workspaces/` is gitignored (user data).
- `server/main.py` — FastAPI app. REST endpoints for workspace CRUD +
  `/api/nodes` + `/api/browse-directory` (backs the path-picker UI, restricted
  to directories only). `/ws/run/{workspace_name}` runs a graph: it checks
  the `Origin` header against an allowlist (WebSockets aren't covered by the
  browser's same-origin policy, so any open page could otherwise drive the
  local server into reading/writing arbitrary files) and runs `run_graph` on
  a background thread, relaying queued events to the client as they arrive.

### Backend: translation logic (`translation_core/`)

Framework-agnostic; `server/nodes/*` is the only consumer. Import from the
package root (`from translation_core import ...`), not submodules —
`translation_core/__init__.py` defines the public API deliberately (e.g.
`OpenAICompatibleProvider` is intentionally *not* re-exported; go through
`create_provider`/`ProviderConfig` instead).

- `providers/` — `LLMProvider` ABC (`base.py`) with one `complete(messages)`
  method; `OpenAICompatibleProvider` is the only implementation, calling a
  `/chat/completions`-shaped endpoint (works with LM Studio, OpenAI, etc.).
  `factory.create_provider(ProviderConfig)` is the only construction path.
  Error bodies are sanitized (`api_key` redacted, length-capped) before being
  wrapped in `ProviderError`.
- `translate.py` — `translate_chunk` builds the system/user messages
  (glossary entries appended to the system prompt) and calls the provider.
- `glossary.py` — `GlossaryEntry` dataclass + JSON load/save +
  `find_relevant_entries` (substring match of `term` in text — this is the
  full "RAG" in this codebase; see git history: a Chroma-backed RAG was
  deliberately replaced with this glossary/chapter-manifest design).
- `chapters.py` — `ChapterRecord` dataclass tracking each translated
  chapter's source/output paths + timestamp, used by `EvaluateAndFixChapters`
  to re-check the N most recent chapters after a glossary term changes.
- `agent_file.py` — trivial read/write of a workspace's `agent.md` (the
  system-prompt-like translation instructions, editable per-workspace).

`ExtractGlossary` (`server/nodes/translate.py`) is the most involved node: it
asks the LLM to propose glossary term candidates from a translated chunk,
detects conflicts against existing entries, asks the LLM to arbitrate
keep-old vs. use-new, and — only when the old→new string swap is unambiguous
(no substring overlap, occurrence counts match) — auto-corrects the just-
translated text in place; otherwise it surfaces a note for manual fixup.

### Frontend (`web/`)

Vanilla JS, no build step, no framework beyond the vendored `litegraph.js`
(`web/js/litegraph.js` — treat as third-party, do not hand-edit).

- `canvas_app.js` — entry point. Fetches `/api/nodes`, wires up the palette/
  inspector/minimap/log console, and drives graph execution over
  `/ws/run/{workspace}`, updating each node's `_runStatus` as events arrive.
- `nodegen.js` — `registerDynamicNodeTypes()` turns each node-metadata entry
  from `/api/nodes` into a `litegraph` node class at runtime (inputs/outputs,
  icon/color from a hardcoded `NODE_TYPE_META` lookup, a status-dot footer).
  `buildExecutionPayload()` is the inverse: reads live node state
  (`node.properties`, not `widgets_values` — properties are what
  `configure()` restores verbatim on reload) back into the
  `{nodes, links}` shape `run_graph` expects. **New node type added on the
  backend → it just works here**; only add to `NODE_TYPE_META` for a custom
  icon/color (falls back to a generic one otherwise).
- `workspace_tabs.js` — workspace open/create/switch/save, one tab per
  workspace, backed by the `/api/workspaces*` REST endpoints.
- `path_picker.js` — modal directory browser (no file picking) backing any
  input whose node metadata sets `"widget": "path"`, backed by
  `/api/browse-directory`.
- `i18n.js` — `t(key)` lookup + `setLang`; UI supports vi/en, switched live
  without a reload (re-renders palette/inspector/tabs in place).
- `inspector_panel.js`, `node_palette.js`, `minimap.js`, `log_console.js`,
  `batch_panel.js` — supporting panels; each owns one region of the UI and is
  initialized once from `canvas_app.js`'s `init()`.

### `templates/`

Tracked-in-git example workflow graphs (unlike `workspaces/`, which is user
data and gitignored). See `templates/README.md` for how to load one into a
workspace — there's no in-app JSON import yet, so it's a manual copy into
that workspace's `graph.json`.

## Conventions worth knowing

- User-facing strings inside translation logic (glossary conflict prompts,
  evaluation reports, the default `agent.md`) are in Vietnamese — this is
  intentional (source→Vietnamese is the primary translation direction this
  tool is built for), not an inconsistency to "fix."
- Adding a new node type requires no frontend changes: define the class in
  `server/nodes/`, decorate with `@register_node(...)`, and make sure its
  module is imported somewhere reachable from `server/main.py`.
- When touching anything under `server/workspace.py`, go through the
  existing name-validation path — never build a `workspaces/<name>/...` path
  by hand.
