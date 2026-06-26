import os
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import quote_plus
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


@dataclass
class EarningsCallContext:
    """Extended context from earnings call coverage."""
    source: str
    url: str
    content: str  # Extracted text content (quotes, key points)


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
            lines.append(f"  Summary: {item.summary[:500]}")

    return "\n".join(lines)


def search_earnings_call_coverage(symbol: str, company_name: str, limit: int = 3) -> list[EarningsCallContext]:
    """
    Search for earnings call coverage, transcripts, and analyst summaries.
    Uses DuckDuckGo to find relevant articles, then extracts content.
    """
    results = []

    # Build search queries targeting free, accessible sources
    quarter = _get_recent_quarter()
    search_queries = [
        f"{company_name} {quarter} earnings results analyst reaction",
        f"{symbol} earnings call {quarter} highlights guidance outlook",
        f"site:fool.com {symbol} {quarter} earnings call transcript",
        f"{company_name} earnings {quarter} CEO CFO quotes guidance",
    ]

    urls_to_fetch = set()

    for query in search_queries:
        try:
            search_results = _duckduckgo_search(query, max_results=5)
            urls_to_fetch.update(search_results)
        except Exception:
            continue

    # Fetch and extract content from found URLs (try more to account for paywalls)
    for url in list(urls_to_fetch)[:limit * 3]:
        try:
            context = _extract_earnings_content(url)
            if context and len(context.content) > 200:  # Only keep substantial content
                results.append(context)
                if len(results) >= limit:
                    break
        except Exception:
            continue

    return results


def _get_recent_quarter() -> str:
    """Get the most recent fiscal quarter string (e.g., 'Q4 2025')."""
    now = datetime.now()
    # Earnings are typically reported 1-2 months after quarter end
    # So if we're in Feb, we're likely looking at Q4 of previous year
    month = now.month
    year = now.year

    if month <= 2:
        return f"Q4 {year - 1}"
    elif month <= 5:
        return f"Q1 {year}"
    elif month <= 8:
        return f"Q2 {year}"
    elif month <= 11:
        return f"Q3 {year}"
    else:
        return f"Q4 {year}"


def _duckduckgo_search(query: str, max_results: int = 5) -> list[str]:
    """
    Search DuckDuckGo and return URLs of results.
    Uses the HTML version to avoid API restrictions.
    """
    encoded_query = quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    urls = []
    # DuckDuckGo HTML results have links in result__a class
    for link in soup.find_all("a", class_="result__a", limit=max_results * 3):
        href = link.get("href", "")
        if href and href.startswith("http"):
            # Filter for financial news sites
            if _is_relevant_source(href):
                urls.append(href)
                if len(urls) >= max_results:
                    break

    return urls


def _is_relevant_source(url: str) -> bool:
    """Check if URL is from a relevant financial news source."""
    relevant_domains = [
        "fool.com",
        "cnbc.com",
        "reuters.com",
        "marketwatch.com",
        "benzinga.com",
        "zacks.com",
        "thestreet.com",
        "investors.com",
        "finance.yahoo.com",
        "seekingalpha.com",
        "bloomberg.com",
        "barrons.com",
        "tipranks.com",
        "investing.com",
    ]
    url_lower = url.lower()
    return any(domain in url_lower for domain in relevant_domains)


