import pandas as pd
from dash import html, dcc, Input, Output, callback

from components.perf_metrics import tab_timer
from components.shared import (
    BG2,
    BG3,
    GRID,
    TEXT,
    MUTED,
    ACCENT,
    get_cached_session,
    get_driver_meta,
    format_laptime,
)
from components.charts.telemetry import build as build_telemetry

# Sector time


def _fmt_sector(seconds):
    """Format sector time in seconds to 3 decimal places."""
    if seconds is None or (isinstance(seconds, float) and pd.isna(seconds)):
        return "–"
    try:
        return f"{float(seconds):.3f}"
    except Exception:
        return "–"


def _sector_badge(value, is_best):
    """Purple badge if this is the best sector, grey otherwise"""
    text = _fmt_sector(value)
    if is_best:
        return html.Span(
            text,
            style={
                "background": "#4c1d95",
                "color": "#c4b5fd",
                "padding": "3px 10px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontWeight": "600",
            },
        )
    return html.Span(
        text,
        style={
            "background": BG3,
            "color": TEXT,
            "padding": "3px 10px",
            "borderRadius": "4px",
            "fontSize": "12px",
        },
    )


def _build_sector_table(laps, drivers, lap_number, driver_meta):
    """Build the sector times table for a specific lap"""
    # Collect data per driver for this lap
    drv_lap_data = {}
    sector_bests = {"S1": None, "S2": None, "S3": None}

    for drv in drivers:
        matching = [
            l for l in laps if l["Driver"] == drv and l["LapNumber"] == lap_number
        ]
        if not matching:
            continue
        lap = matching[0]
        drv_lap_data[drv] = lap

        # Track sector bests across all selected drivers
        for key, col in [
            ("S1", "Sector1TimeSec"),
            ("S2", "Sector2TimeSec"),
            ("S3", "Sector3TimeSec"),
        ]:
            v = lap.get(col)
            if v is not None and v > 0:
                if sector_bests[key] is None or v < sector_bests[key]:
                    sector_bests[key] = v

    # Find best lap time for bolding
    best_lap = min(
        (l.get("LapTimeSec") for l in drv_lap_data.values() if l.get("LapTimeSec")),
        default=None,
    )

    rows = []
    for pos, drv in enumerate(drivers, 1):
        if drv not in drv_lap_data:
            continue
        lap = drv_lap_data[drv]
        meta = driver_meta.get(drv, {})
        color = meta.get("color", "#AAAAAA")
        lt = lap.get("LapTimeSec")

        lap_time_el = html.Span(
            format_laptime(lt),
            style={
                "background": BG3,
                "padding": "4px 12px",
                "borderRadius": "4px",
                "fontSize": "13px",
                "fontWeight": "700" if lt == best_lap else "400",
            },
        )

        rows.append(
            html.Tr(
                style={
                    "borderBottom": f"1px solid {BG3}",
                    "transition": "background 0.12s",
                },
                children=[
                    html.Td(
                        html.Div(
                            str(pos),
                            style={
                                "width": "28px",
                                "height": "28px",
                                "borderRadius": "5px",
                                "background": BG3,
                                "color": "#888",
                                "border": f"1px solid {GRID}",
                                "fontWeight": "700",
                                "fontSize": "12px",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                            },
                        ),
                        style={"padding": "10px 12px", "width": "44px"},
                    ),
                    html.Td(
                        html.Div(
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "10px",
                            },
                            children=[
                                html.Div(
                                    style={
                                        "width": "3px",
                                        "height": "32px",
                                        "background": color,
                                        "borderRadius": "2px",
                                    }
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            meta.get("first", "").upper(),
                                            style={"fontSize": "10px", "color": "#555"},
                                        ),
                                        html.Div(
                                            meta.get("last", drv).upper(),
                                            style={
                                                "fontSize": "13px",
                                                "fontWeight": "700",
                                                "color": color,
                                            },
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        style={"padding": "10px 12px"},
                    ),
                    html.Td(lap_time_el, style={"padding": "10px 12px"}),
                    html.Td(
                        _sector_badge(
                            lap.get("Sector1TimeSec"),
                            lap.get("Sector1TimeSec") == sector_bests["S1"],
                        ),
                        style={"padding": "10px 12px"},
                    ),
                    html.Td(
                        _sector_badge(
                            lap.get("Sector2TimeSec"),
                            lap.get("Sector2TimeSec") == sector_bests["S2"],
                        ),
                        style={"padding": "10px 12px"},
                    ),
                    html.Td(
                        _sector_badge(
                            lap.get("Sector3TimeSec"),
                            lap.get("Sector3TimeSec") == sector_bests["S3"],
                        ),
                        style={"padding": "10px 12px"},
                    ),
                ],
            )
        )

    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse"},
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th(
                            h,
                            style={
                                "fontSize": "9px",
                                "fontWeight": "700",
                                "letterSpacing": "1.8px",
                                "color": "#444",
                                "padding": "8px 12px",
                                "textAlign": "left",
                                "borderBottom": f"1px solid {GRID}",
                                "textTransform": "uppercase",
                                "whiteSpace": "nowrap",
                            },
                        )
                        for h in ["POS", "DRIVER", "LAP TIME", "S1", "S2", "S3"]
                    ]
                )
            ),
            html.Tbody(rows),
        ],
    )


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
                "⏱",
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


# Layout

layout = html.Div(
    [
        html.Div(id="lap-selector-bar", style={"marginBottom": "12px"}),
        dcc.Loading(
            type="circle",
            color="#e8002d",
            children=html.Div(id="sector-table-wrap", style={"marginBottom": "12px"}),
        ),
        dcc.Loading(
            type="circle", color="#e8002d", children=html.Div(id="telemetry-wrap")
        ),
    ]
)


