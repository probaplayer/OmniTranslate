# Node-Graph Engine (A1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the ComfyUI-style node-graph engine core — Python backend
executor + workspace manager + REST/WebSocket API, and a litegraph.js web UI
— running real (non-AI) utility nodes end-to-end.

**Architecture:** FastAPI backend serves a static, buildless web frontend
(litegraph.js) and exposes REST endpoints for workspace/node-registry CRUD
plus a WebSocket endpoint that streams per-node execution events from a
synchronous graph executor run in a background thread.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, pytest + httpx (backend
tests); vanilla JS + litegraph.js, no frontend build step.

**Spec:** [docs/superpowers/specs/2026-08-28-node-graph-engine-design.md](../specs/2026-08-28-node-graph-engine-design.md)
(sections: Kiến trúc tổng quan, Thành phần chi tiết #1-#4, Data flow, Error
handling, Testing — Loop Group/#5 and Template system/#6 are A2, out of
scope here)

## Global Constraints

- Python 3.11+ only; no other backend runtime.
- No frontend build step — plain HTML/CSS/JS served as static files, no
  React/webpack/npm bundling at runtime (npm is only used once, offline of
  the app itself, to fetch the vendored litegraph.js library).
- Storage is filesystem-based under `workspaces/`; no database.
- No caching of node results between runs in A1 (explicitly deferred).
- No auth/multi-user — single local user via `run.bat`.
- No Loop Group, no template system, no real AI/RAG nodes in this plan
  (A2/B/C/D scope).

---

## File Structure

```
MCPToolTranslaterNovel/
  run.bat
  requirements.txt
  pytest.ini
  .gitignore
  server/
    __init__.py
    main.py              # FastAPI app: static mount, REST routes, websocket
    executor.py           # topo sort + run_graph (sync)
    node_registry.py      # NodeBase + register_node/get_node_class/list_node_metadata
    workspace.py           # filesystem workspace CRUD
    nodes/
      __init__.py
      utility.py           # LoadTextFile, SaveTextFile, TextPreview, Note
  web/
    index.html             # workspace picker screen
    canvas.html             # litegraph canvas screen
    js/
      workspace_picker.js
      nodegen.js             # dynamic LiteGraph node type factory + payload builder
      canvas_app.js           # wires canvas.html: load graph, Run button, websocket
      litegraph.js             # vendored (npm) — not hand-written
    css/
      style.css
      litegraph.css            # vendored (npm) — not hand-written
    vendor/                    # npm scratch dir used only to fetch litegraph.js, gitignored
  tests/
    __init__.py
    test_node_registry.py
    test_executor.py
    test_workspace.py
    test_api.py
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.gitignore`
- Create: `server/__init__.py`
- Create: `server/main.py`
- Create: `web/index.html`
- Create: `tests/__init__.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: FastAPI app instance `server.main.app`, importable and runnable
  via `uvicorn server.main:app`.

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
pytest==8.3.3
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
workspaces/
web/vendor/
```

- [ ] **Step 4: Create `server/__init__.py` (empty) and `tests/__init__.py` (empty)**

- [ ] **Step 5: Write the failing test for the health endpoint**

`tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from server.main import app


def test_health_check_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_health_check_returns_ok -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server.main'`)

- [ ] **Step 7: Create minimal `server/main.py`**

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
```

- [ ] **Step 8: Create placeholder `web/index.html` (needed for StaticFiles mount to serve something at `/`)**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>Node Translator</title>
</head>
<body>
  <p>Workspace picker loads here (Task 8).</p>
</body>
</html>
```

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_health_check_returns_ok -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add requirements.txt pytest.ini .gitignore server/__init__.py server/main.py web/index.html tests/__init__.py tests/test_api.py
git commit -m "chore: scaffold FastAPI app with health check"
```

---

### Task 2: Node registry

**Files:**
- Create: `server/node_registry.py`
- Test: `tests/test_node_registry.py`

**Interfaces:**
- Produces:
  - `class NodeBase` with class attrs `CATEGORY: str`, `RETURN_TYPES: tuple`,
    `RETURN_NAMES: tuple`, classmethod `INPUT_TYPES() -> dict`, instance
    method `execute(self, **kwargs) -> tuple`.
  - `register_node(name: str)` — class decorator, raises `ValueError` on
    duplicate name.
  - `get_node_class(name: str) -> type[NodeBase]` — raises `KeyError` if
    unknown.
  - `list_node_metadata() -> list[dict]` — each dict has keys `type`,
    `category`, `input_types`, `return_types`, `return_names`.

- [ ] **Step 1: Write the failing tests**

`tests/test_node_registry.py`:

```python
import pytest

from server.node_registry import (
    NodeBase,
    get_node_class,
    list_node_metadata,
    register_node,
)


def test_register_and_get_node_class():
    @register_node("TestNodeA")
    class TestNodeA(NodeBase):
        CATEGORY = "Test"
        RETURN_TYPES = ("STRING",)
        RETURN_NAMES = ("out",)

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("STRING", {"default": ""})}}

        def execute(self, value):
            return (value,)

    assert get_node_class("TestNodeA") is TestNodeA


def test_register_duplicate_name_raises():
    @register_node("TestNodeB")
    class TestNodeB(NodeBase):
        pass

    with pytest.raises(ValueError):
        @register_node("TestNodeB")
        class TestNodeBAgain(NodeBase):
            pass


