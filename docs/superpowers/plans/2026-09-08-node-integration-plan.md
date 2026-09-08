# Node Integration (Sub-project C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the already-built `translation_core` package (Sub-project B)
into the already-built node-graph engine (Sub-project A) as six real,
draggable node types — Provider, LoadAgentFile, SaveAgentFile, RAGQuery,
SaveToRAG, Translate — so a user can assemble a real translation workflow
on the canvas and run it.

**Architecture:** A small opt-in extension to the executor
(`NEEDS_WORKSPACE`) lets specific node classes receive the running
workspace's name without touching any existing node. Six thin adapter
node classes in one new file call straight into `translation_core`'s
already-tested public API — no new business logic, no changes to
`translation_core` itself.

**Tech Stack:** Python 3.11+ (unchanged), `translation_core`'s public API
(`ProviderConfig`, `create_provider`, `RAGStore`, `RAGExample`,
`load_agent_file`, `save_agent_file`, `translate_chunk`), pytest.

**Spec:** [docs/superpowers/specs/2026-09-08-node-integration-design.md](../specs/2026-09-08-node-integration-design.md)

## Global Constraints

- Python 3.11+ only.
- New nodes register via the existing `@register_node`/`NodeBase`
  convention from Sub-project A — no change to that mechanism beyond
  adding one new opt-in class attribute (`NEEDS_WORKSPACE`).
- `NEEDS_WORKSPACE` defaults to `False` and must not change behavior for
  any existing node that doesn't set it.
- No new REST/WebSocket endpoints — everything rides through the existing
  `/api/nodes`, `/api/workspaces/*`, `/ws/run/{workspace_name}`.
- `translation_core` (Sub-project B) is consumed only via its public
  `__init__.py` exports (`from translation_core import ...`) — it is not
  modified by this plan.
- `api_key` is entered as a plain STRING widget on the Provider node and
  is accepted to be stored in `graph.json` plaintext — this was already
  decided during brainstorming for this MVP (local, single-user tool).
- No template-saving system (Sub-project A2) and no auto-glossary-
  extraction node in this plan — both explicitly deferred.

---

## File Structure

```
server/
  node_registry.py       # +NodeBase.NEEDS_WORKSPACE = False
  executor.py               # +workspace_name param on run_graph(), injects it for flagged nodes
  main.py                     # +import server.nodes.translate for registration; ws_run passes workspace_name through
  workspace.py                   # +get_workspace_path(); create_workspace() seeds agent.md
  nodes/
    translate.py                  # NEW: Provider, LoadAgentFile, SaveAgentFile, RAGQuery, SaveToRAG, Translate
tests/
  test_executor.py                 # +NEEDS_WORKSPACE injection tests
  test_workspace.py                  # +get_workspace_path() + agent.md seeding tests
  test_translate_nodes.py              # NEW: one test per new node
```

---

### Task 1: Executor `NEEDS_WORKSPACE` mechanism

**Files:**
- Modify: `server/node_registry.py`
- Modify: `server/executor.py`
- Modify: `server/main.py`
- Test: `tests/test_executor.py`

**Interfaces:**
- Produces: `NodeBase.NEEDS_WORKSPACE: bool = False` (class attribute);
  `run_graph(nodes, links, on_event=None, workspace_name=None) -> dict` —
  for any node whose class has `NEEDS_WORKSPACE = True`, the executor adds
  `workspace_name` to that node's `execute()` kwargs. `workspace_name` is
  never part of a node's `INPUT_TYPES()` — it is injected purely at
  execution time, not a canvas-visible input.

- [ ] **Step 1: Write the failing tests (append to `tests/test_executor.py`)**

