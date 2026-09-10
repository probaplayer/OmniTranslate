import pytest

from server import agent_templates


@pytest.fixture(autouse=True)
def isolated_agents_root(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_templates, "AGENTS_ROOT", tmp_path / "agents")


def _seed(lang, genre, content="nội dung"):
    path = agent_templates.AGENTS_ROOT / lang / f"{genre}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_list_templates_on_missing_root_returns_empty_dict():
    assert agent_templates.list_templates() == {}


def test_list_templates_groups_by_language():
    _seed("vn", "tien-hiep")
    _seed("vn", "ngon-tinh")
    _seed("en", "tien-hiep")

    result = agent_templates.list_templates()

    assert result == {"vn": ["ngon-tinh", "tien-hiep"], "en": ["tien-hiep"]}


def test_resolve_template_path_returns_existing_file():
    path = _seed("vn", "tien-hiep", "nội dung mẫu")

    resolved = agent_templates.resolve_template_path("vn/tien-hiep")

    assert resolved == path
    assert resolved.read_text(encoding="utf-8") == "nội dung mẫu"


def test_resolve_template_path_rejects_malformed_string_no_slash():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("tien-hiep")


def test_resolve_template_path_rejects_too_many_parts():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("vn/tien-hiep/extra")


def test_resolve_template_path_rejects_path_traversal_payload():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("../etc")


def test_resolve_template_path_rejects_invalid_characters():
    with pytest.raises(ValueError):
        agent_templates.resolve_template_path("vn/tien hiep")


def test_resolve_template_path_raises_file_not_found_for_missing_file():
    with pytest.raises(FileNotFoundError):
        agent_templates.resolve_template_path("vn/does-not-exist")
