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
