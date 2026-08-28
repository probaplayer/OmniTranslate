const params = new URLSearchParams(window.location.search);
const workspaceName = params.get("workspace");

const graph = new LGraph();
const canvasEl = document.getElementById("graph-canvas");
const canvas = new LGraphCanvas(canvasEl, graph);

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

function colorForEvent(eventName) {
  if (eventName === "node_started") return "#557";
  if (eventName === "node_completed") return "#575";
  return "#755";
}

async function init() {
  const nodesResponse = await fetch("/api/nodes");
  const nodeMetadataList = await nodesResponse.json();
  registerDynamicNodeTypes(nodeMetadataList);

  const graphResponse = await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}`);
  const savedGraph = await graphResponse.json();
  if (savedGraph.nodes && savedGraph.nodes.length) {
    graph.configure(savedGraph);
  }

  graph.start();
}

async function saveGraph() {
  await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}/graph`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph.serialize()),
  });
  setStatus("Đã lưu");
}

function runGraph() {
  const payload = buildExecutionPayload(graph);
  const ws = new WebSocket(`ws://${location.host}/ws/run/${encodeURIComponent(workspaceName)}`);

  ws.onopen = () => ws.send(JSON.stringify({ graph: payload }));

  ws.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (event.event === "run_finished") {
      setStatus("Hoàn tất");
      return;
    }
    if (event.event === "validation_error") {
      setStatus(`Lỗi: ${event.message}`);
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
