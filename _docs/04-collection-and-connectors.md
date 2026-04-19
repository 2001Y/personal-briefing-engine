# Collection and Connectors

## Principle

The current target is **Hermes-first**, but the connector model should remain portable.
Connector design must be driven by acquisition reality and source rigor, not by branding or convenience.

## Acquisition modes

- `local_store`
- `official_api`
- `official_export`
- `rss_poll`
- `atom_poll`
- `known_source_search`
- `share_link_import`
- `manual_import`
- `browser_automation_experimental`

These modes matter because many user-facing systems do not expose equally trustworthy or equally stable read paths.

## Connector contract

```ts
export interface Connector {
  id: string
  sourceFamily: string
  capabilities(): string[]
  collect(input: { trigger: TriggerEvent; cursor?: string }): Promise<CollectedItem[]>
  importArtifact?(input: { path?: string; url?: string; text?: string }): Promise<CollectedItem[]>
  latestCursor?(): Promise<string | undefined>
}
```

## Source registry contract

Every durable source should be representable in a registry entry.

A registry entry should capture:
- domain
- source family
- authority tier
- rss/atom endpoint where applicable
- search hints
- topic scopes
- whether primary confirmation is mandatory

This registry is not just for feeds.
It is also the substrate for retrieval that is more reliable than generic open web search.

## Collection presets

A trigger should not always collect everything.
Use named collection presets such as:
- `broad_day_start`
- `broad_day_end`
- `narrow_leave_now`
- `shopping_context`
- `location_context`
- `mail_operational`
- `known_source_delta`
- `known_source_deep_dive`

Each preset defines:
- which connectors are eligible
- which source registries are eligible
- time windows
- fetch depth
- quota before synthesis
- whether generic web search is allowed and at what stage

## Primary-source-first policy

The baseline rule across all domains is:
1. use the lowest-layer authoritative source that is realistically available
2. use secondary sources for discovery, framing, or triangulation
3. when a secondary source cites a primary source, collect the primary source too when practical
4. do not let tertiary summaries stand alone for high-confidence claims

## Provenance requirement

Every collected item must retain provenance.
This is mandatory for:
- trust
- debugging
- re-normalization
- connector-specific bug fixing
- privacy review
- source audits

## Connector readiness matrix

| Source | v1 target mode | Why |
|---|---|---|
| Hermes Agent history | `local_store` | strongest control and easiest sync |
| Calendar | `official_api` or local export | essential future context |
| Gmail / email | `official_api` / webhook / polling | key operational trigger source |
| Notes / docs | local file / API | open-loop and memory context |
| ChatGPT history | `official_export`, `manual_import`, maybe `share_link_import` | consumer UI history is not a clean app API |
| Grok history | `manual_import`, `share_link_import`, maybe export later | same constraint class as ChatGPT |
| X home timeline | official API if available; otherwise constrained fallback | high-value but noisy delta source |
| X bookmarks | official API | stronger explicit intent than likes/home |
| X likes | official API | weaker but still useful memory signal |
| RSS / Atom source registries | `rss_poll` / `atom_poll` | reliable first-line monitoring for official and specialist sources |
| Known-source domain registries | `known_source_search` | more reliable retrieval substrate than generic search when curated well |
| Maps saved places | export/API later | valuable for place-aware triggers |
| Location history (e.g. Dawarich) | local/API | strong proactive trigger substrate |

## RSS / feed registries

The system should support curated feed lists for:
- official blog/newsroom feeds
- changelogs and release feeds
- research labs
- standards bodies / regulatory updates where available
- domain-specialist media
- trusted expert third-party blogs

These feeds should be grouped by domain and by authority tier.

## Known-source retrieval before generic search

When the system needs current external knowledge, the preferred order is:
1. explicit local source / artifact
2. known source registry / feed registry
3. direct primary-source resolution from known domains
4. generic web search

This does not eliminate web search.
It makes web search a fallback or expansion layer rather than the first and only retrieval method.

## Live retrieval vs imported artifacts

### Prefer live retrieval when:
- timing matters now
- the source is operational
- stateful diffing is required
- the source path is authoritative and stable

### Prefer artifact import when:
- the source does not support stable live access
- the user owns an export file
- the data is retrospective memory, not immediate operational context

## Minimal storage stance

Raw artifacts should be retained by reference where practical.
Do not over-normalize too early.
The goal is to support:
- repeatable normalization
- provenance
- citation-chain recovery
- light reprocessing
without committing to a huge warehousing scheme in v1.
