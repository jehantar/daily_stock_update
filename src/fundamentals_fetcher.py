"""Fetch quarterly fundamental data from Yahoo Finance via yfinance."""

from dataclasses import dataclass
from datetime import datetime
import re

import numpy as np
import pandas as pd
import yfinance as yf


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
    # Absolute quarterly values for charts and orchestration.
    revenue: list[float | None] = None
    eps: list[float | None] = None
    ebitda_values: list[float | None] = None
    fcf_values: list[float | None] = None
    capex_values: list[float | None] = None
    # Year-over-year growth rates.
    revenue_yoy: list[float | None] = None
    eps_yoy: list[float | None] = None
    fcf_yoy: list[float | None] = None
    capex_yoy: list[float | None] = None
    financial_currency: str | None = None


def _normalize_label(value: object) -> str:
    """Normalize Yahoo statement row names so aliases match consistently."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


_ROW_ALIASES = {
    "revenue": ("Total Revenue", "Operating Revenue", "Revenue"),
    "eps": ("Diluted EPS", "Basic EPS", "EPS"),
    "ebitda": ("EBITDA",),
    "gross_profit": ("Gross Profit",),
    "operating_income": ("Operating Income", "Operating Income Loss"),
    "net_income": ("Net Income", "Net Income Common Stockholders", "Net Income Continuous Operations"),
    "operating_cash_flow": ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities"),
    "free_cash_flow": ("Free Cash Flow",),
    "capex": ("Capital Expenditure", "Capital Expenditures", "Purchase Of PPE"),
    "total_assets": ("Total Assets",),
    "equity": ("Stockholders Equity", "Total Stockholder Equity", "Total Equity Gross Minority Interest"),
}


def _statement(ticker: object, attribute: str) -> pd.DataFrame:
    """Read a yfinance quarterly statement, tolerating older attribute names."""
    aliases = {
        "quarterly_financials": "quarterly_income_stmt",
        "quarterly_cashflow": "quarterly_cash_flow",
        "quarterly_balance_sheet": "quarterly_balancesheet",
    }
    try:
        frame = getattr(ticker, attribute, None)
    except Exception:
        frame = None
    if frame is None:
        try:
            frame = getattr(ticker, aliases.get(attribute, ""), None)
        except Exception:
            frame = None
    return frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame()


def _find_row(frame: pd.DataFrame, metric: str) -> pd.Series:
    """Return the first available alias row, or an empty series."""
    if frame.empty:
        return pd.Series(dtype="float64")
    rows = {_normalize_label(index): index for index in frame.index}
    for alias in _ROW_ALIASES[metric]:
        actual = rows.get(_normalize_label(alias))
        if actual is not None:
            return frame.loc[actual]
    return pd.Series(index=frame.columns, dtype="float64")


def _to_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _series_by_date(frame: pd.DataFrame, metric: str) -> dict[pd.Timestamp, float | None]:
    """Convert a statement row to timestamp keyed values."""
    if frame.empty:
        return {}
    row = _find_row(frame, metric)
    values: dict[pd.Timestamp, float | None] = {}
    for date, value in row.items():
        timestamp = pd.to_datetime(date, errors="coerce")
        if pd.notna(timestamp):
            values[pd.Timestamp(timestamp).normalize()] = _to_number(value)
    return values


def _pct_change(values: list[float | None], periods: int = 1) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    for index in range(periods, len(values)):
        current, prior = values[index], values[index - periods]
        if current is not None and prior not in (None, 0):
            result[index] = current / prior - 1
    return result


def _currency(ticker: object) -> str | None:
    try:
        info = ticker.get_info() if hasattr(ticker, "get_info") else ticker.info
        currency = info.get("financialCurrency")
        return str(currency).upper() if currency else None
    except Exception:
        return None


def _safe_average_ratio(numerator: float | None, current: float | None, prior: float | None) -> float | None:
    if numerator is None or current is None or prior is None:
        return None
    denominator = (current + prior) / 2
    if denominator == 0:
        return None
    return numerator / denominator


def _fetch_one(symbol: str, company_name: str, quarters: int) -> FundamentalData | None:
    """Fetch and align income, cashflow, and balance-sheet rows for one symbol."""
    ticker = yf.Ticker(symbol)
    income = _statement(ticker, "quarterly_income_stmt")
    if income.empty:
        income = _statement(ticker, "quarterly_financials")
    cashflow = _statement(ticker, "quarterly_cashflow")
    balance = _statement(ticker, "quarterly_balance_sheet")

    if income.empty and cashflow.empty and balance.empty:
        return None

    fields = {
        "revenue": income,
        "eps": income,
        "ebitda": income,
        "gross_profit": income,
        "operating_income": income,
        "net_income": income,
        "operating_cash_flow": cashflow,
        "free_cash_flow": cashflow,
        "capex": cashflow,
        "total_assets": balance,
        "equity": balance,
    }
    series = {name: _series_by_date(frame, name) for name, frame in fields.items()}
    all_dates = sorted(set().union(*(values.keys() for values in series.values())))
    if not all_dates:
        return None

    # Include four extra reports to calculate YoY growth before returning the requested window.
    selected_dates = all_dates[-(quarters + 4):]

    def values(metric: str) -> list[float | None]:
        return [series[metric].get(date) for date in selected_dates]

    revenue = values("revenue")
    eps = values("eps")
    ebitda = values("ebitda")
    gross_profit = values("gross_profit")
    operating_income = values("operating_income")
    net_income = values("net_income")
    operating_cash = values("operating_cash_flow")
    reported_fcf = values("free_cash_flow")
    raw_capex = values("capex")
    assets = values("total_assets")
    equity = values("equity")

    capex = [None if amount is None else abs(amount) for amount in raw_capex]
    fcf = [
        reported if reported is not None else (
            cash - investment if cash is not None and investment is not None else None
        )
        for reported, cash, investment in zip(reported_fcf, operating_cash, capex)
    ]

    def margin(numerators: list[float | None]) -> list[float | None]:
        return [
            numerator / denominator if numerator is not None and denominator not in (None, 0) else None
            for numerator, denominator in zip(numerators, revenue)
        ]

    roe: list[float | None] = []
    roa: list[float | None] = []
    for index in range(len(selected_dates)):
        ttm_net_income = (
            sum(net_income[index - 3:index + 1])
            if index >= 3 and all(v is not None for v in net_income[index - 3:index + 1])
            else None
        )
        prior_assets = assets[index - 4] if index >= 4 else None
        prior_equity = equity[index - 4] if index >= 4 else None
        roa.append(_safe_average_ratio(ttm_net_income, assets[index], prior_assets))
        roe.append(_safe_average_ratio(ttm_net_income, equity[index], prior_equity))

    output_start = max(0, len(selected_dates) - quarters)
    output_dates = selected_dates[output_start:]

    def tail(items: list[float | None]) -> list[float | None]:
        return items[output_start:]

    return FundamentalData(
        ticker=symbol,
        company_name=company_name,
        quarters=[date.to_pydatetime() for date in output_dates],
        revenue_growth=tail(_pct_change(revenue)),
        eps_growth=tail(_pct_change(eps)),
        fcf_growth=tail(_pct_change(fcf)),
        ebitda_growth=tail(_pct_change(ebitda)),
        roe=tail(roe),
        roa=tail(roa),
        gross_margin=tail(margin(gross_profit)),
        net_margin=tail(margin(net_income)),
        operating_margin=tail(margin(operating_income)),
        revenue=tail(revenue),
        eps=tail(eps),
        ebitda_values=tail(ebitda),
        fcf_values=tail(fcf),
        capex_values=tail(capex),
        revenue_yoy=tail(_pct_change(revenue, 4)),
        eps_yoy=tail(_pct_change(eps, 4)),
        fcf_yoy=tail(_pct_change(fcf, 4)),
        capex_yoy=tail(_pct_change(capex, 4)),
        financial_currency=_currency(ticker),
    )


def fetch_fundamentals(
    symbols: list[str],
    company_names: dict[str, str] = None,
    quarters: int = 6,
) -> dict[str, FundamentalData]:
    """Fetch quarterly Yahoo Finance fundamentals, isolating failures by ticker."""
    if not symbols:
        return {}
    if quarters <= 0:
        return {}

    company_names = company_names or {}
    results: dict[str, FundamentalData] = {}
    print(f"  Fetching quarterly fundamentals for {len(symbols)} tickers from Yahoo Finance...")
    for symbol in symbols:
        try:
            data = _fetch_one(symbol, company_names.get(symbol, symbol), quarters)
            if data is None or len(data.quarters) < 2:
                print(f"  Warning: No usable quarterly fundamentals for {symbol}")
                continue
            results[symbol] = data
        except Exception as exc:
            print(f"  Warning: Failed to fetch fundamentals for {symbol}: {exc}")
    print(f"  Retrieved fundamentals for {len(results)} of {len(symbols)} tickers")
    return results
