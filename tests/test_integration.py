"""End-to-end composition tests: real glossary.py -> translate_chunk -> real provider.

Every other test file exercises one piece in isolation; these wire the real
objects together, the seam where a non-str provider response used to slip
through uncaught.
"""

import json

import httpx
import pytest

from translation_core import (
    GlossaryEntry,
    LLMProvider,
    ProviderConfig,
    ProviderError,
    create_provider,
    find_relevant_entries,
    load_agent_file,
    save_agent_file,
    translate_chunk,
)
from translation_core.providers.openai_compatible import OpenAICompatibleProvider

AGENT_INSTRUCTIONS = "Dịch sang tiếng Việt, giữ văn phong trang trọng."
SOURCE_TEXT = "Long Khê rode on through the fog toward the village gate."


def _relevant_glossary_entries():
    entries = [
        GlossaryEntry(term="Long Khê", translation="Long Khê", note="hiệp sĩ rồng", chapter_id="ch1"),
    ]
    return find_relevant_entries(entries, SOURCE_TEXT)


def test_full_composition_real_glossary_lookup_real_provider():
    glossary_entries = _relevant_glossary_entries()
    assert len(glossary_entries) == 1

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
            glossary_entries=glossary_entries,
            source_text=SOURCE_TEXT,
        )

    assert result == "Bản dịch thật"

    system_prompt = captured["json"]["messages"][0]["content"]
    assert captured["json"]["messages"][0]["role"] == "system"
    assert AGENT_INSTRUCTIONS in system_prompt
    assert "Long Khê → Long Khê (hiệp sĩ rồng)" in system_prompt
    assert captured["json"]["messages"][1] == {"role": "user", "content": SOURCE_TEXT}


def test_full_composition_null_content_raises_provider_error():
    """A server sending JSON `"content": null` must fail loudly, not return None."""

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
            glossary_entries=_relevant_glossary_entries(),
            source_text=SOURCE_TEXT,
        )

    assert "content must be a str" in str(excinfo.value)


def test_public_api_exports_the_sixteen_documented_names():
    import translation_core

    expected = {
        "ChapterRecord",
        "GlossaryEntry",
        "LLMProvider",
        "ProviderConfig",
        "ProviderError",
        "create_provider",
        "find_relevant_entries",
        "get_recent",
        "load_agent_file",
        "load_chapters",
        "load_glossary",
        "record_chapter",
        "save_agent_file",
        "save_chapters",
        "save_glossary",
        "translate_chunk",
    }

    assert set(translation_core.__all__) == expected
    for name in expected:
        assert getattr(translation_core, name) is not None

    assert issubclass(ProviderError, Exception)
    assert callable(create_provider)
    assert callable(translate_chunk)
    assert callable(load_agent_file)
    assert callable(save_agent_file)
    assert ProviderConfig.__name__ == "ProviderConfig"
    assert LLMProvider.__name__ == "LLMProvider"
    assert GlossaryEntry.__name__ == "GlossaryEntry"


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
