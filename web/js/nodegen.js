function registerDynamicNodeTypes(nodeMetadataList) {
  for (const meta of nodeMetadataList) {
    function DynamicNode() {
      const required = meta.input_types.required || {};
      const optional = meta.input_types.optional || {};
      const allInputs = Object.assign({}, required, optional);

      this.properties = {};
      for (const [inputName, spec] of Object.entries(allInputs)) {
        const inputType = spec[0];
        const config = spec[1] || {};
        this.addInput(inputName, inputType);
        this.properties[inputName] = config.default || "";
        if (inputType === "STRING") {
          this.addWidget("text", inputName, this.properties[inputName], (value) => {
            this.properties[inputName] = value;
          });
        }
      }

      meta.return_names.forEach((name, idx) => {
        this.addOutput(name, meta.return_types[idx]);
      });
    }

    DynamicNode.title = meta.type;
    DynamicNode.category = meta.category;
    DynamicNode.nodeType = meta.type;
    LiteGraph.registerNodeType(`${meta.category}/${meta.type}`, DynamicNode);
  }
}

// buildExecutionPayload reads node.properties (not widgets_values) as the
// source of truth: litegraph restores `properties` verbatim on configure(),
// while widget display sync after reload is a separate, non-blocking concern.
function buildExecutionPayload(graph) {
  const nodes = graph._nodes.map((n) => ({
    id: String(n.id),
    type: n.constructor.nodeType,
    inputs: Object.assign({}, n.properties),
  }));

  const links = [];
  for (const linkId in graph.links) {
    const link = graph.links[linkId];
    if (!link) continue;
    const originNode = graph.getNodeById(link.origin_id);
    const targetNode = graph.getNodeById(link.target_id);
    links.push({
      from_node: String(link.origin_id),
      from_output: originNode.outputs[link.origin_slot].name,
      to_node: String(link.target_id),
      to_input: targetNode.inputs[link.target_slot].name,
    });
  }

  return { nodes, links };
}
