import pytest

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


def _long_example(source_len: int, translated_len: int) -> RAGExample:
    return RAGExample(
        chapter_id="ch1",
        source_text="S" * source_len,
        translated_text="T" * translated_len,
        distance=0.1,
    )


def test_translate_chunk_truncates_long_rag_examples_by_default():
    provider = RecordingProvider()
    example = _long_example(5000, 6000)

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch.",
        rag_examples=[example],
        source_text="src",
    )

    system_prompt = provider.received_messages[0]["content"]
    assert system_prompt.count("S") == 800
    assert system_prompt.count("T") == 800
    assert "..." in system_prompt
    # RAGExample itself keeps its full values.
    assert len(example.source_text) == 5000
    assert len(example.translated_text) == 6000


def test_translate_chunk_respects_custom_max_example_chars():
    provider = RecordingProvider()

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch.",
        rag_examples=[_long_example(100, 100)],
        source_text="src",
        max_example_chars=10,
    )

    system_prompt = provider.received_messages[0]["content"]
    assert system_prompt.count("S") == 10
    assert system_prompt.count("T") == 10


def test_translate_chunk_does_not_truncate_short_examples_or_source_text():
    provider = RecordingProvider()
    long_source = "U" * 5000

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch.",
        rag_examples=[_long_example(50, 50)],
        source_text=long_source,
    )

    system_prompt = provider.received_messages[0]["content"]
    assert system_prompt.count("S") == 50
    assert system_prompt.count("T") == 50
    assert "..." not in system_prompt
    # source_text is never truncated — only RAG examples are.
    assert provider.received_messages[1]["content"] == long_source


@pytest.mark.parametrize("max_example_chars", [0, -5])
def test_translate_chunk_non_positive_limit_truncates_to_nothing(max_example_chars):
    """A zero/unset limit must not mean 'unlimited' — that was the original bug."""
    provider = RecordingProvider()

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch.",
        rag_examples=[_long_example(5000, 5000)],
        source_text="src",
        max_example_chars=max_example_chars,
    )

    system_prompt = provider.received_messages[0]["content"]
    assert "S" not in system_prompt
    assert "T" not in system_prompt


def test_translate_chunk_truncates_each_example_independently():
    provider = RecordingProvider()

    translate_chunk(
        provider=provider,
        agent_instructions="Dịch.",
        rag_examples=[_long_example(2000, 5), _long_example(5, 2000)],
        source_text="src",
        max_example_chars=100,
    )

    system_prompt = provider.received_messages[0]["content"]
    # 100 (truncated) + 5 (kept whole) for each side.
    assert system_prompt.count("S") == 105
    assert system_prompt.count("T") == 105
