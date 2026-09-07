from translation_core.providers.base import LLMProvider
from translation_core.rag.store import RAGExample


def translate_chunk(
    provider: LLMProvider,
    agent_instructions: str,
    rag_examples: list[RAGExample],
    source_text: str,
) -> str:
    system_prompt = agent_instructions

    if rag_examples:
        examples_text = "\n\n".join(
            f"Nguồn: {example.source_text}\nBản dịch: {example.translated_text}"
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
