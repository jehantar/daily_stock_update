import sys
import types
import unittest
from datetime import datetime


sys.modules.setdefault("finnhub", types.SimpleNamespace(Client=object))

from src.earnings_enrichment import attach_fundamental_context
from src.earnings_tracker import EarningsEvent
from src.fundamentals_fetcher import FundamentalData


def _event(date: str = "2026-08-15") -> EarningsEvent:
    return EarningsEvent(
        symbol="TSM",
        company_name="TSM",
        date=datetime.fromisoformat(date),
        time="amc",
        eps_estimate=2.0,
        revenue_estimate=20e9,
        is_upcoming=False,
        actual_eps=2.1,
        actual_revenue=21e9,
    )


def _data() -> FundamentalData:
    quarters = [datetime.fromisoformat(date) for date in (
        "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31",
        "2026-03-31", "2026-06-30",
    )]
    values = [100.0, 120.0, 130.0, 140.0, 150.0, 180.0]
    return FundamentalData(
        ticker="TSM", company_name="TSM", quarters=quarters,
        revenue_growth=[None] * 6, eps_growth=[None] * 6,
        fcf_growth=[None] * 6, ebitda_growth=[None] * 6,
        roe=[None] * 6, roa=[None] * 6,
        gross_margin=[0.5] * 5 + [0.55],
        net_margin=[0.2] * 5 + [0.22],
        operating_margin=[0.3] * 5 + [0.32],
        revenue=values, eps=[1, 1.1, 1.2, 1.3, 1.4, 1.8],
        fcf_values=[20, 21, 22, 23, 24, 30],
        capex_values=[10, 11, 12, 13, 14, 16],
        financial_currency="TWD",
    )


class EarningsEnrichmentTests(unittest.TestCase):
    def test_attaches_matching_native_currency_statement_without_replacing_finnhub_pair(self):
        event = _event()

        self.assertTrue(attach_fundamental_context(event, _data()))

        context = event.fundamental_context
        self.assertEqual(context.financial_currency, "TWD")
        self.assertEqual(context.revenue, 180)
        self.assertAlmostEqual(context.revenue_qoq_change, 20)
        self.assertAlmostEqual(context.revenue_yoy_change, 50)
        self.assertAlmostEqual(context.fcf_yoy_change, (30 - 21) / 21 * 100)
        self.assertAlmostEqual(context.gross_margin_prior, 0.5)
        self.assertAlmostEqual(context.gross_margin_yoy, 0.5)
        self.assertEqual(event.actual_eps, 2.1)
        self.assertEqual(event.eps_estimate, 2.0)
        self.assertEqual(event.actual_revenue, 21e9)
        self.assertEqual(event.revenue_estimate, 20e9)

    def test_stale_statement_is_not_used_for_new_report(self):
        event = _event("2026-11-15")

        self.assertFalse(attach_fundamental_context(event, _data()))
        self.assertIsNone(event.fundamental_context)

    def test_missing_quarter_does_not_claim_qoq_change(self):
        data = _data()
        data.quarters.pop(-2)
        for field in ("revenue", "eps", "fcf_values", "capex_values", "gross_margin", "net_margin", "operating_margin"):
            getattr(data, field).pop(-2)
        event = _event()

        self.assertTrue(attach_fundamental_context(event, data))
        self.assertIsNone(event.fundamental_context.revenue_qoq_change)


if __name__ == "__main__":
    unittest.main()
