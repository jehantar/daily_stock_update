from collections import Counter
import sys
import types
import unittest


# Keep this mapping test independent of the optional market-data client.
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
finnhub = types.ModuleType("finnhub")
finnhub.Client = object
sys.modules.setdefault("finnhub", finnhub)
sys.modules.setdefault("nasdaqdatalink", types.ModuleType("nasdaqdatalink"))
chart_generator = types.ModuleType("src.chart_generator")
chart_generator.ChartPair = object
sys.modules.setdefault("src.chart_generator", chart_generator)

from src.email_sender import CATEGORY_ORDER, _get_custom_category


CURRENT_TICKERS = """AMD GOOG AMZN APLE AAOI ARM AXON AXTI AVGO CAKE NET CNO
COHR CRWD DOCN LLY FRO INTC LITE MGNI MPC MRVL META MU MSFT NTAP NFLX
NTNX NVDA PAYS PSX PRLB SNDK STX SMTC TSM TGTX TSEM TWLO UBER VLO WMT""".split()

EXPECTED_CATEGORIES = {
    "AMZN": "Platform Technology & Digital Ecosystems",
    "GOOG": "Platform Technology & Digital Ecosystems",
    "META": "Platform Technology & Digital Ecosystems",
    "MGNI": "Platform Technology & Digital Ecosystems",
    "MSFT": "Platform Technology & Digital Ecosystems",
    "NFLX": "Platform Technology & Digital Ecosystems",
    "AAOI": "Semiconductors, Hardware & Digital Infrastructure",
    "AMD": "Semiconductors, Hardware & Digital Infrastructure",
    "ARM": "Semiconductors, Hardware & Digital Infrastructure",
    "AVGO": "Semiconductors, Hardware & Digital Infrastructure",
    "AXTI": "Semiconductors, Hardware & Digital Infrastructure",
    "COHR": "Semiconductors, Hardware & Digital Infrastructure",
    "DOCN": "Semiconductors, Hardware & Digital Infrastructure",
    "INTC": "Semiconductors, Hardware & Digital Infrastructure",
    "LITE": "Semiconductors, Hardware & Digital Infrastructure",
    "MRVL": "Semiconductors, Hardware & Digital Infrastructure",
    "MU": "Semiconductors, Hardware & Digital Infrastructure",
    "NTAP": "Semiconductors, Hardware & Digital Infrastructure",
    "NVDA": "Semiconductors, Hardware & Digital Infrastructure",
    "PRLB": "Semiconductors, Hardware & Digital Infrastructure",
    "SMTC": "Semiconductors, Hardware & Digital Infrastructure",
    "SNDK": "Semiconductors, Hardware & Digital Infrastructure",
    "STX": "Semiconductors, Hardware & Digital Infrastructure",
    "TSM": "Semiconductors, Hardware & Digital Infrastructure",
    "TSEM": "Semiconductors, Hardware & Digital Infrastructure",
    "AXON": "Enterprise, Security & GovTech Software",
    "CRWD": "Enterprise, Security & GovTech Software",
    "NET": "Enterprise, Security & GovTech Software",
    "NTNX": "Enterprise, Security & GovTech Software",
    "TWLO": "Enterprise, Security & GovTech Software",
    "CAKE": "Commerce, Marketplaces & Consumer Logistics",
    "UBER": "Commerce, Marketplaces & Consumer Logistics",
    "WMT": "Commerce, Marketplaces & Consumer Logistics",
    "APLE": "Financials & Assets",
    "CNO": "Financials & Assets",
    "PAYS": "Financials & Assets",
    "LLY": "Resources, Materials & Life Sciences",
    "TGTX": "Resources, Materials & Life Sciences",
    "FRO": "Energy",
    "MPC": "Energy",
    "PSX": "Energy",
    "VLO": "Energy",
}


class EmailSenderCategoryTests(unittest.TestCase):
    def test_current_watchlist_has_complete_theme_coverage(self) -> None:
        self.assertEqual(len(CURRENT_TICKERS), 42)
        self.assertEqual(len(set(CURRENT_TICKERS)), 42)
        self.assertEqual(set(EXPECTED_CATEGORIES), set(CURRENT_TICKERS))
        counts = Counter(_get_custom_category(symbol) for symbol in CURRENT_TICKERS)
        self.assertNotIn("Other", counts)
        self.assertEqual(counts["Resources, Materials & Life Sciences"], 2)
        self.assertTrue(all(count >= 3 for category, count in counts.items()
                            if category != "Resources, Materials & Life Sciences"))

    def test_current_tickers_use_expected_themes(self) -> None:
        for symbol, expected_category in EXPECTED_CATEGORIES.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(_get_custom_category(symbol), expected_category)

    def test_category_order_stays_unchanged(self) -> None:
        self.assertEqual(
            CATEGORY_ORDER,
            [
                "Platform Technology & Digital Ecosystems",
                "Semiconductors, Hardware & Digital Infrastructure",
                "Enterprise, Security & GovTech Software",
                "Commerce, Marketplaces & Consumer Logistics",
                "Financials & Assets",
                "Resources, Materials & Life Sciences",
                "Energy",
                "Utilities & Infrastructure",
                "Other",
            ],
        )
