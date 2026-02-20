"""Render Plotly figures to PNG bytes using matplotlib. No kaleido needed."""

import logging
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

# Chart dimensions
WIDTH = 10
HEIGHT = 6
DPI = 150

COLORS = [
    "#1B365D",
    "#4A90D9",
    "#2ECC71",
    "#E74C3C",
    "#F39C12",
    "#9B59B6",
    "#1ABC9C",
    "#E67E22",
]


def plotly_to_png(fig: go.Figure) -> bytes:
    """Convert a Plotly figure to PNG bytes via matplotlib."""
    mpl_fig, ax = plt.subplots(figsize=(WIDTH, HEIGHT), dpi=DPI)

    title = ""
    if fig.layout.title and fig.layout.title.text:
        title = fig.layout.title.text

    has_secondary_y = any(getattr(t, "yaxis", None) == "y2" for t in fig.data)
    has_secondary_x = any(getattr(t, "xaxis", None) == "x2" for t in fig.data)

    ax2_y = ax.twinx() if has_secondary_y else None
    ax2_x = ax.twiny() if has_secondary_x else None

    for i, trace in enumerate(fig.data):
        color = COLORS[i % len(COLORS)]
        if hasattr(trace, "marker") and trace.marker and trace.marker.color:
            color = trace.marker.color
        if hasattr(trace, "line") and trace.line and trace.line.color:
            color = trace.line.color

        target_ax = ax
        if getattr(trace, "yaxis", None) == "y2" and ax2_y:
            target_ax = ax2_y
        if getattr(trace, "xaxis", None) == "x2" and ax2_x:
            target_ax = ax2_x

        label = trace.name or f"trace_{i}"

        if isinstance(trace, go.Bar):
            _render_bar(target_ax, trace, color, label, fig)
        elif isinstance(trace, go.Scatter):
            _render_scatter(target_ax, trace, color, label)
        elif isinstance(trace, go.Pie):
            _render_pie(ax, trace, mpl_fig)
        elif isinstance(trace, go.Heatmap):
            _render_heatmap(ax, trace, mpl_fig)

    if title:
        mpl_fig.suptitle(title, fontsize=12, fontweight="bold", y=0.98)

    _apply_axis_labels(ax, fig, ax2_y)

    ax.grid(False)
    if ax2_y:
        ax2_y.grid(False)

    handles, labels = ax.get_legend_handles_labels()
    if ax2_y:
        h2, l2 = ax2_y.get_legend_handles_labels()
        handles += h2
        labels += l2
    if labels:
        ax.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.08),
            ncol=min(len(labels), 4),
            fontsize=8,
        )

    mpl_fig.tight_layout(rect=[0, 0.03, 1, 0.95])

    buf = BytesIO()
    mpl_fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight")
    plt.close(mpl_fig)
    buf.seek(0)
    return buf.read()


def _render_bar(ax, trace, color, label, fig):
    """Render a Bar trace."""
    orientation = getattr(trace, "orientation", None)
    if orientation == "h":
        y_vals = list(trace.y) if trace.y is not None else []
        x_vals = list(trace.x) if trace.x is not None else []
        y_pos = range(len(y_vals))
        ax.barh(y_pos, x_vals, color=color, label=label, alpha=0.85)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels([str(v) for v in y_vals], fontsize=8)
    else:
        x_vals = list(trace.x) if trace.x is not None else []
        y_vals = list(trace.y) if trace.y is not None else []
        x_labels = [str(v) for v in x_vals]

        # Offset bars when multiple bar traces exist
        bar_width = 0.4
        x_pos = np.arange(len(x_labels))

        ax.bar(x_pos, y_vals, width=bar_width, color=color, label=label, alpha=0.85)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)


