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

// Names of the node's inputs that have an incoming link. litegraph sets
// `input.link` to null when the slot is unconnected and to a link id when
// it is connected.
function linkedInputNames(node) {
  const names = new Set();
  for (const input of node.inputs || []) {
    if (input && input.link !== null && input.link !== undefined) {
      names.add(input.name);
    }
  }
  return names;
}

// buildExecutionPayload reads node.properties (not widgets_values) as the
// source of truth: litegraph restores `properties` verbatim on configure(),
// while widget display sync after reload is a separate, non-blocking concern.
function buildExecutionPayload(graph) {
  const nodes = graph._nodes.map((n) => {
    const linked = linkedInputNames(n);
    const inputs = {};
    for (const [name, value] of Object.entries(n.properties || {})) {
      // Every input's property is initialized to `config.default || ""`, so
      // without this an untouched widget would arrive as a literal "" and the
      // server's missing-required-input check could never fire. A blank
      // widget means "not provided" -- unless the slot is connected, in which
      // case the link supplies the real value at execution time and the
      // (unused) blank property is kept so nothing about the connection
      // changes.
      if (value === "" && !linked.has(name)) continue;
      inputs[name] = value;
    }
    return {
      id: String(n.id),
      type: n.constructor.nodeType,
      inputs,
    };
  });

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
