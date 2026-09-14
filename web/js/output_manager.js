// Lists, previews, and deletes files under a workspace's own output/
// directory (server/workspace.py's list_output_files/read_output_file/
// delete_output_file) -- opened from the workspace tab's right-click menu.

function closeOutputManager() {
  const overlay = document.getElementById("output-manager-overlay");
  if (overlay) overlay.remove();
}

function formatOutputFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = -1;
  do {
    value /= 1024;
    unitIndex++;
  } while (value >= 1024 && unitIndex < units.length - 1);
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

function formatOutputFileDate(unixSeconds) {
  const d = new Date(unixSeconds * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Each path segment is percent-encoded on its own so a "/" between segments
// stays a path separator (matching the server's {path:path} route) while
// anything unusual inside a single filename is still escaped correctly.
function encodeOutputFilePath(relativePath) {
  return relativePath.split("/").map(encodeURIComponent).join("/");
}

function openOutputManager(workspaceName) {
  closeOutputManager();

  const overlay = document.createElement("div");
  overlay.id = "output-manager-overlay";
  overlay.className = "output-manager-overlay";
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeOutputManager();
  });

  const modal = document.createElement("div");
  modal.className = "output-manager-modal";

  const title = document.createElement("div");
  title.className = "output-manager-title";
  title.textContent = `${t("outputManagerTitle")} — ${workspaceName}`;
  modal.appendChild(title);

  const list = document.createElement("div");
  list.className = "output-manager-list";
  modal.appendChild(list);

  const preview = document.createElement("pre");
  preview.className = "output-manager-preview";
  preview.hidden = true;
  modal.appendChild(preview);

  const actions = document.createElement("div");
  actions.className = "output-manager-actions";
  const closeButton = document.createElement("button");
  closeButton.textContent = t("settingsClose");
  closeButton.addEventListener("click", closeOutputManager);
  actions.appendChild(closeButton);
  modal.appendChild(actions);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  function renderMessage(text) {
    list.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "output-manager-empty";
    empty.textContent = text;
    list.appendChild(empty);
  }

  function renderFiles(files) {
    list.innerHTML = "";
    if (files.length === 0) {
      renderMessage(t("outputManagerEmpty"));
      return;
    }
    for (const file of files) {
      const row = document.createElement("div");
      row.className = "output-manager-item";

      const nameEl = document.createElement("span");
      nameEl.className = "output-manager-item-name";
      nameEl.textContent = file.path;
      nameEl.title = t("outputManagerPreviewHint");
      nameEl.addEventListener("click", () => previewFile(file.path));
      row.appendChild(nameEl);

      const metaEl = document.createElement("span");
      metaEl.className = "output-manager-item-meta";
      metaEl.textContent = `${formatOutputFileSize(file.size)} · ${formatOutputFileDate(file.modified)}`;
      row.appendChild(metaEl);

      const deleteButton = document.createElement("button");
      deleteButton.className = "output-manager-item-delete";
      deleteButton.textContent = "✕";
      deleteButton.title = t("outputManagerDeleteFile");
      deleteButton.addEventListener("click", (event) => {
        event.stopPropagation();
        deleteFile(file.path);
      });
      row.appendChild(deleteButton);

      list.appendChild(row);
    }
  }

  async function refresh() {
    renderMessage(t("outputManagerLoading"));
    try {
      const response = await fetch(`/api/workspaces/${encodeURIComponent(workspaceName)}/output`);
      if (!response.ok) {
        renderMessage(t("outputManagerLoadError"));
        return;
      }
      const data = await response.json();
      renderFiles(data.files);
    } catch {
      renderMessage(t("outputManagerLoadError"));
    }
  }

  async function previewFile(path) {
    preview.hidden = false;
    preview.textContent = t("outputManagerLoading");
    const response = await fetch(
      `/api/workspaces/${encodeURIComponent(workspaceName)}/output/${encodeOutputFilePath(path)}`
    );
    if (!response.ok) {
      let detail = t("outputManagerPreviewError");
      try {
        const body = await response.json();
        if (body.detail) detail = body.detail;
      } catch {
        // response body wasn't JSON -- keep the generic message
      }
      preview.textContent = detail;
      return;
    }
    const body = await response.json();
    preview.textContent = body.content;
  }

  async function deleteFile(path) {
    if (!window.confirm(t("confirmDeleteOutputFile").replace("{name}", path))) return;
    const response = await fetch(
      `/api/workspaces/${encodeURIComponent(workspaceName)}/output/${encodeOutputFilePath(path)}`,
      { method: "DELETE" }
    );
    if (!response.ok) {
      setStatus(`${t("statusDeleteOutputFileError")}${response.status}`, "error");
      return;
    }
    preview.hidden = true;
    setStatus(t("statusDeletedOutputFile"), "ok");
    refresh();
  }

  refresh();
}
