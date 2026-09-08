from typing import Any


class NodeBase:
    CATEGORY = "Uncategorized"
    RETURN_TYPES: tuple = ()
    RETURN_NAMES: tuple = ()
    NEEDS_WORKSPACE: bool = False

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {"required": {}, "optional": {}}

    def execute(self, **kwargs) -> tuple:
        raise NotImplementedError


_REGISTRY: dict[str, type[NodeBase]] = {}


def register_node(name: str):
    def decorator(node_cls: type[NodeBase]):
        if name in _REGISTRY:
            raise ValueError(f"Node type '{name}' already registered")
        _REGISTRY[name] = node_cls
        return node_cls

    return decorator


def get_node_class(name: str) -> type[NodeBase]:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown node type: {name}")
    return _REGISTRY[name]


def list_node_metadata() -> list[dict[str, Any]]:
    result = []
    for name, cls in _REGISTRY.items():
        return_names = list(cls.RETURN_NAMES) or list(cls.RETURN_TYPES)
        result.append(
            {
                "type": name,
                "category": cls.CATEGORY,
                "input_types": cls.INPUT_TYPES(),
                "return_types": list(cls.RETURN_TYPES),
                "return_names": return_names,
            }
        )
    return result
