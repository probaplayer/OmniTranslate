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
