# Sentiment Tracker

Automated daily stock monitoring that delivers AI-analyzed insights via email.

## Features

- **Big Movers Alert**: Stocks with >3% daily change, with AI-synthesized explanation
- **Valuation Snapshot**: Table with P/E, Fwd P/E, P/CF, Dividend Yield, and Market Cap for all tickers
- **Earnings Calendar**: Reminder 1 day before scheduled earnings calls
- **Earnings Summaries**: Key insights from recent earnings reports
- **Fundamental Trends**: Quarterly line charts showing growth and profitability metrics
- **Full Earnings Calendar**: Table showing next earnings date for all tracked tickers

## Quick Start

### 1. Create Your Ticker List

Create a CSV with your stock tickers. The system reads tickers from column C (index 2).

### 2. Create a GitHub Gist

1. Go to [gist.github.com](https://gist.github.com)
2. Create a **secret gist** with your CSV content
3. Copy the raw gist URL

### 3. Get API Keys

#### Gmail App Password
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication
3. Go to Security → 2-Step Verification → App Passwords
4. Generate password for "Mail"
5. Save the 16-character password

#### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create new API key

#### Finnhub API Key
1. Register at [finnhub.io](https://finnhub.io/register)
2. Copy API key from dashboard

### 4. Configure GitHub Secrets

1. Create a new GitHub repository
2. Push this code to the repository
3. Go to Settings → Secrets and variables → Actions
4. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GIST_URL` | Your gist raw URL |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | The 16-character app password |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `FINNHUB_API_KEY` | Your Finnhub API key |

### 5. Enable GitHub Actions

The workflow is triggered on weekdays by the configured external scheduler. It can also be run manually.

To test manually:
1. Go to Actions tab
2. Select "Daily Stock Report"
3. Click "Run workflow"

## Email Preview

Subject: `[ACTION] TSLA -8%, NVDA earnings tomorrow | Jan 30, 2026`

The email includes:
- Price change with direction indicator
- Extended hours movement (if available)
- AI analysis of why it moved
- Valuation snapshot (P/E, Fwd P/E, P/CF, Yield, Mkt Cap)
- Upcoming earnings alerts
- Post-earnings summaries
- Earnings calendar for all tickers
- Fundamental trend charts (Growth & Profitability)

## Fundamental Trends Charts

Stocks with a recent earnings report can include two charts with up to 6 quarters of Yahoo Finance statement history:

**Growth Chart**
- Quarterly revenue, EBITDA, and EPS in the company's reporting currency
- Revenue and EPS year-over-year changes where history is available

**Profitability Chart**
- Return on Equity (ROE %)
- Return on Assets (ROA %)
- Gross Margin %
- Net Margin %
- Operating Margin % where available

Missing statement fields are left blank. Charts include smart axis scaling - extreme outliers are capped with annotations showing actual values.

Finnhub supplies earnings dates, estimates, and reported actuals. Yahoo Finance supplies the quarterly statements used for charts and trend notes. The report keeps those sources separate when it compares actuals with estimates, since statement currency and share basis can differ. Yahoo earnings dates may flag a recent report missing from Finnhub, but this is a best-effort check. Yahoo Finance data comes through an unofficial interface, so statement coverage and timing can vary.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GIST_URL="https://gist.githubusercontent.com/..."
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export OPENAI_API_KEY="sk-..."
export FINNHUB_API_KEY="..."

# Run
python src/main.py
```

## Project Structure

```
sentiment_tracker/
├── .github/workflows/daily_report.yml
├── src/
│   ├── main.py               # Entry point
│   ├── data_fetcher.py       # CSV/Gist fetching, Yahoo Finance prices
│   ├── price_analyzer.py     # >3% movement detection
│   ├── earnings_tracker.py   # Finnhub earnings calendar
│   ├── news_aggregator.py    # Multi-source news
│   ├── ai_analyzer.py        # OpenAI gpt-5-mini integration
│   ├── fundamentals_fetcher.py  # Yahoo Finance quarterly statements
│   ├── chart_generator.py    # matplotlib line charts
│   └── email_sender.py       # Gmail SMTP with embedded images
├── requirements.txt
├── SPEC.md                   # Full specification
└── README.md
```

## Troubleshooting

**Email not sending?**
- Verify Gmail App Password (not your regular password)
- Check 2FA is enabled on your Google account
- Look at GitHub Actions logs for errors

**No analysis appearing?**
- Check OpenAI API key is valid
- Verify you have API credits available

**Missing earnings data?**
- Finnhub free tier has rate limits
- Some smaller stocks may not have earnings calendar data

**Charts not rendering?**
- Yahoo Finance may not have current quarterly statements for every stock
- Charts require at least 2 quarters of data and a statement matching the recent report

**Charts showing broken images?**
- Gmail blocks data URIs; we use CID attachments which should work
- Try viewing the email in a different client
