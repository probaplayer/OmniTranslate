"""End-to-end composition tests: real RAGStore -> translate_chunk -> real provider.

Every other test file exercises one piece in isolation; these wire the real
objects together, which is the seam where a non-str provider response used to
slip through and corrupt the RAG index.
"""

import json

import httpx
import pytest

from translation_core import (
    LLMProvider,
    ProviderConfig,
    ProviderError,
    RAGExample,
    RAGStore,
    create_provider,
    load_agent_file,
    save_agent_file,
    translate_chunk,
)
from translation_core.providers.openai_compatible import OpenAICompatibleProvider

AGENT_INSTRUCTIONS = "Dịch sang tiếng Việt, giữ văn phong trang trọng."
SOURCE_TEXT = "The knight rode on through the fog toward the village gate."


def _real_store_with_one_chapter(tmp_path) -> RAGStore:
    store = RAGStore(persist_directory=tmp_path / "rag_index")
    store.add_chapter(
        chapter_id="ch1",
        source_text="The dragon knight Long Khe traveled to the misty mountain village.",
        translated_text="Long Khê du hành đến ngôi làng núi mù sương.",
    )
    return store


def test_full_composition_real_store_real_provider(tmp_path):
    store = _real_store_with_one_chapter(tmp_path)
    rag_examples = store.query("A knight rides toward a foggy mountain village.", top_k=1)

    assert len(rag_examples) == 1
    assert isinstance(rag_examples[0], RAGExample)
    assert rag_examples[0].chapter_id == "ch1"

    captured = {}

    def handler(request):
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Bản dịch thật"}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with provider:
        result = translate_chunk(
            provider=provider,
            agent_instructions=AGENT_INSTRUCTIONS,
            rag_examples=rag_examples,
            source_text=SOURCE_TEXT,
        )

    assert result == "Bản dịch thật"

    system_prompt = captured["json"]["messages"][0]["content"]
    assert captured["json"]["messages"][0]["role"] == "system"
    assert AGENT_INSTRUCTIONS in system_prompt
    # Content from the REAL RAG example must reach the prompt, not just a
    # type-compatible placeholder.
    assert "Long Khê du hành đến ngôi làng núi mù sương." in system_prompt
    assert "The dragon knight Long Khe" in system_prompt
    assert captured["json"]["messages"][1] == {"role": "user", "content": SOURCE_TEXT}


def test_full_composition_null_content_raises_provider_error(tmp_path):
    """A server sending JSON `"content": null` must fail loudly, not return None."""
    store = _real_store_with_one_chapter(tmp_path)
    rag_examples = store.query("A knight rides toward a foggy mountain village.", top_k=1)

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    provider = OpenAICompatibleProvider(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
        model="local-model",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with provider, pytest.raises(ProviderError) as excinfo:
        translate_chunk(
            provider=provider,
            agent_instructions=AGENT_INSTRUCTIONS,
            rag_examples=rag_examples,
            source_text=SOURCE_TEXT,
        )

    assert "content must be a str" in str(excinfo.value)

    # And the None never reaches the index even if a caller ignored the error.
    with pytest.raises(TypeError):
        store.add_chapter(chapter_id="ch2", source_text=SOURCE_TEXT, translated_text=None)


def test_public_api_exports_the_nine_documented_names():
    import translation_core

    expected = {
        "LLMProvider",
        "ProviderConfig",
        "ProviderError",
        "RAGExample",
        "RAGStore",
        "create_provider",
        "load_agent_file",
        "save_agent_file",
        "translate_chunk",
    }

    assert set(translation_core.__all__) == expected
    for name in expected:
        assert getattr(translation_core, name) is not None

    # Sanity-check the imported-at-module-top names are the real objects.
    assert RAGStore.__name__ == "RAGStore"
    assert issubclass(ProviderError, Exception)
    assert callable(create_provider)
    assert callable(translate_chunk)
    assert callable(load_agent_file)
    assert callable(save_agent_file)
    assert ProviderConfig.__name__ == "ProviderConfig"
    assert LLMProvider.__name__ == "LLMProvider"


def test_create_provider_from_top_level_import_works():
    provider = create_provider(
        ProviderConfig(
            type="openai_compatible",
            base_url="http://localhost:1234/v1",
            api_key="dummy",
            model="local-model",
        )
    )

    with provider:
        assert isinstance(provider, OpenAICompatibleProvider)
