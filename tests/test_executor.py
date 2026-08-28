import pytest

from server.executor import GraphValidationError, run_graph, topological_order
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
