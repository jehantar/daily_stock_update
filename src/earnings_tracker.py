import os
from datetime import datetime, timedelta
from dataclasses import dataclass
import finnhub
import yfinance as yf
import pandas as pd

from src.fundamentals_fetcher import ensure_api_key, _fetch_sf1_data


def _get_effective_today() -> datetime:
    """Get the effective 'today' date, allowing override via REPORT_DATE env var.

    Set REPORT_DATE=YYYY-MM-DD to simulate running the report on a past date.
    """
    override = os.environ.get("REPORT_DATE")
    if override:
        return datetime.strptime(override, "%Y-%m-%d")
    return datetime.now()


@dataclass
class FundamentalContext:
    """QoQ and YoY fundamental trends from Sharadar for earnings analysis."""
    # Quarter-over-Quarter changes
    revenue_qoq_change: float | None = None
    eps_qoq_change: float | None = None
    fcf: float | None = None  # Current quarter FCF
    fcf_qoq_change: float | None = None
    capex: float | None = None  # Current quarter CapEx
    capex_qoq_change: float | None = None
    gross_margin: float | None = None  # Current quarter
    gross_margin_prior: float | None = None  # Prior quarter for comparison
    net_margin: float | None = None
    net_margin_prior: float | None = None
    operating_margin: float | None = None
    operating_margin_prior: float | None = None
    # Year-over-Year changes (same quarter, prior year)
    revenue_yoy_change: float | None = None
    eps_yoy_change: float | None = None
    fcf_yoy_change: float | None = None
    capex_yoy_change: float | None = None
    gross_margin_yoy: float | None = None  # Same quarter last year
    net_margin_yoy: float | None = None
    operating_margin_yoy: float | None = None


@dataclass
class EarningsEvent:
    symbol: str
    company_name: str
    date: datetime
    time: str  # "bmo" (before market open), "amc" (after market close), or "unknown"
    eps_estimate: float | None
    revenue_estimate: float | None
    is_upcoming: bool  # True if earnings haven't happened yet
    actual_eps: float | None = None
    actual_revenue: float | None = None
    fundamental_context: FundamentalContext | None = None  # QoQ trends from Sharadar


