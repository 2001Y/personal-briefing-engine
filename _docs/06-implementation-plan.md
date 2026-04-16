# Implementation Plan

> For implementation, use strict test-first development and keep the engine runtime-neutral.

## Repository structure

```text
_docs/
README.md
src/
  core/
  connectors/
  render/
  delivery/
tests/
```

## Phase 1 — Core schema and state

Files:
- `src/core/types.ts`
- `src/core/state.ts`
- `tests/core/types.test.ts`
- `tests/core/state.test.ts`

Tasks:
1. Define canonical `SourceItem`, `Candidate`, `DigestState`
2. Add SQLite-backed state persistence for connector cursors and delivered/surfaced IDs
3. Add tests for serialization, idempotent updates, duplicate suppression primitives

## Phase 2 — Calendar, Gmail, Hermes connectors

Files:
- `src/connectors/calendar/index.ts`
- `src/connectors/gmail/index.ts`
- `src/connectors/hermes/index.ts`
- tests for each connector

Tasks:
1. Normalize calendar events into `event` items
2. Normalize Gmail threads/messages into `email` items with unread/unresolved flags
3. Normalize Hermes sessions into `conversation` items with unresolved/open-loop hints

## Phase 3 — Candidate building and ranking

Files:
- `src/core/candidate_builder.ts`
- `src/core/bundler.ts`
- `src/core/ranker.ts`
- `src/core/suppressions.ts`

Tasks:
1. Build `today`, `people`, `incoming`, `followup`, `resurface` lanes
2. Bundle related event/email/conversation items by person/topic overlap
3. Rank with future relevance, people overlap, unresolved urgency, save/like/home weighting
4. Suppress recently delivered items

## Phase 4 — X bookmarks, likes, home timeline diff

Files:
- `src/connectors/x/bookmarks.ts`
- `src/connectors/x/likes.ts`
- `src/connectors/x/home_timeline.ts`
- `tests/connectors/x/*.test.ts`

Tasks:
1. Implement bookmarks incremental sync
2. Implement likes incremental sync
3. Implement home timeline diff using `seen_ids + delivered_ids + last_snapshot_ids`
4. Merge duplicate posts across X sources

## Phase 5 — ChatGPT and Grok connectors

Files:
- `src/connectors/chatgpt/export_import.ts`
- `src/connectors/grok/manual_import.ts`
- `src/connectors/grok/share_link.ts`
- tests for import normalization

Tasks:
1. Import ChatGPT exports into canonical conversation items
2. Import Grok manual/share-link transcripts into canonical conversation items
3. Preserve provenance and raw artifact references

## Phase 6 — Rendering and delivery

Files:
- `src/render/morning.ts`
- `src/render/evening.ts`
- `src/delivery/local.ts`
- `src/delivery/slack.ts`

Tasks:
1. Deterministic section selection and limits
2. LLM-assisted compression as optional render stage
3. Deliver local file first; add Slack next

## Test plan

### Core tests
- state cursor update is idempotent
- delivered IDs suppress repeat delivery
- resurfacing windows behave correctly

### Candidate tests
- today events land in `today`
- related email + conversation bundle into `people`
- bookmarks outrank likes; likes outrank home only when stronger relevance exists

### X diff tests
- home timeline reordering does not create false positives
- already delivered posts are not re-delivered
- post seen in home and bookmark is merged, not duplicated

### Import tests
- ChatGPT export normalizes to canonical conversations
- Grok manual/share-link import preserves provenance and timestamps where available
- connector capability flags drive behavior safely when live sync is unavailable

## Initial recommended repo tasks

1. Initialize package/tooling
2. Add canonical types and state DB
3. Add tests for delivered/surfaced suppression
4. Implement calendar connector
5. Implement Gmail connector
6. Implement Hermes connector
7. Implement candidate builder
8. Implement ranker and bundler
9. Implement X bookmarks/likes/home diff
10. Implement ChatGPT/Grok imports
