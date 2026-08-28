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
