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

SSOT rules are strict:
- every source family must have one canonical acquisition path for v1
- if the path is not acquisition-stable enough, mark it out of scope
- do not describe speculative fallback branches as if they were part of the product

| Source | v1 canonical acquisition mode | Concrete path | Status |
|---|---|---|---|
| Hermes Agent history | `local_store` | local session/archive files under the user-controlled Hermes data directory | implemented |
| Calendar | `official_api` | Google Calendar via OAuth-backed Google Workspace API tooling | implemented minimally |
| Gmail | `official_api` | Gmail via OAuth-backed Google Workspace API tooling | implemented minimally |
| Generic email (non-Gmail) | out of scope | do not mix IMAP variants into v1 until a separate canonical path is defined | out of scope |
| Notes / docs | `local_store` | local markdown/text/doc artifacts explicitly pointed at by the user or configured paths | implemented minimally |
| ChatGPT history | `official_export` | official OpenAI export zip or other raw user-owned export artifact | planned |
| Grok history | `manual_import` | raw user-owned artifacts only until an official export path exists | planned |
| X bookmarks | `official_api` | official X API via `xurl` with OAuth 2.0 user context | implemented |
| X likes | `official_api` | official X API via `xurl` with OAuth 2.0 user context | implemented |
| X reverse chronological home timeline | `official_api` | official X API via `xurl` hitting `/2/users/{id}/timelines/reverse_chronological` | implemented |
| X For You timeline | out of scope | recommendation-defined surface; do not treat as SSOT-grade canonical acquisition | out of scope |
| RSS / Atom source registries | `rss_poll` / `atom_poll` | curated source registry with raw feed artifact retention | implemented |
| Known-source domain registries | `known_source_search` | domain-constrained retrieval from registered trusted sources | implemented |
| Maps saved places | out of scope | do not claim support before a stable export or official API path is chosen | out of scope |
| Location history | `local_store` | local Dawarich database/API or other user-controlled location store | planned |

## Source-family decisions for v1

### Calendar
- Canonical path: `official_api`
- Concrete choice: Google Calendar only in v1
- Why: this is an operational source where current state matters and Google exposes a stable official API
- Consequence: if the user wants Apple Calendar or another provider, that is a separate connector family and is out of scope until specified

### Gmail
- Canonical path: `official_api`
- Concrete choice: Gmail only in v1
- Why: operational mail needs live read access and reliable incremental queries; Gmail API is the cleanest source of truth here
- Consequence: generic IMAP is not silently treated as equivalent in v1

### X
- Canonical path for supported signals: `official_api`
- Concrete choice in v1:
  - support `bookmarks`
  - support `likes`
  - support `reverse chronological home timeline`
  - do **not** support `For You`
- Why:
  - bookmarks and likes are explicit user signals and map naturally to authenticated API surfaces
  - reverse chronological home timeline now has an official acquisition path via `/2/users/{id}/timelines/reverse_chronological`
  - `For You` remains recommendation-defined and is not SSOT-grade enough for this project
- Operational requirement:
  - `xurl`
  - OAuth 2.0 user-context app registration in the X developer portal
  - app moved to an X package/environment that allows `/2/*` reads

### ChatGPT
- Canonical path: `official_export`
- Concrete choice: user-triggered export artifact import
- Why: consumer UI live history is not an official operational API surface

### Grok
- Canonical path: `manual_import`
- Concrete choice: user-owned raw artifacts only in v1
- Why: until an official export path exists, internal web endpoints should not be treated as canonical SSOT-grade collection

### Location
- Canonical path: `local_store`
- Concrete choice: Dawarich or another local user-controlled location database
- Why: it preserves raw movement history under user control and avoids over-coupling the runtime to opaque vendor APIs
- Current minimal runtime: fixture-backed `location.arrival` and `location.dwell` flows are implemented; the intended live scheduler shape is a narrow 5-minute poll against the local store rather than a feed-style broad digest run

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

## Feed body enrichment note

For RSS/Atom items, the feed `description`/`excerpt` is often not enough for grounded synthesis. The current runtime now supports bounded article-page body enrichment when a feed item has a primary URL and the page can be fetched successfully. This is still subordinate to source rigor: the article page is treated as the same primary source, failures do not break collection, and the original feed excerpt remains preserved.

## Minimal storage stance

Raw artifacts should be retained by reference where practical.
Do not over-normalize too early.
The goal is to support:
- repeatable normalization
- provenance
- citation-chain recovery
- light reprocessing
without committing to a huge warehousing scheme in v1.
