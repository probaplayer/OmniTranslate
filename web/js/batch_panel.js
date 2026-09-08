function initBatchPanel() {
  const toggleButton = document.getElementById("batch-toggle-button");
  const panel = document.getElementById("batch-panel");
  const startButton = document.getElementById("batch-start-button");
  const messageEl = document.getElementById("batch-message");

  toggleButton.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
  });

  startButton.addEventListener("click", () => {
    messageEl.textContent = t("batchUnavailable");
  });
}
