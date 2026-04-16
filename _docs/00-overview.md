# Overview

## Vision

`personal-briefing-engine` is a personal operating briefing system that produces:

- a **morning edition** optimized for preparation and prioritization
- an **evening edition** optimized for closure, carry-over, and resurfacing

Unlike generic AI news summaries, the product is centered on:

1. **Future relevance** — today/tomorrow schedule, deadlines, upcoming meetings
2. **People context** — who the user will meet and what prior context matters
3. **Open loops** — unresolved email, ongoing conversations, pending decisions
4. **Resurfacing** — old bookmarks, likes, notes, photos, and conversation fragments that matter now
5. **External change** — especially **X home timeline diffs**

## Design principles

- Agent-agnostic core; connectors are replaceable
- Live retrieval first, heavy warehousing later
- Minimal canonical schema shared across all sources
- X timeline is included, but not the sole product center
- User-saved signals (bookmarks) outrank passive signals (likes, timeline)
- Rendering uses LLMs as compression/presentation helpers, not as the source of truth

## v1 included sources

- Calendar
- Gmail / email
- Hermes Agent session history
- ChatGPT session history
- Grok session history
- Notes / docs
- X bookmarks
- X likes
- X home timeline diff

## v1 explicit non-goals

These may be added later, but are not required for v1:

- full-text mirroring of every source
- complex knowledge graph / vector DB first
- heavy end-user manual categorization UI
- high-frequency real-time streaming UX
- deep autonomous importance-learning
