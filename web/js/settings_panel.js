// App-wide preferences (theme, connector-line style, default output folder).
// These are client-only conveniences -- nothing here is sent to the backend
// or saved into a workspace's graph.json, so plain localStorage is enough.

const SETTINGS_STORAGE_KEY = "appSettings";

function loadSettings() {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}");
  } catch {
    stored = {};
  }
  return {
    theme: stored.theme === "light" ? "light" : "dark",
    linkStyle: stored.linkStyle === "orthogonal" ? "orthogonal" : "curved",
    outputRoot: stored.outputRoot || "",
  };
}

let appSettings = loadSettings();

function persistSettings() {
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(appSettings));
}

function applyTheme() {
  document.documentElement.setAttribute("data-theme", appSettings.theme);
}

function applyLinkStyle(canvas) {
  if (appSettings.linkStyle === "orthogonal") {
    canvas.links_render_mode = LiteGraph.STRAIGHT_LINK;
    canvas.render_curved_connections = false;
  } else {
    canvas.links_render_mode = LiteGraph.SPLINE_LINK;
    canvas.render_curved_connections = true;
  }
  canvas.setDirty(true, true);
}

// Used to prefill a freshly-dropped SaveTextFile node's `path` property --
// never called on nodes restored from a saved graph, so it can't clobber a
// path the user already chose. Falls back to "" (no prefill) when no root
// is configured yet, leaving the field exactly as blank as it is today.
function defaultOutputPathFor(workspaceName) {
  if (!appSettings.outputRoot || !workspaceName) return "";
  const sep = appSettings.outputRoot.includes("/") ? "/" : "\\";
  const root = appSettings.outputRoot.endsWith(sep)
    ? appSettings.outputRoot
    : `${appSettings.outputRoot}${sep}`;
  return `${root}${workspaceName}${sep}`;
}

function initSettingsPanel(canvas) {
  applyTheme();
  applyLinkStyle(canvas);
  const button = document.getElementById("settings-button");
  if (button) button.addEventListener("click", () => openSettingsPanel(canvas));
}

function closeSettingsPanel() {
  const overlay = document.getElementById("settings-panel-overlay");
  if (overlay) overlay.remove();
}

function openSettingsPanel(canvas) {
  closeSettingsPanel();

  const overlay = document.createElement("div");
  overlay.id = "settings-panel-overlay";
  overlay.className = "settings-panel-overlay";
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeSettingsPanel();
  });

  const modal = document.createElement("div");
  modal.className = "settings-panel-modal";

  const title = document.createElement("div");
  title.className = "settings-panel-title";
  title.textContent = t("settingsTitle");
  modal.appendChild(title);

  modal.appendChild(
    buildSegmentedRow(
      t("settingsThemeLabel"),
      [
        { value: "dark", label: t("settingsThemeDark") },
        { value: "light", label: t("settingsThemeLight") },
      ],
      appSettings.theme,
      (value) => {
        appSettings.theme = value;
        persistSettings();
        applyTheme();
      }
    )
  );

  modal.appendChild(
    buildSegmentedRow(
      t("settingsLinkStyleLabel"),
      [
        { value: "curved", label: t("settingsLinkStyleCurved") },
        { value: "orthogonal", label: t("settingsLinkStyleOrthogonal") },
      ],
      appSettings.linkStyle,
      (value) => {
        appSettings.linkStyle = value;
        persistSettings();
        applyLinkStyle(canvas);
      }
    )
  );

  const pathRow = document.createElement("div");
  pathRow.className = "settings-row";
  const pathLabel = document.createElement("label");
  pathLabel.textContent = t("settingsOutputPathLabel");
  pathRow.appendChild(pathLabel);

  const pathDisplay = document.createElement("div");
  pathDisplay.className = "settings-path-display";
  pathDisplay.textContent = appSettings.outputRoot || t("settingsOutputPathEmpty");
  pathRow.appendChild(pathDisplay);

  const browseButton = document.createElement("button");
  browseButton.className = "inspector-browse-button";
  browseButton.textContent = t("browseButton");
  browseButton.addEventListener("click", () => {
    openPathPicker(appSettings.outputRoot, (chosen) => {
      appSettings.outputRoot = chosen;
      persistSettings();
      pathDisplay.textContent = chosen || t("settingsOutputPathEmpty");
    });
  });
  pathRow.appendChild(browseButton);
  modal.appendChild(pathRow);

  const actions = document.createElement("div");
  actions.className = "settings-panel-actions";
  const closeButton = document.createElement("button");
  closeButton.textContent = t("settingsClose");
  closeButton.addEventListener("click", closeSettingsPanel);
  actions.appendChild(closeButton);
  modal.appendChild(actions);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

function buildSegmentedRow(labelText, options, activeValue, onChange) {
  const row = document.createElement("div");
  row.className = "settings-row";

  const label = document.createElement("label");
  label.textContent = labelText;
  row.appendChild(label);

  const segmented = document.createElement("div");
  segmented.className = "settings-segmented";
  const buttons = [];
  for (const option of options) {
    const button = document.createElement("button");
    button.className = "settings-segmented-button" + (option.value === activeValue ? " active" : "");
    button.textContent = option.label;
    button.addEventListener("click", () => {
      onChange(option.value);
      for (const b of buttons) b.classList.remove("active");
      button.classList.add("active");
    });
    buttons.push(button);
    segmented.appendChild(button);
  }
  row.appendChild(segmented);
  return row;
}
