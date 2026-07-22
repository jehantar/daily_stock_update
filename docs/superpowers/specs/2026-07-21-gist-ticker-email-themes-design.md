# Gist Ticker Email Theme Mapping

## Goal

Group the 43 tickers in the current gist under the valuation table themes already present on `main`.

## Design

Keep `_get_custom_category()` as the single source of truth and extend its static map. Preserve `CATEGORY_ORDER`, parsing, and email markup.

- Platform Technology & Digital Ecosystems: `AMZN`, `GOOG`, `META`, `MSFT`, `NFLX`
- Semiconductors, Hardware & Digital Infrastructure: `AAOI`, `AMD`, `ARM`, `ASML`, `AVGO`, `AXTI`, `CIEN`, `COHU`, `DOCN`, `INTC`, `KLIC`, `LRCX`, `MRVL`, `MU`, `MXL`, `NVDA`, `SNDK`, `STX`, `TER`, `TSM`, `TSEM`, `VICR`, `WDC`
- Enterprise, Security & GovTech Software: `APP`, `AXON`, `BB`, `CRWD`, `NET`
- Commerce, Marketplaces & Consumer Logistics: `UBER`, `WMT`
- Financials & Assets: `PGC`
- Resources, Materials & Life Sciences: `LLY`, `TWST`
- Energy: `TIGO`
- Utilities & Infrastructure: `AGX`, `FIX`
- Other: `LINC`, `WLY`

## Testing

Add a table-driven unit test for all 43 tickers and an assertion that `CATEGORY_ORDER` retains the current `main` order.

## Success Criteria

- Every requested ticker returns the theme listed above.
- `LINC` and `WLY` remain under `Other`.
- Theme names, order, parsing, and email markup remain unchanged.
- The focused test and full test discovery pass.
