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

- [source-notes/conversation-history](./source-notes/conversation-history.md)
- [source-notes/feeds-and-source-registry](./source-notes/feeds-and-source-registry.md)
- [source-notes/x](./source-notes/x.md)

## Reading order

If you want the shortest path:
1. `01-product-thesis`
2. `02-system-architecture`
3. `03-trigger-model`
4. `04-collection-and-connectors`
5. `05-synthesis-ranking-and-suppression`
6. `06-output-delivery-and-actions`
7. `07-state-memory-and-audit`

## Why this doc set exists

The repository is now positioned as **Hermes Pulse**: a Hermes-first, domain-agnostic but expert-depth-capable briefing pipeline.
Morning and evening editions are treated as scheduled trigger profiles inside the same system that also handles proactive event triggers, feed updates, known-source retrieval, and trigger self-review.

The current implementation target is practical Hermes-first execution:
trigger → collect → compose → deliver.

The deeper stance is equally important:
- primary-source-first retrieval
- known-source retrieval before generic search when possible
- strong provenance and citation chains
- depth that adapts to the user and the task rather than flattening every topic into generic summaries
