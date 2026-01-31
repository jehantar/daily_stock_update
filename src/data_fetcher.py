import os
import requests
import yfinance as yf
from dataclasses import dataclass


@dataclass
class Ticker:
    symbol: str
    daily_change: float  # As decimal (e.g., -0.05 for -5%)
    company_name: str = ""


def fetch_tickers_from_gist() -> list[str]:
    """Fetch ticker symbols from GitHub Gist.

    Supports simple format: one ticker per line.
    Lines starting with # are comments.
    """
    gist_url = os.environ.get("GIST_URL")
    if not gist_url:
        raise ValueError("GIST_URL environment variable not set")

    # Convert Gist URL to raw URL if needed
    if "gist.github.com" in gist_url and "/raw" not in gist_url:
        gist_url = gist_url.replace("gist.github.com", "gist.githubusercontent.com")
        if not gist_url.endswith("/raw"):
            gist_url = gist_url + "/raw"

    response = requests.get(gist_url, timeout=30)
    response.raise_for_status()

    return parse_ticker_list(response.text)


def parse_ticker_list(content: str) -> list[str]:
    """Parse ticker list from content.

    Supports:
    1. Simple list: one ticker per line
    2. CSV format: (empty), Category, Ticker, ...
    """
    lines = content.strip().split('\n')
    if not lines:
        return []

    symbols = []

    # Check if it's a CSV with multiple columns
    first_line = lines[0]
    if ',' in first_line:
        # CSV format: (empty), Category, Ticker, YTD%, Daily%, (empty)
        # Ticker is in column index 2
        for line in lines:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                ticker = parts[2].upper()
                # Valid ticker: 1-5 alphanumeric chars, not a category name
                if ticker and 1 <= len(ticker) <= 5 and ticker not in ('CORE', 'IRA', 'TICKER'):
                    symbols.append(ticker)
    else:
        # Simple list format: one ticker per line
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                symbol = line.upper().split()[0]  # Take first word
                if symbol and symbol not in ('CORE', 'IRA', 'TICKER'):
                    symbols.append(symbol)

    return list(dict.fromkeys(symbols))  # Remove duplicates, preserve order


def fetch_price_data(symbols: list[str]) -> list[Ticker]:
    """Fetch current price data from Yahoo Finance for all symbols."""
    tickers = []

    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            # Get daily change
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

            daily_change = 0.0
            if current_price and prev_close and prev_close > 0:
                daily_change = (current_price - prev_close) / prev_close

            company_name = info.get("shortName") or info.get("longName") or symbol

            tickers.append(Ticker(
                symbol=symbol,
                daily_change=daily_change,
                company_name=company_name
            ))
            print(f"  {symbol}: {daily_change*100:+.1f}%")

        except Exception as e:
            print(f"  {symbol}: failed to fetch ({e})")
            # Still add the ticker with 0 change so it's tracked
            tickers.append(Ticker(symbol=symbol, daily_change=0.0, company_name=symbol))

    return tickers
