let inspectorNodeMetadata = {};
let inspectorSelectedNode = null;

function initInspectorPanel(nodeMetadataList, canvas) {
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

function clearInspectorSelection() {
  inspectorSelectedNode = null;
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
  const typeMeta = NODE_TYPE_META[node.constructor.nodeType] || NODE_TYPE_META_FALLBACK;

  const header = document.createElement("div");
  header.className = "inspector-header";

  const headerIcon = document.createElement("span");
  headerIcon.className = "inspector-header-icon";
  headerIcon.style.color = typeMeta.color;
  headerIcon.textContent = typeMeta.icon;
  header.appendChild(headerIcon);

  const headerText = document.createElement("div");
  const headerType = document.createElement("div");
  headerType.className = "inspector-header-type";
  headerType.style.color = typeMeta.color;
  headerType.textContent = nodeTypeLabel(node.constructor.nodeType);
  const headerTitle = document.createElement("div");
  headerTitle.className = "inspector-header-title";
  headerTitle.textContent = node.title || node.constructor.nodeType;
  headerText.appendChild(headerType);
  headerText.appendChild(headerTitle);
  header.appendChild(headerText);

  panel.appendChild(header);

  appendInspectorLabel(panel, t("nodeName"));
  const titleInput = document.createElement("input");
  titleInput.className = "inspector-input";
  titleInput.value = node.title || node.constructor.nodeType;
  titleInput.addEventListener("change", () => {
    node.title = titleInput.value;
    markActiveDirty();
    const activeGraph = getActiveGraph();
    if (activeGraph) activeGraph.setDirtyCanvas(true, true);
    renderInspector();
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
      markActiveDirty();
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
    const activeGraph = getActiveGraph();
    if (activeGraph) activeGraph.remove(node);
    markActiveDirty();
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
  const activeGraph = getActiveGraph();
  const activeWorkspaceName = getActiveWorkspaceName();
  if (!activeGraph) return;
  if (!activeWorkspaceName) {
    setStatus(t("statusSaveBeforeRun"), "error");
    return;
  }

  const payload = buildExecutionPayload(activeGraph);
  const nodeId = String(node.id);

  const ancestorIds = new Set([nodeId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const link of payload.links) {
      if (ancestorIds.has(link.to_node) && !ancestorIds.has(link.from_node)) {
        ancestorIds.add(link.from_node);
        changed = true;
      }
    }
  }

  const isolatedNodes = payload.nodes.filter((n) => ancestorIds.has(n.id));
  const isolatedLinks = payload.links.filter(
    (link) => ancestorIds.has(link.from_node) && ancestorIds.has(link.to_node)
  );

  const ws = new WebSocket(
    `ws://${location.host}/ws/run/${encodeURIComponent(activeWorkspaceName)}`
  );
  ws.onopen = () => {
    ws.send(JSON.stringify({ graph: { nodes: isolatedNodes, links: isolatedLinks } }));
  };
  ws.onerror = () => setStatus(t("statusWsError"), "error");
  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    appendLogEntry(event);
    if (event.event === "run_finished") {
      setStatus(t("statusRunFinished"), "ok");
      ws.close();
    }
  };
}
