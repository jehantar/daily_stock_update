# Sentiment Tracker Memory

- `src/email_sender.py::_get_custom_category()` is the source of truth for valuation-table themes; `CATEGORY_ORDER` controls section order.
- The current gist coverage has a table-driven regression test in `tests/test_email_sender.py` for all 43 tracked tickers and the exact category order.
- `LINC` and `WLY` deliberately fall back to `Other`; `TIGO` maps to `Energy`; `AGX` and `FIX` map to `Utilities & Infrastructure`.
- Pull request #8 merged the complete mapping into `main` on 2026-07-21 as commit `3488b73`.
- Base new work on current `origin/main`. The old `sharadar-first-earnings-detection` snapshot has unrelated root history and cannot open a PR against `main`.
- `.github/workflows/daily_report.yml` runs only through `repository_dispatch` or `workflow_dispatch`; a push to `main` does not send an email.
- The current requested Gist has 42 tickers. Its additional email theme mappings are in separate PR #9; this fundamentals migration starts from `main` and does not include that PR's theme edits.
- The paid Sharadar SF1 feed used to supply quarterly charts, earnings context, actual EPS/revenue overrides, and recent-filing detection. The free replacement uses Yahoo Finance quarterly statements for charts and trend context, keeps Finnhub's own actual/estimate pairs, and uses Yahoo earnings dates only when Finnhub misses a recent report.
- Direct SEC ticker-map and submissions requests returned HTTP 403 in this environment, so SEC is not in the migration's required runtime path. Yahoo date and statement coverage can vary; the report continues when either is missing.
- The migration's local verification uses `.venv/bin/python -m unittest discover -s tests -v`. Live Yahoo samples for AMD and TSM returned statements in USD and TWD, and TSM's growth and profitability charts rendered.
- Draft PR #10 contains the free-source migration. The Yahoo earnings-date fallback has a 120-second run budget and stops after three consecutive errors; missing Finnhub keys degrade to Yahoo dates. The owner explicitly waived the Claude review gate for PRs #9 and #10 after the local CLI token expired.
