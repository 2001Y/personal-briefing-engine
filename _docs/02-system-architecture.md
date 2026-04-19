# System Architecture

## One-system model

Do not build separate systems for:
- morning digest
- evening digest
- feed monitoring
- proactive trigger messages
- expert-depth investigation

Build **one trigger-driven system** with different trigger profiles, source registries, and output modes.

## Topology

A single runner / daemon / CLI is enough for v1.
It can be activated by:
- cron
- feed polling
- lightweight polling
- webhooks when available
- manual invocation for testing

## Canonical A-F pipeline

### A. Trigger events
The system begins with a `TriggerEvent` produced by a `TriggerProfile`.
Examples:
- `digest.morning`
- `digest.evening`
- `feed.update`
- `location.arrival`
- `calendar.leave_now`
- `mail.operational`
- `shopping.replenishment`
- `review.trigger_quality`

### B. Collection
The trigger chooses a narrow `AcquisitionPlan`.
The system collects only what is needed for that trigger:
- live data where possible
- feed/registry data when that is the most reliable path
- imported artifacts when live access is unavailable
- recent state for suppression and carry-over
- generic web search only after known-source retrieval when appropriate

### C. Synthesis / ranking / suppression
Collected evidence is turned into:
- normalized items
- bundles
- candidates
- suppression decisions
- source audits

### D. Output generation
The system chooses one output contract:
- `digest`
- `mini_digest`
- `warning`
- `nudge`
- `action_prep`
- `deep_brief`
- `source_audit`

### E. Delivery / action execution
After output generation, the system:
- delivers the result
- or prepares a user-approved action
- or drafts but does not send

### F. State / memory / audit
Persist:
- cursors
- source registry state
- artifact provenance
- citation chains
- delivery history
- suppression decisions
- approval history
- trigger feedback
- run logs

## Canonical objects

### TriggerEvent
```ts
export type TriggerEvent = {
  id: string
  type: string
  profileId: string
  occurredAt: string
  scope: {
    timeWindow?: { start: string; end: string }
    placeWindow?: { lat: number; lon: number; radiusM?: number }
    entities?: string[]
    domains?: string[]
    sourceRegistryIds?: string[]
  }
  evidenceRefs?: string[]
  metadata?: Record<string, unknown>
}
```

### TriggerProfile
```ts
export type TriggerProfile = {
  id: string
  family: 'scheduled' | 'event' | 'review'
  eventType: string
  collectionPreset: string
  outputMode: 'digest' | 'mini_digest' | 'warning' | 'nudge' | 'action_prep' | 'deep_brief' | 'source_audit'
  actionCeiling: 0 | 1 | 2 | 3
  cooldownMinutes?: number
  rankingWeights?: Record<string, number>
  quotas?: Record<string, number>
}
```

### SourceRegistryEntry
```ts
export type SourceRegistryEntry = {
  id: string
  sourceFamily: string
  domain: string
  title: string
  acquisitionMode: 'official_api' | 'official_export' | 'rss_poll' | 'atom_poll' | 'known_source_search' | 'manual_import' | 'browser_automation_experimental'
  authorityTier: 'primary' | 'trusted_secondary' | 'discovery_only'
  rssUrl?: string
  searchHints?: string[]
  topicalScopes?: string[]
  language?: string
  requiresPrimaryConfirmation?: boolean
}
```

### CollectedItem
```ts
export type CollectedItem = {
  id: string
  source: string
  sourceKind: 'event' | 'email' | 'conversation' | 'note' | 'post' | 'place' | 'artifact' | 'feed_item' | 'document'
  title?: string
  excerpt?: string
  body?: string
  url?: string
  people?: string[]
  topics?: string[]
  placeRefs?: string[]
  timestamps?: {
    createdAt?: string
    updatedAt?: string
    startAt?: string
    endAt?: string
  }
  intentSignals?: {
    saved?: boolean
    liked?: boolean
    unread?: boolean
    unresolved?: boolean
  }
  provenance: {
    provider: string
    acquisitionMode: 'local_store' | 'official_api' | 'official_export' | 'share_link_import' | 'manual_import' | 'browser_automation_experimental' | 'rss_poll' | 'atom_poll' | 'known_source_search'
    authorityTier?: 'primary' | 'trusted_secondary' | 'discovery_only'
    primarySourceUrl?: string
    artifactId?: string
    rawRecordId?: string
  }
  citationChain?: Array<{ label: string; url: string; relation: 'primary' | 'secondary' | 'discussion' | 'derived' }>
  metadata?: Record<string, unknown>
}
```

### Candidate
```ts
export type Candidate = {
  id: string
  kind: 'today' | 'people' | 'incoming' | 'resurface' | 'followup' | 'tomorrow' | 'tonight' | 'warning' | 'action_prep' | 'deep_brief' | 'source_audit'
  itemIds: string[]
  triggerRelevance: number
  actionability: 'none' | 'info' | 'prep' | 'approval_needed'
  score: number
  reasons: string[]
  suppressionScope?: string[]
}
```

## Degradation rules

The system must still work when some connectors are unavailable.
Examples:
- no ChatGPT import available -> still produce briefings from calendar/email/X/Hermes/feed registries
- no generic web search -> still operate through known-source registries and feeds
- no maps/place data -> still produce people/open-loop lanes

## Why not microservices

The repo is about correctness of retrieval, verification, selection, ranking, and action gating.
Microservice decomposition would increase ceremony before proving value.

v1 should prefer:
- one codebase
- one local DB
- one trigger registry
- one shared ranking/suppression core
- one source registry layer
- thin source adapters
- thin delivery adapters