def test_get_unknown_node_class_raises():
    with pytest.raises(KeyError):
        get_node_class("DoesNotExist")


def test_list_node_metadata_includes_registered_node():
    @register_node("TestNodeC")
    class TestNodeC(NodeBase):
        CATEGORY = "Test"
        RETURN_TYPES = ("STRING",)
        RETURN_NAMES = ("out",)

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("STRING", {"default": "x"})}}

        def execute(self, value):
            return (value,)

    metadata = list_node_metadata()
    entry = next(m for m in metadata if m["type"] == "TestNodeC")
    assert entry["category"] == "Test"
    assert entry["return_types"] == ["STRING"]
    assert entry["return_names"] == ["out"]
    assert entry["input_types"]["required"]["value"][0] == "STRING"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_node_registry.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server.node_registry'`)

- [ ] **Step 3: Implement `server/node_registry.py`**

```python
from typing import Any


class NodeBase:
    CATEGORY = "Uncategorized"
    RETURN_TYPES: tuple = ()
    RETURN_NAMES: tuple = ()

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {"required": {}, "optional": {}}

    def execute(self, **kwargs) -> tuple:
        raise NotImplementedError


_REGISTRY: dict[str, type[NodeBase]] = {}


def register_node(name: str):
    def decorator(node_cls: type[NodeBase]):
        if name in _REGISTRY:
            raise ValueError(f"Node type '{name}' already registered")
        _REGISTRY[name] = node_cls
        return node_cls

    return decorator


def get_node_class(name: str) -> type[NodeBase]:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown node type: {name}")
    return _REGISTRY[name]


def list_node_metadata() -> list[dict[str, Any]]:
    result = []
    for name, cls in _REGISTRY.items():
        return_names = list(cls.RETURN_NAMES) or list(cls.RETURN_TYPES)
        result.append(
            {
                "type": name,
                "category": cls.CATEGORY,
                "input_types": cls.INPUT_TYPES(),
                "return_types": list(cls.RETURN_TYPES),
                "return_names": return_names,
            }
        )
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_node_registry.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add server/node_registry.py tests/test_node_registry.py
git commit -m "feat: add node registry with register/get/list_metadata"
```

---

### Task 3: Utility nodes

**Files:**
- Create: `server/nodes/__init__.py`
- Create: `server/nodes/utility.py`
- Test: `tests/test_utility_nodes.py`

**Interfaces:**
- Consumes: `NodeBase`, `register_node` from `server.node_registry` (Task 2).
- Produces: registered node types `"LoadTextFile"`, `"SaveTextFile"`,
  `"TextPreview"`, `"Note"`, each with `.execute(**kwargs) -> tuple` per the
  signatures below — later tasks (executor, API) call these only through
  `get_node_class(name)().execute(**kwargs)`, never import the classes
  directly.

- [ ] **Step 1: Write the failing tests**

`tests/test_utility_nodes.py`:

```python
from server.node_registry import get_node_class
from server.nodes import utility  # noqa: F401  (triggers registration)


def test_load_text_file_reads_content(tmp_path):
    file_path = tmp_path / "chapter1.txt"
    file_path.write_text("hello novel", encoding="utf-8")

    node = get_node_class("LoadTextFile")()
    result = node.execute(path=str(file_path))

    assert result == ("hello novel",)


def test_save_text_file_creates_parent_dirs_and_writes(tmp_path):
    file_path = tmp_path / "out" / "chapter1.txt"

    node = get_node_class("SaveTextFile")()
    result = node.execute(text="translated text", path=str(file_path))

    assert result == ()
    assert file_path.read_text(encoding="utf-8") == "translated text"


def test_text_preview_does_not_raise():
    node = get_node_class("TextPreview")()
    assert node.execute(text="anything") == ()


def test_note_does_not_raise():
    node = get_node_class("Note")()
    assert node.execute(text="a note") == ()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_utility_nodes.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server.nodes'`)

- [ ] **Step 3: Create `server/nodes/__init__.py` (empty)**

- [ ] **Step 4: Implement `server/nodes/utility.py`**

```python
from pathlib import Path

from server.node_registry import NodeBase, register_node


@register_node("LoadTextFile")
class LoadTextFile(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"path": ("STRING", {"default": ""})}}

    def execute(self, path: str) -> tuple:
        content = Path(path).read_text(encoding="utf-8")
        return (content,)


@register_node("SaveTextFile")
class SaveTextFile(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": ""}),
                "path": ("STRING", {"default": ""}),
            }
        }

    def execute(self, text: str, path: str) -> tuple:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return ()


@register_node("TextPreview")
class TextPreview(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, text: str) -> tuple:
        return ()


@register_node("Note")
class Note(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, text: str) -> tuple:
        return ()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_utility_nodes.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add server/nodes/__init__.py server/nodes/utility.py tests/test_utility_nodes.py
git commit -m "feat: add LoadTextFile/SaveTextFile/TextPreview/Note utility nodes"
```

---

### Task 4: Graph executor

**Files:**
- Create: `server/executor.py`
- Test: `tests/test_executor.py`

**Interfaces:**
- Consumes: `get_node_class` from `server.node_registry` (Task 2); real
  registered nodes from `server.nodes.utility` (Task 3) for the integration
  test; the graph payload shape:
  ```python
  nodes = [{"id": "1", "type": "LoadTextFile", "inputs": {"path": "..."}}]
  links = [{"from_node": "1", "from_output": "text", "to_node": "2", "to_input": "text"}]
  ```
