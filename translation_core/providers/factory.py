from dataclasses import dataclass

from translation_core.providers.base import LLMProvider, ProviderError
from translation_core.providers.openai_compatible import OpenAICompatibleProvider


@dataclass
class ProviderConfig:
    type: str
    base_url: str
    api_key: str
    model: str


def create_provider(config: ProviderConfig) -> LLMProvider:
    if config.type == "openai_compatible":
        return OpenAICompatibleProvider(
            base_url=config.base_url, api_key=config.api_key, model=config.model
        )
    raise ProviderError(f"Unknown provider type: {config.type}")
