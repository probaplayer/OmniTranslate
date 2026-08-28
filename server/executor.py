from collections import deque

from server.node_registry import get_node_class


class GraphValidationError(Exception):
    pass


def _build_dependency_map(nodes, links):
    node_ids = {n["id"] for n in nodes}
    dependents = {n["id"]: [] for n in nodes}
    dependency_count = {n["id"]: 0 for n in nodes}
    link_by_target = {}
    for link in links:
        from_node = link["from_node"]
        to_node = link["to_node"]
        if from_node not in node_ids:
            raise GraphValidationError(
                f"Link references unknown node id '{from_node}'"
            )
        if to_node not in node_ids:
            raise GraphValidationError(
                f"Link references unknown node id '{to_node}'"
            )
        dependents[from_node].append(to_node)
        dependency_count[to_node] += 1
        link_by_target[(to_node, link["to_input"])] = (
            from_node,
            link["from_output"],
        )
    return dependents, dependency_count, link_by_target


def topological_order(nodes, links) -> list:
    dependents, dependency_count, _ = _build_dependency_map(nodes, links)
    remaining = dict(dependency_count)
    queue = deque(node_id for node_id, count in remaining.items() if count == 0)
    order = []
    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for dependent_id in dependents[node_id]:
            remaining[dependent_id] -= 1
            if remaining[dependent_id] == 0:
                queue.append(dependent_id)
    if len(order) != len(nodes):
        raise GraphValidationError("Graph contains a cycle")
    return order


def validate_required_inputs(nodes, link_by_target) -> None:
    for node in nodes:
        try:
            node_cls = get_node_class(node["type"])
        except KeyError:
            raise GraphValidationError(
                f"Node {node['id']} references unknown node type '{node['type']}'"
            )
        required = node_cls.INPUT_TYPES().get("required", {})
        for input_name in required:
            has_literal = input_name in node.get("inputs", {})
            has_link = (node["id"], input_name) in link_by_target
            if not has_literal and not has_link:
                raise GraphValidationError(
                    f"Node {node['id']} ({node['type']}) missing required "
                    f"input '{input_name}'"
                )


def run_graph(nodes, links, on_event=None) -> dict:
    def emit(event):
        if on_event:
            on_event(event)

    dependents, _, link_by_target = _build_dependency_map(nodes, links)
    order = topological_order(nodes, links)
    validate_required_inputs(nodes, link_by_target)

    node_by_id = {n["id"]: n for n in nodes}
    outputs = {}
    skipped = set()

    for node_id in order:
        if node_id in skipped:
            outputs[node_id] = ()
            emit(
                {
                    "event": "node_error",
                    "node_id": node_id,
                    "message": "skipped: upstream dependency failed",
                }
            )
            skipped.update(dependents[node_id])
            continue

        node = node_by_id[node_id]
        kwargs = dict(node.get("inputs", {}))
        for (target_node, target_input), (from_node, from_output) in link_by_target.items():
            if target_node != node_id:
                continue
            from_node_type = node_by_id[from_node]["type"]
            out_names = list(get_node_class(from_node_type).RETURN_NAMES)
            kwargs[target_input] = outputs[from_node][out_names.index(from_output)]

        emit({"event": "node_started", "node_id": node_id})
        try:
            result = get_node_class(node["type"])().execute(**kwargs)
            outputs[node_id] = result
            emit({"event": "node_completed", "node_id": node_id, "outputs": result})
        except Exception as exc:
            outputs[node_id] = ()
            emit({"event": "node_error", "node_id": node_id, "message": str(exc)})
            skipped.update(dependents[node_id])

    emit({"event": "run_finished"})
    return outputs
