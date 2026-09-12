"""Shared Plotly chart builders for the app.

Color choices follow the dataviz skill's validated default palette
(references/palette.md): WOE is a diverging measure around zero (positive
WOE = safer = blue, negative = riskier = red) so it uses the blue<->red
diverging pair, not an arbitrary rainbow; a predicted-vs-observed comparison
uses two categorical slots (blue, orange); PSI status uses the fixed
good/warning/critical status colors, never a categorical slot. Every chart
below carries hover text — an HTML/interactive chart ships with a hover
layer by default, not as an afterthought.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

BLUE = "#2a78d6"    # diverging pole: safer / positive WOE; categorical slot 1
RED = "#e34948"     # diverging pole: riskier / negative WOE; categorical slot 8
ORANGE = "#eb6834"  # categorical slot 2 — second series in a two-series comparison
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
MUTED = "#898781"
INK = "#0b0b0b"

STATUS_COLOR = {
    "stable": "#0ca30c",
    "moderate shift — monitor": "#fab219",
    "significant shift — investigate": "#d03b3b",
}

_AXIS_STYLE = dict(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=BASELINE)


def woe_bar_chart(binning_table: pd.DataFrame, feature_name: str) -> go.Figure:
    """Bar chart of WoE per bin — blue above zero (safer), red below (riskier).

    `optbinning`'s binning table carries a summary row indexed "Totals" (not a
    value in the "Bin" column, which is blank for that row) — it must be
    dropped by index, and the WoE/IV columns come back as object dtype
    because of that blank value, so they're coerced to numeric here.
    """
    df = binning_table.drop(index="Totals", errors="ignore").copy()
    df["WoE"] = pd.to_numeric(df["WoE"], errors="coerce")
    colors = [BLUE if w >= 0 else RED for w in df["WoE"]]
    hover = [
        f"Bin: {b}<br>Count: {c:,}<br>Event rate: {r:.2%}<br>WoE: {w:.3f}"
        for b, c, r, w in zip(df["Bin"], df["Count"], df["Event rate"], df["WoE"])
    ]

    fig = go.Figure(
        go.Bar(
            x=df["Bin"].astype(str),
            y=df["WoE"],
            marker_color=colors,
            hovertext=hover,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        title=f"WoE by bin — {feature_name}",
        xaxis=dict(title="Bin", **_AXIS_STYLE),
        yaxis=dict(title="WoE (higher = safer)", **_AXIS_STYLE),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color=INK),
        showlegend=False,
        margin=dict(t=48, b=40),
    )
    return fig


def roc_chart(fpr, tpr, auc: float) -> go.Figure:
    """ROC curve (blue) against the chance diagonal (dashed muted gray).

    Takes precomputed (fpr, tpr) points — saved by src/pipeline/train.py as
    models/give-me-some-credit/roc_curve.csv — rather than raw predictions,
    so this chart never needs the raw data or a live model call to render.
    """
    hover = [f"FPR: {f:.3f}<br>TPR: {t:.3f}" for f, t in zip(fpr, tpr)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=fpr, y=tpr, mode="lines", name=f"Model (AUC={auc:.3f})",
            line=dict(color=BLUE, width=2), hovertext=hover, hoverinfo="text",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0, 1], y=[0, 1], mode="lines", name="Chance",
            line=dict(color=BASELINE, width=2, dash="dash"), hoverinfo="skip",
        )
    )
    fig.update_layout(
        title="ROC curve",
        xaxis=dict(title="False positive rate", range=[0, 1], **_AXIS_STYLE),
        yaxis=dict(title="True positive rate", range=[0, 1], **_AXIS_STYLE),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color=INK),
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=48, b=40),
    )
    return fig


def calibration_chart(calib_table: pd.DataFrame) -> go.Figure:
    """Predicted vs. observed default rate by score band — one shared rate axis."""
    x = list(range(1, len(calib_table) + 1))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x, y=calib_table["predicted_rate"], mode="lines+markers", name="Predicted",
            line=dict(color=BLUE, width=2), marker=dict(size=8),
            hovertext=[f"Bin {i}<br>Predicted: {v:.2%}" for i, v in zip(x, calib_table["predicted_rate"])],
            hoverinfo="text",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=calib_table["observed_rate"], mode="lines+markers", name="Observed",
            line=dict(color=ORANGE, width=2), marker=dict(size=8),
            hovertext=[f"Bin {i}<br>Observed: {v:.2%}" for i, v in zip(x, calib_table["observed_rate"])],
            hoverinfo="text",
        )
    )
    fig.update_layout(
        title="Calibration — predicted vs. observed default rate by score band",
        xaxis=dict(title="Score band (1 = riskiest)", dtick=1, **_AXIS_STYLE),
        yaxis=dict(title="Default rate", tickformat=".0%", **_AXIS_STYLE),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color=INK),
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=48, b=40),
    )
    return fig


def histogram(series: pd.Series, title: str, nbins: int = 40) -> go.Figure:
    """Single-hue distribution histogram (sequential blue)."""
    fig = go.Figure(go.Histogram(x=series.dropna(), nbinsx=nbins, marker_color=BLUE))
    fig.update_layout(
        title=title,
        xaxis=dict(title=series.name, **_AXIS_STYLE),
        yaxis=dict(title="Count", **_AXIS_STYLE),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color=INK),
        showlegend=False,
        margin=dict(t=48, b=40),
        bargap=0.02,
    )
    return fig


def histogram_from_bins(counts: list[float], bin_edges: list[float], title: str, x_title: str) -> go.Figure:
    """Distribution histogram from precomputed bin counts (src/data/profile.py) —
    used when the raw values themselves aren't available (e.g. hosted deployment)."""
    centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]
    widths = [bin_edges[i + 1] - bin_edges[i] for i in range(len(bin_edges) - 1)]
    fig = go.Figure(go.Bar(x=centers, y=counts, width=widths, marker_color=BLUE))
    fig.update_layout(
        title=title,
        xaxis=dict(title=x_title, **_AXIS_STYLE),
        yaxis=dict(title="Count", **_AXIS_STYLE),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color=INK),
        showlegend=False,
        margin=dict(t=48, b=40),
        bargap=0.02,
    )
    return fig


def target_rate_bar(default_rate: float) -> go.Figure:
    """A single-bar view of the overall default vs. non-default split."""
    fig = go.Figure(
        go.Bar(
            x=["Non-default", "Default"],
            y=[1 - default_rate, default_rate],
            marker_color=[BLUE, RED],
            text=[f"{1 - default_rate:.1%}", f"{default_rate:.1%}"],
            textposition="outside",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        title="Target distribution",
        yaxis=dict(title="Share", tickformat=".0%", **_AXIS_STYLE),
        xaxis=dict(**_AXIS_STYLE),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color=INK),
        showlegend=False,
        margin=dict(t=48, b=40),
    )
    return fig
