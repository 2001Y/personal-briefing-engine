# Feeds and Source Registry Notes

## Why this note exists

Hermes Pulse should not rely on generic web search as its only external retrieval path.
Curated feed and source registries provide a firmer substrate for reliable collection and verification.

## Registry families

Useful registry buckets include:
- official blogs / newsroom feeds
- changelog / release feeds
- research lab feeds
- standards / policy / regulatory feeds
- domain-specialist media feeds
- trusted expert third-party blogs

## Authority tiers

Suggested tiers:
- `primary`
- `trusted_secondary`
- `discovery_only`

Interpretation:
- `primary`: official docs, repo, changelog, press, paper, standard, filing, regulation
- `trusted_secondary`: strong specialist analysis worth reading and citing, but not enough alone for a high-confidence claim
- `discovery_only`: useful for surfacing possibilities, not for final authority

## Retrieval order

Preferred retrieval order when current external knowledge is needed:
1. local or user-owned artifact
2. known source registry / feed registry
3. direct primary-source lookup on known domains
4. generic web search

## Why feeds are more than news

Feeds matter not just for “news” but for:
- product changes
- API/changelog monitoring
- research progress
- policy/regulatory updates
- domain-specialist commentary
- long-tail expert publishing

## Feed update trigger behavior

A new feed item should not always notify the user.
Promotion should depend on:
- user relevance
- domain relevance
- authority tier
- novelty
- whether the item changes action or understanding

## Registry-backed search hints

Each registry entry can carry:
- official site domain
- rss/atom url
- common title patterns
- search hints
- likely primary-source targets
- topic tags

This lets the collector use a more deterministic path than open-ended search alone.
