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
- [x] Test missing-provider paths, mixed currencies, statement aliases, recent-report detection, and a report dry run. Twenty-two combined tests passed; live AMD and TSM statements loaded, and TSM charts rendered.
- [x] Review and publish the migration in draft PR #10, separate from the theme update in PR #9.

Final review: The free replacement removes every runtime Sharadar and Nasdaq key reference. Finnhub keeps paired actual and estimate figures; Yahoo statements use their native currency, and Yahoo earnings dates fill recent Finnhub misses. A two-minute Yahoo lookup budget and a three-error stop keep a provider outage from delaying the email indefinitely. The owner waived the Claude review gate for these PRs. Local tests, compilation, and diff checks passed; a live scheduled email has not run yet.

# Group the Current 42-Stock Email List

- [x] Review all new symbols against the existing themes and choose honest groups of at least three where possible. Seven active themes; only Life Sciences has two.
- [x] Update the category map and its current-list test.
- [x] Verify the focused and full test suites and review the diff. Three tests pass; the rendered table has all 42 tickers in theme order and no `Other` group.
- [x] Publish the code change so future reports use the new grouping; PR #9 merged into `main` as `4990fb4`.

# Split the Broad Hardware Email Theme

- [x] Check the current 42-stock theme map and company descriptions for the less obvious names.
- [x] Split the 19-stock group into four smaller groups and move DOCN to platform technology; keep each new active group at four or more stocks.
- [x] Run the full test suite and inspect the rendered email table. All 23 tests pass, and the table renders 42 stock rows with the four new headings in order.
- [ ] Publish the theme update and record the final result.
