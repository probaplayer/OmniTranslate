const NODE_TYPE_META = {
  LoadTextFile: { icon: "▤", color: "#7ea6c9" },
  SaveTextFile: { icon: "⤓", color: "#9b8fc4" },
  TextPreview: { icon: "◐", color: "#8d949e" },
  Note: { icon: "✎", color: "#8d949e" },
  Provider: { icon: "✦", color: "#7fb98a" },
  LoadAgentFile: { icon: "◈", color: "#d9a44c" },
  SaveAgentFile: { icon: "◆", color: "#d9a44c" },
  RAGQuery: { icon: "◎", color: "#c98a7e" },
  SaveToRAG: { icon: "◉", color: "#c98a7e" },
  Translate: { icon: "⇄", color: "#7fb98a" },
};
const NODE_TYPE_META_FALLBACK = { icon: "●", color: "#767d88" };

const NODE_HEADER_HEIGHT = 20;
const NODE_FOOTER_HEIGHT = 22;

const RUN_STATUS_COLOR = {
  idle: "#6b7280",
  running: "#d9a44c",
  done: "#7fb98a",
  error: "#d97070",
};
const RUN_STATUS_KEY = {
  idle: "stIdle",
  running: "stRunning",
  done: "stDone",
  error: "stError",
};

function formatClockTime(ms) {
  const d = new Date(ms);
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
}

function registerDynamicNodeTypes(nodeMetadataList) {
  for (const meta of nodeMetadataList) {
    const typeMeta = NODE_TYPE_META[meta.type] || NODE_TYPE_META_FALLBACK;

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
      }

      meta.return_names.forEach((name, idx) => {
        this.addOutput(name, meta.return_types[idx]);
      });

      this.boxcolor = typeMeta.color;
      this._runStatus = "idle";
      this._runStatusAt = null;
    }

    DynamicNode.title = meta.type;
    DynamicNode.category = meta.category;
    DynamicNode.nodeType = meta.type;
    DynamicNode.slot_start_y = NODE_HEADER_HEIGHT;

    DynamicNode.prototype.computeSize = function (out) {
      const size = LiteGraph.LGraphNode.prototype.computeSize.call(this, out);
      size[1] += NODE_FOOTER_HEIGHT;
      return size;
    };

    DynamicNode.prototype.onDrawForeground = function (ctx) {
      if (this.flags.collapsed) return;
      const tm = NODE_TYPE_META[this.constructor.nodeType] || NODE_TYPE_META_FALLBACK;
      const w = this.size[0];
      const h = this.size[1];

      ctx.save();

      // Header row: icon + uppercase type label, in the type's color.
      ctx.fillStyle = tm.color;
      ctx.font = "10px 'IBM Plex Mono', monospace";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(`${tm.icon} ${nodeTypeLabel(this.constructor.nodeType)}`, 8, NODE_HEADER_HEIGHT / 2);

      // Footer row: separator + status dot + status text + timestamp meta.
      const footerY = h - NODE_FOOTER_HEIGHT;
      ctx.strokeStyle = "rgba(255,255,255,0.06)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, footerY);
      ctx.lineTo(w, footerY);
      ctx.stroke();

      const dotY = footerY + NODE_FOOTER_HEIGHT / 2;
      const statusColor = RUN_STATUS_COLOR[this._runStatus] || RUN_STATUS_COLOR.idle;
      ctx.fillStyle = statusColor;
      ctx.beginPath();
      ctx.arc(10, dotY, 3, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = statusColor;
      ctx.font = "10px 'IBM Plex Mono', monospace";
      ctx.textAlign = "left";
      ctx.fillText(t(RUN_STATUS_KEY[this._runStatus] || RUN_STATUS_KEY.idle), 18, dotY);

      if (this._runStatusAt && (this._runStatus === "done" || this._runStatus === "error")) {
        ctx.fillStyle = "#6f7681";
        ctx.textAlign = "right";
        ctx.fillText(formatClockTime(this._runStatusAt), w - 8, dotY);
      }

      ctx.restore();
    };

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
