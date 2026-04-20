# Hermes Pulse Phase 1 Foundation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the minimum executable Hermes Pulse runtime that can generate a morning digest from scheduled triggers, curated feed/source registries, and a small set of high-value connectors while preserving strong provenance and a path to expert-depth expansion.

**Architecture:** Start with one Python codebase, one SQLite database, one trigger registry, and one serial pipeline: trigger → collect → compose → deliver. Implement only the minimum needed for a stable scheduled morning digest plus the source-registry/feed foundation, so later event triggers and deeper domain packs can reuse the same primitives without redesign.

**Tech Stack:** Python 3.11+, SQLite, pytest, feedparser (or standard-library XML parsing if preferred), pydantic/dataclasses, Typer or argparse for CLI entrypoints.

---

## Current context / assumptions

- The repo is currently documentation-first and contains no runtime implementation yet.
- The design now assumes:
  - Hermes-first runtime target
  - primary-source-first retrieval
  - known-source retrieval before generic search when possible
  - RSS / Atom source registries
  - output modes including `digest`, `deep_brief`, and `source_audit`
- The first useful deliverable should be a **scheduled morning digest**, not a full event-trigger platform.
- Keep the implementation minimal and reversible: one binary/CLI, one DB, no queueing system, no microservices.

## Proposed repository layout

Create this initial structure:

- `src/hermes_pulse/__init__.py`
- `src/hermes_pulse/config.py`
- `src/hermes_pulse/models.py`
- `src/hermes_pulse/db.py`
- `src/hermes_pulse/trigger_registry.py`
- `src/hermes_pulse/source_registry.py`
- `src/hermes_pulse/connectors/base.py`
- `src/hermes_pulse/connectors/feed_registry.py`
- `src/hermes_pulse/connectors/hermes_history.py`
- `src/hermes_pulse/connectors/notes.py`
- `src/hermes_pulse/collection.py`
- `src/hermes_pulse/synthesis.py`
- `src/hermes_pulse/rendering.py`
- `src/hermes_pulse/delivery/base.py`
- `src/hermes_pulse/delivery/local_markdown.py`
- `src/hermes_pulse/cli.py`
- `tests/test_trigger_registry.py`
- `tests/test_source_registry.py`
- `tests/test_feed_connector.py`
- `tests/test_synthesis.py`
- `tests/test_rendering.py`
- `tests/test_cli_morning_digest.py`
- `fixtures/source_registry/sample_sources.yaml`
- `fixtures/feed_samples/*.xml`
- `fixtures/hermes_history/sample_session.json`
- `fixtures/notes/sample_notes.md`

## Implementation phases

### Task 1: Establish Python project skeleton

**Objective:** Add the minimal executable package layout and test harness.

**Files:**
- Create: `pyproject.toml`
- Create: `src/hermes_pulse/__init__.py`
- Create: `src/hermes_pulse/cli.py`
- Create: `tests/test_cli_morning_digest.py`

**Step 1: Write failing test**

Create `tests/test_cli_morning_digest.py` with a smoke test that imports `hermes_pulse.cli` and expects a `main()` entrypoint.

**Step 2: Run test to verify failure**

Run: `pytest tests/test_cli_morning_digest.py -v`
Expected: FAIL — module or entrypoint missing.

**Step 3: Write minimal implementation**

