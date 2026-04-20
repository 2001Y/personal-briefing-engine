# Hermes Pulse Slack/body/location alerts Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make Hermes Pulse Slack delivery actually usable in production, enrich feed items with article body text when reality supports it, and add a high-frequency location-driven alert slice that fits Hermes Pulse’s event-first design instead of degenerating into a noisy tracker.

**Architecture:** Keep the existing `trigger -> collect -> compose -> deliver` shape. Add a Slack-native delivery formatting layer after synthesis, add bounded body enrichment inside the feed connector with strong provenance and reversible defaults, and add a new narrow `location.dwell` trigger family for high-frequency polling that can emit context-aware nudges for stopped-moving / meal / snack moments without pretending to solve all location intelligence in v1.

**Tech Stack:** Python 3.11+, argparse, pytest, standard-library HTML parsing/networking, existing Hermes Pulse trigger registry/collection/rendering/delivery helpers.

---

## Product decisions from Hermes Pulse design docs

1. **Slack formatting is a delivery concern, not a summarization concern.**
   - Keep canonical archive markdown as the source artifact.
   - Convert it to Slack-native text only at direct delivery time.
   - Split oversized digests into a parent post plus threaded replies.

2. **`body` fetch must be bounded and source-rigorous.**
   - Do not fetch arbitrary third-party pages for every item forever.
   - Only enrich feed items that already have a primary URL.
   - Use the article page as primary evidence and retain the original feed excerpt too.
   - Keep extraction small and deterministic rather than adding a heavy scraping stack.

3. **High-frequency location alerts should be one narrow trigger family, not many ad-hoc jobs.**
   - Add `location.dwell.default` as the canonical trigger.
   - Let one trigger emit a `nudge` with different reasons in metadata: `stopped_moving`, `meal_window`, `snack_window`.
   - This matches the product docs: event-driven proactivity, minimal layers, right-moment delivery, and trigger-specific suppression.

4. **5-minute monitoring belongs to the scheduler/runtime layer, but the repo should first implement the trigger + fixture path.**
   - Implement the trigger, connector contract, rendering, and tests now.
   - Add docs describing the intended 5-minute launchd/cron polling shape.
   - Do not silently install a real recurring job during implementation.

---

## Task 1: Add a plan document for this feature slice

**Objective:** Capture the design and execution plan inside the repo before code changes.

**Files:**
- Create: `docs/plans/2026-04-20-hermes-pulse-slack-body-location-alerts.md`

**Step 1: Write the plan**

Document:
- why Markdown links fail in Slack now
- why `body` is missing today
- why `location.dwell` is the right high-frequency trigger shape
- the TDD sequence below

**Step 2: Commit later with the feature/docs checkpoints**

No separate early commit required if implementation follows immediately in the same branch.

---

## Task 2: Add failing tests for Slack-native formatting and chunked thread delivery

**Objective:** Prove the current raw markdown passthrough is insufficient and define the target behavior.

**Files:**
- Modify: `tests/test_direct_delivery.py`

**Step 1: Write failing tests**

Add tests that assert:
1. markdown links like `[Launch update](https://example.com/posts/launch-update)` become Slack links `<https://example.com/posts/launch-update|Launch update>`
2. oversized digest content is split into multiple posts
3. the first post uses the caller-provided `thread_ts` when present
4. when no `thread_ts` is provided, later chunks use the timestamp returned from the first Slack response
5. `DirectDeliveryResult` stores all Slack responses, not only one

Example test shapes:

```python
def test_post_canonical_digest_to_slack_converts_markdown_links_to_slack_links(...):
    ...


def test_post_canonical_digest_to_slack_splits_oversized_digest_into_threaded_posts(...):
    ...
```

**Step 2: Run tests to verify failure**

Run:
```bash
pytest tests/test_direct_delivery.py -q
```

Expected: FAIL because current implementation posts one raw markdown string.

**Step 3: Implement minimal code**

In `src/hermes_pulse/direct_delivery.py`:
- expand `DirectDeliveryResult` to hold `posted_messages` and `slack_responses`
- add helpers such as:
  - `_render_digest_for_slack(markdown: str) -> str`
  - `_split_slack_text(text: str, limit: int = 3500) -> list[str]`
  - `_post_slack_chunks(...)`
- keep the archive markdown unchanged on disk
- call the Slack renderer only inside direct delivery

