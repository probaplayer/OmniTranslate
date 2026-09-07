const params = new URLSearchParams(window.location.search);
const workspaceName = params.get("workspace");

const graph = new LGraph();
const canvasEl = document.getElementById("graph-canvas");
const canvas = new LGraphCanvas(canvasEl, graph);

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

function setStatus(text, kind = "info") {
  const statusEl = document.getElementById("status");
  statusEl.textContent = text;
  statusEl.className = `status-${kind}`;
}

function colorForEvent(eventName) {
  if (eventName === "node_started") return "#557";
  if (eventName === "node_completed") return "#575";
  return "#755";
}

async function init() {
  const nodesResponse = await fetch("/api/nodes");
  if (!nodesResponse.ok) {
    setStatus(`Lỗi tải danh sách node: ${nodesResponse.status}`, "error");
    return;
  }
  const nodeMetadataList = await nodesResponse.json();
  registerDynamicNodeTypes(nodeMetadataList);
  initNodePalette(nodeMetadataList, graph, canvas, canvasEl);

  const graphResponse = await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}`);
  if (!graphResponse.ok) {
    setStatus(`Lỗi tải workspace: ${graphResponse.status}`, "error");
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
    setStatus(`Lỗi lưu: ${response.status}`, "error");
    return;
  }
  setStatus("Đã lưu", "ok");
}

function runGraph() {
  const payload = buildExecutionPayload(graph);
  const ws = new WebSocket(`ws://${location.host}/ws/run/${encodeURIComponent(workspaceName)}`);

  ws.onopen = () => ws.send(JSON.stringify({ graph: payload }));

  ws.onerror = () => setStatus("Lỗi kết nối WebSocket", "error");

  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (event.event === "run_finished") {
      setStatus("Hoàn tất", "ok");
      return;
    }
    if (event.event === "validation_error") {
      setStatus(`Lỗi: ${event.message}`, "error");
      return;
    }
    if (event.event === "runtime_error") {
      setStatus(`Lỗi thực thi: ${event.message}`, "error");
      return;
    }
    const node = graph.getNodeById(Number(event.node_id));
    if (node) {
      node.bgcolor = colorForEvent(event.event);
      graph.setDirtyCanvas(true, true);
    }
    setStatus(`${event.event}: node ${event.node_id}`);
  };
}

document.getElementById("run-button").addEventListener("click", runGraph);
document.getElementById("save-button").addEventListener("click", saveGraph);

init();
