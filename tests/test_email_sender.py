import unittest
import sys
import types

sys.modules.setdefault("finnhub", types.SimpleNamespace(Client=lambda *args, **kwargs: None))
sys.modules.setdefault("nasdaqdatalink", types.SimpleNamespace(ApiConfig=types.SimpleNamespace(api_key=None)))
sys.modules.setdefault("src.chart_generator", types.SimpleNamespace(ChartPair=object))
from src.data_fetcher import Ticker
from src.email_sender import _generate_valuation_table, _get_custom_category


class EmailCategoryTest(unittest.TestCase):
    def test_latest_tickers_are_bucketed_into_existing_groups(self):
        semiconductor_tickers = [
            "AEIS", "AMD", "AAOI", "ARM", "ASML", "AXTI", "CIEN", "COHR",
            "INTC", "LRCX", "LITE", "MRVL", "SNDK", "TSEM", "VRT",
        ]
        for symbol in semiconductor_tickers:
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    _get_custom_category(symbol),
                    "Semiconductors, Hardware & Digital Infrastructure",
                )

        for symbol in ["CNQ", "KGC", "NEM", "LLY", "GSK"]:
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    _get_custom_category(symbol),
                    "Resources, Materials & Life Sciences",
                )

    def test_utility_tickers_get_dedicated_email_section(self):
        self.assertEqual(_get_custom_category("EIX"), "Energy, Utilities & Infrastructure")

        html = _generate_valuation_table([
            Ticker(symbol="EIX", daily_change=0.01),
            Ticker(symbol="ZZZZ", daily_change=0.0),
        ])

        utility_index = html.index("Energy, Utilities & Infrastructure")
        other_index = html.index("Other")
        self.assertLess(utility_index, other_index)


if __name__ == "__main__":
    unittest.main()
