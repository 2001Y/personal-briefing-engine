# Hermes Pulse

English README / [日本語版README](./README.ja.md)

Hermes Pulse is a Hermes-first, source-rigorous personal briefing and operating pipeline for scheduled and proactive delivery.

This repository is organized around one practical flow:

1. **Trigger** — cron schedules, feed updates, polling, webhooks, or manual runs start a run
2. **Collect** — fetch only the sources needed for that trigger, preferring primary sources and known-source retrieval before generic web search when possible
3. **Compose** — synthesize context into a briefing, warning, reply draft, expert-depth analysis, or action prep
4. **Deliver** — send the result to the user or prepare the next action through the chosen channel/runtime

Today, the primary target runtime is **Hermes Agent**. The design may later be adapted to standalone runtimes or other agent environments, but this repository optimizes for the Hermes use case first.

## Visual summary

![Hermes Pulse overview](./assets/overview-architecture.svg)

## What this repo does

This is **not** a narrow product for AI news only.
It is a general-purpose operating briefing engine that can go shallow or deep depending on domain, urgency, and user understanding.
It should answer questions like:

- What matters now?
- What matters later today?
- Which incoming changes deserve action rather than passive awareness?
- What should be resurfaced instead of forgotten?
- Which sources are authoritative enough to trust?
- When should the system proactively act before I ask?
- When should the system escalate from a concise note to an expert-depth synthesis?

## Core flow

The runtime-facing flow is intentionally simple.

### 1. Trigger
Scheduled and proactive triggers enter the same pipeline.

Examples:
- `digest.morning`
- `digest.evening`
- `feed.update`
- `calendar.leave_now`
- `mail.operational`
- `location.arrival`
- `shopping.replenishment`
- `review.trigger_quality`

### 2. Collect
Fetch only the sources needed for that trigger profile.

Source families:
- Calendar / Gmail / email
- Notes / docs / local knowledge
- Maps / saved places / location history
- Hermes Agent conversation history
- ChatGPT / Grok history where available through local, export, share, or manual paths
- X home timeline diff / bookmarks / likes
- RSS / Atom feeds from official blogs, press rooms, changelogs, research labs, domain media, and specialist third-party blogs
- Known-source registries used as a more reliable retrieval substrate than open web search when possible

Collection policy:
- primary source first
- known-source retrieval before generic search when possible
- secondary/tertiary sources may help discovery, but should resolve back to primary evidence
- preserve provenance and citation chain for every collected item

### 3. Compose
Bundle evidence, rank relevance, suppress spam, and generate the right output type.

Possible outputs:
- digest
- mini_digest
- warning
- nudge
- action_prep
- deep_brief
- source_audit
- reply_draft

Priority should generally remain:
- future relevance
- people overlap
- open loops
- explicit user intent
- source authority and primary confirmation
- then external deltas and passive signals

Within X itself:
- `bookmark > like > home timeline diff`

### 4. Deliver
Deliver the result or prepare the next action through the chosen runtime/channel.

Initial delivery targets:
- Hermes Agent cron jobs
- Slack / Telegram / local files / email summaries via Hermes delivery paths

## Why Hermes first

This repo used to frame itself mainly as an abstract briefing pipeline.
That portability still matters, but it should not be the main entry point.

For now, the practical target is:
- **runtime:** Hermes Agent
- **scheduler:** cron-based runs and event triggers
- **shape:** trigger → collect → compose → deliver
- **goal:** personal briefings and proactive notifications that actually help in the next moment

## Design principles

- **Hermes-first runtime target**
- **Domain-agnostic, expert-depth capable**
- **Primary-source-first retrieval**
- **Known-source retrieval before generic search when possible**
- **Minimal layers**: one runner, not a microservice zoo
- **Live retrieval first where reality supports it**
- **Simple canonical data model**
- **Strong provenance and citation chains** for imported/non-live sources
- **User-intent signals outrank passive signals**
- **Depth adapts to the user's understanding and the task**
- **LLMs compress and explain; they do not replace source truth**

## Docs index

- [`_docs/README.md`](./_docs/README.md)
- [`_docs/01-product-thesis.md`](./_docs/01-product-thesis.md)
- [`_docs/02-system-architecture.md`](./_docs/02-system-architecture.md)
- [`_docs/03-trigger-model.md`](./_docs/03-trigger-model.md)
- [`_docs/04-collection-and-connectors.md`](./_docs/04-collection-and-connectors.md)
- [`_docs/05-synthesis-ranking-and-suppression.md`](./_docs/05-synthesis-ranking-and-suppression.md)
- [`_docs/06-output-delivery-and-actions.md`](./_docs/06-output-delivery-and-actions.md)
- [`_docs/07-state-memory-and-audit.md`](./_docs/07-state-memory-and-audit.md)
- [`_docs/08-roadmap.md`](./_docs/08-roadmap.md)
- [`_docs/09-migration-from-legacy.md`](./_docs/09-migration-from-legacy.md)
- [`_docs/10-appendix-legacy-research.md`](./_docs/10-appendix-legacy-research.md)
- [`_docs/source-notes/conversation-history.md`](./_docs/source-notes/conversation-history.md)
- [`_docs/source-notes/feeds-and-source-registry.md`](./_docs/source-notes/feeds-and-source-registry.md)
- [`_docs/source-notes/x.md`](./_docs/source-notes/x.md)

## Current repo status

This repository is currently a **planning and architecture repo**.
It intentionally documents:
- the Hermes-first system model
- source acquisition constraints
- feed/source registry ideas
- ranking and suppression policy
- delivery and approval patterns
- state and audit requirements
- a phased roadmap for future implementation

It does **not** yet claim a production implementation.
