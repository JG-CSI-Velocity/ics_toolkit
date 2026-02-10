"""Charts for source analyses (ax08-ax13)."""

import plotly.graph_objects as go

from ics_toolkit.settings import ChartConfig

LAYOUT_DEFAULTS = dict(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, b=40),
)


def chart_source_dist(df, config: ChartConfig) -> go.Figure:
    """ax08: Bar chart of ICS accounts by Source."""
    data = df[df["Source"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Bar(
            x=data["Source"],
            y=data["Count"],
            marker_color=colors[0],
            text=data["Count"],
            textposition="outside",
        )
    )

    fig.update_layout(
        template=config.theme,
        xaxis_title="Source",
        yaxis_title="Count",
        **LAYOUT_DEFAULTS,
    )
    return fig


def chart_account_type(df, config: ChartConfig) -> go.Figure:
    """ax12: Pie chart of Personal vs Business ICS accounts."""
    data = df[df["Business?"] != "Total"].copy()
    colors = config.colors

    fig = go.Figure(
        go.Pie(
            labels=data["Business?"],
            values=data["Count"],
            marker=dict(colors=colors[: len(data)]),
            textinfo="label+percent+value",
            hole=0.35,
        )
    )

    fig.update_layout(template=config.theme, **LAYOUT_DEFAULTS)
    return fig
