import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from src import fundamentals_fetcher

try:
    from src import chart_generator
except ImportError:
    chart_generator = None


def _statements(currency="USD", *, omit=()):
    dates = pd.to_datetime([
        "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31",
        "2025-03-31", "2025-06-30",
    ])[::-1]
    rows = {
        "Total Revenue": [160, 150, 140, 130, 120, 100],
        "Diluted EPS": [1.6, 1.5, 1.4, 1.3, 1.2, 1.0],
        "EBITDA": [32, 30, 28, 26, 24, 20],
        "Gross Profit": [80, 75, 70, 65, 60, 50],
        "Operating Income": [40, 38, 35, 33, 30, 25],
        "Net Income": [16, 15, 14, 13, 12, 10],
    }
    for row in omit:
        rows.pop(row, None)
    income = pd.DataFrame(rows, index=dates).T
    cashflow = pd.DataFrame({
        "Operating Cash Flow": [50, 48, 45, 42, 40, 35],
        "Capital Expenditure": [-10, -9, -8, -7, -6, -5],
    }, index=dates).T
    balance = pd.DataFrame({
        "Total Assets": [220, 210, 200, 190, 180, 170],
        "Stockholders Equity": [120, 115, 110, 105, 100, 95],
    }, index=dates).T
    return SimpleNamespace(
        quarterly_income_stmt=income,
        quarterly_cashflow=cashflow,
        quarterly_balance_sheet=balance,
        get_info=lambda: {"financialCurrency": currency, "currency": "USD"},
    )


class FundamentalsFetcherTests(unittest.TestCase):
    def test_fetches_and_aligns_quarterly_yahoo_statements(self):
        with patch.object(fundamentals_fetcher.yf, "Ticker", return_value=_statements()):
            data = fundamentals_fetcher.fetch_fundamentals(
                ["TEST"], {"TEST": "Test Co"}, quarters=6
            )["TEST"]

        self.assertEqual(data.company_name, "Test Co")
        self.assertEqual(data.quarters[0].strftime("%Y-%m-%d"), "2024-03-31")
        self.assertEqual(data.quarters[-1].strftime("%Y-%m-%d"), "2025-06-30")
        self.assertEqual(data.revenue, [100, 120, 130, 140, 150, 160])
        self.assertAlmostEqual(data.revenue_growth[1], 0.2)
        self.assertAlmostEqual(data.revenue_yoy[-1], (160 / 120) - 1)
        self.assertEqual(data.fcf_values, [30, 34, 35, 37, 39, 40])
        self.assertEqual(data.capex_values, [5, 6, 7, 8, 9, 10])
        self.assertAlmostEqual(data.fcf_yoy[-1], (40 / 34) - 1)
        self.assertAlmostEqual(data.capex_yoy[-1], (10 / 6) - 1)
        self.assertAlmostEqual(data.gross_margin[-1], 0.5)
        self.assertAlmostEqual(data.operating_margin[-1], 0.25)
        self.assertAlmostEqual(data.net_margin[-1], 0.1)
        # TTM net income is 58; balance denominators average current and year-ago values.
        self.assertAlmostEqual(data.roa[-1], 58 / ((220 + 180) / 2))
        self.assertAlmostEqual(data.roe[-1], 58 / ((120 + 100) / 2))

    def test_missing_rows_and_failed_statement_property_leave_other_data_usable(self):
        ticker = _statements(omit=("EBITDA", "Gross Profit", "Operating Income"))

        class PartiallyFailingTicker:
            quarterly_income_stmt = ticker.quarterly_income_stmt
            quarterly_balance_sheet = ticker.quarterly_balance_sheet

            @property
            def quarterly_cashflow(self):
                raise RuntimeError("cash flow statement unavailable")

            def get_info(self):
                return {"financialCurrency": "USD"}

        def ticker_factory(symbol):
            if symbol == "BROKEN":
                raise RuntimeError("provider unavailable")
            return PartiallyFailingTicker()

        with patch.object(fundamentals_fetcher.yf, "Ticker", side_effect=ticker_factory):
            results = fundamentals_fetcher.fetch_fundamentals(["PARTIAL", "BROKEN"], quarters=4)

        data = results["PARTIAL"]
        self.assertEqual(len(data.quarters), 4)
        self.assertEqual(data.ebitda_values, [None] * 4)
        self.assertEqual(data.fcf_values, [None] * 4)
        self.assertEqual(data.capex_values, [None] * 4)
        self.assertEqual(data.gross_margin, [None] * 4)
        self.assertEqual(data.operating_margin, [None] * 4)
        self.assertNotIn("BROKEN", results)

    def test_uses_statement_currency_and_ignores_quote_currency_fallback(self):
        with patch.object(fundamentals_fetcher.yf, "Ticker", return_value=_statements("TWD")):
            data = fundamentals_fetcher.fetch_fundamentals(["TSM"], quarters=2)["TSM"]

        self.assertEqual(data.financial_currency, "TWD")
        ticker = SimpleNamespace(get_info=lambda: {"currency": "USD"})
        self.assertIsNone(fundamentals_fetcher._currency(ticker))

    @unittest.skipIf(chart_generator is None, "matplotlib is not installed")
    def test_growth_chart_formats_absolute_values_in_financial_currency(self):
        with patch.object(fundamentals_fetcher.yf, "Ticker", return_value=_statements("TWD")):
            data = fundamentals_fetcher.fetch_fundamentals(["TSM"], quarters=2)["TSM"]
        with patch.object(chart_generator, "_fig_to_base64", side_effect=lambda fig: fig):
            fig = chart_generator._create_growth_chart(data)

        self.assertEqual(fig.axes[0].yaxis.get_major_formatter()(120_000_000), "TWD 120M")
        self.assertEqual(fig.axes[2].yaxis.get_major_formatter()(30_000_000), "TWD 30M")
        self.assertEqual(fig.axes[1].yaxis.get_major_formatter()(1.25), "TWD 1.25")
        import matplotlib.pyplot as plt
        plt.close(fig)


if __name__ == "__main__":
    unittest.main()
