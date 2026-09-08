import pytest

from translation_core.providers.openai_compatible import OpenAICompatibleProvider

from server import workspace
from server.node_registry import get_node_class
from server.nodes import translate  # noqa: F401  (triggers registration)


@pytest.fixture(autouse=True)
def isolated_workspaces_root(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "WORKSPACES_ROOT", tmp_path / "workspaces")


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
