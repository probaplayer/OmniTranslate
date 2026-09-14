let tabs = [];
let activeTabId = null;

const TABS_STORAGE_KEY = "openWorkspaceTabs";
const ACTIVE_STORAGE_KEY = "activeWorkspaceTab";

function persistTabState() {
  const names = tabs.map((tab) => tab.workspaceName).filter(Boolean);
  localStorage.setItem(TABS_STORAGE_KEY, JSON.stringify(names));
  const activeTab = getActiveTab();
  if (activeTab && activeTab.workspaceName) {
    localStorage.setItem(ACTIVE_STORAGE_KEY, activeTab.workspaceName);
  } else {
    localStorage.removeItem(ACTIVE_STORAGE_KEY);
  }
}

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
  if (tab) {
    tab.dirty = true;
    renderTabBar();
  }
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
    pill.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      showTabContextMenu(event, tab);
    });

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

function removeTab(tab) {
  const index = tabs.indexOf(tab);
  if (index === -1) return;
  tabs.splice(index, 1);
  tab.graph.stop();

  if (tabs.length === 0) {
    activateTab(createTabForGraph(null, new LGraph()));
  } else if (tab.id === activeTabId) {
    const neighbor = tabs[index] || tabs[index - 1];
    activateTab(neighbor);
  } else {
    renderTabBar();
  }
  persistTabState();
}

function closeTab(id) {
  const tab = tabs.find((t) => t.id === id);
  if (!tab) return;
  if (tab.dirty && !window.confirm(t("confirmDiscardTab"))) return;
  removeTab(tab);
}

function closeTabContextMenu() {
  const existing = document.getElementById("tab-context-menu");
  if (existing) existing.remove();
}

function showTabContextMenu(event, tab) {
  closeTabContextMenu();
  if (!tab.workspaceName) return; // nothing on disk to delete for an unsaved tab

  const menu = document.createElement("div");
  menu.id = "tab-context-menu";
  menu.className = "tab-context-menu";
  menu.style.left = `${event.clientX}px`;
  menu.style.top = `${event.clientY}px`;

  const renameItem = document.createElement("div");
  renameItem.className = "tab-context-menu-item";
  renameItem.textContent = t("renameWorkspaceButton");
  renameItem.addEventListener("click", async () => {
    closeTabContextMenu();
    let newName = window.prompt(t("promptRenameWorkspace"), tab.workspaceName);
    if (newName === null) return;
    newName = newName.trim();
    if (newName === tab.workspaceName) return;
    if (!/^[A-Za-z0-9_-]+$/.test(newName)) {
      setStatus(t("statusInvalidWorkspaceName"), "error");
      return;
    }
    const response = await fetch(`/api/workspaces/${encodeURIComponent(tab.workspaceName)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_name: newName }),
    });
    if (!response.ok) {
      let detail = `${t("statusRenameWorkspaceError")}${response.status}`;
      try {
        const body = await response.json();
        if (body.detail) detail = body.detail;
      } catch {
        // response body wasn't JSON -- keep the generic message
      }
      setStatus(detail, "error");
      return;
    }
    tab.workspaceName = newName;
    renderTabBar();
    persistTabState();
    setStatus(t("statusRenamedWorkspace"), "ok");
  });
  menu.appendChild(renameItem);

  const outputItem = document.createElement("div");
  outputItem.className = "tab-context-menu-item";
  outputItem.textContent = t("outputManagerButton");
  outputItem.addEventListener("click", () => {
    closeTabContextMenu();
    openOutputManager(tab.workspaceName);
  });
  menu.appendChild(outputItem);

  const deleteItem = document.createElement("div");
  deleteItem.className = "tab-context-menu-item danger";
  deleteItem.textContent = t("deleteWorkspaceButton");
  deleteItem.addEventListener("click", async () => {
    closeTabContextMenu();
    if (!window.confirm(t("confirmDeleteWorkspace").replace("{name}", tab.workspaceName))) return;
    const response = await fetch(`/api/workspaces/${encodeURIComponent(tab.workspaceName)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      setStatus(`${t("statusDeleteWorkspaceError")}${response.status}`, "error");
      return;
    }
    removeTab(tab);
    setStatus(t("statusDeletedWorkspace"), "ok");
  });
  menu.appendChild(deleteItem);

  document.body.appendChild(menu);

  // Deferred so the same right-click that opened the menu doesn't immediately
  // dismiss it via bubbling on browsers that fire "click" after "contextmenu".
  setTimeout(() => {
    document.addEventListener("click", dismissTabContextMenuOnOutsideClick);
  }, 0);
}

function dismissTabContextMenuOnOutsideClick(event) {
  const menu = document.getElementById("tab-context-menu");
  if (menu && !menu.contains(event.target)) {
    closeTabContextMenu();
  }
  document.removeEventListener("click", dismissTabContextMenuOnOutsideClick);
}

function createBlankTab() {
  activateTab(createTabForGraph(null, new LGraph()));
}

async function openWorkspaceAsTab(name) {
  const existing = tabs.find((t) => t.workspaceName === name);
  if (existing) {
    switchToTab(existing.id);
    return;
  }
  const response = await fetch(`/api/workspaces/${encodeURIComponent(name)}`);
  const graph = new LGraph();
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
    return;
  }
  activateTab(createTabForGraph(name, graph));
}

