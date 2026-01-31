"""Generate fundamental metrics charts using matplotlib."""

import io
import base64
from dataclasses import dataclass

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import numpy as np

from src.fundamentals_fetcher import FundamentalData


# Chart configuration
CHART_WIDTH = 3.5  # inches
CHART_HEIGHT = 2.2  # inches
CHART_DPI = 100

# Colors
COLORS = {
    # Growth chart colors
    "revenue": "#3b82f6",  # Blue
    "eps": "#16a34a",      # Green (matches existing up color)
    "fcf": "#f59e0b",      # Amber

    # Profitability chart colors
    "roe": "#8b5cf6",      # Purple
    "roa": "#06b6d4",      # Cyan
    "gross_margin": "#14b8a6",  # Teal
    "net_margin": "#ec4899",    # Pink

    # Chart elements
    "grid": "#e5e5e5",
    "text": "#374151",
    "background": "#ffffff",
}


@dataclass
class ChartPair:
    """Base64-encoded PNG charts for a single ticker."""
    ticker: str
    company_name: str
    growth_chart_base64: str
    profitability_chart_base64: str


def _format_quarter(dt) -> str:
    """Format datetime as quarter label (e.g., 'Q1 24')."""
    quarter = (dt.month - 1) // 3 + 1
    year = str(dt.year)[-2:]
    return f"Q{quarter}'{year}"


def _fig_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=CHART_DPI, bbox_inches='tight',
                facecolor=COLORS["background"], edgecolor='none')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)
    return img_base64


def _create_grouped_bar_chart(
    quarter_labels: list[str],
    metrics: dict[str, list[float | None]],
    colors: dict[str, str],
    title: str,
    ylabel: str,
    is_percentage: bool = True,
) -> plt.Figure:
    """
    Create a grouped bar chart.

    Args:
        quarter_labels: X-axis labels (e.g., ["Q1'24", "Q2'24"])
        metrics: Dict mapping metric name -> values list
        colors: Dict mapping metric name -> color hex
        title: Chart title
        ylabel: Y-axis label
        is_percentage: If True, format values as percentages
    """
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT))

    # Filter out metrics with all None values
    valid_metrics = {k: v for k, v in metrics.items() if any(x is not None for x in v)}

    if not valid_metrics:
        ax.text(0.5, 0.5, "No data available", ha='center', va='center',
                transform=ax.transAxes, fontsize=9, color=COLORS["text"])
        ax.set_xticks([])
        ax.set_yticks([])
        return fig

    n_quarters = len(quarter_labels)
    n_metrics = len(valid_metrics)
    bar_width = 0.8 / n_metrics
    x = np.arange(n_quarters)

    for i, (metric_name, values) in enumerate(valid_metrics.items()):
        # Replace None with 0 for plotting (or np.nan to skip)
        plot_values = [v if v is not None else 0 for v in values]
        offset = (i - n_metrics / 2 + 0.5) * bar_width
        bars = ax.bar(x + offset, plot_values, bar_width,
                      label=metric_name.replace("_", " ").title(),
                      color=colors.get(metric_name, "#999999"),
                      edgecolor='none')

    # Styling
    ax.set_xticks(x)
    ax.set_xticklabels(quarter_labels, fontsize=7, color=COLORS["text"])
    ax.set_ylabel(ylabel, fontsize=7, color=COLORS["text"])

    # Y-axis formatting
    if is_percentage:
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    ax.tick_params(axis='y', labelsize=7, colors=COLORS["text"])

    # Grid
    ax.yaxis.grid(True, color=COLORS["grid"], linewidth=0.5)
    ax.set_axisbelow(True)

    # Remove spines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color(COLORS["grid"])

    # Legend
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              ncol=min(n_metrics, 3), fontsize=6, frameon=False)

    # Add zero line if there are negative values
    all_values = [v for values in valid_metrics.values() for v in values if v is not None]
    if any(v < 0 for v in all_values):
        ax.axhline(y=0, color=COLORS["text"], linewidth=0.5, linestyle='-')

    fig.tight_layout()
    return fig


def _create_growth_chart(data: FundamentalData) -> str:
    """Create growth metrics chart (Revenue, EPS, FCF growth %)."""
    quarter_labels = [_format_quarter(q) for q in data.quarters]

    metrics = {
        "revenue": data.revenue_growth,
        "eps": data.eps_growth,
        "fcf": data.fcf_growth,
    }

    colors = {
        "revenue": COLORS["revenue"],
        "eps": COLORS["eps"],
        "fcf": COLORS["fcf"],
    }

    fig = _create_grouped_bar_chart(
        quarter_labels=quarter_labels,
        metrics=metrics,
        colors=colors,
        title="Growth (QoQ)",
        ylabel="Change %",
        is_percentage=True,
    )

    return _fig_to_base64(fig)


def _create_profitability_chart(data: FundamentalData) -> str:
    """Create profitability metrics chart (ROE, ROA, Gross Margin, Net Margin)."""
    quarter_labels = [_format_quarter(q) for q in data.quarters]

    metrics = {
        "roe": data.roe,
        "roa": data.roa,
        "gross_margin": data.gross_margin,
        "net_margin": data.net_margin,
    }

    colors = {
        "roe": COLORS["roe"],
        "roa": COLORS["roa"],
        "gross_margin": COLORS["gross_margin"],
        "net_margin": COLORS["net_margin"],
    }

    fig = _create_grouped_bar_chart(
        quarter_labels=quarter_labels,
        metrics=metrics,
        colors=colors,
        title="Profitability",
        ylabel="Percentage",
        is_percentage=True,
    )

    return _fig_to_base64(fig)


def generate_charts_for_ticker(data: FundamentalData) -> ChartPair | None:
    """
    Generate both charts for a single ticker.

    Returns None if insufficient data (< 2 quarters).
    """
    if len(data.quarters) < 2:
        return None

    try:
        growth_chart = _create_growth_chart(data)
        profitability_chart = _create_profitability_chart(data)

        return ChartPair(
            ticker=data.ticker,
            company_name=data.company_name,
            growth_chart_base64=growth_chart,
            profitability_chart_base64=profitability_chart,
        )
    except Exception as e:
        print(f"  Warning: Failed to generate charts for {data.ticker}: {e}")
        return None


def generate_all_charts(fundamentals: dict[str, FundamentalData]) -> dict[str, ChartPair]:
    """
    Generate charts for all tickers with sufficient data.

    Args:
        fundamentals: Dict mapping symbol -> FundamentalData

    Returns:
        Dict mapping symbol -> ChartPair
    """
    results: dict[str, ChartPair] = {}

    for ticker, data in fundamentals.items():
        chart_pair = generate_charts_for_ticker(data)
        if chart_pair:
            results[ticker] = chart_pair

    return results
