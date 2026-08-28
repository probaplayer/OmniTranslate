async function loadWorkspaces() {
  const response = await fetch("/api/workspaces");
  const data = await response.json();
  const list = document.getElementById("workspace-list");
  list.innerHTML = "";
  for (const name of data.workspaces) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `/canvas.html?workspace=${encodeURIComponent(name)}`;
    link.textContent = name;
    item.appendChild(link);
    list.appendChild(item);
  }
}

async function createWorkspace(event) {
  event.preventDefault();
  const errorEl = document.getElementById("picker-error");
  errorEl.textContent = "";

  const name = document.getElementById("new-name").value.trim();
  const sourceLang = document.getElementById("new-source-lang").value.trim();
  const targetLang = document.getElementById("new-target-lang").value.trim();

  const response = await fetch("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, source_lang: sourceLang, target_lang: targetLang }),
  });

  if (!response.ok) {
    const body = await response.json();
    errorEl.textContent = body.detail || "Không tạo được workspace";
    return;
  }

  window.location.href = `/canvas.html?workspace=${encodeURIComponent(name)}`;
}

document.getElementById("create-form").addEventListener("submit", createWorkspace);
loadWorkspaces();
