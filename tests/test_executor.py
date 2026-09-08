import pytest

from server.executor import (
    MAX_EVENT_STRING_CHARS,
    GraphValidationError,
    run_graph,
    topological_order,
)
from server.node_registry import NodeBase, register_node
from server.nodes import utility  # noqa: F401


@register_node("_TestAdd")
class _TestAdd(NodeBase):
    CATEGORY = "Test"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("out",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("STRING", {"default": ""})}}

    def execute(self, value):
        return (value + "!",)


@register_node("_TestFail")
class _TestFail(NodeBase):
    CATEGORY = "Test"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("out",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"value": ("STRING", {"default": ""})}}

    def execute(self, value):
        raise RuntimeError("boom")


def test_topological_order_simple_chain():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}},
             {"id": "2", "type": "_TestAdd", "inputs": {"value": "b"}}]
    links = [{"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"}]
    assert topological_order(nodes, links) == ["1", "2"]


def test_topological_order_detects_cycle():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {}},
             {"id": "2", "type": "_TestAdd", "inputs": {}}]
    links = [
        {"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"},
        {"from_node": "2", "from_output": "out", "to_node": "1", "to_input": "value"},
    ]
    with pytest.raises(GraphValidationError):
        topological_order(nodes, links)


def test_run_graph_missing_required_input_raises():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {}}]
    with pytest.raises(GraphValidationError):
        run_graph(nodes, [])


def test_run_graph_chains_output_to_input():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}},
             {"id": "2", "type": "_TestAdd", "inputs": {"value": "unused"}}]
    links = [{"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"}]

    outputs = run_graph(nodes, links)

    assert outputs["1"] == ("a!",)
    assert outputs["2"] == ("a!!",)


def test_run_graph_error_skips_downstream_but_not_independent_branch():
    nodes = [
        {"id": "1", "type": "_TestFail", "inputs": {"value": "a"}},
        {"id": "2", "type": "_TestAdd", "inputs": {"value": "unused"}},
        {"id": "3", "type": "_TestAdd", "inputs": {"value": "independent"}},
    ]
    links = [{"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"}]

    events = []
    outputs = run_graph(nodes, links, on_event=events.append)

    assert outputs["3"] == ("independent!",)
    error_events = [e for e in events if e["event"] == "node_error"]
    assert {e["node_id"] for e in error_events} == {"1", "2"}
    assert any(e["event"] == "run_finished" for e in events)


def test_run_graph_writes_file_via_real_utility_nodes(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("raw chapter", encoding="utf-8")
    dst = tmp_path / "out.txt"

    nodes = [
        {"id": "1", "type": "LoadTextFile", "inputs": {"path": str(src)}},
        {"id": "2", "type": "SaveTextFile", "inputs": {"path": str(dst)}},
    ]
    links = [{"from_node": "1", "from_output": "text", "to_node": "2", "to_input": "text"}]

    run_graph(nodes, links)

    assert dst.read_text(encoding="utf-8") == "raw chapter"


def test_run_graph_unregistered_node_type_raises_gracefully():
    nodes = [{"id": "1", "type": "UnknownNodeType", "inputs": {}}]
    with pytest.raises(GraphValidationError) as exc_info:
        run_graph(nodes, [])
    assert "unknown node type" in str(exc_info.value).lower()


def test_run_graph_skipped_node_has_output_entry():
    nodes = [
        {"id": "1", "type": "_TestFail", "inputs": {"value": "a"}},
        {"id": "2", "type": "_TestAdd", "inputs": {"value": "unused"}},
    ]
    links = [{"from_node": "1", "from_output": "out", "to_node": "2", "to_input": "value"}]

    outputs = run_graph(nodes, links)

    # Verify that skipped node 2 has an entry in outputs dict (empty tuple)
    assert "2" in outputs
    assert outputs["2"] == ()
    # Verify that error node 1 also has an entry
    assert "1" in outputs
    assert outputs["1"] == ()


def test_run_graph_dangling_link_reference_raises_gracefully():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}}]
    links = [{"from_node": "1", "from_output": "out", "to_node": "nonexistent", "to_input": "value"}]
    with pytest.raises(GraphValidationError) as exc_info:
        run_graph(nodes, links)
    assert "unknown node id" in str(exc_info.value).lower()


