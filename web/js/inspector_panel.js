let inspectorNodeMetadata = {};
let inspectorGraph = null;
let inspectorWorkspaceName = null;
let inspectorSelectedNode = null;

function initInspectorPanel(nodeMetadataList, graph, canvas, workspaceName) {
  inspectorGraph = graph;
  inspectorWorkspaceName = workspaceName;
  inspectorNodeMetadata = {};
  for (const meta of nodeMetadataList) {
    inspectorNodeMetadata[meta.type] = meta;
  }

  canvas.onNodeSelected = (node) => {
    inspectorSelectedNode = node;
    renderInspector();
  };
  canvas.onNodeDeselected = () => {
    inspectorSelectedNode = null;
    renderInspector();
  };

  renderInspector();
}

function renderInspector() {
  const panel = document.getElementById("inspector-panel");
  if (!panel) return;
  panel.innerHTML = "";

  if (!inspectorSelectedNode) {
    const empty = document.createElement("p");
    empty.className = "inspector-empty";
    empty.textContent = t("inspectorEmpty");
    panel.appendChild(empty);
    return;
  }

  const node = inspectorSelectedNode;
  const meta = inspectorNodeMetadata[node.constructor.nodeType] || {
    input_types: { required: {}, optional: {} },
  };

  appendInspectorLabel(panel, t("nodeName"));
  const titleInput = document.createElement("input");
  titleInput.className = "inspector-input";
  titleInput.value = node.title || node.constructor.nodeType;
  titleInput.addEventListener("change", () => {
    node.title = titleInput.value;
    inspectorGraph.setDirtyCanvas(true, true);
  });
  panel.appendChild(titleInput);

  const linked = linkedInputNames(node);
  const allInputs = Object.assign(
    {},
    meta.input_types.required || {},
    meta.input_types.optional || {}
  );

  for (const [name, spec] of Object.entries(allInputs)) {
    const inputType = spec[0];
    if (inputType !== "STRING" || linked.has(name)) continue;

    appendInspectorLabel(panel, name);
    const field = document.createElement("textarea");
    field.className = "inspector-input";
    field.rows = 3;
    field.value = node.properties[name] || "";
    field.addEventListener("input", () => {
      node.properties[name] = field.value;
    });
    panel.appendChild(field);
  }

  const actions = document.createElement("div");
  actions.className = "inspector-actions";

  const runButton = document.createElement("button");
  runButton.textContent = t("runNode");
  runButton.addEventListener("click", () => runSingleNode(node));
  actions.appendChild(runButton);

  const deleteButton = document.createElement("button");
  deleteButton.className = "inspector-delete";
  deleteButton.textContent = t("delete");
  deleteButton.addEventListener("click", () => {
    inspectorGraph.remove(node);
    inspectorSelectedNode = null;
    renderInspector();
  });
  actions.appendChild(deleteButton);

  panel.appendChild(actions);
}

function appendInspectorLabel(panel, text) {
  const label = document.createElement("div");
  label.className = "inspector-label";
  label.textContent = text;
  panel.appendChild(label);
}

function runSingleNode(node) {
  const payload = buildExecutionPayload(inspectorGraph);
  const nodeId = String(node.id);
  const isolatedNodes = payload.nodes.filter((n) => n.id === nodeId);

  const ws = new WebSocket(
    `ws://${location.host}/ws/run/${encodeURIComponent(inspectorWorkspaceName)}`
  );
  ws.onopen = () => {
    ws.send(JSON.stringify({ graph: { nodes: isolatedNodes, links: [] } }));
  };
  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (typeof appendLogEntry === "function") appendLogEntry(event);
    if (event.event === "run_finished") ws.close();
  };
}
