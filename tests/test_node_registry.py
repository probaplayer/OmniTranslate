import pytest

from server.node_registry import (
    NodeBase,
    get_node_class,
    list_node_metadata,
    register_node,
)


def test_register_and_get_node_class():
    @register_node("TestNodeA")
    class TestNodeA(NodeBase):
        CATEGORY = "Test"
        RETURN_TYPES = ("STRING",)
        RETURN_NAMES = ("out",)

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("STRING", {"default": ""})}}

        def execute(self, value):
            return (value,)

    assert get_node_class("TestNodeA") is TestNodeA


def test_register_duplicate_name_raises():
    @register_node("TestNodeB")
    class TestNodeB(NodeBase):
        pass

    with pytest.raises(ValueError):
        @register_node("TestNodeB")
        class TestNodeBAgain(NodeBase):
            pass


def test_get_unknown_node_class_raises():
    with pytest.raises(KeyError):
        get_node_class("DoesNotExist")


def test_list_node_metadata_includes_registered_node():
    @register_node("TestNodeC")
    class TestNodeC(NodeBase):
        CATEGORY = "Test"
        RETURN_TYPES = ("STRING",)
        RETURN_NAMES = ("out",)

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("STRING", {"default": "x"})}}

        def execute(self, value):
            return (value,)

    metadata = list_node_metadata()
    entry = next(m for m in metadata if m["type"] == "TestNodeC")
    assert entry["category"] == "Test"
    assert entry["return_types"] == ["STRING"]
    assert entry["return_names"] == ["out"]
    assert entry["input_types"]["required"]["value"][0] == "STRING"
