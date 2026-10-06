"""Check that the report can use free fundamentals without sending mail."""

import os
import unittest
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import patch

from src import main as report
from src.earnings_tracker import EarningsEvent
from src.fundamentals_fetcher import FundamentalData


class ReportDryRunTests(unittest.TestCase):
    def test_recent_report_uses_one_statement_download_without_nasdaq_key(self) -> None:
        event = EarningsEvent(
            symbol="ACME",
            company_name="Acme",
            date=datetime(2026, 10, 4),
            time="amc",
            eps_estimate=None,
            revenue_estimate=None,
            is_upcoming=False,
        )
        data = FundamentalData(
            ticker="ACME",
            company_name="Acme",
            quarters=[datetime(2026, 6, 30), datetime(2026, 9, 30)],
            revenue_growth=[None, 0.1],
            eps_growth=[None, 0.2],
            fcf_growth=[None, 0.3],
            ebitda_growth=[None, 0.1],
            roe=[None, None],
            roa=[None, None],
            gross_margin=[0.4, 0.41],
            net_margin=[0.2, 0.21],
            operating_margin=[0.3, 0.31],
            revenue=[90_000_000, 100_000_000],
            eps=[0.8, 1.0],
            fcf_values=[10_000_000, 12_000_000],
            capex_values=[2_000_000, 3_000_000],
            financial_currency="USD",
        )
        replacements = {
            "is_market_holiday": False,
            "fetch_tickers_from_gist": ["ACME"],
            "fetch_price_data": [],
            "identify_movers": [],
            "get_earnings_calendar": {"ACME": event},
            "get_upcoming_earnings": [],
            "get_recent_earnings": [event],
            "fetch_fundamentals": {"ACME": data},
            "generate_all_charts": {},
            "aggregate_earnings_context": ([], []),
            "analyze_earnings_report": "Summary",
            "send_daily_report": True,
        }
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"REPORT_DATE": "2026-10-05"}, clear=True))
            mocks = {
                name: stack.enter_context(patch.object(report, name, return_value=value))
                for name, value in replacements.items()
            }
            self.assertEqual(report.main(), 0)

        mocks["fetch_fundamentals"].assert_called_once_with(["ACME"], {}, quarters=6)
        mocks["generate_all_charts"].assert_called_once_with({"ACME": data})
        self.assertEqual(event.fundamental_context.revenue, 100_000_000)
        self.assertEqual(event.fundamental_context.financial_currency, "USD")
        mocks["send_daily_report"].assert_called_once()


if __name__ == "__main__":
    unittest.main()
