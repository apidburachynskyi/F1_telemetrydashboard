"""
components/charts/racing_line.py
==================================
Animated 2D racing line chart for a single corner.

Shows:
- A 3-layer dark track background
- One racing line per driver (team color or speed heatmap)
- Animated car dots that travel through the corner at REAL speed
  (dots linger where the car brakes, fly through fast sections)
- Apex marker (white X)

Animation is time-correct: dots are resampled uniformly in TIME,
not in space. Computed from distance + speed → cumulative time axis,
then uniformly sampled so the dot velocity reflects actual car speed.

Input:  active_tels - dict mapping driver → {"slc": DataFrame, "color": str,
                                               "lap_info": dict}
        mode        - "team" (solid team color) or "speed" (heatmap)

Output: plotly Figure with animation frames
"""

import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import CubicSpline
from components.shared import (
    TYRE_COLORS,
    BG,
    GRID,
    TEXT,
    FONT,
)

#  Time-correct resampling


def _resample_in_time(slc, n_frames):
    """
    Resample X, Y, Speed onto a uniform TIME grid.
    """
    x = slc["X"].values.astype(float)
    y = slc["Y"].values.astype(float)
    spd = slc["Speed"].values.astype(float)
    dist = slc["RelDist"].values.astype(float)

    # Guard: need at least 2 points and non-zero speed
    if len(x) < 2:
        return (
            np.full(n_frames, x[0]),
            np.full(n_frames, y[0]),
            np.full(n_frames, spd[0]),
        )

    # Speed in m/s (clamp to 1 m/s min to avoid division by zero at rest)
    spd_ms = np.maximum(spd / 3.6, 1.0)

    # Distance differences between consecutive samples
    d_dist = np.abs(np.diff(dist))  # always positive
    d_dist = np.maximum(d_dist, 1e-6)  # avoid zero

    # Time to travel each segment = distance / avg_speed_in_segment
    avg_spd = (spd_ms[:-1] + spd_ms[1:]) / 2.0
    dt = d_dist / avg_spd  # seconds per segment

    # Cumulative time axis (starts at 0)
    cum_t = np.concatenate([[0.0], np.cumsum(dt)])  # shape (n,)
    total_t = cum_t[-1]

    if total_t < 1e-6:
        # Degenerate — fall back to spatial resampling
        return (
            _resample_spatial(x, n_frames),
            _resample_spatial(y, n_frames),
            _resample_spatial(spd, n_frames),
        )

    # Uniform time grid
    t_uniform = np.linspace(0, total_t, n_frames)

    # Interpolate each channel onto uniform time grid
    x_t = np.interp(t_uniform, cum_t, x)
    y_t = np.interp(t_uniform, cum_t, y)
    spd_t = np.interp(t_uniform, cum_t, spd)

    return x_t, y_t, spd_t


def _resample_spatial(arr, n):
    """Fallback: resample array to n points in space"""
    a = np.asarray(arr, dtype=float)
    if len(a) < 4:
        return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(a)), a)
    cs = CubicSpline(np.linspace(0, 1, len(a)), a)
    return cs(np.linspace(0, 1, n))


#  Main build function


