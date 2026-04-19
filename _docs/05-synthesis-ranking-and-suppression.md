# Synthesis, Ranking, and Suppression

## Purpose

Collection only gathers evidence.
This stage decides what actually deserves attention and how deep the system should go.

## Core operations

1. normalize source items
2. link by people, time, place, topic, and unresolved status
3. resolve source authority and citation chain
4. form bundles
5. create candidates
6. score candidates
7. decide output depth
8. apply quotas
9. suppress duplicates/noise/recent repeats

## Bundle types

### People bundle
Combines:
- upcoming meeting
- prior conversations
- email threads
- notes
- saved posts or links relevant to that person/org

### Open-loop bundle
Combines:
- unread or unresolved email
- unfinished conversation threads
- follow-up notes
- prior reminders that were not completed

### Resurfacing bundle
Combines:
- neglected bookmarks
- old likes
- stale notes
- prior conversations or documents that newly overlap with current context

### Place/time bundle
Combines:
- current or upcoming place
- travel feasibility
- gap windows
- nearby saved places
- local suggestions when the trigger justifies them

### Source-rigor bundle
Combines:
- primary source
- trusted secondary commentary
- relevant supporting docs / changelogs / repos
- unresolved claims that still need confirmation

## Ranking signals

Global ranking should generally prefer:
1. future relevance
2. people overlap with upcoming events
3. open-loop urgency
4. explicit user-intent signal
5. source authority and primary confirmation
6. recency / novelty
7. passive signal strength

## Depth escalation

Do not force every topic into one summary shape.
Escalate depth when at least one is true:
- the topic is critical to a near-future decision
- the source is authoritative and materially changes understanding
- the user historically cares deeply about the domain
- multiple strong sources disagree and need synthesis
- the trigger explicitly requests deeper explanation

Typical mapping:
- simple awareness -> `nudge`
- scheduled relevance -> `digest`
- urgent operational change -> `warning`
- action-adjacent next step -> `action_prep`
- high-value domain update or deep investigation -> `deep_brief`
- source trust / claim verification summary -> `source_audit`

## X-specific ranking rules

Within the X family:
- bookmark > like > home timeline

X-origin items should be promoted only if at least one is true:
- overlaps with today/tomorrow schedule
- overlaps with a person/org in upcoming meetings
- overlaps with recent conversation topics
- overlaps with saved-interest clusters
- is unusually high-signal and within quota

## Candidate quotas

Quotas prevent the product from becoming a feed dump.

Suggested v1 defaults:
- morning total candidates rendered: 6-10
- evening total candidates rendered: 6-10
- feed-specific visible items: 0-3 unless the trigger is feed-focused
- resurfacing items: 1-3
- people bundles: up to 2
- deep briefs: usually 0-1
- warnings: usually 1

## Source authority policy in ranking

Useful authority tiers:
- `primary`
- `trusted_secondary`
- `discovery_only`

High-confidence claims should prefer:
- directly collected primary evidence
- or trusted secondary sources that have been resolved to primary evidence

Discovery-only items can still be useful, but should not dominate outputs or appear as fully trusted conclusions.

## Resurfacing policy

### Bookmarks
- resurfacing can begin relatively early because the save is explicit
- typical age threshold: 3+ days unless strongly relevant sooner

### Likes
- weaker signal, so require more context overlap or longer age
- typical age threshold: 7-90 days depending on quota and overlap

### Notes / conversations
- resurface when linked to a near-future event/person/topic
- otherwise prefer digest carry-over rather than aggressive random recall

## Suppression model

Suppression should not be a single global set.
Use dimensions such as:
- candidate ID
- underlying item IDs
- trigger family
- output mode
- still-open status
- suppression reason
- cooldown expiry
- source authority supersession

Example reasons:
- already delivered in same trigger family
- already actioned
- recently dismissed
- too weak after ranking cutoff
- duplicate of stronger candidate bundle
- superseded by higher-authority source

## Carry-over behavior

An event alert should not permanently remove an item from later digests if it remains open.
Instead:
- suppress duplicate wording in the short term
- allow re-entry into follow-up lanes if unresolved
- lower score if recently seen but not resolved

## Suggested scoring components

```ts
score =
  futureRelevance * w1 +
  peopleOverlap * w2 +
  openLoopUrgency * w3 +
  explicitIntent * w4 +
  authorityStrength * w5 +
  primaryConfirmation * w6 +
  novelty * w7 +
  userDepthFit * w8 -
  suppressionPenalty -
  alreadyDeliveredPenalty
```

## Product-level safeguard

The synthesis layer is the main guardrail against product drift.
If this layer is weak, the product degenerates into:
- a feed reader
- a mail summarizer
- an unverified search summary
- an X recap
- or an over-notifying proactive bot
