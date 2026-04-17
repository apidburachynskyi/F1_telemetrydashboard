import plotly.graph_objects as go
import numpy as np
from components.shared import BG, GRID, FONT


def build(driver_telemetry: dict, n_frames: int = 100) -> go.Figure:
    """
    ЗРАДА ПОВНА НЕ ПРАЦЮЄ 
    """
    fig     = go.Figure()
    ref_tel = None
    dlist   = []

    # ── Track background (drawn from reference driver's telemetry) ──
    for drv, data in driver_telemetry.items():
        if ref_tel is None:
            ref_tel = data["tel"]
        dlist.append(drv)

    if ref_tel is None:
        return fig

    for width, color in [(28, "#1c1f26"), (20, "#262932"), (13, "#2e333f")]:
        fig.add_trace(go.Scatter(
            x=ref_tel["X"], y=ref_tel["Y"], mode="lines",
            line=dict(color=color, width=width),
            hoverinfo="skip", showlegend=False,
        ))
    for width, opacity in [(22, 0.09), (16, 0.05)]:
        fig.add_trace(go.Scatter(
            x=ref_tel["X"], y=ref_tel["Y"], mode="lines",
            line=dict(color="#fff", width=width), opacity=opacity,
            hoverinfo="skip", showlegend=False,
        ))

    # Start/finish line marker
    fig.add_trace(go.Scatter(
        x=[ref_tel["X"].iloc[0]], y=[ref_tel["Y"].iloc[0]],
        mode="markers+text",
        marker=dict(size=14, color="#fff", symbol="line-ns",
                    line=dict(width=3, color="#fff")),
        text=["S/F"], textposition="middle right",
        textfont=dict(size=10, color="#fff"),
        showlegend=False, hoverinfo="skip",
    ))

    # ── Initial car dots ──────────────────────────────────────
    n_static   = len(fig.data)
    resampled  = {}

    for drv in dlist:
        tel   = driver_telemetry[drv]["tel"]
        color = driver_telemetry[drv]["color"]
        resampled[drv] = {
            "X": _resample(tel["X"].values,     n_frames),
            "Y": _resample(tel["Y"].values,     n_frames),
            "S": _resample(tel["Speed"].values, n_frames),
        }
        x0, y0 = resampled[drv]["X"][0], resampled[drv]["Y"][0]
        # Glow
        fig.add_trace(go.Scatter(
            x=[x0], y=[y0], mode="markers",
            marker=dict(size=20, color=color, opacity=0.18),
            showlegend=False, hoverinfo="skip",
        ))
        # Main dot
        fig.add_trace(go.Scatter(
            x=[x0], y=[y0], mode="markers+text",
            marker=dict(size=12, color=color, line=dict(width=2, color="#fff")),
            text=[drv], textposition="top center",
            textfont=dict(size=9, color="#fff"),
            name=drv, showlegend=True,
            hovertemplate=f"<b>{drv}</b><extra></extra>",
        ))

    dot_indices = list(range(n_static, len(fig.data)))

    # ── Animation frames ──────────────────────────────────────
    fig.frames = [
        go.Frame(
            data=[
                trace
                for drv in dlist
                for trace in [
                    go.Scatter(
                        x=[resampled[drv]["X"][fi]],
                        y=[resampled[drv]["Y"][fi]],
                        mode="markers",
                        marker=dict(
                            size=20,
                            color=driver_telemetry[drv]["color"],
                            opacity=0.18,
                        ),
                    ),
                    go.Scatter(
                        x=[resampled[drv]["X"][fi]],
                        y=[resampled[drv]["Y"][fi]],
                        mode="markers+text",
                        marker=dict(
                            size=12,
                            color=driver_telemetry[drv]["color"],
                            line=dict(width=2, color="#fff"),
                        ),
                        text=[drv],
                        textposition="top center",
                        textfont=dict(size=9, color="#fff"),
                        hovertemplate=(
                            f"<b>{drv}</b>  "
                            f"{resampled[drv]['S'][fi]:.0f} km/h"
                            "<extra></extra>"
                        ),
                    ),
                ]
            ],
            name=str(fi),
            traces=dot_indices,
        )
        for fi in range(n_frames)
    ]

    steps = [
        {
            "args": [[str(i)], {
                "frame": {"duration": 50, "redraw": False},
                "mode": "immediate",
                "transition": {"duration": 0},
            }],
            "label": "",
            "method": "animate",
        }
        for i in range(n_frames)
    ]

    # ── Axis range ────────────────────────────────────────────
    all_x = ref_tel["X"].values
    all_y = ref_tel["Y"].values
    pad   = max((all_x.max() - all_x.min()) * 0.08, 20)

    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color="#ccc", family=FONT),
        height=560,
        margin=dict(l=0, r=0, t=32, b=64),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[all_x.min() - pad, all_x.max() + pad],
            scaleanchor="y", scaleratio=1,
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[all_y.min() - pad, all_y.max() + pad],
        ),
        legend=dict(
            bgcolor="rgba(8,9,13,0.9)", bordercolor=GRID, borderwidth=0.5,
            font=dict(size=10), orientation="h", x=0, y=1.05,
        ),
        updatemenus=[{
            "type": "buttons", "showactive": False,
            "y": -0.11, "x": 0.5, "xanchor": "center",
            "bgcolor": "#1a1d24", "bordercolor": GRID,
            "font": {"color": "#ccc", "size": 11},
            "buttons": [
                {
                    "label": "▶  Play",
                    "method": "animate",
                    "args": [None, {
                        "frame": {"duration": 50, "redraw": False},
                        "fromcurrent": True,
                        "transition": {"duration": 0},
                    }],
                },
                {
                    "label": "⏸  Pause",
                    "method": "animate",
                    "args": [[None], {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate",
                        "transition": {"duration": 0},
                    }],
                },
            ],
        }],
        sliders=[{
            "active": 0, "steps": steps,
            "y": -0.06, "len": 0.86, "x": 0.07,
            "currentvalue": {"visible": False},
            "transition": {"duration": 0},
            "bgcolor": "#1a1d24", "bordercolor": GRID,
        }],
        hoverlabel=dict(
            bgcolor="#1a1d24", bordercolor=GRID,
            font=dict(color="#fff", size=11),
        ),
    )
    return fig


def _resample(arr, n):
    """Resample array to n points using linear interpolation."""
    a = np.asarray(arr, dtype=float)
    if len(a) < 2:
        return np.full(n, a[0] if len(a) == 1 else 0.0)
    return np.interp(
        np.linspace(0, 1, n),
        np.linspace(0, 1, len(a)),
        a,
    )
