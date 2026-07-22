# Match Gist Tickers to Email Themes

- [x] Inspect current `main` themes and branch history.
- [x] Re-plan the mapping against the current `main` categories.
- [x] Add a failing regression test for all 43 requested tickers.
- [x] Verify the focused test fails only on missing or miscategorized mappings. `python3 -m unittest tests.test_email_sender` failed with 23 expected missing mappings; the category-order assertion passed.
- [x] Update the static category map.
- [x] Run focused and full test discovery. Both `python3 -m unittest tests.test_email_sender` and `python3 -m unittest discover -s tests` passed: 2 tests, `OK`.
- [x] Review the diff and record results. `git diff --check` passed; the review found only the intended category map, regression test, and task tracking changes.
- [x] Commit the clean integration change: `893e10c Group tracked tickers by email theme`.
- [ ] Open, review, and merge the pull request into `main`.