```python
@register_node("_TestNeedsWorkspace")
class _TestNeedsWorkspace(NodeBase):
    CATEGORY = "Test"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("out",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self, workspace_name):
        return (workspace_name,)


def test_run_graph_injects_workspace_name_for_flagged_nodes():
    nodes = [{"id": "1", "type": "_TestNeedsWorkspace", "inputs": {}}]

    outputs = run_graph(nodes, [], workspace_name="my-novel")

    assert outputs["1"] == ("my-novel",)


def test_run_graph_does_not_inject_workspace_name_for_normal_nodes():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}}]

    outputs = run_graph(nodes, [], workspace_name="my-novel")

    assert outputs["1"] == ("a!",)
```

The second test is the regression guard: `_TestAdd.execute(self, value)`
(already defined earlier in this file) does not accept a `workspace_name`
kwarg — if the executor injected it unconditionally instead of only for
flagged nodes, this test would fail with `TypeError: execute() got an
unexpected keyword argument 'workspace_name'`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_executor.py -v`
Expected: FAIL — `test_run_graph_injects_workspace_name_for_flagged_nodes`
fails with `TypeError: run_graph() got an unexpected keyword argument
'workspace_name'`.

- [ ] **Step 3: Add `NEEDS_WORKSPACE` to `NodeBase`**

In `server/node_registry.py`, add the class attribute alongside the
existing ones:

```python
class NodeBase:
    CATEGORY = "Uncategorized"
    RETURN_TYPES: tuple = ()
    RETURN_NAMES: tuple = ()
    NEEDS_WORKSPACE: bool = False

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {"required": {}, "optional": {}}

    def execute(self, **kwargs) -> tuple:
        raise NotImplementedError
```

- [ ] **Step 4: Update `run_graph()` in `server/executor.py`**

Replace the function signature and the node-execution block inside the
`for node_id in order:` loop. The current code is:

```python
def run_graph(nodes, links, on_event=None) -> dict:
```

```python
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
```

Change to:

```python
def run_graph(nodes, links, on_event=None, workspace_name=None) -> dict:
```

```python
        node = node_by_id[node_id]
        node_cls = get_node_class(node["type"])
        kwargs = dict(node.get("inputs", {}))
        for (target_node, target_input), (from_node, from_output) in link_by_target.items():
            if target_node != node_id:
                continue
            from_node_type = node_by_id[from_node]["type"]
            out_names = list(get_node_class(from_node_type).RETURN_NAMES)
            kwargs[target_input] = outputs[from_node][out_names.index(from_output)]
        if node_cls.NEEDS_WORKSPACE:
            kwargs["workspace_name"] = workspace_name

        emit({"event": "node_started", "node_id": node_id})
        try:
            result = node_cls().execute(**kwargs)
```

(Everything else in `run_graph` — the `outputs[node_id] = result`,
`emit(...)`, `except Exception` block, etc. — is unchanged.)

- [ ] **Step 5: Thread `workspace_name` through `server/main.py`'s `ws_run`**

In `server/main.py`, change:

```python
            run_graph(graph["nodes"], graph["links"], on_event=on_event)
```

to:

```python
            run_graph(
                graph["nodes"], graph["links"], on_event=on_event,
                workspace_name=workspace_name,
            )
```

(`workspace_name` is already a parameter of `ws_run(websocket, workspace_name)` — it was previously unused inside the function body; this is the first thing that actually consumes it.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_executor.py -v`
Expected: PASS (all tests in the file, including the 2 new ones)

- [ ] **Step 7: Run the full suite to confirm no regressions**

Run: `pytest -v`
Expected: all tests pass (should be 107 existing + 2 new = 109).

- [ ] **Step 8: Commit**

```bash
git add server/node_registry.py server/executor.py server/main.py tests/test_executor.py
git commit -m "feat: add NEEDS_WORKSPACE mechanism so nodes can receive the running workspace name"
```

---

### Task 2: Workspace path helper + agent file seeding

**Files:**
- Modify: `server/workspace.py`
- Test: `tests/test_workspace.py`

