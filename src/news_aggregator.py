import os
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
import finnhub


@dataclass
class NewsItem:
    headline: str
    source: str
    url: str
    published: datetime | None
    summary: str | None = None


def aggregate_news(symbol: str, company_name: str, limit: int = 10) -> list[NewsItem]:
    """Aggregate news from multiple sources for a given symbol."""
    all_news = []

    # Fetch from multiple sources
    all_news.extend(fetch_finnhub_news(symbol, limit=5))
    all_news.extend(fetch_yahoo_news(symbol, limit=5))

    # Deduplicate by headline similarity
    seen_headlines = set()
    unique_news = []
    for item in all_news:
        headline_key = item.headline.lower()[:50]
        if headline_key not in seen_headlines:
            seen_headlines.add(headline_key)
            unique_news.append(item)

    # Sort by date (newest first) and limit
    unique_news.sort(key=lambda x: x.published or datetime.min, reverse=True)
    return unique_news[:limit]


def fetch_finnhub_news(symbol: str, limit: int = 5) -> list[NewsItem]:
    """Fetch company news from Finnhub."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return []

    try:
        client = finnhub.Client(api_key=api_key)
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        news = client.company_news(symbol, _from=str(week_ago), to=str(today))

        items = []
        for article in news[:limit]:
            published = None
            if "datetime" in article:
                published = datetime.fromtimestamp(article["datetime"])

            items.append(NewsItem(
                headline=article.get("headline", ""),
                source=article.get("source", "Finnhub"),
                url=article.get("url", ""),
                published=published,
                summary=article.get("summary")
            ))
        return items
    except Exception:
        return []


def fetch_yahoo_news(symbol: str, limit: int = 5) -> list[NewsItem]:
    """Scrape news headlines from Yahoo Finance."""
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}/news"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        items = []
        # Look for news article links
        for article in soup.find_all("h3", limit=limit):
            link = article.find("a")
            if link:
                headline = link.get_text(strip=True)
                href = link.get("href", "")
                if not href.startswith("http"):
                    href = f"https://finance.yahoo.com{href}"

                items.append(NewsItem(
                    headline=headline,
                    source="Yahoo Finance",
                    url=href,
                    published=None
                ))

        return items
    except Exception:
        return []


def format_news_for_prompt(news_items: list[NewsItem]) -> str:
    """Format news items for inclusion in AI prompt."""
    if not news_items:
        return "No recent news articles found."

    lines = []
    for item in news_items:
        date_str = ""
        if item.published:
            date_str = f" ({item.published.strftime('%b %d')})"

        lines.append(f"- [{item.source}]{date_str}: {item.headline}")
        if item.summary:
            lines.append(f"  Summary: {item.summary[:200]}...")

    return "\n".join(lines)
