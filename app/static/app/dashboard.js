const TOKEN_KEY = "cloudvault.tokens";

const state = {
  tokens: readTokens(),
  user: null,
  folders: [],
  files: [],
  currentFolder: null,
  modalResolver: null,
  toastTimer: null,
};

const el = {
  authPanel: document.querySelector("#authPanel"),
  appPanel: document.querySelector("#appPanel"),
  loginTab: document.querySelector("#loginTab"),
  registerTab: document.querySelector("#registerTab"),
  loginForm: document.querySelector("#loginForm"),
  registerForm: document.querySelector("#registerForm"),
  logoutButton: document.querySelector("#logoutButton"),
  currentUser: document.querySelector("#currentUser"),
  avatar: document.querySelector("#avatar"),
  uploadButton: document.querySelector("#uploadButton"),
  fileInput: document.querySelector("#fileInput"),
  newFolderButton: document.querySelector("#newFolderButton"),
  allFilesButton: document.querySelector("#allFilesButton"),
  folderTree: document.querySelector("#folderTree"),
  folderGrid: document.querySelector("#folderGrid"),
  fileTableBody: document.querySelector("#fileTableBody"),
  fileCount: document.querySelector("#fileCount"),
  folderCount: document.querySelector("#folderCount"),
  totalSize: document.querySelector("#totalSize"),
  locationLabel: document.querySelector("#locationLabel"),
  viewTitle: document.querySelector("#viewTitle"),
  searchInput: document.querySelector("#searchInput"),
  refreshButton: document.querySelector("#refreshButton"),
  toast: document.querySelector("#toast"),
  modalBackdrop: document.querySelector("#modalBackdrop"),
  modalForm: document.querySelector("#modalForm"),
  modalTitle: document.querySelector("#modalTitle"),
  modalLabel: document.querySelector("#modalLabel"),
  modalInput: document.querySelector("#modalInput"),
  modalSelect: document.querySelector("#modalSelect"),
  modalSubmit: document.querySelector("#modalSubmit"),
  modalCancel: document.querySelector("#modalCancel"),
  modalClose: document.querySelector("#modalClose"),
};

init();

function init() {
  bindAuthForms();
  bindAppActions();
  bindModal();

  if (state.tokens?.access) {
    showApp();
    refreshVault();
  } else {
    showAuth();
  }
}

function bindAuthForms() {
  el.loginTab.addEventListener("click", () => setAuthMode("login"));
  el.registerTab.addEventListener("click", () => setAuthMode("register"));

  el.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = formPayload(el.loginForm);
    try {
      const tokens = await publicApi("/api/auth/login/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      saveTokens(tokens);
      showApp();
      await refreshVault();
    } catch (error) {
      notify(error.message);
    }
  });

  el.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = formPayload(el.registerForm);
    try {
      const response = await publicApi("/api/auth/register/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      saveTokens(response.tokens);
      showApp();
      await refreshVault();
    } catch (error) {
      notify(error.message);
    }
  });
}

function bindAppActions() {
  el.logoutButton.addEventListener("click", logout);
  el.refreshButton.addEventListener("click", refreshVault);
  el.searchInput.addEventListener("input", render);

  el.allFilesButton.addEventListener("click", async () => {
    state.currentFolder = null;
    await loadFiles();
    render();
  });

  el.newFolderButton.addEventListener("click", async () => {
    const folderName = await promptValue("New folder", "Folder name", "Create");
    if (!folderName) return;

    const body = { folder_name: folderName };
    if (state.currentFolder) body.parent_folder = state.currentFolder;

    try {
      await api("/api/folders/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      await refreshVault();
      notify("Folder created.");
    } catch (error) {
      notify(error.message);
    }
  });

  el.uploadButton.addEventListener("click", () => {
    el.fileInput.value = "";
    el.fileInput.click();
  });

  el.fileInput.addEventListener("change", async () => {
    const file = el.fileInput.files[0];
    if (!file) return;

    const form = new FormData();
    form.append("file", file);
    if (state.currentFolder) form.append("folder", state.currentFolder);

    try {
      await api("/api/files/", {
        method: "POST",
        body: form,
      });
      await refreshVault();
      notify("File uploaded.");
    } catch (error) {
      notify(error.message);
    }
  });
}

function bindModal() {
  el.modalForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = el.modalSelect.classList.contains("is-hidden")
      ? el.modalInput.value.trim()
      : el.modalSelect.value;
    closeModal(value);
  });
  el.modalCancel.addEventListener("click", () => closeModal(null));
  el.modalClose.addEventListener("click", () => closeModal(null));
  el.modalBackdrop.addEventListener("click", (event) => {
    if (event.target === el.modalBackdrop) closeModal(null);
  });
}

