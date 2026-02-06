import os
import time
from openai import OpenAI
from src.news_aggregator import (
    NewsItem,
    EarningsCallContext,
    format_news_for_prompt,
    format_earnings_context_for_prompt,
)
from src.price_analyzer import PriceMover, format_change
from src.earnings_tracker import EarningsEvent, FundamentalContext

# Initialize client globally
_client = None
_last_request_time = 0
MIN_REQUEST_INTERVAL = 1.0  # OpenAI has higher rate limits

def get_openai_client():
    """Initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = OpenAI(api_key=api_key)
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
    client = get_openai_client()

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
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
        if response.output_text:
            return response.output_text.strip()
        else:
            return "No analysis generated."
    except Exception as e:
        return f"Analysis unavailable: {str(e)}"


def analyze_earnings_report(
    event: EarningsEvent,
    news_items: list[NewsItem],
    earnings_contexts: list[EarningsCallContext] | None = None
) -> str:
    """
    Generate comprehensive AI summary of an earnings report.

    Args:
        event: The earnings event data
        news_items: Recent news articles
        earnings_contexts: Optional additional context from earnings call coverage
    """
    client = get_openai_client()

    # Use enhanced context if available, otherwise just news
    if earnings_contexts:
        full_context = format_earnings_context_for_prompt(news_items, earnings_contexts)
    else:
        full_context = format_news_for_prompt(news_items)

    eps_info = ""
    if event.eps_estimate and event.actual_eps:
        beat_miss = "beat" if event.actual_eps > event.eps_estimate else "missed"
        diff_pct = ((event.actual_eps - event.eps_estimate) / abs(event.eps_estimate)) * 100 if event.eps_estimate != 0 else 0
        eps_info = f"EPS: ${event.actual_eps:.2f} actual vs ${event.eps_estimate:.2f} expected ({beat_miss} by {abs(diff_pct):.1f}%)"

    revenue_info = ""
    if event.revenue_estimate and event.actual_revenue:
        beat_miss = "beat" if event.actual_revenue > event.revenue_estimate else "missed"
        rev_b = event.actual_revenue / 1e9
        est_b = event.revenue_estimate / 1e9
        diff_pct = ((event.actual_revenue - event.revenue_estimate) / event.revenue_estimate) * 100 if event.revenue_estimate != 0 else 0
        revenue_info = f"Revenue: ${rev_b:.2f}B actual vs ${est_b:.2f}B expected ({beat_miss} by {abs(diff_pct):.1f}%)"

    # Build fundamental trends section from Sharadar data
    fundamental_trends = ""
    ctx = event.fundamental_context
    if ctx:
        trends = []
        if ctx.revenue_qoq_change is not None:
            trends.append(f"Revenue QoQ: {ctx.revenue_qoq_change:+.1f}%")
        if ctx.eps_qoq_change is not None:
            trends.append(f"EPS QoQ: {ctx.eps_qoq_change:+.1f}%")
        if ctx.fcf is not None:
            fcf_b = ctx.fcf / 1e9
            fcf_trend = f" ({ctx.fcf_qoq_change:+.1f}% QoQ)" if ctx.fcf_qoq_change is not None else ""
            trends.append(f"Free Cash Flow: ${fcf_b:.2f}B{fcf_trend}")
        if ctx.capex is not None:
            capex_b = abs(ctx.capex) / 1e9  # CapEx is often negative, show absolute
            capex_trend = f" ({ctx.capex_qoq_change:+.1f}% QoQ)" if ctx.capex_qoq_change is not None else ""
            trends.append(f"CapEx: ${capex_b:.2f}B{capex_trend}")
        if ctx.gross_margin is not None:
            gm_change = ""
            if ctx.gross_margin_prior is not None:
                gm_diff = (ctx.gross_margin - ctx.gross_margin_prior) * 100  # Convert to percentage points
                gm_change = f" ({gm_diff:+.1f}pp vs prior Q)"
            trends.append(f"Gross Margin: {ctx.gross_margin*100:.1f}%{gm_change}")
        if ctx.operating_margin is not None:
            om_change = ""
            if ctx.operating_margin_prior is not None:
                om_diff = (ctx.operating_margin - ctx.operating_margin_prior) * 100
                om_change = f" ({om_diff:+.1f}pp vs prior Q)"
            trends.append(f"Operating Margin: {ctx.operating_margin*100:.1f}%{om_change}")
        if ctx.net_margin is not None:
            nm_change = ""
            if ctx.net_margin_prior is not None:
                nm_diff = (ctx.net_margin - ctx.net_margin_prior) * 100
                nm_change = f" ({nm_diff:+.1f}pp vs prior Q)"
            trends.append(f"Net Margin: {ctx.net_margin*100:.1f}%{nm_change}")

        if trends:
            fundamental_trends = "Quarter-over-Quarter Trends:\n" + "\n".join(f"- {t}" for t in trends)

    prompt = f"""Provide a comprehensive earnings analysis for {event.symbol} ({event.company_name}).

Earnings date: {event.date.strftime('%B %d, %Y')}
{eps_info}
{revenue_info}

{fundamental_trends}

{full_context}

Provide your analysis in this exact format:

HIGHLIGHTS:
- [2-3 bullet points on positive results, beats, strong segments, raised guidance]

LOWLIGHTS:
- [2-3 bullet points on misses, weak segments, concerns, lowered guidance]

ANALYST REACTIONS:
- [Key analyst upgrades/downgrades, price target changes, sentiment shifts mentioned in the news coverage]

FORWARD OUTLOOK:
- [Management guidance, growth expectations, key metrics to watch based on the coverage]

KEY QUOTES:
- [1-2 notable direct quotes from CEO/CFO if found in the coverage. If no direct quotes are available, write "No direct quotes available in current coverage"]

Instructions:
- Be specific with numbers and percentages where available
- For ANALYST REACTIONS: Synthesize from the news coverage provided. Look for mentions of analyst ratings, price targets, upgrades, downgrades, or Wall Street sentiment. If the news mentions analyst commentary even indirectly, include it.
- For FORWARD OUTLOOK: Extract any forward-looking statements, guidance, or expectations mentioned in the news. Include management commentary on future quarters if available.
- For KEY QUOTES: Only include actual direct quotes found in the coverage. Do not fabricate quotes.
- Every section except KEY QUOTES must have substantive content. Use the earnings results data and news context to provide analysis even when coverage is limited.
- Focus on what investors care about most
- Do not use markdown formatting beyond the section headers above
- Write in a professional, concise style"""

    try:
        rate_limit()
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
        if response.output_text:
            return response.output_text.strip()
        else:
            return "No earnings analysis generated."
    except Exception as e:
        return f"Earnings analysis unavailable: {str(e)}"


def generate_speculative_context(symbol: str, company_name: str, daily_change: float) -> str:
    """Generate brief speculative analysis when no news is found."""
    client = get_openai_client()

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
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )
        if response.output_text:
            return response.output_text.strip()
        else:
            return "Unable to generate speculative analysis."
    except Exception as e:
        return "Unable to generate speculative analysis."
