# personal-briefing-engine

Agent-agnostic personal briefing engine for morning/evening digests.

This project is designed to work with Hermes Agent, ChatGPT, Grok, and future agents through connector abstractions instead of provider-specific assumptions.

## Goals

- Build a high-signal morning/evening digest around:
  - future schedule context
  - people context
  - open loops
  - resurfaced memories
  - X timeline diffs
  - X bookmarks / likes resurfacing
  - conversation history from Hermes Agent, ChatGPT, and Grok
- Keep the core engine independent from any one agent runtime.
- Support multiple acquisition modes:
  - local state/database
  - official API
  - official export import
  - share-link import
  - manual transcript import
  - experimental browser automation plugins

## Initial docs

See [`_docs/`](./_docs):

- `00-overview.md`
- `01-competitive-research.md`
- `02-product-requirements.md`
- `03-architecture.md`
- `04-connectors-and-ingestion.md`
- `05-x-timeline-diff.md`
- `06-implementation-plan.md`

## Status

Planning repository initialized with research and implementation design docs.
