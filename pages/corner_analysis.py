import traceback
import numpy as np
import pandas as pd
import json
from dash import html, dcc, Input, Output, State, callback, ctx, ALL
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import CubicSpline

from components.perf_metrics import tab_timer
from components.shared import (
    TYRE_COLORS,
    BG2,
    BG3,
    GRID,
    TEXT,
    MUTED,
    ACCENT,
    FONT,
    get_cached_session,
    get_driver_meta,
    hex_to_rgba,
)
from components.charts.racing_line import build as build_racing_line

MARGIN = 100


def detect_corners(session, tel):
    dist = tel["Distance"].values.astype(float)
    try:
        ci = session.get_circuit_info()
        out = []
        for _, r in ci.corners.iterrows():
            idx = int(np.argmin(np.abs(dist - float(r["Distance"]))))
            num = int(r["Number"])
            let = str(r.get("Letter", "")).strip()
            out.append(
                {
                    "label": f"T{num}{let}" if let else f"T{num}",
                    "apex_dist": float(dist[idx]),
                    "entry_speed": float(tel["Speed"].iloc[max(0, idx - 30)]),
                    "apex_speed": float(tel["Speed"].iloc[idx]),
                    "exit_speed": float(tel["Speed"].iloc[min(len(tel) - 1, idx + 30)]),
                }
            )
        return sorted(out, key=lambda c: c["apex_dist"])
    except Exception:
        spd = (
            pd.Series(tel["Speed"].values.astype(float))
            .rolling(15, center=True, min_periods=1)
            .mean()
            .values
        )
        out = []
        for i in range(1, len(spd) - 1):
            if spd[i] < spd[i - 1] and spd[i] < spd[i + 1]:
                if not out or (dist[i] - out[-1]["apex_dist"]) > 200:
                    n = len(out) + 1
                    out.append(
                        {
                            "label": f"T{n}",
                            "apex_dist": float(dist[i]),
                            "entry_speed": float(tel["Speed"].iloc[max(0, i - 30)]),
                            "apex_speed": float(spd[i]),
                            "exit_speed": float(
                                tel["Speed"].iloc[min(len(tel) - 1, i + 30)]
                            ),
                        }
                    )
        return out


def build_active_tels(tels_data, apex_dist):
    """
    DOESNT WORK PROPERLY NEED complete overhaul of process
    """
    # ── Pass 1: collect each driver's real rel-dist span ──────
    spans = {}  # drv -> (rel_min, rel_max, rel_raw, mask)
    for drv, data in tels_data.items():
        dist = np.array(data["distance"])
        mask = (dist >= apex_dist - MARGIN) & (dist <= apex_dist + MARGIN)
        if not mask.any():
            continue
        rel_raw = dist[mask] - apex_dist
        spans[drv] = (float(rel_raw.min()), float(rel_raw.max()), rel_raw, mask)

    if not spans:
        return {
            drv: {"slc": pd.DataFrame(), "color": d["color"], "lap_info": d["lap_info"]}
            for drv, d in tels_data.items()
        }

    # ── Shared overlap ─────────────────────────────────────────
    shared_start = max(v[0] for v in spans.values())
    shared_end = min(v[1] for v in spans.values())

    result = {}
    for drv, data in tels_data.items():
        if drv not in spans:
            result[drv] = {
                "slc": pd.DataFrame(),
                "color": data["color"],
                "lap_info": data["lap_info"],
            }
            continue

        rel_min, rel_max, rel_raw, mask = spans[drv]

        # If this driver has no overlap at all, return empty
        if shared_start >= shared_end:
            result[drv] = {
                "slc": pd.DataFrame(),
                "color": data["color"],
                "lap_info": data["lap_info"],
            }
            continue

        # Common grid strictly within the shared overlap, no extrapolation
        common_grid = np.linspace(shared_start, shared_end, 200)

        def _i(key):
            raw = np.array(data[key])[mask]
            # bounds_error=False + fill_value raises outside raw range,
            # but common_grid is within shared overlap so rel_raw always covers it
            return np.interp(common_grid, rel_raw, raw)

        slc = pd.DataFrame(
            {
                "X": _i("x"),
                "Y": _i("y"),
                "Distance": common_grid + apex_dist,
                "Speed": _i("speed"),
                "Throttle": _i("throttle"),
                "Brake": _i("brake"),
                "nGear": _i("gear"),
                "RelDist": common_grid,
            }
        )
        result[drv] = {"slc": slc, "color": data["color"], "lap_info": data["lap_info"]}

    return result