**Interfaces:**
- Produces: `get_workspace_path(name: str, *parts: str) -> Path` — validates
  `name` the same way every other workspace function does (raises
  `InvalidWorkspaceNameError` for a bad name) and returns
  `WORKSPACES_ROOT / name / *parts`. `create_workspace()` now also writes
  an `agent.md` seed file into every new workspace. Later tasks (3-6) call
  `get_workspace_path(workspace_name, "agent.md")` and
  `get_workspace_path(workspace_name, "rag_index")`.

- [ ] **Step 1: Write the failing tests (append to `tests/test_workspace.py`)**

```python
def test_get_workspace_path_returns_path_under_workspace():
    workspace.create_workspace("novel-a")

    path = workspace.get_workspace_path("novel-a", "rag_index")

    assert path == workspace.WORKSPACES_ROOT / "novel-a" / "rag_index"


def test_get_workspace_path_validates_name():
    with pytest.raises(workspace.InvalidWorkspaceNameError):
        workspace.get_workspace_path("../evil", "agent.md")


def test_create_workspace_seeds_agent_file():
    workspace.create_workspace("novel-a")

    agent_path = workspace.get_workspace_path("novel-a", "agent.md")

    assert agent_path.exists()
    assert "Dịch sang tiếng Việt" in agent_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workspace.py -v`
Expected: FAIL — `AttributeError: module 'server.workspace' has no
attribute 'get_workspace_path'`.

- [ ] **Step 3: Implement in `server/workspace.py`**

Add near the top, alongside `_DEFAULT_GRAPH`:

```python
_DEFAULT_AGENT_FILE = (
    "# Hướng dẫn dịch\n\n"
    "Dịch sang tiếng Việt, giữ văn phong tự nhiên, nhất quán tên riêng/thuật ngữ.\n"
)
```

Add this public function (anywhere after `_workspace_dir` is defined, e.g.
right after it):

```python
def get_workspace_path(name: str, *parts: str) -> Path:
    return _workspace_dir(name).joinpath(*parts)
```

In `create_workspace()`, add one line after the existing `graph.json`
write:

```python
    (ws_dir / "graph.json").write_text(json.dumps(_DEFAULT_GRAPH), encoding="utf-8")
    (ws_dir / "agent.md").write_text(_DEFAULT_AGENT_FILE, encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_workspace.py -v`
Expected: PASS (all tests in the file, including the 3 new ones)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all pass (109 + 3 = 112).

- [ ] **Step 6: Commit**

```bash
git add server/workspace.py tests/test_workspace.py
git commit -m "feat: add get_workspace_path() helper and seed agent.md on workspace creation"
```

---

### Task 3: `Provider` node

**Files:**
- Create: `server/nodes/translate.py`
- Modify: `server/main.py`
- Test: `tests/test_translate_nodes.py`

**Interfaces:**
- Consumes: `ProviderConfig`, `create_provider` from `translation_core`
  (Sub-project B, already built); `NodeBase`, `register_node` from
  `server.node_registry` (Sub-project A).
- Produces: registered node type `"Provider"`, `RETURN_TYPES = ("PROVIDER",)`.
  Its runtime output value (index 0 of the returned tuple) is a real
  `LLMProvider` instance (an `OpenAICompatibleProvider`), not a string —
  the executor passes Python objects between nodes untouched. Task 6's
  `Translate` node consumes a value of this same runtime type via its
  `provider` input.

- [ ] **Step 1: Write the failing test**

`tests/test_translate_nodes.py`:

```python
from translation_core.providers.openai_compatible import OpenAICompatibleProvider

from server.node_registry import get_node_class
from server.nodes import translate  # noqa: F401  (triggers registration)


def test_provider_node_creates_openai_compatible_provider():
    node = get_node_class("Provider")()

    result = node.execute(
        base_url="http://localhost:1234/v1", api_key="dummy", model="local-model"
    )

    assert len(result) == 1
    provider = result[0]
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://localhost:1234/v1"
    assert provider.model == "local-model"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server.nodes.translate'`)

