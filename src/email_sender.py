import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from src.price_analyzer import PriceMover, format_change
from src.earnings_tracker import EarningsEvent, format_earnings_time


def send_daily_report(
    movers: list[tuple[PriceMover, str]],  # (mover, analysis)
    upcoming_earnings: list[EarningsEvent],
    recent_earnings: list[tuple[EarningsEvent, str]],  # (event, summary)
    all_earnings: dict[str, EarningsEvent | None] = None,  # Full earnings calendar
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
    html_body = generate_html_body(movers, upcoming_earnings, recent_earnings, all_earnings)

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
) -> str:
    """Generate minimal HTML email body."""
    today = datetime.now().strftime("%B %d, %Y")

    sections = [f"<h2>Daily Stock Report - {today}</h2>"]

    # Big Movers Section
    for mover, analysis in movers:
        change = format_change(mover.daily_change)
        color = "#16a34a" if mover.daily_change > 0 else "#dc2626"
        arrow = "UP" if mover.daily_change > 0 else "DOWN"

        extended_note = ""
        if mover.extended_hours_change:
            ext_change = format_change(mover.extended_hours_change)
            extended_note = f" (Extended hours: {ext_change})"

        sections.append(f"""
<h3>{mover.symbol} - {mover.company_name}</h3>
<p><strong style="color: {color};">{arrow} {change}</strong>{extended_note}</p>
<p><strong>Why it moved:</strong> {analysis}</p>
<hr>
""")

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