Add a package skeleton and a no-op `main()` that exits successfully.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_cli_morning_digest.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml src/hermes_pulse/__init__.py src/hermes_pulse/cli.py tests/test_cli_morning_digest.py
git commit -m "feat: initialize Hermes Pulse runtime skeleton"
```

### Task 2: Add canonical runtime models

**Objective:** Encode the core objects already documented in architecture docs.

**Files:**
- Create: `src/hermes_pulse/models.py`
- Create: `tests/test_models.py`

**Step 1: Write failing test**

Add tests for:
- `TriggerEvent`
- `TriggerProfile`
- `SourceRegistryEntry`
- `CollectedItem`
- `Candidate`

Verify required fields like `authority_tier`, `acquisition_mode`, and `citation_chain` exist.

**Step 2: Run test to verify failure**

Run: `pytest tests/test_models.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Use `dataclasses` or `pydantic` to define the canonical objects exactly once.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/models.py tests/test_models.py
git commit -m "feat: add canonical Hermes Pulse models"
```

### Task 3: Add trigger registry with `digest.morning`

**Objective:** Make scheduled trigger selection explicit and testable.

**Files:**
- Create: `src/hermes_pulse/trigger_registry.py`
- Create: `tests/test_trigger_registry.py`

**Step 1: Write failing test**

Test that `digest.morning.default` resolves to:
- family: `scheduled`
- event type: `digest.morning`
- output mode: `digest`
- collection preset: `broad_day_start`

**Step 2: Run test to verify failure**

Run: `pytest tests/test_trigger_registry.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement an in-code registry dictionary first. Avoid overengineering file-based registries yet.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_trigger_registry.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/trigger_registry.py tests/test_trigger_registry.py
git commit -m "feat: add scheduled trigger registry"
```

### Task 4: Add source registry loader

**Objective:** Establish the known-source / RSS substrate before generic search.

**Files:**
- Create: `src/hermes_pulse/source_registry.py`
- Create: `fixtures/source_registry/sample_sources.yaml`
- Create: `tests/test_source_registry.py`

**Step 1: Write failing test**

Test loading registry entries from YAML and validate:
- `authority_tier`
- `rss_url`
- `search_hints`
- `requires_primary_confirmation`

Include examples for:
- official blog
- trusted secondary domain blog
- discovery-only source

**Step 2: Run test to verify failure**

Run: `pytest tests/test_source_registry.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement a simple YAML-backed registry loader with validation.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_source_registry.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/source_registry.py fixtures/source_registry/sample_sources.yaml tests/test_source_registry.py
git commit -m "feat: add source registry foundation"
```

### Task 5: Add SQLite state layer

**Objective:** Persist trigger runs, deliveries, connector cursors, and source registry state.

**Files:**
- Create: `src/hermes_pulse/db.py`
- Create: `tests/test_db.py`

**Step 1: Write failing test**

Test that database initialization creates:
- `trigger_runs`
- `connector_cursors`
- `source_registry_state`
- `deliveries`

**Step 2: Run test to verify failure**

Run: `pytest tests/test_db.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement one initialization function with explicit SQL schema.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_db.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/db.py tests/test_db.py
git commit -m "feat: add sqlite state schema"
```

### Task 6: Add feed registry connector

**Objective:** Collect current external deltas from curated feeds.

**Files:**
- Create: `src/hermes_pulse/connectors/base.py`
- Create: `src/hermes_pulse/connectors/feed_registry.py`
- Create: `fixtures/feed_samples/official_feed.xml`
- Create: `tests/test_feed_connector.py`

**Step 1: Write failing test**

Test that the feed connector:
- reads registry entries with feed URLs
- parses RSS/Atom fixture items
- maps them to `CollectedItem`
- preserves authority tier and provenance

**Step 2: Run test to verify failure**

Run: `pytest tests/test_feed_connector.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement fixture-driven parsing first. Avoid real network calls in tests.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_feed_connector.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/connectors/base.py src/hermes_pulse/connectors/feed_registry.py fixtures/feed_samples/official_feed.xml tests/test_feed_connector.py
git commit -m "feat: add feed registry connector"
```

### Task 7: Add minimal local connectors for Hermes history and notes

**Objective:** Give the morning digest something personal to combine with feeds.

**Files:**
- Create: `src/hermes_pulse/connectors/hermes_history.py`
- Create: `src/hermes_pulse/connectors/notes.py`
- Create: `fixtures/hermes_history/sample_session.json`
- Create: `fixtures/notes/sample_notes.md`
- Create: `tests/test_local_connectors.py`

**Step 1: Write failing test**

Test that local connectors produce normalized `CollectedItem`s with provenance.

**Step 2: Run test to verify failure**

Run: `pytest tests/test_local_connectors.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement fixture-based local parsing only. Do not overgeneralize connector discovery yet.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_local_connectors.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/connectors/hermes_history.py src/hermes_pulse/connectors/notes.py fixtures/hermes_history/sample_session.json fixtures/notes/sample_notes.md tests/test_local_connectors.py
git commit -m "feat: add local context connectors"
```

### Task 8: Add collection orchestrator

**Objective:** Select the right connectors and source registries for `broad_day_start`.

**Files:**
- Create: `src/hermes_pulse/collection.py`
- Create: `tests/test_collection.py`

**Step 1: Write failing test**

Test that the `broad_day_start` preset invokes:
- feed registry connector
- Hermes history connector
- notes connector

and does **not** invoke unrelated connectors.

**Step 2: Run test to verify failure**

Run: `pytest tests/test_collection.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement one preset table and a collection orchestrator.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_collection.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/collection.py tests/test_collection.py
git commit -m "feat: add collection orchestration for scheduled digests"
```

### Task 9: Add synthesis layer for morning digest candidates

**Objective:** Turn collected items into ranked candidate sections.

**Files:**
- Create: `src/hermes_pulse/synthesis.py`
- Create: `tests/test_synthesis.py`

**Step 1: Write failing test**

Test a minimal scoring policy that prefers:
- explicit future relevance
- open loops
- primary authority feed items over lower-tier items
- saved / explicit-intent signals

**Step 2: Run test to verify failure**

Run: `pytest tests/test_synthesis.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement a simple deterministic scorer and section bundler.
Avoid LLM dependence in the first pass.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_synthesis.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/synthesis.py tests/test_synthesis.py
git commit -m "feat: add deterministic candidate synthesis"
```

### Task 10: Add markdown renderer for morning digest

**Objective:** Render a useful digest from ranked candidates.

**Files:**
- Create: `src/hermes_pulse/rendering.py`
- Create: `tests/test_rendering.py`

**Step 1: Write failing test**

Test that a rendered morning digest includes sections:
- today
- incoming
- followup
- resurface
- optional feed updates

and preserves citations/URLs for source-rigorous items.

**Step 2: Run test to verify failure**

Run: `pytest tests/test_rendering.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Implement markdown rendering only.
Do not build channel-specific formatting yet.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_rendering.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/rendering.py tests/test_rendering.py
git commit -m "feat: add morning digest markdown renderer"
```

### Task 11: Add local-file delivery adapter

**Objective:** Produce a real output artifact from the CLI without depending on messaging APIs.

**Files:**
- Create: `src/hermes_pulse/delivery/base.py`
- Create: `src/hermes_pulse/delivery/local_markdown.py`
- Modify: `src/hermes_pulse/cli.py`
- Create: `tests/test_delivery_local_markdown.py`

**Step 1: Write failing test**

Test that the CLI can write a morning digest markdown file to an output path.

**Step 2: Run test to verify failure**

Run: `pytest tests/test_delivery_local_markdown.py tests/test_cli_morning_digest.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Add a local markdown delivery adapter and wire the CLI to it.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_delivery_local_markdown.py tests/test_cli_morning_digest.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/hermes_pulse/delivery/base.py src/hermes_pulse/delivery/local_markdown.py src/hermes_pulse/cli.py tests/test_delivery_local_markdown.py tests/test_cli_morning_digest.py
git commit -m "feat: add local markdown delivery path"
```

### Task 12: Add end-to-end scheduled morning digest test

**Objective:** Prove the minimum product actually works end to end.

**Files:**
- Create: `tests/test_end_to_end_morning_digest.py`
- Reuse existing implementation files

**Step 1: Write failing test**

Run the CLI against fixture data and assert:
- trigger registry resolves `digest.morning`
- source registry loads
- feeds and local context collect
- synthesis produces ranked candidates
- markdown file is written
- output includes source links for authoritative items

**Step 2: Run test to verify failure**

Run: `pytest tests/test_end_to_end_morning_digest.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Patch integration gaps only. Avoid redesign.