Implementation rules:
- convert markdown links to Slack links with a regex
- keep plain URLs intact
- split on paragraph boundaries first, then line boundaries, then hard-wrap only as a fallback
- first chunk uses `thread_ts` if provided; otherwise later chunks should thread under the first response timestamp

**Step 4: Run tests to verify pass**

Run:
```bash
pytest tests/test_direct_delivery.py -q
```

Expected: PASS.

**Step 5: Run full suite**

Run:
```bash
pytest -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/hermes_pulse/direct_delivery.py tests/test_direct_delivery.py
git commit -m "feat: make Slack direct delivery render links and split threads"
```

---

## Task 3: Add failing tests for bounded feed body enrichment

**Objective:** Make feed items carry real article body text when the page is fetchable, without breaking existing feed behavior.

**Files:**
- Modify: `tests/test_feed_connector.py`
- Possibly create: `fixtures/feed_samples/article_page.html`

**Step 1: Write failing tests**

Add tests that assert:
1. when a feed item has a URL and the article page is fetchable, the item body is populated from the page text
2. when article body fetch fails, collection still succeeds and keeps the feed item
3. existing feed excerpt/url/provenance behavior remains unchanged
4. extraction strips HTML and ignores script/style noise

A good minimal approach is to inject a page fetcher into `FeedRegistryConnector` in tests:

```python
def test_feed_registry_connector_enriches_body_from_article_page_when_available():
    ...
```

**Step 2: Run tests to verify failure**

Run:
```bash
pytest tests/test_feed_connector.py -q
```

Expected: FAIL because connector currently never sets `body`.

**Step 3: Implement minimal code**

In `src/hermes_pulse/connectors/feed_registry.py`:
- add optional `page_fetcher: Callable[[str], str] | None = None`
- add a bounded HTML text extractor using stdlib `html.parser.HTMLParser`
- for each parsed feed item:
  - keep `excerpt` from feed description
  - if `url` exists and a page fetcher is available (or live fetching is enabled), attempt to fetch the article page
  - extract readable text and store a truncated-but-useful body
  - if body extraction fails, log and continue
- prefer article body text over leaving `body` null, but do not erase `excerpt`

Boundaries:
- keep extraction deterministic and lightweight
- truncate overly large body text
- do not add heavy dependencies

**Step 4: Run tests to verify pass**

Run:
```bash
pytest tests/test_feed_connector.py -q
```

Expected: PASS.

**Step 5: Run full suite**

Run:
```bash
pytest -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/hermes_pulse/connectors/feed_registry.py tests/test_feed_connector.py fixtures/feed_samples/article_page.html
git commit -m "feat: enrich feed items with fetched article bodies"
```

---

## Task 4: Add failing tests for the new `location.dwell` trigger family

**Objective:** Define the high-frequency location alert slice around one canonical trigger instead of many special-case schedulers.

**Files:**
- Modify: `src/hermes_pulse/trigger_registry.py`
- Modify: `src/hermes_pulse/collection.py`
- Modify: `src/hermes_pulse/cli.py`
- Modify: `src/hermes_pulse/rendering.py`
- Modify: `src/hermes_pulse/connectors/location_context.py`
- Create: `tests/test_location_dwell.py`
- Modify: `tests/test_collection.py`
- Create: `fixtures/location/location_dwell_meal.json`
- Create: `fixtures/location/location_dwell_snack.json`
- Create: `fixtures/location/location_dwell_stop.json`

**Step 1: Write failing tests**

Add tests that assert:
1. `location.dwell.default` resolves from the registry with output mode `nudge`
2. collection preset `location_dwell` invokes only `location_context`
3. CLI command `location-dwell` writes a nudge markdown file from a location fixture
4. dwell output includes:
   - place name
   - reason-specific message
   - Google Maps URL
5. meal-window and snack-window fixtures produce different guidance than a generic stopped-moving fixture

**Step 2: Run tests to verify failure**

Run:
```bash
pytest tests/test_location_dwell.py tests/test_collection.py -q
```

Expected: FAIL because the trigger/command/rendering do not exist yet.

**Step 3: Implement minimal code**

Implementation shape:
- add `location.dwell.default` to `trigger_registry.py`
- add `location_dwell` preset in `collection.py`
- extend `location_context.py` so fixtures can carry:
  - `detected_reason`
  - `place_category`
  - `local_time`
  - `dwell_minutes`
  - `nearby_context`
