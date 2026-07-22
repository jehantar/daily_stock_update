# Sentiment Tracker Memory

- Daily report workflow: `.github/workflows/daily_report.yml` can be manually triggered with `gh workflow run "Daily Stock Report" --repo jehantar/daily_stock_update`.
- Manual test on 2026-06-26: run `28210791626` succeeded and sent email subject `[ACTION] SNDK +21.5% | Jun 26, 2026`; it loaded 39 gist symbols and exposed invalid parsed symbol `THAT'S`.
- Ticker parsing now uses `csv.reader` for CSV input and shared strict validation (`^[A-Z0-9]{1,5}$`, excluding `CORE`, `IRA`, `TICKER`) for both CSV and simple-list input.
- Parser regression tests live in `tests/test_data_fetcher.py`.
- Email valuation categories are static in `src/email_sender.py`; mappings include hardware/semis names, `BB` under Enterprise, `PGC` under Financials, `TWST` under Resources, and `AGX/FIX/TIGO` under Energy. `LINC` and `WLY` deliberately fall back to `Other`. Category regression tests live in `tests/test_email_sender.py`.
