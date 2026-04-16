# Connectors and Ingestion Strategy

## Principle

The project must be **agent-compatible, not Hermes-only**.
Hermes is one excellent runtime/integration surface, but the project should survive outside it.

Therefore connectors should be defined by acquisition mode rather than vendor identity.

## Acquisition modes

- `local_store`
- `official_api`
- `official_export`
- `share_link_import`
- `manual_import`
- `browser_automation_experimental`

## Connector interface

```ts
export interface Connector {
  id: string
  capabilities(): string[]
  list(cursor?: string): Promise<unknown[]>
  get(id: string): Promise<unknown>
  syncIncremental?(cursor?: string): Promise<unknown[]>
  importArtifact?(input: { path?: string; url?: string; text?: string }): Promise<unknown[]>
  normalize(raw: unknown): SourceItem[]
}
```

## Hermes Agent connector

### Preferred path
- local SQLite / Hermes CLI / export APIs

### Why first
- strongest control
- stable local access
- full session/tool-call context possible

### v1 approach
- read Hermes session store locally
- normalize session title, timestamps, messages, unresolved topics
- include sessions as conversation items and open-loop candidates

## ChatGPT connector

### Realistic paths
1. official export import
2. manual transcript import / shared artifact import
3. browser automation plugin (experimental, opt-in only)

### Important note
There is no clean official API for reading the user’s existing ChatGPT UI conversation history as a normal app integration.
For v1, plan around imports, not always-on live sync.

### v1 approach
- ZIP export importer
- manual transcript / pasted conversation importer
- mark acquisition mode in provenance

## Grok connector

### Realistic paths
1. manual transcript import / share-link import
2. privacy export when available/verified for the specific account/tenant
3. browser automation plugin (experimental, opt-in only)

### Important note
xAI API persistence is not the same thing as reading consumer grok.com chat history.
Treat API-created responses and consumer chat history as distinct acquisition modes.

### v1 approach
- manual import and share-link import first
- optional future privacy-export connector

## X connector family

Three sub-connectors should exist under one X auth context:

- `x_home_timeline`
- `x_bookmarks`
- `x_likes`

These should normalize into a common `post` item shape, but retain source provenance.

## Provenance requirements

Every normalized item should carry provenance such as:

```json
{
  "provider": "chatgpt",
  "acquisition_mode": "official_export",
  "artifact_id": "...",
  "raw_record_id": "..."
}
```

This is critical because some connectors are not fully live / official API driven.

## Recommendation for v1 implementation order

1. Hermes local connector
2. Calendar connector
3. Gmail connector
4. X bookmarks connector
5. X likes connector
6. X home timeline diff connector
7. ChatGPT export importer
8. Grok manual/share-link importer
