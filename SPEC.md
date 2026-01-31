# Sentiment Tracker - Specification

## Overview
Automated daily stock monitoring system that analyzes portfolio movements, tracks earnings, and delivers actionable insights via email.

---

## Core Features

### 1. Price Movement Detection (>5% Movers)
- **Threshold**: Daily price change exceeds ±5%
- **Data Source**: Yahoo Finance for real-time price data
- **Extended Hours**: Fetch supplementary pre-market/after-hours data to explain gaps
- **Analysis Output**: AI-synthesized explanation of why the stock moved

### 2. Earnings Calendar Tracking
- **Data Source**: Finnhub API (free tier) for earnings dates
- **Reminder**: Alert in email 1 day before scheduled earnings call
- **Calendar View**: Table showing next earnings date for all tracked tickers

### 3. Earnings Report Summaries
- **Trigger**: After a stock reports earnings
- **Timing**: Summary generated when workflow runs (3 PM Pacific)
- **Source Priority**: Company press releases (via news aggregation)
- **Content**: Key metrics, guidance, notable quotes, market reaction

---

## Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GitHub Gist    │────▶│  GitHub Action   │────▶│  Gmail SMTP     │
│  (CSV tickers)  │     │  (Python script) │     │  (Daily email)  │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                │
                   ┌────────────┼────────────┐
                   ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ Yahoo    │ │ Finnhub  │ │ OpenAI   │
             │ Finance  │ │ API      │ │ API      │
             │ (prices) │ │(earnings)│ │ (AI)     │
             └──────────┘ └──────────┘ └──────────┘
```

---

## Input: Ticker List

**Location**: GitHub Gist (secret gist recommended)
**Update Frequency**: Manual update when tickers change
**Format**: CSV with tickers in column C (index 2)

**Expected portfolio size**: 20-50 tickers

---

## Output: Daily Email

### Subject Line Format
```
[ACTION] TSLA -7.2%, NVDA earnings tomorrow | Jan 30, 2026
```
- Highlights most significant mover and upcoming earnings
- Date appended for filtering

### Body Sections
1. **Big Movers**: Stocks with >5% daily change
   - Direction indicator (UP/DOWN)
   - Extended hours movement if available
   - AI-synthesized "Why it moved" analysis

2. **Upcoming Earnings**: Stocks reporting within 1 day
   - Expected date and time (before/after market)
   - EPS and revenue estimates

3. **Recent Earnings**: Stocks that recently reported
   - Beat/miss on EPS and revenue
   - AI-generated summary of key insights

4. **Earnings Calendar**: Table of all tracked tickers
   - Next earnings date for each
   - Sorted by date

### Email Behavior
- **Quiet days**: No email sent if no >5% movers AND no earnings news
- **Market holidays**: Skip email entirely
- **Send time**: 3 PM Pacific on weekdays
- **Recipient**: Same Gmail account that sends it

---

## AI Analysis Specifications

### LLM Provider
- **Provider**: OpenAI
- **Model**: gpt-5-mini (via Responses API)

### News Sources for Context
Query these sources to gather context before AI synthesis:
1. **Yahoo Finance** - Company news, analyst ratings
2. **Finnhub** - Financial-specific news (free tier)

### Analysis Prompt Structure
```
Analyze why {TICKER} ({COMPANY_NAME}) moved {PERCENT}% today.

News context:
{AGGREGATED_NEWS_SNIPPETS}

Instructions:
- If clear news explains the move, synthesize a 2-3 sentence explanation
- If no significant news found, explicitly state "No significant news identified"
  BEFORE providing speculative analysis (sector rotation, technical factors,
  low volume, etc.)
- Include analyst actions if relevant (upgrades/downgrades)
- Keep response under 100 words
```

---

## Infrastructure

### GitHub Actions Workflow
- **Schedule**: `cron: '0 23 * * 1-5'` (3 PM Pacific on weekdays)
- **Runner**: `ubuntu-latest`
- **Timeout**: 10 minutes

### Required Secrets (GitHub Repo Settings)
| Secret Name | Description |
|-------------|-------------|
| `GIST_URL` | URL to your secret Gist with ticker CSV |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not regular password) |
| `OPENAI_API_KEY` | OpenAI API key |
| `FINNHUB_API_KEY` | Finnhub API key (free) |

### API Rate Limits
| Service | Limit | Our Usage |
|---------|-------|-----------|
| Yahoo Finance | Unofficial, ~2000/hr | ~50-100 calls/day |
| Finnhub | 60 calls/min | ~50-100 calls/day |
| OpenAI | Pay per token | ~10-50 calls/day |

---

## Setup Guides

### Gmail App Password
1. Go to Google Account → Security
2. Enable 2-Factor Authentication (required)
3. Go to Security → 2-Step Verification → App Passwords
4. Generate new app password for "Mail"
5. Save the 16-character password as `GMAIL_APP_PASSWORD` secret

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Save as `OPENAI_API_KEY` secret

### Finnhub API Key
1. Register at https://finnhub.io/register
2. Copy API key from dashboard
3. Save as `FINNHUB_API_KEY` secret

### GitHub Secrets Setup
1. Go to your repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret with the exact names listed above

---

## Error Handling

- **API failures**: GitHub Actions sends failure notification (default GitHub behavior)
- **No email on errors**: Silent failure, retry next day
- **Missing ticker data**: Skip that ticker, continue with others
- **Rate limits**: Implement delays between calls, fail gracefully

---

## File Structure

```
sentiment_tracker/
├── .github/
│   └── workflows/
│       └── daily_report.yml      # GitHub Actions workflow
├── src/
│   ├── main.py                   # Entry point
│   ├── data_fetcher.py           # CSV + API data fetching
│   ├── price_analyzer.py         # >5% movement detection
│   ├── earnings_tracker.py       # Earnings calendar logic
│   ├── news_aggregator.py        # Multi-source news gathering
│   ├── ai_analyzer.py            # OpenAI API integration
│   └── email_sender.py           # Gmail SMTP logic
├── requirements.txt              # Python dependencies
├── SPEC.md                       # This file
└── README.md                     # Setup instructions
```

---

## Dependencies

```
requests>=2.31.0          # HTTP requests
yfinance>=0.2.36          # Yahoo Finance data
finnhub-python>=2.4.18    # Finnhub API client
openai>=1.0.0             # OpenAI API
beautifulsoup4>=4.12      # HTML parsing for news
python-dateutil>=2.8      # Date handling
```
