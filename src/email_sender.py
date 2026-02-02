import os
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from src.data_fetcher import Ticker
from src.price_analyzer import PriceMover, format_change
from src.earnings_tracker import EarningsEvent, format_earnings_time
from src.chart_generator import ChartPair


def _format_market_cap(market_cap: int | None) -> str:
    """Format market cap as human-readable string (e.g., $1.2T, $580B, $45M)."""
    if market_cap is None:
        return "-"
    if market_cap >= 1e12:
        return f"${market_cap / 1e12:.1f}T"
    elif market_cap >= 1e9:
        return f"${market_cap / 1e9:.0f}B"
    elif market_cap >= 1e6:
        return f"${market_cap / 1e6:.0f}M"
    else:
        return f"${market_cap:,.0f}"


def _generate_portfolio_summary(tickers: list[Ticker]) -> str:
    """Generate portfolio summary header with key stats."""
    if not tickers:
        return ""

    total = len(tickers)
    gainers = sum(1 for t in tickers if t.daily_change > 0)
    losers = sum(1 for t in tickers if t.daily_change < 0)
    unchanged = total - gainers - losers

    avg_change = sum(t.daily_change for t in tickers) / total if total > 0 else 0

    # Find top gainer and loser
    sorted_by_change = sorted(tickers, key=lambda t: t.daily_change, reverse=True)
    top_gainer = sorted_by_change[0] if sorted_by_change else None
    top_loser = sorted_by_change[-1] if sorted_by_change else None

    top_line = []
    if top_gainer and top_gainer.daily_change > 0:
        top_line.append(f"Top: {top_gainer.symbol} {format_change(top_gainer.daily_change)}")
    if top_loser and top_loser.daily_change < 0:
        top_line.append(f"Bottom: {top_loser.symbol} {format_change(top_loser.daily_change)}")

    top_str = " | ".join(top_line) if top_line else ""

    return f"""
<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px;">
    <p style="margin: 0 0 4px 0; font-size: 14px; color: #64748b;">Portfolio Summary</p>
    <p style="margin: 0; font-size: 15px;">
        <strong>{total} stocks</strong> |
        <span style="color: #16a34a;">{gainers} up</span>,
        <span style="color: #dc2626;">{losers} down</span>{f", {unchanged} flat" if unchanged else ""} |
        Avg: <strong>{format_change(avg_change)}</strong>
    </p>
    {f'<p style="margin: 4px 0 0 0; font-size: 13px; color: #475569;">{top_str}</p>' if top_str else ""}
</div>
"""


def _get_custom_category(symbol: str) -> str:
    """Map ticker symbol to custom category."""
    CATEGORIES = {
        # Platform Technology & Digital Ecosystems
        "META": "Platform Technology & Digital Ecosystems",
        "GOOGL": "Platform Technology & Digital Ecosystems",
        "GOOG": "Platform Technology & Digital Ecosystems",
        "MSFT": "Platform Technology & Digital Ecosystems",
        "AMZN": "Platform Technology & Digital Ecosystems",
        "NFLX": "Platform Technology & Digital Ecosystems",
        # Semiconductors, Hardware & Digital Infrastructure
        "NVDA": "Semiconductors, Hardware & Digital Infrastructure",
        "AVGO": "Semiconductors, Hardware & Digital Infrastructure",
        "TSM": "Semiconductors, Hardware & Digital Infrastructure",
        "MU": "Semiconductors, Hardware & Digital Infrastructure",
        "WDC": "Semiconductors, Hardware & Digital Infrastructure",
        "CLS": "Semiconductors, Hardware & Digital Infrastructure",
        # Enterprise, Security & GovTech Software
        "CRWD": "Enterprise, Security & GovTech Software",
        "NET": "Enterprise, Security & GovTech Software",
        "AXON": "Enterprise, Security & GovTech Software",
        "APP": "Enterprise, Security & GovTech Software",
        # Commerce, Marketplaces & Consumer Logistics
        "MELI": "Commerce, Marketplaces & Consumer Logistics",
        "UBER": "Commerce, Marketplaces & Consumer Logistics",
        "WMT": "Commerce, Marketplaces & Consumer Logistics",
        "BABA": "Commerce, Marketplaces & Consumer Logistics",
        # Financials & Assets
        "AMG": "Financials & Assets",
        "B": "Financials & Assets",
        # Resources, Materials & Life Sciences
        "EQX": "Resources, Materials & Life Sciences",
        "HL": "Resources, Materials & Life Sciences",
        "NGD": "Resources, Materials & Life Sciences",
        "KRYS": "Resources, Materials & Life Sciences",
        "MEDP": "Resources, Materials & Life Sciences",
    }
    return CATEGORIES.get(symbol.upper(), "Other")


