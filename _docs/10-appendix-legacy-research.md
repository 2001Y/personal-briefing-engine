# Appendix: Legacy Research Carry-over

This appendix preserves the most important informational content from the legacy competitive-research and references docs without making them part of the primary architecture spine.

## Competitive landscape summary

The closest products and references cluster into four categories:

1. **Proactive AI briefings**
   - ChatGPT Pulse
   - Google / Gemini daily briefing style products
2. **Information aggregation digests**
   - generic digest / newsletter consolidators
3. **X-specific memory tools**
   - bookmark summarizers such as Tweetsmash-like products
4. **People-memory systems**
   - Dex
   - Monica
   - related personal CRM products

## Why those products are not enough

### ChatGPT Pulse / similar briefing products
Strengths:
- strong proactive briefing UX
- likely good personalization inside one ecosystem

Weaknesses relative to this repo:
- ecosystem-bounded
- weak multi-agent memory
- weak X timeline diff + bookmark/like resurfacing
- weaker user-owned connector architecture

### Google / Gemini-style daily briefings
Strengths:
- excellent calendar / mail / drive integration
- future-oriented preparation inside Google ecosystem

Weaknesses relative to this repo:
- Google-centric
- weaker long-tail resurfacing
- weak X-centric memory/delta handling

### Digest / feed consolidator products
Strengths:
- broad feed aggregation
- clear delivery mechanics

Weaknesses:
- aggregation-heavy, weak “why now?” logic
- not centered on people prep / open loops / personal operational context

### Dex / Monica / relationship-memory products
Strengths:
- strong people context
- good precedent for relationship memory

Weaknesses:
- not a full operating briefing engine
- weak feed delta and multi-agent conversation ingestion

### X-focused tools
Strengths:
- strong precedents for bookmark summarization and incremental timeline handling

Weaknesses:
- single-source
- poor integration with calendar, email, notes, and conversation memory

## Strategic differentiation carried forward

The defensible wedge remains the combination of:
- future-first briefing
- people-centered preparation
- open-loop handling
- resurfacing of saved/forgotten material
- X timeline diff plus bookmark/like memory
- multi-agent conversation history ingestion
- proactive event triggers beyond time-of-day digests

## Important technical carry-over points

### X timeline diff
The following points from legacy research remain useful, but they are not part of the v1 scope unless an official stable acquisition path is verified:
- home timeline diff is not an append-only cursor problem
- `last_seen_id` alone is insufficient
- state would need `last_poll_at`, `last_top_id`, `seen_ids`, `last_snapshot_ids`, and `delivered_ids`
- bookmarks and likes are stronger than home timeline from an intent perspective

### Conversation history acquisition
The following reality constraints remain canonical:
- Hermes is the easiest and strongest v1 source
- ChatGPT consumer history should be treated as export/manual/share-link first, not assumed live-sync API
- Grok should be treated similarly
- browser automation is experimental and opt-in, not the default architecture

### Product weighting
The following ranking stance remains canonical:
- future relevance > people overlap > open-loop urgency > saved intent > external change > passive taste signal

## Useful reference families retained from legacy docs

The old reference list mainly served these purposes:
- precedent for proactive daily briefing products
- precedent for X timeline/bookmark handling
- precedent for people-memory systems
- precedent for email/open-loop tools

That information is now represented in this appendix rather than as a top-level architecture driver.

## Why this appendix exists

The repo refresh intentionally simplified the canonical doc set.
This appendix exists so that deleting legacy files does **not** mean losing awareness of their research value.
