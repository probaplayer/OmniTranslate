let logOpen = true;

function appendLogEntry(event) {
  const body = document.getElementById("log-console-body");
  if (!body) return;

  const now = new Date();
  const time = [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");

  const row = document.createElement("div");
  row.className = "log-entry";

  const timeEl = document.createElement("span");
  timeEl.className = "log-time";
  timeEl.textContent = time;

  const sourceEl = document.createElement("span");
  sourceEl.textContent = event.node_id ? `node ${event.node_id}` : "run";

  const messageEl = document.createElement("span");
  messageEl.textContent = event.message || event.event;

  row.appendChild(timeEl);
  row.appendChild(sourceEl);
  row.appendChild(messageEl);
  body.appendChild(row);
  body.scrollTop = body.scrollHeight;
}

function clearLog() {
  const body = document.getElementById("log-console-body");
  if (body) body.innerHTML = "";
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
}
