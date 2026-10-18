// apps/browser/electron/main.js — Electron main process
// Wraps decree-portal.html in a desktop window. Loads preload.js to expose
// the DecreeBridge via contextBridge (secure: contextIsolation=true,
// nodeIntegration=false). The renderer (portal HTML) talks to
// window.decreeBridge — never touches Node directly.
//
// Per ADR-0022: human decree = real SQLite law. This wrapper makes that
// work outside a Node CLI / pure browser context.

const { app, BrowserWindow } = require("electron");
const path = require("node:path");

const isDev = process.argv.includes("--dev");

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    backgroundColor: "#101713",
    title: "СИНГУЛЯР · ДЕКРЕТ ПОРТАЛ — ВОЛЯ = НАКАЗ",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      // Electron 31: renderer sandbox is ON by default. A sandboxed preload
      // can require() only a fixed builtin whitelist — preload.js needs
      // require("../decree-bridge.js"), so sandbox must stay OFF here.
      // contextIsolation still separates renderer from Node (ADR-0022).
      sandbox: false,
    },
  });

  win.loadFile(path.join(__dirname, "..", "decree-portal.html"));

  if (isDev) {
    win.webContents.openDevTools({ mode: "detach" });
  }

  return win;
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    // macOS: re-create a window when the dock icon is clicked and no windows are open.
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  // macOS: apps stay active until explicitly quit.
  if (process.platform !== "darwin") {
    app.quit();
  }
});
