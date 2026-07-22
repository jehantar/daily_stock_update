# Gist Ticker Email Themes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map all 43 requested gist tickers to the existing email themes on current `main`.

**Architecture:** Extend the static map in `_get_custom_category()` and add a focused table-driven regression test. Keep theme names, theme order, parsing, and email markup unchanged.

**Tech Stack:** Python 3, `unittest`

## Global Constraints

- Use only the themes already present on `main`.
- Keep `LINC` and `WLY` under `Other`.
- Map `TIGO` to `Energy` and `AGX`/`FIX` to `Utilities & Infrastructure`.
- Do not change `CATEGORY_ORDER`, parsing, or email markup.
- Verify the new test fails before changing production code.

---

### Task 1: Add Complete Gist Theme Coverage

**Files:**
- Create: `tests/test_email_sender.py`
- Modify: `src/email_sender.py`
- Create: `tasks/todo.md`

**Interfaces:**
- Consumes: `_get_custom_category(symbol: str) -> str` and `CATEGORY_ORDER` from `src.email_sender`
- Produces: the approved category for every requested ticker

- [x] **Step 1: Write the failing test**

Create `tests/test_email_sender.py` with optional dependency stubs, an `EXPECTED_CATEGORIES` dictionary containing every ticker and theme from the design spec, a subtest for each mapping, and an exact assertion for the current nine-item `CATEGORY_ORDER` ending in `Other`.

- [x] **Step 2: Verify the red state**

Run `python3 -m unittest tests.test_email_sender`. Expected: failures only for tickers missing or miscategorized in the current static map.

- [x] **Step 3: Add the mappings**

Add only the missing ticker entries to the matching sections of `CATEGORIES`. Keep `LINC` and `WLY` absent so they use the `Other` fallback. Do not edit `CATEGORY_ORDER`.

- [x] **Step 4: Verify the green state**

Run `python3 -m unittest tests.test_email_sender` and `python3 -m unittest discover -s tests`. Expected: both exit 0 and report `OK`.

- [x] **Step 5: Review and commit**

Run `git diff --check`, inspect the full diff, record red and green results in `tasks/todo.md`, stage only the owned source, test, spec, plan, and task files, then commit as `Group tracked tickers by email theme`. Do not stage `.claude/` and do not push.
