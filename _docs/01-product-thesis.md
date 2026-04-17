# Product Thesis

## Product statement

Build a **Hermes-first personal briefing pipeline** that combines future preparation, people context, unresolved loops, resurfaced memory, and carefully filtered external deltas.

## What makes this product different

Most briefing products collapse into one of four weak shapes:
- generic news digest
- feed aggregation
- note retrieval
- CRM / relationship memory

This project should instead combine five distinct values:

1. **future-first preparation**
2. **people-centered context recall**
3. **open-loop management**
4. **resurfacing of saved/forgotten material**
5. **event-driven proactivity**

## Core user questions

### Morning edition
- What matters today?
- Who am I meeting and what should I remember before that?
- Which inbox / conversation / task loops are still open?
- Which saved or older items are newly relevant today?
- What changed on X that actually overlaps with today’s context?

### Evening edition
- What happened today?
- What remains unfinished?
- What should carry into tomorrow?
- What is worth reading tonight rather than forgetting?
- What should be resurfaced while the context is still warm?

### Event-driven moments
- Did I just arrive somewhere important?
- Am I now likely dwelling rather than passing through?
- Do I need to leave now to make the next event?
- Did an operational email just materially change today?
- Is there a replenishment / repurchase need becoming actionable?

## Priority order

At the product level, relevance should generally rank as:

1. explicit future relevance
2. people overlap with near-future schedule
3. unresolved / operational urgency
4. explicit user-intent signals
5. external changes
6. passive taste signals

This order matters because it prevents X, news, and noisy feeds from overwhelming the product.

## Why X still matters

X is special here for two reasons:

1. it is both a **fresh external signal** and a **memory surface**
2. the user explicitly values timeline diff, bookmarks, and likes resurfacing

But X must remain subordinate to the larger product thesis.
The product is not “an X digest with some calendar sprinkled on top.”
It is a personal operating briefing engine where X is one important source family.

## Runtime portability requirement

The repo should currently optimize for Hermes-first execution without assuming one runtime forever.
The architecture should remain valid when run:
- inside Hermes Agent
- as a standalone service
- under future agent runtimes

That means:
- connectors own provider-specific auth
- ingestion modes are first-class
- core synthesis and output contracts remain runtime-neutral

## Non-goals for v1

- heavy microservice decomposition
- knowledge graph or vector DB as a prerequisite
- perfect live sync for every source
- strong end-user taxonomy / manual labeling UI
- autonomous triggering from social sources alone
- full historical mirroring of everything the user has ever seen

## v1 source commitment

### Must cover
- Calendar
- Gmail / email
- Notes / docs
- Hermes Agent history
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
- blogs / RSS / long-tail web monitoring

## Strategic conclusion

The sharpest wedge is the combination of:
- future planning
- people prep
- multi-agent memory
- X delta + resurfacing
- proactive triggers beyond time-of-day editions
