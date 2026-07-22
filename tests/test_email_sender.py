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
        expected_categories = {
            "AEIS": "Semiconductors, Hardware & Digital Infrastructure",
            "AMD": "Semiconductors, Hardware & Digital Infrastructure",
            "AAOI": "Semiconductors, Hardware & Digital Infrastructure",
            "ARM": "Semiconductors, Hardware & Digital Infrastructure",
            "ASML": "Semiconductors, Hardware & Digital Infrastructure",
            "AXTI": "Semiconductors, Hardware & Digital Infrastructure",
            "CIEN": "Semiconductors, Hardware & Digital Infrastructure",
            "COHR": "Semiconductors, Hardware & Digital Infrastructure",
            "INTC": "Semiconductors, Hardware & Digital Infrastructure",
            "LRCX": "Semiconductors, Hardware & Digital Infrastructure",
            "LITE": "Semiconductors, Hardware & Digital Infrastructure",
            "MRVL": "Semiconductors, Hardware & Digital Infrastructure",
            "SNDK": "Semiconductors, Hardware & Digital Infrastructure",
            "TSEM": "Semiconductors, Hardware & Digital Infrastructure",
            "VRT": "Semiconductors, Hardware & Digital Infrastructure",
            "CNQ": "Resources, Materials & Life Sciences",
            "KGC": "Resources, Materials & Life Sciences",
            "NEM": "Resources, Materials & Life Sciences",
            "LLY": "Resources, Materials & Life Sciences",
            "GSK": "Resources, Materials & Life Sciences",
            "BB": "Enterprise, Security & GovTech Software",
            "COHU": "Semiconductors, Hardware & Digital Infrastructure",
            "KLIC": "Semiconductors, Hardware & Digital Infrastructure",
            "MXL": "Semiconductors, Hardware & Digital Infrastructure",
            "DOCN": "Semiconductors, Hardware & Digital Infrastructure",
            "STX": "Semiconductors, Hardware & Digital Infrastructure",
            "TER": "Semiconductors, Hardware & Digital Infrastructure",
            "VICR": "Semiconductors, Hardware & Digital Infrastructure",
            "PGC": "Financials & Assets",
            "TWST": "Resources, Materials & Life Sciences",
            "AGX": "Energy, Utilities & Infrastructure",
            "FIX": "Energy, Utilities & Infrastructure",
            "TIGO": "Energy, Utilities & Infrastructure",
            "LINC": "Other",
            "WLY": "Other",
        }
        for symbol, category in expected_categories.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(_get_custom_category(symbol), category)

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
