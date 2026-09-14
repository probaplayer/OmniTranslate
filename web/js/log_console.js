let logOpen = true;

const LOG_MESSAGE_COLOR = {
  node_started: "#d9a44c",
  node_completed: "#7fb98a",
  node_error: "#d97070",
  validation_error: "#d97070",
  runtime_error: "#d97070",
  run_finished: "#7fb98a",
};

function updateLogCountBadge() {
  const badge = document.getElementById("log-count-badge");
  const body = document.getElementById("log-console-body");
  if (!badge || !body) return;
  badge.textContent = String(body.querySelectorAll(".log-entry").length);
}

function renderLogEmptyState() {
  const body = document.getElementById("log-console-body");
  if (!body) return;
  if (body.querySelector(".log-entry")) return;
  let empty = body.querySelector(".log-empty");
  if (!empty) {
    empty = document.createElement("div");
    empty.className = "log-empty";
    empty.style.padding = "14px 12px";
    empty.style.fontSize = "11.5px";
    empty.style.color = "#5d646e";
    body.appendChild(empty);
  }
  empty.textContent = t("logEmpty");
}

// event.node_type comes straight from the executor (always present for any
// per-node event), so this works even if the node was since deleted from
// the canvas. When the node still exists and the user renamed it, its
// custom title is appended too -- that's the name the user actually
// recognizes, vs. the bare node type.
function describeLogSource(event) {
  const graph = typeof getActiveGraph === "function" ? getActiveGraph() : null;
  const node = graph ? graph.getNodeById(Number(event.node_id)) : null;
  const typeName = event.node_type || (node && node.constructor.nodeType) || "?";
  const customTitle =
    node && node.title && node.title !== node.constructor.nodeType ? ` "${node.title}"` : "";
  return `#${event.node_id} ${typeName}${customTitle}`;
}

function appendLogEntry(event) {
  const body = document.getElementById("log-console-body");
  if (!body) return;

  const existingEmpty = body.querySelector(".log-empty");
  if (existingEmpty) existingEmpty.remove();

  const now = new Date();
  const time = [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");

  const row = document.createElement("div");
  row.className = "log-entry";

  const timeEl = document.createElement("span");
  timeEl.className = "log-time";
  timeEl.textContent = time;

  const isSkippedEntry =
    event.event === "node_error" && event.message === "skipped: upstream dependency failed";

  const sourceEl = document.createElement("span");
  sourceEl.textContent = event.node_id ? describeLogSource(event) : "run";

  const messageEl = document.createElement("span");
  messageEl.textContent = event.message || event.event;
  const color = isSkippedEntry ? "var(--text-faint)" : LOG_MESSAGE_COLOR[event.event];
  if (color) messageEl.style.color = color;

  if (isSkippedEntry) {
    row.classList.add("log-entry-skipped");
  } else if (event.event === "node_error") {
    row.classList.add("log-entry-root-error");
  }

  row.appendChild(timeEl);
  row.appendChild(sourceEl);
  row.appendChild(messageEl);
  body.appendChild(row);
  body.scrollTop = body.scrollHeight;

  updateLogCountBadge();
}

function clearLog() {
  const body = document.getElementById("log-console-body");
  if (body) body.innerHTML = "";
  renderLogEmptyState();
  updateLogCountBadge();
}

function initLogConsole() {
  const header = document.getElementById("log-console-header");
  const body = document.getElementById("log-console-body");
  const clearButton = document.getElementById("clear-log-button");

  header.addEventListener("click", (event) => {
    if (event.target === clearButton) return;
    logOpen = !logOpen;
    body.style.display = logOpen ? "block" : "none";
  });

  clearButton.addEventListener("click", (event) => {
    event.stopPropagation();
    clearLog();
  });

  renderLogEmptyState();
  updateLogCountBadge();
}
