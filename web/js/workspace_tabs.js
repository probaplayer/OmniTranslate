let tabs = [];
let activeTabId = null;

function makeTabId() {
  return `t${Date.now()}${Math.random().toString(36).slice(2)}`;
}

function getActiveTab() {
  return tabs.find((tab) => tab.id === activeTabId) || null;
}

function getActiveGraph() {
  const tab = getActiveTab();
  return tab ? tab.graph : null;
}

function getActiveWorkspaceName() {
  const tab = getActiveTab();
  return tab ? tab.workspaceName : null;
}

function markActiveDirty() {
  const tab = getActiveTab();
  if (tab) tab.dirty = true;
}

function createTabForGraph(workspaceName, graph) {
  graph.on_change = () => markActiveDirty();
  graph.start();
  const tab = { id: makeTabId(), workspaceName, graph, dirty: false };
  tabs.push(tab);
  return tab;
}

function renderTabBar() {
  const bar = document.getElementById("workspace-tabs");
  if (!bar) return;
  bar.querySelectorAll(".workspace-tab").forEach((el) => el.remove());

  const newTabButton = document.getElementById("new-tab-button");
  for (const tab of tabs) {
    const pill = document.createElement("div");
    pill.className = "workspace-tab" + (tab.id === activeTabId ? " active" : "");
    pill.addEventListener("click", () => switchToTab(tab.id));

    if (tab.dirty) {
      const dot = document.createElement("span");
      dot.className = "workspace-tab-dirty-dot";
      pill.appendChild(dot);
    }

    const label = document.createElement("span");
    label.textContent = tab.workspaceName || t("untitledWorkspace");
    pill.appendChild(label);

    const closeButton = document.createElement("button");
    closeButton.className = "workspace-tab-close";
    closeButton.textContent = "×";
    closeButton.addEventListener("click", (event) => {
      event.stopPropagation();
      closeTab(tab.id);
    });
    pill.appendChild(closeButton);

    bar.insertBefore(pill, newTabButton);
  }
}

function switchToTab(id) {
  const tab = tabs.find((t) => t.id === id);
  if (!tab) return;
  activateTab(tab);
}

function closeTab(id) {
  const tab = tabs.find((t) => t.id === id);
  if (!tab) return;
  if (tab.dirty && !window.confirm(t("confirmDiscardTab"))) return;

  const index = tabs.indexOf(tab);
  tabs.splice(index, 1);

  if (tabs.length === 0) {
    activateTab(createTabForGraph(null, new LGraph()));
  } else if (tab.id === activeTabId) {
    const neighbor = tabs[index] || tabs[index - 1];
    activateTab(neighbor);
  } else {
    renderTabBar();
  }
}

function createBlankTab() {
  activateTab(createTabForGraph(null, new LGraph()));
}

document.getElementById("new-tab-button").addEventListener("click", createBlankTab);

function activateTab(tab) {
  activeTabId = tab.id;
  canvas.setGraph(tab.graph);
  if (typeof clearInspectorSelection === "function") clearInspectorSelection();
  canvas.setDirty(true, true);
  renderTabBar();
}

async function saveActiveTab() {
  const tab = getActiveTab();
  if (!tab) return;

  if (tab.workspaceName === null) {
    let name = window.prompt(t("promptWorkspaceName"));
    if (name === null) return;
    name = name.trim();
    if (!/^[A-Za-z0-9_-]+$/.test(name)) {
      setStatus(t("statusInvalidWorkspaceName"), "error");
      return;
    }
    const createResponse = await fetch("/api/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, source_lang: "", target_lang: "" }),
    });
    if (!createResponse.ok) {
      let detail = t("createWorkspaceGenericError");
      try {
        const body = await createResponse.json();
        detail = body.detail || detail;
      } catch {
        // response body wasn't JSON -- keep the generic message
      }
      setStatus(detail, "error");
      return;
    }
    tab.workspaceName = name;
  }

  const saveResponse = await fetch(
    `/api/workspaces/${encodeURIComponent(tab.workspaceName)}/graph`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tab.graph.serialize()),
    }
  );
  if (!saveResponse.ok) {
    setStatus(`${t("statusSaveError")}${saveResponse.status}`, "error");
    return;
  }
  tab.dirty = false;
  setStatus(t("statusSaved"), "ok");
  renderTabBar();
}

async function initWorkspaceTabs() {
  const params = new URLSearchParams(window.location.search);
  const initialWorkspaceName = params.get("workspace");

  let graph;
  if (initialWorkspaceName) {
    const response = await fetch(`/api/workspaces/${encodeURIComponent(initialWorkspaceName)}`);
    graph = new LGraph();
    if (response.ok) {
      const savedGraph = await response.json();
      if (savedGraph.nodes && savedGraph.nodes.length) {
        graph.configure(savedGraph);
        for (const node of graph._nodes) {
          const minHeight = node.computeSize()[1];
          if (node.size[1] < minHeight) node.size[1] = minHeight;
        }
      }
    } else {
      setStatus(`${t("statusLoadWorkspaceError")}${response.status}`, "error");
    }
    const tab = createTabForGraph(initialWorkspaceName, graph);
    activateTab(tab);
  } else {
    graph = new LGraph();
    const tab = createTabForGraph(null, graph);
    activateTab(tab);
  }
}
