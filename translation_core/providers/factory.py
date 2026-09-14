from dataclasses import dataclass, field

from translation_core.providers.base import LLMProvider, ProviderError
from translation_core.providers.openai_compatible import OpenAICompatibleProvider


@dataclass
class ProviderConfig:
    type: str
    base_url: str
    # repr=False so a traceback or diagnostic payload that reprs a config
    # never leaks the key in cleartext.
    api_key: str = field(repr=False)
    model: str
    # A real chapter translated by a local model can legitimately take much
    # longer than a typical HTTP default (httpx's own default is 5s; this
    # codebase's old hardcoded value was 60s) -- both are far too short for
    # local LLM inference over a full chapter + glossary + agent prompt, so
    # default to a generous ceiling rather than a network-API-sized one.
    timeout: float = 600.0


def create_provider(config: ProviderConfig) -> LLMProvider:
    if config.type == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            timeout=config.timeout,
        )
    raise ProviderError(f"Unknown provider type: {config.type}")
