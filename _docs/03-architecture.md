# Architecture

## Core pipeline

1. **Collect** from available connectors
2. **Normalize** into canonical records
3. **Build candidates** for digest lanes
4. **Bundle related items** into context sets
5. **Score and rank** by future relevance, people overlap, open-loop urgency, and saved intent
6. **Suppress duplicates/recently surfaced items**
7. **Render** into morning/evening output
8. **Deliver** via a chosen adapter
9. **Persist state** for incremental sync and resurfacing control

## Core modules

```text
src/
  core/
    types.ts
    state.ts
    candidate_builder.ts
    bundler.ts
    ranker.ts
    resurfacing.ts
    suppressions.ts
  connectors/
    calendar/
    gmail/
    hermes/
    chatgpt/
    grok/
    notes/
    x/
  render/
    morning.ts
    evening.ts
  delivery/
    slack.ts
    telegram.ts
    local.ts
```

## Canonical types

### Source item
Minimal common representation for events, emails, notes, posts, conversations.

```ts
export type SourceItem = {
  id: string
  source: string
  kind: 'event' | 'email' | 'conversation' | 'note' | 'post' | 'photo'
  title: string
  body?: string
  excerpt?: string
  url?: string
  author?: string
  participants?: string[]
  entities?: string[]
  topics?: string[]
  createdAt?: string
  updatedAt?: string
  startAt?: string
  endAt?: string
  saved?: boolean
  unread?: boolean
  unresolved?: boolean
  metadata?: Record<string, unknown>
}
```

### Candidate

```ts
export type Candidate = {
  id: string
  lane: 'today' | 'people' | 'incoming' | 'resurface' | 'followup' | 'tonight' | 'tomorrow'
  itemIds: string[]
  headline: string
  summary: string
  reasons: string[]
  score: number
}
```

## Connector abstraction

The engine should not know whether data came from:
- a local DB
- an official API
- an export ZIP
- a share link
- manual pasted text
- experimental browser automation

It only knows capabilities.

## Capability model

Suggested capability flags:
- LIST_CONVERSATIONS
- GET_CONVERSATION
- BULK_EXPORT_IMPORT
- INCREMENTAL_SYNC
- LOCAL_READ
- SHARE_LINK_IMPORT
- MANUAL_IMPORT
- POSTS_HOME_TIMELINE
- POSTS_BOOKMARKS
- POSTS_LIKES

## Storage model

Use SQLite for v1 with tables for:
- connector cursors
- surfaced history
- dismissed history
- imported artifacts
- normalized items cache (optional, thin)

## Important architectural choice

The project should be runnable:
- inside Hermes Agent orchestration
- as a standalone CLI / daemon
- later inside other agents

That means:
- keep provider-specific auth in connectors
- keep digest logic in a runtime-neutral core package
- keep delivery adapters separate from collection logic
