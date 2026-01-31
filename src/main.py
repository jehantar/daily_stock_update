#!/usr/bin/env python3
"""
Sentiment Tracker - Daily Stock Report Generator

Orchestrates the daily workflow:
1. Fetch tickers from CSV (GitHub Gist)
2. Identify >5% price movers
3. Check earnings calendar
4. Generate AI analysis
5. Send email report
"""

import sys
from datetime import datetime

from src.data_fetcher import fetch_tickers_from_gist, fetch_price_data
from src.price_analyzer import identify_movers
from src.earnings_tracker import get_upcoming_earnings, get_recent_earnings
from src.news_aggregator import aggregate_news
from src.ai_analyzer import analyze_price_movement, analyze_earnings_report
from src.email_sender import send_daily_report


def is_market_holiday() -> bool:
    """Check if today is a US market holiday."""
    # Simple weekend check - market is closed Sat/Sun
    today = datetime.now()
    if today.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return True

    # Major US market holidays (approximate - would need a proper calendar for accuracy)
    # This is a simplified check; production would use a proper market calendar API
    holidays_2026 = [
        (1, 1),   # New Year's Day
        (1, 19),  # MLK Day
        (2, 16),  # Presidents Day
        (4, 3),   # Good Friday (approximate)
        (5, 25),  # Memorial Day
        (6, 19),  # Juneteenth
        (7, 3),   # Independence Day observed
        (9, 7),   # Labor Day
        (11, 26), # Thanksgiving
        (12, 25), # Christmas
    ]

    return (today.month, today.day) in holidays_2026


def main():
    """Main entry point for daily report generation."""
    print(f"Starting Sentiment Tracker - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check for market holidays
    if is_market_holiday():
        print("Market holiday detected. Skipping report.")
        return 0

    # Step 1: Fetch ticker symbols from Gist
    print("Fetching tickers from Gist...")
    try:
        symbols = fetch_tickers_from_gist()
        print(f"Loaded {len(symbols)} ticker symbols")
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return 1

    if not symbols:
        print("No tickers found. Exiting.")
        return 0

    # Step 2: Fetch price data from Yahoo Finance
    print("Fetching price data from Yahoo Finance...")
    tickers = fetch_price_data(symbols)

    # Step 3: Identify big movers (>5%)
    print("Analyzing price movements...")
    movers = identify_movers(tickers, threshold=0.05)
    print(f"Found {len(movers)} stocks with >5% movement")

    # Step 3: Check earnings calendar
    print("Checking earnings calendar...")
    upcoming_earnings = get_upcoming_earnings(symbols, days_ahead=1)
    recent_earnings = get_recent_earnings(symbols, days_back=1)
    print(f"Upcoming earnings: {len(upcoming_earnings)}, Recent reports: {len(recent_earnings)}")

    # Step 4: Generate AI analysis for movers
    print("Generating analysis for movers...")
    analyzed_movers = []
    for mover in movers:
        news = aggregate_news(mover.symbol, mover.company_name)
        analysis = analyze_price_movement(mover, news)
        analyzed_movers.append((mover, analysis))
        print(f"  {mover.symbol}: analyzed")

    # Step 5: Generate AI summaries for recent earnings
    print("Generating earnings summaries...")
    analyzed_earnings = []
    for event in recent_earnings:
        news = aggregate_news(event.symbol, event.company_name)
        summary = analyze_earnings_report(event, news)
        analyzed_earnings.append((event, summary))
        print(f"  {event.symbol}: summarized")

    # Step 6: Send email
    print("Sending email report...")
    try:
        sent = send_daily_report(
            movers=analyzed_movers,
            upcoming_earnings=upcoming_earnings,
            recent_earnings=analyzed_earnings
        )
        if sent:
            print("Report sent successfully!")
        else:
            print("No significant events - email skipped.")
    except Exception as e:
        print(f"Error sending email: {e}")
        return 1

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