- Produces:
  - `class GraphValidationError(Exception)`
  - `topological_order(nodes, links) -> list[str]` — raises
    `GraphValidationError` on cycle.
  - `validate_required_inputs(nodes, link_by_target) -> None` — raises
    `GraphValidationError` on missing required input.
  - `run_graph(nodes, links, on_event=None) -> dict[str, tuple]` — returns
    `{node_id: output_tuple}`; calls `on_event(event_dict)` for each of
    `node_started`, `node_completed`, `node_error`, `run_finished`, where
    `event_dict["event"]` is one of those four strings and always includes
    `"node_id"` (absent only for `run_finished`).

- [ ] **Step 1: Write the failing tests**

`tests/test_executor.py`:

```python
import pytest

from server.executor import GraphValidationError, run_graph, topological_order
from server.node_registry import NodeBase, register_node
from server.nodes import utility  # noqa: F401


@register_node("_TestAdd")
class _TestAdd(NodeBase):
    CATEGORY = "Test"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("out",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("STRING", {"default": ""})}}

    def execute(self, value):
        return (value + "!",)


@register_node("_TestFail")
class _TestFail(NodeBase):
    CATEGORY = "Test"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("out",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("STRING", {"default": ""})}}

    def execute(self, value):
        raise RuntimeError("boom")


def test_topological_order_simple_chain():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}},
             {"id": "2", "type": "_TestAdd", "inputs": {"value": "b"}}]
    links = [{"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"}]
    assert topological_order(nodes, links) == ["1", "2"]


def test_topological_order_detects_cycle():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {}},
             {"id": "2", "type": "_TestAdd", "inputs": {}}]
    links = [
        {"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"},
        {"from_node": "2", "from_output": "out", "to_node": "1", "to_input": "value"},
    ]
    with pytest.raises(GraphValidationError):
        topological_order(nodes, links)


def test_run_graph_missing_required_input_raises():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {}}]
    with pytest.raises(GraphValidationError):
        run_graph(nodes, [])


def test_run_graph_chains_output_to_input():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}},
             {"id": "2", "type": "_TestAdd", "inputs": {"value": "unused"}}]
    links = [{"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"}]

    outputs = run_graph(nodes, links)

    assert outputs["1"] == ("a!",)
    assert outputs["2"] == ("a!!",)


def test_run_graph_error_skips_downstream_but_not_independent_branch():
    nodes = [
        {"id": "1", "type": "_TestFail", "inputs": {"value": "a"}},
        {"id": "2", "type": "_TestAdd", "inputs": {"value": "unused"}},
        {"id": "3", "type": "_TestAdd", "inputs": {"value": "independent"}},
    ]
    links = [{"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"}]

    events = []
    outputs = run_graph(nodes, links, on_event=events.append)

    assert outputs["3"] == ("independent!",)
    error_events = [e for e in events if e["event"] == "node_error"]
    assert {e["node_id"] for e in error_events} == {"1", "2"}
    assert any(e["event"] == "run_finished" for e in events)


def test_run_graph_writes_file_via_real_utility_nodes(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("raw chapter", encoding="utf-8")
    dst = tmp_path / "out.txt"

    nodes = [
        {"id": "1", "type": "LoadTextFile", "inputs": {"path": str(src)}},
        {"id": "2", "type": "SaveTextFile", "inputs": {"path": str(dst)}},
    ]
    links = [{"from_node": "1", "from_output": "text", "to_node": "2", "to_input": "text"}]

    run_graph(nodes, links)

    assert dst.read_text(encoding="utf-8") == "raw chapter"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_executor.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server.executor'`)

- [ ] **Step 3: Implement `server/executor.py`**

```python
from collections import deque

from server.node_registry import get_node_class


class GraphValidationError(Exception):
    pass


def _build_dependency_map(nodes, links):
    dependents = {n["id"]: [] for n in nodes}
    dependency_count = {n["id"]: 0 for n in nodes}
    link_by_target = {}
    for link in links:
        dependents[link["from_node"]].append(link["to_node"])
        dependency_count[link["to_node"]] += 1
        link_by_target[(link["to_node"], link["to_input"])] = (
            link["from_node"],
            link["from_output"],
        )
    return dependents, dependency_count, link_by_target


def topological_order(nodes, links) -> list:
    dependents, dependency_count, _ = _build_dependency_map(nodes, links)
    remaining = dict(dependency_count)
    queue = deque(node_id for node_id, count in remaining.items() if count == 0)
    order = []
    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for dependent_id in dependents[node_id]:
            remaining[dependent_id] -= 1
            if remaining[dependent_id] == 0:
                queue.append(dependent_id)
    if len(order) != len(nodes):
        raise GraphValidationError("Graph contains a cycle")
    return order


def validate_required_inputs(nodes, link_by_target) -> None:
    for node in nodes:
        node_cls = get_node_class(node["type"])
        required = node_cls.INPUT_TYPES().get("required", {})
        for input_name in required:
            has_literal = input_name in node.get("inputs", {})
            has_link = (node["id"], input_name) in link_by_target
            if not has_literal and not has_link:
                raise GraphValidationError(
                    f"Node {node['id']} ({node['type']}) missing required "
                    f"input '{input_name}'"
                )


def run_graph(nodes, links, on_event=None) -> dict:
    def emit(event):
        if on_event:
            on_event(event)

    dependents, _, link_by_target = _build_dependency_map(nodes, links)
    order = topological_order(nodes, links)
    validate_required_inputs(nodes, link_by_target)

    node_by_id = {n["id"]: n for n in nodes}
    outputs = {}
    skipped = set()

    for node_id in order:
        if node_id in skipped:
            emit(
                {
                    "event": "node_error",
                    "node_id": node_id,
                    "message": "skipped: upstream dependency failed",
                }
            )
            skipped.update(dependents[node_id])
            continue

        node = node_by_id[node_id]
        kwargs = dict(node.get("inputs", {}))
        for (target_node, target_input), (from_node, from_output) in link_by_target.items():
            if target_node != node_id:
                continue
            from_node_type = node_by_id[from_node]["type"]
            out_names = list(get_node_class(from_node_type).RETURN_NAMES)
            kwargs[target_input] = outputs[from_node][out_names.index(from_output)]

        emit({"event": "node_started", "node_id": node_id})
        try:
            result = get_node_class(node["type"])().execute(**kwargs)
            outputs[node_id] = result
            emit({"event": "node_completed", "node_id": node_id, "outputs": result})
        except Exception as exc:
            outputs[node_id] = ()
            emit({"event": "node_error", "node_id": node_id, "message": str(exc)})
            skipped.update(dependents[node_id])

    emit({"event": "run_finished"})
    return outputs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_executor.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add server/executor.py tests/test_executor.py
git commit -m "feat: add graph executor with topo sort and error propagation"
```

