# apps/browser/ — Sovereign Browser

**"Не гоже человеку пользоваться браузерами для корпораций."**

A sovereign browser shell: zero corporate dependencies, zero telemetry,
zero cloud sync, intent-driven, default-deny, local-first.

## What this is NOT

- NOT Chrome (Google)
- NOT Firefox (Mozilla Foundation, but corporate-funded)
- NOT Edge (Microsoft)
- NOT Safari (Apple)
- NOT a rendering engine

## What this IS

A **browser shell** — bookmarks, notes, history, settings, all in
localStorage. Zero remote scripts. Zero CDN. Zero telemetry. Zero
corporate sync.

The **rendering engine** is an open slot (`engines.txt`) — first
existing path wins. Candidates: NetSurf, Servo, Ladybird (all
independent, non-corporate). Any engine can be slotted in.

The **intent layer** (`intent-runtime.js`) — deterministic, no LLM.
Three capabilities: note.create.local, web.search.prepare,
system.status.read. Unknown commands → DENIED (not guessed).

## Files

| File | Lines | What |
|---|---|---|
| `index.html` | 36 | Browser shell (sidebar, tabs, address bar) |
| `style.css` | ~200 | Dark theme, responsive, WCAG 2.2 AA |
| `app.js` | ~300 | Tab management, bookmarks, notes, settings |
| `intent-lab.html` | ~150 | Intent lifecycle UI (Plan→Policy→Evidence→Journal) |
| `intent-runtime.js` | 59 | Deterministic intent runtime (3 capabilities) |
| `engines.txt` | 15 | Sovereign engine slot (first-existing-path wins) |

## Sovereignty principles

1. **Zero corporate dependencies** — no Google/Apple/Microsoft/Mozilla
2. **Zero telemetry** — no analytics, no sync, no "sign in to sync"
3. **Local-first** — all data in localStorage, exportable as JSON
4. **Intent-driven** — address bar accepts intents, not just URLs
5. **Default-deny** — unknown commands → DENIED, not guessed
6. **Engine-slot** — rendering engine is pluggable (engines.txt)
7. **PREPARED_NOT_SENT** — web search prepares URL, user clicks manually

## Connection to polymath-os

The `intent-runtime.js` is a JS reference implementation of the
SINGULYAR EIR kernel's Adapter contract. Via the Python↔JS bridge
(`runtime/src/bridge/subprocess_bridge.py`), the browser can call
the Python kernel for full SINGULYAR EIR processing.

## Origin

Based on singulyar-browser-prototype-0.2 (from WIN_PE material).
Ported into polymath-os as the sovereign browser layer.

Per user: "У НАС СВОЙ ПУТЬ!!! НО ТУТ ЕСТЬ РАЗУМНОЕ ЗЕРНО"
The grain: a browser that serves the human, not the corporation.