- add renderer `render_location_dwell_nudge(items)` in `rendering.py`
- add CLI command `location-dwell` in `cli.py`

Behavior rules:
- `meal_window` when local time is around lunch/dinner and the place/context suggests eating is plausible
- `snack_window` when local time is around afternoon break or a snack-oriented venue/context fits
- `stopped_moving` as the default low-urgency context reminder when the user has paused somewhere meaningful
- output mode stays `nudge`, not `warning`
- include map link every time

**Step 4: Run tests to verify pass**

Run:
```bash
pytest tests/test_location_dwell.py tests/test_collection.py -q
```

Expected: PASS.

**Step 5: Run full suite**

Run:
```bash
pytest -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/hermes_pulse/trigger_registry.py src/hermes_pulse/collection.py src/hermes_pulse/cli.py src/hermes_pulse/rendering.py src/hermes_pulse/connectors/location_context.py tests/test_location_dwell.py tests/test_collection.py fixtures/location/location_dwell_*.json
git commit -m "feat: add location dwell nudge trigger"
```

---

## Task 5: Document the 5-minute polling design without silently installing it

**Objective:** Make the runtime shape explicit: high-frequency location polling is supported as a trigger family, but scheduler installation remains an operator/runtime step.

**Files:**
- Modify: `README.md`
- Modify: `README.ja.md`
- Modify: `_docs/03-trigger-model.md`
- Modify: `_docs/04-collection-and-connectors.md`
- Modify: `_docs/06-output-delivery-and-actions.md`
- Modify: `_docs/07-state-memory-and-audit.md`

**Step 1: Update docs**

Document:
- Slack direct delivery now renders Slack-native links and splits oversized digests into threads
- feed connector now enriches `body` from article pages minimally
- `location.dwell.default` exists as the high-frequency location alert slice
- the intended scheduler shape is a 5-minute poll against a local-store location source such as Dawarich
- suppression/cooldown should prevent spam between successive polls

**Step 2: Run targeted tests if doc text references exact commands**

At minimum rerun:
```bash
pytest tests/test_direct_delivery.py tests/test_feed_connector.py tests/test_location_dwell.py -q
```

**Step 3: Commit docs**

```bash
git add README.md README.ja.md _docs/03-trigger-model.md _docs/04-collection-and-connectors.md _docs/06-output-delivery-and-actions.md _docs/07-state-memory-and-audit.md docs/plans/2026-04-20-hermes-pulse-slack-body-location-alerts.md
git commit -m "docs: describe Slack delivery and location dwell alerts"
```

---

## Task 6: Smoke verification

**Objective:** Prove the new slices work in repo-local execution.

**Files:**
- No code changes required unless smoke finds regressions.

**Step 1: Direct-delivery smoke**

Run a repo-local test invocation that generates a digest and verifies the resulting Slack-rendered chunks in a fake poster test, or if doing live smoke later, use a safe test channel/thread.

**Step 2: Feed body smoke**

Run a fixture-backed test proving article body enrichment lands in `raw/collected-items.json`.

**Step 3: Location dwell smoke**

Run:
```bash
PYTHONPATH=src python -m hermes_pulse.cli location-dwell \
  --source-registry fixtures/source_registry/sample_sources.yaml \
  --location-fixture fixtures/location/location_dwell_meal.json \
  --output /tmp/hermes-pulse-location-dwell.md
```

Expected:
- output file exists
- includes place name
- includes meal/snack/stopped-moving reason
- includes map link

**Step 4: Full suite**

Run:
```bash
pytest -q
```

Expected: PASS.

---

## Final verification checklist

- [ ] Slack delivery converts markdown links to Slack-native links
- [ ] Oversized digests split into parent + threaded replies
- [ ] `DirectDeliveryResult` preserves multi-post delivery results
- [ ] Feed items can carry fetched article `body`
- [ ] Feed body fetch failures do not break collection
- [ ] `location.dwell.default` exists and is test-covered
- [ ] `location-dwell` CLI works with fixtures
- [ ] Docs reflect what is actually implemented
- [ ] Full `pytest -q` passes

## Notes for future work

Not in this slice unless already trivial after implementation:
- real Dawarich live connector instead of fixture-driven location context
- automatic meal/snack confidence tuning from feedback history
- launchd/cron installer helpers for 5-minute location polling
- stronger nearby-place suggestions from saved places / starred places once a stable acquisition path exists
