# State, Memory, and Audit

## Why this layer matters

Without explicit state, the system will:
- redeliver the same things
- miss incremental changes
- lose track of source authority
- be impossible to debug
- be unable to improve trigger quality

## Storage recommendation

Use a single local SQLite database for v1.
Optionally keep raw imported artifacts on disk with references in SQLite.

Current runtime status:
- minimal schema exists in `src/hermes_pulse/db.py`
- `codex-pulse --state-db /path/to/db.sqlite3 ...` now records trigger runs, local deliveries, delivered-item suppression history, review/audit-derived feedback logs, approval/action logs for current `action_prep` flows, X-signal connector cursors, and source-registry poll state snapshots (`last_poll_at`, `last_seen_item_ids`, `last_promoted_item_ids`, `authority_tier`)
- digest delivery now also filters active same-trigger suppression entries before archive/summarization, while cursor/state observation still uses raw collected items
- approval/action logs now support minimal `approve-action` / `reject-action` state transitions, while final side-effect execution updates remain future work
- richer approval history (for example explicit execution receipts beyond the current minimal transitions), trust-review notes, and source error metadata updates remain future work

## Required state families

### Connector cursors
Per connector / source stream:
- last poll time
- last cursor / history ID
- last successful sync
- last error metadata

### Source registry state
For feed and known-source registries:
- registry entry ID
- last poll time
- etag / last-modified where available
- last seen item IDs
- last promoted item IDs
- authority tier snapshot
- quality / trust review notes

### Imported artifact registry
For exports, share links, and manual imports:
- artifact ID
- source/provider
- acquisition mode
- import time
- raw path or reference
- parse status

### Delivery history
Track:
- output mode
- candidate IDs
- item IDs
- destination
- delivered at
- success/failure

### Suppression history
Track:
- suppression subject
- trigger family
- reason
- cooldown expiry
- dismissal status
- superseded-by-higher-authority flag

### Approval / action log
Track:
- prepared action
- approval boundary reached
- user approved/rejected
- final execution result

### Trigger run log
Track:
- trigger event
- selected collection preset
- connectors touched
- source registries touched
- candidate counts
- final output mode
- runtime metrics

### Feedback log
Track:
- explicit dismissals
- accepted suggestions
- ignored alerts if measurable
- future trigger tuning suggestions
- source quality feedback where relevant

## Citation-chain state

For items whose trust depends on source resolution, keep:
- primary source URL
- secondary source URL if used
- confirmation status
- confirmation timestamp
- unresolved-claim markers

## X-specific state

Per X source (`home`, `bookmarks`, `likes`) keep:
- `last_poll_at`
- `last_top_id`
- `seen_ids` with TTL/LRU behavior
- `last_snapshot_ids`
- `delivered_ids`

## Minimal schema sketch

```sql
create table trigger_runs (
  run_id text primary key,
  event_type text not null,
  profile_id text not null,
  occurred_at text not null,
  output_mode text,
  status text not null,
  created_at text not null
);

create table connector_cursors (
  connector_id text primary key,
  cursor text,
  last_poll_at text,
  last_success_at text,
  last_error text
);

create table source_registry_state (
  registry_id text primary key,
  last_poll_at text,
  last_seen_item_ids text,
  last_promoted_item_ids text,
  authority_tier text,
  notes text
);

create table imported_artifacts (
  artifact_id text primary key,
  provider text not null,
  acquisition_mode text not null,
  raw_ref text,
  imported_at text not null,
  parse_status text not null
);

create table deliveries (
  delivery_id text primary key,
  run_id text not null,
  destination text not null,
  delivered_at text not null,
  status text not null
);
```

## Privacy and retention

Because the system touches personal and externally sourced data, make retention explicit.
At minimum define:
- what raw artifacts are stored
- how long state is retained
- which sources are re-fetchable vs archived
- whether imported conversation artifacts can be deleted while preserving normalized derivatives
- whether source registry state keeps only IDs or raw content too

## Audit payoff

This layer is what makes `review.trigger_quality` and `source_audit` possible.
If a trigger was noisy, late, redundant, useful, or weakly sourced, the evidence should come from audit state rather than memory or guesswork.