def test_run_graph_dangling_link_source_raises_gracefully():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}}]
    links = [{"from_node": "nonexistent", "from_output": "out", "to_node": "1", "to_input": "value"}]
    with pytest.raises(GraphValidationError) as exc_info:
        run_graph(nodes, links)
    assert "unknown node id" in str(exc_info.value).lower()


def test_node_completed_event_truncates_long_string_but_outputs_dict_does_not():
    long_value = "x" * (MAX_EVENT_STRING_CHARS + 250)
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": long_value}}]

    events = []
    outputs = run_graph(nodes, [], on_event=events.append)

    full_value = long_value + "!"
    # The function's return value keeps the full text for internal use.
    assert outputs["1"] == (full_value,)

    completed = next(e for e in events if e["event"] == "node_completed")
    streamed = completed["outputs"][0]
    assert streamed != full_value
    assert streamed.startswith(full_value[:MAX_EVENT_STRING_CHARS])
    assert streamed.endswith(f"...(truncated, {len(full_value)} chars total)")
    assert len(streamed) < len(full_value)


def test_node_completed_event_leaves_short_string_untouched():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "short"}}]

    events = []
    outputs = run_graph(nodes, [], on_event=events.append)

    completed = next(e for e in events if e["event"] == "node_completed")
    assert completed["outputs"] == ("short!",)
    assert outputs["1"] == ("short!",)


@register_node("_TestNeedsWorkspace")
class _TestNeedsWorkspace(NodeBase):
    CATEGORY = "Test"
    NEEDS_WORKSPACE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("out",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self, workspace_name):
        return (workspace_name,)


def test_run_graph_injects_workspace_name_for_flagged_nodes():
    nodes = [{"id": "1", "type": "_TestNeedsWorkspace", "inputs": {}}]

    outputs = run_graph(nodes, [], workspace_name="my-novel")

    assert outputs["1"] == ("my-novel",)


def test_run_graph_does_not_inject_workspace_name_for_normal_nodes():
    nodes = [{"id": "1", "type": "_TestAdd", "inputs": {"value": "a"}}]

    outputs = run_graph(nodes, [], workspace_name="my-novel")

    assert outputs["1"] == ("a!",)


class _NonSerializableThing:
    """A plain object with no __repr__/json support -- mimics LLMProvider."""

    def __init__(self, label):
        self.label = label


@register_node("_TestReturnsNonSerializable")
class _TestReturnsNonSerializable(NodeBase):
    CATEGORY = "Test"
    RETURN_TYPES = ("OBJECT",)
    RETURN_NAMES = ("out",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    def execute(self):
        return (_NonSerializableThing("provider-instance"),)


def test_node_completed_event_replaces_non_serializable_value_with_placeholder():
    nodes = [{"id": "1", "type": "_TestReturnsNonSerializable", "inputs": {}}]

    events = []
    outputs = run_graph(nodes, [], on_event=events.append)

    completed = next(e for e in events if e["event"] == "node_completed")
    streamed = completed["outputs"][0]
    assert isinstance(streamed, str)
    assert "_NonSerializableThing" in streamed


def test_run_graph_returned_outputs_keep_real_non_serializable_object():
    nodes = [{"id": "1", "type": "_TestReturnsNonSerializable", "inputs": {}}]

    events = []
    outputs = run_graph(nodes, [], on_event=events.append)

    real_value = outputs["1"][0]
    assert isinstance(real_value, _NonSerializableThing)
    assert real_value.label == "provider-instance"
