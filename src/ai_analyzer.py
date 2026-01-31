import os
import time
from google import genai
from src.news_aggregator import NewsItem, format_news_for_prompt
from src.price_analyzer import PriceMover, format_change
from src.earnings_tracker import EarningsEvent

# Initialize client globally
_client = None
_last_request_time = 0
MIN_REQUEST_INTERVAL = 4.5  # seconds between requests (safe for 15 RPM limit)

def get_gemini_client():
    """Initialize Gemini client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        _client = genai.Client(api_key=api_key)
    return _client

def rate_limit():
    """Enforce rate limiting between API calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def analyze_price_movement(mover: PriceMover, news_items: list[NewsItem]) -> str:
    """Generate AI analysis of why a stock moved significantly."""
    client = get_gemini_client()

    news_context = format_news_for_prompt(news_items)
    direction = "up" if mover.daily_change > 0 else "down"
    change_str = format_change(mover.daily_change)

    prompt = f"""Analyze why {mover.symbol} ({mover.company_name}) moved {change_str} {direction} today.

Recent news:
{news_context}

Instructions:
- If the news clearly explains the move, write a 2-3 sentence synthesis
- If no significant news was found, explicitly state "No significant news identified." on its own line, then provide brief speculative analysis (sector trends, technical factors, low volume, etc.)
- Mention analyst actions if visible in the news (upgrades/downgrades)
- Keep response under 100 words
- Do not use markdown formatting
- Write in a professional, concise style"""

    try:
        rate_limit()
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Analysis unavailable: {str(e)}"


def analyze_earnings_report(event: EarningsEvent, news_items: list[NewsItem]) -> str:
    """Generate AI summary of an earnings report."""
    client = get_gemini_client()

    news_context = format_news_for_prompt(news_items)

    eps_info = ""
    if event.eps_estimate and event.actual_eps:
        beat_miss = "beat" if event.actual_eps > event.eps_estimate else "missed"
        eps_info = f"EPS: ${event.actual_eps:.2f} actual vs ${event.eps_estimate:.2f} expected ({beat_miss})"

    revenue_info = ""
    if event.revenue_estimate and event.actual_revenue:
        beat_miss = "beat" if event.actual_revenue > event.revenue_estimate else "missed"
        rev_b = event.actual_revenue / 1e9
        est_b = event.revenue_estimate / 1e9
        revenue_info = f"Revenue: ${rev_b:.2f}B actual vs ${est_b:.2f}B expected ({beat_miss})"

    prompt = f"""Summarize the earnings report for {event.symbol} ({event.company_name}).

Earnings date: {event.date.strftime('%B %d, %Y')}
{eps_info}
{revenue_info}

Recent news and coverage:
{news_context}

Instructions:
- Provide a brief summary of the earnings results
- Highlight 2-3 key insights (guidance, segment performance, notable quotes)
- If market reaction data is in the news, mention it
- Keep response under 150 words
- Do not use markdown formatting
- Write in a professional, concise style"""

    try:
        rate_limit()
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Earnings analysis unavailable: {str(e)}"


def generate_speculative_context(symbol: str, company_name: str, daily_change: float) -> str:
    """Generate brief speculative analysis when no news is found."""
    client = get_gemini_client()

    direction = "increase" if daily_change > 0 else "decrease"
    change_str = format_change(daily_change)

    prompt = f"""The stock {symbol} ({company_name}) had a {change_str} {direction} today, but no significant news was found.

Provide 2-3 brief possible explanations for this move. Consider:
- Sector or market-wide movements
- Technical trading patterns
- Low volume amplifying moves
- Institutional rebalancing

Keep response under 60 words. Do not use markdown. Start with "Possible factors:"."""

    try:
        rate_limit()
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return "Unable to generate speculative analysis."
