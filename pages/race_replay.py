import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, callback, clientside_callback

from components.perf_metrics import tab_timer
from components.shared import (
    BG2,
    GRID,
    TEXT,
    ACCENT,
    FONT,
    get_cached_session,
    get_driver_meta,
)

_FRAMES_BY_SPEED = {0.5: 120, 1.0: 60, 2.0: 30, 4.0: 15}
N_TRACK_PTS = 200  # GPS resample resolution


def _resample(arr, n):
    a = np.asarray(arr, dtype=float)
    if len(a) < 2:
        return np.full(n, a[0] if len(a) == 1 else 0.0)
    return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(a)), a)


def _load_replay_data(session, drivers, n_frames_per_lap=60):
    """
    Returns dict per driver:
    color, track_x, track_y (resampled GPS),
    cum_time (seconds), cum_dist (0..1 fraction of track, per frame)

    Only ONE telemetry call per driver (fastest lap).
    Lap times come from session.laps (already in RAM).
    """
    driver_data = {}
    ref_x = ref_y = None

    for drv in drivers:
        try:
            meta = get_driver_meta(session, drv)
            laps_drv = session.laps.pick_drivers(drv)
            if laps_drv.empty:
                continue

            # Fastest lap GPS shape
            fastest = laps_drv.pick_fastest()
            if fastest is None or fastest.empty:
                continue
            tel = fastest.get_telemetry().add_distance()
            tx = _resample(tel["X"].values, N_TRACK_PTS)
            ty = _resample(tel["Y"].values, N_TRACK_PTS)
            if ref_x is None:
                ref_x, ref_y = tel["X"].values, tel["Y"].values

            # All valid lap times cumulative race time
            valid_laps = laps_drv[laps_drv["LapTime"].notna()].sort_values("LapNumber")
            if valid_laps.empty:
                continue

            lap_times = valid_laps["LapTime"].dt.total_seconds().values
            lap_nums = valid_laps["LapNumber"].values.astype(int)

            # Cumulative time at end of each lap
            cum_time = np.cumsum(lap_times)  # seconds
            total_laps = int(lap_nums[-1])

            # DOESNT WORK DOESNT MATTER NEED REBUILD

            n_laps = len(lap_times)
            n_frames = n_laps * n_frames_per_lap
            total_time = cum_time[-1]
            frame_times = np.linspace(0, total_time, n_frames)

            TRACK_LENGTH = N_TRACK_PTS

            cum_time_ext = np.concatenate([[0.0], cum_time])
            cum_dist_ext = np.arange(len(cum_time_ext), dtype=float) * TRACK_LENGTH

            progress = np.interp(frame_times, cum_time_ext, cum_dist_ext)

            track_indices = (progress % TRACK_LENGTH).astype(int)
            track_indices = np.clip(track_indices, 0, N_TRACK_PTS - 1)

            driver_data[drv] = {
                "color": meta["color"],
                "track_x": tx,
                "track_y": ty,
                "track_indices": track_indices,
                "n_frames": n_frames,
                "total_laps": total_laps,
                "total_time": float(total_time),
                "cum_time_ext": cum_time_ext,
                "cum_dist_ext": cum_dist_ext,
            }

        except Exception:
            continue

    return driver_data, ref_x, ref_y


