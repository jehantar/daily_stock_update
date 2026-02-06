import os
from datetime import datetime, timedelta
from dataclasses import dataclass
import finnhub


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


def get_finnhub_client() -> finnhub.Client:
    """Create Finnhub client from environment."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY environment variable not set")
    return finnhub.Client(api_key=api_key)


def get_earnings_calendar(symbols: list[str]) -> dict[str, EarningsEvent | None]:
    """Get next earnings date for each symbol."""
    client = get_finnhub_client()
    today = datetime.now().date()
    results = {}

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

                # Sort events by date to ensure chronological order
                events_list = sorted(events_list, key=lambda e: e.get("date", "9999-99-99"))

                # Find the most relevant event:
                # 1. Priority: Recently reported earnings (with actual_eps, within past 7 days)
                # 2. Fallback: Nearest upcoming/future earnings
                best_event = None
                nearest_upcoming = None

                for event in events_list:
                    event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
                    actual_eps = event.get("epsActual")

                    # Check if this is a recently reported earnings (with actual results)
                    if actual_eps is not None and event_date <= today:
                        # Reported earnings takes priority - use the most recent one
                        best_event = event

                    # Track the nearest upcoming/future event as fallback
                    if nearest_upcoming is None and event_date >= today and event.get("epsActual") is None:
                        nearest_upcoming = event

                # Use reported earnings if found, otherwise use nearest upcoming
                selected_event = best_event if best_event else nearest_upcoming

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

    return results


def get_upcoming_earnings(symbols: list[str], days_ahead: int = 1) -> list[EarningsEvent]:
    """Get earnings events happening within the specified days."""
    calendar = get_earnings_calendar(symbols)
    today = datetime.now().date()
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
    today = datetime.now().date()
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
