from translation_core import ProviderConfig, create_provider

from server.node_registry import NodeBase, register_node


@register_node("Provider")
class Provider(NodeBase):
    CATEGORY = "Translation"
    RETURN_TYPES = ("PROVIDER",)
    RETURN_NAMES = ("provider",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": ("STRING", {"default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "model": ("STRING", {"default": ""}),
            }
        }

    def execute(self, base_url: str, api_key: str, model: str) -> tuple:
        config = ProviderConfig(
            type="openai_compatible", base_url=base_url, api_key=api_key, model=model
        )
        return (create_provider(config),)
