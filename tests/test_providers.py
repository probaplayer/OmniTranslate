import json

import httpx
import pytest

from translation_core.providers.base import LLMProvider, ProviderError
from translation_core.providers.openai_compatible import OpenAICompatibleProvider


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()


def test_provider_error_is_exception():
    assert issubclass(ProviderError, Exception)


def test_concrete_subclass_can_implement_complete():
    class EchoProvider(LLMProvider):
        def complete(self, messages, **kwargs):
            return messages[-1]["content"]

    provider = EchoProvider()
    result = provider.complete([{"role": "user", "content": "hello"}])

    assert result == "hello"


def _client_with_handler(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_complete_returns_message_content():
    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "Xin chào"}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    result = provider.complete([{"role": "user", "content": "hello"}])

    assert result == "Xin chào"


def test_complete_sends_expected_payload_and_headers():
    captured = {}

    def handler(request):
        captured["headers"] = request.headers
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="secret-key",
        model="local-model",
        client=_client_with_handler(handler),
    )

    provider.complete([{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}])

    assert captured["headers"]["authorization"] == "Bearer secret-key"
    assert captured["json"]["model"] == "local-model"
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]


def test_complete_raises_provider_error_on_http_status_error():
    def handler(request):
        return httpx.Response(500, text="internal error")

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError):
        provider.complete([{"role": "user", "content": "hi"}])


def test_complete_raises_provider_error_on_malformed_response():
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError):
        provider.complete([{"role": "user", "content": "hi"}])


def test_complete_raises_provider_error_on_network_failure():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError):
        provider.complete([{"role": "user", "content": "hi"}])


from translation_core.providers.factory import ProviderConfig, create_provider


def test_create_provider_openai_compatible():
    config = ProviderConfig(
        type="openai_compatible",
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
    )

    provider = create_provider(config)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://localhost:1234/v1"
    assert provider.model == "local-model"


def test_create_provider_unknown_type_raises():
    config = ProviderConfig(type="unknown", base_url="", api_key="", model="")

    with pytest.raises(ProviderError):
        create_provider(config)