def build(active_tels: dict, mode: str = "team", n_frames: int = 30) -> go.Figure:
    """
    Build an animated racing line figure for a corner.

    """
    fig = go.Figure()
    valid = {d: t for d, t in active_tels.items() if not t["slc"].empty}
    if not valid:
        return fig

    #  Track background
    ref = next(iter(valid.values()))["slc"]
    _add_track_layers(fig, ref)

    #  Axis range with padding
    all_x = np.concatenate([t["slc"]["X"].values for t in valid.values()])
    all_y = np.concatenate([t["slc"]["Y"].values for t in valid.values()])
    pad = max((all_x.max() - all_x.min()) * 0.25, 15)
    x_range = [all_x.min() - pad, all_x.max() + pad]
    y_range = [all_y.min() - pad, all_y.max() + pad]

    #  Speed range for colorscale
    if mode == "speed":
        all_spd = np.concatenate([t["slc"]["Speed"].values for t in valid.values()])
        spd_min = np.percentile(all_spd, 2)
        spd_max = np.percentile(all_spd, 98)

    #  Racing lines
    driver_list = list(valid.keys())
    for drv, info in valid.items():
        slc, color = info["slc"], info["color"]
        li = info["lap_info"]
        label = (
            f"{drv}  L{li.get('lap_number','?')}  "
            f"{li.get('compound','')} ({li.get('tyre_life',0)}L)"
        )

        if mode == "speed":
            fig.add_trace(
                go.Scatter(
                    x=slc["X"],
                    y=slc["Y"],
                    mode="markers",
                    marker=dict(
                        size=5,
                        color=slc["Speed"],
                        colorscale=[
                            [0.00, "#e8002d"],
                            [0.40, "#ff6b00"],
                            [0.65, "#ffd700"],
                            [1.00, "#00d2be"],
                        ],
                        cmin=spd_min,
                        cmax=spd_max,
                        showscale=False,
                    ),
                    name=label,
                    customdata=slc["Speed"],
                    hovertemplate=f"<b>{drv}</b>  %{{customdata:.0f}} km/h<extra></extra>",
                )
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=slc["X"],
                    y=slc["Y"],
                    mode="lines",
                    line=dict(color=color, width=6),
                    opacity=0.12,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=slc["X"],
                    y=slc["Y"],
                    mode="lines",
                    line=dict(color=color, width=2),
                    name=label,
                    customdata=slc["Speed"],
                    hovertemplate=f"<b>{drv}</b>  %{{customdata:.0f}} km/h<extra></extra>",
                )
            )

    #  Apex marker
    apex = ref.iloc[(ref["RelDist"].abs()).argmin()]
    fig.add_trace(
        go.Scatter(
            x=[apex["X"]],
            y=[apex["Y"]],
            mode="markers",
            marker=dict(
                size=10, color="#fff", symbol="x", line=dict(width=2, color="#fff")
            ),
            name="Apex",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    #  Precompute time-correct animation paths
    n_static = len(fig.data)

    resampled = {}
    for drv in driver_list:
        slc = valid[drv]["slc"]
        x_t, y_t, s_t = _resample_in_time(slc, n_frames)
        resampled[drv] = {"X": x_t, "Y": y_t, "S": s_t}

    #  Initial car dots
    _add_initial_dots(fig, valid, driver_list, resampled)
    dot_indices = list(range(n_static, len(fig.data)))

    fig.frames = [
        go.Frame(
            data=_frame_data(driver_list, valid, resampled, fi),
            name=str(fi),
            traces=dot_indices,
        )
        for fi in range(n_frames)
    ]

    steps = [
        {
            "args": [
                [str(i)],
                {
                    "frame": {"duration": 40, "redraw": False},
                    "mode": "immediate",
                    "transition": {"duration": 0},
                },
            ],
            "label": "",
            "method": "animate",
        }
        for i in range(n_frames)
    ]

    fig.update_layout(
        paper_bgcolor="#08090d",
        plot_bgcolor="#08090d",
        font=dict(color="#ccc", family=FONT),
        height=420,
        margin=dict(l=0, r=0, t=28, b=60),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=x_range,
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=y_range,
        ),
        legend=dict(
            bgcolor="rgba(8,9,13,0.95)",
            bordercolor="#1a1d24",
            borderwidth=1,
            font=dict(size=11, color="#ccc"),
            orientation="h",
            x=0,
            y=1.06,
        ),
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "y": -0.15,
                "x": 0.5,
                "xanchor": "center",
                "bgcolor": "#1a1d24",
                "bordercolor": GRID,
                "font": {"color": "#ccc", "size": 11},
                "buttons": [
                    {
                        "label": "▶  Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 40, "redraw": False},
                                "fromcurrent": True,
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "⏸  Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "steps": steps,
                "y": -0.08,
                "len": 0.86,
                "x": 0.07,
                "currentvalue": {"visible": False},
                "transition": {"duration": 0},
                "bgcolor": "#1a1d24",
                "bordercolor": GRID,
            }
        ],
        hoverlabel=dict(
            bgcolor="#1a1d24",
            bordercolor=GRID,
            font=dict(color="#fff", size=11),
        ),
    )
    return fig


def _add_track_layers(fig, ref_slc):
    """Draw 3-layer track background + white edge lines."""
    for width, color in [(36, "#14171e"), (26, "#1e2229"), (16, "#262c36")]:
        fig.add_trace(
            go.Scatter(
                x=ref_slc["X"],
                y=ref_slc["Y"],
                mode="lines",
                line=dict(color=color, width=width),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    for width, opacity in [(28, 0.12), (20, 0.07)]:
        fig.add_trace(
            go.Scatter(
                x=ref_slc["X"],
                y=ref_slc["Y"],
                mode="lines",
                line=dict(color="#ffffff", width=width),
                opacity=opacity,
                hoverinfo="skip",
                showlegend=False,
            )
        )


def _add_initial_dots(fig, valid, driver_list, resampled):

    for drv in driver_list:
        color = valid[drv]["color"]
        x0 = resampled[drv]["X"][0]
        y0 = resampled[drv]["Y"][0]
        fig.add_trace(
            go.Scatter(
                x=[x0],
                y=[y0],
                mode="markers",
                marker=dict(size=20, color=color, opacity=0.18),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[x0],
                y=[y0],
                mode="markers+text",
                marker=dict(size=12, color=color, line=dict(width=2, color="#fff")),
                text=[drv],
                textposition="top center",
                textfont=dict(size=9, color="#fff"),
                showlegend=False,
            )
        )


def _frame_data(driver_list, valid, resampled, frame_index):

    data = []
    for drv in driver_list:
        color = valid[drv]["color"]
        xi = resampled[drv]["X"][frame_index]
        yi = resampled[drv]["Y"][frame_index]
        si = resampled[drv]["S"][frame_index]
        data.append(
            go.Scatter(
                x=[xi],
                y=[yi],
                mode="markers",
                marker=dict(size=20, color=color, opacity=0.18),
            )
        )
        data.append(
            go.Scatter(
                x=[xi],
                y=[yi],
                mode="markers+text",
                marker=dict(size=12, color=color, line=dict(width=2, color="#fff")),
                text=[drv],
                textposition="top center",
                textfont=dict(size=9, color="#fff"),
                hovertemplate=f"<b>{drv}</b>  {si:.0f} km/h<extra></extra>",
            )
        )
    return data
