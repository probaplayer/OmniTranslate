"""Translation core.

Public API — consumers (e.g. server/nodes) import from here:

    from translation_core import create_provider, ProviderConfig, GlossaryEntry, ...

``OpenAICompatibleProvider`` is deliberately not re-exported: it is one
concrete backend, while ``create_provider``/``ProviderConfig`` are the
intended generic entry point for constructing a provider.
"""

from translation_core.agent_file import load_agent_file, save_agent_file
from translation_core.chapters import ChapterRecord, get_recent, load_chapters, record_chapter, save_chapters
from translation_core.glossary import GlossaryEntry, find_relevant_entries, load_glossary, save_glossary
from translation_core.providers.base import LLMProvider, ProviderError
from translation_core.providers.factory import ProviderConfig, create_provider
from translation_core.translate import translate_chunk

__all__ = [
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
]