def _render_scatter(ax, trace, color, label):
    """Render a Scatter trace as a line chart."""
    x_vals = list(trace.x) if trace.x is not None else []
    y_vals = list(trace.y) if trace.y is not None else []

    linestyle = "-"
    if hasattr(trace, "line") and trace.line and trace.line.dash:
        dash_map = {"dash": "--", "dot": ":", "dashdot": "-."}
        linestyle = dash_map.get(trace.line.dash, "-")

    marker = "o"
    mode = getattr(trace, "mode", "lines+markers") or "lines+markers"
    show_markers = "markers" in mode
    show_lines = "lines" in mode

    if show_lines and show_markers:
        ax.plot(
            x_vals,
            y_vals,
            color=color,
            label=label,
            marker=marker,
            markersize=5,
            linestyle=linestyle,
            linewidth=1.5,
        )
    elif show_lines:
        ax.plot(
            x_vals,
            y_vals,
            color=color,
            label=label,
            linestyle=linestyle,
            linewidth=1.5,
        )
    elif show_markers:
        ax.scatter(x_vals, y_vals, color=color, label=label, s=30)

    if len(x_vals) > 6:
        ax.tick_params(axis="x", rotation=45)


def _render_pie(ax, trace, mpl_fig):
    """Render a Pie trace."""
    ax.clear()
    labels = list(trace.labels) if trace.labels is not None else []
    values = list(trace.values) if trace.values is not None else []

    hole = 0
    if hasattr(trace, "hole") and trace.hole:
        hole = trace.hole

    colors = COLORS[: len(labels)]
    if hasattr(trace, "marker") and trace.marker and trace.marker.colors:
        colors = list(trace.marker.colors)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.75,
    )

    if hole > 0:
        centre = plt.Circle((0, 0), hole, fc="white")
        ax.add_patch(centre)

    for t in texts:
        t.set_fontsize(8)
    for t in autotexts:
        t.set_fontsize(7)


def _render_heatmap(ax, trace, mpl_fig):
    """Render a Heatmap trace."""
    ax.clear()
    z = np.array(trace.z) if trace.z is not None else np.array([])
    x = list(trace.x) if trace.x is not None else []
    y = list(trace.y) if trace.y is not None else []

    if z.size == 0:
        return

    im = ax.imshow(z, aspect="auto", cmap="Blues")
    mpl_fig.colorbar(im, ax=ax, shrink=0.8)

    if x:
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels([str(v) for v in x], rotation=45, ha="right", fontsize=8)
    if y:
        ax.set_yticks(range(len(y)))
        ax.set_yticklabels([str(v) for v in y], fontsize=8)

    # Add text annotations
    for row_i in range(z.shape[0]):
        for col_i in range(z.shape[1]):
            val = z[row_i, col_i]
            ax.text(
                col_i,
                row_i,
                f"{int(val)}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if val > z.max() * 0.6 else "black",
            )


def _apply_axis_labels(ax, fig, ax2_y):
    """Apply axis labels from Plotly layout."""
    layout = fig.layout

    if layout.xaxis and layout.xaxis.title:
        title = layout.xaxis.title
        if isinstance(title, dict):
            ax.set_xlabel(title.get("text", ""), fontsize=9)
        elif hasattr(title, "text") and title.text:
            ax.set_xlabel(title.text, fontsize=9)

    if layout.yaxis and layout.yaxis.title:
        title = layout.yaxis.title
        if isinstance(title, dict):
            ax.set_ylabel(title.get("text", ""), fontsize=9)
        elif hasattr(title, "text") and title.text:
            ax.set_ylabel(title.text, fontsize=9)

    if ax2_y and layout.yaxis2 and layout.yaxis2.title:
        title = layout.yaxis2.title
        if isinstance(title, dict):
            ax2_y.set_ylabel(title.get("text", ""), fontsize=9)
        elif hasattr(title, "text") and title.text:
            ax2_y.set_ylabel(title.text, fontsize=9)


def render_all_chart_pngs(
    charts: dict[str, go.Figure],
) -> dict[str, bytes]:
    """Render all Plotly charts to PNG bytes using matplotlib."""
    if not charts:
        return {}

    pngs: dict[str, bytes] = {}
    total = len(charts)
    for i, (name, fig) in enumerate(charts.items(), start=1):
        try:
            logger.info("  Rendering chart [%d/%d] %s", i, total, name)
            pngs[name] = plotly_to_png(fig)
        except Exception as e:
            logger.warning("  Chart PNG for '%s' failed: %s", name, e)
    return pngs
