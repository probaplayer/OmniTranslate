import pytest

from translation_core.glossary import GlossaryEntry
from translation_core.providers.base import LLMProvider
from translation_core.translate import translate_chunk


class RecordingProvider(LLMProvider):
    def __init__(self):
        self.received_messages = None

    def complete(self, messages, **kwargs):
        self.received_messages = messages
        return "bản dịch giả"


def test_translate_chunk_builds_system_prompt_with_glossary_entries():
    provider = RecordingProvider()
    entries = [
        GlossaryEntry(term="Long Khê", translation="Long Khê", note="hiệp sĩ rồng", chapter_id="ch1"),
    ]

    result = translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt, văn phong trang trọng.",
        glossary_entries=entries,
        source_text="Long Khê drew his sword.",
    )

    assert result == "bản dịch giả"
    system_prompt = provider.received_messages[0]["content"]
    assert provider.received_messages[0]["role"] == "system"
    assert "Dịch sang tiếng Việt" in system_prompt
    assert "Long Khê → Long Khê (hiệp sĩ rồng)" in system_prompt
    assert provider.received_messages[1] == {"role": "user", "content": "Long Khê drew his sword."}


def test_translate_chunk_without_glossary_entries_omits_the_section():
    provider = RecordingProvider()

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        glossary_entries=[],
        source_text="Hello world.",
    )

    assert "đã xác lập" not in provider.received_messages[0]["content"]


def test_translate_chunk_omits_note_parens_when_note_is_empty():
    provider = RecordingProvider()
    entries = [GlossaryEntry(term="龙王", translation="Long Vương", note="", chapter_id="ch1")]

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch.",
        glossary_entries=entries,
        source_text="src",
    )

    system_prompt = provider.received_messages[0]["content"]
    assert "龙王 → Long Vương" in system_prompt
    assert "()" not in system_prompt
