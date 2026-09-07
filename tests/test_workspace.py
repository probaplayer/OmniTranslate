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


def test_create_workspace_with_path_traversal_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.create_workspace("../evil")


def test_create_workspace_with_forward_slash_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.create_workspace("evil/path")


def test_create_workspace_with_backslash_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.create_workspace("evil\\path")


def test_create_workspace_with_absolute_path_raises():
    abs_path = str(workspace.WORKSPACES_ROOT.parent / "evil")
    with pytest.raises(workspace.WorkspaceError):
        workspace.create_workspace(abs_path)


def test_open_workspace_with_non_dict_json_raises_clear_error():
    workspace.create_workspace("novel-a")
    graph_path = workspace.WORKSPACES_ROOT / "novel-a" / "graph.json"
    # Test with null (valid JSON but not a dict)
    graph_path.write_text("null", encoding="utf-8")
    with pytest.raises(workspace.WorkspaceError):
        workspace.open_workspace("novel-a")


def test_open_workspace_with_number_json_raises_clear_error():
    workspace.create_workspace("novel-a")
    graph_path = workspace.WORKSPACES_ROOT / "novel-a" / "graph.json"
    # Test with number (valid JSON but not a dict)
    graph_path.write_text("42", encoding="utf-8")
    with pytest.raises(workspace.WorkspaceError):
        workspace.open_workspace("novel-a")


def test_open_workspace_with_boolean_json_raises_clear_error():
    workspace.create_workspace("novel-a")
    graph_path = workspace.WORKSPACES_ROOT / "novel-a" / "graph.json"
    # Test with boolean (valid JSON but not a dict)
    graph_path.write_text("true", encoding="utf-8")
    with pytest.raises(workspace.WorkspaceError):
        workspace.open_workspace("novel-a")


def test_create_workspace_with_colon_windows_drive_bypass_raises():
    """Reject Windows drive-letter bypass like 'C:evil'."""
    with pytest.raises(workspace.WorkspaceError):
        workspace.create_workspace("C:evil")


def test_create_workspace_with_valid_underscore_name():
    """Valid names with underscores should work."""
    workspace.create_workspace("my_novel_1")
    assert workspace.list_workspaces() == ["my_novel_1"]
    graph = workspace.open_workspace("my_novel_1")
    assert graph["nodes"] == []
    assert graph["links"] == []


def test_create_workspace_with_valid_hyphen_name():
    """Valid names with hyphens should work."""
    workspace.create_workspace("test-123")
    assert workspace.list_workspaces() == ["test-123"]
    graph = workspace.open_workspace("test-123")
    assert graph["nodes"] == []
    assert graph["links"] == []


def test_workspaces_root_default_is_absolute():
    """WORKSPACES_ROOT must not depend on the process cwd.

    Loaded as a separate module instance so the autouse monkeypatch on the
    real `server.workspace` is left alone.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ws_fresh", workspace.__file__)
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)

    assert fresh.WORKSPACES_ROOT.is_absolute()
    assert fresh.WORKSPACES_ROOT.name == "workspaces"


def test_create_workspace_with_trailing_newline_raises_not_oserror():
    """`re.match` with `$` accepts a trailing newline; `fullmatch` must not."""
    with pytest.raises(workspace.InvalidWorkspaceNameError):
        workspace.create_workspace("ok\n")


def test_invalid_name_raises_invalid_workspace_name_error():
    with pytest.raises(workspace.InvalidWorkspaceNameError):
        workspace.open_workspace("bad name")


def test_corrupted_graph_raises_corrupt_workspace_error():
    workspace.create_workspace("novel-a")
    graph_path = workspace.WORKSPACES_ROOT / "novel-a" / "graph.json"
    graph_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(workspace.CorruptWorkspaceError):
        workspace.open_workspace("novel-a")


def test_missing_workspace_raises_base_error_not_a_subclass():
    with pytest.raises(workspace.WorkspaceError) as excinfo:
        workspace.open_workspace("does-not-exist")
    assert type(excinfo.value) is workspace.WorkspaceError


def test_save_graph_rejects_shape_without_nodes_and_links():
    workspace.create_workspace("novel-a")
    workspace.save_graph("novel-a", {"nodes": [{"id": "1"}], "links": []})

    with pytest.raises(workspace.InvalidGraphError):
        workspace.save_graph("novel-a", {})

    # The previously-saved valid graph must survive the rejected write.
    assert workspace.open_workspace("novel-a")["nodes"] == [{"id": "1"}]


def test_save_graph_rejects_non_dict_graph():
    workspace.create_workspace("novel-a")
    with pytest.raises(workspace.InvalidGraphError):
        workspace.save_graph("novel-a", ["not", "a", "dict"])
    assert workspace.open_workspace("novel-a")["nodes"] == []


def test_list_workspaces_skips_names_failing_validation():
    workspace.create_workspace("novel-a")
    (workspace.WORKSPACES_ROOT / "hand made").mkdir()
    assert workspace.list_workspaces() == ["novel-a"]
