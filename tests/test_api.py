import pytest
from fastapi.testclient import TestClient

from server import workspace
from server.main import app


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")


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


def test_websocket_run_reports_runtime_error_for_invalid_link_output(tmp_path):
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
