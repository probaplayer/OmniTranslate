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


def create_provider(config: ProviderConfig) -> LLMProvider:
    if config.type == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=config.base_url, api_key=config.api_key, model=config.model
        )
    raise ProviderError(f"Unknown provider type: {config.type}")
