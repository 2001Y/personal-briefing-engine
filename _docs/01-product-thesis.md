# Product Thesis

## Product statement

Build **Hermes Pulse** as a Hermes-first personal operating briefing pipeline that combines future preparation, people context, unresolved loops, resurfaced memory, authoritative external deltas, and source-rigorous expert-depth synthesis.

## What makes this product different

Most briefing products collapse into one of a few weak shapes:
- generic news digest
- feed aggregation
- note retrieval
- relationship memory
- chat summary without source rigor

This project should instead combine:
1. **future-first preparation**
2. **people-centered context recall**
3. **open-loop management**
4. **resurfacing of saved/forgotten material**
5. **event-driven proactivity**
6. **source-rigorous retrieval and verification**
7. **depth calibration to the user's understanding and domain need**

## Core user questions

### Morning edition
- What matters today?
- Who am I meeting and what should I remember before that?
- Which inbox / conversation / task loops are still open?
- Which saved or older items are newly relevant today?
- Which external changes are authoritative enough to trust?

### Evening edition
- What happened today?
- What remains unfinished?
- What should carry into tomorrow?
- What is worth reading tonight rather than forgetting?
- What deserves a deeper follow-up tomorrow?

### Event-driven moments
- Did I just arrive somewhere important?
- Do I need to leave now to make the next event?
- Did an operational email materially change today?
- Did a known source publish something that changes a decision or understanding?
- Should this stay a short update or become an expert-depth synthesis?

## Product stance

This repo should not position itself as news-specific.
It should be **domain-agnostic** while being able to go extremely deep in any domain where the user has strong interest or current need.

That means the product must support:
- broad but curated source acquisition
- authoritative-source preference
- escalation from concise briefing to deeper analysis
- user-aware explanation depth
- evidence chains that remain inspectable

## Priority order

At the product level, relevance should generally rank as:
1. explicit future relevance
2. people overlap with near-future schedule
3. unresolved / operational urgency
4. explicit user-intent signals
5. source authority and primary confirmation
6. external changes
7. passive taste signals

This order prevents feeds, social noise, and thin summaries from overwhelming the product.

## Source-rigor requirement

The product should prefer the lowest-layer source that is realistically accessible:
- official docs
- official blog / newsroom / press
- changelog / repo / release note
- standards / filings / papers / regulations
- direct exports / local stores

Third-party articles remain useful for discovery and framing, but they should resolve back to primary evidence when possible.

## Why RSS and known-source registries matter

Open web search is useful but not sufficient.
The system should maintain curated source registries that include:
- official blogs and newsroom feeds
- research lab and standards feeds
- domain-specialist media feeds
- trusted third-party expert blogs

These registries enable a more reliable retrieval path than generic search alone and are reusable across domains, not just news.

## Runtime portability requirement

The repo should optimize for Hermes-first execution without assuming one runtime forever.
The architecture should remain valid when run:
- inside Hermes Agent
- as a standalone service
- under future agent runtimes

## Non-goals for v1

- heavy microservice decomposition
- perfect live sync for every source
- flattening all topics into one summary style
- source-free opinionated synthesis
- autonomous triggering from noisy social sources alone
- replacing evidence with LLM confidence

## v1 source commitment

### Must cover
- Calendar
- Gmail / email
- Notes / docs
- Hermes Agent history
- RSS / Atom feed registries
- known-source retrieval registries
- ChatGPT history where feasible
- Grok history where feasible
- X home timeline diff
- X bookmarks
- X likes

### Strong future candidates
- Google Photos
- Maps saved places / starred places
- commerce / order history
- reservation systems
- blogs / RSS / long-tail web monitoring beyond the initial curated sets

## Strategic conclusion

The sharpest wedge is the combination of:
- future planning
- people prep
- source-rigorous evidence gathering
- multi-agent memory
- curated feed and known-source retrieval
- expert-depth synthesis when needed
- proactive triggers beyond time-of-day editions