# Category display order
CATEGORY_ORDER = [
    "Platform Technology & Digital Ecosystems",
    "Semiconductors, Hardware & Digital Infrastructure",
    "Enterprise, Security & GovTech Software",
    "Commerce, Marketplaces & Consumer Logistics",
    "Financials & Assets",
    "Resources, Materials & Life Sciences",
    "Other",
]


def _generate_valuation_table(tickers: list[Ticker]) -> str:
    """Generate valuation snapshot table for all stocks, grouped by custom categories."""
    if not tickers:
        return ""

    # Group tickers by custom category
    from collections import defaultdict
    categories: dict[str, list[Ticker]] = defaultdict(list)
    for t in tickers:
        category = _get_custom_category(t.symbol)
        categories[category].append(t)

    # Use predefined category order
    sorted_categories = [c for c in CATEGORY_ORDER if c in categories]

    rows = []
    for category in sorted_categories:
        category_tickers = categories[category]
        # Sort tickers within category alphabetically
        category_tickers.sort(key=lambda t: t.symbol)

        # Category header row
        rows.append(f"""
<tr style="background: #e2e8f0;">
    <td colspan="6" style="padding: 8px; font-weight: bold; color: #475569;">{category}</td>
</tr>""")

        for t in sector_tickers:
            change_str = format_change(t.daily_change)
            change_color = "#16a34a" if t.daily_change > 0 else "#dc2626" if t.daily_change < 0 else "#666"
            pe_str = f"{t.trailing_pe:.1f}" if t.trailing_pe else "-"
            fwd_pe_str = f"{t.forward_pe:.1f}" if t.forward_pe else "-"
            yield_str = f"{t.dividend_yield * 100:.1f}%" if t.dividend_yield else "-"
            cap_str = _format_market_cap(t.market_cap)

            rows.append(f"""
<tr style="border-bottom: 1px solid #eee;">
    <td style="padding: 6px 8px;"><strong>{t.symbol}</strong></td>
    <td style="padding: 6px 8px; text-align: right; color: {change_color};">{change_str}</td>
    <td style="padding: 6px 8px; text-align: right;">{pe_str}</td>
    <td style="padding: 6px 8px; text-align: right;">{fwd_pe_str}</td>
    <td style="padding: 6px 8px; text-align: right;">{yield_str}</td>
    <td style="padding: 6px 8px; text-align: right;">{cap_str}</td>
</tr>""")

    return f"""
<h3>Valuation Snapshot</h3>
<table style="width: 100%; border-collapse: collapse; font-size: 14px;">
<tr style="background: #f5f5f5; text-align: left;">
    <th style="padding: 8px; border-bottom: 1px solid #ddd;">Ticker</th>
    <th style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">Daily</th>
    <th style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">P/E</th>
    <th style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">Fwd P/E</th>
    <th style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">Yield</th>
    <th style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">Mkt Cap</th>
</tr>
{"".join(rows)}
</table>
<hr>
"""


