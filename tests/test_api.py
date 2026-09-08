import json

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from server import main as server_main
from server import workspace
from server.main import app


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")


@pytest.fixture
def ws_workspace():
    """A real workspace on disk, named "any", for the /ws/run/{name} tests.

    ws_run refuses to run a graph against a workspace that does not exist --
    otherwise a typo'd name lets the RAG nodes materialise a phantom
    workspaces/<name>/rag_index/ tree -- so these tests need one to exist.
    """
    workspace.create_workspace("any")
    return "any"


def test_health_check_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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


def test_put_and_delete_missing_workspace_return_404():
    client = TestClient(app)
    assert (
        client.put(
            "/api/workspaces/does-not-exist/graph", json={"nodes": [], "links": []}
        ).status_code
        == 404
    )
    assert client.delete("/api/workspaces/does-not-exist").status_code == 404


def test_create_workspace_with_invalid_name_returns_400():
    client = TestClient(app)
    response = client.post("/api/workspaces", json={"name": "My Novel"})
    assert response.status_code == 400


def test_get_put_delete_with_invalid_name_return_400():
    client = TestClient(app)
    bad = "My%20Novel"
    assert client.get(f"/api/workspaces/{bad}").status_code == 400
    assert (
        client.put(
            f"/api/workspaces/{bad}/graph", json={"nodes": [], "links": []}
        ).status_code
        == 400
    )
    assert client.delete(f"/api/workspaces/{bad}").status_code == 400


def test_get_workspace_with_corrupted_graph_returns_422():
    client = TestClient(app)
    client.post("/api/workspaces", json={"name": "novel-a"})
    (workspace.WORKSPACES_ROOT / "novel-a" / "graph.json").write_text(
        "{not valid json", encoding="utf-8"
    )

    response = client.get("/api/workspaces/novel-a")
    assert response.status_code == 422


def test_put_graph_with_bad_shape_returns_400_and_keeps_previous_graph():
    client = TestClient(app)
    client.post("/api/workspaces", json={"name": "novel-a"})
    client.put("/api/workspaces/novel-a/graph", json={"nodes": [{"id": "1"}], "links": []})

    response = client.put("/api/workspaces/novel-a/graph", json={})
    assert response.status_code == 400

    reopened = client.get("/api/workspaces/novel-a")
    assert reopened.status_code == 200
    assert reopened.json()["nodes"] == [{"id": "1"}]


def test_websocket_run_streams_events_and_writes_file(tmp_path, ws_workspace):
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


def test_websocket_run_reports_validation_error(ws_workspace):
    client = TestClient(app)
    graph = {"nodes": [{"id": "1", "type": "LoadTextFile", "inputs": {}}], "links": []}

    with client.websocket_connect("/ws/run/any") as websocket:
        websocket.send_json({"graph": graph})
        event = websocket.receive_json()

    assert event["event"] == "validation_error"


def test_websocket_rejects_disallowed_origin(tmp_path):
    """A foreign page must not be able to drive the local server."""
    src = tmp_path / "in.txt"
    src.write_text("secret", encoding="utf-8")

    client = TestClient(app)
    graph = {
        "nodes": [{"id": "1", "type": "LoadTextFile", "inputs": {"path": str(src)}}],
        "links": [],
    }

    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/ws/run/any", headers={"origin": "http://evil.example.com"}
        ) as websocket:
            websocket.send_json({"graph": graph})
            websocket.receive_json()

    assert excinfo.value.code == 1008


def test_websocket_accepts_allowed_origin(tmp_path, ws_workspace):
    src = tmp_path / "in.txt"
    src.write_text("raw chapter", encoding="utf-8")

    client = TestClient(app)
    graph = {
        "nodes": [{"id": "1", "type": "LoadTextFile", "inputs": {"path": str(src)}}],
        "links": [],
    }

    events = []
    with client.websocket_connect(
        "/ws/run/any", headers={"origin": "http://127.0.0.1:8000"}
    ) as websocket:
        websocket.send_json({"graph": graph})
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["event"] == "run_finished":
                break

    assert [e["event"] for e in events] == [
        "node_started",
        "node_completed",
        "run_finished",
    ]