def build_telemetry_panel(active_tels):
    """Speed / Throttle / Brake — clean 3-panel chart."""
    valid = {d: t for d, t in active_tels.items() if not t["slc"].empty}
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.40, 0.32, 0.28],
        vertical_spacing=0.03,
        subplot_titles=["Speed (km/h)", "Throttle (%)", "Brake (%)"],
    )
    for drv, info in valid.items():
        slc, color = info["slc"], info["color"]
        fig.add_trace(
            go.Scatter(
                x=slc["RelDist"],
                y=slc["Speed"],
                mode="lines",
                line=dict(color=color, width=2.4),
                name=drv,
                legendgroup=drv,
                hovertemplate=f"<b>{drv}</b> %{{y:.0f}} km/h<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=slc["RelDist"],
                y=slc["Throttle"],
                mode="lines",
                line=dict(color=color, width=2.0),
                legendgroup=drv,
                showlegend=False,
                hovertemplate=f"<b>{drv}</b> %{{y:.0f}}%<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=slc["RelDist"],
                y=slc["Brake"].astype(float) * 100,
                mode="lines",
                fill="tozeroy",
                fillcolor=hex_to_rgba(color, 0.15),
                line=dict(color=color, width=1.8),
                legendgroup=drv,
                showlegend=False,
                hovertemplate=f"<b>{drv}</b> %{{y:.0f}}%<extra></extra>",
            ),
            row=3,
            col=1,
        )
    for r in [1, 2, 3]:
        fig.add_vline(x=0, line=dict(color="#333", width=1.5, dash="dot"), row=r, col=1)
    for r in [1, 2]:
        fig.update_xaxes(
            showticklabels=False,
            gridcolor="#161920",
            showline=True,
            linecolor="#1a1d24",
            row=r,
            col=1,
        )
    fig.update_xaxes(
        gridcolor="#161920",
        tickfont=dict(size=10, color="#777"),
        title_text="Distance from apex (m)",
        title_font=dict(size=10, color="#666"),
        showline=True,
        linecolor="#1a1d24",
        row=3,
        col=1,
    )
    for r, lbl in [(1, "km/h"), (2, "%"), (3, "%")]:
        fig.update_yaxes(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=9, color="#777"),
            title_text=lbl,
            title_font=dict(size=9, color="#666"),
            showline=True,
            linecolor="#1a1d24",
            row=r,
            col=1,
        )
    for ann in fig.layout.annotations:
        ann.update(font=dict(size=9, color="#555", family=FONT))
    fig.update_layout(
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0a0c11",
        font=dict(color="#888", family=FONT, size=10),
        height=420,
        margin=dict(l=52, r=12, t=36, b=16),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            bgcolor="rgba(13,15,20,0.9)",
            bordercolor="#1a1d24",
            borderwidth=1,
            font=dict(size=11, color="#ccc"),
            orientation="h",
            x=0,
            y=1.06,
        ),
        hoverlabel=dict(
            bgcolor="#13161e", bordercolor="#252830", font=dict(color="#fff", size=11)
        ),
    )
    return fig


