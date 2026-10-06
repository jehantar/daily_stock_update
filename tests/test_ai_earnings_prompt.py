"""Check that mixed-source earnings context stays labeled in the AI prompt."""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from src import ai_analyzer
from src.earnings_tracker import EarningsEvent, FundamentalContext


class EarningsPromptTests(unittest.TestCase):
    def test_native_statement_currency_is_not_compared_with_finnhub_estimates(self) -> None:
        event = EarningsEvent(
            symbol="TSM",
            company_name="Taiwan Semiconductor",
            date=datetime(2026, 10, 5),
            time="bmo",
            eps_estimate=4.0,
            revenue_estimate=30_000_000_000,
            is_upcoming=False,
            actual_eps=4.2,
            actual_revenue=31_000_000_000,
            fundamental_context=FundamentalContext(
                revenue=1_000_000_000_000,
                eps=130.0,
                fcf=200_000_000_000,
                financial_currency="TWD",
            ),
        )
        client = Mock()
        client.responses.create.return_value.output_text = "Summary"
        with patch.object(ai_analyzer, "get_openai_client", return_value=client), \
                patch.object(ai_analyzer, "rate_limit"), \
                patch.object(ai_analyzer, "format_news_for_prompt", return_value="No news"):
            self.assertEqual(ai_analyzer.analyze_earnings_report(event, []), "Summary")

        prompt = client.responses.create.call_args.kwargs["input"]
        self.assertIn("Yahoo quarterly statements (TWD)", prompt)
        self.assertIn("Statement EPS: 130.00 TWD", prompt)
        self.assertIn("Do not compare these figures with Finnhub estimates", prompt)
        self.assertIn("A calendar date alone does not confirm reported results", prompt)


if __name__ == "__main__":
    unittest.main()
