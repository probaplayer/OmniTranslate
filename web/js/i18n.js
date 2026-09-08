const STR = {
  vi: {
    pickerTitle: "Chọn workspace",
    createWorkspaceTitle: "Tạo workspace mới",
    namePlaceholder: "Tên workspace (vd: truyen-a)",
    sourceLangPlaceholder: "Ngôn ngữ nguồn (vd: ja)",
    targetLangPlaceholder: "Ngôn ngữ đích (vd: vi)",
    createButton: "Tạo",
    nameHint:
      "Tên workspace chỉ được chứa chữ cái, chữ số, dấu gạch ngang (-) và gạch dưới (_) — không có dấu cách hay ký tự đặc biệt.",
    loadWorkspacesError: "Không thể tải danh sách workspace — kiểm tra server có đang chạy không.",
    createWorkspaceGenericError: "Không tạo được workspace",
    createWorkspaceServerError: "Không tạo được workspace — kiểm tra server.",
    backToWorkspaces: "← Workspaces",
    runAllButton: "Chạy toàn bộ",
    saveButton: "Lưu",
    batchToggleButton: "Hàng loạt",
    statusLoadNodesError: "Lỗi tải danh sách node: ",
    statusLoadWorkspaceError: "Lỗi tải workspace: ",
    statusSaveError: "Lỗi lưu: ",
    statusSaved: "Đã lưu",
    statusWsError: "Lỗi kết nối WebSocket",
    statusRunFinished: "Hoàn tất",
    statusValidationError: "Lỗi: ",
    statusRuntimeError: "Lỗi thực thi: ",
    inspectorEmpty: "Chọn 1 node trên canvas để xem chi tiết.",
    nodeName: "Tên node",
    runNode: "Chạy node này",
    delete: "Xoá",
    logTitle: "Log chạy",
    clearLog: "Xoá log",
    logEmpty: "Chưa có gì.",
    batchTitle: "Chạy hàng loạt chương",
    batchFrom: "Từ chương",
    batchTo: "Đến chương",
    batchConcurrency: "Chạy song song",
    batchStart: "Bắt đầu",
    batchUnavailable: "Cần Sub-project A2 (Loop Group) — chưa khả dụng.",
  },
  en: {
    pickerTitle: "Select workspace",
    createWorkspaceTitle: "Create new workspace",
    namePlaceholder: "Workspace name (e.g. novel-a)",
    sourceLangPlaceholder: "Source language (e.g. ja)",
    targetLangPlaceholder: "Target language (e.g. vi)",
    createButton: "Create",
    nameHint:
      "Workspace name may only contain letters, digits, hyphen (-) and underscore (_) — no spaces or special characters.",
    loadWorkspacesError: "Could not load the workspace list — check that the server is running.",
    createWorkspaceGenericError: "Could not create workspace",
    createWorkspaceServerError: "Could not create workspace — check the server.",
    backToWorkspaces: "← Workspaces",
    runAllButton: "Run all",
    saveButton: "Save",
    batchToggleButton: "Batch",
    statusLoadNodesError: "Failed to load node list: ",
    statusLoadWorkspaceError: "Failed to load workspace: ",
    statusSaveError: "Save failed: ",
    statusSaved: "Saved",
    statusWsError: "WebSocket connection error",
    statusRunFinished: "Done",
    statusValidationError: "Error: ",
    statusRuntimeError: "Runtime error: ",
    inspectorEmpty: "Select a node on the canvas to inspect it.",
    nodeName: "Node name",
    runNode: "Run this node",
    delete: "Delete",
    logTitle: "Run log",
    clearLog: "Clear",
    logEmpty: "Nothing yet.",
    batchTitle: "Batch run chapters",
    batchFrom: "From chapter",
    batchTo: "To chapter",
    batchConcurrency: "Parallel runs",
    batchStart: "Start",
    batchUnavailable: "Requires Sub-project A2 (Loop Group) — not available yet.",
  },
};

function currentLang() {
  return localStorage.getItem("lang") || "vi";
}

function t(key) {
  const table = STR[currentLang()] || STR.vi;
  return table[key] || key;
}

function setLang(lang) {
  localStorage.setItem("lang", lang);
  applyTranslations();
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

applyTranslations();
