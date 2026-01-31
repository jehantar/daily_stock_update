#!/usr/bin/env python3
"""
Sentiment Tracker - Daily Stock Report Generator

Orchestrates the daily workflow:
1. Fetch tickers from CSV (GitHub Gist)
2. Fetch price data from Yahoo Finance
3. Identify >5% price movers
4. Fetch fundamentals and generate charts
5. Check earnings calendar
6. Generate AI analysis for movers
7. Generate AI summaries for earnings
8. Send email report
"""

import sys
from datetime import datetime

from src.data_fetcher import fetch_tickers_from_gist, fetch_price_data
from src.price_analyzer import identify_movers
from src.earnings_tracker import get_upcoming_earnings, get_recent_earnings, get_earnings_calendar
from src.news_aggregator import aggregate_news
from src.ai_analyzer import analyze_price_movement, analyze_earnings_report
from src.email_sender import send_daily_report
from src.fundamentals_fetcher import fetch_fundamentals
from src.chart_generator import generate_all_charts


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

    # Build company names dict for later use
    company_names = {t.symbol: t.company_name for t in tickers}

    # Step 3: Identify big movers (>5%)
    print("Analyzing price movements...")
    movers = identify_movers(tickers, threshold=0.05)
    print(f"Found {len(movers)} stocks with >5% movement")

    # Step 4: Fetch fundamental data and generate charts
    print("Fetching fundamental data from Nasdaq Data Link...")
    fundamental_charts = {}
    try:
        fundamentals = fetch_fundamentals(symbols, company_names, quarters=6)
        print(f"  Retrieved fundamentals for {len(fundamentals)} tickers")

        print("Generating fundamental charts...")
        fundamental_charts = generate_all_charts(fundamentals)
        print(f"  Generated {len(fundamental_charts)} chart pairs")
    except Exception as e:
        print(f"  Warning: Failed to fetch/generate fundamentals: {e}")
        print("  Continuing without fundamentals section...")

    # Step 5: Check earnings calendar
    print("Checking earnings calendar...")
    all_earnings = get_earnings_calendar(symbols)
    upcoming_earnings = get_upcoming_earnings(symbols, days_ahead=1)
    recent_earnings = get_recent_earnings(symbols, days_back=1)
    earnings_with_dates = sum(1 for e in all_earnings.values() if e and e.is_upcoming)
    print(f"Upcoming earnings: {len(upcoming_earnings)}, Recent reports: {len(recent_earnings)}, Scheduled: {earnings_with_dates}")

    # Step 6: Generate AI analysis for movers
    print("Generating analysis for movers...")
    analyzed_movers = []
    for mover in movers:
        news = aggregate_news(mover.symbol, mover.company_name)
        analysis = analyze_price_movement(mover, news)
        analyzed_movers.append((mover, analysis))
        print(f"  {mover.symbol}: analyzed")

    # Step 7: Generate AI summaries for recent earnings
    print("Generating earnings summaries...")
    analyzed_earnings = []
    for event in recent_earnings:
        news = aggregate_news(event.symbol, event.company_name)
        summary = analyze_earnings_report(event, news)
        analyzed_earnings.append((event, summary))
        print(f"  {event.symbol}: summarized")

    # Step 8: Send email
    print("Sending email report...")
    try:
        sent = send_daily_report(
            movers=analyzed_movers,
            upcoming_earnings=upcoming_earnings,
            recent_earnings=analyzed_earnings,
            all_earnings=all_earnings,
            fundamental_charts=fundamental_charts,
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
