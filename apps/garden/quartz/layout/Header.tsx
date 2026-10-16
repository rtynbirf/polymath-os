// apps/garden/quartz/layout/Header.tsx — minimal custom Quartz header override
//
// Quartz v4 lets you override any component by placing a file at the matching
// path under `quartz/`. This file overrides `quartz/layout/Header.tsx` to
// add a minimal "Polymath OS Garden" wordmark + link back to the source repo.
//
// See https://quartz.jzhao.xyz/layout for the full layout override mechanism.
//
// NOTE: keep this override minimal. The upstream `Header` already renders
// the explorer toggle, search bar, theme toggle, and graph button — we just
// wrap it with a wordmark.

import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../components/types"
import { resolveRelative, classNames } from "../util/path"

const Header: QuartzComponent = ({
  fileData,
  cfg,
  externalResources,
}: QuartzComponentConstructor) => {
  const pageUrl = resolveRelative(fileData.slug!, fileData.slug ?? "index")
  return (
    <header class={classNames.pageTitle}>
      <a href={pageUrl} class="wordmark">
        <span class="wordmark-text">Polymath OS Garden</span>
      </a>
      <span class="wordmark-sep" aria-hidden="true">·</span>
      <a
        href="https://github.com/USER/polymath-os"
        class="wordmark-source"
        target="_blank"
        rel="noopener noreferrer"
      >
        source
      </a>
    </header>
  )
}

Header.css = `
header.pageTitle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  padding: 0.25rem 0;
}
.wordmark {
  font-weight: 600;
  color: var(--dark);
  text-decoration: none;
}
.wordmark-sep {
  opacity: 0.4;
}
.wordmark-source {
  opacity: 0.7;
  font-size: 0.85rem;
}
`

export default Header

// Type stubs to keep this file self-contained before `npx quartz bootstrap`
// populates the real `quartz/components/types.ts` and `quartz/util/path.ts`.
export type _QuartzComponent = QuartzComponent
export type _QuartzComponentConstructor = QuartzComponentConstructor
export type _QuartzComponentProps = QuartzComponentProps
