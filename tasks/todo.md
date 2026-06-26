# Rebucket Email Valuation Categories

- [x] Review current email category mapping and latest ticker list from the test run.
- [x] Confirm category design for tickers currently landing in `Other`.
- [x] Add regression tests for category assignment.
- [x] Update category mapping in `src/email_sender.py`.
- [x] Verify tests and document results.

## Proposed Bucket Design

Recommended approach: keep the existing static category labels and expand the ticker map. This is simple, predictable, and matches how the email is already rendered.

Alternative 1: infer categories from Yahoo `sector`/`industry`. This would require more data plumbing and could produce unstable category names.

Alternative 2: put category labels in the gist. This gives manual control but makes the gist schema more important and risks breaking parsing.

Proposed mappings from the latest run:

- `AEIS`, `AMD`, `AAOI`, `ARM`, `ASML`, `AXTI`, `CIEN`, `COHR`, `INTC`, `LRCX`, `LITE`, `MRVL`, `SNDK`, `TSEM`, `VRT` -> `Semiconductors, Hardware & Digital Infrastructure`
- `CNQ`, `KGC`, `NEM` -> `Resources, Materials & Life Sciences`
- `LLY`, `GSK` -> `Resources, Materials & Life Sciences`
- `EIX` -> `Energy, Utilities & Infrastructure`

Decision: add `Energy, Utilities & Infrastructure` so utility holdings do not get forced into Resources.

## Results

- Added `tests/test_email_sender.py` coverage for the newly bucketed tickers and the dedicated utility section.
- Updated `src/email_sender.py` with the expanded semiconductor/hardware, resources/life sciences, and energy/utilities mappings.
- Verified with:
  - `python3 -m unittest tests.test_email_sender`
  - `python3 -m unittest tests.test_data_fetcher`
  - `python3 -m unittest discover -s tests`
  - `python3 -m compileall src tests`
