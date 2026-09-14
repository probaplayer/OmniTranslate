import json

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from pathlib import Path

from server import main as server_main
from server import workspace
from server import agent_templates
from server.main import app
from translation_core.glossary import GlossaryEntry, save_glossary


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")


@pytest.fixture
def ws_workspace():
    """A real workspace on disk, named "any", for the /ws/run/{name} tests.

    ws_run refuses to run a graph against a workspace that does not exist --
    otherwise a NEEDS_WORKSPACE node's own file I/O would surface a raw,
    unhelpful FileNotFoundError instead of a clear validation error -- so
    these tests need a real workspace to exist.
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


def test_patch_workspace_renames_it():
    client = TestClient(app)
    client.post("/api/workspaces", json={"name": "novel-a"})

    response = client.patch("/api/workspaces/novel-a", json={"new_name": "novel-b"})

    assert response.status_code == 200
    assert client.get("/api/workspaces").json()["workspaces"] == ["novel-b"]


def test_patch_missing_workspace_returns_404():
    client = TestClient(app)
    response = client.patch(
        "/api/workspaces/does-not-exist", json={"new_name": "novel-b"}
    )
    assert response.status_code == 404


def test_patch_workspace_to_existing_name_returns_409():
    client = TestClient(app)
    client.post("/api/workspaces", json={"name": "novel-a"})
    client.post("/api/workspaces", json={"name": "novel-b"})

    response = client.patch("/api/workspaces/novel-a", json={"new_name": "novel-b"})

    assert response.status_code == 409


def test_patch_workspace_with_invalid_new_name_returns_400():
    client = TestClient(app)
    client.post("/api/workspaces", json={"name": "novel-a"})

    response = client.patch("/api/workspaces/novel-a", json={"new_name": "bad name"})

    assert response.status_code == 400


def test_patch_workspace_with_invalid_old_name_returns_400_not_404():
    """A malformed old name must not be silently treated as 'not found' --
    list_workspaces() filters malformed names out of its own listing, which
    would make a naive 'is this name in the list' check return 404 instead
    of the 400 every other workspace endpoint gives for a bad name."""
    client = TestClient(app)
    bad = "My%20Novel"

    response = client.patch(f"/api/workspaces/{bad}", json={"new_name": "novel-b"})

    assert response.status_code == 400


class _FakeProvider:
    def __init__(self, should_fail=False, error_message="boom"):
        self.should_fail = should_fail
        self.error_message = error_message
        self.closed = False

    def complete(self, messages, **kwargs):
        if self.should_fail:
            from translation_core import ProviderError

            raise ProviderError(self.error_message)
        return "pong"

    def close(self):
        self.closed = True


def test_test_provider_returns_ok_on_success(monkeypatch):
    client = TestClient(app)
    fake = _FakeProvider(should_fail=False)
    monkeypatch.setattr(server_main, "create_provider", lambda config: fake)

    response = client.post(
        "/api/test-provider",
        json={"base_url": "http://localhost:1234/v1", "api_key": "k", "model": "m"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake.closed


def test_test_provider_passes_custom_timeout_through_to_provider_config(monkeypatch):
    client = TestClient(app)
    captured = {}

    def fake_create_provider(config):
        captured["config"] = config
        return _FakeProvider(should_fail=False)

    monkeypatch.setattr(server_main, "create_provider", fake_create_provider)

    response = client.post(
        "/api/test-provider",
        json={
            "base_url": "http://localhost:1234/v1",
            "api_key": "k",
            "model": "m",
            "timeout_seconds": "900",
        },
    )

    assert response.status_code == 200
    assert captured["config"].timeout == 900.0


def test_test_provider_falls_back_to_default_timeout_when_omitted(monkeypatch):
    client = TestClient(app)
    captured = {}

    def fake_create_provider(config):
        captured["config"] = config
        return _FakeProvider(should_fail=False)

    monkeypatch.setattr(server_main, "create_provider", fake_create_provider)

    response = client.post(
        "/api/test-provider",
        json={"base_url": "http://localhost:1234/v1", "api_key": "k", "model": "m"},
    )

    assert response.status_code == 200
    assert captured["config"].timeout == 600.0


def test_test_provider_returns_error_message_on_failure(monkeypatch):
    client = TestClient(app)
    fake = _FakeProvider(should_fail=True, error_message="Provider returned HTTP 401")
    monkeypatch.setattr(server_main, "create_provider", lambda config: fake)

    response = client.post(
        "/api/test-provider",
        json={"base_url": "http://localhost:1234/v1", "api_key": "wrong", "model": "m"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "401" in body["message"]
    assert fake.closed


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


def test_websocket_run_with_glossary_nodes_streams_serializable_events(ws_workspace):
    """Regression guard for the GLOSSARY_ENTRIES path.

    LookupGlossary returns `list[GlossaryEntry]` -- a list of dataclass
    instances, unserializable as-is -- the same shape of bug this guarded
    against for RAG_EXAMPLES before RAGQuery/SaveToRAG were replaced.
    """
    save_glossary(
        workspace.get_workspace_path(ws_workspace, "glossary.json"),
        [GlossaryEntry(term="世界", translation="thế giới", note="", chapter_id="ch0")],
    )

    client = TestClient(app)
    graph = {
        "nodes": [
            {"id": "1", "type": "LoadGlossary", "inputs": {}},
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
                "type": "LookupGlossary",
                "inputs": {"text": "こんにちは世界"},
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
                "from_node": "1",
                "from_output": "glossary_entries",
                "to_node": "3",
                "to_input": "glossary_entries",
            },
            {
                "from_node": "2",
                "from_output": "provider",
                "to_node": "4",
                "to_input": "provider",
            },
            {
                "from_node": "3",
                "from_output": "relevant_entries",
                "to_node": "4",
                "to_input": "glossary_entries",
            },
        ],
    }

    with client.websocket_connect(f"/ws/run/{ws_workspace}") as websocket:
        websocket.send_json({"graph": graph})
        events = _drain(websocket)

    assert json.dumps(events)

    lookup_completed = next(
        e for e in events if e["event"] == "node_completed" and e["node_id"] == "3"
    )
    assert lookup_completed["outputs"] == ["<list>"]

    assert any(e["event"] == "node_error" and e["node_id"] == "4" for e in events)
    assert events[-1]["event"] == "run_finished"


def test_websocket_run_against_missing_workspace_errors_and_creates_nothing():
    """A typo'd workspace name must not materialise a phantom directory.

    Any NEEDS_WORKSPACE node's file I/O (LoadGlossary here) must never run
    against a workspace name that was never validated to exist -- ws_run's
    upfront existence check must reject the run before any node's execute()
    does anything.
    """
    client = TestClient(app)
    graph = {
        "nodes": [{"id": "1", "type": "LoadGlossary", "inputs": {}}],
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


def test_get_agent_templates_returns_grouped_list(tmp_path, monkeypatch):
    (tmp_path / "vn").mkdir()
    (tmp_path / "vn" / "tien-hiep.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(agent_templates, "AGENTS_ROOT", tmp_path)

    client = TestClient(app)
    response = client.get("/api/agent-templates")

    assert response.status_code == 200
    assert response.json() == {"vn": ["tien-hiep"]}