def _generate_fundamentals_section(charts: dict[str, ChartPair]) -> str:
    """Generate HTML section with fundamental metrics charts using CID references."""
    if not charts:
        return ""

    html_parts = ['<h3>Fundamental Trends</h3>']

    for ticker in sorted(charts.keys()):
        chart_pair = charts[ticker]
        growth_cid = f"growth_{ticker.lower()}"
        profit_cid = f"profit_{ticker.lower()}"

        html_parts.append(f"""
<div style="margin-bottom: 24px;">
    <h4 style="color: #2563eb; margin-bottom: 8px; margin-top: 16px;">{chart_pair.ticker} - {chart_pair.company_name}</h4>
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="width: 50%; padding: 4px; vertical-align: top;">
                <img src="cid:{growth_cid}"
                     alt="{chart_pair.ticker} Growth Metrics"
                     style="width: 100%; max-width: 350px; height: auto;" />
                <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">Growth (QoQ %): Revenue, EPS, FCF</p>
            </td>
            <td style="width: 50%; padding: 4px; vertical-align: top;">
                <img src="cid:{profit_cid}"
                     alt="{chart_pair.ticker} Profitability Metrics"
                     style="width: 100%; max-width: 350px; height: auto;" />
                <p style="font-size: 11px; color: #666; margin: 4px 0 0 0;">Profitability (%): ROE, ROA, Margins</p>
            </td>
        </tr>
    </table>
</div>
<hr>
""")

    return "\n".join(html_parts)


def _attach_chart_images(msg: MIMEMultipart, charts: dict[str, ChartPair]) -> None:
    """Attach chart images with Content-ID headers for inline display."""
    for ticker in sorted(charts.keys()):
        chart_pair = charts[ticker]

        # Growth chart
        growth_cid = f"growth_{ticker.lower()}"
        growth_data = base64.b64decode(chart_pair.growth_chart_base64)
        growth_img = MIMEImage(growth_data, _subtype='png')
        growth_img.add_header('Content-ID', f'<{growth_cid}>')
        growth_img.add_header('Content-Disposition', 'inline', filename=f'{ticker}_growth.png')
        msg.attach(growth_img)

        # Profitability chart
        profit_cid = f"profit_{ticker.lower()}"
        profit_data = base64.b64decode(chart_pair.profitability_chart_base64)
        profit_img = MIMEImage(profit_data, _subtype='png')
        profit_img.add_header('Content-ID', f'<{profit_cid}>')
        profit_img.add_header('Content-Disposition', 'inline', filename=f'{ticker}_profitability.png')
        msg.attach(profit_img)