**Step 4: Run test to verify pass**

Run: `pytest tests/test_end_to_end_morning_digest.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_end_to_end_morning_digest.py src/hermes_pulse tests
 git commit -m "test: add end-to-end morning digest verification"
```

## Validation commands

Run the full minimum suite:

```bash
pytest tests/test_models.py \
  tests/test_trigger_registry.py \
  tests/test_source_registry.py \
  tests/test_feed_connector.py \
  tests/test_local_connectors.py \
  tests/test_collection.py \
  tests/test_synthesis.py \
  tests/test_rendering.py \
  tests/test_delivery_local_markdown.py \
  tests/test_end_to_end_morning_digest.py -v
```

Manual verification command target:

```bash
python -m hermes_pulse.cli morning-digest \
  --source-registry fixtures/source_registry/sample_sources.yaml \
  --output /tmp/hermes-pulse-morning.md
```

Expected result:
- a markdown morning digest file is produced
- the digest contains both personal context and authoritative feed deltas
- authoritative feed items include links/citations
- no network dependency is required for the fixture-backed test path

## Risks / tradeoffs

- Starting with Python is the simplest path, but if the future runtime is expected to embed deeply into Hermes internals, some later refactoring may be needed.
- Feed polling is easy to start but can lead to noisy collection if source registry curation is weak.
- Too much scoring sophistication early will slow delivery; keep ranking deterministic first.
- Real Hermes history ingestion may later require adapter changes; use fixture-backed parsing first.

## Open questions

- Should v1 include Gmail immediately, or keep it for Phase 2 after proving digest quality with feeds + Hermes + notes?
- Should the source registry live in YAML permanently, or later move to SQLite-backed editable storage?
- Should local markdown remain the only v1 delivery path, or should Hermes cron/local delivery be wired immediately after the first green E2E?
- Should `deep_brief` remain documented-only until Phase 2, or should a stub output contract exist from day one?
