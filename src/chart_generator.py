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
CHART_WIDTH = 3.2  # inches
CHART_HEIGHT = 2.0  # inches
CHART_DPI = 120  # Higher DPI for sharper images

# Outlier detection threshold (values beyond this multiple of IQR are considered outliers)
OUTLIER_IQR_MULTIPLIER = 2.0

# Colors
COLORS = {
    # Growth chart colors
    "revenue": "#3b82f6",  # Blue
    "eps": "#16a34a",      # Green (matches existing up color)
    "fcf": "#f59e0b",      # Amber
    "ebitda": "#ef4444",   # Red

    # Profitability chart colors
    "roe": "#8b5cf6",      # Purple
    "roa": "#06b6d4",      # Cyan
    "gross_margin": "#14b8a6",  # Teal
    "net_margin": "#ec4899",    # Pink
    "operating_margin": "#f97316",  # Orange

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


def _detect_axis_bounds(all_values: list[float]) -> tuple[float, float, list[tuple[int, float]]]:
    """
    Detect reasonable axis bounds, identifying outliers that should be capped.

    Returns:
        (y_min, y_max, outliers) where outliers is list of (index, actual_value)
    """
    if not all_values or len(all_values) < 3:
        return None, None, []

    # Calculate IQR-based bounds
    sorted_vals = sorted(all_values)
    q1 = sorted_vals[len(sorted_vals) // 4]
    q3 = sorted_vals[3 * len(sorted_vals) // 4]
    iqr = q3 - q1

    if iqr == 0:
        # All values similar, use simple min/max with padding
        return None, None, []

    lower_bound = q1 - OUTLIER_IQR_MULTIPLIER * iqr
    upper_bound = q3 + OUTLIER_IQR_MULTIPLIER * iqr

    # Check if any values exceed bounds significantly
    has_outliers = any(v < lower_bound or v > upper_bound for v in all_values)

    if not has_outliers:
        return None, None, []

    return lower_bound, upper_bound, []


def _create_line_chart(
    quarter_labels: list[str],
    metrics: dict[str, list[float | None]],
    colors: dict[str, str],
    title: str,
    ylabel: str,
    is_percentage: bool = True,
) -> plt.Figure:
    """
    Create a line chart for tracking metrics over time.
    Handles outliers by capping axis and annotating extreme values.
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

    x = np.arange(len(quarter_labels))

    # Collect all values for outlier detection
    all_values = [v for values in valid_metrics.values() for v in values if v is not None]
    y_min_bound, y_max_bound, _ = _detect_axis_bounds(all_values)

    # Track outliers for annotation
    outlier_annotations = []

    for metric_name, values in valid_metrics.items():
        # Use np.nan for None values so lines break at missing data
        plot_values = []
        for i, v in enumerate(values):
            if v is None:
                plot_values.append(np.nan)
            elif y_max_bound is not None and v > y_max_bound:
                # Cap at upper bound and mark for annotation
                plot_values.append(y_max_bound)
                outlier_annotations.append((i, y_max_bound, v, colors.get(metric_name, "#999999"), 'up'))
            elif y_min_bound is not None and v < y_min_bound:
                # Cap at lower bound and mark for annotation
                plot_values.append(y_min_bound)
                outlier_annotations.append((i, y_min_bound, v, colors.get(metric_name, "#999999"), 'down'))
            else:
                plot_values.append(v)

        ax.plot(x, plot_values,
                label=metric_name.replace("_", " ").title(),
                color=colors.get(metric_name, "#999999"),
                linewidth=2,
                marker='o',
                markersize=4)

    # Add outlier annotations
    for x_pos, y_pos, actual_val, color, direction in outlier_annotations:
        if is_percentage:
            label = f'{actual_val:+.0%}'
        else:
            label = f'{actual_val:+.1f}'

        # Position annotation above or below the capped point
        y_offset = 0.02 * (y_max_bound - y_min_bound) if y_max_bound and y_min_bound else 0.02
        if direction == 'up':
            va = 'bottom'
        else:
            va = 'top'
            y_offset = -y_offset

        ax.annotate(label, (x_pos, y_pos),
                    fontsize=5, color=color, fontweight='bold',
                    ha='center', va=va,
                    xytext=(0, 3 if direction == 'up' else -3),
                    textcoords='offset points')
        # Add small arrow indicator
        ax.plot(x_pos, y_pos, marker='^' if direction == 'up' else 'v',
                markersize=5, color=color, markeredgecolor='white', markeredgewidth=0.5)

    # Set axis limits if we have outliers
    if y_min_bound is not None and y_max_bound is not None:
        padding = (y_max_bound - y_min_bound) * 0.1
        ax.set_ylim(y_min_bound - padding, y_max_bound + padding)

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
    ax.xaxis.grid(True, color=COLORS["grid"], linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    # Remove spines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color(COLORS["grid"])

    # Legend
    n_metrics = len(valid_metrics)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
              ncol=min(n_metrics, 4), fontsize=6, frameon=False)

    # Add zero line if it's within the visible range
    y_limits = ax.get_ylim()
    if y_limits[0] < 0 < y_limits[1]:
        ax.axhline(y=0, color=COLORS["text"], linewidth=0.5, linestyle='-')

    fig.tight_layout()
    return fig


def _create_growth_chart(data: FundamentalData) -> str:
    """Create growth metrics line chart (Revenue, EPS, FCF, EBITDA growth %)."""
    quarter_labels = [_format_quarter(q) for q in data.quarters]

    metrics = {
        "revenue": data.revenue_growth,
        "eps": data.eps_growth,
        "fcf": data.fcf_growth,
        "ebitda": data.ebitda_growth,
    }

    colors = {
        "revenue": COLORS["revenue"],
        "eps": COLORS["eps"],
        "fcf": COLORS["fcf"],
        "ebitda": COLORS["ebitda"],
    }

    fig = _create_line_chart(
        quarter_labels=quarter_labels,
        metrics=metrics,
        colors=colors,
        title="Growth (QoQ)",
        ylabel="Change %",
        is_percentage=True,
    )

    return _fig_to_base64(fig)


def _create_profitability_chart(data: FundamentalData) -> str:
    """Create profitability metrics line chart (ROE, ROA, margins)."""
    quarter_labels = [_format_quarter(q) for q in data.quarters]

    metrics = {
        "roe": data.roe,
        "roa": data.roa,
        "gross_margin": data.gross_margin,
        "operating_margin": data.operating_margin,
        "net_margin": data.net_margin,
    }

    colors = {
        "roe": COLORS["roe"],
        "roa": COLORS["roa"],
        "gross_margin": COLORS["gross_margin"],
        "operating_margin": COLORS["operating_margin"],
        "net_margin": COLORS["net_margin"],
    }

    fig = _create_line_chart(
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
