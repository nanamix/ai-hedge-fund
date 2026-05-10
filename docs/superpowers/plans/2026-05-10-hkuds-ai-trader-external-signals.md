# HKUDS AI-Trader External Signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only external signal adapter so HKUDS/AI-Trader opinions appear in Telegram flow alerts as `외부 의견` without changing local buy/hold decisions.

**Architecture:** Add a focused `external_signals` module for models, JSON loading, safe action mapping, and stale filtering. Extend `FlowSnapshot` and the formatter to carry external opinions. The CLI only reads a local JSON file and never starts AI-Trader, touches broker credentials, or writes order files.

**Tech Stack:** Python dataclasses, JSON file loading, `datetime`, pytest, existing notification package.

---

## File Structure

- Create `src/notifications/external_signals.py`: parse external JSON, normalize raw AI-Trader actions into safe local actions, and filter stale signals.
- Modify `src/notifications/models.py`: add `ExternalSignal` and `external_signals` to `FlowSnapshot`.
- Modify `src/notifications/config.py`: add `external_signals_path` and `load_external_signals` wrapper.
- Modify `src/notifications/telegram_flow_check.py`: load external signals and attach them to static/live snapshots.
- Modify `src/notifications/formatter.py`: add `외부 의견` to payload and text output.
- Create `tests/notifications/test_external_signals.py`: loader, mapping, and stale filtering tests.
- Modify `tests/notifications/test_formatter.py`: verify external opinions render.
- Modify `tests/notifications/test_cli.py`: verify CLI includes external signals during dry-run.

## Task 1: External Signal Models And Loader

**Files:**
- Create: `src/notifications/external_signals.py`
- Modify: `src/notifications/models.py`
- Test: `tests/notifications/test_external_signals.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:

- `buy` normalizes to `review`.
- `short` and `cover` normalize to `avoid`.
- stale signals older than the freshness window are ignored.
- missing file returns an empty list.

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/notifications/test_external_signals.py -q`

Expected: FAIL because `src.notifications.external_signals` and `ExternalSignal` do not exist.

- [ ] **Step 3: Implement minimal loader and mapper**

Create `ExternalSignal`, `normalize_external_signal`, and `load_external_signals`.

Safe action mapping:

- `buy`, `strong_buy`, `accumulate` -> `review`
- `sell`, `reduce` -> `review`
- `hold` -> `hold`
- `watch`, `review` -> same
- `short`, `cover`, leveraged action text -> `avoid`
- unknown -> `watch`

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/notifications/test_external_signals.py -q`

Expected: PASS.

## Task 2: Formatter And Snapshot Integration

**Files:**
- Modify: `src/notifications/models.py`
- Modify: `src/notifications/formatter.py`
- Test: `tests/notifications/test_formatter.py`

- [ ] **Step 1: Write the failing formatter test**

Add a test with one `ExternalSignal` and assert the message contains:

- `외부 의견`
- `HKUDS/AI-Trader`
- the symbol
- safe action `review`
- the rationale

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/notifications/test_formatter.py::test_format_flow_message_includes_external_opinions -q`

Expected: FAIL because formatter does not render external opinions.

- [ ] **Step 3: Implement formatter support**

Add `external_opinions` lines to `build_flow_payload` and render them after `입금/현금 이벤트` and before `리스크 신호`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/notifications/test_formatter.py::test_format_flow_message_includes_external_opinions -q`

Expected: PASS.

## Task 3: CLI File Wiring

**Files:**
- Modify: `src/notifications/config.py`
- Modify: `src/notifications/telegram_flow_check.py`
- Modify: `tests/notifications/test_cli.py`

- [ ] **Step 1: Write failing CLI test**

Add a dry-run test that sets `AI_HEDGE_FLOW_EXTERNAL_SIGNALS_PATH` to a temp JSON file and asserts `외부 의견` appears in stdout.

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/notifications/test_cli.py::test_cli_dry_run_includes_external_signals -q`

Expected: FAIL because config/CLI does not load external signals.

- [ ] **Step 3: Wire config and snapshot**

Add `external_signals_path` to `FlowConfig`, read it from `AI_HEDGE_FLOW_EXTERNAL_SIGNALS_PATH`, load signals in CLI, and attach them to both static and live snapshots.

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/notifications/test_cli.py::test_cli_dry_run_includes_external_signals -q`

Expected: PASS.

## Task 4: Verification And Docs

**Files:**
- Modify: `/Users/hajinyoung/Dev/medi-jyha-note/8000_Dev/8100_Super-Power/8110_AI-Headge/10_텔레그램-흐름체크-진행상황.md`

- [ ] **Step 1: Run notification tests**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/notifications -q`

Expected: PASS.

- [ ] **Step 2: Run cache regression tests**

Run: `/Users/hajinyoung/Dev/ai-hedge-fund/.venv/bin/python -m pytest tests/test_cache.py -q`

Expected: PASS.

- [ ] **Step 3: Run dry-run with sample external signal**

Create or use a local `.cache/telegram-flow-alerts/external-signals.json` sample and run:

`scripts/run-telegram-flow-alerts.sh --dry-run --slot 09:00`

Expected: message includes `외부 의견` and does not change the local decision into a buy recommendation.

- [ ] **Step 4: Update Obsidian progress**

Append implementation and verification results to the Super-Power progress note.

- [ ] **Step 5: Commit**

Commit the implementation with:

`git commit -m "feat: include external trading opinions in alerts"`
