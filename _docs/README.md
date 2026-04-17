# Docs Index

## Canonical docs

1. [01-product-thesis](./01-product-thesis.md)
2. [02-system-architecture](./02-system-architecture.md)
3. [03-trigger-model](./03-trigger-model.md)
4. [04-collection-and-connectors](./04-collection-and-connectors.md)
5. [05-synthesis-ranking-and-suppression](./05-synthesis-ranking-and-suppression.md)
6. [06-output-delivery-and-actions](./06-output-delivery-and-actions.md)
7. [07-state-memory-and-audit](./07-state-memory-and-audit.md)
8. [08-roadmap](./08-roadmap.md)
9. [09-migration-from-legacy](./09-migration-from-legacy.md)
10. [10-appendix-legacy-research](./10-appendix-legacy-research.md)

## Source notes

- [source-notes/x](./source-notes/x.md)
- [source-notes/conversation-history](./source-notes/conversation-history.md)

## Reading order

If you want the shortest path:
1. `01-product-thesis`
2. `02-system-architecture`
3. `03-trigger-model`
4. `05-synthesis-ranking-and-suppression`
5. `06-output-delivery-and-actions`
6. `07-state-memory-and-audit`

## Why this doc set exists

The repository is now positioned as a Hermes-first briefing pipeline.
Morning and evening editions are treated as scheduled trigger profiles inside the same system that also handles proactive event triggers such as location arrival, dwell, calendar proximity, inbound mail, shopping/replenishment, and trigger self-review.

The internal structure remains portable, but the current implementation target is practical Hermes-first cron execution: trigger → collect → compose → deliver.
