let inspectorNodeMetadata = {};
let inspectorSelectedNode = null;

// Both node types build a plain OpenAICompatibleProvider under the hood
// (Provider.execute() never makes a network call, see testProviderConnection
// below) -- GeminiProvider just fixes base_url to Google's OpenAI-compatible
// endpoint instead of exposing it as a field, so it needs the exact same
// standalone connection test.
const PROVIDER_NODE_TYPES = new Set(["Provider", "GeminiProvider"]);
const GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/";

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

    const config = spec[1] || {};
    if (config.widget === "path") {
      const browseButton = document.createElement("button");
      browseButton.className = "inspector-browse-button";
      browseButton.textContent = t("browseButton");
      browseButton.addEventListener("click", () => {
        openPathPicker(field.value, (chosen) => {
          field.value = chosen;
          node.properties[name] = chosen;
          markActiveDirty();
        });
      });
      panel.appendChild(browseButton);
    } else if (config.widget === "agent_template") {
      const chooseButton = document.createElement("button");
      chooseButton.className = "inspector-browse-button";
      chooseButton.textContent = t("agentTemplateButton");
      chooseButton.addEventListener("click", () => {
        openAgentTemplatePicker(field.value, (chosen) => {
          field.value = chosen;
          node.properties[name] = chosen;
          markActiveDirty();
        });
      });
      panel.appendChild(chooseButton);
    }
  }

  const actions = document.createElement("div");
  actions.className = "inspector-actions";

  if (PROVIDER_NODE_TYPES.has(node.constructor.nodeType)) {
    const testButton = document.createElement("button");
    testButton.textContent = t("testProviderConnection");
    testButton.addEventListener("click", () => testProviderConnection(node));
    actions.appendChild(testButton);
  }

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

async function testProviderConnection(node) {
  setStatus(t("statusTestingProvider"), "info");
  try {
    const response = await fetch("/api/test-provider", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_url:
          node.constructor.nodeType === "GeminiProvider"
            ? GEMINI_OPENAI_BASE_URL
            : node.properties.base_url || "",
        api_key: node.properties.api_key || "",
        model: node.properties.model || "",
        timeout_seconds: node.properties.timeout_seconds || "",
      }),
    });
    if (!response.ok) {
      setStatus(`${t("statusTestProviderError")}HTTP ${response.status}`, "error");
      return;
    }
    const data = await response.json();
    if (data.ok) {
      setStatus(t("statusTestProviderOk"), "ok");
    } else {
      setStatus(`${t("statusTestProviderError")}${data.message}`, "error");
    }
  } catch (err) {
    setStatus(`${t("statusTestProviderError")}${err}`, "error");
  }
}
