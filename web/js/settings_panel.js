// App-wide preferences (theme, connector-line style, default output folder).
// These are client-only conveniences -- nothing here is sent to the backend
// or saved into a workspace's graph.json, so plain localStorage is enough.

const SETTINGS_STORAGE_KEY = "appSettings";
const DEFAULT_PROVIDER_TIMEOUT_SECONDS = "600";

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
    providerTimeoutSeconds: stored.providerTimeoutSeconds || DEFAULT_PROVIDER_TIMEOUT_SECONDS,
  };
}

let appSettings = loadSettings();

function persistSettings() {
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(appSettings));
}

// litegraph draws nodes/links directly on <canvas>, not through CSS, so
// switching data-theme alone (which only re-paints CSS-driven chrome) never
// touches the workspace itself -- these are the same colors as the CSS
// tokens in style.css's :root / :root[data-theme="light"], applied to
// litegraph's own color knobs instead.
const CANVAS_THEME_COLORS = {
  dark: {
    background: "#101216",
    nodeBg: "#1a1d23",
    nodeBorder: "#2a2f37",
    titleText: "#9aa1ab",
    bodyText: "#aaaaaa",
    link: "#d9a44c",
  },
  light: {
    background: "#f4f3f0",
    nodeBg: "#ffffff",
    nodeBorder: "#d8d5cd",
    titleText: "#55534c",
    bodyText: "#33322e",
    link: "#b5792e",
  },
};

function applyTheme(canvas) {
  document.documentElement.setAttribute("data-theme", appSettings.theme);

  const colors = CANVAS_THEME_COLORS[appSettings.theme] || CANVAS_THEME_COLORS.dark;
  LiteGraph.NODE_DEFAULT_BGCOLOR = colors.nodeBg;
  LiteGraph.NODE_DEFAULT_COLOR = colors.nodeBorder;
  LiteGraph.NODE_TEXT_COLOR = colors.bodyText;
  if (!canvas) return;
  // node_title_color/default_link_color are copied from the LiteGraph
  // globals only once, at LGraphCanvas construction time -- past that point
  // only the instance properties themselves have any effect on drawing.
  canvas.node_title_color = colors.titleText;
  canvas.default_link_color = colors.link;
  canvas.clear_background_color = colors.background;
  canvas.setDirty(true, true);
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

// Used to prefill a freshly-dropped Provider node's `timeout_seconds`
// property -- like defaultOutputPathFor, never called on nodes restored
// from a saved graph, so a workspace saved with a different value keeps it.
function defaultProviderTimeoutSeconds() {
  return appSettings.providerTimeoutSeconds || DEFAULT_PROVIDER_TIMEOUT_SECONDS;
}

function initSettingsPanel(canvas) {
  applyTheme(canvas);
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
        applyTheme(canvas);
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

  const timeoutRow = document.createElement("div");
  timeoutRow.className = "settings-row";
  const timeoutLabel = document.createElement("label");
  timeoutLabel.textContent = t("settingsTimeoutLabel");
  timeoutRow.appendChild(timeoutLabel);

  const timeoutInput = document.createElement("input");
  timeoutInput.type = "text";
  timeoutInput.inputMode = "numeric";
  timeoutInput.className = "settings-text-input";
  timeoutInput.value = appSettings.providerTimeoutSeconds;
  timeoutInput.addEventListener("change", () => {
    const parsed = parseFloat(timeoutInput.value);
    appSettings.providerTimeoutSeconds =
      Number.isFinite(parsed) && parsed > 0
        ? String(parsed)
        : DEFAULT_PROVIDER_TIMEOUT_SECONDS;
    timeoutInput.value = appSettings.providerTimeoutSeconds;
    persistSettings();
  });
  timeoutRow.appendChild(timeoutInput);
  modal.appendChild(timeoutRow);

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