def test_websocket_run_reports_runtime_error_for_invalid_link_output(
    tmp_path, ws_workspace
):
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
            # "nonexistent" is not in LoadTextFile's RETURN_NAMES ("text",),
            # so run_graph raises a plain ValueError while assembling node 2's
            # kwargs -- before node 2's node_started is ever emitted, and
            # after node 1 has already fully completed.
            {
                "from_node": "1",
                "from_output": "nonexistent",
                "to_node": "2",
                "to_input": "text",
            }
        ],
    }

    events = []
    with client.websocket_connect("/ws/run/any") as websocket:
        websocket.send_json({"graph": graph})
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["event"] == "runtime_error":
                break

    event_names = [e["event"] for e in events]
    assert event_names == ["node_started", "node_completed", "runtime_error"]
    assert events[-1]["message"]


def _drain(websocket) -> list:
    """Collect every event up to and including the run's terminal event."""
    events = []
    while True:
        event = websocket.receive_json()
        events.append(event)
        if event["event"] in ("run_finished", "runtime_error", "validation_error"):
            return events


def test_websocket_run_with_provider_node_streams_serializable_events(ws_workspace):
    """Regression guard for the bug that killed the connection mid-run.

    The Provider node returns a real Python object, which `send_json` cannot
    serialize. Before executor's placeholder fix, `websocket.send_json()`
    raised inside ws_run's drain loop, the coroutine died, and the client
    never saw `node_error`/`run_finished` -- the run just hung. Every other
    test for these nodes calls `execute()` directly, so nothing covered this
    boundary. `json.dumps(events)` below is the actual assertion that would
    have failed.
    """
    client = TestClient(app)
    graph = {
        "nodes": [
            {
                "id": "1",
                "type": "Provider",
                "inputs": {
                    # Port 1 connect-refuses immediately: no real network, no
                    # waiting on a timeout.
                    "base_url": "http://127.0.0.1:1/v1",
                    "api_key": "sk-not-a-real-key",
                    "model": "test-model",
                },
            },
            {
                "id": "2",
                "type": "Translate",
                "inputs": {
                    "agent_instructions": "Translate to Vietnamese.",
                    "source_text": "hello",
                },
            },
        ],
        "links": [
            {
                "from_node": "1",
                "from_output": "provider",
                "to_node": "2",
                "to_input": "provider",
            }
        ],
    }

    with client.websocket_connect(f"/ws/run/{ws_workspace}") as websocket:
        websocket.send_json({"graph": graph})
        events = _drain(websocket)

    # The whole point: the streamed event log is JSON-serializable end to end.
    assert json.dumps(events)

    # The Provider node itself succeeds (constructing a provider makes no HTTP
    # call) and its object output is streamed as a bare type-name placeholder.
    provider_completed = next(
        e for e in events if e["event"] == "node_completed" and e["node_id"] == "1"
    )
    assert provider_completed["outputs"] == ["<OpenAICompatibleProvider>"]
    # The placeholder is a type name only, so the plaintext api_key the
    # provider object holds never reaches the wire.
    assert "sk-not-a-real-key" not in json.dumps(events)

    # Translate is the node that actually talks HTTP, so it is the one that
    # fails -- as a clean node_error, not a skip, and the run still finishes.
    translate_error = next(
        e for e in events if e["event"] == "node_error" and e["node_id"] == "2"
    )
    assert "provider request failed" in translate_error["message"].lower()
    assert [e["event"] for e in events] == [
        "node_started",
        "node_completed",
        "node_started",
        "node_error",
        "run_finished",
    ]