@callback(
    Output("lap-selector-bar", "children"),
    Output("sector-table-wrap", "children"),
    Output("telemetry-wrap", "children"),
    Input("store-race", "data"),
    Input("store-session-key", "data"),
    Input("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
@tab_timer("lap")
def render(store, session_key, selected_drivers):
    """Render the lap analysis page."""
    if not store:
        return html.Div(), empty(), html.Div()

    drivers = selected_drivers or [d["drv"] for d in store.get("drivers", [])]
    if not drivers:
        msg = html.Div(
            "Select drivers from the sidebar.",
            style={"color": "#555", "padding": "20px"},
        )
        return html.Div(), msg, html.Div()

    laps = store.get("laps", [])
    driver_meta = {d["drv"]: d for d in store.get("drivers", [])}
    all_laps = sorted(set(l["LapNumber"] for l in laps if l.get("LapNumber")))
    default_lap = all_laps[2] if len(all_laps) > 2 else (all_laps[0] if all_laps else 1)

    # Lap selector bar
    selector = html.Div(
        style={
            "background": BG2,
            "border": f"1px solid {GRID}",
            "borderRadius": "8px",
            "padding": "14px 18px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.25)",
        },
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "8px"},
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
                        "LAP SELECTOR",
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
                style={"display": "flex", "alignItems": "center", "gap": "10px"},
                children=[
                    html.Span(
                        "SELECT LAP:",
                        style={
                            "fontSize": "10px",
                            "color": "#555",
                            "letterSpacing": "1px",
                            "fontWeight": "700",
                        },
                    ),
                    dcc.Dropdown(
                        id="dd-lap",
                        options=[{"label": f"Lap {n}", "value": n} for n in all_laps],
                        value=default_lap,
                        clearable=False,
                        style={"width": "130px"},
                    ),
                    html.Span(
                        f"{len(drivers)} DRIVERS",
                        style={
                            "fontSize": "10px",
                            "color": "#555",
                            "padding": "4px 10px",
                            "background": BG3,
                            "borderRadius": "4px",
                            "fontWeight": "700",
                        },
                    ),
                ],
            ),
        ],
    )

    # Initial sector table
    sector_card = html.Div(
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
                    "marginBottom": "14px",
                    "paddingBottom": "10px",
                    "borderBottom": f"1px solid {GRID}",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "marginBottom": "4px",
                        },
                        children=[
                            html.Div(
                                style={
                                    "width": "3px",
                                    "height": "18px",
                                    "background": ACCENT,
                                    "borderRadius": "2px",
                                    "flexShrink": "0",
                                }
                            ),
                            html.Div(
                                "SECTOR TIMES",
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
                        "Lap-by-lap sector performance  ·  Purple = best sector",
                        style={
                            "fontSize": "10px",
                            "color": "#555",
                            "paddingLeft": "11px",
                        },
                    ),
                ],
            ),
            html.Div(
                id="sector-table-inner",
                children=[_build_sector_table(laps, drivers, default_lap, driver_meta)],
            ),
        ],
    )

    # Telemetry chart (pull raw data from FastF1)
    telemetry_card = _build_telemetry_card(session_key, drivers)

    return selector, sector_card, telemetry_card


@callback(
    Output("sector-table-inner", "children"),
    Input("dd-lap", "value"),
    Input("store-race", "data"),
    Input("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
def update_sector_table(lap_num, store, selected_drivers):
    """Update the sectr table when the lap dopdwn change"""
    if not store or not lap_num:
        return html.Div()
    drivers = selected_drivers or []
    laps = store.get("laps", [])
    driver_meta = {d["drv"]: d for d in store.get("drivers", [])}
    return _build_sector_table(laps, drivers, lap_num, driver_meta)


def _build_telemetry_card(session_key, drivers):
    """Fetch raw telemetry from FastF1 (fastest lap per driver) and build chart.


    telemetry data is too big to store in dcc.Store.
    """
    if not session_key:
        return html.Div()

    try:
        year, gp, stype = session_key.split("|")
        session = get_cached_session(int(year), gp, stype)
    except Exception as e:
        return html.Div(
            f"Could not load telemetry: {e}", style={"color": "#555", "padding": "20px"}
        )

    driver_telemetry = {}
    for drv in drivers:
        try:
            meta = get_driver_meta(session, drv)
            laps_drv = session.laps.pick_drivers(drv)
            if laps_drv.empty:
                continue
            lap = laps_drv.pick_fastest()
            if lap is None or lap.empty:
                continue
            tel = lap.get_telemetry().add_distance()
            driver_telemetry[drv] = {"tel": tel, "color": meta["color"]}
        except Exception:
            continue

    if not driver_telemetry:
        return html.Div(
            "No telemetry available.", style={"color": "#555", "padding": "20px"}
        )

    return html.Div(
        style={
            "background": BG2,
            "border": f"1px solid {GRID}",
            "borderRadius": "6px",
            "padding": "16px",
        },
        children=[
            html.Div(
                "COMBINED TELEMETRY — FASTEST LAP PER DRIVER",
                style={
                    "fontSize": "12px",
                    "fontWeight": "700",
                    "letterSpacing": "2px",
                    "color": TEXT,
                    "borderLeft": f"3px solid {ACCENT}",
                    "paddingLeft": "10px",
                    "marginBottom": "12px",
                },
            ),
            dcc.Graph(
                figure=build_telemetry(driver_telemetry),
                config={"displayModeBar": True},
            ),
        ],
    )
