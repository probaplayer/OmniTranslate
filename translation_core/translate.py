from translation_core.glossary import GlossaryEntry
from translation_core.providers.base import LLMProvider


def translate_chunk(
    provider: LLMProvider,
    agent_instructions: str,
    glossary_entries: list[GlossaryEntry],
    source_text: str,
) -> str:
    system_prompt = agent_instructions
    if glossary_entries:
        entries_text = "\n".join(
            f"- {e.term} → {e.translation}" + (f" ({e.note})" if e.note else "")
            for e in glossary_entries
        )
        system_prompt += "\n\n## Thuật ngữ/quan hệ đã xác lập (giữ nhất quán):\n" + entries_text
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": source_text},
    ]
    return provider.complete(messages)
