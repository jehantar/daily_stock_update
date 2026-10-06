"""Attach current quarterly statement context to a reported earnings event."""

from datetime import timedelta

from src.earnings_tracker import EarningsEvent, FundamentalContext
from src.fundamentals_fetcher import FundamentalData


MAX_REPORT_LAG_DAYS = 100


def _value(data: FundamentalData, field: str, index: int | None) -> float | None:
    if index is None:
        return None
    values = getattr(data, field, None)
    return values[index] if values and index < len(values) else None


def _change(current: float | None, prior: float | None) -> float | None:
    if current is None or prior in (None, 0):
        return None
    return (current - prior) / abs(prior) * 100


def _matching_quarter(event: EarningsEvent, data: FundamentalData) -> int | None:
    """Skip statements that have not yet caught up with this earnings release."""
    matches = [
        index for index, quarter in enumerate(data.quarters)
        if 0 <= (event.date.date() - quarter.date()).days <= MAX_REPORT_LAG_DAYS
    ]
    return matches[-1] if matches else None


def attach_fundamental_context(event: EarningsEvent, data: FundamentalData) -> bool:
    """Use the latest matching fiscal quarter; leave stale or sparse data out."""
    index = _matching_quarter(event, data)
    if index is None:
        return False

    quarter = data.quarters[index]
    prior = index - 1 if index > 0 and 60 <= (quarter - data.quarters[index - 1]).days <= 120 else None
    year_ago_date = quarter - timedelta(days=365)
    year_ago = min(
        (i for i in range(index) if abs((data.quarters[i] - year_ago_date).days) <= 30),
        key=lambda i: abs((data.quarters[i] - year_ago_date).days),
        default=None,
    )

    revenue = _value(data, "revenue", index)
    eps = _value(data, "eps", index)
    fcf = _value(data, "fcf_values", index)
    capex = _value(data, "capex_values", index)
    gross_margin = _value(data, "gross_margin", index)
    net_margin = _value(data, "net_margin", index)
    operating_margin = _value(data, "operating_margin", index)
    if all(value is None for value in (revenue, eps, fcf, capex, gross_margin, net_margin, operating_margin)):
        return False

    event.fundamental_context = FundamentalContext(
        revenue=revenue,
        eps=eps,
        financial_currency=data.financial_currency,
        revenue_qoq_change=_change(revenue, _value(data, "revenue", prior)),
        eps_qoq_change=_change(eps, _value(data, "eps", prior)),
        fcf=fcf,
        fcf_qoq_change=_change(fcf, _value(data, "fcf_values", prior)),
        capex=capex,
        capex_qoq_change=_change(capex, _value(data, "capex_values", prior)),
        gross_margin=gross_margin,
        gross_margin_prior=_value(data, "gross_margin", prior),
        net_margin=net_margin,
        net_margin_prior=_value(data, "net_margin", prior),
        operating_margin=operating_margin,
        operating_margin_prior=_value(data, "operating_margin", prior),
        revenue_yoy_change=_change(revenue, _value(data, "revenue", year_ago)),
        eps_yoy_change=_change(eps, _value(data, "eps", year_ago)),
        fcf_yoy_change=_change(fcf, _value(data, "fcf_values", year_ago)),
        capex_yoy_change=_change(capex, _value(data, "capex_values", year_ago)),
        gross_margin_yoy=_value(data, "gross_margin", year_ago),
        net_margin_yoy=_value(data, "net_margin", year_ago),
        operating_margin_yoy=_value(data, "operating_margin", year_ago),
    )
    return True