def build_static_fig(ref_x, ref_y, driver_data, dlist):
    """Build track initial car dots"""
    fig = go.Figure()

    tx = _resample(ref_x, N_TRACK_PTS)
    ty = _resample(ref_y, N_TRACK_PTS)

    # Track layers
    for w, c in [(32, "#14171e"), (22, "#1e2229"), (13, "#262c36")]:
        fig.add_trace(
            go.Scatter(
                x=tx,
                y=ty,
                mode="lines",
                line=dict(color=c, width=w),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    for w, op in [(24, 0.11), (16, 0.06)]:
        fig.add_trace(
            go.Scatter(
                x=tx,
                y=ty,
                mode="lines",
                line=dict(color="#fff", width=w),
                opacity=op,
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # S/F line
    fig.add_trace(
        go.Scatter(
            x=[tx[0]],
            y=[ty[0]],
            mode="markers+text",
            marker=dict(
                size=12,
                color="#fff",
                symbol="line-ns",
                line=dict(width=3, color="#fff"),
            ),
            text=["S/F"],
            textposition="middle right",
            textfont=dict(size=9, color="#fff"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    n_static = len(fig.data)

    # Initial car dots at frame 0
    for drv in dlist:
        d = driver_data[drv]
        color = d["color"]
        idx0 = d["track_indices"][0]
        x0, y0 = d["track_x"][idx0], d["track_y"][idx0]

        fig.add_trace(
            go.Scatter(
                x=[x0],
                y=[y0],
                mode="markers",
                marker=dict(size=24, color=color, opacity=0.20),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[x0],
                y=[y0],
                mode="markers+text",
                marker=dict(size=13, color=color, line=dict(width=2.5, color="#fff")),
                text=[drv],
                textposition="top center",
                textfont=dict(size=11, color="#fff"),
                name=drv,
                showlegend=True,
                hovertemplate=f"<b>{drv}</b><extra></extra>",
            )
        )

    dot_indices = list(range(n_static, len(fig.data)))

    all_x = np.concatenate([ref_x, tx])
    all_y = np.concatenate([ref_y, ty])
    pad = max((all_x.max() - all_x.min()) * 0.08, 20)

    fig.update_layout(
        paper_bgcolor="#08090d",
        plot_bgcolor="#08090d",
        font=dict(color="#ccc", family=FONT),
        height=520,
        margin=dict(l=0, r=0, t=32, b=72),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[all_x.min() - pad, all_x.max() + pad],
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[all_y.min() - pad, all_y.max() + pad],
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
        hoverlabel=dict(
            bgcolor="#1a1d24", bordercolor=GRID, font=dict(color="#fff", size=11)
        ),
    )
    return fig, n_static, dot_indices


def add_animation(fig, driver_data, dlist, dot_indices, speed=1.0, n_frames_per_lap=60):
    """Add animation frames and controls to the static figure."""
    # Global time axis
    total_time = max(d["total_time"] for d in driver_data.values())
    total_laps = max(d["total_laps"] for d in driver_data.values())
    n_frames = total_laps * n_frames_per_lap

    # Global frame times (same for every driver)
    global_frame_times = np.linspace(0, total_time, n_frames)

    # Drivers who finished earlier stay at their final position.
    TRACK_LENGTH = N_TRACK_PTS
    for drv in dlist:
        d = driver_data[drv]
        cum_t = d["cum_time_ext"]
        cum_d = d["cum_dist_ext"]
        # Clamp time to driver's own race end they stop at finish
        t_clamped = np.minimum(global_frame_times, cum_t[-1])
        progress = np.interp(t_clamped, cum_t, cum_d)
        d["track_indices"] = np.clip(
            (progress % TRACK_LENGTH).astype(int), 0, N_TRACK_PTS - 1
        )

    frame_duration_ms = max(16, int(50 / speed))
    frames_per_lap = n_frames_per_lap

    # only update dot traces
    fig.frames = [
        go.Frame(
            data=[
                trace for drv in dlist for trace in _frame_traces(driver_data[drv], fi)
            ],
            name=str(fi),
            traces=dot_indices,
        )
        for fi in range(n_frames)
    ]

    lap_steps = []
    for lap in range(total_laps + 1):
        fi = min(lap * frames_per_lap, n_frames - 1)
        lap_steps.append(
            {
                "args": [
                    [str(fi)],
                    {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate",
                        "transition": {"duration": 0},
                    },
                ],
                "label": str(lap),
                "method": "animate",
            }
        )

    fig.update_layout(
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "y": -0.13,
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
                                "frame": {
                                    "duration": frame_duration_ms,
                                    "redraw": False,
                                },
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
                "steps": lap_steps,
                "y": -0.07,
                "len": 0.86,
                "x": 0.07,
                "currentvalue": {
                    "prefix": "Lap: ",
                    "font": {"color": "#888", "size": 10},
                    "visible": True,
                    "xanchor": "left",
                },
                "transition": {"duration": 0},
                "bgcolor": "#1a1d24",
                "bordercolor": GRID,
            }
        ],
    )
    return fig


def _frame_traces(d, fi):
    """Return (glow, dot) traces for one driver at frame fi."""
    color = d["color"]
    n = d["n_frames"]
    idx = d["track_indices"][min(fi, n - 1)]
    x, y = d["track_x"][idx], d["track_y"][idx]
    return [
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers",
            marker=dict(size=18, color=color, opacity=0.18),
        ),
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            marker=dict(size=11, color=color, line=dict(width=2, color="#fff")),
            text=[d.get("drv", "")],
            textposition="top center",
            textfont=dict(size=9, color="#fff"),
        ),
    ]


def build_replay(session_key, drivers, speed=1.0):
    """Full pipeline"""
    if not session_key:
        return go.Figure()
    try:
        year, gp, stype = session_key.split("|")
        session = get_cached_session(int(year), gp, stype)
    except Exception:
        return go.Figure()

    n_frames_per_lap = _FRAMES_BY_SPEED.get(speed, 60)
    driver_data, ref_x, ref_y = _load_replay_data(session, drivers, n_frames_per_lap)
    if not driver_data or ref_x is None:
        return go.Figure()

    dlist = list(driver_data.keys())
    for drv in dlist:
        driver_data[drv]["drv"] = drv

    fig, n_static, dot_indices = build_static_fig(ref_x, ref_y, driver_data, dlist)
    fig = add_animation(
        fig,
        driver_data,
        dlist,
        dot_indices,
        speed=speed,
        n_frames_per_lap=n_frames_per_lap,
    )
    fig.update_layout(uirevision=f"{session_key}-{speed}-{','.join(sorted(drivers))}")
    return fig


# Page layout & callbacks─


def empty():
    return html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
            "minHeight": "50vh",
            "gap": "12px",
        },
        children=[
            html.Div(
                "🏁",
                style={
                    "fontSize": "36px",
                    "background": "#1a0508",
                    "borderRadius": "12px",
                    "padding": "12px 16px",
                },
            ),
            html.Div(
                "NO SESSION LOADED",
                style={
                    "fontSize": "14px",
                    "fontWeight": "700",
                    "letterSpacing": "2px",
                    "color": TEXT,
                },
            ),
        ],
    )


layout = dcc.Loading(
    id="replay-loading",
    type="circle",
    color="#e8002d",
    style={
        "position": "fixed",
        "top": "50%",
        "left": "50%",
        "transform": "translate(-50%,-50%)",
        "zIndex": "999",
    },
    children=html.Div(id="replay-container", children=[empty()]),
)


@callback(
    Output("replay-container", "children"),
    Input("store-race", "data"),
    Input("store-session-key", "data"),
    Input("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
@tab_timer("replay")
def render(store, session_key, selected_drivers):
    if not store or not session_key:
        return empty()
    drivers = selected_drivers or [d["drv"] for d in store.get("drivers", [])]
    ev = store.get("event", {})

    return html.Div(
        [
            html.Div(
                style={
                    "background": BG2,
                    "border": f"1px solid {GRID}",
                    "borderRadius": "8px",
                    "padding": "18px 20px",
                    "boxShadow": "0 2px 12px rgba(0,0,0,0.3)",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "marginBottom": "12px",
                            "flexWrap": "wrap",
                            "gap": "12px",
                        },
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "8px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "width": "3px",
                                            "height": "18px",
                                            "background": ACCENT,
                                            "borderRadius": "2px",
                                        }
                                    ),
                                    html.Div(
                                        "2D RACE REPLAY",
                                        style={
                                            "fontSize": "11px",
                                            "fontWeight": "700",
                                            "letterSpacing": "2.5px",
                                            "color": TEXT,
                                        },
                                    ),
                                ],
                            ),
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "10px",
                                },
                                children=[
                                    html.Span(
                                        "SPEED:",
                                        style={
                                            "fontSize": "10px",
                                            "color": "#555",
                                            "fontWeight": "700",
                                            "letterSpacing": "1px",
                                        },
                                    ),
                                    dcc.RadioItems(
                                        id="replay-speed",
                                        options=[
                                            {"label": "0.5×", "value": 0.5},
                                            {"label": "1×", "value": 1.0},
                                            {"label": "2×", "value": 2.0},
                                            {"label": "4×", "value": 4.0},
                                        ],
                                        value=1.0,
                                        inline=True,
                                        labelStyle={
                                            "marginLeft": "10px",
                                            "fontSize": "11px",
                                            "color": "#888",
                                            "cursor": "pointer",
                                        },
                                        inputStyle={
                                            "marginRight": "4px",
                                            "accentColor": ACCENT,
                                        },
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        f"{ev.get('name', '')} {ev.get('year', '')} — "
                        f"Smooth interpolated replay  ·  Hit ▶ to play",
                        style={
                            "fontSize": "11px",
                            "color": "#444",
                            "marginBottom": "10px",
                        },
                    ),
                    dcc.Loading(
                        type="circle",
                        color="#e8002d",
                        children=html.Div(
                            id="replay-chart-wrap",
                            children=[
                                dcc.Graph(
                                    id=f"replay-graph-{session_key}",
                                    figure=build_replay(
                                        session_key, drivers, speed=1.0
                                    ),
                                    config={"displayModeBar": False},
                                )
                            ],
                        ),
                    ),
                ],
            ),
        ]
    )


clientside_callback(
    """
    function(session_key) {
        var graphs = document.querySelectorAll('#replay-chart-wrap .js-plotly-plot');
        graphs.forEach(function(g) {
            try { Plotly.animate(g, [], {mode: 'immediate'}); } catch(e) {}
        });
        return window.dash_clientside.no_update;
    }
    """,
    Output("replay-chart-wrap", "style"),
    Input("store-session-key", "data"),
    prevent_initial_call=True,
)


@callback(
    Output("replay-chart-wrap", "children"),
    Input("replay-speed", "value"),
    State("store-session-key", "data"),
    State("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
def update_speed(speed, session_key, selected_drivers):
    if not session_key:
        import dash

        raise dash.exceptions.PreventUpdate
    fig = build_replay(session_key, selected_drivers or [], speed=speed or 1.0)
    return dcc.Graph(
        id=f"replay-graph-{session_key}-{speed}",
        figure=fig,
        config={"displayModeBar": False},
    )
