# Sentiment Tracker - Specification

## Overview
Automated daily stock monitoring system that analyzes portfolio movements, tracks earnings, and delivers actionable insights via email.

---

## Core Features

### 1. Price Movement Detection (>5% Movers)
- **Threshold**: Daily price change exceeds ±5%
- **Data Source**: User's CSV export (column: `Daily Price Change`) - treated as source of truth
- **Extended Hours**: Fetch supplementary pre-market/after-hours data from Yahoo Finance to explain gaps
- **Analysis Output**: AI-synthesized explanation of why the stock moved

### 2. Earnings Calendar Tracking
- **Data Source**: Finnhub API (free tier) for earnings dates
- **Reminder**: Alert in email 1 day before scheduled earnings call
- **No sheet modification**: Earnings dates tracked in email only, not written to CSV

### 3. Earnings Report Summaries
- **Trigger**: After a stock reports earnings
- **Timing**:
  - Preliminary summary same day (if earnings released before Action runs at 2-3 PM PT)
  - Updated summary next trading day with market reaction included
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
              │ Yahoo    │ │ Finnhub  │ │ Gemini   │
              │ Finance  │ │ API      │ │ API      │
              │ (prices) │ │(earnings)│ │ (AI)     │
              └──────────┘ └──────────┘ └──────────┘
```

---

## Input: CSV Format

**Location**: GitHub Gist (secret gist recommended)
**Update Frequency**: Manual export when tickers change

| Column | Required | Description |
|--------|----------|-------------|
| `Ticker` | Yes | Stock symbol (e.g., AAPL, GOOGL) |
| `Daily Price Change` | Yes | Percentage change as decimal or percentage (e.g., -0.05 or -5%) |
| `YTD Price Change` | No | For reference, not used in logic |

**Expected portfolio size**: 20-50 tickers

---

## Output: Daily Email

### Subject Line Format
```
[ACTION] TSLA -7.2%, NVDA earnings tomorrow | Jan 30, 2026
```
- Highlights most significant mover and upcoming earnings
- Date appended for filtering

### Body Format (Minimal HTML)
Single ticker-centric list - each stock with all its relevant info grouped together:

```html
<h2>📊 Daily Stock Report - Jan 30, 2026</h2>

<h3>TSLA - Tesla Inc</h3>
<p><strong>🔴 DOWN 7.2%</strong> (Extended hours: additional -1.3%)</p>
<p><strong>Why it moved:</strong> [AI-synthesized analysis]
Tesla shares dropped following reports of production delays at the
Berlin facility. Analyst downgrades from Morgan Stanley and concerns
about EV demand in China contributed to selling pressure. No company
statement issued.</p>

<hr>

<h3>NVDA - NVIDIA Corp</h3>
<p><strong>⚠️ Earnings Tomorrow</strong> - Feb 1, 2026 (After Market Close)</p>
<p>Expected EPS: $5.42 | Expected Revenue: $28.5B</p>

<hr>

<h3>AAPL - Apple Inc</h3>
<p><strong>📋 Earnings Report Summary</strong> (Reported: Jan 29, 2026)</p>
<p><strong>Results:</strong> Beat on EPS ($2.10 vs $2.05 expected),
slight revenue miss ($119.5B vs $120.1B expected)</p>
<p><strong>Key Insights:</strong></p>
<ul>
  <li>Services revenue hit all-time high of $22.3B</li>
  <li>iPhone sales down 3% YoY in China</li>
  <li>Raised dividend by 4%</li>
</ul>
<p><strong>Market Reaction:</strong> +2.3% in after-hours trading</p>
```

### Email Behavior
- **Quiet days**: No email sent if no >5% movers AND no earnings news
- **Market holidays**: Skip email entirely
- **Send time**: After market close, ~2-3 PM Pacific
- **Recipient**: Same Gmail account that sends it

---

## AI Analysis Specifications

### LLM Provider
- **Primary**: Google Gemini API (free tier - 1,500 requests/day)
- **Model**: gemini-1.5-flash (fast, cost-effective)

### News Sources for Context
Query these sources to gather context before AI synthesis:
1. **Yahoo Finance** - Company news, analyst ratings
2. **Google News** - Broader news coverage
3. **Finnhub/Benzinga** - Financial-specific news (free tier)
4. **SEC EDGAR** - 8-K filings for material events

### Analysis Prompt Structure
```
Analyze why {TICKER} ({COMPANY_NAME}) moved {PERCENT}% today.

News context:
{AGGREGATED_NEWS_SNIPPETS}

SEC filings (if any):
{RECENT_8K_SUMMARIES}

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
- **Schedule**: `cron: '0 22 * * 1-5'` (2 PM Pacific on weekdays)
- **Runner**: `ubuntu-latest`
- **Timeout**: 10 minutes

### Required Secrets (GitHub Repo Settings)
| Secret Name | Description | Setup Guide |
|-------------|-------------|-------------|
| `GIST_URL` | URL to your secret Gist with CSV | Create at gist.github.com |
| `GMAIL_ADDRESS` | Your Gmail address | - |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not regular password) | See setup guide below |
| `GEMINI_API_KEY` | Google AI Studio API key | See setup guide below |
| `FINNHUB_API_KEY` | Finnhub API key (free) | See setup guide below |

### API Rate Limits (Free Tiers)
| Service | Limit | Our Usage |
|---------|-------|-----------|
| Yahoo Finance | Unofficial, ~2000/hr | ~50-100 calls/day |
| Finnhub | 60 calls/min | ~50-100 calls/day |
| Gemini | 1,500/day | ~10-50 calls/day |

---

## Setup Guides

### Gmail App Password
1. Go to Google Account → Security
2. Enable 2-Factor Authentication (required)
3. Go to Security → 2-Step Verification → App Passwords
4. Generate new app password for "Mail"
5. Save the 16-character password as `GMAIL_APP_PASSWORD` secret

### Gemini API Key
1. Go to https://aistudio.google.com/apikey
2. Create new API key
3. Save as `GEMINI_API_KEY` secret

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
- **Rate limits**: Implement exponential backoff, fail gracefully

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
│   ├── ai_analyzer.py            # Gemini API integration
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
google-generativeai>=0.4  # Gemini API
beautifulsoup4>=4.12      # HTML parsing for news
python-dateutil>=2.8      # Date handling
```

---

## Future Enhancements (Out of Scope)
- Slack/Discord notifications
- Web dashboard
- Historical trend analysis
- Custom threshold per ticker
- Multiple recipient support