def build_stat_cards(active_tels):
    """Clean speed/throttle/brake stat cards — readable table format."""
    valid = {d: t for d, t in active_tels.items() if not t["slc"].empty}
    if not valid:
        return html.Div()
    dlist = list(valid.keys())

    rows = []
    for drv, info in valid.items():
        slc, color = info["slc"], info["color"]
        apex = slc.iloc[(slc["RelDist"].abs()).argmin()]
        entry = slc.iloc[0]
        exit_ = slc.iloc[-1]
        bp = slc[slc["Brake"] > 0.1]["RelDist"].min()
        max_t = slc["Throttle"].max()
        min_g = int(slc["nGear"].min())

        # Speed delta vs reference
        if drv != dlist[0]:
            ref_apex_spd = valid[dlist[0]]["slc"].iloc[
                (valid[dlist[0]]["slc"]["RelDist"].abs()).argmin()
            ]["Speed"]
            dv = apex["Speed"] - ref_apex_spd
            delta = f"{dv:+.1f} km/h"
            delta_color = "#00d2be" if dv >= 0 else ACCENT
        else:
            delta = "reference"
            delta_color = "#555"

        rows.append(
            html.Div(
                style={
                    "flex": "1",
                    "background": BG3,
                    "border": f"1px solid {GRID}",
                    "borderRadius": "8px",
                    "padding": "16px 18px",
                    "minWidth": "160px",
                    "boxShadow": "0 2px 8px rgba(0,0,0,0.3)",
                },
                children=[
                    # Driver header
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "marginBottom": "12px",
                            "paddingBottom": "8px",
                            "borderBottom": f"1px solid {GRID}",
                        },
                        children=[
                            html.Div(
                                style={
                                    "width": "3px",
                                    "height": "24px",
                                    "background": color,
                                    "borderRadius": "2px",
                                }
                            ),
                            html.Div(
                                drv,
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": "700",
                                    "color": color,
                                },
                            ),
                            html.Div(
                                f"L{info['lap_info'].get('lap_number','?')}",
                                style={
                                    "fontSize": "10px",
                                    "color": "#555",
                                    "marginLeft": "4px",
                                },
                            ),
                            html.Div(
                                info["lap_info"].get("compound", ""),
                                style={
                                    "marginLeft": "auto",
                                    "fontSize": "9px",
                                    "fontWeight": "700",
                                    "color": TYRE_COLORS.get(
                                        info["lap_info"].get("compound", ""), "#555"
                                    ),
                                },
                            ),
                        ],
                    ),
                    # Stats table
                    *[
                        html.Div(
                            style={
                                "display": "flex",
                                "justifyContent": "space-between",
                                "marginBottom": "6px",
                            },
                            children=[
                                html.Span(
                                    label, style={"fontSize": "11px", "color": "#888"}
                                ),
                                html.Span(
                                    value,
                                    style={
                                        "fontSize": "11px",
                                        "color": vc,
                                        "fontWeight": fw,
                                    },
                                ),
                            ],
                        )
                        for label, value, vc, fw in [
                            (
                                "Entry speed",
                                f"{entry['Speed']:.0f} km/h",
                                TEXT,
                                "normal",
                            ),
                            ("Apex speed", f"{apex['Speed']:.0f} km/h", TEXT, "700"),
                            (
                                "Exit speed",
                                f"{exit_['Speed']:.0f} km/h",
                                TEXT,
                                "normal",
                            ),
                            ("Apex delta", delta, delta_color, "700"),
                            (
                                "Brake point",
                                f"{bp:.0f}m" if pd.notna(bp) else "—",
                                "#aaa",
                                "normal",
                            ),
                            ("Max throttle", f"{max_t:.0f}%", "#aaa", "normal"),
                            ("Min gear", f"G{min_g}", "#aaa", "normal"),
                        ]
                    ],
                ],
            )
        )
    return html.Div(
        style={
            "display": "flex",
            "gap": "10px",
            "flexWrap": "wrap",
            "marginTop": "12px",
        },
        children=rows,
    )


