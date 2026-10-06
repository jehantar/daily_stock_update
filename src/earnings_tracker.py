import os
from datetime import datetime, timedelta
import math
from dataclasses import dataclass
import finnhub
import yfinance as yf


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
    """QoQ and YoY fundamental trends for earnings analysis."""
    revenue: float | None = None
    eps: float | None = None
    financial_currency: str | None = None
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
    fundamental_context: FundamentalContext | None = None


def get_finnhub_client() -> finnhub.Client:
    """Create Finnhub client from environment."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY environment variable not set")
    return finnhub.Client(api_key=api_key)


def _finite_float(value) -> float | None:
    """Return a finite number, or None for missing/invalid values."""
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _calendar_date(value):
    """Return the date shown by Yahoo, preserving the timestamp's own timezone."""
    if hasattr(value, "date"):
        return value.date()
    return datetime.fromisoformat(str(value)).date()


def _fetch_yahoo_earnings_event(symbol: str) -> EarningsEvent | None:
    """Fetch one best-effort earnings date when Finnhub has no reported event."""
    today = _get_effective_today().date()
    # The report only includes earnings from the last two days. Older Yahoo
    # dates must not displace an imminent Finnhub reminder.
    cutoff = today - timedelta(days=2)
    try:
        dates = yf.Ticker(symbol).get_earnings_dates(limit=4)
        if dates is None or dates.empty:
            return None

        candidates = []
        for date_value, row in dates.iterrows():
            event_date = _calendar_date(date_value)
            reported_eps = _finite_float(row.get("Reported EPS"))
            if cutoff <= event_date <= today or event_date > today:
                candidates.append((event_date, reported_eps))

        if not candidates:
            return None

        recent_reported = [
            (date, eps) for date, eps in candidates
            if date < today or (date == today and eps is not None)
        ]
        if recent_reported:
            event_date, actual_eps = max(recent_reported, key=lambda event: event[0])
            is_upcoming = False
        else:
            # A same-day row without Reported EPS remains pending. Otherwise,
            # use the nearest future earnings date.
            same_day_pending = [(date, eps) for date, eps in candidates if date == today]
            event_date, actual_eps = same_day_pending[0] if same_day_pending else min(candidates, key=lambda event: event[0])
            is_upcoming = True

        return EarningsEvent(
            symbol=symbol,
            company_name=symbol,
            date=datetime.combine(event_date, datetime.min.time()),
            time="unknown",
            eps_estimate=None,
            revenue_estimate=None,
            is_upcoming=is_upcoming,
            actual_eps=actual_eps if not is_upcoming else None,
            actual_revenue=None,
        )
    except Exception as exc:
        print(f"  [Yahoo] Unable to get earnings date for {symbol}: {exc}")
        return None


def get_earnings_calendar(symbols: list[str]) -> dict[str, EarningsEvent | None]:
    """Get Finnhub earnings dates, with Yahoo as a best-effort date fallback."""
    client = get_finnhub_client()
    today = _get_effective_today().date()
    results = {}

    # Finnhub supplies event dates, timing, estimates, and paired actuals.
    for symbol in symbols:
        try:
            earnings = client.earnings_calendar(
                symbol=symbol,
                _from=str(today - timedelta(days=7)),
                to=str(today + timedelta(days=90)),
            )
            events_list = earnings.get("earningsCalendar", []) if earnings else []
            for event in events_list:
                if event.get("epsActual") is not None or event.get("date", "") >= str(today - timedelta(days=3)):
                    print(f"  [Finnhub] {symbol} {event.get('date')}: "
                          f"EPS actual={event.get('epsActual')} est={event.get('epsEstimate')} | "
                          f"Rev actual={event.get('revenueActual')} est={event.get('revenueEstimate')}")

            events_list = sorted(events_list, key=lambda event: event.get("date", "9999-99-99"))
            reported_with_results = None
            reported_pending_results = None
            nearest_upcoming = None
            for event in events_list:
                event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
                if event_date <= today:
                    if event.get("epsActual") is not None:
                        reported_with_results = event
                    else:
                        reported_pending_results = event
                elif nearest_upcoming is None:
                    nearest_upcoming = event

            selected_event = reported_with_results or reported_pending_results or nearest_upcoming
            if not selected_event:
                results[symbol] = None
                continue

            event_date = datetime.strptime(selected_event["date"], "%Y-%m-%d").date()
            actual_eps = selected_event.get("epsActual")
            is_upcoming = not (event_date < today or (event_date == today and actual_eps is not None))
            results[symbol] = EarningsEvent(
                symbol=symbol,
                company_name=selected_event.get("symbol", symbol),
                date=datetime.strptime(selected_event["date"], "%Y-%m-%d"),
                time=selected_event.get("hour", "unknown"),
                eps_estimate=selected_event.get("epsEstimate"),
                revenue_estimate=selected_event.get("revenueEstimate"),
                is_upcoming=is_upcoming,
                actual_eps=selected_event.get("epsActual"),
                actual_revenue=selected_event.get("revenueActual"),
            )
        except Exception:
            results[symbol] = None

    # Yahoo is queried once per ticker only when Finnhub has no event or only
    # an upcoming event. It supplies dates and reported EPS status, not revenue.
    for symbol in symbols:
        existing = results.get(symbol)
        has_finnhub_actuals = existing is not None and (
            existing.actual_eps is not None or existing.actual_revenue is not None
        )
        if (existing is None or existing.is_upcoming) and not has_finnhub_actuals:
            yahoo_event = _fetch_yahoo_earnings_event(symbol)
            if yahoo_event is not None and (existing is None or not yahoo_event.is_upcoming):
                print(f"  [Yahoo] {symbol}: using earnings date {yahoo_event.date.date()}")
                results[symbol] = yahoo_event

    return results


def get_upcoming_earnings(
    symbols: list[str],
    days_ahead: int = 1,
    calendar: dict[str, EarningsEvent | None] | None = None,
) -> list[EarningsEvent]:
    """Get earnings events happening within the specified days."""
    if calendar is None:
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


def get_recent_earnings(
    symbols: list[str],
    days_back: int = 1,
    calendar: dict[str, EarningsEvent | None] | None = None,
) -> list[EarningsEvent]:
    """Get earnings events that happened within the specified days."""
    if calendar is None:
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