---

### Task 5: Workspace manager

**Files:**
- Create: `server/workspace.py`
- Test: `tests/test_workspace.py`

**Interfaces:**
- Produces:
  - `class WorkspaceError(Exception)`
  - `WORKSPACES_ROOT: Path` (module-level, monkeypatchable by tests and by
    Task 6's API layer)
  - `list_workspaces() -> list[str]`
  - `create_workspace(name: str, source_lang: str = "", target_lang: str = "") -> None`
    — raises `WorkspaceError` if it already exists.
  - `open_workspace(name: str) -> dict` — returns the parsed `graph.json`
    contents; raises `WorkspaceError` if missing, corrupted, or missing
    `nodes`/`links` keys.
  - `save_graph(name: str, graph: dict) -> None` — raises `WorkspaceError`
    if the workspace doesn't exist.
  - `delete_workspace(name: str) -> None` — raises `WorkspaceError` if the
    workspace doesn't exist.

- [ ] **Step 1: Write the failing tests**

`tests/test_workspace.py`:

```python
import json

import pytest

from server import workspace


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")


def test_list_workspaces_empty_when_root_missing():
    assert workspace.list_workspaces() == []


def test_create_and_list_workspace():
    workspace.create_workspace("novel-a", source_lang="ja", target_lang="vi")
    assert workspace.list_workspaces() == ["novel-a"]


def test_create_duplicate_workspace_raises():
    workspace.create_workspace("novel-a")
    with pytest.raises(workspace.WorkspaceError):
        workspace.create_workspace("novel-a")


def test_open_workspace_returns_default_graph():
    workspace.create_workspace("novel-a")
    graph = workspace.open_workspace("novel-a")
    assert graph["nodes"] == []
    assert graph["links"] == []


def test_open_missing_workspace_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.open_workspace("does-not-exist")


def test_open_workspace_with_corrupted_graph_raises_clear_error():
    workspace.create_workspace("novel-a")
    graph_path = workspace.WORKSPACES_ROOT / "novel-a" / "graph.json"
    graph_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(workspace.WorkspaceError):
        workspace.open_workspace("novel-a")


def test_save_graph_persists_content():
    workspace.create_workspace("novel-a")
    workspace.save_graph("novel-a", {"nodes": [{"id": "1"}], "links": []})

    reloaded = workspace.open_workspace("novel-a")
    assert reloaded["nodes"] == [{"id": "1"}]


def test_delete_workspace_removes_directory():
    workspace.create_workspace("novel-a")
    workspace.delete_workspace("novel-a")
    assert workspace.list_workspaces() == []


def test_delete_missing_workspace_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.delete_workspace("does-not-exist")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workspace.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server.workspace'`)

- [ ] **Step 3: Implement `server/workspace.py`**

```python
import json
import shutil
from pathlib import Path

WORKSPACES_ROOT = Path("workspaces")

_DEFAULT_GRAPH = {"nodes": [], "links": []}


class WorkspaceError(Exception):
    pass


def _workspace_dir(name: str) -> Path:
    return WORKSPACES_ROOT / name


def list_workspaces() -> list:
    if not WORKSPACES_ROOT.exists():
        return []
    return sorted(p.name for p in WORKSPACES_ROOT.iterdir() if p.is_dir())


def create_workspace(name: str, source_lang: str = "", target_lang: str = "") -> None:
    ws_dir = _workspace_dir(name)
    if ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' already exists")
    ws_dir.mkdir(parents=True)
    (ws_dir / "chapters").mkdir()
    (ws_dir / "output").mkdir()
    (ws_dir / "config.json").write_text(
        json.dumps(
            {"name": name, "source_lang": source_lang, "target_lang": target_lang},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (ws_dir / "graph.json").write_text(json.dumps(_DEFAULT_GRAPH), encoding="utf-8")


def open_workspace(name: str) -> dict:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    graph_path = ws_dir / "graph.json"
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        raise WorkspaceError(f"Workspace '{name}' has a corrupted graph.json: {exc}")
    if "nodes" not in graph or "links" not in graph:
        raise WorkspaceError(f"Workspace '{name}' graph.json missing 'nodes'/'links'")
    return graph


def save_graph(name: str, graph: dict) -> None:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    (ws_dir / "graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def delete_workspace(name: str) -> None:
    ws_dir = _workspace_dir(name)
    if not ws_dir.exists():
        raise WorkspaceError(f"Workspace '{name}' does not exist")
    shutil.rmtree(ws_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_workspace.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add server/workspace.py tests/test_workspace.py
git commit -m "feat: add filesystem-backed workspace manager"
```