- [ ] **Step 3: Create `server/nodes/translate.py`**

```python
from translation_core import ProviderConfig, create_provider

from server.node_registry import NodeBase, register_node


@register_node("Provider")
class Provider(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("PROVIDER",)
    RETURN_NAMES = ("provider",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": ("STRING", {"default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "model": ("STRING", {"default": ""}),
            }
        }

    def execute(self, base_url: str, api_key: str, model: str) -> tuple:
        config = ProviderConfig(
            type="openai_compatible", base_url=base_url, api_key=api_key, model=model
        )
        return (create_provider(config),)
```

- [ ] **Step 4: Register the new module in `server/main.py`**

Add this import alongside the existing `from server.nodes import utility`
line:

```python
from server.nodes import translate as translate_nodes  # noqa: F401  (triggers registration)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: all pass (112 + 1 = 113).

- [ ] **Step 7: Commit**

```bash
git add server/nodes/translate.py server/main.py tests/test_translate_nodes.py
git commit -m "feat: add Provider node wrapping translation_core's provider factory"
```

---

### Task 4: `LoadAgentFile` / `SaveAgentFile` nodes

**Files:**
- Modify: `server/nodes/translate.py`
- Modify: `tests/test_translate_nodes.py`

**Interfaces:**
- Consumes: `load_agent_file`, `save_agent_file` from `translation_core`
  (Sub-project B); `workspace.get_workspace_path` from `server.workspace`
  (Task 2); the `NEEDS_WORKSPACE` mechanism (Task 1).
- Produces: registered node types `"LoadAgentFile"` (`RETURN_TYPES =
  ("STRING",)`, no inputs) and `"SaveAgentFile"` (`RETURN_TYPES = ()`,
  required input `text`). Both have `NEEDS_WORKSPACE = True`, so their
  `execute()` receives a `workspace_name` kwarg from the executor — this
  is not a widget/slot on the node itself.

- [ ] **Step 1: Add the isolation fixture and write the failing tests**

Add this fixture near the top of `tests/test_translate_nodes.py`, right
after the existing imports (it must apply to every test in the file,
including Task 3's — that test doesn't touch the filesystem, so the
fixture is harmless there):

```python
import pytest

from server import workspace


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")
```

Then append these tests:

```python
def test_load_agent_file_node_reads_seeded_file():
    workspace.create_workspace("novel-a")
    node = get_node_class("LoadAgentFile")()

    result = node.execute(workspace_name="novel-a")

    assert "Dịch sang tiếng Việt" in result[0]


def test_load_agent_file_node_raises_when_missing():
    workspace.create_workspace("novel-a")
    workspace.get_workspace_path("novel-a", "agent.md").unlink()
    node = get_node_class("LoadAgentFile")()

    with pytest.raises(FileNotFoundError):
        node.execute(workspace_name="novel-a")


def test_save_agent_file_node_overwrites_content():
    workspace.create_workspace("novel-a")
    node = get_node_class("SaveAgentFile")()

    result = node.execute(workspace_name="novel-a", text="Nội dung mới")

    assert result == ()
    saved = workspace.get_workspace_path("novel-a", "agent.md").read_text(encoding="utf-8")
    assert saved == "Nội dung mới"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: FAIL (`KeyError: Unknown node type: LoadAgentFile`)

- [ ] **Step 3: Append to `server/nodes/translate.py`**

Add this import at the top of the file, alongside the existing one:

```python
from translation_core import load_agent_file, save_agent_file

from server import workspace
```

Append these two classes at the end of the file:

