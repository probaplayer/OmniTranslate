let pathPickerState = null;

function openPathPicker(initialPath, onSelect) {
  closePathPicker();

  const overlay = document.createElement("div");
  overlay.id = "path-picker-overlay";
  overlay.className = "path-picker-overlay";

  const modal = document.createElement("div");
  modal.className = "path-picker-modal";

  const breadcrumb = document.createElement("div");
  breadcrumb.className = "path-picker-breadcrumb";
  modal.appendChild(breadcrumb);

  const list = document.createElement("div");
  list.className = "path-picker-list";
  modal.appendChild(list);

  const actions = document.createElement("div");
  actions.className = "path-picker-actions";
  const selectButton = document.createElement("button");
  selectButton.textContent = t("pathPickerSelect");
  const cancelButton = document.createElement("button");
  cancelButton.textContent = t("pathPickerCancel");
  actions.appendChild(selectButton);
  actions.appendChild(cancelButton);
  modal.appendChild(actions);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  pathPickerState = { currentPath: null, onSelect };

  cancelButton.addEventListener("click", closePathPicker);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closePathPicker();
  });
  selectButton.addEventListener("click", () => {
    if (pathPickerState && pathPickerState.currentPath) {
      pathPickerState.onSelect(pathPickerState.currentPath);
    }
    closePathPicker();
  });

  loadPathPickerDirectory(initialPath || "");
}

function closePathPicker() {
  const overlay = document.getElementById("path-picker-overlay");
  if (overlay) overlay.remove();
  pathPickerState = null;
}

async function loadPathPickerDirectory(path) {
  let response;
  try {
    response = await fetch(`/api/browse-directory?path=${encodeURIComponent(path)}`);
  } catch (error) {
    renderPathPickerError(t("pathPickerLoadError"));
    return;
  }
  if (!response.ok) {
    // The starting path (e.g. an old, now-deleted folder already in the
    // field) may not exist any more -- fall back to the drive list
    // instead of leaving the modal stuck on a failed request.
    if (path !== "") {
      await loadPathPickerDirectory("");
    }
    return;
  }
  const data = await response.json();
  renderPathPicker(data);
}

function renderPathPickerError(message) {
  const overlay = document.getElementById("path-picker-overlay");
  if (!overlay) return;
  const list = overlay.querySelector(".path-picker-list");
  list.innerHTML = "";
  const errorEl = document.createElement("div");
  errorEl.className = "path-picker-item";
  errorEl.textContent = message;
  list.appendChild(errorEl);
}

function renderPathPicker(data) {
  if (!pathPickerState) return;
  pathPickerState.currentPath = data.path;

  const overlay = document.getElementById("path-picker-overlay");
  if (!overlay) return;

  const breadcrumb = overlay.querySelector(".path-picker-breadcrumb");
  breadcrumb.textContent = data.path || t("pathPickerDrives");

  const list = overlay.querySelector(".path-picker-list");
  list.innerHTML = "";

  if (data.parent !== null) {
    const upItem = document.createElement("div");
    upItem.className = "path-picker-item";
    upItem.textContent = "..";
    upItem.addEventListener("click", () => loadPathPickerDirectory(data.parent));
    list.appendChild(upItem);
  }

  for (const entry of data.entries) {
    const item = document.createElement("div");
    item.className = "path-picker-item";
    item.textContent = entry.name;
    item.addEventListener("dblclick", () => loadPathPickerDirectory(entry.path));
    item.addEventListener("click", () => {
      pathPickerState.currentPath = entry.path;
      list
        .querySelectorAll(".path-picker-item.selected")
        .forEach((el) => el.classList.remove("selected"));
      item.classList.add("selected");
    });
    list.appendChild(item);
  }
}
