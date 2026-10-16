// apps/garden/quartz.config.ts — Quartz v4 configuration for Polymath OS digital garden
// Layer 3 → public export. See ADR-0009 (default-deny vault publish).
//
// How publishing works in this repo (ADR-0009):
//
//   1. Author writes a permanent note in `vault/60-permanent/` with
//      `publish: true` in YAML frontmatter. The default template
//      (`vault/90-meta/templates/permanent.md`) sets `publish: false`
//      — every note is private until explicitly flipped.
//   2. On push to main, `.github/workflows/publish-garden.yml` filters
//      `vault/60-permanent/` and copies ONLY notes with `publish: true`
//      into `apps/garden/content/`. Notes without that flag never reach
//      this directory.
//   3. Only then does Quartz build. It can never see a note without
//      `publish: true` — the filter is upstream, not in Quartz.
//   4. `ignorePatterns` below is belt-and-suspenders for drafts/canaries
//      that might be checked in here directly (they shouldn't be).
//
// Quartz v4 itself does not have a `defaultPublish` option — the
// default-deny guarantee is structural (upstream filter), not configurable.

import { QuartzConfig } from "./quartz/util/theme"
import {
  Frontmatter,
  TableOfContents,
  CrawlLinks,
  SyntaxHighlight,
  ObsidianFlavoredMarkdown,
  Description,
  Wikilinks,
  RemoveRedundantFlags,
} from "./quartz/plugins/transformers"
import {
  ContentIndex,
  FolderPage,
  TagPage,
  ContentPage,
  IndexPage,
  AliasRedirects,
  ComponentResources,
  StaticSiteMap,
  RSSFeed,
} from "./quartz/plugins/emitters"
import * as Component from "./quartz/components"

const config: QuartzConfig = {
  configuration: {
    pageTitle: "Polymath OS Garden",
    pageTitleSuffix: "",
    enableSPA: true,
    enablePopovers: true,
    analytics: {
      // Provider "none" by default — keeps the garden telemetry-free.
      // Switch to "plausible" (self-host) if you want traffic insights.
      provider: "none",
    },
    // Public base URL. Override via env GARDEN_BASE_URL in CI.
    baseUrl: process.env.GARDEN_BASE_URL ?? "https://polymath-os-garden.example.com",
    ignorePatterns: ["private", "drafts", "canary-*"],
    defaultDateType: "created",
  },
  // ⛔ Default-deny is enforced by CI pre-filter (see header comment).
  // Nothing in this theme block relaxes that — it's cosmetic only.
  theme: {
    typography: {
      header: "Source Sans 3",
      body: "Source Sans 3",
      code: "IBM Plex Mono",
    },
    colors: {
      light: { mode: "light" },
      dark: { mode: "dark" },
    },
  },
  plugins: {
    transformers: [
      Frontmatter(),
      ObsidianFlavoredMarkdown(),
      TableOfContents({ min: 1, max: 3 }),
      Wikilinks(),
      CrawlLinks(),
      Description(),
      SyntaxHighlight({ theme: { light: "github-light", dark: "github-dark" } }),
      RemoveRedundantFlags(),
    ],
    emitters: [
      ContentIndex({ enableCrawlLinks: true }),
      FolderPage(),
      TagPage(),
      ContentPage(),
      IndexPage(),
      AliasRedirects(),
      ComponentResources({ inlineInCSV: false, componentPaths: Component._componentPaths }),
      StaticSiteMap(),
      RSSFeed(),
    ],
  },
}

export default config