function setAuthMode(mode) {
  const isLogin = mode === "login";
  el.loginTab.classList.toggle("is-active", isLogin);
  el.registerTab.classList.toggle("is-active", !isLogin);
  el.loginForm.classList.toggle("is-hidden", !isLogin);
  el.registerForm.classList.toggle("is-hidden", isLogin);
}

function showAuth() {
  el.appPanel.classList.add("is-hidden");
  el.authPanel.classList.remove("is-hidden");
}

function showApp() {
  el.authPanel.classList.add("is-hidden");
  el.appPanel.classList.remove("is-hidden");
}

async function refreshVault() {
  try {
    state.user = await api("/api/whoami");
    el.currentUser.textContent = state.user.username;
    el.avatar.textContent = state.user.username.slice(0, 1).toUpperCase();
    await Promise.all([loadFolders(), loadFiles()]);
    render();
  } catch (error) {
    notify(error.message);
    if (error.status === 401) logout();
  }
}

async function loadFolders() {
  state.folders = await api("/api/folders/");
}

async function loadFiles() {
  if (state.currentFolder) {
    state.files = await api(`/api/folders/${state.currentFolder}/files/`);
  } else {
    const files = await api("/api/files/?folder=root");
    state.files = files.filter((file) => !file.folder);
  }
}

function render() {
  const currentFolder = getCurrentFolder();
  const query = el.searchInput.value.trim().toLowerCase();
  const visibleFolders = getVisibleFolders().filter((folder) =>
    folder.folder_name.toLowerCase().includes(query)
  );
  const visibleFiles = state.files.filter((file) =>
    file.file_name.toLowerCase().includes(query)
  );

  el.locationLabel.textContent = currentFolder ? "Folder" : "Vault";
  el.viewTitle.textContent = currentFolder ? currentFolder.folder_name : "Root";
  el.fileCount.textContent = String(state.files.length);
  el.folderCount.textContent = String(getVisibleFolders().length);
  el.totalSize.textContent = formatBytes(
    state.files.reduce((total, file) => total + Number(file.file_size || 0), 0)
  );

  renderFolderTree();
  renderFolderGrid(visibleFolders);
  renderFiles(visibleFiles);
}

function renderFolderTree() {
  el.folderTree.replaceChildren();
  el.allFilesButton.classList.toggle("is-active", !state.currentFolder);

  const childrenByParent = groupFoldersByParent();
  const fragment = document.createDocumentFragment();
  appendFolderRows(fragment, childrenByParent.get(null) || [], childrenByParent, 0);
  el.folderTree.appendChild(fragment);
}

function appendFolderRows(parent, folders, childrenByParent, depth) {
  folders
    .slice()
    .sort((a, b) => a.folder_name.localeCompare(b.folder_name))
    .forEach((folder) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "folder-row";
      row.style.paddingLeft = `${10 + depth * 16}px`;
      row.classList.toggle("is-active", state.currentFolder === folder.folder_uuid);
      row.innerHTML = `<span class="folder-icon" aria-hidden="true"></span><span></span>`;
      row.querySelector("span:last-child").textContent = folder.folder_name;
      row.addEventListener("click", async () => {
        state.currentFolder = folder.folder_uuid;
        await loadFiles();
        render();
      });
      parent.appendChild(row);
      appendFolderRows(
        parent,
        childrenByParent.get(folder.folder_uuid) || [],
        childrenByParent,
        depth + 1
      );
    });
}

function renderFolderGrid(folders) {
  el.folderGrid.replaceChildren();

  if (!folders.length) {
    el.folderGrid.appendChild(emptyState("No folders here."));
    return;
  }

  const fragment = document.createDocumentFragment();
  folders.forEach((folder) => {
    const tile = document.createElement("article");
    tile.className = "folder-tile";

    const main = document.createElement("button");
    main.type = "button";
    main.className = "folder-row";
    main.innerHTML = `<span class="folder-icon" aria-hidden="true"></span><span class="folder-tile-title"></span>`;
    main.querySelector(".folder-tile-title").textContent = folder.folder_name;
    main.addEventListener("click", async () => {
      state.currentFolder = folder.folder_uuid;
      await loadFiles();
      render();
    });

    const actions = document.createElement("div");
    actions.className = "item-actions";
    if (folder.is_owner) {
      actions.append(
        actionButton("Rename", () => renameFolder(folder)),
        actionButton("Share", () => shareFolder(folder)),
        actionButton("Delete", () => deleteFolder(folder), "danger-button")
      );
    }

    tile.append(main, actions);
    fragment.appendChild(tile);
  });

  el.folderGrid.appendChild(fragment);
}

