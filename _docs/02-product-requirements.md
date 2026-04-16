# Product Requirements

## Product statement

Build an agent-agnostic personal briefing engine that assembles a high-signal morning and evening digest from multiple personal data sources and external feeds.

## Primary user value

### Morning edition
Help the user answer:
- What matters today?
- Who am I meeting and what context should I remember?
- Which unresolved threads should I close first?
- What changed on X since I last checked?
- What older saved material is suddenly relevant again?

### Evening edition
Help the user answer:
- What happened today?
- What remains open?
- What should I prepare for tomorrow?
- What is worth reading tonight?
- What should be resurfaced instead of forgotten?

## Required v1 sources

### Personal operational context
- Calendar
- Gmail / email
- Notes / docs

### Agent conversation history
- Hermes Agent session history
- ChatGPT session history
- Grok session history

### X sources
- Home timeline diffs
- Bookmarks
- Likes

## Core digest lanes

### Morning lanes
- today
- people
- incoming
- resurface
- followup

### Evening lanes
- today
- followup
- tomorrow
- tonight
- resurface

## Ranking rules

Signal priority should be:
1. explicit future relevance
2. person overlap with upcoming meetings
3. unresolved/open loop urgency
4. user-saved intent (bookmark, explicit save)
5. recent external changes
6. passive taste signal (likes)

## Success criteria for v1

- Produces morning and evening digests with stable section structure
- Includes at least one meaningful people-context bundle when schedule data allows
- Includes X timeline diffs without flooding the digest
- Includes resurfaced bookmarks / likes only when relevant or long-neglected
- Works even when some connectors are unavailable
- Core engine remains agent-agnostic

## Non-functional requirements

- Connectors are capability-based, not provider-hardcoded in the engine
- Raw artifacts should be retained where practical for re-normalization
- State store must support idempotent sync and duplicate suppression
- Timeline diff logic must tolerate ranked feeds and reordering
