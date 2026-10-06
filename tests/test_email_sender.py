import importlib.util
from collections import Counter
import sys
import types
import unittest


# Keep this mapping test independent of the optional market-data client.
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
finnhub = types.ModuleType("finnhub")
finnhub.Client = object
sys.modules.setdefault("finnhub", finnhub)
if importlib.util.find_spec("matplotlib") is None:
    chart_generator = types.ModuleType("src.chart_generator")
    chart_generator.ChartPair = object
    sys.modules.setdefault("src.chart_generator", chart_generator)

from src.email_sender import CATEGORY_ORDER, _get_custom_category


CURRENT_TICKERS = """AMD GOOG AMZN APLE AAOI ARM AXON AXTI AVGO CAKE NET CNO
COHR CRWD DOCN LLY FRO INTC LITE MGNI MPC MRVL META MU MSFT NTAP NFLX
NTNX NVDA PAYS PSX PRLB SNDK STX SMTC TSM TGTX TSEM TWLO UBER VLO WMT""".split()

EXPECTED_CATEGORIES = {
    "AMZN": "Platform Technology & Digital Ecosystems",
    "DOCN": "Platform Technology & Digital Ecosystems",
    "GOOG": "Platform Technology & Digital Ecosystems",
    "META": "Platform Technology & Digital Ecosystems",
    "MGNI": "Platform Technology & Digital Ecosystems",
    "MSFT": "Platform Technology & Digital Ecosystems",
    "NFLX": "Platform Technology & Digital Ecosystems",
    "AMD": "Chip Design & IP",
    "ARM": "Chip Design & IP",
    "AVGO": "Chip Design & IP",
    "MRVL": "Chip Design & IP",
    "NVDA": "Chip Design & IP",
    "SMTC": "Chip Design & IP",
    "INTC": "Manufacturing & Chip Foundries",
    "PRLB": "Manufacturing & Chip Foundries",
    "TSM": "Manufacturing & Chip Foundries",
    "TSEM": "Manufacturing & Chip Foundries",
    "AAOI": "Optical Networks & Materials",
    "AXTI": "Optical Networks & Materials",
    "COHR": "Optical Networks & Materials",
    "LITE": "Optical Networks & Materials",
    "MU": "Memory & Data Storage",
    "NTAP": "Memory & Data Storage",
    "SNDK": "Memory & Data Storage",
    "STX": "Memory & Data Storage",
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

LEGACY_HARDWARE_CATEGORIES = {
    "AEIS": "Manufacturing & Chip Foundries",
    "ASML": "Manufacturing & Chip Foundries",
    "CIEN": "Optical Networks & Materials",
    "CLS": "Manufacturing & Chip Foundries",
    "COHU": "Manufacturing & Chip Foundries",
    "KLIC": "Manufacturing & Chip Foundries",
    "LRCX": "Manufacturing & Chip Foundries",
    "MXL": "Chip Design & IP",
    "TER": "Manufacturing & Chip Foundries",
    "VICR": "Manufacturing & Chip Foundries",
    "WDC": "Memory & Data Storage",
}


class EmailSenderCategoryTests(unittest.TestCase):
    def test_current_watchlist_has_complete_theme_coverage(self) -> None:
        self.assertEqual(len(CURRENT_TICKERS), 42)
        self.assertEqual(len(set(CURRENT_TICKERS)), 42)
        self.assertEqual(set(EXPECTED_CATEGORIES), set(CURRENT_TICKERS))
        counts = Counter(_get_custom_category(symbol) for symbol in CURRENT_TICKERS)
        self.assertNotIn("Other", counts)
        self.assertNotIn("Semiconductors, Hardware & Digital Infrastructure", counts)
        self.assertEqual(counts["Chip Design & IP"], 6)
        self.assertEqual(counts["Manufacturing & Chip Foundries"], 4)
        self.assertEqual(counts["Optical Networks & Materials"], 4)
        self.assertEqual(counts["Memory & Data Storage"], 4)
        self.assertEqual(counts["Resources, Materials & Life Sciences"], 2)
        self.assertTrue(all(count >= 3 for category, count in counts.items()
                            if category != "Resources, Materials & Life Sciences"))

    def test_current_tickers_use_expected_themes(self) -> None:
        for symbol, expected_category in EXPECTED_CATEGORIES.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(_get_custom_category(symbol), expected_category)

    def test_legacy_hardware_tickers_use_the_split_themes(self) -> None:
        for symbol, expected_category in LEGACY_HARDWARE_CATEGORIES.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(_get_custom_category(symbol), expected_category)

    def test_category_order_stays_unchanged(self) -> None:
        self.assertEqual(
            CATEGORY_ORDER,
            [
                "Platform Technology & Digital Ecosystems",
                "Chip Design & IP",
                "Manufacturing & Chip Foundries",
                "Optical Networks & Materials",
                "Memory & Data Storage",
                "Enterprise, Security & GovTech Software",
                "Commerce, Marketplaces & Consumer Logistics",
                "Financials & Assets",
                "Resources, Materials & Life Sciences",
                "Energy",
                "Utilities & Infrastructure",
                "Other",
            ],
        )
