"""Fetch quarterly fundamental data from Nasdaq Data Link (SHARADAR/SF1)."""

import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Iterable

import nasdaqdatalink as ndl
import numpy as np
import pandas as pd
from pandas.tseries.offsets import QuarterEnd


# API configuration
TICKER_CHUNK_SIZE = 150
MIN_REQUEST_INTERVAL = 0.5  # seconds between API calls
_last_request_time = 0

# Columns to fetch from each dimension
MRQ_COLUMNS = ["ticker", "dimension", "calendardate", "revenueusd", "eps", "fcf", "ebitda", "grossmargin", "netmargin"]
ART_COLUMNS = ["ticker", "dimension", "calendardate", "roe", "roa"]


@dataclass
class FundamentalData:
    """Quarterly fundamental metrics for a single ticker."""
    ticker: str
    company_name: str
    quarters: list[datetime]
    revenue_growth: list[float | None]
    eps_growth: list[float | None]
    fcf_growth: list[float | None]
    ebitda_growth: list[float | None]
    roe: list[float | None]
    roa: list[float | None]
    gross_margin: list[float | None]
    net_margin: list[float | None]
    operating_margin: list[float | None]
    # Absolute values for bar charts
    revenue: list[float | None] = None
    eps: list[float | None] = None
    ebitda_values: list[float | None] = None
    # YoY growth rates
    revenue_yoy: list[float | None] = None
    eps_yoy: list[float | None] = None


def ensure_api_key() -> str:
    """Load NASDAQ_DATA_LINK_API_KEY from environment."""
    api_key = os.environ.get("NASDAQ_DATA_LINK_API_KEY")
    if not api_key:
        raise ValueError("NASDAQ_DATA_LINK_API_KEY environment variable not set")
    return api_key


def _rate_limit():
    """Enforce rate limiting between API calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _chunked(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    """Split iterable into chunks of specified size."""
    chunk: List[str] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _download_sf1_chunk(
    api_key: str,
    tickers: List[str],
    dimension: str,
    columns: List[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Download a chunk of SF1 data from Nasdaq Data Link."""
    params = {
        "ticker": tickers,
        "dimension": dimension,
        "calendardate": {"gte": start_date, "lte": end_date},
        "qopts": {"columns": columns},
    }

    _rate_limit()
    ndl.ApiConfig.api_key = api_key
    df = ndl.get_table("SHARADAR/SF1", paginate=True, **params)

    if df.empty:
        return pd.DataFrame(columns=columns)

    return df


