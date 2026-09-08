from translation_core.providers.base import LLMProvider
from translation_core.rag.store import RAGExample

_TRUNCATION_MARKER = "..."


def _truncate(text: str, max_chars: int) -> str:
    # A non-positive limit truncates to nothing rather than meaning
    # "unlimited" — an unset/zero caller-supplied limit must never widen the
    # prompt back to unbounded.
    limit = max(max_chars, 0)
    if len(text) > limit:
        return text[:limit] + _TRUNCATION_MARKER
    return text


def translate_chunk(
    provider: LLMProvider,
    agent_instructions: str,
    rag_examples: list[RAGExample],
    source_text: str,
    max_example_chars: int = 800,
) -> str:
    system_prompt = agent_instructions

    if rag_examples:
        # Each RAG entry is a whole chapter (thousands of tokens); interpolating
        # them in full would blow a local model's context window. Truncate for
        # the prompt only — RAGExample keeps its full values.
        examples_text = "\n\n".join(
            f"Nguồn: {_truncate(example.source_text, max_example_chars)}\n"
            f"Bản dịch: {_truncate(example.translated_text, max_example_chars)}"
            for example in rag_examples
        )
        system_prompt += (
            "\n\n## Ví dụ dịch trước đó (tham khảo văn phong/thuật ngữ):\n" + examples_text
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": source_text},
    ]
    return provider.complete(messages)