```python
@register_node("LoadAgentFile")
class LoadAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self, workspace_name: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "agent.md")
        return (load_agent_file(path),)


@register_node("SaveAgentFile")
class SaveAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, workspace_name: str, text: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "agent.md")
        save_agent_file(path, text)
        return ()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: PASS (all 4 tests in the file)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all pass (113 + 3 = 116).

- [ ] **Step 6: Commit**

```bash
git add server/nodes/translate.py tests/test_translate_nodes.py
git commit -m "feat: add LoadAgentFile/SaveAgentFile nodes"
```

---

### Task 5: `RAGQuery` / `SaveToRAG` nodes

**Files:**
- Modify: `server/nodes/translate.py`
- Modify: `tests/test_translate_nodes.py`

**Interfaces:**
- Consumes: `RAGStore` from `translation_core` (Sub-project B);
  `workspace.get_workspace_path` (Task 2); `NEEDS_WORKSPACE` (Task 1).
- Produces: registered node types `"RAGQuery"` (`RETURN_TYPES =
  ("RAG_EXAMPLES",)`, required input `text`, optional input `top_k`) and
  `"SaveToRAG"` (`RETURN_TYPES = ()`, required inputs `chapter_id`,
  `source_text`, `translated_text`). Both `NEEDS_WORKSPACE = True`.
  `RAGQuery`'s runtime output is a real `list[RAGExample]` — Task 6's
  `Translate` node consumes this same runtime type via its optional
  `rag_examples` input.

This task uses a real `RAGStore` (real ChromaDB + real embedding model),
same as Sub-project B's own tests — no mocking. The embedding model should
already be cached locally from Sub-project B's test runs, so this should
be fast; if not, the first run downloads it (~470MB, needs internet).

- [ ] **Step 1: Write the failing tests (append to `tests/test_translate_nodes.py`)**

```python
def test_save_to_rag_and_query_returns_saved_chapter():
    workspace.create_workspace("novel-a")
    save_node = get_node_class("SaveToRAG")()
    save_node.execute(
        workspace_name="novel-a",
        chapter_id="ch1",
        source_text="The dragon knight traveled to the misty mountain village.",
        translated_text="Hiệp sĩ rồng du hành đến ngôi làng núi mù sương.",
    )

    query_node = get_node_class("RAGQuery")()
    result = query_node.execute(
        workspace_name="novel-a",
        text="A knight rides toward a mountain village shrouded in fog.",
        top_k="1",
    )

    examples = result[0]
    assert len(examples) == 1
    assert examples[0].chapter_id == "ch1"
    assert examples[0].translated_text == "Hiệp sĩ rồng du hành đến ngôi làng núi mù sương."


def test_rag_query_on_empty_store_returns_empty_list():
    workspace.create_workspace("novel-a")
    node = get_node_class("RAGQuery")()

    result = node.execute(workspace_name="novel-a", text="anything")

    assert result == ([],)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: FAIL (`KeyError: Unknown node type: SaveToRAG`)

- [ ] **Step 3: Append to `server/nodes/translate.py`**

Add this import at the top, alongside the others:

```python
from translation_core import RAGStore
```

Append these two classes at the end of the file:

