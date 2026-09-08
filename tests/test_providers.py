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


@pytest.mark.parametrize("bad_content", [None, 123, {"text": "hi"}, ["a"]])
def test_complete_raises_provider_error_on_non_string_content(bad_content):
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": bad_content}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError) as excinfo:
        provider.complete([{"role": "user", "content": "hi"}])

    assert "content must be a str" in str(excinfo.value)


def test_http_error_message_redacts_api_key():
    api_key = "sk-supersecret123"

    def handler(request):
        return httpx.Response(401, text=f"Invalid credentials for Bearer {api_key}")

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key=api_key,
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError) as excinfo:
        provider.complete([{"role": "user", "content": "hi"}])

    message = str(excinfo.value)
    assert api_key not in message
    assert "***REDACTED***" in message
    assert "401" in message


def test_http_error_message_truncates_long_body():
    def handler(request):
        return httpx.Response(500, text="x" * 5000)

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError) as excinfo:
        provider.complete([{"role": "user", "content": "hi"}])

    message = str(excinfo.value)
    assert "...(truncated)" in message
    assert message.count("x") == 500


def test_http_error_message_redacts_key_before_truncating():
    """A key beyond the 500-char boundary must still be redacted, not truncated away."""
    api_key = "sk-tail-secret"

    def handler(request):
        return httpx.Response(500, text=("y" * 1000) + api_key)

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key=api_key,
        model="local-model",
        client=_client_with_handler(handler),
    )

    with pytest.raises(ProviderError) as excinfo:
        provider.complete([{"role": "user", "content": "hi"}])

    assert api_key not in str(excinfo.value)


def test_close_closes_the_client():
    client = _client_with_handler(lambda request: httpx.Response(200, json={}))
    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1", api_key="dummy", model="m", client=client
    )

    provider.close()

    assert client.is_closed


def test_context_manager_closes_the_client():
    client = _client_with_handler(
        lambda request: httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
    )

    with OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1", api_key="dummy", model="m", client=client
    ) as provider:
        assert provider.complete([{"role": "user", "content": "hi"}]) == "ok"
        assert not client.is_closed

    assert client.is_closed


def test_default_constructed_client_can_be_closed():
    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1", api_key="dummy", model="m"
    )

    provider.close()

    assert provider._client.is_closed


from translation_core.providers.factory import ProviderConfig, create_provider


def test_provider_config_repr_hides_api_key():
    config = ProviderConfig(type="x", base_url="y", api_key="secret", model="z")

    assert "secret" not in repr(config)
    # ...but the value is still usable by code.
    assert config.api_key == "secret"


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
