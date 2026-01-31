# Sentiment Tracker

Automated daily stock monitoring that delivers AI-analyzed insights via email.

## Features

- **Big Movers Alert**: Stocks with >5% daily change, with AI-synthesized explanation
- **Earnings Calendar**: Reminder 1 day before scheduled earnings calls
- **Earnings Summaries**: Key insights from recent earnings reports

## Quick Start

### 1. Create Your Ticker CSV

Export your Google Sheet tab to CSV with these columns:
- `Ticker` (required): Stock symbol (e.g., AAPL)
- `Daily Price Change` (required): Percentage as decimal or with % sign

### 2. Create a GitHub Gist

1. Go to [gist.github.com](https://gist.github.com)
2. Create a **secret gist** with your CSV content
3. Copy the gist URL

### 3. Get API Keys

#### Gmail App Password
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication
3. Go to Security → 2-Step Verification → App Passwords
4. Generate password for "Mail"
5. Save the 16-character password

#### Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
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
| `GIST_URL` | Your gist URL (e.g., `https://gist.github.com/username/abc123`) |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | The 16-character app password |
| `GEMINI_API_KEY` | Your Gemini API key |
| `FINNHUB_API_KEY` | Your Finnhub API key |

### 5. Enable GitHub Actions

The workflow runs automatically at 2 PM Pacific on weekdays.

To test manually:
1. Go to Actions tab
2. Select "Daily Stock Report"
3. Click "Run workflow"

## CSV Format Example

```csv
Ticker,Daily Price Change,YTD Price Change
AAPL,-0.02,0.15
GOOGL,0.07,0.22
TSLA,-0.08,0.05
NVDA,0.03,0.45
```

## Email Preview

Subject: `[ACTION] TSLA -8%, NVDA earnings tomorrow | Jan 30, 2026`

The email groups all info by ticker:
- Price change with direction indicator
- Extended hours movement (if available)
- AI analysis of why it moved
- Upcoming earnings alerts
- Post-earnings summaries

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GIST_URL="https://gist.github.com/..."
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export GEMINI_API_KEY="..."
export FINNHUB_API_KEY="..."

# Run
python src/main.py
```

## Project Structure

```
sentiment_tracker/
├── .github/workflows/daily_report.yml
├── src/
│   ├── main.py              # Entry point
│   ├── data_fetcher.py      # CSV/Gist fetching
│   ├── price_analyzer.py    # >5% movement detection
│   ├── earnings_tracker.py  # Finnhub earnings calendar
│   ├── news_aggregator.py   # Multi-source news
│   ├── ai_analyzer.py       # Gemini AI integration
│   └── email_sender.py      # Gmail SMTP
├── requirements.txt
├── SPEC.md                  # Full specification
└── README.md
```

## Troubleshooting

**Email not sending?**
- Verify Gmail App Password (not your regular password)
- Check 2FA is enabled on your Google account
- Look at GitHub Actions logs for errors

**No analysis appearing?**
- Check Gemini API key is valid
- Verify you haven't hit rate limits (1,500/day free)

**Missing earnings data?**
- Finnhub free tier has rate limits
- Some smaller stocks may not have earnings calendar data
