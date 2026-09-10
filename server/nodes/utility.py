from pathlib import Path

from server.node_registry import NodeBase, register_node


@register_node("LoadTextFile")
class LoadTextFile(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"path": ("STRING", {"default": "", "widget": "path"})}}

    def execute(self, path: str) -> tuple:
        content = Path(path).read_text(encoding="utf-8")
        return (content,)


@register_node("SaveTextFile")
class SaveTextFile(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": ""}),
                "path": ("STRING", {"default": "", "widget": "path"}),
            }
        }

    def execute(self, text: str, path: str) -> tuple:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return ()


@register_node("TextPreview")
class TextPreview(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, text: str) -> tuple:
        return ()


@register_node("Note")
class Note(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, text: str) -> tuple:
        return ()


@register_node("TextInput")
class TextInput(NodeBase):
    CATEGORY = "Utility"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"default": ""})}}

    def execute(self, text: str) -> tuple:
        return (text,)