---

### Task 6: REST API wiring

**Files:**
- Modify: `server/main.py` (full replacement shown below)
- Test: `tests/test_api.py` (extend)

**Interfaces:**
- Consumes: `list_node_metadata` (Task 2), `server.nodes.utility` (Task 3,
  imported for side-effect registration), `workspace.list_workspaces`,
  `workspace.create_workspace`, `workspace.open_workspace`,
  `workspace.save_graph`, `workspace.delete_workspace`,
  `workspace.WorkspaceError` (Task 5).
- Produces REST endpoints:
  - `GET /api/health` → `{"status": "ok"}` (unchanged from Task 1)
  - `GET /api/nodes` → `list_node_metadata()`
  - `GET /api/workspaces` → `{"workspaces": [...]}`
  - `POST /api/workspaces` body `{"name", "source_lang"?, "target_lang"?}` →
    201 `{"name": ...}`; 409 if it already exists
  - `GET /api/workspaces/{name}` → the graph dict; 404 if missing/corrupted
  - `PUT /api/workspaces/{name}/graph` body: the graph dict → `{"status": "ok"}`;
    404 if workspace missing
  - `DELETE /api/workspaces/{name}` → `{"status": "ok"}`; 404 if missing

- [ ] **Step 1: Write the failing tests (append to `tests/test_api.py`)**

```python
import pytest

from server import workspace


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")


def test_list_nodes_includes_utility_nodes():
    client = TestClient(app)
    response = client.get("/api/nodes")
    assert response.status_code == 200
    types = {n["type"] for n in response.json()}
    assert {"LoadTextFile", "SaveTextFile", "TextPreview", "Note"} <= types


def test_create_list_open_save_delete_workspace_via_api():
    client = TestClient(app)

    create_resp = client.post(
        "/api/workspaces", json={"name": "novel-a", "source_lang": "ja", "target_lang": "vi"}
    )
    assert create_resp.status_code == 201

    list_resp = client.get("/api/workspaces")
    assert list_resp.json() == {"workspaces": ["novel-a"]}

    open_resp = client.get("/api/workspaces/novel-a")
    assert open_resp.json() == {"nodes": [], "links": []}

    save_resp = client.put(
        "/api/workspaces/novel-a/graph", json={"nodes": [{"id": "1"}], "links": []}
    )
    assert save_resp.status_code == 200

    reopen_resp = client.get("/api/workspaces/novel-a")
    assert reopen_resp.json()["nodes"] == [{"id": "1"}]

    delete_resp = client.delete("/api/workspaces/novel-a")
    assert delete_resp.status_code == 200
    assert client.get("/api/workspaces").json() == {"workspaces": []}


def test_create_duplicate_workspace_returns_409():
    client = TestClient(app)
    client.post("/api/workspaces", json={"name": "novel-a"})
    response = client.post("/api/workspaces", json={"name": "novel-a"})
    assert response.status_code == 409


def test_open_missing_workspace_returns_404():
    client = TestClient(app)
    response = client.get("/api/workspaces/does-not-exist")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py -v`
Expected: FAIL (404s on new routes / `AttributeError`)

- [ ] **Step 3: Replace `server/main.py` with the full wiring**

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import workspace
from server.node_registry import list_node_metadata
from server.nodes import utility  # noqa: F401  (triggers registration)

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class CreateWorkspaceRequest(BaseModel):
    name: str
    source_lang: str = ""
    target_lang: str = ""


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/nodes")
def get_nodes():
    return list_node_metadata()


@app.get("/api/workspaces")
def get_workspaces():
    return {"workspaces": workspace.list_workspaces()}


@app.post("/api/workspaces", status_code=201)
def post_workspace(body: CreateWorkspaceRequest):
    try:
        workspace.create_workspace(body.name, body.source_lang, body.target_lang)
    except workspace.WorkspaceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"name": body.name}


@app.get("/api/workspaces/{name}")
def get_workspace_graph(name: str):
    try:
        return workspace.open_workspace(name)
    except workspace.WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.put("/api/workspaces/{name}/graph")
def put_workspace_graph(name: str, graph: dict):
    try:
        workspace.save_graph(name, graph)
    except workspace.WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok"}


@app.delete("/api/workspaces/{name}")
def delete_workspace(name: str):
    try:
        workspace.delete_workspace(name)
    except workspace.WorkspaceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: PASS (all passed)

- [ ] **Step 5: Commit**

```bash
git add server/main.py tests/test_api.py
git commit -m "feat: wire node registry and workspace CRUD into REST API"
```

---

### Task 7: WebSocket execution endpoint

**Files:**
- Modify: `server/main.py` (add the websocket route + imports shown below)
- Test: `tests/test_api.py` (extend)

**Interfaces:**
- Consumes: `run_graph`, `GraphValidationError` from `server.executor`
  (Task 4).
