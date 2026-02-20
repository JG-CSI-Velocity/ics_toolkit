"""Charts for portfolio analyses: Engagement Decay, Net Growth, Concentration."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_engagement_decay(df, config: ChartConfig) -> go.Figure:
    """Stacked bar of engagement decay categories."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Decay Category"],
            y=df["Count"],
            marker_color=colors[: len(df)],
            text=df["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Category",
        yaxis_title="Account Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_net_portfolio_growth(df, config: ChartConfig) -> go.Figure:
    """Dual-axis: bars for net opens/closes + cumulative line."""
    colors = config.colors

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Month"],
            y=df["Cumulative"],
            name="Cumulative Net",
            mode="lines+markers",
            marker=dict(color=colors[2], size=6),
            line=dict(color=colors[2], width=2),
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["Month"],
            y=df["Opens"],
            name="Opens",
            marker_color=colors[0],
            yaxis="y2",
        )
    )

    closes_neg = -pd.to_numeric(df["Closes"], errors="coerce").fillna(0)
    fig.add_trace(
        go.Bar(
            x=df["Month"],
            y=closes_neg,
            name="Closes",
            marker_color=colors[4] if len(colors) > 4 else colors[-1],
            yaxis="y2",
        )
    )

    # Align zero on both axes so the zero lines match visually
    y1_range, y2_range = _align_dual_axis_zero(
        y1_values=list(df["Cumulative"]),
        y2_values=list(df["Opens"]) + list(closes_neg),
    )

    fig.update_layout(
        template=config.theme,
        barmode="relative",
        xaxis_title="Month",
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="Cumulative Net", range=y1_range),
        yaxis2=dict(
            title="Opens / Closes",
            side="right",
            overlaying="y",
            range=y2_range,
        ),
        **LAYOUT_DEFAULTS,
    )
    return fig


def _align_dual_axis_zero(
    y1_values: list,
    y2_values: list,
    pad: float = 0.15,
) -> tuple[list[float], list[float]]:
    """Compute axis ranges so zero is at the same vertical position.

    Returns ([y1_lo, y1_hi], [y2_lo, y2_hi]).
    """
    y1_nums = [float(v) for v in y1_values if v is not None]
    y2_nums = [float(v) for v in y2_values if v is not None]

    if not y1_nums or not y2_nums:
        return [0, 1], [0, 1]

    y1_min, y1_max = min(y1_nums), max(y1_nums)
    y2_min, y2_max = min(y2_nums), max(y2_nums)

    # Add padding
    y1_span = y1_max - y1_min or 1
    y1_lo = y1_min - pad * y1_span
    y1_hi = y1_max + pad * y1_span

    # Where is zero on the primary axis (fraction from bottom)?
    y1_total = y1_hi - y1_lo
    zero_frac = (0 - y1_lo) / y1_total

    # Set secondary max with padding, then compute lo so zero aligns
    y2_span = y2_max - y2_min or 1
    y2_hi = y2_max + pad * y2_span

    # Solve: zero_frac = (0 - y2_lo) / (y2_hi - y2_lo)
    #   => y2_lo = -zero_frac * y2_hi / (1 - zero_frac)
    if zero_frac >= 1.0:
        y2_lo = y2_min - pad * y2_span
    else:
        y2_lo = -zero_frac * y2_hi / (1 - zero_frac)

    return [y1_lo, y1_hi], [y2_lo, y2_hi]


def chart_concentration(df, config: ChartConfig) -> go.Figure:
    """Bar chart showing spend share by percentile."""
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=df["Percentile"],
            y=pd.to_numeric(df["Spend Share %"], errors="coerce"),
            marker_color=colors[: len(df)],
            text=df["Spend Share %"].apply(
                lambda v: f"{v:.1f}%" if isinstance(v, (int, float)) else str(v)
            ),
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Percentile",
        yaxis_title="% of Total Spend",
        **LAYOUT_DEFAULTS,
    )
    return fig
