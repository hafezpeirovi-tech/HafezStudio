"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("hermes", {
  getConfig: () => ipcRenderer.invoke("config:get"),
  getBrandTokens: () => ipcRenderer.invoke("brand:get-tokens"),
  saveConfig: (config) => ipcRenderer.invoke("config:save", config),
  getResourcePaths: () => ipcRenderer.invoke("resource:paths"),
  getIntegrations: () => ipcRenderer.invoke("system:integrations"),
  selectVideo: () => ipcRenderer.invoke("file:video"),
  selectFont: () => ipcRenderer.invoke("file:font"),
  loadFont: (fontPath) => ipcRenderer.invoke("font:load", fontPath),
  selectOutput: () => ipcRenderer.invoke("folder:output"),
  doctor: () => ipcRenderer.invoke("system:doctor"),
  startJob: (payload) => ipcRenderer.invoke("job:start", payload),
  cancelJob: () => ipcRenderer.invoke("job:cancel"),
  openPath: (target) => ipcRenderer.invoke("path:open", target),
  showPath: (target) => ipcRenderer.invoke("path:show", target),
  onJobLog: (callback) => ipcRenderer.on("job:log", (_, data) => callback(data)),
  onJobProgress: (callback) => ipcRenderer.on("job:progress", (_, data) => callback(data)),
  onJobState: (callback) => ipcRenderer.on("job:state", (_, data) => callback(data))
});
