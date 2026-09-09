function initMinimap(canvas, canvasEl) {
  const minimapEl = document.getElementById("minimap");
  if (!minimapEl) return;
  const ctx = minimapEl.getContext("2d");

  function computeWorldBounds(graph) {
    const nodes = graph._nodes;
    if (!nodes.length) return { minX: 0, minY: 0, maxX: 1000, maxY: 1000 };
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const node of nodes) {
      minX = Math.min(minX, node.pos[0]);
      minY = Math.min(minY, node.pos[1]);
      maxX = Math.max(maxX, node.pos[0] + node.size[0]);
      maxY = Math.max(maxY, node.pos[1] + node.size[1]);
    }
    const pad = 100;
    return { minX: minX - pad, minY: minY - pad, maxX: maxX + pad, maxY: maxY + pad };
  }

  function draw() {
    const graph = getActiveGraph();
    const w = minimapEl.width;
    const h = minimapEl.height;
    ctx.clearRect(0, 0, w, h);
    if (!graph) return;

    const bounds = computeWorldBounds(graph);
    const worldW = Math.max(bounds.maxX - bounds.minX, 1);
    const worldH = Math.max(bounds.maxY - bounds.minY, 1);
    const scaleX = w / worldW;
    const scaleY = h / worldH;

    ctx.fillStyle = "#3a3f4a";
    for (const node of graph._nodes) {
      const x = (node.pos[0] - bounds.minX) * scaleX;
      const y = (node.pos[1] - bounds.minY) * scaleY;
      const nw = Math.max(node.size[0] * scaleX, 2);
      const nh = Math.max(node.size[1] * scaleY, 2);
      ctx.fillRect(x, y, nw, nh);
    }

    const viewX = (-canvas.ds.offset[0] - bounds.minX) * scaleX;
    const viewY = (-canvas.ds.offset[1] - bounds.minY) * scaleY;
    const viewW = (canvasEl.clientWidth / canvas.ds.scale) * scaleX;
    const viewH = (canvasEl.clientHeight / canvas.ds.scale) * scaleY;
    ctx.strokeStyle = "#d9a44c";
    ctx.lineWidth = 1;
    ctx.strokeRect(viewX, viewY, viewW, viewH);
  }

  minimapEl.addEventListener("click", (event) => {
    const graph = getActiveGraph();
    if (!graph) return;
    const rect = minimapEl.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    const bounds = computeWorldBounds(graph);
    const worldW = Math.max(bounds.maxX - bounds.minX, 1);
    const worldH = Math.max(bounds.maxY - bounds.minY, 1);
    const worldX = bounds.minX + (clickX / minimapEl.width) * worldW;
    const worldY = bounds.minY + (clickY / minimapEl.height) * worldH;

    canvas.ds.offset[0] = -worldX + canvasEl.clientWidth / (2 * canvas.ds.scale);
    canvas.ds.offset[1] = -worldY + canvasEl.clientHeight / (2 * canvas.ds.scale);
    canvas.setDirty(true, true);
  });

  setInterval(draw, 200);
  draw();
}
