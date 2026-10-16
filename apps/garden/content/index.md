---
title: "Polymath OS Garden"
description: "Public digital garden — atomic permanent notes exported from the Polymath OS second brain. Markdown-first, default-deny publish (ADR-0009)."
publish: true
---

# Polymath OS Garden

> Atomic permanent notes from a personal operating system.
> Source: [github.com/USER/polymath-os](https://github.com/USER/polymath-os) ·
> License: MIT · Default-deny: only notes with `publish: true` land here.

## What this is

This site is the **public export** of a private [second brain](https://en.wikipedia.org/wiki/Personal_knowledge_writing) —
a markdown vault structured by PARA + Zettelkasten + MOC, synced via git, edited in Obsidian, augmented by local LLMs.
The full vault is private; this garden contains only the permanent notes the
author has explicitly marked `publish: true`.

## Why "default-deny"

By default, every note in the vault is private. To publish, the author must
set `publish: true` in the note's YAML frontmatter — there is no
"publish-everything" path, no auto-export. A mistake in the filter cannot leak
a note that was never explicitly opted in.

See [`ADR-0009`](https://github.com/USER/polymath-os/blob/main/docs/adr/0009-default-deny-vault-publish.md)
for the full decision and its trade-offs.

## How to read

- **Backlinks**: each note ends with a list of other garden notes that link
  to it — that's the bidirectional `[[wikilink]]` graph in action.
- **Graph view**: top-right corner. Click any node to navigate.
- **Search**: `Ctrl+K` (or `Cmd+K`) for full-text + indexed content search.

## What's here

- [[0001-welcome]] — entry point: what the vault is and how to navigate it.
- [[0002-default-deny-publish]] — why every note here is explicitly opted in.

## What's NOT here

- Daily notes (`00-daily/`) — always private, journal.
- Literature notes (`50-literature/`) — private reading notes, kept raw.
- Project / Area / Resource notes — operational, not for public.
- Canary test note (`90-meta/canary-secret.md`) — should never appear here.
  If you see the string `__CANARY__do_not_publish__` on this site, the
  default-deny filter is broken — please open an issue.

## License

Content here is MIT-licensed (same as the source repo). Take it. Use it.
Fork it.