- Produces: `WS /ws/run/{workspace_name}` — client sends one JSON message
  `{"graph": {"nodes": [...], "links": [...]}}` (already in the executor's
  simplified format, e.g. built client-side by Task 9's `buildExecutionPayload`);
  server streams one JSON object per line for each executor event
  (`node_started`/`node_completed`/`node_error`/`run_finished`), or a single
  `{"event": "validation_error", "message": ...}` if the graph fails
  validation, then closes the connection.

- [ ] **Step 1: Write the failing test (append to `tests/test_api.py`)**

```python
def test_websocket_run_streams_events_and_writes_file(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("raw chapter", encoding="utf-8")
    dst = tmp_path / "out.txt"

    client = TestClient(app)
    graph = {
        "nodes": [
            {"id": "1", "type": "LoadTextFile", "inputs": {"path": str(src)}},
            {"id": "2", "type": "SaveTextFile", "inputs": {"path": str(dst)}},
        ],
        "links": [
            {"from_node": "1", "from_output": "text", "to_node": "2", "to_input": "text"}
        ],
    }

    events = []
    with client.websocket_connect("/ws/run/any") as websocket:
        websocket.send_json({"graph": graph})
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["event"] == "run_finished":
                break

    assert dst.read_text(encoding="utf-8") == "raw chapter"
    event_names = [e["event"] for e in events]
    assert event_names == [
        "node_started",
        "node_completed",
        "node_started",
        "node_completed",
        "run_finished",
    ]


def test_websocket_run_reports_validation_error():
    client = TestClient(app)
    graph = {"nodes": [{"id": "1", "type": "LoadTextFile", "inputs": {}}], "links": []}

    with client.websocket_connect("/ws/run/any") as websocket:
        websocket.send_json({"graph": graph})
        event = websocket.receive_json()

    assert event["event"] == "validation_error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py -v`
Expected: FAIL (websocket connect 404 — route doesn't exist yet)

- [ ] **Step 3: Add the websocket endpoint to `server/main.py`**

Add these imports at the top (alongside the existing ones):

```python
import asyncio
import queue
import threading

from fastapi import WebSocket

from server.executor import GraphValidationError, run_graph
```

Add this route before the `app.mount(...)` line at the bottom of the file
(the static mount must stay last):

```python
@app.websocket("/ws/run/{workspace_name}")
async def ws_run(websocket: WebSocket, workspace_name: str):
    await websocket.accept()
    data = await websocket.receive_json()
    graph = data["graph"]

    event_queue: "queue.Queue" = queue.Queue()

    def on_event(event):
        event_queue.put(event)

    def worker():
        try:
            run_graph(graph["nodes"], graph["links"], on_event=on_event)
        except GraphValidationError as exc:
            event_queue.put({"event": "validation_error", "message": str(exc)})
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    loop = asyncio.get_event_loop()
    while True:
        event = await loop.run_in_executor(None, event_queue.get)
        if event is None:
            break
        await websocket.send_json(event)

    await websocket.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: PASS (all passed)

- [ ] **Step 5: Commit**

```bash
git add server/main.py tests/test_api.py
git commit -m "feat: stream graph execution events over websocket"
```

---

### Task 8: Frontend — workspace picker screen

**Files:**
- Modify: `web/index.html` (full replacement)
- Create: `web/js/workspace_picker.js`
- Create: `web/css/style.css`

**Interfaces:**
- Consumes: `GET /api/workspaces`, `POST /api/workspaces` (Task 6).
- Produces: navigating to `canvas.html?workspace=<name>` on selecting or
  creating a workspace (consumed by Task 9).

- [ ] **Step 1: Replace `web/index.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>Node Translator — Workspaces</title>
  <link rel="stylesheet" href="/css/style.css" />
</head>
<body>
  <main class="picker">
    <h1>Chọn workspace</h1>
    <ul id="workspace-list"></ul>

    <h2>Tạo workspace mới</h2>
    <form id="create-form">
      <input id="new-name" placeholder="Tên workspace" required />
      <input id="new-source-lang" placeholder="Ngôn ngữ nguồn (vd: ja)" />
      <input id="new-target-lang" placeholder="Ngôn ngữ đích (vd: vi)" />
      <button type="submit">Tạo</button>
    </form>
    <p id="picker-error" class="error"></p>
  </main>
  <script src="/js/workspace_picker.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `web/js/workspace_picker.js`**

```js
async function loadWorkspaces() {
  const response = await fetch("/api/workspaces");
  const data = await response.json();
  const list = document.getElementById("workspace-list");
  list.innerHTML = "";
  for (const name of data.workspaces) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `/canvas.html?workspace=${encodeURIComponent(name)}`;
    link.textContent = name;
    item.appendChild(link);
    list.appendChild(item);
  }
}

async function createWorkspace(event) {
  event.preventDefault();
  const errorEl = document.getElementById("picker-error");
  errorEl.textContent = "";

  const name = document.getElementById("new-name").value.trim();
  const sourceLang = document.getElementById("new-source-lang").value.trim();
  const targetLang = document.getElementById("new-target-lang").value.trim();

  const response = await fetch("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, source_lang: sourceLang, target_lang: targetLang }),
  });

  if (!response.ok) {
    const body = await response.json();
    errorEl.textContent = body.detail || "Không tạo được workspace";
    return;
  }

  window.location.href = `/canvas.html?workspace=${encodeURIComponent(name)}`;
}

document.getElementById("create-form").addEventListener("submit", createWorkspace);
loadWorkspaces();
```

- [ ] **Step 3: Create `web/css/style.css`**

```css
body {
  font-family: system-ui, sans-serif;
  max-width: 600px;
  margin: 40px auto;
  color: #222;
}

.picker ul {
  list-style: none;
  padding: 0;
}

.picker li {
  padding: 8px 0;
  border-bottom: 1px solid #ddd;
}

.picker form {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.error {
  color: #b00020;
}
```

- [ ] **Step 4: Manual verification**

Run: `python -m uvicorn server.main:app --reload` then open
`http://127.0.0.1:8000/` in a browser.

Expected: page shows "Chọn workspace" with an empty list, creating a
workspace named `test-novel` navigates to `canvas.html?workspace=test-novel`
(a 404/blank page is fine here — `canvas.html` doesn't exist until Task 9),
and reloading `/` afterward shows `test-novel` in the list.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/js/workspace_picker.js web/css/style.css
git commit -m "feat: add workspace picker screen"
```

---

### Task 9: Frontend — vendor litegraph.js and build the canvas page

**Files:**
- Create: `web/vendor/package.json` (npm scratch dir, gitignored)
- Create: `web/js/litegraph.js` (vendored, copied from npm package)
- Create: `web/css/litegraph.css` (vendored, copied from npm package)
- Create: `web/canvas.html`
- Create: `web/js/nodegen.js`
- Create: `web/js/canvas_app.js`

**Interfaces:**
- Consumes: `GET /api/nodes` (Task 6), `GET /api/workspaces/{name}` (Task 6),
  `PUT /api/workspaces/{name}/graph` (Task 6), `WS /ws/run/{workspace_name}`
  (Task 7); the `?workspace=<name>` query param set by Task 8's navigation.
- Produces: `registerDynamicNodeTypes(nodeMetadataList)` and
  `buildExecutionPayload(graph)` in `nodegen.js`, used by `canvas_app.js`.

- [ ] **Step 1: Vendor litegraph.js via npm**

```bash
mkdir -p web/vendor
cd web/vendor && npm init -y && npm install litegraph.js@0.7.18
cd ../..
cp web/vendor/node_modules/litegraph.js/build/litegraph.js web/js/litegraph.js
cp web/vendor/node_modules/litegraph.js/css/litegraph.css web/css/litegraph.css
```

If npm/the registry is unavailable in this environment, fetch the same
build directly instead:

```bash
curl -L -o web/js/litegraph.js https://unpkg.com/litegraph.js@0.7.18/build/litegraph.js
curl -L -o web/css/litegraph.css https://unpkg.com/litegraph.js@0.7.18/css/litegraph.css
```

Verify: `web/js/litegraph.js` exists and is non-empty (`wc -l web/js/litegraph.js`
reports more than a few thousand lines).

- [ ] **Step 2: Create `web/js/nodegen.js`**

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
        if (inputType === "STRING") {
          this.addWidget("text", inputName, this.properties[inputName], (value) => {
            this.properties[inputName] = value;
          });
        }
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

// buildExecutionPayload reads node.properties (not widgets_values) as the
// source of truth: litegraph restores `properties` verbatim on configure(),
// while widget display sync after reload is a separate, non-blocking concern.
function buildExecutionPayload(graph) {
  const nodes = graph._nodes.map((n) => ({
    id: String(n.id),
    type: n.constructor.nodeType,
    inputs: Object.assign({}, n.properties),
  }));

  const links = [];
  for (const linkId in graph.links) {
    const link = graph.links[linkId];
    if (!link) continue;
    const originNode = graph.getNodeById(link.origin_id);
    const targetNode = graph.getNodeById(link.target_id);
    links.push({
      from_node: String(link.origin_id),
      from_output: originNode.outputs[link.origin_slot].name,
      to_node: String(link.target_id),
      to_input: targetNode.inputs[link.target_slot].name,
    });
  }

  return { nodes, links };
}
```

- [ ] **Step 3: Create `web/canvas.html`**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>Node Translator — Canvas</title>
  <link rel="stylesheet" href="/css/litegraph.css" />
  <link rel="stylesheet" href="/css/style.css" />
  <style>
    #graph-canvas { width: 100vw; height: 80vh; }
    #toolbar { padding: 8px; }
  </style>
</head>
<body>
  <div id="toolbar">
    <a href="/index.html">&larr; Workspaces</a>
    <button id="run-button">Run</button>
    <button id="save-button">Save</button>
    <span id="status"></span>
  </div>
  <canvas id="graph-canvas"></canvas>
  <script src="/js/litegraph.js"></script>
  <script src="/js/nodegen.js"></script>
  <script src="/js/canvas_app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create `web/js/canvas_app.js`**

```js
const params = new URLSearchParams(window.location.search);
const workspaceName = params.get("workspace");

const graph = new LGraph();
const canvasEl = document.getElementById("graph-canvas");
const canvas = new LGraphCanvas(canvasEl, graph);

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

function colorForEvent(eventName) {
  if (eventName === "node_started") return "#557";
  if (eventName === "node_completed") return "#575";
  return "#755";
}

async function init() {
  const nodesResponse = await fetch("/api/nodes");
  const nodeMetadataList = await nodesResponse.json();
  registerDynamicNodeTypes(nodeMetadataList);

  const graphResponse = await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}`);
  const savedGraph = await graphResponse.json();
  if (savedGraph.nodes && savedGraph.nodes.length) {
    graph.configure(savedGraph);
  }

  graph.start();
}

async function saveGraph() {
  await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}/graph`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph.serialize()),
  });
  setStatus("Đã lưu");
}

function runGraph() {
  const payload = buildExecutionPayload(graph);
  const ws = new WebSocket(`ws://${location.host}/ws/run/${encodeURIComponent(workspaceName)}`);

  ws.onopen = () => ws.send(JSON.stringify({ graph: payload }));

  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (event.event === "run_finished") {
      setStatus("Hoàn tất");
      return;
    }
    if (event.event === "validation_error") {
      setStatus(`Lỗi: ${event.message}`);
      return;
    }
    const node = graph.getNodeById(Number(event.node_id));
    if (node) {
      node.bgcolor = colorForEvent(event.event);
      graph.setDirtyCanvas(true, true);
    }
    setStatus(`${event.event}: node ${event.node_id}`);
  };
}