def _corner_list_items(corners, selected_idx):
    return [
        html.Div(
            "CORNERS",
            style={
                "fontSize": "10px",
                "fontWeight": "700",
                "letterSpacing": "1.5px",
                "color": "#444",
                "marginBottom": "8px",
            },
        ),
        html.Div(
            style={"maxHeight": "520px", "overflowY": "auto"},
            children=[
                html.Div(
                    id={"type": "corner-btn", "index": i},
                    n_clicks=0,
                    style={
                        "padding": "7px 10px",
                        "marginBottom": "3px",
                        "borderRadius": "4px",
                        "border": f"1px solid {ACCENT if i==selected_idx else GRID}",
                        "cursor": "pointer",
                        "background": "#1a0508" if i == selected_idx else "#12151c",
                    },
                    children=[
                        html.Div(
                            c["label"],
                            style={
                                "fontSize": "12px",
                                "fontWeight": "700",
                                "color": ACCENT if i == selected_idx else TEXT,
                            },
                        ),
                        html.Div(
                            f"apex {c['apex_speed']:.0f} km/h",
                            style={"fontSize": "10px", "color": "#555"},
                        ),
                    ],
                )
                for i, c in enumerate(corners)
            ],
        ),
    ]


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
                "🏎",
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
    id="corner-loading",
    type="circle",
    color="#e8002d",
    style={
        "position": "fixed",
        "top": "50%",
        "left": "50%",
        "transform": "translate(-50%,-50%)",
        "zIndex": "999",
    },
    children=html.Div(id="corner-outer", children=[empty()]),
)


