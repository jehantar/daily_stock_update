# Sentiment Tracker - Specification

## Overview
Automated daily stock monitoring system that analyzes portfolio movements, tracks earnings, and delivers actionable insights via email with fundamental trend visualizations.

---

## Core Features

### 1. Price Movement Detection (>3% Movers)
- **Threshold**: Daily price change exceeds ±3%
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

### 4. Fundamental Trends (Charts)
- **Data Source**: Nasdaq Data Link SHARADAR/SF1 dataset
- **History Depth**: 6 quarters
- **Visualization**: Line charts with markers, embedded as CID attachments
- **Outlier Handling**: IQR-based detection with axis capping and value annotations

### 5. Valuation Snapshot
- **Data Source**: Yahoo Finance
- **Metrics**: Trailing P/E, Forward P/E, Price/Cash Flow (P/CF), Dividend Yield, Market Cap
- **Display**: Table grouped by custom categories (Platform Tech, Semiconductors, Enterprise Software, Commerce, Financials, Resources/Materials/Life Sciences)

---

## Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GitHub Gist    │────▶│  GitHub Action   │────▶│  Gmail SMTP     │
│  (CSV tickers)  │     │  (Python script) │     │  (Daily email)  │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                │
                   ┌────────────┼────────────┬────────────┐
                   ▼            ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ Yahoo    │ │ Finnhub  │ │ OpenAI   │ │ Nasdaq   │
             │ Finance  │ │ API      │ │ API      │ │ Data Link│
             │ (prices) │ │(earnings)│ │ (AI)     │ │(fundmtls)│
             └──────────┘ └──────────┘ └──────────┘ └──────────┘
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
1. **Big Movers**: Stocks with >3% daily change
   - Direction indicator (UP/DOWN)
   - Extended hours movement if available
   - AI-synthesized "Why it moved" analysis

2. **Valuation Snapshot**: All tracked tickers
   - Trailing P/E, Forward P/E, P/CF, Dividend Yield, Market Cap
   - Grouped by custom categories

3. **Upcoming Earnings**: Stocks reporting within 1 day
   - Expected date and time (before/after market)
   - EPS and revenue estimates

3. **Recent Earnings**: Stocks that recently reported
   - Beat/miss on EPS and revenue
   - AI-generated summary of key insights

4. **Earnings Calendar**: Table of all tracked tickers
   - Next earnings date for each
   - Sorted by date

5. **Fundamental Trends**: Two charts per ticker
   - Growth chart: Revenue, EPS, FCF (QoQ % change)
   - Profitability chart: ROE, ROA, Gross Margin, Net Margin (%)

### Email Behavior
- **Quiet days**: No email sent if no >3% movers AND no earnings news
- **Market holidays**: Skip email entirely
- **Send time**: 3 PM Pacific on weekdays
- **Recipient**: Same Gmail account that sends it

---

## Fundamental Charts Specification

### Metrics

**Growth Chart (QoQ % change)**
| Metric | Source Field | Color |
|--------|--------------|-------|
| Revenue | `revenueusd` | Blue (#3b82f6) |
| EPS | `eps` | Green (#16a34a) |
| Free Cash Flow | `fcf` | Amber (#f59e0b) |

**Profitability Chart (absolute %)**
| Metric | Source Field | Color |
|--------|--------------|-------|
| ROE | `roe` | Purple (#8b5cf6) |
| ROA | `roa` | Cyan (#06b6d4) |
| Gross Margin | `grossmargin` | Teal (#14b8a6) |
| Net Margin | `netmargin` | Pink (#ec4899) |

### Chart Configuration
- **Size**: 3.2 × 2.0 inches at 120 DPI
- **Type**: Line chart with circular markers
- **Grid**: Horizontal and vertical gridlines
- **Legend**: Positioned below chart

### Outlier Handling
- **Detection**: IQR-based (values beyond 2× IQR from quartiles)
- **Display**: Axis capped at bounds, outlier values annotated
- **Indicators**: Arrow markers (▲/▼) show direction of extreme values

### Email Embedding
- **Method**: CID (Content-ID) attachments
- **Format**: PNG images attached to MIME message
- **Reference**: `<img src="cid:growth_ticker">` in HTML

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
| `NASDAQ_DATA_LINK_API_KEY` | Nasdaq Data Link API key (SHARADAR subscription) |

### API Rate Limits
| Service | Limit | Our Usage |
|---------|-------|-----------|
| Yahoo Finance | Unofficial, ~2000/hr | ~50-100 calls/day |
| Finnhub | 60 calls/min | ~50-100 calls/day |
| OpenAI | Pay per token | ~10-50 calls/day |
| Nasdaq Data Link | Varies by plan | ~2-4 calls/day |

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

### Nasdaq Data Link API Key
1. Register at https://data.nasdaq.com
2. Subscribe to SHARADAR Core US Fundamentals (SF1)
3. Copy API key from account settings (20 characters)
4. Save as `NASDAQ_DATA_LINK_API_KEY` secret

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
- **Missing fundamentals**: Charts section skipped, email still sends
- **Insufficient chart data**: Tickers with <2 quarters excluded from charts

---

## File Structure

```
sentiment_tracker/
├── .github/
│   └── workflows/
│       └── daily_report.yml      # GitHub Actions workflow
├── src/
│   ├── main.py                   # Entry point (8-step workflow)
│   ├── data_fetcher.py           # CSV + Yahoo Finance data fetching
│   ├── price_analyzer.py         # >3% movement detection
│   ├── earnings_tracker.py       # Earnings calendar logic
│   ├── news_aggregator.py        # Multi-source news gathering
│   ├── ai_analyzer.py            # OpenAI API integration
│   ├── fundamentals_fetcher.py   # Nasdaq Data Link integration
│   ├── chart_generator.py        # matplotlib chart generation
│   └── email_sender.py           # Gmail SMTP with CID images
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
nasdaq-data-link>=1.0.0   # Nasdaq Data Link API
matplotlib>=3.7.0         # Chart generation
pandas>=2.0.0             # Data manipulation
numpy>=1.24.0             # Numerical operations
```