document.getElementById("run-button").addEventListener("click", runGraph);
document.getElementById("save-button").addEventListener("click", saveGraph);

init();
```

- [ ] **Step 5: Manual verification**

Run: `python -m uvicorn server.main:app --reload`, open
`http://127.0.0.1:8000/`, create workspace `demo`.

Expected on the resulting canvas page:
1. Right-click canvas → node menu shows `Utility/LoadTextFile`,
   `Utility/SaveTextFile`, `Utility/TextPreview`, `Utility/Note`.
2. Drag a `LoadTextFile` and a `SaveTextFile` node onto the canvas, connect
   `text` output to `text` input, fill in the `path` widgets with real file
   paths on disk (create a small `.txt` file first for the source path).
3. Click **Save** → status shows "Đã lưu"; reload the page → the two nodes
   and their connection are still there.
4. Click **Run** → both nodes flash blue then green in sequence, status
   ends with "Hoàn tất", and the destination file now contains the source
   file's text.
5. Point `LoadTextFile`'s path at a nonexistent file, click Run → status
   shows an error event for that node and the destination file is not
   overwritten.

- [ ] **Step 6: Commit**

```bash
git add web/canvas.html web/js/nodegen.js web/js/canvas_app.js web/js/litegraph.js web/css/litegraph.css
git commit -m "feat: add litegraph canvas page with dynamic node types and run wiring"
```

