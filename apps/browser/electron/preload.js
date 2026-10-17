// apps/browser/electron/preload.js — preload script
// Runs in an isolated context with Node access. Exposes ONLY the DecreeBridge
// API to the renderer (decree-portal.html) via contextBridge. The renderer
// never sees `require` or `process` — only `window.decreeBridge.*`.
//
// Per ADR-0022: bridge calls python3 -> DecreeLog -> SQLite (hash-chained,
// append-only). This preload is the secure seam between the untrusted HTML
// and the Node/Python backend.

const { contextBridge } = require("electron");
const { DecreeBridge } = require("../decree-bridge.js");

const bridge = new DecreeBridge();

contextBridge.exposeInMainWorld("decreeBridge", {
  isAvailable: () => true,
  issueDecree: (text, category, scope) => bridge.issueDecree(text, category, scope),
  getDecrees: () => bridge.getDecrees(),
  checkCompliance: (intentText) => bridge.checkCompliance(intentText),
});
