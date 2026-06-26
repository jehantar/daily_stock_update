from dataclasses import dataclass
import yfinance as yf
from src.data_fetcher import Ticker


@dataclass
class PriceMover:
    symbol: str
    daily_change: float
    extended_hours_change: float | None
    current_price: float | None
    company_name: str


def identify_movers(tickers: list[Ticker], threshold: float = 0.05) -> list[PriceMover]:
    """Identify stocks with daily change exceeding threshold (default 5%)."""
    movers = []

    for ticker in tickers:
        if abs(ticker.daily_change) >= threshold:
            extended_info = get_extended_hours_info(ticker.symbol)
            movers.append(PriceMover(
                symbol=ticker.symbol,
                daily_change=ticker.daily_change,
                extended_hours_change=extended_info.get("extended_change"),
                current_price=extended_info.get("current_price"),
                company_name=ticker.company_name or extended_info.get("name", ticker.symbol)
            ))

    # Sort by absolute change (largest moves first)
    movers.sort(key=lambda x: abs(x.daily_change), reverse=True)
    return movers


def get_extended_hours_info(symbol: str) -> dict:
    """Fetch extended hours data and company name from Yahoo Finance."""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        result = {
            "name": info.get("shortName") or info.get("longName") or symbol,
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        }

        # Calculate extended hours movement if available
        regular_close = info.get("regularMarketPrice")
        pre_market = info.get("preMarketPrice")
        post_market = info.get("postMarketPrice")

        if regular_close:
            # Use post-market if available, otherwise pre-market
            extended_price = post_market or pre_market
            if extended_price:
                extended_change = (extended_price - regular_close) / regular_close
                result["extended_change"] = extended_change

        return result
    except Exception:
        return {"name": symbol}


def format_change(change: float) -> str:
    """Format percentage change for display."""
    sign = "+" if change > 0 else ""
    return f"{sign}{change * 100:.1f}%"
