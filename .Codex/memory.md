# Sentiment Tracker Memory

- `src/email_sender.py::_get_custom_category()` is the source of truth for valuation-table themes; `CATEGORY_ORDER` controls section order.
- The current gist coverage has a table-driven regression test in `tests/test_email_sender.py` for all 43 tracked tickers and the exact category order.
- `LINC` and `WLY` deliberately fall back to `Other`; `TIGO` maps to `Energy`; `AGX` and `FIX` map to `Utilities & Infrastructure`.
- Pull request #8 merged the complete mapping into `main` on 2026-07-21 as commit `3488b73`.
- Base new work on current `origin/main`. The old `sharadar-first-earnings-detection` snapshot has unrelated root history and cannot open a PR against `main`.
- `.github/workflows/daily_report.yml` runs only through `repository_dispatch` or `workflow_dispatch`; a push to `main` does not send an email.
