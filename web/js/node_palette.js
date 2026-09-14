// Renders the sidebar node list and wires HTML5 drag-and-drop so dropping a
// palette item onto the canvas creates that node type at the drop position.
// This is an alternative entry point to the canvas's existing right-click
// menu (still available) -- neither replaces the other.
function initNodePalette(nodeMetadataList, canvas, canvasEl) {
  const paletteEl = document.getElementById("node-palette");
  if (!paletteEl) return;

  const byCategory = {};
  for (const meta of nodeMetadataList) {
    if (!byCategory[meta.category]) byCategory[meta.category] = [];
    byCategory[meta.category].push(meta);
  }

  paletteEl.innerHTML = "";

  const header = document.createElement("div");
  header.className = "palette-header";
  header.setAttribute("data-i18n", "palette");
  header.textContent = t("palette");
  paletteEl.appendChild(header);

  const hint = document.createElement("div");
  hint.className = "palette-hint";
  hint.setAttribute("data-i18n", "paletteHint");
  hint.textContent = t("paletteHint");
  paletteEl.appendChild(hint);

  for (const [category, metas] of Object.entries(byCategory)) {
    const heading = document.createElement("div");
    heading.className = "palette-category";
    heading.textContent = category;
    paletteEl.appendChild(heading);

    for (const meta of metas) {
      const nodeTypeKey = `${meta.category}/${meta.type}`;
      const typeMeta = NODE_TYPE_META[meta.type] || NODE_TYPE_META_FALLBACK;

      const item = document.createElement("div");
      item.className = "palette-item";
      item.draggable = true;

      const icon = document.createElement("span");
      icon.className = "palette-item-icon";
      icon.style.color = typeMeta.color;
      icon.textContent = typeMeta.icon;
      item.appendChild(icon);

      const body = document.createElement("div");
      body.className = "palette-item-body";
      const name = document.createElement("div");
      name.className = "palette-item-name";
      name.textContent = meta.type;
      const desc = document.createElement("div");
      desc.className = "palette-item-desc";
      desc.textContent = nodeTypeDesc(meta.type);
      body.appendChild(name);
      body.appendChild(desc);
      item.appendChild(body);

      item.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", nodeTypeKey);
        event.dataTransfer.effectAllowed = "copy";
      });
      paletteEl.appendChild(item);
    }
  }

  if (!canvasEl.dataset.paletteDropWired) {
    canvasEl.dataset.paletteDropWired = "true";

    canvasEl.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    });

    canvasEl.addEventListener("drop", (event) => {
      event.preventDefault();
      const nodeTypeKey = event.dataTransfer.getData("text/plain");
      if (!nodeTypeKey) return;

      const activeGraph = getActiveGraph();
      if (!activeGraph) return;

      const node = LiteGraph.createNode(nodeTypeKey);
      if (!node) return;

      const rect = canvasEl.getBoundingClientRect();
      const canvasPos = [event.clientX - rect.left, event.clientY - rect.top];
      node.pos = canvas.convertCanvasToOffset(canvasPos);

      if (node.constructor.nodeType === "SaveTextFile" && !node.properties.path) {
        const defaultPath = defaultOutputPathFor(getActiveWorkspaceName());
        if (defaultPath) node.properties.path = defaultPath;
      }
      if (node.constructor.nodeType === "Provider" || node.constructor.nodeType === "GeminiProvider") {
        // The backend's own declared default ("600") is already non-empty,
        // unlike SaveTextFile's blank path default above, so there's no
        // falsy value to gate on here -- this only ever runs for a node
        // this handler just created, never one restored via configure().
        node.properties.timeout_seconds = defaultProviderTimeoutSeconds();
      }

      activeGraph.add(node);
      markActiveDirty();
      activeGraph.setDirtyCanvas(true, true);
    });
  }
}
