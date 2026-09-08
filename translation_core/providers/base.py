from abc import ABC, abstractmethod


class ProviderError(Exception):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        raise NotImplementedError