def _extract_earnings_content(url: str) -> EarningsCallContext | None:
    """
    Fetch a URL and extract earnings-relevant content.
    Focuses on quotes, key metrics, and analyst commentary.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script, style, nav, footer elements
        for element in soup.find_all(["script", "style", "nav", "footer", "aside", "header"]):
            element.decompose()

        # Determine source from URL
        source = _get_source_name(url)

        # Extract article content based on common patterns
        content = _extract_article_text(soup, source)

        if not content:
            return None

        # Extract the most relevant parts (quotes, key points)
        relevant_content = _extract_relevant_sections(content)

        if relevant_content:
            return EarningsCallContext(
                source=source,
                url=url,
                content=relevant_content
            )

        return None

    except Exception:
        return None


def _get_source_name(url: str) -> str:
    """Extract readable source name from URL."""
    source_map = {
        "seekingalpha": "Seeking Alpha",
        "fool.com": "Motley Fool",
        "cnbc.com": "CNBC",
        "bloomberg.com": "Bloomberg",
        "reuters.com": "Reuters",
        "marketwatch.com": "MarketWatch",
        "barrons.com": "Barron's",
        "investors.com": "IBD",
        "thestreet.com": "TheStreet",
        "benzinga.com": "Benzinga",
        "zacks.com": "Zacks",
    }
    url_lower = url.lower()
    for domain, name in source_map.items():
        if domain in url_lower:
            return name
    return "Web"


def _extract_article_text(soup: BeautifulSoup, source: str) -> str:
    """Extract main article text based on source-specific selectors."""
    content_selectors = [
        # Common article containers
        ("article", {}),
        ("div", {"class": re.compile(r"article|content|post|entry", re.I)}),
        ("div", {"id": re.compile(r"article|content|post|entry", re.I)}),
        # Seeking Alpha specific
        ("div", {"data-test-id": "article-content"}),
        # General fallback
        ("main", {}),
    ]

    for tag, attrs in content_selectors:
        container = soup.find(tag, attrs) if attrs else soup.find(tag)
        if container:
            # Get text from paragraphs within container
            paragraphs = container.find_all("p")
            if paragraphs:
                text = "\n".join(p.get_text(strip=True) for p in paragraphs)
                if len(text) > 200:
                    return text

    # Fallback: get all paragraphs
    paragraphs = soup.find_all("p")
    text = "\n".join(p.get_text(strip=True) for p in paragraphs[:30])
    return text


def _extract_relevant_sections(content: str) -> str:
    """
    Extract the most relevant parts of article content for earnings analysis.
    Focuses on quotes, guidance, key metrics, and analyst commentary.
    """
    if not content:
        return ""

    # Keywords that indicate relevant content
    keywords = [
        # Executive quotes
        "ceo", "cfo", "said", "stated", "commented", "noted", "added",
        # Guidance
        "guidance", "outlook", "expects", "forecast", "projects", "anticipates",
        # Results
        "beat", "missed", "exceeded", "fell short", "revenue", "earnings", "eps",
        "growth", "margin", "profit", "loss",
        # Analyst reactions
        "analyst", "upgrade", "downgrade", "price target", "rating", "buy", "sell", "hold",
        # Forward looking
        "next quarter", "full year", "fiscal", "q1", "q2", "q3", "q4",
        # Concerns/highlights
        "concern", "challenge", "headwind", "tailwind", "strong", "weak", "record",
    ]

    sentences = re.split(r'(?<=[.!?])\s+', content)
    relevant_sentences = []

    for sentence in sentences:
        sentence_lower = sentence.lower()
        # Check if sentence contains relevant keywords
        if any(kw in sentence_lower for kw in keywords):
            # Clean up the sentence
            sentence = sentence.strip()
            if 20 < len(sentence) < 500:  # Reasonable sentence length
                relevant_sentences.append(sentence)

    # Limit to most relevant content (to fit in prompt)
    result = " ".join(relevant_sentences[:20])

    # Truncate if too long
    if len(result) > 2000:
        result = result[:2000] + "..."

    return result


def aggregate_earnings_context(symbol: str, company_name: str) -> tuple[list[NewsItem], list[EarningsCallContext]]:
    """
    Aggregate both news and earnings call context for comprehensive earnings analysis.
    Returns tuple of (news_items, earnings_call_contexts).
    """
    news_items = aggregate_news(symbol, company_name, limit=10)
    earnings_contexts = search_earnings_call_coverage(symbol, company_name, limit=3)

    return news_items, earnings_contexts


def format_earnings_context_for_prompt(
    news_items: list[NewsItem],
    earnings_contexts: list[EarningsCallContext]
) -> str:
    """Format both news and earnings call context for AI prompt."""
    parts = []

    # Add news section
    news_text = format_news_for_prompt(news_items)
    parts.append("RECENT NEWS:")
    parts.append(news_text)

    # Add earnings call context section
    if earnings_contexts:
        parts.append("\nEARNINGS CALL COVERAGE & ANALYSIS:")
        for ctx in earnings_contexts:
            parts.append(f"\n[{ctx.source}]")
            parts.append(ctx.content)
    else:
        parts.append("\nEARNINGS CALL COVERAGE: No additional earnings call coverage found.")

    return "\n".join(parts)
