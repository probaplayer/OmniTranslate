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
    brand: "OMNITRANSLATE STUDIO",
    runAllButton: "Chạy toàn bộ",
    saveButton: "Lưu",
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
    testProviderConnection: "Kiểm tra kết nối",
    statusTestingProvider: "Đang kiểm tra kết nối...",
    statusTestProviderOk: "Kết nối thành công",
    statusTestProviderError: "Lỗi kết nối: ",
    delete: "Xoá",
    logTitle: "Log chạy",
    clearLog: "Xoá log",
    logEmpty: "Chưa có gì.",
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
    deleteWorkspaceButton: "Xóa workspace",
    confirmDeleteWorkspace: "Xóa vĩnh viễn workspace '{name}'? Toàn bộ chương, bản dịch, glossary sẽ mất, không thể hoàn tác.",
    statusDeleteWorkspaceError: "Lỗi xóa workspace: ",
    statusDeletedWorkspace: "Đã xóa workspace",
    renameWorkspaceButton: "Đổi tên",
    promptRenameWorkspace: "Đặt tên mới cho workspace:",
    statusRenameWorkspaceError: "Lỗi đổi tên: ",
    statusRenamedWorkspace: "Đã đổi tên workspace",
    outputManagerButton: "Quản lý output",
    outputManagerTitle: "File output",
    outputManagerLoading: "Đang tải...",
    outputManagerLoadError: "Không tải được danh sách file",
    outputManagerEmpty: "Chưa có file output nào",
    outputManagerPreviewHint: "Bấm để xem nội dung",
    outputManagerPreviewError: "Không đọc được file",
    outputManagerDeleteFile: "Xoá file",
    confirmDeleteOutputFile: "Xoá file '{name}'? Không thể hoàn tác.",
    statusDeleteOutputFileError: "Lỗi xoá file: ",
    statusDeletedOutputFile: "Đã xoá file",
    settingsButton: "Cài đặt",
    settingsTitle: "Cài đặt",
    settingsThemeLabel: "Giao diện",
    settingsThemeDark: "Tối",
    settingsThemeLight: "Sáng",
    settingsLinkStyleLabel: "Kiểu đường nối",
    settingsLinkStyleCurved: "Cong",
    settingsLinkStyleOrthogonal: "Vuông góc",
    settingsOutputPathLabel: "Thư mục output mặc định",
    settingsOutputPathEmpty: "Chưa chọn — mỗi node SaveTextFile tự nhập đường dẫn riêng",
    settingsTimeoutLabel: "Timeout mặc định cho Provider (giây)",
    settingsClose: "Đóng",
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
    brand: "OMNITRANSLATE STUDIO",
    runAllButton: "Run all",
    saveButton: "Save",
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
    testProviderConnection: "Test connection",
    statusTestingProvider: "Testing connection...",
    statusTestProviderOk: "Connected successfully",
    statusTestProviderError: "Connection failed: ",
    delete: "Delete",
    logTitle: "Run log",
    clearLog: "Clear",
    logEmpty: "Nothing yet.",
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
    deleteWorkspaceButton: "Delete workspace",
    confirmDeleteWorkspace: "Permanently delete workspace '{name}'? All chapters, translations, and the glossary will be lost — this cannot be undone.",
    statusDeleteWorkspaceError: "Failed to delete workspace: ",
    statusDeletedWorkspace: "Workspace deleted",
    renameWorkspaceButton: "Rename",
    promptRenameWorkspace: "New name for this workspace:",
    statusRenameWorkspaceError: "Rename failed: ",
    statusRenamedWorkspace: "Workspace renamed",
    outputManagerButton: "Manage output",
    outputManagerTitle: "Output files",
    outputManagerLoading: "Loading...",
    outputManagerLoadError: "Could not load the file list",
    outputManagerEmpty: "No output files yet",
    outputManagerPreviewHint: "Click to preview",
    outputManagerPreviewError: "Could not read this file",
    outputManagerDeleteFile: "Delete file",
    confirmDeleteOutputFile: "Delete file '{name}'? This cannot be undone.",
    statusDeleteOutputFileError: "Failed to delete file: ",
    statusDeletedOutputFile: "File deleted",
    settingsButton: "Settings",
    settingsTitle: "Settings",
    settingsThemeLabel: "Theme",
    settingsThemeDark: "Dark",
    settingsThemeLight: "Light",
    settingsLinkStyleLabel: "Connector style",
    settingsLinkStyleCurved: "Curved",
    settingsLinkStyleOrthogonal: "Orthogonal",
    settingsOutputPathLabel: "Default output folder",
    settingsOutputPathEmpty: "Not set — each SaveTextFile node enters its own path",
    settingsTimeoutLabel: "Default Provider timeout (seconds)",
    settingsClose: "Close",
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