def test_websocket_run_with_rag_nodes_streams_serializable_events(ws_workspace):
    """Same regression guard for the RAG_EXAMPLES path.

    RAGQuery returns `list[RAGExample]` -- a list of dataclass instances,
    equally unserializable. Uses a real RAGStore (real chromadb + real
    embeddings), matching tests/test_translate_nodes.py, so it is slow.
    """
    client = TestClient(app)
    graph = {
        "nodes": [
            # SaveToRAG declares no outputs, so it cannot be wired to RAGQuery.
            # It is listed first instead: among nodes with no dependencies,
            # topological_order preserves declaration order, so this runs (and
            # populates the index) before RAGQuery reads it. RAGQuery must find
            # at least one row -- an empty list would serialize fine and defeat
            # the placeholder assertion below.
            {
                "id": "1",
                "type": "SaveToRAG",
                "inputs": {
                    "chapter_id": "ch1",
                    "source_text": "こんにちは世界",
                    "translated_text": "Xin chào thế giới",
                },
            },
            {
                "id": "2",
                "type": "Provider",
                "inputs": {
                    "base_url": "http://127.0.0.1:1/v1",
                    "api_key": "sk-not-a-real-key",
                    "model": "test-model",
                },
            },
            {
                "id": "3",
                "type": "RAGQuery",
                "inputs": {"text": "こんにちは世界", "top_k": "3"},
            },
            {
                "id": "4",
                "type": "Translate",
                "inputs": {
                    "agent_instructions": "Translate to Vietnamese.",
                    "source_text": "こんにちは世界",
                },
            },
        ],
        "links": [
            {
                "from_node": "2",
                "from_output": "provider",
                "to_node": "4",
                "to_input": "provider",
            },
            {
                "from_node": "3",
                "from_output": "rag_examples",
                "to_node": "4",
                "to_input": "rag_examples",
            },
        ],
    }

    with client.websocket_connect(f"/ws/run/{ws_workspace}") as websocket:
        websocket.send_json({"graph": graph})
        events = _drain(websocket)

    assert json.dumps(events)

    rag_completed = next(
        e for e in events if e["event"] == "node_completed" and e["node_id"] == "3"
    )
    assert rag_completed["outputs"] == ["<list>"]

    # Translate still fails on its HTTP call, and the run still finishes.
    assert any(
        e["event"] == "node_error" and e["node_id"] == "4" for e in events
    )
    assert events[-1]["event"] == "run_finished"


def test_websocket_run_against_missing_workspace_errors_and_creates_nothing():
    """A typo'd workspace name must not materialise a phantom directory.

    chromadb.PersistentClient auto-creates its parents, so a RAG node running
    against a nonexistent workspace would leave behind a
    workspaces/<name>/rag_index/ with no config.json or graph.json -- which
    then lists in the workspace picker and 422s when clicked.
    """
    client = TestClient(app)
    graph = {
        "nodes": [
            {
                "id": "1",
                "type": "RAGQuery",
                "inputs": {"text": "anything", "top_k": "3"},
            }
        ],
        "links": [],
    }

    with client.websocket_connect("/ws/run/typo-workspace") as websocket:
        websocket.send_json({"graph": graph})
        events = _drain(websocket)

    assert [e["event"] for e in events] == ["validation_error"]
    assert "does not exist" in events[0]["message"]
    assert not (workspace.WORKSPACES_ROOT / "typo-workspace").exists()
    assert workspace.list_workspaces() == []


def test_websocket_run_sends_terminal_event_when_an_event_cannot_be_sent(
    monkeypatch, ws_workspace
):
    """The drain loop must never leave the client waiting on nothing.

    executor replaces unserializable node outputs with placeholders, but that
    guard has an early return for a node whose execute() returns a bare
    non-tuple value, so an unsendable event is still reachable. If send_json
    raises unguarded, ws_run's coroutine dies before close(), and the client
    hangs with no run_finished. Simulate that by feeding the loop an event
    that cannot be serialized.
    """

    class _Unsendable:
        pass

    def fake_run_graph(nodes, links, on_event=None, workspace_name=None):
        on_event({"event": "node_started", "node_id": "1"})
        on_event(
            {"event": "node_completed", "node_id": "1", "outputs": _Unsendable()}
        )
        on_event({"event": "run_finished"})
        return {}

    monkeypatch.setattr(server_main, "run_graph", fake_run_graph)

    client = TestClient(app)
    with client.websocket_connect(f"/ws/run/{ws_workspace}") as websocket:
        websocket.send_json({"graph": {"nodes": [], "links": []}})
        events = _drain(websocket)

    # node_started got through; the unsendable one is reported instead of
    # silently killing the connection.
    assert [e["event"] for e in events] == ["node_started", "runtime_error"]
    assert "Failed to send event" in events[-1]["message"]