def get_finnhub_client() -> finnhub.Client:
    """Create Finnhub client from environment."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY environment variable not set")
    return finnhub.Client(api_key=api_key)


# Sharadar uses different ticker symbols for some companies
SHARADAR_TICKER_MAP = {
    "GOOG": "GOOGL",  # Alphabet Class C -> Class A
}


def _map_to_sharadar_ticker(symbol: str) -> str:
    """Map a ticker symbol to its Sharadar equivalent."""
    return SHARADAR_TICKER_MAP.get(symbol, symbol)


def _map_from_sharadar_ticker(sharadar_ticker: str) -> str:
    """Map a Sharadar ticker back to the original symbol."""
    reverse_map = {v: k for k, v in SHARADAR_TICKER_MAP.items()}
    return reverse_map.get(sharadar_ticker, sharadar_ticker)


def _earnings_date_to_quarter_end(earnings_date: datetime) -> str:
    """Map an earnings report date to its fiscal quarter end date.

    Earnings reports come out 1-2 months after quarter end:
    - Jan-Mar earnings -> Q4 of previous year (Dec 31)
    - Apr-Jun earnings -> Q1 (Mar 31)
    - Jul-Sep earnings -> Q2 (Jun 30)
    - Oct-Dec earnings -> Q3 (Sep 30)
    """
    month = earnings_date.month
    year = earnings_date.year

    if month <= 3:  # Jan-Mar -> Q4 previous year
        return f"{year - 1}-12-31"
    elif month <= 6:  # Apr-Jun -> Q1
        return f"{year}-03-31"
    elif month <= 9:  # Jul-Sep -> Q2
        return f"{year}-06-30"
    else:  # Oct-Dec -> Q3
        return f"{year}-09-30"


def _safe_float(value) -> float | None:
    """Convert value to float, handling NaN and None."""
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN check
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _calc_pct_change(current: float | None, prior: float | None) -> float | None:
    """Calculate percentage change between two values."""
    if current is None or prior is None or prior == 0:
        return None
    return ((current - prior) / abs(prior)) * 100


def _calc_capex_change(current: float | None, prior: float | None) -> float | None:
    """Calculate CapEx percentage change using absolute values.

    CapEx is reported as negative (cash outflow), so we use absolute values.
    A larger negative = increased spending = positive growth.
    """
    if current is None or prior is None or prior == 0:
        return None
    # Use absolute values: -12B vs -10B = 20% increase in spending
    return ((abs(current) - abs(prior)) / abs(prior)) * 100


def _fetch_sharadar_actuals(symbols: list[str], earnings_dates: dict[str, datetime]) -> dict[str, dict]:
    """Fetch actual EPS, revenue, and fundamental context from Sharadar.

    Args:
        symbols: List of ticker symbols
        earnings_dates: Dict mapping symbol -> earnings report date

    Returns:
        Dict mapping symbol -> {eps, revenue, fundamental_context} or empty dict if not found
    """
    if not symbols:
        return {}

    api_key = ensure_api_key()

    # Map symbols to Sharadar tickers
    sharadar_tickers = [_map_to_sharadar_ticker(s) for s in symbols]

    # Determine date range - expand to include prior year for YoY calculations
    all_quarter_ends = [_earnings_date_to_quarter_end(dt) for dt in earnings_dates.values()]
    if not all_quarter_ends:
        return {}

    # Go back ~400 days from min date to capture same quarter from prior year
    min_date_dt = datetime.strptime(min(all_quarter_ends), "%Y-%m-%d")
    min_date = (min_date_dt - timedelta(days=400)).strftime("%Y-%m-%d")
    max_date = max(all_quarter_ends)

    # Fetch MRQ data with additional columns for fundamental context
    # Note: opmargin doesn't exist in Sharadar SF1, so we skip operating margin
    columns = ["ticker", "dimension", "calendardate", "eps", "revenueusd", "fcf", "capex", "grossmargin", "netmargin"]
    print(f"  [Sharadar] Fetching actuals for {len(symbols)} symbols...")

    try:
        df = _fetch_sf1_data(api_key, sharadar_tickers, "MRQ", columns, min_date, max_date)
    except Exception as e:
        print(f"  [Sharadar] Failed to fetch data: {e}")
        return {}

    if df.empty:
        print("  [Sharadar] No data returned")
        return {}

    # Build result dict by matching each symbol to its expected quarter
    results = {}
    for symbol in symbols:
        if symbol not in earnings_dates:
            continue

        sharadar_ticker = _map_to_sharadar_ticker(symbol)
        expected_quarter = _earnings_date_to_quarter_end(earnings_dates[symbol])
        expected_dt = datetime.strptime(expected_quarter, "%Y-%m-%d")

        # Find all rows for this ticker, sorted by date
        ticker_df = df[df["ticker"] == sharadar_ticker].sort_values("calendardate")
        if ticker_df.empty:
            continue

        # Match current quarter by calendardate
        match = ticker_df[ticker_df["calendardate"] == expected_dt]
        if match.empty:
            # Try closest date within 15 days
            ticker_df_copy = ticker_df.copy()
            ticker_df_copy["date_diff"] = abs((ticker_df_copy["calendardate"] - expected_dt).dt.days)
            close_matches = ticker_df_copy[ticker_df_copy["date_diff"] <= 15]
            if not close_matches.empty:
                match = close_matches.loc[[close_matches["date_diff"].idxmin()]]

        if match.empty:
            continue

        current = match.iloc[0]
        eps = _safe_float(current.get("eps"))
        revenue = _safe_float(current.get("revenueusd"))

        if eps is None and revenue is None:
            continue

        # Build fundamental context with QoQ and YoY changes
        fundamental_context = None
        current_date = current["calendardate"]

        # Find prior quarter (QoQ)
        prior_quarters = ticker_df[ticker_df["calendardate"] < current_date]
        prior = prior_quarters.iloc[-1] if not prior_quarters.empty else None

        # Find same quarter from prior year (YoY) - look for date ~365 days back
        prior_year_date = current_date - pd.Timedelta(days=365)
        prior_year_quarters = ticker_df[
            (ticker_df["calendardate"] >= prior_year_date - pd.Timedelta(days=30)) &
            (ticker_df["calendardate"] <= prior_year_date + pd.Timedelta(days=30))
        ]
        prior_year = prior_year_quarters.iloc[0] if not prior_year_quarters.empty else None

        if prior is not None or prior_year is not None:
            current_fcf = _safe_float(current.get("fcf"))
            current_capex = _safe_float(current.get("capex"))

            # QoQ values
            prior_eps = _safe_float(prior.get("eps")) if prior is not None else None
            prior_revenue = _safe_float(prior.get("revenueusd")) if prior is not None else None
            prior_fcf = _safe_float(prior.get("fcf")) if prior is not None else None
            prior_capex = _safe_float(prior.get("capex")) if prior is not None else None

            # YoY values (same quarter, prior year)
            yoy_eps = _safe_float(prior_year.get("eps")) if prior_year is not None else None
            yoy_revenue = _safe_float(prior_year.get("revenueusd")) if prior_year is not None else None
            yoy_fcf = _safe_float(prior_year.get("fcf")) if prior_year is not None else None
            yoy_capex = _safe_float(prior_year.get("capex")) if prior_year is not None else None

            fundamental_context = FundamentalContext(
                # QoQ changes
                revenue_qoq_change=_calc_pct_change(revenue, prior_revenue),
                eps_qoq_change=_calc_pct_change(eps, prior_eps),
                fcf=current_fcf,
                fcf_qoq_change=_calc_pct_change(current_fcf, prior_fcf),
                capex=current_capex,
                capex_qoq_change=_calc_capex_change(current_capex, prior_capex),
                gross_margin=_safe_float(current.get("grossmargin")),
                gross_margin_prior=_safe_float(prior.get("grossmargin")) if prior is not None else None,
                net_margin=_safe_float(current.get("netmargin")),
                net_margin_prior=_safe_float(prior.get("netmargin")) if prior is not None else None,
                operating_margin=None,  # opmargin not available in Sharadar SF1
                operating_margin_prior=None,
                # YoY changes
                revenue_yoy_change=_calc_pct_change(revenue, yoy_revenue),
                eps_yoy_change=_calc_pct_change(eps, yoy_eps),
                fcf_yoy_change=_calc_pct_change(current_fcf, yoy_fcf),
                capex_yoy_change=_calc_capex_change(current_capex, yoy_capex),
                gross_margin_yoy=_safe_float(prior_year.get("grossmargin")) if prior_year is not None else None,
                net_margin_yoy=_safe_float(prior_year.get("netmargin")) if prior_year is not None else None,
                operating_margin_yoy=None,
            )

        results[symbol] = {
            "eps": eps,
            "revenue": revenue,
            "quarter": str(current["calendardate"].date()),
            "fundamental_context": fundamental_context,
        }

        # Log with more detail
        rev_b = f"${revenue/1e9:.2f}B" if revenue else "N/A"
        print(f"  [Sharadar] {symbol} Q{expected_quarter}: EPS={eps}, Rev={rev_b}")
        if fundamental_context and fundamental_context.revenue_qoq_change is not None:
            print(f"    QoQ: Rev {fundamental_context.revenue_qoq_change:+.1f}%, "
                  f"EPS {fundamental_context.eps_qoq_change:+.1f}% " if fundamental_context.eps_qoq_change else "")

    return results


def _fetch_yfinance_actuals(symbols: list[str], earnings_dates: dict[str, datetime]) -> dict[str, dict]:
    """Fetch actual EPS and revenue from yfinance for given symbols.

    Args:
        symbols: List of ticker symbols
        earnings_dates: Dict mapping symbol -> earnings report date

    Returns:
        Dict mapping symbol -> {eps: float, revenue: float} or empty dict if not found
    """
    if not symbols:
        return {}

    results = {}
    print(f"  [yfinance] Fetching actuals for {len(symbols)} symbols...")

    for symbol in symbols:
        if symbol not in earnings_dates:
            continue

        try:
            ticker = yf.Ticker(symbol)
            expected_quarter = _earnings_date_to_quarter_end(earnings_dates[symbol])
            expected_dt = pd.Timestamp(expected_quarter)

            # Get quarterly income statement
            qi = ticker.quarterly_income_stmt
            if qi is None or qi.empty:
                continue

            # Find matching quarter (within 15 days tolerance)
            matched_col = None
            for col in qi.columns:
                if abs((col - expected_dt).days) <= 15:
                    matched_col = col
                    break

            if matched_col is None:
                continue

            eps = None
            revenue = None

            # Get EPS (prefer Diluted)
            if "Diluted EPS" in qi.index:
                val = qi.loc["Diluted EPS", matched_col]
                if pd.notna(val):
                    eps = float(val)
            elif "Basic EPS" in qi.index:
                val = qi.loc["Basic EPS", matched_col]
                if pd.notna(val):
                    eps = float(val)

            # Get Revenue
            if "Total Revenue" in qi.index:
                val = qi.loc["Total Revenue", matched_col]
                if pd.notna(val):
                    revenue = float(val)

            if eps is not None or revenue is not None:
                results[symbol] = {
                    "eps": eps,
                    "revenue": revenue,
                    "quarter": str(matched_col.date()),
                }
                print(f"  [yfinance] {symbol} Q{expected_quarter}: EPS={eps}, Rev={revenue}")

        except Exception as e:
            print(f"  [yfinance] {symbol}: Failed to fetch - {e}")
            continue

    return results


def get_earnings_calendar(symbols: list[str]) -> dict[str, EarningsEvent | None]:
    """Get next earnings date for each symbol.

    Uses Finnhub for calendar dates/timing/estimates, but prefers Sharadar/SF1
    for actual reported EPS and revenue. Falls back to yfinance, then Finnhub.
    """
    client = get_finnhub_client()
    today = _get_effective_today().date()
    results = {}

    # First pass: get calendar data from Finnhub
    for symbol in symbols:
        try:
            # Get earnings calendar for this symbol
            earnings = client.earnings_calendar(
                symbol=symbol,
                _from=str(today - timedelta(days=7)),  # Check recent past too
                to=str(today + timedelta(days=90))
            )

            if earnings and "earningsCalendar" in earnings:
                events_list = earnings["earningsCalendar"]
                # Log raw data for debugging earnings accuracy
                for e in events_list:
                    if e.get("epsActual") is not None or e.get("date", "") >= str(today - timedelta(days=3)):
                        print(f"  [Finnhub] {symbol} {e.get('date')}: "
                              f"EPS actual={e.get('epsActual')} est={e.get('epsEstimate')} | "
                              f"Rev actual={e.get('revenueActual')} est={e.get('revenueEstimate')}")

                # Sort events by date to ensure chronological order
                events_list = sorted(events_list, key=lambda e: e.get("date", "9999-99-99"))

                # Find the most relevant event:
                # 1. Priority: Past events with actual_eps (confirmed reported)
                # 2. Second: Past events without actual_eps (reported but results pending in API)
                # 3. Fallback: Nearest upcoming/future earnings
                reported_with_results = None
                reported_pending_results = None
                nearest_upcoming = None

                for event in events_list:
                    event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
                    actual_eps = event.get("epsActual")

                    if event_date <= today:
                        # Past or today's event
                        if actual_eps is not None:
                            # Has actual results - highest priority (keep most recent)
                            reported_with_results = event
                        else:
                            # No results yet but date has passed - second priority
                            reported_pending_results = event
                    else:
                        # Future event - track first one as fallback
                        if nearest_upcoming is None:
                            nearest_upcoming = event

                # Priority: confirmed results > pending results > upcoming
                selected_event = reported_with_results or reported_pending_results or nearest_upcoming

                if selected_event:
                    event_date = datetime.strptime(selected_event["date"], "%Y-%m-%d").date()
                    actual_eps = selected_event.get("epsActual")

                    # Consider earnings as "reported" (not upcoming) if:
                    # 1. Date is in the past, OR
                    # 2. Date is today AND actual_eps exists (results already released)
                    if event_date < today:
                        is_upcoming = False
                    elif event_date == today and actual_eps is not None:
                        is_upcoming = False  # Same-day earnings already reported
                    else:
                        is_upcoming = True

                    results[symbol] = EarningsEvent(
                        symbol=symbol,
                        company_name=selected_event.get("symbol", symbol),
                        date=datetime.strptime(selected_event["date"], "%Y-%m-%d"),
                        time=selected_event.get("hour", "unknown"),
                        eps_estimate=selected_event.get("epsEstimate"),
                        revenue_estimate=selected_event.get("revenueEstimate"),
                        is_upcoming=is_upcoming,
                        actual_eps=selected_event.get("epsActual"),
                        actual_revenue=selected_event.get("revenueActual")
                    )
            else:
                results[symbol] = None

        except Exception:
            results[symbol] = None

    # Second pass: fetch Sharadar actuals for reported earnings (more reliable)
    reported_symbols = [
        symbol for symbol, event in results.items()
        if event is not None and not event.is_upcoming
    ]

    if reported_symbols:
        # Build earnings dates dict for Sharadar lookup
        earnings_dates = {
            symbol: results[symbol].date
            for symbol in reported_symbols
        }

        sharadar_actuals = _fetch_sharadar_actuals(reported_symbols, earnings_dates)

        # Always prefer Sharadar data over Finnhub (more reliable)
        for symbol, actuals in sharadar_actuals.items():
            event = results[symbol]
            sharadar_eps = actuals.get("eps")
            sharadar_revenue = actuals.get("revenue")
            fundamental_context = actuals.get("fundamental_context")

            # Always use Sharadar EPS when available
            if sharadar_eps is not None:
                if event.actual_eps != sharadar_eps:
                    print(f"  [Hybrid] {symbol}: Using Sharadar EPS {sharadar_eps} (Finnhub had {event.actual_eps})")
                event.actual_eps = sharadar_eps

            # Always use Sharadar revenue when available
            if sharadar_revenue is not None:
                if event.actual_revenue != sharadar_revenue:
                    rev_b = sharadar_revenue / 1e9
                    finnhub_b = event.actual_revenue / 1e9 if event.actual_revenue else 0
                    print(f"  [Hybrid] {symbol}: Using Sharadar revenue ${rev_b:.2f}B (Finnhub had ${finnhub_b:.2f}B)")
                event.actual_revenue = sharadar_revenue

            # Set fundamental context for earnings analysis
            if fundamental_context is not None:
                event.fundamental_context = fundamental_context

        # Third pass: try yfinance for symbols still missing data
        symbols_needing_data = [
            symbol for symbol in reported_symbols
            if symbol not in sharadar_actuals
        ]

        if symbols_needing_data:
            yfinance_actuals = _fetch_yfinance_actuals(symbols_needing_data, earnings_dates)

            for symbol, actuals in yfinance_actuals.items():
                event = results[symbol]
                yf_eps = actuals.get("eps")
                yf_revenue = actuals.get("revenue")

                # Use yfinance values where Finnhub data is missing or unreliable
                if yf_eps is not None and event.actual_eps is None:
                    print(f"  [Hybrid] {symbol}: Using yfinance EPS {yf_eps}")
                    event.actual_eps = yf_eps

                if yf_revenue is not None:
                    # Prefer yfinance revenue over Finnhub (Finnhub often has segment data)
                    if event.actual_revenue != yf_revenue:
                        print(f"  [Hybrid] {symbol}: Using yfinance revenue {yf_revenue} (Finnhub had {event.actual_revenue})")
                    event.actual_revenue = yf_revenue

    return results


def get_upcoming_earnings(symbols: list[str], days_ahead: int = 1) -> list[EarningsEvent]:
    """Get earnings events happening within the specified days."""
    calendar = get_earnings_calendar(symbols)
    today = _get_effective_today().date()
    target_date = today + timedelta(days=days_ahead)

    upcoming = []
    for symbol, event in calendar.items():
        if event and event.is_upcoming:
            if event.date.date() <= target_date:
                upcoming.append(event)

    upcoming.sort(key=lambda x: x.date)
    return upcoming


def get_recent_earnings(symbols: list[str], days_back: int = 1) -> list[EarningsEvent]:
    """Get earnings events that happened within the specified days."""
    calendar = get_earnings_calendar(symbols)
    today = _get_effective_today().date()
    cutoff_date = today - timedelta(days=days_back)

    recent = []
    for symbol, event in calendar.items():
        if event and not event.is_upcoming:
            if event.date.date() >= cutoff_date:
                recent.append(event)

    recent.sort(key=lambda x: x.date, reverse=True)
    return recent


def format_earnings_time(time_code: str) -> str:
    """Format earnings time code for display."""
    mapping = {
        "bmo": "Before Market Open",
        "amc": "After Market Close",
        "dmh": "During Market Hours",
    }
    return mapping.get(time_code, "Time TBD")
