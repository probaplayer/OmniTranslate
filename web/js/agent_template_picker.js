let agentTemplatePickerState = null;

function openAgentTemplatePicker(onSelect) {
  closeAgentTemplatePicker();

  const overlay = document.createElement("div");
  overlay.id = "agent-template-picker-overlay";
  overlay.className = "agent-template-picker-overlay";

  const modal = document.createElement("div");
  modal.className = "agent-template-picker-modal";

  const workspaceOption = document.createElement("div");
  workspaceOption.className = "agent-template-picker-item";
  workspaceOption.textContent = t("agentTemplateWorkspaceOption");
  workspaceOption.addEventListener("click", () => {
    onSelect("workspace");
    closeAgentTemplatePicker();
  });
  modal.appendChild(workspaceOption);

  const tabs = document.createElement("div");
  tabs.className = "agent-template-picker-tabs";
  modal.appendChild(tabs);

  const list = document.createElement("div");
  list.className = "agent-template-picker-list";
  modal.appendChild(list);

  const actions = document.createElement("div");
  actions.className = "agent-template-picker-actions";
  const cancelButton = document.createElement("button");
  cancelButton.textContent = t("agentTemplateCancel");
  cancelButton.addEventListener("click", closeAgentTemplatePicker);
  actions.appendChild(cancelButton);
  modal.appendChild(actions);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeAgentTemplatePicker();
  });

  agentTemplatePickerState = { onSelect, data: {}, activeLang: null };

  fetch("/api/agent-templates")
    .then((response) => response.json())
    .then((data) => {
      if (!agentTemplatePickerState) return;
      agentTemplatePickerState.data = data;
      agentTemplatePickerState.activeLang = Object.keys(data)[0] || null;
      renderAgentTemplateTabs();
      renderAgentTemplateList();
    });
}

function closeAgentTemplatePicker() {
  const overlay = document.getElementById("agent-template-picker-overlay");
  if (overlay) overlay.remove();
  agentTemplatePickerState = null;
}

function renderAgentTemplateTabs() {
  const overlay = document.getElementById("agent-template-picker-overlay");
  if (!overlay || !agentTemplatePickerState) return;
  const tabs = overlay.querySelector(".agent-template-picker-tabs");
  tabs.innerHTML = "";

  for (const lang of Object.keys(agentTemplatePickerState.data)) {
    const tab = document.createElement("button");
    tab.className =
      "agent-template-picker-tab" + (lang === agentTemplatePickerState.activeLang ? " active" : "");
    tab.textContent = lang.toUpperCase();
    tab.addEventListener("click", () => {
      agentTemplatePickerState.activeLang = lang;
      renderAgentTemplateTabs();
      renderAgentTemplateList();
    });
    tabs.appendChild(tab);
  }
}

function renderAgentTemplateList() {
  const overlay = document.getElementById("agent-template-picker-overlay");
  if (!overlay || !agentTemplatePickerState) return;
  const list = overlay.querySelector(".agent-template-picker-list");
  list.innerHTML = "";

  const lang = agentTemplatePickerState.activeLang;
  const genres = (lang && agentTemplatePickerState.data[lang]) || [];

  for (const genre of genres) {
    const item = document.createElement("div");
    item.className = "agent-template-picker-item";
    item.textContent = genre;
    item.addEventListener("click", () => {
      agentTemplatePickerState.onSelect(`${lang}/${genre}`);
      closeAgentTemplatePicker();
    });
    list.appendChild(item);
  }
}
