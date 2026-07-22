# Gist Ticker Email Theme Mapping

## Goal

Group the 43 tickers in the user's current gist under the email valuation table's existing themes. Keep the table stable and avoid adding a new theme.

## Current Behavior

`src/email_sender.py` assigns each ticker through `_get_custom_category()`. Tickers missing from its static map appear under `Other`. Of the 43 requested tickers, 28 already have the intended theme and 15 need a decision.

## Design

Extend the existing static map with these assignments:

- `BB` -> `Enterprise, Security & GovTech Software`
- `COHU`, `KLIC`, `MXL`, `DOCN`, `STX`, `TER`, `VICR` -> `Semiconductors, Hardware & Digital Infrastructure`
- `PGC` -> `Financials & Assets`
- `TWST` -> `Resources, Materials & Life Sciences`
- `AGX`, `FIX`, `TIGO` -> `Energy, Utilities & Infrastructure`

Leave `LINC` and `WLY` unmapped so they remain under `Other`. Their core education and publishing businesses do not fit the current themes well enough to justify a forced match.

Do not change `CATEGORY_ORDER` or the email markup. The update affects only ticker assignment within the existing valuation table.

## Alternatives Considered

1. Infer themes from third-party sector or industry metadata. This adds data work and may change grouping when a provider changes its labels.
2. Store theme names in the gist. This gives direct control but changes the gist format and parser contract.
3. Add an education and publishing theme. This would fit `LINC` and `WLY`, but the user chose to keep them under `Other` and asked to use the existing themes.

The static map is the smallest and most predictable change.

## Testing

Add regression coverage in `tests/test_email_sender.py` that checks:

- Each of the 13 newly mapped tickers returns the approved theme.
- `LINC` and `WLY` still return `Other`.
- The existing category order remains unchanged.

Run the focused email tests, then the full unit test suite.

## Success Criteria

- All 43 gist tickers render under the approved themes.
- Only `LINC` and `WLY` appear under `Other` from this list.
- Existing email sections and their order do not change.
- Focused and full unit tests pass.
