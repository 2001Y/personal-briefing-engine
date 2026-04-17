# Collection and Connectors

## Principle

The current target is **Hermes-first**, but the connector model should remain portable.
Connector design must be driven by acquisition reality, not by branding.

## Acquisition modes

- `local_store`
- `official_api`
- `official_export`
- `share_link_import`
- `manual_import`
- `browser_automation_experimental`

These modes are important because many user-facing AI products do not expose clean read APIs for personal history.

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

## Collection presets

A trigger should not always collect everything.
Use named collection presets such as:
- `broad_day_start`
- `broad_day_end`
- `narrow_leave_now`
- `shopping_context`
- `location_context`
- `mail_operational`

Each preset defines:
- which connectors are eligible
- time windows
- fetch depth
- quota before synthesis

## Provenance requirement

Every collected item must retain provenance.
This is mandatory for:
- trust
- debugging
- re-normalization
- connector-specific bug fixing
- privacy review

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
| Maps saved places | export/API later | valuable for place-aware triggers |
| Location history (e.g. Dawarich) | local/API | strong proactive trigger substrate |

## Hermes Agent history

Preferred path:
- local SQLite / local session store / CLI / export path

Why it matters:
- strongest access
- easiest provenance
- good unresolved-topic extraction

Normalization targets:
- title
- timestamps
- participants if derivable
- topic/entity hints
- unresolved/open-loop signal

## ChatGPT history

Reality constraint:
there is no clean, standard, always-on consumer history read API suitable for a normal integration path.

Therefore v1 should be honest:
- ZIP export import first
- manual transcript import second
- share-link import when practical
- browser automation only as experimental opt-in

## Grok history

Treat Grok similarly.
Do not confuse API persistence for API-created runs with clean access to consumer chat history.

v1 should prefer:
- manual transcript import
- share-link import
- optional verified export path later

## X family

Model X as three sub-connectors under one auth surface:
- `x_home_timeline`
- `x_bookmarks`
- `x_likes`

All normalize into a common post shape but preserve source provenance and intent strength.

## Live retrieval vs imported artifacts

### Prefer live retrieval when:
- timing matters now
- stateful diffing is required
- the source is operational

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
- light reprocessing
without committing to a huge warehousing scheme in v1.
