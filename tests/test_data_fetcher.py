import unittest

from src.data_fetcher import parse_ticker_list


class ParseTickerListTest(unittest.TestCase):
    def test_simple_list_rejects_non_ticker_text(self):
        content = "\n".join(["MU", "THAT'S", "SNDK"])

        self.assertEqual(parse_ticker_list(content), ["MU", "SNDK"])

    def test_csv_parser_respects_quoted_columns_before_ticker(self):
        content = "\n".join([
            '"Semis, Hardware",Core,MU',
            '"Optical, Networking",Core,SNDK',
        ])

        self.assertEqual(parse_ticker_list(content), ["MU", "SNDK"])


if __name__ == "__main__":
    unittest.main()
