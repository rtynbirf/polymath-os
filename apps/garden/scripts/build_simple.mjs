#!/usr/bin/env node
// build_simple.mjs — Simple garden build (no Quartz dependency). Canonical logic.
// Port of build_simple.sh (bash) to Node so `pnpm -r run build` works everywhere
// (Windows has no bash; CI/runner always has node). Zero npm deps, zero CDN.
// Per LIBERATION_ROADMAP: eliminate corporate CDN + external deps.
// Quartz v4 requires @jackyzha0/quartz git repo (unreachable from GHA) —
// the pre-bootstrap quartz path stays available as `pnpm build:quartz`.
//
// Publishing contract (ADR-0009, default-deny): only notes with
// `publish: true` in frontmatter are rendered; canary marker must never
// appear in the output (negative test, exit 2 blocks deploy).

import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(SCRIPT_DIR, "..", "..", "..");

// Same argv contract as build_simple.sh: vault_dir out_dir [canary_marker] [canary_path]
const VAULT_DIR = resolve(REPO_ROOT, process.argv[2] ?? "vault/60-permanent");
const OUT_DIR = resolve(REPO_ROOT, process.argv[3] ?? "apps/garden/content");
const CANARY_MARKER = process.argv[4] ?? "__CANARY_p1m0s_8f3a2e91_dnp_v1__";
const CANARY_PATH = resolve(REPO_ROOT, process.argv[5] ?? "vault/90-meta/canary-secret.md");

console.log(
  `[garden-simple] Building from ${relative(REPO_ROOT, VAULT_DIR)} → ${relative(REPO_ROOT, OUT_DIR)}`,
);
mkdirSync(OUT_DIR, { recursive: true });

const PAGE_HEAD = (title) =>
  `<!doctype html><html lang='ru'><head><meta charset='utf-8'>` +
  `<meta name='viewport' content='width=device-width,initial-scale=1'>` +
  `<title>${title} — Polymath OS Garden</title>` +
  `<style>body{max-width:720px;margin:0 auto;padding:2rem;font:16px/1.6 sans-serif;color:#333}` +
  `pre{white-space:pre-wrap;word-wrap:break-word}</style></head><body>` +
  `<h1>Polymath OS Garden</h1>`;

// Filter: only publish: true notes (ADR-0009 default-deny). Same rule as the
// bash original: the flag is looked for in the first 20 lines of frontmatter.
const stripFrontmatter = (text) => {
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== "---") return lines; // no frontmatter — keep as is
  const end = lines.indexOf("---", 1);
  return end === -1 ? lines : lines.slice(end + 1);
};

let count = 0;
for (const name of readdirSync(VAULT_DIR).sort()) {
  const f = join(VAULT_DIR, name);
  if (!statSync(f).isFile() || !name.endsWith(".md")) continue;
  const head = readFileSync(f, "utf8").split(/\r?\n/).slice(0, 20).join("\n");
  if (!/^publish:.*true/m.test(head)) continue;
  const stem = basename(name, ".md");
  const body = stripFrontmatter(readFileSync(f, "utf8")).join("\n");
  const html = `${PAGE_HEAD(stem)}\n${body}\n<hr><a href='index.html'>← Garden</a></body></html>`;
  writeFileSync(join(OUT_DIR, `${stem}.html`), html, "utf8");
  count += 1;
  console.log(`[garden-simple] ✓ ${stem}.html`);
}

// Canary check (ADR-0009 negative test)
const leaked = [];
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (readFileSync(p, "utf8").includes(CANARY_MARKER)) leaked.push(p);
  }
};
if (existsSync(OUT_DIR)) walk(OUT_DIR);
if (leaked.length > 0) {
  console.error(`[garden-simple] ⛔ CANARY LEAKED — deploy blocked! (${leaked.join(", ")})`);
  process.exit(2);
}
console.log("[garden-simple] ✓ canary not in output");

// Create index.html
let index =
  `<!doctype html><html lang='ru'><head><meta charset='utf-8'>` +
  `<meta name='viewport' content='width=device-width,initial-scale=1'>` +
  `<title>Polymath OS Garden</title>` +
  `<style>body{max-width:720px;margin:0 auto;padding:2rem;font:16px/1.6 sans-serif}</style>` +
  `</head><body><h1>🌱 Polymath OS Garden</h1>` +
  `<p>Permanent notes published via default-deny filter (ADR-0009).</p>` +
  `<p><a href='https://github.com/rtynbirf/polymath-os'>→ Source repo</a></p>` +
  `<hr><h2>Notes</h2>`;
for (const name of readdirSync(OUT_DIR).sort()) {
  if (!name.endsWith(".html") || name === "index.html") continue;
  const stem = basename(name, ".html");
  index += `<p><a href='${stem}.html'>${stem}</a></p>`;
}
index += "</body></html>";
writeFileSync(join(OUT_DIR, "index.html"), index, "utf8");
console.log("[garden-simple] ✓ index.html created");
console.log(`[garden-simple] Done: ${count} note(s) published`);
void sep;
void dirname; // keep imports honest for linters
