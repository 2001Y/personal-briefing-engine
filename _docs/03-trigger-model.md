# Trigger Model

## Principle

Time-of-day triggers, feed-driven triggers, and event-driven triggers should coexist in one registry.
The system should not care whether a trigger came from cron, RSS polling, generic polling, or webhook once it becomes a `TriggerEvent`.

## Trigger categories

### 1. Scheduled digests
These are broad-scope triggers.
- `digest.morning`
- `digest.evening`

### 2. Feed / source update triggers
These represent changes detected from curated source registries.
- `feed.update`
- later: `registry.priority_update`

Characteristics:
- narrow-to-medium collection scope
- source-rigorous retrieval from known registries
- can escalate from short update to deep brief
- should prefer primary confirmation before strong claims

### 3. Operational event triggers
These are narrow, high-intent triggers.
- `calendar.leave_now`
- `calendar.gap_window`
- `mail.operational`
- `shopping.replenishment`

### 4. Context / location triggers
These use movement or place change as the trigger substrate.
- `location.area_change`
- `location.arrival`
- `location.dwell`
- later: `location.routine_break`

### 5. Self-review triggers
These improve the system itself.
- `review.trigger_quality`

## Practical trigger catalog

| Trigger | Purpose | Typical output | Default action ceiling |
|---|---|---|---|
| `digest.morning` | prep for the day | `digest` | 1 |
| `digest.evening` | closure and carry-over | `digest` | 1 |
| `feed.update` | detect meaningful new information from curated sources | `nudge`, `deep_brief`, or `source_audit` | 1 |
| `location.arrival` | detect likely arrival | `mini_digest` or `nudge` | 1 |
| `location.dwell` | detect a meaningful pause that deserves context or a food-timing nudge | `nudge` | 1 |
| `calendar.leave_now` | lateness prevention | `warning` | 1 |
| `mail.operational` | react to reservation/delivery/change | `warning` or `action_prep` | 2 |
| `shopping.replenishment` | repurchase / refill / restock | `action_prep` | 2 |
| `review.trigger_quality` | self-improvement | `source_audit` | 0 |

Current implementation note:
- `feed.update.default` currently renders a minimal `nudge`
- `feed.update.expert_depth` currently renders a minimal `deep_brief`
- `feed.update.source_audit` currently renders a minimal `source_audit`
- `calendar.leave_now.default` currently renders a minimal `warning`
- `calendar.gap_window.default` currently renders a minimal `mini_digest`
- `mail.operational.default` currently renders a minimal `warning`
- `shopping.replenishment.default` currently renders a minimal `action_prep`
- `location.arrival.default` currently renders a minimal `mini_digest`
- `location.dwell.default` currently renders a minimal `nudge`
- `review.trigger_quality.default` currently renders a minimal `source_audit`

## TriggerProfile examples

### Morning
```json
{
  "id": "digest.morning.default",
  "family": "scheduled",
  "eventType": "digest.morning",
  "collectionPreset": "broad_day_start",
  "outputMode": "digest",
  "actionCeiling": 1,
  "cooldownMinutes": 360,
  "quotas": { "feed_items": 3, "resurface_items": 3, "people_bundles": 2 }
}
```

### Feed update
```json
{
  "id": "feed.update.default",
  "family": "event",
  "eventType": "feed.update",
  "collectionPreset": "known_source_delta",
  "outputMode": "nudge",
  "actionCeiling": 1,
  "cooldownMinutes": 60
}
```

### Deep brief escalation
```json
{
  "id": "feed.update.expert_depth",
  "family": "event",
  "eventType": "feed.update",
  "collectionPreset": "known_source_deep_dive",
  "outputMode": "deep_brief",
  "actionCeiling": 1,
  "cooldownMinutes": 240
}
```

## Trigger coexistence rules

### Scheduled digests do not replace event triggers
Morning/evening provide broad coherence.
Event triggers provide timeliness.
For high-frequency polling (for example every 5 minutes), prefer one narrow trigger like `location.dwell` over many special-case schedulers so suppression, feedback, and cooldown stay inside the trigger model.

### Feed triggers do not imply news-only behavior
The same mechanism should support:
- official product updates
- research lab posts
- standards / regulatory changes
- domain-specialist media updates
- trusted expert blogs

### Trigger-specific suppression is mandatory
Global dedupe is insufficient.
Suppression should consider:
- trigger family
- candidate kind
- still-open status
- cooldown window
- delivery outcome
- whether a higher-authority source later superseded a lower-authority one

## Self-improvement loop

`review.trigger_quality` should periodically inspect:
- notification rate
- dismiss / ignore rate
- repeated false positives
- time-to-usefulness
- trigger overlap
- source authority success/failure patterns

Outputs should be suggestions like:
- raise dwell threshold
- lower leave-now buffer
- shrink weak feed quotas
- upgrade a registry source from trusted secondary to discovery only
- require stronger primary confirmation before escalation
