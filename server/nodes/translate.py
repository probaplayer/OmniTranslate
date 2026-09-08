from translation_core import ProviderConfig, RAGStore, create_provider, load_agent_file, save_agent_file

from server import workspace
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


@register_node("LoadAgentFile")
class LoadAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self, workspace_name: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "agent.md")
        return (load_agent_file(path),)


@register_node("SaveAgentFile")
class SaveAgentFile(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, workspace_name: str, text: str) -> tuple:
        path = workspace.get_workspace_path(workspace_name, "agent.md")
        save_agent_file(path, text)
        return ()


@register_node("RAGQuery")
class RAGQuery(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("RAG_EXAMPLES",)
    RETURN_NAMES = ("rag_examples",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"text": ("STRING", {"default": ""})},
            "optional": {"top_k": ("STRING", {"default": "3"})},
        }

    def execute(self, workspace_name: str, text: str, top_k: str = "3") -> tuple:
        store = RAGStore(workspace.get_workspace_path(workspace_name, "rag_index"))
        examples = store.query(text, top_k=int(top_k))
        return (examples,)


@register_node("SaveToRAG")
class SaveToRAG(NodeBase):
    CATEGORY = "Translation"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "chapter_id": ("STRING", {"default": ""}),
                "source_text": ("STRING", {"default": ""}),
                "translated_text": ("STRING", {"default": ""}),
            }
        }

    def execute(
        self, workspace_name: str, chapter_id: str, source_text: str, translated_text: str
    ) -> tuple:
        store = RAGStore(workspace.get_workspace_path(workspace_name, "rag_index"))
        store.add_chapter(chapter_id, source_text, translated_text)
        return ()