```python
@register_node("RAGQuery")
class RAGQuery(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("RAG_EXAMPLES",)
    RETURN_NAMES = ("rag_examples",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"text": ("STRING", {"default": ""})},
            "optional": {"top_k": ("STRING", {"default": "3"})},
        }

    def execute(self, workspace_name: str, text: str, top_k: str = "3") -> tuple:
        store = RAGStore(workspace.get_workspace_path(workspace_name, "rag_index"))
        examples = store.query(text, top_k=int(top_k))
        return (examples,)


@register_node("SaveToRAG")
class SaveToRAG(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "chapter_id": ("STRING", {"default": ""}),
                "source_text": ("STRING", {"default": ""}),
                "translated_text": ("STRING", {"default": ""}),
            }
        }

    def execute(
        self, workspace_name: str, chapter_id: str, source_text: str, translated_text: str
    ) -> tuple:
        store = RAGStore(workspace.get_workspace_path(workspace_name, "rag_index"))
        store.add_chapter(chapter_id, source_text, translated_text)
        return ()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: PASS (all 6 tests in the file)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all pass (116 + 2 = 118).

- [ ] **Step 6: Commit**

```bash
git add server/nodes/translate.py tests/test_translate_nodes.py
git commit -m "feat: add RAGQuery/SaveToRAG nodes"
```

---

### Task 6: `Translate` node

**Files:**
- Modify: `server/nodes/translate.py`
- Modify: `tests/test_translate_nodes.py`

**Interfaces:**
- Consumes: `translate_chunk`, `LLMProvider`, `RAGExample` from
  `translation_core` (Sub-project B). Does NOT use `NEEDS_WORKSPACE` —
  everything it needs arrives via node inputs (a `PROVIDER` value from
  Task 3's `Provider` node, a `RAG_EXAMPLES` value from Task 5's
  `RAGQuery` node, and plain `STRING` values), not via workspace context.
- Produces: registered node type `"Translate"`, `RETURN_TYPES =
  ("STRING",)`, required inputs `provider` (PROVIDER), `agent_instructions`
  (STRING), `source_text` (STRING); optional input `rag_examples`
  (RAG_EXAMPLES).

- [ ] **Step 1: Write the failing tests (append to `tests/test_translate_nodes.py`)**

Add this import at the top, alongside the others:

```python
from translation_core import LLMProvider, RAGExample
```

Append:

```python
class _RecordingProvider(LLMProvider):
    def __init__(self):
        self.received_messages = None

    def complete(self, messages, **kwargs):
        self.received_messages = messages
        return "bản dịch giả"


def test_translate_node_calls_translate_chunk_with_composed_inputs():
    node = get_node_class("Translate")()
    provider = _RecordingProvider()
    rag_examples = [
        RAGExample(
            chapter_id="ch1",
            source_text="A knight traveled to the village.",
            translated_text="Một hiệp sĩ đã đến ngôi làng.",
            distance=0.1,
        )
    ]

    result = node.execute(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        source_text="The knight drew his sword.",
        rag_examples=rag_examples,
    )

    assert result == ("bản dịch giả",)
    assert provider.received_messages[1] == {
        "role": "user",
        "content": "The knight drew his sword.",
    }


def test_translate_node_works_without_rag_examples():
    node = get_node_class("Translate")()
    provider = _RecordingProvider()

    result = node.execute(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        source_text="Hello world.",
    )

    assert result == ("bản dịch giả",)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: FAIL (`KeyError: Unknown node type: Translate`)

- [ ] **Step 3: Append to `server/nodes/translate.py`**

Add this import at the top, alongside the others:

```python
from translation_core import translate_chunk
```

Append this class at the end of the file:

```python
@register_node("Translate")
class Translate(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("translated_text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": ("PROVIDER", {}),
                "agent_instructions": ("STRING", {"default": ""}),
                "source_text": ("STRING", {"default": ""}),
            },
            "optional": {"rag_examples": ("RAG_EXAMPLES", {})},
        }

    def execute(
        self, provider, agent_instructions: str, source_text: str, rag_examples=None
    ) -> tuple:
        result = translate_chunk(provider, agent_instructions, rag_examples or [], source_text)
        return (result,)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_translate_nodes.py -v`
Expected: PASS (all 8 tests in the file)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all pass (118 + 2 = 120).

- [ ] **Step 6: Commit**

```bash
git add server/nodes/translate.py tests/test_translate_nodes.py
git commit -m "feat: add Translate node composing provider + RAG + agent instructions"
```

---

### Task 7: End-to-end verification via `run.bat` and a real browser

**Files:**
- None created/modified — this task is verification only.

**Interfaces:**
- Consumes: everything from Tasks 1-6, plus the existing `/api/nodes`,
  workspace REST endpoints, and `/ws/run/{workspace_name}` from
  Sub-project A.