async function toggleOpenWorkspaceMenu() {
  const existingMenu = document.getElementById("open-workspace-menu");
  if (existingMenu) {
    existingMenu.remove();
    return;
  }
  const response = await fetch("/api/workspaces");
  if (!response.ok) {
    setStatus(`${t("statusLoadWorkspaceError")}${response.status}`, "error");
    return;
  }
  const data = await response.json();
  const openNames = new Set(tabs.map((t) => t.workspaceName).filter(Boolean));
  const available = data.workspaces.filter((name) => !openNames.has(name));

  const menu = document.createElement("div");
  menu.id = "open-workspace-menu";
  if (available.length === 0) {
    const empty = document.createElement("div");
    empty.className = "open-workspace-menu-empty";
    empty.textContent = t("noOtherWorkspaces");
    menu.appendChild(empty);
  } else {
    for (const name of available) {
      const item = document.createElement("div");
      item.className = "open-workspace-menu-item";
      item.textContent = name;
      item.addEventListener("click", () => {
        menu.remove();
        openWorkspaceAsTab(name);
      });
      menu.appendChild(item);
    }
  }
  document.getElementById("open-workspace-button").parentElement.appendChild(menu);
}

document.getElementById("new-tab-button").addEventListener("click", createBlankTab);
document.getElementById("open-workspace-button").addEventListener("click", toggleOpenWorkspaceMenu);

function activateTab(tab) {
  activeTabId = tab.id;
  canvas.setGraph(tab.graph);
  if (typeof clearInspectorSelection === "function") clearInspectorSelection();
  canvas.setDirty(true, true);
  renderTabBar();
  persistTabState();
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
  persistTabState();
}

async function initWorkspaceTabs() {
  const params = new URLSearchParams(window.location.search);
  const urlWorkspaceName = params.get("workspace");

  let remembered = [];
  try {
    remembered = JSON.parse(localStorage.getItem(TABS_STORAGE_KEY) || "[]");
  } catch {
    remembered = [];
  }
  const namesToOpen = [...remembered];
  if (urlWorkspaceName && !namesToOpen.includes(urlWorkspaceName)) {
    namesToOpen.push(urlWorkspaceName);
  }
  const activeName = urlWorkspaceName || localStorage.getItem(ACTIVE_STORAGE_KEY);

  const createdTabs = [];
  for (const name of namesToOpen) {
    const response = await fetch(`/api/workspaces/${encodeURIComponent(name)}`);
    if (!response.ok) continue; // a remembered workspace that no longer exists -- skip it silently
    const graph = new LGraph();
    const savedGraph = await response.json();
    if (savedGraph.nodes && savedGraph.nodes.length) {
      graph.configure(savedGraph);
      for (const node of graph._nodes) {
        const minHeight = node.computeSize()[1];
        if (node.size[1] < minHeight) node.size[1] = minHeight;
      }
    }
    createdTabs.push(createTabForGraph(name, graph));
  }

  let tabToActivate = createdTabs.find((tab) => tab.workspaceName === activeName);
  if (!tabToActivate) tabToActivate = createdTabs[0];
  if (!tabToActivate) tabToActivate = createTabForGraph(null, new LGraph());

  activateTab(tabToActivate);
}
