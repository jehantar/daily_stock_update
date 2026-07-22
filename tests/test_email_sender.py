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


EXPECTED_CATEGORIES = {
    "AMZN": "Platform Technology & Digital Ecosystems",
    "GOOG": "Platform Technology & Digital Ecosystems",
    "META": "Platform Technology & Digital Ecosystems",
    "MSFT": "Platform Technology & Digital Ecosystems",
    "NFLX": "Platform Technology & Digital Ecosystems",
    "AAOI": "Semiconductors, Hardware & Digital Infrastructure",
    "AMD": "Semiconductors, Hardware & Digital Infrastructure",
    "ARM": "Semiconductors, Hardware & Digital Infrastructure",
    "ASML": "Semiconductors, Hardware & Digital Infrastructure",
    "AVGO": "Semiconductors, Hardware & Digital Infrastructure",
    "AXTI": "Semiconductors, Hardware & Digital Infrastructure",
    "CIEN": "Semiconductors, Hardware & Digital Infrastructure",
    "COHU": "Semiconductors, Hardware & Digital Infrastructure",
    "DOCN": "Semiconductors, Hardware & Digital Infrastructure",
    "INTC": "Semiconductors, Hardware & Digital Infrastructure",
    "KLIC": "Semiconductors, Hardware & Digital Infrastructure",
    "LRCX": "Semiconductors, Hardware & Digital Infrastructure",
    "MRVL": "Semiconductors, Hardware & Digital Infrastructure",
    "MU": "Semiconductors, Hardware & Digital Infrastructure",
    "MXL": "Semiconductors, Hardware & Digital Infrastructure",
    "NVDA": "Semiconductors, Hardware & Digital Infrastructure",
    "SNDK": "Semiconductors, Hardware & Digital Infrastructure",
    "STX": "Semiconductors, Hardware & Digital Infrastructure",
    "TER": "Semiconductors, Hardware & Digital Infrastructure",
    "TSM": "Semiconductors, Hardware & Digital Infrastructure",
    "TSEM": "Semiconductors, Hardware & Digital Infrastructure",
    "VICR": "Semiconductors, Hardware & Digital Infrastructure",
    "WDC": "Semiconductors, Hardware & Digital Infrastructure",
    "APP": "Enterprise, Security & GovTech Software",
    "AXON": "Enterprise, Security & GovTech Software",
    "BB": "Enterprise, Security & GovTech Software",
    "CRWD": "Enterprise, Security & GovTech Software",
    "NET": "Enterprise, Security & GovTech Software",
    "UBER": "Commerce, Marketplaces & Consumer Logistics",
    "WMT": "Commerce, Marketplaces & Consumer Logistics",
    "PGC": "Financials & Assets",
    "LLY": "Resources, Materials & Life Sciences",
    "TWST": "Resources, Materials & Life Sciences",
    "TIGO": "Energy",
    "AGX": "Utilities & Infrastructure",
    "FIX": "Utilities & Infrastructure",
    "LINC": "Other",
    "WLY": "Other",
}


class EmailSenderCategoryTests(unittest.TestCase):
    def test_requested_tickers_use_approved_themes(self) -> None:
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
