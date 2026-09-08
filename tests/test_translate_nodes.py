from translation_core.providers.openai_compatible import OpenAICompatibleProvider

from server.node_registry import get_node_class
from server.nodes import translate  # noqa: F401  (triggers registration)


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
