# Gist Ticker Email Themes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assign the 13 newly categorized gist tickers to existing email themes while leaving `LINC` and `WLY` under `Other`.

**Architecture:** Keep `_get_custom_category()` as the single source of truth. Extend its static `CATEGORIES` map and add regression assertions to the existing email category test module. Do not change theme names, theme order, parsing, or email markup.

**Tech Stack:** Python 3, `unittest`, static ticker-to-theme mapping

## Global Constraints

- Use only the existing email themes.
- Keep `LINC` and `WLY` under `Other`.
- Do not change `CATEGORY_ORDER` or email markup.
- Follow test-driven development: verify the new test fails before changing production code.

---

### Task 1: Extend the Email Theme Map

**Files:**
- Modify: `tests/test_email_sender.py`
- Modify: `src/email_sender.py`
- Modify: `tasks/todo.md`

**Interfaces:**
- Consumes: `_get_custom_category(symbol: str) -> str` from `src.email_sender`
- Produces: approved category results for all 15 previously unmapped gist tickers

- [x] **Step 1: Add the mapping regression test**

Replace `test_latest_tickers_are_bucketed_into_existing_groups` with a table-driven assertion that retains the old cases and adds these exact entries:

```python
expected_categories = {
    "BB": "Enterprise, Security & GovTech Software",
    "COHU": "Semiconductors, Hardware & Digital Infrastructure",
    "KLIC": "Semiconductors, Hardware & Digital Infrastructure",
    "MXL": "Semiconductors, Hardware & Digital Infrastructure",
    "DOCN": "Semiconductors, Hardware & Digital Infrastructure",
    "STX": "Semiconductors, Hardware & Digital Infrastructure",
    "TER": "Semiconductors, Hardware & Digital Infrastructure",
    "VICR": "Semiconductors, Hardware & Digital Infrastructure",
    "PGC": "Financials & Assets",
    "TWST": "Resources, Materials & Life Sciences",
    "AGX": "Energy, Utilities & Infrastructure",
    "FIX": "Energy, Utilities & Infrastructure",
    "TIGO": "Energy, Utilities & Infrastructure",
    "LINC": "Other",
    "WLY": "Other",
}
for symbol, category in expected_categories.items():
    with self.subTest(symbol=symbol):
        self.assertEqual(_get_custom_category(symbol), category)
```

Keep the prior semiconductor and life-sciences expectations in the same table so this change does not cut existing coverage.

- [x] **Step 2: Run the focused test and verify the red state**

Run:

```bash
python3 -m unittest tests.test_email_sender
```

Expected: failure subtests for the 13 newly mapped tickers because they still return `Other`; `LINC` and `WLY` pass.

- [x] **Step 3: Add the approved static mappings**

Add these entries to the matching sections of `CATEGORIES` in `src/email_sender.py`:

```python
"BB": "Enterprise, Security & GovTech Software",
"COHU": "Semiconductors, Hardware & Digital Infrastructure",
"KLIC": "Semiconductors, Hardware & Digital Infrastructure",
"MXL": "Semiconductors, Hardware & Digital Infrastructure",
"DOCN": "Semiconductors, Hardware & Digital Infrastructure",
"STX": "Semiconductors, Hardware & Digital Infrastructure",
"TER": "Semiconductors, Hardware & Digital Infrastructure",
"VICR": "Semiconductors, Hardware & Digital Infrastructure",
"PGC": "Financials & Assets",
"TWST": "Resources, Materials & Life Sciences",
"AGX": "Energy, Utilities & Infrastructure",
"FIX": "Energy, Utilities & Infrastructure",
"TIGO": "Energy, Utilities & Infrastructure",
```

Do not add `LINC` or `WLY` to the map.

- [x] **Step 4: Verify the focused and full green state**

Run:

```bash
python3 -m unittest tests.test_email_sender
python3 -m unittest discover -s tests
```

Expected: both commands exit with status 0 and report `OK`.

- [x] **Step 5: Review scope and record results**

Run:

```bash
git diff --check
git diff -- src/email_sender.py tests/test_email_sender.py tasks/todo.md docs/superpowers/plans/2026-07-21-gist-ticker-email-themes.md
git status --short
```

Confirm that only the approved mapping, tests, plan, and task record changed. Mark the implementation checklist complete and add the exact test results to `tasks/todo.md`.

- [x] **Step 6: Commit the verified change**

Stage only the owned files and create a terse commit:

```bash
git add src/email_sender.py tests/test_email_sender.py tasks/todo.md docs/superpowers/plans/2026-07-21-gist-ticker-email-themes.md
git commit -m "Group tracked tickers by email theme"
```

Expected: the implementation, tests, plan, and task record are committed together.

After task and whole-branch reviews pass, the controller will run the full test suite again and push `sharadar-first-earnings-detection` to `origin`. This keeps unreviewed code off the remote branch.