---

### Task 10: `run.bat` launcher and full end-to-end verification

**Files:**
- Create: `run.bat`

**Interfaces:**
- Consumes: `requirements.txt` (Task 1), `server.main:app` (Tasks 1/6/7).
- Produces: a double-clickable entry point for a non-technical user.

- [ ] **Step 1: Create `run.bat`**

```bat
@echo off
setlocal

set VENV_DIR=%~dp0.venv

if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Installing dependencies...
pip install -r "%~dp0requirements.txt" --quiet

start "" http://127.0.0.1:8000

python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

- [ ] **Step 2: Manual end-to-end verification**

Run: double-click `run.bat` from Windows Explorer (or run it from a fresh
`cmd.exe`, not the existing dev shell, to confirm it works without any
pre-activated environment).

Expected:
1. A `.venv` folder is created on first run; console shows dependency
   installation.
2. Default browser opens automatically to `http://127.0.0.1:8000/` showing
   the workspace picker.
3. Repeat the full flow from Task 9 Step 5 (create workspace, build a
   two-node graph, save, run, confirm output file) using this
   `run.bat`-launched server.
4. Close the console window, run `run.bat` again — startup is fast (no
   reinstall) and the previously created workspace still appears in the
   list.

- [ ] **Step 3: Commit**

```bash
git add run.bat
git commit -m "feat: add run.bat launcher"
```

---

## Self-Review Notes

- **Spec coverage:** Workspace manager (#1) → Task 5/6; Node registry/base
  class (#2) → Task 2; MVP utility nodes (#3) → Task 3; Graph executor (#4)
  → Task 4/7; Data flow (open → edit → run → stream → save) → Tasks 6-9;
  Error handling (validation before run, per-node error, corrupted
  workspace file) → Tasks 4/5/7 tests; Testing section (pytest executor,
  integration sample graph, manual frontend) → Tasks 4/7/9-10. Loop Group
  (#5) and Template system (#6) are explicitly out of scope for this plan
  (A2, separate plan) per the spec's own phase split.
- **Type consistency:** `NodeBase`/`register_node`/`get_node_class`/
  `list_node_metadata` (Task 2) are used with identical names and
  signatures in Tasks 3, 4, 6. `GraphValidationError`/`run_graph` (Task 4)
  match their use in Task 7. `WorkspaceError`/`list_workspaces`/
  `create_workspace`/`open_workspace`/`save_graph`/`delete_workspace`
  (Task 5) match their use in Task 6. The executor's graph payload shape
  (`{"id", "type", "inputs"}` nodes / `{"from_node", "from_output",
  "to_node", "to_input"}` links) is identical across Tasks 4, 7, and the
  JS `buildExecutionPayload` in Task 9.
- **Placeholder scan:** no TBD/TODO; every step has runnable code or an
  explicit manual-verification checklist (frontend/launcher tasks only,
  consistent with the spec's "manual testing for frontend" decision).

---

Plan complete and saved to `docs/superpowers/plans/2026-08-28-node-graph-engine-a1-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
