// Renders the sidebar node list and wires HTML5 drag-and-drop so dropping a
// palette item onto the canvas creates that node type at the drop position.
// This is an alternative entry point to the canvas's existing right-click
// menu (still available) -- neither replaces the other.
function initNodePalette(nodeMetadataList, graph, canvas, canvasEl) {
  const paletteEl = document.getElementById("node-palette");
  if (!paletteEl) return;

  const byCategory = {};
  for (const meta of nodeMetadataList) {
    if (!byCategory[meta.category]) byCategory[meta.category] = [];
    byCategory[meta.category].push(meta);
  }

  paletteEl.innerHTML = "";
  for (const [category, metas] of Object.entries(byCategory)) {
    const heading = document.createElement("div");
    heading.className = "palette-category";
    heading.textContent = category;
    paletteEl.appendChild(heading);

    for (const meta of metas) {
      const nodeTypeKey = `${meta.category}/${meta.type}`;
      const item = document.createElement("div");
      item.className = "palette-item";
      item.textContent = meta.type;
      item.draggable = true;
      item.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", nodeTypeKey);
        event.dataTransfer.effectAllowed = "copy";
      });
      paletteEl.appendChild(item);
    }
  }

  canvasEl.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  });

  canvasEl.addEventListener("drop", (event) => {
    event.preventDefault();
    const nodeTypeKey = event.dataTransfer.getData("text/plain");
    if (!nodeTypeKey) return;

    const node = LiteGraph.createNode(nodeTypeKey);
    if (!node) return;

    const rect = canvasEl.getBoundingClientRect();
    const canvasPos = [event.clientX - rect.left, event.clientY - rect.top];
    node.pos = canvas.convertCanvasToOffset(canvasPos);

    graph.add(node);
    graph.setDirtyCanvas(true, true);
  });
}
