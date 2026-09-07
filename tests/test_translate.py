from translation_core.providers.base import LLMProvider
from translation_core.rag.store import RAGExample
from translation_core.translate import translate_chunk


class RecordingProvider(LLMProvider):
    def __init__(self):
        self.received_messages = None

    def complete(self, messages, **kwargs):
        self.received_messages = messages
        return "bản dịch giả"


def test_translate_chunk_builds_system_prompt_with_rag_examples_and_calls_provider():
    provider = RecordingProvider()
    rag_examples = [
        RAGExample(
            chapter_id="ch1",
            source_text="A knight traveled to the village.",
            translated_text="Một hiệp sĩ đã đến ngôi làng.",
            distance=0.1,
        )
    ]

    result = translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt, văn phong trang trọng.",
        rag_examples=rag_examples,
        source_text="The knight drew his sword.",
    )

    assert result == "bản dịch giả"
    assert provider.received_messages[0]["role"] == "system"
    assert "Dịch sang tiếng Việt" in provider.received_messages[0]["content"]
    assert "A knight traveled to the village." in provider.received_messages[0]["content"]
    assert "Một hiệp sĩ đã đến ngôi làng." in provider.received_messages[0]["content"]
    assert provider.received_messages[1] == {"role": "user", "content": "The knight drew his sword."}


def test_translate_chunk_without_rag_examples_omits_examples_section():
    provider = RecordingProvider()

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch sang tiếng Việt.",
        rag_examples=[],
        source_text="Hello world.",
    )

    assert "Ví dụ dịch trước đó" not in provider.received_messages[0]["content"]
