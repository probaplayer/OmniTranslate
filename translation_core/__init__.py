"""Translation & RAG core (Sub-project B).

Public API — consumers (e.g. Sub-project C's nodes) import from here:

    from translation_core import create_provider, ProviderConfig, RAGStore, ...

``OpenAICompatibleProvider`` is deliberately not re-exported: it is one
concrete backend, while ``create_provider``/``ProviderConfig`` are the
intended generic entry point for constructing a provider.
"""

from translation_core.agent_file import load_agent_file, save_agent_file
from translation_core.providers.base import LLMProvider, ProviderError
from translation_core.providers.factory import ProviderConfig, create_provider
from translation_core.rag.store import RAGExample, RAGStore
from translation_core.translate import translate_chunk

__all__ = [
    "LLMProvider",
    "ProviderConfig",
    "ProviderError",
    "RAGExample",
    "RAGStore",
    "create_provider",
    "load_agent_file",
    "save_agent_file",
    "translate_chunk",
]
