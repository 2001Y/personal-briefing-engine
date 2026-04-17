# personal-briefing-engine

English README / [日本語版README](./README.ja.md)

Agent-agnostic personal operating briefing engine.

This repository defines a unified architecture for two things that should not be designed separately:

1. **scheduled briefings** such as morning and evening editions
2. **event-driven proactive triggers** such as when movement settles down, when arrival is detected, when a calendar event is getting close, when it is time to leave, when operational mail arrives, and when replenishment reminders become actionable

The project is intentionally **not Hermes-only**. Hermes Agent is one strong runtime example, but the core design should also work as a standalone daemon/CLI or under other agent runtimes.

## Visual summary

![personal-briefing-engine overview](./assets/overview-architecture.svg)

## Product thesis

This is **not** a generic AI news summary app.
The product is a personal operating system for attention and action.
It should answer:

- What matters now?
- What matters later today?
- Who am I about to meet and what context should I recall?
- What changed externally that is actually relevant?
- What should be resurfaced instead of forgotten?
- When should the system proactively act before I ask?

## Top-level architecture

The whole system uses one shared A-F pipeline:

1. **Trigger events** — scheduled or event-driven triggers create a `TriggerEvent`
2. **Collection** — fetch only the sources needed for that trigger profile
3. **Synthesis / ranking / suppression** — bundle evidence into candidates and avoid spam
4. **Output generation** — render digest, warning, nudge, or action-prep output
5. **Delivery / action execution** — send the result or prepare a side-effectful action
6. **State / memory / audit** — persist cursors, delivery history, approvals, and feedback

Morning and evening are therefore **just scheduled trigger profiles**, not separate engines.

## Trigger families

### Scheduled triggers
- `digest.morning`
- `digest.evening`
- `review.trigger_quality`

### Event-driven triggers
- `location.arrival`
- `location.dwell`
- `location.area_change`
- `calendar.leave_now`
- `calendar.gap_window`
- `mail.operational`
- `shopping.replenishment`
- later: `interest.watch`, `price.drop`, `reservation.change`

## Source families

### Operational context
- Calendar
- Gmail / email
- Notes / docs
- Maps / saved places
- Location history (for example Dawarich)

### Agent conversation history
- Hermes Agent
- ChatGPT
- Grok

### Social / memory sources
- X home timeline diff
- X bookmarks
- X likes
- later: Google Photos, Instagram, blog/RSS, commerce/order history

## Design principles

- **Agent-agnostic core**
- **Minimal layers**: one runner, not a microservice zoo
- **Live retrieval first**
- **Simple canonical data model**
- **Strong provenance** for imported/non-live sources
- **User-intent signals outrank passive signals**
- **LLMs compress and explain; they do not replace source truth**

## X / Twitter stance

X is important, but it is not the whole product.

Priority should remain:
- future relevance
- people overlap
- open loops
- saved intent
- then external deltas

Within X itself:
- `bookmark > like > home timeline diff`

Home timeline diff is treated as a **high-value but noisy novelty source**. It must pass through relevance and quota rules before appearing in output.

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
- the unified system model
- source acquisition constraints
- ranking and suppression policy
- state and audit requirements
- a phased roadmap for future implementation

It does **not** yet claim a production implementation.
