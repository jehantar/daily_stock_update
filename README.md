# Sentiment Tracker

Automated daily stock monitoring that delivers AI-analyzed insights via email.

## Features

- **Big Movers Alert**: Stocks with >5% daily change, with AI-synthesized explanation
- **Earnings Calendar**: Reminder 1 day before scheduled earnings calls
- **Earnings Summaries**: Key insights from recent earnings reports
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

The workflow runs automatically at 3 PM Pacific on weekdays.

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
- Upcoming earnings alerts
- Post-earnings summaries
- Earnings calendar for all tickers

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
│   ├── main.py              # Entry point
│   ├── data_fetcher.py      # CSV/Gist fetching, Yahoo Finance prices
│   ├── price_analyzer.py    # >5% movement detection
│   ├── earnings_tracker.py  # Finnhub earnings calendar
│   ├── news_aggregator.py   # Multi-source news
│   ├── ai_analyzer.py       # OpenAI gpt-5-mini integration
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
- Check OpenAI API key is valid
- Verify you have API credits available

**Missing earnings data?**
- Finnhub free tier has rate limits
- Some smaller stocks may not have earnings calendar data