def _fetch_sf1_data(
    api_key: str,
    tickers: List[str],
    dimension: str,
    columns: List[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch SF1 data for all tickers, chunking to stay within API limits."""
    frames: List[pd.DataFrame] = []

    for chunk in _chunked(tickers, TICKER_CHUNK_SIZE):
        try:
            chunk_df = _download_sf1_chunk(api_key, chunk, dimension, columns, start_date, end_date)
            frames.append(chunk_df)
        except Exception as e:
            print(f"  Warning: Failed to fetch chunk: {e}")
            continue

    if not frames:
        return pd.DataFrame(columns=columns)

    df = pd.concat(frames, ignore_index=True)
    df = df[df["dimension"] == dimension]
    df["calendardate"] = pd.to_datetime(df["calendardate"])
    df = df.sort_values(["ticker", "calendardate"]).drop_duplicates(["ticker", "calendardate"], keep="last")

    return df.reset_index(drop=True)


def _add_growth_columns(df: pd.DataFrame, value_columns: List[str]) -> pd.DataFrame:
    """Calculate QoQ percentage change for specified columns."""
    df = df.copy()
    df = df.sort_values(["ticker", "calendardate"])

    for col in value_columns:
        if col in df.columns:
            growth_col = f"{col}_growth"
            df[growth_col] = df.groupby("ticker")[col].pct_change(fill_method=None)

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    return df


def _add_yoy_growth_columns(df: pd.DataFrame, value_columns: List[str]) -> pd.DataFrame:
    """Calculate YoY (4-quarter) percentage change for specified columns."""
    df = df.copy()
    df = df.sort_values(["ticker", "calendardate"])

    for col in value_columns:
        if col in df.columns:
            yoy_col = f"{col}_yoy"
            df[yoy_col] = df.groupby("ticker")[col].pct_change(periods=4, fill_method=None)

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    return df


def _get_date_range(quarters: int) -> tuple[str, str]:
    """Calculate start and end dates to cover the requested number of quarters."""
    today = pd.Timestamp.today()
    end_date = today + QuarterEnd(0)
    # Need extra quarters: +1 for QoQ growth, +4 for YoY growth
    start_date = end_date - QuarterEnd(quarters + 5)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def fetch_fundamentals(
    symbols: list[str],
    company_names: dict[str, str] = None,
    quarters: int = 6,
) -> dict[str, FundamentalData]:
    """
    Fetch fundamental data for all symbols.

    Args:
        symbols: List of ticker symbols
        company_names: Optional dict mapping symbol -> company name
        quarters: Number of quarters of history to fetch (default 6)

    Returns:
        Dict mapping symbol -> FundamentalData (missing/failed tickers excluded)
    """
    if not symbols:
        return {}

    company_names = company_names or {}
    api_key = ensure_api_key()
    start_date, end_date = _get_date_range(quarters)

    print(f"  Fetching MRQ data for {len(symbols)} tickers...")
    mrq_df = _fetch_sf1_data(api_key, symbols, "MRQ", MRQ_COLUMNS, start_date, end_date)
    mrq_df = _add_growth_columns(mrq_df, ["revenueusd", "eps", "fcf", "ebitda"])
    mrq_df = _add_yoy_growth_columns(mrq_df, ["revenueusd", "eps"])

    print(f"  Fetching ART data for {len(symbols)} tickers...")
    art_df = _fetch_sf1_data(api_key, symbols, "ART", ART_COLUMNS, start_date, end_date)

    # Merge MRQ and ART data
    if mrq_df.empty and art_df.empty:
        print("  Warning: No fundamental data retrieved")
        return {}

    if not mrq_df.empty and not art_df.empty:
        merged = pd.merge(
            mrq_df,
            art_df.drop(columns=["dimension"]),
            on=["ticker", "calendardate"],
            how="outer",
            suffixes=("", "_art"),
        )
    elif not mrq_df.empty:
        merged = mrq_df
    else:
        merged = art_df

    merged = merged.sort_values(["ticker", "calendardate"])

    # Convert to FundamentalData objects
    results: dict[str, FundamentalData] = {}

    for ticker in merged["ticker"].unique():
        ticker_data = merged[merged["ticker"] == ticker].tail(quarters)

        if len(ticker_data) < 2:
            # Not enough data for meaningful charts
            continue

        def safe_list(col: str) -> list[float | None]:
            if col not in ticker_data.columns:
                return [None] * len(ticker_data)
            return [None if pd.isna(v) else float(v) for v in ticker_data[col].tolist()]

        results[ticker] = FundamentalData(
            ticker=ticker,
            company_name=company_names.get(ticker, ticker),
            quarters=[dt.to_pydatetime() for dt in ticker_data["calendardate"]],
            revenue_growth=safe_list("revenueusd_growth"),
            eps_growth=safe_list("eps_growth"),
            fcf_growth=safe_list("fcf_growth"),
            ebitda_growth=safe_list("ebitda_growth"),
            roe=safe_list("roe"),
            roa=safe_list("roa"),
            gross_margin=safe_list("grossmargin"),
            net_margin=safe_list("netmargin"),
            operating_margin=[None] * len(ticker_data),  # opmargin not available in Sharadar SF1
            revenue=safe_list("revenueusd"),
            eps=safe_list("eps"),
            ebitda_values=safe_list("ebitda"),
            revenue_yoy=safe_list("revenueusd_yoy"),
            eps_yoy=safe_list("eps_yoy"),
        )

    return results
