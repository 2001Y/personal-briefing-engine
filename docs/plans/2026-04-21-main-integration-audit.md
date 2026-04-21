# Hermes Pulse Main Integration Audit Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Hermes Pulse の開発状態を `main` 一本に整理し、残タスクを明示した上で、安全に local branches / worktrees / stash を片付ける。

**Architecture:** 実装本体の正本は `main` とし、未統合のものが branch / worktree / stash に残っていないかを先に監査する。内容が既に `main` に等価反映済みなら branch は消し、未反映なら commit 単位で cherry-pick ではなく `main` 上で再構成する。

**Tech Stack:** git, pytest, Hermes Pulse Python runtime, session_search

---

## Current audited state

- repo: `~/.hermes/hermes-pulse`
- active development branch: `main`
- audited integration base before this docs commit: `5ea65be fix: stabilize launchd grok history refresh`
- full tests on the integration base: `185 passed`

## Cleanup result completed in this audit

- removed stale worktree `~/.hermes/hermes-pulse-walk-trigger`
- deleted stale branch `feat/location-walk-trigger`
- verified that its patch was already equivalently reflected in `main` via `git cherry main feat/location-walk-trigger => - a74ef90`
- dropped old stash entries after confirming their representative action-feedback / execution-detail changes are already present in current `main`
- result: no extra worktree, no stash, active line is now `main` only

## Session-derived unfinished work buckets

### A. History preservation / refresh
- Grok live export refresh automation is implemented in-repo, but still depends on a live browser/CDP endpoint being available at runtime
- ChatGPT では `prepare-chatgpt-history --input-file <OpenAI-export.zip> --output-dir <dir>` により、official export zip（nested zip 含む）を script-only で Pulse import 形式へ整形できるようになった
- ただし ChatGPT export request 自体の発行・取得はまだ manual
- history connectors now persist and respect item-level watermarks for already-seen filtering, but broader export freshness orchestration is still unfinished

### B. Action execution / feedback
- `state-summary` now surfaces connector cursors, recent approval actions, and aggregated feedback totals from the SQLite state DB
- higher-level analytics/reporting over `feedback_log` is still minimal beyond that CLI surface
- approval action execution details are persisted and rendered in `state-summary`, but downstream UI/report destinations are still not built

### C. History export / launchd operational verification
- live `xurl` OAuth2 verification succeeded via `/2/users/me`
- launchd wrapper/plist wiring for the morning digest exists and includes ChatGPT/Grok/X optional inputs
- current blocker observed live: Grok refresh fails when CDP port `9223` is not available, and `ai.hermes.pulse.morning-digest` currently shows `last exit code = 1`

### D. Repository hygiene
- push local `main` commit to origin
- remove stale `feat/location-walk-trigger` branch/worktree after verification
- inspect stash entries and either convert to issues/tasks or drop them if already reflected

---

## Task 1: Re-verify `main` and record baseline

**Objective:** Confirm the current audited branch is green and can be treated as the integration base.

**Files:**
- Read only: `git log`, `git status`, `git worktree list`

**Steps:**
1. Run `git -C ~/.hermes/hermes-pulse status --short --branch`
2. Run `git -C ~/.hermes/hermes-pulse worktree list --porcelain`
3. Run `cd ~/.hermes/hermes-pulse && pytest -q`
4. Confirm expected result: clean worktree, tests green

## Task 2: Retire stale location walk feature branch

**Objective:** Remove the redundant worktree/branch only after verifying its patch is already in `main`.

**Files:**
- Read only: git history

**Steps:**
1. Run `git -C ~/.hermes/hermes-pulse cherry main feat/location-walk-trigger`
2. Confirm result starts with `-`, meaning equivalent patch already exists in `main`
3. Remove worktree:
   - `git -C ~/.hermes/hermes-pulse worktree remove ~/.hermes/hermes-pulse-walk-trigger`
4. Delete branch:
   - `git -C ~/.hermes/hermes-pulse branch -D feat/location-walk-trigger`

## Task 3: Audit stash entries one by one

**Objective:** Decide whether stash contents are already merged, should be reintroduced, or should be discarded.

**Files:**
- Inspect: `src/hermes_pulse/cli.py`
- Inspect: `src/hermes_pulse/db.py`
- Inspect: `tests/test_state_runtime.py`

**Steps:**
1. Run `git -C ~/.hermes/hermes-pulse stash show --stat stash@{0}`
2. Run `git -C ~/.hermes/hermes-pulse stash show --stat stash@{1}`
3. Search current `main` for representative symbols from each stash
4. If stash changes are already present on `main`, drop stash
5. If not fully present, convert remaining delta into a fresh branch from current `main` rather than popping old stash blindly

## Task 4: Convert session leftovers into explicit tracked tasks

**Objective:** Make “unfinished per session” concrete and visible.

**Files:**
- Modify or create: `docs/plans/2026-04-21-main-integration-audit.md`
- Optional follow-up: GitHub issues or local TODO doc

**Steps:**
1. Record unresolved buckets A-D from this plan
2. Split them into independent future tasks
3. Mark which are product work vs cleanup work

## Task 5: Push integrated `main`

**Objective:** Make `main` the only authoritative line both locally and remotely.

**Steps:**
1. Run `git -C ~/.hermes/hermes-pulse push origin main`
2. Confirm `main` no longer shows `ahead 1`

## Task 6: Final verification

**Objective:** Confirm the repo is truly simplified to one mainline.

**Steps:**
1. Run `git -C ~/.hermes/hermes-pulse branch -vv`
2. Run `git -C ~/.hermes/hermes-pulse worktree list --porcelain`
3. Run `git -C ~/.hermes/hermes-pulse stash list`
4. Confirm desired end state:
   - only `main` remains as active development branch
   - no stale feature worktree
   - stash either empty or intentionally preserved with rationale
   - local and remote `main` aligned

---

## Success criteria

- `main` is green and pushed
- no stale feature worktree remains
- old stash entries are either dropped or explicitly promoted into tracked tasks
- unfinished work is listed as future tasks rather than hidden in git state
- future development can resume from `main` only