function renderFiles(files) {
  el.fileTableBody.replaceChildren();

  if (!files.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.appendChild(emptyState("No files to show."));
    row.appendChild(cell);
    el.fileTableBody.appendChild(row);
    return;
  }

  const fragment = document.createDocumentFragment();
  files.forEach((file) => {
    const row = document.createElement("tr");
    row.append(
      fileNameCell(file),
      textCell(file.file_type || "Unknown"),
      textCell(formatBytes(file.file_size)),
      textCell(formatDate(file.uploaded_at)),
      fileActionsCell(file)
    );
    fragment.appendChild(row);
  });
  el.fileTableBody.appendChild(fragment);
}

function fileNameCell(file) {
  const cell = document.createElement("td");
  const wrap = document.createElement("div");
  wrap.className = "file-name-cell";
  const name = document.createElement("span");
  name.className = "file-name";
  name.textContent = file.file_name;
  const owner = document.createElement("span");
  owner.className = "file-owner";
  owner.textContent = file.is_owner ? "Owner" : `Shared by ${file.owner_username}`;
  wrap.append(name, owner);
  cell.appendChild(wrap);
  return cell;
}

function fileActionsCell(file) {
  const cell = document.createElement("td");
  const actions = document.createElement("div");
  actions.className = "item-actions";
  actions.appendChild(actionButton("Download", () => downloadFile(file)));
  if (file.is_owner) {
    actions.append(
      actionButton("Rename", () => renameFile(file)),
      actionButton("Move", () => moveFile(file)),
      actionButton("Share", () => shareFile(file)),
      actionButton("Delete", () => deleteFile(file), "danger-button")
    );
  }
  cell.appendChild(actions);
  return cell;
}

function textCell(value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  return cell;
}

function actionButton(label, onClick, className = "ghost-button") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

async function renameFolder(folder) {
  const folderName = await promptValue("Rename folder", "Folder name", "Rename", folder.folder_name);
  if (!folderName) return;

  try {
    await api(`/api/folders/${folder.folder_uuid}/`, {
      method: "PATCH",
      body: JSON.stringify({ folder_name: folderName }),
    });
    await refreshVault();
    notify("Folder renamed.");
  } catch (error) {
    notify(error.message);
  }
}

async function shareFolder(folder) {
  const username = await promptValue("Share folder", "Username", "Share");
  if (!username) return;

  try {
    await api(`/api/folders/${folder.folder_uuid}/share/`, {
      method: "POST",
      body: JSON.stringify({ username }),
    });
    notify("Folder shared.");
  } catch (error) {
    notify(error.message);
  }
}

async function deleteFolder(folder) {
  if (!window.confirm(`Delete folder "${folder.folder_name}"?`)) return;

  try {
    await api(`/api/folders/${folder.folder_uuid}/`, { method: "DELETE" });
    if (state.currentFolder === folder.folder_uuid) state.currentFolder = null;
    await refreshVault();
    notify("Folder deleted.");
  } catch (error) {
    notify(error.message);
  }
}

async function renameFile(file) {
  const fileName = await promptValue("Rename file", "File name", "Rename", file.file_name);
  if (!fileName) return;

  try {
    await api(`/api/files/${file.file_uuid}/`, {
      method: "PATCH",
      body: JSON.stringify({ file_name: fileName }),
    });
    await refreshVault();
    notify("File renamed.");
  } catch (error) {
    notify(error.message);
  }
}

async function moveFile(file) {
  const folderId = await promptChoice(
    "Move file",
    "Destination",
    "Move",
    folderChoices(),
    file.folder || ""
  );
  if (folderId === null) return;

  try {
    await api(`/api/files/${file.file_uuid}/`, {
      method: "PATCH",
      body: JSON.stringify({ folder: folderId || null }),
    });
    await refreshVault();
    notify("File moved.");
  } catch (error) {
    notify(error.message);
  }
}

async function shareFile(file) {
  const username = await promptValue("Share file", "Username", "Share");
  if (!username) return;

  try {
    await api(`/api/files/${file.file_uuid}/share/`, {
      method: "POST",
      body: JSON.stringify({ username }),
    });
    notify("File shared.");
  } catch (error) {
    notify(error.message);
  }
}

async function deleteFile(file) {
  if (!window.confirm(`Delete file "${file.file_name}"?`)) return;

  try {
    await api(`/api/files/${file.file_uuid}/`, { method: "DELETE" });
    await refreshVault();
    notify("File deleted.");
  } catch (error) {
    notify(error.message);
  }
}

