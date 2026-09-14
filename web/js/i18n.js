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
    brand: "DỊCH XƯỞNG",
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
    promptWorkspaceName: "Đặt tên cho workspace:",
    statusInvalidWorkspaceName: "Tên workspace không hợp lệ — chỉ dùng chữ, số, - và _",
    statusSaveBeforeRun: "Hãy lưu workspace trước khi chạy",
    newTabButton: "+ Workspace mới",
    untitledWorkspace: "Chưa lưu",
    confirmDiscardTab: "Đóng workspace này? Các thay đổi chưa lưu sẽ mất.",
    palette: "Thư viện node",
    paletteHint: "Kéo vào canvas để thêm.",
    stIdle: "Chờ",
    stRunning: "Đang chạy",
    stDone: "Xong",
    stError: "Lỗi",
    openWorkspaceButton: "Mở workspace...",
    noOtherWorkspaces: "Không có workspace nào khác",
    pathPickerSelect: "Chọn thư mục này",
    pathPickerCancel: "Hủy",
    pathPickerDrives: "Ổ đĩa",
    pathPickerLoadError: "Không kết nối được tới server.",
    browseButton: "Duyệt...",
    agentTemplateButton: "Chọn agent...",
    agentTemplateWorkspaceOption: "Tùy chỉnh riêng cho workspace này",
    agentTemplateCancel: "Hủy",
    agentTemplateLoadError: "Không kết nối được tới server.",
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
    brand: "DICH XUONG",
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
    promptWorkspaceName: "Name this workspace:",
    statusInvalidWorkspaceName: "Invalid workspace name — letters, digits, - and _ only",
    statusSaveBeforeRun: "Save the workspace before running",
    newTabButton: "+ New workspace",
    untitledWorkspace: "Untitled",
    confirmDiscardTab: "Close this workspace? Unsaved changes will be lost.",
    palette: "Node library",
    paletteHint: "Drag onto the canvas to add.",
    stIdle: "Idle",
    stRunning: "Running",
    stDone: "Done",
    stError: "Error",
    openWorkspaceButton: "Open workspace...",
    noOtherWorkspaces: "No other workspaces",
    pathPickerSelect: "Select this folder",
    pathPickerCancel: "Cancel",
    pathPickerDrives: "Drives",
    pathPickerLoadError: "Could not reach the server.",
    browseButton: "Browse...",
    agentTemplateButton: "Choose agent...",
    agentTemplateWorkspaceOption: "Custom for this workspace",
    agentTemplateCancel: "Cancel",
    agentTemplateLoadError: "Could not reach the server.",
  },
};

const NODE_TYPE_LABELS = {
  vi: {
    LoadTextFile: "ĐỌC FILE", SaveTextFile: "GHI FILE", TextPreview: "XEM TRƯỚC",
    Note: "GHI CHÚ", Provider: "NGUỒN MODEL", LoadAgentFile: "ĐỌC AGENT",
    SaveAgentFile: "GHI AGENT", Translate: "DỊCH",
    LoadGlossary: "ĐỌC GLOSSARY", SaveGlossary: "GHI GLOSSARY", LookupGlossary: "TRA GLOSSARY",
    RecordChapter: "GHI CHƯƠNG", ExtractGlossary: "TRÍCH GLOSSARY",
    EvaluateAndFixChapters: "RÀ SOÁT CHƯƠNG",
  },
  en: {
    LoadTextFile: "LOAD FILE", SaveTextFile: "SAVE FILE", TextPreview: "PREVIEW",
    Note: "NOTE", Provider: "MODEL SOURCE", LoadAgentFile: "LOAD AGENT",
    SaveAgentFile: "SAVE AGENT", Translate: "TRANSLATE",
    LoadGlossary: "LOAD GLOSSARY", SaveGlossary: "SAVE GLOSSARY", LookupGlossary: "LOOKUP GLOSSARY",
    RecordChapter: "RECORD CHAPTER", ExtractGlossary: "EXTRACT GLOSSARY",
    EvaluateAndFixChapters: "EVALUATE & FIX CHAPTERS",
  },
};

const NODE_TYPE_DESCS = {
  vi: {
    LoadTextFile: "Đọc file text", SaveTextFile: "Ghi file text",
    TextPreview: "Xem trước nội dung", Note: "Ghi chú tự do",
    Provider: "Kết nối API/LM Studio", LoadAgentFile: "Đọc file agent",
    SaveAgentFile: "Ghi file agent", Translate: "Dịch văn bản",
    LoadGlossary: "Đọc glossary.json", SaveGlossary: "Ghi glossary.json",
    LookupGlossary: "Tìm thuật ngữ liên quan", RecordChapter: "Ghi nhận 1 chương đã dịch",
    ExtractGlossary: "Trích & giải quyết xung đột thuật ngữ",
    EvaluateAndFixChapters: "Rà soát & sửa chương gần đây",
  },
  en: {
    LoadTextFile: "Read a text file", SaveTextFile: "Write a text file",
    TextPreview: "Preview text content", Note: "Freeform note",
    Provider: "API or LM Studio connection", LoadAgentFile: "Read the agent file",
    SaveAgentFile: "Write the agent file", Translate: "Translate text",
    LoadGlossary: "Load glossary.json", SaveGlossary: "Save glossary.json",
    LookupGlossary: "Find relevant terms", RecordChapter: "Record a translated chapter",
    ExtractGlossary: "Extract terms & resolve conflicts",
    EvaluateAndFixChapters: "Review & fix recent chapters",
  },
};

function nodeTypeLabel(type) {
  const table = NODE_TYPE_LABELS[currentLang()] || NODE_TYPE_LABELS.vi;
  return table[type] || type;
}

function nodeTypeDesc(type) {
  const table = NODE_TYPE_DESCS[currentLang()] || NODE_TYPE_DESCS.vi;
  return table[type] || "";
}

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
