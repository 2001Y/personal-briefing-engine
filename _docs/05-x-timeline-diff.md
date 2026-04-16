# X Timeline Diff Design

## Goal

Include **meaningful X home timeline changes** in morning/evening digests without flooding the user and without pretending the home feed is a simple append-only stream.

## Why timeline diff is tricky

The X home feed is not a clean chronological append log.
Even when using a reverse-chronological or home timeline endpoint, practical issues remain:

- the feed can reorder
- older posts can reappear
- the same post can be encountered via home + like + bookmark paths
- the morning/evening digest should not resend what was already delivered

Therefore timeline diff cannot rely only on a single `last_seen_id` cursor.

## Recommended state model

Per source (`home`, `bookmarks`, `likes`) persist:

- `last_poll_at`
- `last_top_id`
- `seen_ids` (TTL/LRU set, e.g. 7–14 days)
- `last_snapshot_ids` (top N from previous poll, e.g. 100–300)
- `delivered_ids` (IDs already included in a digest)

## Recommended algorithm

### Home timeline diff

At each poll:

1. Fetch the latest `N` posts from home timeline
2. Extract `current_ids`
3. Compute candidate new IDs:
   - `candidate_ids = current_ids - seen_ids`
4. Filter candidate IDs using a grace/time window:
   - prefer posts newer than `last_poll_at - grace_window`
   - or IDs greater than previous top range when applicable
5. Remove posts already in `delivered_ids`
6. Persist updated `seen_ids`, `last_snapshot_ids`, `last_top_id`, `last_poll_at`

### Bookmarks / likes diff

Bookmarks and likes are closer to “user action” streams.
For each poll:

1. Fetch latest `N` records
2. Treat unseen IDs as additions
3. Optionally ignore removals in v1
4. Persist `seen_ids` and `delivered_ids`

## Why not rely only on `last_seen_id`

Because home feeds may surface or re-surface posts non-monotonically.
Simple cursor-only logic risks:
- missing posts
- duplicate resurfacing
- overcounting re-ranked content as truly new

Use **set difference + delivery suppression + recency guard**.

## Candidate weighting

X-derived scoring should usually be:

- bookmark > like > home timeline

Suggested X-specific scoring signals:
- explicit save/bookmark bonus
- like bonus
- recency
- author affinity
- topic overlap with today’s schedule
- entity overlap with today’s people
- novelty bonus
- already-delivered penalty

## Digest inclusion policy

### Home timeline items should be included only when at least one is true:
- topic overlaps with today/tomorrow events
- entity overlaps with a person/org in upcoming meetings
- matches recent agent conversation themes
- matches user-saved interest clusters
- is unusually high-signal by engagement/author priority

### Bookmarks / likes can be included via resurfacing when:
- they have not been surfaced recently
- they match current schedule/people/topics
- they have remained unsurfaced for a long time but still look relevant

## Polling cadence

For morning/evening digest quality, a practical starting point is:

- home timeline: every 10–30 minutes, or a few lightweight polls between digest runs
- bookmarks: every 15–60 minutes
- likes: every 15–60 minutes

If cost/control is tighter, use:
- light intermittent home polling to avoid missed mid-day items
- deeper fetch near digest generation

## De-duplication rules across X sources

If the same post appears in:
- home timeline
- bookmarks
- likes

merge into one canonical post candidate with multiple source tags.

Example metadata:

```json
{
  "sources": ["x_home_timeline", "x_bookmark"],
  "first_seen_via": "x_home_timeline",
  "saved": true,
  "liked": false
}
```

## Fallback strategy if home timeline access is constrained

Preferred order:
1. official home timeline API
2. synthetic home from selected lists / followed-user timelines
3. bookmarks + likes + selected list diffs
4. browser automation plugin as experimental last resort

## Engineering takeaway

Treat X timeline diff as a **high-value but noisy input**.
Do not let it dominate the product. Instead:
- detect deltas carefully
- dedupe aggressively
- rank below explicit user intent
- inject only the most relevant few items into the digest
