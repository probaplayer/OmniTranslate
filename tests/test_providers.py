import pytest

from translation_core.providers.base import LLMProvider, ProviderError


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
