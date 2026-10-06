# Sentiment Tracker Memory

- `src/email_sender.py::_get_custom_category()` is the source of truth for valuation-table themes; `CATEGORY_ORDER` controls section order.
- `tests/test_email_sender.py` checks themes for the current 42-symbol Gist list and the exact category order.
- `LINC` and `WLY` deliberately fall back to `Other`; `TIGO` maps to `Energy`; `AGX` and `FIX` map to `Utilities & Infrastructure`.
- Pull request #8 merged the complete mapping into `main` on 2026-07-21 as commit `3488b73`.
- Base new work on current `origin/main`. The old `sharadar-first-earnings-detection` snapshot has unrelated root history and cannot open a PR against `main`.
- `.github/workflows/daily_report.yml` runs only through `repository_dispatch` or `workflow_dispatch`; a push to `main` does not send an email.
- PR #9 merged the current 42-stock email theme mapping into `main` as `4990fb4`.
- The paid Sharadar SF1 feed used to supply quarterly charts, earnings context, actual EPS/revenue overrides, and recent-filing detection. The free replacement uses Yahoo Finance quarterly statements for charts and trend context, keeps Finnhub's own actual/estimate pairs, and uses Yahoo earnings dates only when Finnhub misses a recent report.
- Direct SEC ticker-map and submissions requests returned HTTP 403 in this environment, so SEC is not in the migration's required runtime path. Yahoo date and statement coverage can vary; the report continues when either is missing.
- The migration's local verification uses `.venv/bin/python -m unittest discover -s tests -v`. Live Yahoo samples for AMD and TSM returned statements in USD and TWD, and TSM's growth and profitability charts rendered.
- PR #10 contains the free-source migration. The Yahoo earnings-date fallback has a 120-second run budget and stops after three consecutive errors; missing Finnhub keys degrade to Yahoo dates. The owner explicitly waived the Claude review gate for PRs #9 and #10 after the local CLI token expired.
- On 2026-10-05, the existing secret `tickers.csv` Gist was replaced with the user's 42-symbol list from a screenshot. The report reads this Gist at run time. The saved rows matched the screenshot exactly, and `parse_ticker_list()` accepted all 42 in order.
- The current 42 symbols use seven existing valuation themes. All active themes have at least three stocks except `Resources, Materials & Life Sciences`, which has two; no current symbol falls under `Other`. Keep the two-stock exception rather than grouping an unrelated business with life sciences.
