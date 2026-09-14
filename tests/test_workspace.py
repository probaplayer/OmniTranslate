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


def test_get_workspace_path_returns_path_under_workspace():
    workspace.create_workspace("novel-a")

    path = workspace.get_workspace_path("novel-a", "glossary.json")

    assert path == workspace.WORKSPACES_ROOT / "novel-a" / "glossary.json"


def test_get_workspace_path_validates_name():
    with pytest.raises(workspace.InvalidWorkspaceNameError):
        workspace.get_workspace_path("../evil", "agent.md")


def test_create_workspace_seeds_agent_file():
    workspace.create_workspace("novel-a")

    agent_path = workspace.get_workspace_path("novel-a", "agent.md")

    assert agent_path.exists()
    assert "Dịch sang tiếng Việt" in agent_path.read_text(encoding="utf-8")


def test_create_workspace_seeds_empty_glossary_file():
    workspace.create_workspace("novel-a")

    glossary_path = workspace.get_workspace_path("novel-a", "glossary.json")

    assert glossary_path.exists()
    assert json.loads(glossary_path.read_text(encoding="utf-8")) == {"entries": []}


def test_create_workspace_seeds_empty_chapters_file():
    workspace.create_workspace("novel-a")

    chapters_path = workspace.get_workspace_path("novel-a", "chapters.json")

    assert chapters_path.exists()
    assert json.loads(chapters_path.read_text(encoding="utf-8")) == {"chapters": []}


def test_validate_workspace_name_rejects_none_with_own_error():
    """None must not reach the regex and surface as a raw TypeError.

    run_graph defaults workspace_name to None, so a caller that omits it while
    the graph holds a NEEDS_WORKSPACE node lands here.
    """
    with pytest.raises(workspace.InvalidWorkspaceNameError) as exc_info:
        workspace._validate_workspace_name(None)
    assert "must be a string" in str(exc_info.value)
    assert "NoneType" in str(exc_info.value)


def test_get_workspace_path_with_none_raises_invalid_name_not_type_error():
    with pytest.raises(workspace.InvalidWorkspaceNameError):
        workspace.get_workspace_path(None, "agent.md")


def test_is_valid_workspace_name_is_total_for_non_strings():
    assert workspace._is_valid_workspace_name(None) is False
    assert workspace._is_valid_workspace_name(42) is False


def test_rename_workspace_moves_the_directory():
    workspace.create_workspace("novel-a")

    workspace.rename_workspace("novel-a", "novel-b")

    assert workspace.list_workspaces() == ["novel-b"]
    assert workspace.open_workspace("novel-b")["nodes"] == []


def test_rename_workspace_updates_config_name():
    workspace.create_workspace("novel-a")

    workspace.rename_workspace("novel-a", "novel-b")

    config = json.loads(
        workspace.get_workspace_path("novel-b", "config.json").read_text(encoding="utf-8")
    )
    assert config["name"] == "novel-b"


def test_rename_missing_workspace_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.rename_workspace("does-not-exist", "novel-b")


def test_rename_to_existing_name_raises():
    workspace.create_workspace("novel-a")
    workspace.create_workspace("novel-b")

    with pytest.raises(workspace.WorkspaceError):
        workspace.rename_workspace("novel-a", "novel-b")

    # Neither workspace was touched by the failed rename.
    assert set(workspace.list_workspaces()) == {"novel-a", "novel-b"}


def test_rename_workspace_rejects_invalid_new_name():
    workspace.create_workspace("novel-a")

    with pytest.raises(workspace.InvalidWorkspaceNameError):
        workspace.rename_workspace("novel-a", "bad name")


def test_duplicate_workspace_copies_graph_and_agent_file():
    workspace.create_workspace("novel-a", source_lang="ja", target_lang="vi")
    workspace.get_workspace_path("novel-a", "graph.json").write_text(
        json.dumps({"nodes": [{"id": "1"}], "links": []}), encoding="utf-8"
    )
    workspace.get_workspace_path("novel-a", "agent.md").write_text(
        "Hướng dẫn riêng cho truyện này", encoding="utf-8"
    )

    workspace.duplicate_workspace("novel-a", "novel-b")

    assert set(workspace.list_workspaces()) == {"novel-a", "novel-b"}
    copied_graph = workspace.open_workspace("novel-b")
    assert copied_graph["nodes"] == [{"id": "1"}]
    assert (
        workspace.get_workspace_path("novel-b", "agent.md").read_text(encoding="utf-8")
        == "Hướng dẫn riêng cho truyện này"
    )
    config = json.loads(
        workspace.get_workspace_path("novel-b", "config.json").read_text(encoding="utf-8")
    )
    assert config["source_lang"] == "ja"
    assert config["target_lang"] == "vi"


