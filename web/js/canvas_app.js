const canvasEl = document.getElementById("graph-canvas");

// NODE_TITLE_COLOR/LINK_COLOR must be set before LGraphCanvas is
// constructed: its constructor copies them into instance properties
// (node_title_color/default_link_color) once, at construction time, and
// the renderer reads those cached copies rather than the LiteGraph
// globals afterward -- setting these after `new LGraphCanvas(...)` would
// silently have no visual effect.
LiteGraph.NODE_DEFAULT_BGCOLOR = "#1a1d23";
LiteGraph.NODE_DEFAULT_COLOR = "#2a2f37";
LiteGraph.NODE_TITLE_COLOR = "#9aa1ab";
LiteGraph.LINK_COLOR = "#d9a44c";
LiteGraph.NODE_WIDTH = 200;

// No graph is attached yet -- LGraphCanvas's constructor explicitly
// tolerates this (`if (graph) { graph.attachCanvas(this); }`, verified
// in the vendored source). workspace_tabs.js's initWorkspaceTabs()
// attaches the first real graph via canvas.setGraph(...).
const canvas = new LGraphCanvas(canvasEl, null);
canvas.clear_background_color = "#101216";

// The <canvas> element's drawing-buffer resolution defaults to 300x150 and
// does not track its CSS/flex-layout size on its own -- without this, nodes
// are drawn into (and clipped by) that tiny buffer while it's stretched to
// fill the page, making them invisible or misplaced relative to real mouse
// coordinates.
function syncCanvasSize() {
  canvas.resize(canvasEl.clientWidth, canvasEl.clientHeight);
}
syncCanvasSize();
window.addEventListener("resize", syncCanvasSize);
if (window.ResizeObserver) {
  new ResizeObserver(syncCanvasSize).observe(document.getElementById("canvas-area"));
}

function setStatus(text, kind = "info") {
  const statusEl = document.getElementById("status");
  statusEl.textContent = text;
  statusEl.className = `status-${kind}`;
}

let nodeMetadataList = null;

async function init() {
  const nodesResponse = await fetch("/api/nodes");
  if (!nodesResponse.ok) {
    setStatus(`${t("statusLoadNodesError")}${nodesResponse.status}`, "error");
    return;
  }
  nodeMetadataList = await nodesResponse.json();
  registerDynamicNodeTypes(nodeMetadataList);
  initNodePalette(nodeMetadataList, canvas, canvasEl);
  initInspectorPanel(nodeMetadataList, canvas);
  initLogConsole();
  initMinimap(canvas, canvasEl);
  initSettingsPanel(canvas);

  await initWorkspaceTabs();
}

function runGraph() {
  const activeGraph = getActiveGraph();
  const activeWorkspaceName = getActiveWorkspaceName();
  if (!activeGraph) return;
  if (!activeWorkspaceName) {
    setStatus(t("statusSaveBeforeRun"), "error");
    return;
  }

  const payload = buildExecutionPayload(activeGraph);
  const ws = new WebSocket(`ws://${location.host}/ws/run/${encodeURIComponent(activeWorkspaceName)}`);

  ws.onopen = () => ws.send(JSON.stringify({ graph: payload }));

  ws.onerror = () => setStatus(t("statusWsError"), "error");

  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    appendLogEntry(event);
    if (event.event === "run_finished") {
      setStatus(t("statusRunFinished"), "ok");
      return;
    }
    if (event.event === "validation_error") {
      setStatus(`${t("statusValidationError")}${event.message}`, "error");
      return;
    }
    if (event.event === "runtime_error") {
      setStatus(`${t("statusRuntimeError")}${event.message}`, "error");
      return;
    }
    const node = activeGraph.getNodeById(Number(event.node_id));
    if (node) {
      if (event.event === "node_started") node._runStatus = "running";
      else if (event.event === "node_completed") node._runStatus = "done";
      else node._runStatus = "error";
      node._runStatusAt = Date.now();
      activeGraph.setDirtyCanvas(true, true);
    }
    setStatus(`${event.event}: node ${event.node_id}`);
  };
}

document.getElementById("run-button").addEventListener("click", runGraph);
document.getElementById("save-button").addEventListener("click", saveActiveTab);
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    saveActiveTab();
  }
});

function switchLang(lang) {
  setLang(lang);
  document.getElementById("lang-vi-button").classList.toggle("active", lang === "vi");
  document.getElementById("lang-en-button").classList.toggle("active", lang === "en");
  renderTabBar();
  renderInspector();
  if (nodeMetadataList) initNodePalette(nodeMetadataList, canvas, canvasEl);
  renderLogEmptyState();
  const activeGraph = getActiveGraph();
  if (activeGraph) activeGraph.setDirtyCanvas(true, true);
}

document.getElementById("lang-vi-button").classList.toggle("active", currentLang() === "vi");
document.getElementById("lang-en-button").classList.toggle("active", currentLang() === "en");
document.getElementById("lang-vi-button").addEventListener("click", () => switchLang("vi"));
document.getElementById("lang-en-button").addEventListener("click", () => switchLang("en"));

init();
