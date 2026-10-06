# Match Gist Tickers to Email Themes

- [x] Inspect current `main` themes and branch history.
- [x] Re-plan the mapping against the current `main` categories.
- [x] Add a failing regression test for all 43 requested tickers.
- [x] Verify the focused test fails only on missing or miscategorized mappings. `python3 -m unittest tests.test_email_sender` failed with 23 expected missing mappings; the category-order assertion passed.
- [x] Update the static category map.
- [x] Run focused and full test discovery. Both `python3 -m unittest tests.test_email_sender` and `python3 -m unittest discover -s tests` passed: 2 tests, `OK`.
- [x] Review the diff and record results. `git diff --check` passed; the review found only the intended category map, regression test, and task tracking changes.
- [x] Commit the clean integration change: `893e10c Group tracked tickers by email theme`.
- [x] Open, review, and merge pull request #8 into `main` as `3488b73`.

# Replace Sharadar After Subscription Cancellation

- [x] Keep Finnhub earnings dates working without a Nasdaq key; check Yahoo earnings dates for missed recent reports.
- [x] Fill quarterly charts and earnings context from free Yahoo statements, with explicit statement currency.
- [x] Reuse each downloaded statement bundle for the chart and earnings write-up; avoid unsupported cross-source beat/miss comparisons.
- [x] Remove the Nasdaq package and secret from the run, then update setup docs.
- [x] Test missing-provider paths, mixed currencies, statement aliases, recent-report detection, and a report dry run. Seventeen tests passed; live AMD and TSM statements loaded, and TSM charts rendered.
- [ ] Review and publish the migration in a separate pull request from the theme update.
