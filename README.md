# hermes-briefing-pipeline

English README / [日本語版README](./README.ja.md)

Hermes-first personal briefing pipeline for scheduled and proactive delivery.

This repository is organized around one practical flow:

1. **Trigger** — cron schedules or other trigger sources start a run
2. **Collect** — fetch only the sources needed for that trigger
3. **Compose** — synthesize context into a briefing, reply draft, warning, or nudge
4. **Deliver** — send the result to the user through the chosen channel

Today, the primary target runtime is **Hermes Agent**. The design may later be adapted to OpenClaw, Codex, Claude Code, or standalone runtimes using skills and MCP, but this repository currently optimizes for the Hermes use case first.

## Visual summary

![hermes-briefing-pipeline overview](./assets/overview-architecture.svg)

## What this repo does

This is **not** a generic AI news summary app.
It is a Hermes-first personal operating briefing pipeline for attention and action.
It should answer:

- What matters now?
- What matters later today?
- Who am I about to meet and what context should I recall?
- What changed externally that is actually relevant?
- What should be resurfaced instead of forgotten?
- When should the system proactively act before I ask?

## Core flow

The runtime-facing flow is intentionally simple:

### 1. Trigger
Scheduled and proactive triggers enter the same pipeline.

Examples:
- `digest.morning`
- `digest.evening`
- `review.trigger_quality`
- `location.arrival`
- `location.dwell`
- `calendar.leave_now`
- `mail.operational`
- `shopping.replenishment`

### 2. Collect
Fetch only the sources needed for that trigger profile.

Source families:
- Calendar / Gmail / email
- Notes / docs
- Maps / saved places
- Location history (for example Dawarich)
- Hermes Agent conversation history
- ChatGPT / Grok history where available through local, export, share, or manual paths
- X home timeline diff / bookmarks / likes

### 3. Compose
Bundle evidence, rank relevance, suppress spam, and generate the right output type.

Possible outputs:
- digest
- mini-digest
- warning
- nudge
- action-prep
- reply draft

Priority should remain:
- future relevance
- people overlap
- open loops
- saved intent
- then external deltas

Within X itself:
- `bookmark > like > home timeline diff`

### 4. Deliver
Deliver the result or prepare the next action through the chosen runtime/channel.

Initial delivery targets:
- Hermes Agent cron jobs
- Slack / Telegram / local files via Hermes delivery paths

## Why Hermes first

This repo used to frame itself mainly as agent-agnostic architecture.
That portability still matters, but it should not be the main entry point.

For now, the practical target is:
- **runtime:** Hermes Agent
- **scheduler:** cron-based runs
- **shape:** trigger → collect → compose → deliver
- **goal:** personal briefings and proactive notifications that actually help in the next moment

## Future portability

The internal model is meant to stay portable.
Later, the same structure may run under:
- OpenClaw
- Codex + skills + MCP
- Claude Code + skills + MCP
- standalone daemons / CLIs

But those are follow-on targets, not the primary positioning of this repository today.

## Design principles

- **Hermes-first runtime target**
- **Minimal layers**: one runner, not a microservice zoo
- **Live retrieval first**
- **Simple canonical data model**
- **Strong provenance** for imported/non-live sources
- **User-intent signals outrank passive signals**
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
- [`_docs/source-notes/x.md`](./_docs/source-notes/x.md)
- [`_docs/source-notes/conversation-history.md`](./_docs/source-notes/conversation-history.md)
- [`_docs/08-roadmap.md`](./_docs/08-roadmap.md)
- [`_docs/09-migration-from-legacy.md`](./_docs/09-migration-from-legacy.md)
- [`_docs/10-appendix-legacy-research.md`](./_docs/10-appendix-legacy-research.md)

## Current repo status

This repository is currently a **planning and architecture repo**.
It intentionally documents:
- the Hermes-first system model
- source acquisition constraints
- ranking and suppression policy
- delivery and approval patterns
- state and audit requirements
- a phased roadmap for future implementation

It does **not** yet claim a production implementation.
