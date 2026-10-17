# Polymath-OS Decree Portal — Electron Wrapper

This is a minimal Electron desktop app that wraps the existing
`apps/browser/decree-portal.html` so the Decree Bridge (`decree-bridge.js`)
actually works in a real desktop context — not just a Node CLI, and not just a
pure browser where `require` is unavailable.

## Why it exists

`decree-portal.html` calls `getBridge()` which historically tried
`require('./decree-bridge.js')`. That call works in Node CLI and in the
Electron **main** process, but the renderer (the HTML page loaded in a
`BrowserWindow`) runs in a Chromium context where `require` is disabled by
default for security. So in a real desktop window, the bridge was silently
unavailable and the portal fell back to `localStorage` — meaning typed
decrees never reached the SQLite `DecreeLog`.

The Electron preload + `contextBridge` pattern is the secure, sanctioned way
to bridge Node-only modules into a renderer. The preload runs in a privileged
context (Node available), and `contextBridge.exposeInMainWorld` exposes only
an explicitly-allow-listed API (`decreeBridge.*`) to the untrusted HTML.
The renderer never sees `require`, `process`, or `child_process`.

## Prerequisites

- **Node.js >= 20** (Electron 31 requires Node 18+, but Polymath-OS targets 20).
- **`python3`** on `PATH` — the bridge spawns `python3 -c` to import
  `runtime/src/decree_log.py` and operate on `~/.polymath-os/decrees.db`.
- **Electron** — installed by `npm install` (declared as a `devDependency`
  in `package.json` at `^31.0.0`). The first `npm install` will download
  the Electron binary (~200 MB) — this is expected and one-time.

## How to run

```bash
cd apps/browser/electron
npm install        # one-time, downloads Electron ~200MB
npm start          # opens the Decree Portal in a desktop window
# or, with DevTools detached:
npm run dev
```

From the repo root, you can also use the launcher in `electron` mode:

```bash
apps/browser/launch.sh electron
```

If `electron` is not on `PATH`, the launcher prints a notice and falls back
to the default browser behaviour.

## What to expect

- A 1200×800 dark window titled
  `СИНГУЛЯР · ДЕКРЕТ ПОРТАЛ — ВОЛЯ = НАКАЗ`.
- The portal renders with the existing styling (`apps/browser/style.css`).
- Each issued decree is written to real SQLite at
  `~/.polymath-os/decrees.db` via the Python `DecreeLog` — hash-chained,
  append-only, impossible to edit or delete.
- Each decree entry shows a `SQLite` badge (not `local`) — confirming the
  bridge path is live.
- Decrees issued here are immediately visible to the SINGULYAR EIR runtime's
  decree gate (`runtime/src/singulyar_runtime.py::_advance()`).

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Electron Main Process  (apps/browser/electron/main.js)          │
│   • BrowserWindow 1200×800, dark #101713                        │
│   • loadFile ../decree-portal.html                              │
│   • webPreferences.preload = preload.js                         │
│        contextIsolation = true,  nodeIntegration = false        │
└──────────────────────────────────────────────────────────────────┘
                            │  (isolated preload, Node available)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ Preload  (apps/browser/electron/preload.js)                      │
│   const { DecreeBridge } = require('../decree-bridge.js')        │
│   contextBridge.exposeInMainWorld('decreeBridge', {              │
│     isAvailable, issueDecree, getDecrees, checkCompliance       │
│   })                                                             │
└──────────────────────────────────────────────────────────────────┘
                            │  (window.decreeBridge — only this API)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ Renderer  (apps/browser/decree-portal.html)                      │
│   getBridge():                                                  │
│     1) typeof require === 'function'  → main-process path       │
│     2) window.decreeBridge            → preload path (this app) │
│     3) null                           → localStorage fallback   │
│   fetchAllDecrees() → bridge.getDecrees() (Promise)              │
│   issueBtn click    → bridge.issueDecree(text, category, scope) │
└──────────────────────────────────────────────────────────────────┘
                            │  (Node child_process.spawn)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ Node Bridge  (apps/browser/decree-bridge.js)                      │
│   DecreeBridge.issueDecree/getDecrees/checkCompliance           │
│   each method: python3 -c "<script>" with PYTHONPATH=runtime/src│
└──────────────────────────────────────────────────────────────────┘
                            │  (subprocess)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ Python DecreeLog  (runtime/src/decree_log.py)                    │
│   DecreeLog(db).issue(text, category, scope)                    │
│   DecreeLog(db).get_all()                                       │
│   DecreeLog(db).check_compliance(intent_text)                   │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                   ~/.polymath-os/decrees.db
                   (SQLite, hash-chained, append-only)
```

## Security notes

- **`contextIsolation: true`** — the renderer's `window` object is
  isolated from the preload's Node-context globals. The renderer cannot
  reach `require`, `process`, or `Buffer` even by accident.
- **`nodeIntegration: false`** — no Node symbols leak into the renderer.
- **Only the `decreeBridge` API is exposed.** The portal HTML cannot
  spawn arbitrary subprocesses, read arbitrary files, or call other Node
  modules — only `issueDecree`, `getDecrees`, `checkCompliance`, and
  `isAvailable`. The bridge itself only ever calls `python3 -c` with
  hard-coded scripts.
- The preload script is a tiny audit surface (~15 lines). It is the only
  seam between untrusted HTML and the Node backend.
- No remote module, no `webSecurity: false`, no `allowRunningInsecureContent`.
  This is the Electron-recommended secure baseline.

## Verification

```bash
# 1. Syntax-check preload (will throw ReferenceError for contextBridge
#    outside Electron — that's expected, we just want no SyntaxError):
node -e "require('./apps/browser/electron/preload.js')"

# 2. Biome lint:
pnpm biome check apps/browser/electron/

# 3. Full repo verification (must remain 22/22):
make verify
```

## Files

- `package.json` — Electron app manifest, `electron ^31.0.0` devDep.
- `main.js` — Electron main process: BrowserWindow + security flags.
- `preload.js` — `contextBridge.exposeInMainWorld('decreeBridge', …)`.
- `README.md` — this file.

## License

MIT — see repo root `LICENSE`.
