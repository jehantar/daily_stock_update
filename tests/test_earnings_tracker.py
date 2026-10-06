import os
import sys
import types
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

# Calendar clients are mocked, so vendor SDKs are not needed for these fixtures.
sys.modules.setdefault("finnhub", types.SimpleNamespace(Client=object))
sys.modules.setdefault("yfinance", types.SimpleNamespace(Ticker=object))

from src import earnings_tracker as tracker


class EarningsDates:
    def __init__(self, rows):
        self.rows = rows
        self.empty = not rows

    def iterrows(self):
        return iter(self.rows)


class EarningsTrackerTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 5)
        self.event = {
            "date": "2026-10-04",
            "symbol": "ACME",
            "hour": "amc",
            "epsEstimate": 1.2,
            "revenueEstimate": 100.0,
            "epsActual": 1.3,
            "revenueActual": 105.0,
        }
        self.env = {"REPORT_DATE": self.today.isoformat()}

    def run_calendar(self, finnhub_events, yahoo_rows=None, yahoo_error=None):
        client = Mock()
        client.earnings_calendar.return_value = {"earningsCalendar": finnhub_events}
        yahoo_ticker = Mock()
        if yahoo_error:
            yahoo_ticker.get_earnings_dates.side_effect = yahoo_error
        else:
            yahoo_ticker.get_earnings_dates.return_value = EarningsDates(yahoo_rows or [])
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(tracker, "get_finnhub_client", return_value=client), \
                patch.object(tracker.yf, "Ticker", return_value=yahoo_ticker) as ticker_factory:
            results = tracker.get_earnings_calendar(["ACME"])
        return results["ACME"], client, ticker_factory, yahoo_ticker

    def test_finnhub_miss_uses_recent_yahoo_report_date(self):
        yahoo_rows = [(datetime(2026, 10, 4, tzinfo=timezone.utc), {"Reported EPS": 2.4})]
        event, client, ticker_factory, yahoo_ticker = self.run_calendar([], yahoo_rows)

        self.assertFalse(event.is_upcoming)
        self.assertEqual(event.date.date(), date(2026, 10, 4))
        self.assertEqual(event.actual_eps, 2.4)
        self.assertIsNone(event.actual_revenue)
        self.assertIsNone(event.eps_estimate)
        self.assertIsNone(event.revenue_estimate)
        ticker_factory.assert_called_once_with("ACME")
        yahoo_ticker.get_earnings_dates.assert_called_once_with(limit=4)

    def test_future_yahoo_date_is_upcoming(self):
        yahoo_rows = [(datetime(2026, 10, 15, tzinfo=timezone.utc), {"Reported EPS": None})]
        event, *_ = self.run_calendar([], yahoo_rows)

        self.assertTrue(event.is_upcoming)
        self.assertEqual(event.date.date(), date(2026, 10, 15))
        self.assertIsNone(event.actual_eps)
        self.assertIsNone(event.actual_revenue)
        self.assertIsNone(event.eps_estimate)
        self.assertIsNone(event.revenue_estimate)

    def test_same_day_without_reported_eps_stays_upcoming(self):
        yahoo_rows = [
            (datetime(2026, 10, 5, 16, tzinfo=timezone(timedelta(hours=-4))), {"Reported EPS": float("nan")}),
            (datetime(2026, 10, 15, tzinfo=timezone.utc), {"Reported EPS": None}),
        ]
        event, *_ = self.run_calendar([], yahoo_rows)

        self.assertTrue(event.is_upcoming)
        self.assertEqual(event.date.date(), self.today)
        self.assertIsNone(event.actual_eps)

    def test_yahoo_exception_keeps_finnhub_event_and_values(self):
        future_finnhub_event = {
            **self.event,
            "date": "2026-10-10",
            "epsActual": None,
            "revenueActual": None,
        }
        event, client, ticker_factory, yahoo_ticker = self.run_calendar(
            [future_finnhub_event], yahoo_error=RuntimeError("Yahoo unavailable")
        )

        self.assertTrue(event.is_upcoming)
        self.assertEqual(event.date.date(), date(2026, 10, 10))
        self.assertEqual(event.eps_estimate, 1.2)
        self.assertEqual(event.revenue_estimate, 100.0)
        client.earnings_calendar.assert_called_once()
        ticker_factory.assert_called_once_with("ACME")
        yahoo_ticker.get_earnings_dates.assert_called_once_with(limit=4)

    def test_yahoo_future_date_does_not_erase_finnhub_estimates(self):
        future_finnhub_event = {
            **self.event,
            "date": "2026-10-06",
            "epsActual": None,
            "revenueActual": None,
        }
        yahoo_rows = [(datetime(2026, 10, 15, tzinfo=timezone.utc), {"Reported EPS": None})]
        event, *_ = self.run_calendar([future_finnhub_event], yahoo_rows)

        self.assertEqual(event.date.date(), date(2026, 10, 6))
        self.assertEqual(event.eps_estimate, 1.2)
        self.assertEqual(event.revenue_estimate, 100.0)

    def test_same_day_finnhub_revenue_actual_marks_reported(self):
        same_day_event = {
            **self.event,
            "date": "2026-10-05",
            "epsActual": None,
        }
        event, _, ticker_factory, _ = self.run_calendar([same_day_event])

        self.assertFalse(event.is_upcoming)
        self.assertEqual(event.actual_revenue, 105.0)
        ticker_factory.assert_not_called()

    def test_old_yahoo_report_does_not_erase_finnhub_reminder(self):
        future_finnhub_event = {
            **self.event,
            "date": "2026-10-06",
            "epsActual": None,
            "revenueActual": None,
        }
        yahoo_rows = [
            (datetime(2026, 9, 30, tzinfo=timezone.utc), {"Reported EPS": 1.0}),
            (datetime(2026, 10, 15, tzinfo=timezone.utc), {"Reported EPS": None}),
        ]
        event, *_ = self.run_calendar([future_finnhub_event], yahoo_rows)

        self.assertEqual(event.date.date(), date(2026, 10, 6))
        self.assertEqual(event.eps_estimate, 1.2)

    def test_missing_finnhub_key_uses_yahoo_dates(self):
        yahoo_ticker = Mock()
        yahoo_ticker.get_earnings_dates.return_value = EarningsDates([
            (datetime(2026, 10, 4, tzinfo=timezone.utc), {"Reported EPS": 2.4}),
        ])
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(tracker.yf, "Ticker", return_value=yahoo_ticker):
            event = tracker.get_earnings_calendar(["ACME"])["ACME"]

        self.assertFalse(event.is_upcoming)
        self.assertEqual(event.date.date(), date(2026, 10, 4))

    def test_repeated_yahoo_errors_stop_optional_lookup(self):
        client = Mock()
        client.earnings_calendar.return_value = {"earningsCalendar": []}
        symbols = ["A", "B", "C", "D"]
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(tracker, "get_finnhub_client", return_value=client), \
                patch.object(tracker.yf, "Ticker", side_effect=RuntimeError("Yahoo unavailable")) as ticker_factory:
            results = tracker.get_earnings_calendar(symbols)

        self.assertEqual(ticker_factory.call_count, 3)
        self.assertEqual(results, {symbol: None for symbol in symbols})

    def test_yahoo_time_budget_keeps_finnhub_calendar(self):
        client = Mock()
        client.earnings_calendar.return_value = {"earningsCalendar": []}
        yahoo_ticker = Mock()
        yahoo_ticker.get_earnings_dates.return_value = EarningsDates([])
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(tracker, "get_finnhub_client", return_value=client), \
                patch.object(tracker.yf, "Ticker", return_value=yahoo_ticker) as ticker_factory, \
                patch.object(tracker.time, "monotonic", side_effect=[0, 0, 121]):
            results = tracker.get_earnings_calendar(["A", "B"])

        ticker_factory.assert_called_once_with("A")
        self.assertEqual(results, {"A": None, "B": None})


if __name__ == "__main__":
    unittest.main()
