# Roadmap

## Build order

The implementation order should follow architecture seams, not doc history.

### Phase 0 — planning baseline
- finalize canonical docs
- define canonical objects
- define trigger registry
- define source registry / feed registry
- define SQLite state plan

### Phase 1 — minimum useful scheduled briefing
Focus on scheduled value first.

Build:
- morning/evening trigger profiles
- calendar connector
- Gmail connector
- Hermes connector
- notes connector
- feed registry ingestion
- candidate synthesis core
- digest rendering
- delivery adapter for one destination

Success criteria:
- stable morning/evening digests
- people bundle when schedule permits
- follow-up and resurfacing lanes work without X
- feed updates can appear in digest without turning it into a feed dump

### Phase 2 — source-rigorous feed + registry layer
Build:
- RSS / Atom polling
- known-source registry storage
- authority tiers
- primary-confirmation workflow
- source audit rendering

Success criteria:
- official and specialist feeds can be monitored reliably
- the system can prefer known-source retrieval over generic search where appropriate
- secondary discoveries can be resolved back to primary sources when practical

### Phase 3 — X as source family
Build:
- X bookmarks
- X likes
- X-specific ranking quota rules
- delivered-ID / suppression state for supported X signals

Success criteria:
- X adds value without dominating output
- dedupe across bookmark/like works
- delivered IDs and suppression behave correctly (minimal same-trigger digest suppression now implemented)
- the project keeps X support aligned with official `xurl`/X API surfaces and does not claim `For You` support in v1

### Phase 4 — cross-agent memory imports
Build:
- ChatGPT export/manual import
- Grok manual/share-link import
- conversation provenance tracking

Success criteria:
- imported histories contribute to people/follow-up/resurfacing
- system remains honest about freshness and acquisition mode

### Phase 5 — expert-depth synthesis
Build:
- deep-brief output contract
- source-audit output contract
- user-understanding calibration
- per-domain source packs / registry packs

Success criteria:
- the system can stay concise by default but go deep when justified
- domain-specific source packs improve quality without changing the core architecture
- outputs stay grounded in evidence and citation chains

### Phase 6 — event-driven triggers
Build:
- leave-now trigger
- mail.operational trigger
- shopping.replenishment trigger
- location-arrival/dwell trigger using minimal heuristics
- feed.update trigger promotion rules

Success criteria:
- short-form event outputs are useful and non-spammy
- carry-over into later digests works
- approval boundary respected for action_prep (minimal persistence now implemented)

### Phase 7 — self-improvement loop
Build:
- trigger run logs
- usefulness feedback capture
- source quality feedback capture (minimal audit-derived persistence now implemented)
- review.trigger_quality

Success criteria:
- system can suggest threshold/quota tuning from actual logs
- weak sources can be demoted or suppressed over time

## Testing strategy

### Unit tests
- trigger profile selection
- candidate scoring
- suppression logic
- feed delta handling
- source authority resolution
- bundle formation

### Integration tests
- morning digest without X still succeeds
- feed update from curated registry escalates correctly
- bookmark outranks like outranks home diff
- import-based ChatGPT/Grok artifacts affect ranking with correct provenance
- source audit identifies primary vs secondary evidence correctly

### Golden-output tests
Keep fixed fixtures for:
- morning digest
- evening digest
- leave-now warning
- shopping action prep
- feed update deep brief
- source audit report

## Observability milestones
- trigger run counts
- delivery counts
- suppression counts by reason
- average candidate count before/after ranking
- source registry hit rate
- known-source retrieval vs generic search rate
- ignored vs useful trigger review later
