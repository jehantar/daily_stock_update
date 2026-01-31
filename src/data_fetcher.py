import os
import csv
import requests
from io import StringIO
from dataclasses import dataclass


@dataclass
class Ticker:
    symbol: str
    daily_change: float  # As decimal (e.g., -0.05 for -5%)
    ytd_change: float | None = None


def fetch_tickers_from_gist() -> list[Ticker]:
    """Fetch and parse ticker list from GitHub Gist CSV."""
    gist_url = os.environ.get("GIST_URL")
    if not gist_url:
        raise ValueError("GIST_URL environment variable not set")

    # Convert Gist URL to raw URL if needed
    if "gist.github.com" in gist_url and "/raw" not in gist_url:
        # Handle standard gist URLs
        gist_url = gist_url.replace("gist.github.com", "gist.githubusercontent.com")
        if not gist_url.endswith("/raw"):
            gist_url = gist_url + "/raw"

    response = requests.get(gist_url, timeout=30)
    response.raise_for_status()

    return parse_csv(response.text)


def parse_csv(csv_content: str) -> list[Ticker]:
    """Parse CSV content into Ticker objects."""
    tickers = []
    reader = csv.DictReader(StringIO(csv_content))

    for row in reader:
        symbol = row.get("Ticker", "").strip().upper()
        if not symbol:
            continue

        daily_change = parse_percentage(row.get("Daily Price Change", "0"))
        ytd_change = parse_percentage(row.get("YTD Price Change"))

        tickers.append(Ticker(
            symbol=symbol,
            daily_change=daily_change,
            ytd_change=ytd_change
        ))

    return tickers


def parse_percentage(value: str | None) -> float | None:
    """Parse percentage string to decimal. Handles '5%', '0.05', '-5%', etc."""
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        if "%" in value:
            return float(value.replace("%", "")) / 100
        else:
            num = float(value)
            # If value > 1 or < -1, assume it's already a percentage
            if abs(num) > 1:
                return num / 100
            return num
    except ValueError:
        return None