async function downloadFile(file) {
  try {
    const response = await apiRaw(`/api/files/${file.file_uuid}/download/`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = file.file_name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    notify(error.message);
  }
}

function groupFoldersByParent() {
  const childrenByParent = new Map();
  state.folders.forEach((folder) => {
    const parent = folder.parent_folder || null;
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(folder);
  });
  return childrenByParent;
}

function getVisibleFolders() {
  if (!state.currentFolder) {
    return state.folders.filter((folder) => !folder.parent_folder);
  }
  return state.folders.filter((folder) => folder.parent_folder === state.currentFolder);
}

function getCurrentFolder() {
  return state.folders.find((folder) => folder.folder_uuid === state.currentFolder);
}

function emptyState(message) {
  const node = document.createElement("div");
  node.className = "empty-state";
  node.textContent = message;
  return node;
}

async function promptValue(title, label, submitLabel, initialValue = "") {
  el.modalTitle.textContent = title;
  el.modalLabel.textContent = label;
  el.modalSubmit.textContent = submitLabel;
  el.modalInput.disabled = false;
  el.modalInput.required = true;
  el.modalInput.classList.remove("is-hidden");
  el.modalSelect.disabled = true;
  el.modalSelect.classList.add("is-hidden");
  el.modalInput.value = initialValue;
  el.modalBackdrop.classList.remove("is-hidden");
  el.modalInput.focus();
  el.modalInput.select();

  return new Promise((resolve) => {
    state.modalResolver = resolve;
  });
}

async function promptChoice(title, label, submitLabel, choices, initialValue = "") {
  el.modalTitle.textContent = title;
  el.modalLabel.textContent = label;
  el.modalSubmit.textContent = submitLabel;
  el.modalInput.disabled = true;
  el.modalInput.required = false;
  el.modalInput.classList.add("is-hidden");
  el.modalSelect.disabled = false;
  el.modalSelect.classList.remove("is-hidden");
  el.modalSelect.replaceChildren();

  choices.forEach((choice) => {
    const option = document.createElement("option");
    option.value = choice.value;
    option.textContent = choice.label;
    el.modalSelect.appendChild(option);
  });

  el.modalSelect.value = initialValue;
  el.modalBackdrop.classList.remove("is-hidden");
  el.modalSelect.focus();

  return new Promise((resolve) => {
    state.modalResolver = resolve;
  });
}

function closeModal(value) {
  el.modalBackdrop.classList.add("is-hidden");
  if (state.modalResolver) {
    state.modalResolver(value);
    state.modalResolver = null;
  }
}

async function publicApi(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  return parseResponse(response);
}

async function api(path, options = {}) {
  const response = await apiRaw(path, options);
  return parseResponse(response);
}

async function apiRaw(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${state.tokens?.access || ""}`);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (response.status === 401 && retry && state.tokens?.refresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiRaw(path, options, false);
  }

  if (!response.ok) {
    await parseResponse(response);
  }

  return response;
}

async function refreshAccessToken() {
  try {
    const tokens = await publicApi("/api/auth/refresh/", {
      method: "POST",
      body: JSON.stringify({ refresh: state.tokens.refresh }),
    });
    saveTokens({ ...state.tokens, access: tokens.access });
    return true;
  } catch {
    return false;
  }
}

async function parseResponse(response) {
  if (response.status === 204) return null;

  const contentType = response.headers.get("Content-Type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (response.ok) return data;

  const error = new Error(responseErrorMessage(data));
  error.status = response.status;
  error.data = data;
  throw error;
}

function responseErrorMessage(data) {
  if (!data) return "Request failed.";
  if (typeof data === "string") return data;
  if (data.detail) return String(data.detail);
  const firstKey = Object.keys(data)[0];
  const value = data[firstKey];
  if (Array.isArray(value)) return `${firstKey}: ${value.join(" ")}`;
  if (typeof value === "string") return `${firstKey}: ${value}`;
  return "Request failed.";
}

function saveTokens(tokens) {
  state.tokens = tokens;
  window.localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

function readTokens() {
  try {
    return JSON.parse(window.localStorage.getItem(TOKEN_KEY));
  } catch {
    return null;
  }
}

function logout() {
  state.tokens = null;
  state.user = null;
  state.folders = [];
  state.files = [];
  state.currentFolder = null;
  window.localStorage.removeItem(TOKEN_KEY);
  showAuth();
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = bytes / 1024;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(new Date(value));
}

function folderChoices() {
  const folderMap = new Map(
    state.folders.map((folder) => [folder.folder_uuid, folder])
  );
  const folders = state.folders
    .filter((folder) => folder.is_owner)
    .map((folder) => ({
      value: folder.folder_uuid,
      label: folderPath(folder, folderMap),
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

  return [{ value: "", label: "Root" }, ...folders];
}

function folderPath(folder, folderMap) {
  const names = [folder.folder_name];
  let parentId = folder.parent_folder;
  while (parentId && folderMap.has(parentId)) {
    const parent = folderMap.get(parentId);
    names.unshift(parent.folder_name);
    parentId = parent.parent_folder;
  }
  return names.join(" / ");
}

function notify(message) {
  el.toast.textContent = message;
  el.toast.classList.add("is-visible");
  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    el.toast.classList.remove("is-visible");
  }, 3200);
}