def test_duplicate_workspace_does_not_copy_data():
    workspace.create_workspace("novel-a")
    workspace.get_workspace_path("novel-a", "glossary.json").write_text(
        json.dumps({"entries": [{"term": "x"}]}), encoding="utf-8"
    )
    workspace.get_workspace_path("novel-a", "chapters.json").write_text(
        json.dumps({"chapters": [{"chapter_id": "ch1"}]}), encoding="utf-8"
    )
    (workspace.get_workspace_path("novel-a", "output") / "ch1.txt").write_text(
        "bản dịch", encoding="utf-8"
    )

    workspace.duplicate_workspace("novel-a", "novel-b")

    glossary = json.loads(
        workspace.get_workspace_path("novel-b", "glossary.json").read_text(encoding="utf-8")
    )
    assert glossary == {"entries": []}
    chapters = json.loads(
        workspace.get_workspace_path("novel-b", "chapters.json").read_text(encoding="utf-8")
    )
    assert chapters == {"chapters": []}
    assert workspace.list_output_files("novel-b") == []


def test_duplicate_missing_source_workspace_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.duplicate_workspace("does-not-exist", "novel-b")


def test_duplicate_workspace_to_existing_name_raises():
    workspace.create_workspace("novel-a")
    workspace.create_workspace("novel-b")

    with pytest.raises(workspace.WorkspaceError):
        workspace.duplicate_workspace("novel-a", "novel-b")


def test_duplicate_workspace_rejects_invalid_new_name():
    workspace.create_workspace("novel-a")

    with pytest.raises(workspace.InvalidWorkspaceNameError):
        workspace.duplicate_workspace("novel-a", "bad name")


def test_duplicate_workspace_survives_missing_graph_and_agent_file():
    """A source workspace whose graph.json/agent.md are missing (e.g.
    corrupted on disk by hand) must still produce a usable, empty-workflow
    duplicate rather than raising."""
    workspace.create_workspace("novel-a")
    workspace.get_workspace_path("novel-a", "graph.json").unlink()
    workspace.get_workspace_path("novel-a", "agent.md").unlink()

    workspace.duplicate_workspace("novel-a", "novel-b")

    assert workspace.open_workspace("novel-b") == {"nodes": [], "links": []}


def test_list_output_files_empty_for_new_workspace():
    workspace.create_workspace("novel-a")

    assert workspace.list_output_files("novel-a") == []


def test_list_output_files_missing_workspace_raises():
    with pytest.raises(workspace.WorkspaceError):
        workspace.list_output_files("does-not-exist")


def test_list_output_files_lists_nested_files_with_size_and_mtime():
    workspace.create_workspace("novel-a")
    output_dir = workspace.get_workspace_path("novel-a", "output")
    (output_dir / "ch1.txt").write_text("hello", encoding="utf-8")
    nested = output_dir / "sub"
    nested.mkdir()
    (nested / "ch2.txt").write_text("world!", encoding="utf-8")

    files = workspace.list_output_files("novel-a")

    assert [f["path"] for f in files] == ["ch1.txt", "sub/ch2.txt"]
    ch1 = next(f for f in files if f["path"] == "ch1.txt")
    assert ch1["size"] == 5
    assert isinstance(ch1["modified"], float)


def test_read_output_file_returns_content():
    workspace.create_workspace("novel-a")
    output_dir = workspace.get_workspace_path("novel-a", "output")
    (output_dir / "ch1.txt").write_text("nội dung", encoding="utf-8")

    assert workspace.read_output_file("novel-a", "ch1.txt") == "nội dung"


def test_read_output_file_missing_raises():
    workspace.create_workspace("novel-a")

    with pytest.raises(workspace.WorkspaceError):
        workspace.read_output_file("novel-a", "does-not-exist.txt")


def test_read_output_file_rejects_path_escaping_output_dir():
    workspace.create_workspace("novel-a")
    # A sibling file inside the workspace but outside output/ -- must not be
    # readable through the output-file endpoint.
    workspace.get_workspace_path("novel-a", "agent.md").write_text("secret", encoding="utf-8")

    with pytest.raises(workspace.InvalidOutputPathError):
        workspace.read_output_file("novel-a", "../agent.md")


def test_read_output_file_rejects_absolute_path_escape(tmp_path):
    workspace.create_workspace("novel-a")
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")

    with pytest.raises(workspace.InvalidOutputPathError):
        workspace.read_output_file("novel-a", str(outside))


def test_read_output_file_rejects_non_utf8_content():
    workspace.create_workspace("novel-a")
    output_dir = workspace.get_workspace_path("novel-a", "output")
    (output_dir / "binary.bin").write_bytes(b"\xff\xfe\x00\x01")

    with pytest.raises(workspace.NotTextFileError):
        workspace.read_output_file("novel-a", "binary.bin")


def test_delete_output_file_removes_it():
    workspace.create_workspace("novel-a")
    output_dir = workspace.get_workspace_path("novel-a", "output")
    (output_dir / "ch1.txt").write_text("hello", encoding="utf-8")

    workspace.delete_output_file("novel-a", "ch1.txt")

    assert workspace.list_output_files("novel-a") == []


def test_delete_output_file_missing_raises():
    workspace.create_workspace("novel-a")

    with pytest.raises(workspace.WorkspaceError):
        workspace.delete_output_file("novel-a", "does-not-exist.txt")


def test_delete_output_file_rejects_path_escaping_output_dir():
    workspace.create_workspace("novel-a")
    agent_path = workspace.get_workspace_path("novel-a", "agent.md")

    with pytest.raises(workspace.InvalidOutputPathError):
        workspace.delete_output_file("novel-a", "../agent.md")

    assert agent_path.exists()
