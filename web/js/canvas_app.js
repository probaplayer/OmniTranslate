const params = new URLSearchParams(window.location.search);
const workspaceName = params.get("workspace");

const graph = new LGraph();
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

const canvas = new LGraphCanvas(canvasEl, graph);
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
  initNodePalette(nodeMetadataList, graph, canvas, canvasEl);
  initInspectorPanel(nodeMetadataList, graph, canvas, workspaceName);
  initLogConsole();
  initMinimap(graph, canvas, canvasEl);
  initBatchPanel();

  const graphResponse = await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}`);
  if (!graphResponse.ok) {
    setStatus(`${t("statusLoadWorkspaceError")}${graphResponse.status}`, "error");
    return;
  }
  const savedGraph = await graphResponse.json();
  if (savedGraph.nodes && savedGraph.nodes.length) {
    graph.configure(savedGraph);
  }

  graph.start();
}

async function saveGraph() {
  const response = await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}/graph`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph.serialize()),
  });
  if (!response.ok) {
    setStatus(`${t("statusSaveError")}${response.status}`, "error");
    return;
  }
  setStatus(t("statusSaved"), "ok");
}

function runGraph() {
  const payload = buildExecutionPayload(graph);
  const ws = new WebSocket(`ws://${location.host}/ws/run/${encodeURIComponent(workspaceName)}`);

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
    const node = graph.getNodeById(Number(event.node_id));
    if (node) {
      if (event.event === "node_started") node._runStatus = "running";
      else if (event.event === "node_completed") node._runStatus = "done";
      else node._runStatus = "error";
      node._runStatusAt = Date.now();
      graph.setDirtyCanvas(true, true);
    }
    setStatus(`${event.event}: node ${event.node_id}`);
  };
}

document.getElementById("run-button").addEventListener("click", runGraph);
document.getElementById("save-button").addEventListener("click", saveGraph);
document.getElementById("lang-vi-button").addEventListener("click", () => {
  setLang("vi");
  renderInspector();
  if (nodeMetadataList) initNodePalette(nodeMetadataList, graph, canvas, canvasEl);
  renderLogEmptyState();
});
document.getElementById("lang-en-button").addEventListener("click", () => {
  setLang("en");
  renderInspector();
  if (nodeMetadataList) initNodePalette(nodeMetadataList, graph, canvas, canvasEl);
  renderLogEmptyState();
});

init();