This is the point of the whole plan: prove a user can actually drag these
6 new node types onto the canvas (via the sidebar palette from A1's UI
polish), wire them into the workflow the spec describes, and get a real
translated file out — not just pass unit tests in isolation.

- [ ] **Step 1: Start a local mock OpenAI-compatible server**

Since a real LLM API key/subscription isn't available in every
environment, verify against a tiny local stand-in server instead of a
real provider. Create a throwaway script (do not commit it — delete it in
Step 8) at, e.g., a temp path, with this content:

```python
import http.server
import json


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        request_body = json.loads(self.rfile.read(length))
        last_user_message = [m for m in request_body["messages"] if m["role"] == "user"][-1]
        translated = f"[DICH] {last_user_message['content']}"
        response = {"choices": [{"message": {"content": translated}}]}
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # keep test output quiet


http.server.HTTPServer(("127.0.0.1", 8999), Handler).serve_forever()
```

Run it in the background (e.g. `python mock_provider_server.py &` or as a
background process via your tooling) and confirm it's listening:
`curl -s -X POST http://127.0.0.1:8999/v1/chat/completions -d '{"messages":[{"role":"user","content":"hi"}]}'`
should return `{"choices": [{"message": {"content": "[DICH] hi"}}]}`.

- [ ] **Step 2: Start the real app server**

Run `run.bat` from the repo root (or `python -m uvicorn server.main:app
--host 127.0.0.1 --port 8000` directly if you need it in the foreground
for log visibility). Confirm `curl http://127.0.0.1:8000/api/health`
returns `{"status": "ok"}`, and confirm `curl http://127.0.0.1:8000/api/nodes`
now includes `Provider`, `LoadAgentFile`, `SaveAgentFile`, `RAGQuery`,
`SaveToRAG`, and `Translate` in its response.

- [ ] **Step 3: Create a workspace and prepare a source chapter file**

Via the browser (navigate to `http://127.0.0.1:8000/`) or via `curl -X
POST http://127.0.0.1:8000/api/workspaces -H "Content-Type:
application/json" -d '{"name":"demo-c"}'`, create a workspace named
`demo-c`. Confirm `workspaces/demo-c/agent.md` now exists with the seeded
content from Task 2. Create a source chapter file for the canvas's
`LoadTextFile` node to read, e.g. at
`workspaces/demo-c/chapters/ch1.txt` with content `"The dragon knight
traveled to the misty mountain village."`.

- [ ] **Step 4: Build the workflow on the canvas**

Open `http://127.0.0.1:8000/canvas.html?workspace=demo-c` in a real
browser (use browser automation tools if available in your environment,
per this project's established verification convention from Sub-project
A's Task 9/10 — otherwise do this manually and describe what you did).
Using the sidebar palette (drag-and-drop) and/or right-click menu, build
this graph:

- `LoadTextFile` — `path` = the chapters/ch1.txt file's full path
- `Provider` — `base_url` = `http://127.0.0.1:8999/v1`, `api_key` = `dummy`, `model` = `mock-model`
- `LoadAgentFile` — no widgets
- `RAGQuery` — connect `LoadTextFile`'s `text` output to `RAGQuery`'s `text` input; leave `top_k` at default `3`
- `Translate` — connect `Provider` → `provider`, `LoadAgentFile`'s `text` output → `agent_instructions`, `LoadTextFile`'s `text` output → `source_text`, `RAGQuery`'s `rag_examples` output → `rag_examples`
- `SaveTextFile` — connect `Translate`'s `translated_text` output → `text`; set `path` to the workspace's `output/ch1.txt` full path
- `SaveToRAG` — connect `chapter_id` to a literal `"ch1"`, `LoadTextFile`'s `text` output → `source_text`, `Translate`'s `translated_text` output → `translated_text`

Save the graph (Save button), reload the page, and confirm the graph
persisted (all 7 nodes and their connections still there).

- [ ] **Step 5: Run it and verify the result**

Click Run. Watch the status area and node colors update as each node
completes. Confirm:
- No `node_error`/`validation_error`/`runtime_error` events.
- `workspaces/demo-c/output/ch1.txt` now exists and contains `"[DICH] The
  dragon knight traveled to the misty mountain village."` (matching the
  mock server's canned transform, proving the whole chain — Provider's
  HTTP call, agent file load, RAG query, and translate_chunk's message
  composition — actually executed for real).
- `workspaces/demo-c/rag_index/` now exists and is non-empty (the
  ChromaDB persistence directory was created and written to).

- [ ] **Step 6: Verify a second run picks up RAG context**

Create a second chapter file `workspaces/demo-c/chapters/ch2.txt` with
similar content (e.g. `"A knight rides toward a mountain village shrouded
in fog."` — deliberately semantically close to ch1 so it ranks as a RAG
match). Change `LoadTextFile`'s `path` (and `SaveTextFile`'s output path,
and the literal `chapter_id`) to point at ch2, run again, and confirm it
completes without error. (The mock server ignores the RAG-examples content
in its canned reply, so this step is really about confirming the pipeline
runs error-free with a non-empty RAG index behind it — not about
inspecting the actual retrieved examples, which Task 5's unit tests
already cover directly.)