def send_daily_report(
    movers: list[tuple[PriceMover, str]],  # (mover, analysis)
    upcoming_earnings: list[EarningsEvent],
    recent_earnings: list[tuple[EarningsEvent, str]],  # (event, summary)
    all_earnings: dict[str, EarningsEvent | None] = None,  # Full earnings calendar
    fundamental_charts: dict[str, ChartPair] = None,  # Fundamental metrics charts
    tickers: list[Ticker] = None,  # All tickers for portfolio summary
) -> bool:
    """Send the daily report email. Returns True if sent successfully."""

    # Check if there's anything to report
    if not movers and not upcoming_earnings and not recent_earnings and not all_earnings:
        print("No significant events to report. Skipping email.")
        return False

    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        raise ValueError("Gmail credentials not set in environment")

    subject = generate_subject(movers, upcoming_earnings, recent_earnings)
    html_body = generate_html_body(movers, upcoming_earnings, recent_earnings, all_earnings, fundamental_charts, tickers)

    # Use "related" for HTML with embedded images, otherwise "alternative"
    if fundamental_charts:
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = gmail_address
        msg["To"] = gmail_address

        # HTML goes in a nested alternative part
        msg_alt = MIMEMultipart("alternative")
        msg_alt.attach(MIMEText(html_body, "html"))
        msg.attach(msg_alt)

        # Attach chart images with CID references
        _attach_chart_images(msg, fundamental_charts)
    else:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_address
        msg["To"] = gmail_address
        msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        print(f"Email sent successfully: {subject}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise


def generate_subject(
    movers: list[tuple[PriceMover, str]],
    upcoming_earnings: list[EarningsEvent],
    recent_earnings: list[tuple[EarningsEvent, str]],
) -> str:
    """Generate alert-style subject line."""
    today = datetime.now().strftime("%b %d, %Y")
    parts = []

    # Add top mover
    if movers:
        top_mover = movers[0][0]
        change = format_change(top_mover.daily_change)
        parts.append(f"{top_mover.symbol} {change}")

    # Add upcoming earnings
    if upcoming_earnings:
        event = upcoming_earnings[0]
        parts.append(f"{event.symbol} earnings tomorrow")

    # Add recent earnings
    if recent_earnings and not parts:
        event = recent_earnings[0][0]
        parts.append(f"{event.symbol} reported earnings")

    action_text = ", ".join(parts[:2]) if parts else "Portfolio Update"
    return f"[ACTION] {action_text} | {today}"


def generate_html_body(
    movers: list[tuple[PriceMover, str]],
    upcoming_earnings: list[EarningsEvent],
    recent_earnings: list[tuple[EarningsEvent, str]],
    all_earnings: dict[str, EarningsEvent | None] = None,
    fundamental_charts: dict[str, ChartPair] = None,
    tickers: list[Ticker] = None,
) -> str:
    """Generate minimal HTML email body."""
    today = datetime.now().strftime("%B %d, %Y")

    sections = [f"<h2>Daily Stock Report - {today}</h2>"]

    # Portfolio Summary (at top)
    if tickers:
        sections.append(_generate_portfolio_summary(tickers))

    # Build ticker lookup for 52-week context
    ticker_lookup = {t.symbol: t for t in tickers} if tickers else {}

    # Big Movers Section
    if movers:
        sections.append("<h3>Big Movers (>5%)</h3>")

    for mover, analysis in movers:
        change = format_change(mover.daily_change)
        color = "#16a34a" if mover.daily_change > 0 else "#dc2626"
        arrow = "UP" if mover.daily_change > 0 else "DOWN"

        extended_note = ""
        if mover.extended_hours_change:
            ext_change = format_change(mover.extended_hours_change)
            extended_note = f" (Extended hours: {ext_change})"

        # 52-week context
        week_52_note = ""
        t = ticker_lookup.get(mover.symbol)
        if t and t.current_price and t.fifty_two_week_high and t.fifty_two_week_low:
            if t.current_price < t.fifty_two_week_high:
                pct_below = (t.fifty_two_week_high - t.current_price) / t.fifty_two_week_high
                week_52_note = f'<p style="color: #64748b; font-size: 13px; margin: 4px 0;">{pct_below*100:.0f}% below 52-week high (${t.fifty_two_week_high:.2f})</p>'
            elif t.current_price > t.fifty_two_week_low:
                pct_above = (t.current_price - t.fifty_two_week_low) / t.fifty_two_week_low
                if pct_above < 0.1:  # Near 52-week low
                    week_52_note = f'<p style="color: #64748b; font-size: 13px; margin: 4px 0;">Near 52-week low (${t.fifty_two_week_low:.2f})</p>'

        sections.append(f"""
<h4 style="color: #2563eb; margin-bottom: 4px;">{mover.symbol} - {mover.company_name}</h4>
<p><strong style="color: {color};">{arrow} {change}</strong>{extended_note}</p>
{week_52_note}<p><strong>Why it moved:</strong> {analysis}</p>
<hr>
""")

    # Valuation Snapshot Table (all stocks, grouped by sector)
    if tickers:
        sections.append(_generate_valuation_table(tickers))

    # Upcoming Earnings Section
    for event in upcoming_earnings:
        time_str = format_earnings_time(event.time)
        date_str = event.date.strftime("%B %d, %Y")

        estimates = []
        if event.eps_estimate:
            estimates.append(f"EPS: ${event.eps_estimate:.2f}")
        if event.revenue_estimate:
            rev_b = event.revenue_estimate / 1e9
            estimates.append(f"Revenue: ${rev_b:.1f}B")
        estimate_str = " | ".join(estimates) if estimates else "Estimates not available"

        sections.append(f"""
<h3>{event.symbol} - {event.company_name}</h3>
<p><strong>Earnings Tomorrow</strong> - {date_str} ({time_str})</p>
<p>Expected: {estimate_str}</p>
<hr>
""")

    # Recent Earnings Section
    for event, summary in recent_earnings:
        date_str = event.date.strftime("%B %d, %Y")

        results = []
        if event.actual_eps and event.eps_estimate:
            diff = "beat" if event.actual_eps > event.eps_estimate else "missed"
            results.append(f"EPS: ${event.actual_eps:.2f} ({diff} ${event.eps_estimate:.2f})")
        if event.actual_revenue and event.revenue_estimate:
            diff = "beat" if event.actual_revenue > event.revenue_estimate else "missed"
            actual_b = event.actual_revenue / 1e9
            est_b = event.revenue_estimate / 1e9
            results.append(f"Revenue: ${actual_b:.1f}B ({diff} ${est_b:.1f}B)")
        results_str = " | ".join(results) if results else ""

        sections.append(f"""
<h3>{event.symbol} - {event.company_name}</h3>
<p><strong>Earnings Report</strong> (Reported: {date_str})</p>
{"<p><strong>Results:</strong> " + results_str + "</p>" if results_str else ""}
<p><strong>Summary:</strong> {summary}</p>
<hr>
""")

    # Earnings Calendar Section (all tickers)
    if all_earnings:
        # Sort by date, with stocks that have earnings dates first
        sorted_earnings = sorted(
            all_earnings.items(),
            key=lambda x: (x[1].date if x[1] else datetime.max, x[0])
        )

        calendar_rows = []
        for symbol, event in sorted_earnings:
            if event and event.is_upcoming:
                date_str = event.date.strftime("%b %d, %Y")
                time_str = format_earnings_time(event.time)
                calendar_rows.append(f"<tr><td><strong>{symbol}</strong></td><td>{date_str}</td><td>{time_str}</td></tr>")
            else:
                calendar_rows.append(f"<tr><td><strong>{symbol}</strong></td><td colspan='2' style='color: #999;'>Not scheduled</td></tr>")

        if calendar_rows:
            # Add padding to each row
            styled_rows = [row.replace("<tr>", "<tr style='border-bottom: 1px solid #eee;'>").replace("<td>", "<td style='padding: 6px 8px;'>") for row in calendar_rows]
            sections.append(f"""
<h3>Upcoming Earnings Calendar</h3>
<table style="width: 100%; border-collapse: collapse; font-size: 14px;">
<tr style="background: #f5f5f5; text-align: left;">
    <th style="padding: 8px; border-bottom: 1px solid #ddd;">Ticker</th>
    <th style="padding: 8px; border-bottom: 1px solid #ddd;">Date</th>
    <th style="padding: 8px; border-bottom: 1px solid #ddd;">Time</th>
</tr>
{"".join(styled_rows)}
</table>
""")

    # Fundamental Trends Section
    if fundamental_charts:
        sections.append(_generate_fundamentals_section(fundamental_charts))

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: #333; max-width: 600px; }}
        h2 {{ color: #1a1a1a; border-bottom: 2px solid #e5e5e5; padding-bottom: 8px; }}
        h3 {{ color: #2563eb; margin-bottom: 4px; }}
        hr {{ border: none; border-top: 1px solid #e5e5e5; margin: 16px 0; }}
        p {{ margin: 8px 0; }}
    </style>
</head>
<body>
{"".join(sections)}
<p style="color: #666; font-size: 12px; margin-top: 24px;">
Generated by Sentiment Tracker
</p>
</body>
</html>
"""