@callback(
    Output("corner-outer", "children"),
    Input("store-session-key", "data"),
    Input("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
@tab_timer("corner")
def build_page(session_key, selected_drivers):
    if not session_key:
        return empty()
    try:
        return _build_page_inner(session_key, selected_drivers)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[corner_analysis] ERROR: {e}\n{tb}")
        return html.Div(
            [
                html.Div(
                    f"Corner Analysis error: {e}",
                    style={"color": ACCENT, "padding": "20px", "fontWeight": "700"},
                ),
                html.Pre(
                    tb,
                    style={
                        "color": "#888",
                        "fontSize": "11px",
                        "padding": "10px 20px",
                        "whiteSpace": "pre-wrap",
                    },
                ),
            ]
        )


def _build_page_inner(session_key, selected_drivers):
    try:
        year, gp, stype = session_key.split("|")
        session = get_cached_session(int(year), gp, stype)
    except Exception as e:
        return html.Div(f"Error: {e}", style={"color": ACCENT, "padding": "20px"})

    drivers = selected_drivers or []
    if not drivers:
        return html.Div(
            "Select drivers from the sidebar.",
            style={"color": "#555", "padding": "20px"},
        )

    # Get available laps per driver for lap selector
    driver_lap_options = {}
    driver_tels_raw = {}
    ref_tel = None

    for drv in drivers:
        try:
            info = get_driver_meta(session, drv)
            laps_drv = session.laps.pick_drivers(drv)
            if laps_drv.empty:
                continue

            # Lap options for this driver
            lap_nums = sorted(
                laps_drv["LapNumber"].dropna().unique().astype(int).tolist()
            )
            driver_lap_options[drv] = lap_nums

            # Default: fastest lap
            fastest = laps_drv.pick_fastest()
            if fastest is None or fastest.empty:
                continue
            tel = fastest.get_telemetry().add_distance()
            li = {
                "lap_number": int(fastest["LapNumber"]),
                "compound": str(fastest.get("Compound", "N/A")).upper(),
                "tyre_life": (
                    int(fastest.get("TyreLife", 0))
                    if pd.notna(fastest.get("TyreLife", 0))
                    else 0
                ),
            }
            driver_tels_raw[drv] = {"tel": tel, "color": info["color"], "lap_info": li}
            if ref_tel is None:
                ref_tel = tel
        except Exception:
            continue

    if not driver_tels_raw or ref_tel is None:
        return html.Div(
            "Could not load telemetry.", style={"color": "#555", "padding": "20px"}
        )

    corners = detect_corners(session, ref_tel)
    if not corners:
        return html.Div(
            "No corners detected.", style={"color": "#555", "padding": "20px"}
        )

    # Serialize telemetry for sub-callbacks
    tels_store = {
        drv: {
            "color": data["color"],
            "lap_info": data["lap_info"],
            "x": data["tel"]["X"].tolist(),
            "y": data["tel"]["Y"].tolist(),
            "distance": data["tel"]["Distance"].tolist(),
            "speed": data["tel"]["Speed"].tolist(),
            "throttle": data["tel"]["Throttle"].tolist(),
            "brake": data["tel"]["Brake"].tolist(),
            "gear": data["tel"]["nGear"].tolist(),
        }
        for drv, data in driver_tels_raw.items()
    }

    corners_store = [
        {
            "label": c["label"],
            "apex_dist": c["apex_dist"],
            "entry_speed": c["entry_speed"],
            "apex_speed": c["apex_speed"],
        }
        for c in corners
    ]

    active_tels = build_active_tels(tels_store, corners_store[0]["apex_dist"])

    # Lap selector dropdowns per driver
    lap_selectors = []
    for drv in drivers:
        if drv not in driver_lap_options:
            continue
        lap_nums = driver_lap_options[drv]
        cur_lap = driver_tels_raw[drv]["lap_info"]["lap_number"]
        color = driver_tels_raw[drv]["color"]
        lap_selectors.append(
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "8px"},
                children=[
                    html.Span(
                        drv,
                        style={
                            "fontSize": "11px",
                            "fontWeight": "700",
                            "color": color,
                            "minWidth": "30px",
                        },
                    ),
                    dcc.Dropdown(
                        id={"type": "lap-selector", "index": drv},
                        options=[{"label": f"L{n}", "value": n} for n in lap_nums],
                        value=cur_lap,
                        clearable=False,
                        style={"width": "90px", "fontSize": "11px"},
                    ),
                ],
            )
        )

    return html.Div(
        [
            dcc.Store(id="corner-tels-store", data=tels_store),
            dcc.Store(id="corner-corners-store", data=corners_store),
            dcc.Store(id="corner-selected-idx", data=0),
            dcc.Store(id="corner-session-key", data=session_key),
            dcc.Store(id="corner-drivers", data=drivers),
            # Lap selector bar
            html.Div(
                style={
                    "background": BG2,
                    "border": f"1px solid {GRID}",
                    "borderRadius": "8px",
                    "padding": "10px 14px",
                    "marginBottom": "10px",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "16px",
                    "flexWrap": "wrap",
                },
                children=[
                    html.Div(
                        "LAP SELECTOR",
                        style={
                            "fontSize": "10px",
                            "fontWeight": "700",
                            "letterSpacing": "1.5px",
                            "color": "#555",
                        },
                    ),
                    *lap_selectors,
                ],
            ),
            html.Div(
                style={"display": "flex", "gap": "12px"},
                children=[
                    # Corner list
                    html.Div(
                        id="corner-list-panel",
                        style={
                            "width": "180px",
                            "flexShrink": "0",
                            "background": BG2,
                            "border": f"1px solid {GRID}",
                            "borderRadius": "6px",
                            "padding": "12px",
                        },
                        children=_corner_list_items(corners_store, 0),
                    ),
                    # Main charts
                    html.Div(
                        style={"flex": "1", "minWidth": "0"},
                        children=[
                            html.Div(
                                style={
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "alignItems": "center",
                                    "marginBottom": "8px",
                                },
                                children=[
                                    html.Div(
                                        id="corner-title",
                                        children=corners_store[0]["label"],
                                        style={
                                            "fontSize": "14px",
                                            "fontWeight": "700",
                                            "color": ACCENT,
                                        },
                                    ),
                                    dcc.RadioItems(
                                        id="corner-line-mode",
                                        options=[
                                            {"label": " Team", "value": "team"},
                                            {"label": " Speed", "value": "speed"},
                                        ],
                                        value="team",
                                        inline=True,
                                        labelStyle={
                                            "marginLeft": "12px",
                                            "fontSize": "11px",
                                            "color": "#888",
                                            "cursor": "pointer",
                                        },
                                        inputStyle={"marginRight": "4px"},
                                    ),
                                ],
                            ),
                            html.Div(
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "10px",
                                },
                                children=[
                                    html.Div(
                                        id="corner-racing-line",
                                        children=[
                                            html.Div(
                                                style={
                                                    "background": BG2,
                                                    "border": f"1px solid {GRID}",
                                                    "borderRadius": "6px",
                                                    "padding": "10px",
                                                },
                                                children=[
                                                    dcc.Graph(
                                                        figure=build_racing_line(
                                                            active_tels, "team"
                                                        ),
                                                        config={
                                                            "displayModeBar": False
                                                        },
                                                    )
                                                ],
                                            )
                                        ],
                                    ),
                                    html.Div(
                                        id="corner-telemetry",
                                        children=[
                                            html.Div(
                                                style={
                                                    "background": BG2,
                                                    "border": f"1px solid {GRID}",
                                                    "borderRadius": "6px",
                                                    "padding": "10px",
                                                },
                                                children=[
                                                    dcc.Graph(
                                                        figure=build_telemetry_panel(
                                                            active_tels
                                                        ),
                                                        config={
                                                            "displayModeBar": False
                                                        },
                                                    )
                                                ],
                                            )
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                id="corner-stat-cards",
                                children=[build_stat_cards(active_tels)],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )


@callback(
    Output("corner-selected-idx", "data"),
    Output("corner-list-panel", "children"),
    Input({"type": "corner-btn", "index": ALL}, "n_clicks"),
    State("corner-corners-store", "data"),
    prevent_initial_call=True,
)
def select_corner(_, corners):
    if not ctx.triggered or not corners:
        raise Exception("no update")
    idx = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["index"]
    return idx, _corner_list_items(corners, idx)


@callback(
    Output("corner-racing-line", "children"),
    Output("corner-telemetry", "children"),
    Output("corner-stat-cards", "children"),
    Output("corner-title", "children"),
    Input("corner-selected-idx", "data"),
    Input("corner-line-mode", "value"),
    Input({"type": "lap-selector", "index": ALL}, "value"),
    State({"type": "lap-selector", "index": ALL}, "id"),
    State("corner-tels-store", "data"),
    State("corner-corners-store", "data"),
    State("corner-session-key", "data"),
    State("corner-drivers", "data"),
    prevent_initial_call=True,
)
def update_corner(
    corner_idx, line_mode, lap_values, lap_ids, tels_data, corners, session_key, drivers
):
    if not corners or not tels_data:
        raise Exception("no data")

    # If lap changed, reload telemetry for that driver
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    if "lap-selector" in triggered and session_key and lap_ids:
        try:
            year, gp, stype = session_key.split("|")
            session = get_cached_session(int(year), gp, stype)
            for lap_val, lap_id in zip(lap_values, lap_ids):
                drv = lap_id["index"]
                if drv not in tels_data:
                    continue
                try:
                    laps_drv = session.laps.pick_drivers(drv)
                    lap_row = laps_drv[laps_drv["LapNumber"] == lap_val]
                    if lap_row.empty:
                        continue
                    tel = lap_row.iloc[0].get_telemetry().add_distance()
                    r = lap_row.iloc[0]
                    tels_data[drv].update(
                        {
                            "x": tel["X"].tolist(),
                            "y": tel["Y"].tolist(),
                            "distance": tel["Distance"].tolist(),
                            "speed": tel["Speed"].tolist(),
                            "throttle": tel["Throttle"].tolist(),
                            "brake": tel["Brake"].tolist(),
                            "gear": tel["nGear"].tolist(),
                            "lap_info": {
                                "lap_number": int(lap_val),
                                "compound": str(r.get("Compound", "N/A")).upper(),
                                "tyre_life": (
                                    int(r.get("TyreLife", 0))
                                    if pd.notna(r.get("TyreLife", 0))
                                    else 0
                                ),
                            },
                        }
                    )
                except Exception:
                    pass
        except Exception:
            pass

    corner = corners[corner_idx or 0]
    apex_dist = corner["apex_dist"]
    active_tels = build_active_tels(tels_data, apex_dist)
    title = f"{corner['label']}  ·  apex {apex_dist:.0f}m"

    def _card(content):
        return html.Div(
            style={
                "background": BG2,
                "border": f"1px solid {GRID}",
                "borderRadius": "6px",
                "padding": "10px",
            },
            children=[content],
        )

    return (
        _card(
            dcc.Graph(
                figure=build_racing_line(active_tels, line_mode),
                config={"displayModeBar": False},
            )
        ),
        _card(
            dcc.Graph(
                figure=build_telemetry_panel(active_tels),
                config={"displayModeBar": False},
            )
        ),
        build_stat_cards(active_tels),
        title,
    )