- [ ] **Step 7: Stop both servers**

Kill the mock provider server and the app server. Confirm nothing is left
listening on ports 8000/8999.

- [ ] **Step 8: Delete the throwaway mock server script**

It was never meant to be committed — remove it from wherever you created
it in Step 1.

- [ ] **Step 9: Report results**

No commit for this task (nothing was created/modified in the repo). Write
up what you did and observed — this becomes the task's report for review,
same as every other task, since it's verifying real end-to-end behavior
rather than adding a unit test.

---

## Self-Review Notes

- **Spec coverage:** Node breakdown (§1, 6 node types) → Tasks 3-6; new
  slot types PROVIDER/RAG_EXAMPLES (§2) → Tasks 3/5/6 (no code changes
  needed to `nodegen.js`, confirmed against its existing dynamic-slot
  logic which only special-cases `"STRING"`); `NEEDS_WORKSPACE` executor
  mechanism (§3) → Task 1; `get_workspace_path()` + agent.md seeding (§4)
  → Task 2; data flow / sample workflow → Task 7; error handling (no new
  mechanism, relies on A's existing per-node catch) → implicitly exercised
  by every task's tests plus Task 7's real run; testing section → matches
  each task's actual test approach. Out-of-scope items (template system,
  auto-glossary node, Anthropic/Gemini, api_key encryption, MCP) are
  correctly absent from every task.
- **Type consistency:** `NodeBase.NEEDS_WORKSPACE` (Task 1) is read via
  `node_cls.NEEDS_WORKSPACE` in the executor and set to `True` on exactly
  the four nodes that need it (Tasks 4-5), left at its `False` default on
  `Provider` and `Translate` (Tasks 3, 6) which need no workspace context.
  `get_workspace_path(name, *parts)` (Task 2) is called identically in
  Tasks 4 and 5 with `"agent.md"` and `"rag_index"` respectively.
  `translation_core`'s exact exported names (`ProviderConfig`,
  `create_provider`, `RAGStore`, `RAGExample`, `load_agent_file`,
  `save_agent_file`, `translate_chunk`, `LLMProvider`) are used exactly as
  defined in `translation_core/__init__.py` — verified against the actual
  installed file before writing this plan, not assumed from the spec.
- **Placeholder scan:** no TBD/TODO; every step has runnable code or an
  explicit manual-verification checklist (Task 7, consistent with how
  Sub-project A's equivalent end-to-end tasks were written).

---

Plan complete and saved to `docs/superpowers/plans/2026-09-08-node-integration-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
