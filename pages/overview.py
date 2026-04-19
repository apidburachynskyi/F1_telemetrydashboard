import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback
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
    team_logo_img,
)

# helpers


def _section(text, icon=""):
    return html.Div(
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
            "marginBottom": "16px",
            "paddingBottom": "10px",
            "borderBottom": f"1px solid {GRID}",
        },
        children=[
            html.Div(
                style={
                    "width": "3px",
                    "height": "20px",
                    "background": ACCENT,
                    "borderRadius": "2px",
                    "flexShrink": "0",
                }
            ),
            html.Div(
                text,
                style={
                    "fontSize": "11px",
                    "fontWeight": "700",
                    "letterSpacing": "2.5px",
                    "color": TEXT,
                },
            ),
        ],
    )


def _info_card(icon, label, val):
    return html.Div(
        className="info-card",
        children=[
            html.Div(
                [
                    html.Span(icon, style={"marginRight": "4px", "fontSize": "11px"}),
                    html.Span(label, className="info-label"),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginBottom": "4px",
                },
            ),
            html.Div(val, className="info-value"),
        ],
    )


def _stat_card(icon, label, val, color=ACCENT):
    return html.Div(
        className="stat-card",
        children=[
            html.Span(
                icon, style={"fontSize": "16px", "color": color, "marginTop": "2px"}
            ),
            html.Div(
                [
                    html.Div(label, className="stat-label"),
                    html.Div(val, className="stat-value"),
                ]
            ),
        ],
    )


def _pos_badge(pos):
    cls = {1: "pos-1", 2: "pos-2", 3: "pos-3"}.get(pos, "pos-other")
    return html.Div(str(pos), className=f"pos-badge {cls}")


def empty_state():
    return html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
            "minHeight": "60vh",
            "gap": "14px",
        },
        children=[
            html.Div(
                "📊",
                style={
                    "fontSize": "44px",
                    "background": "#12151c",
                    "borderRadius": "14px",
                    "padding": "14px 18px",
                    "border": f"1px solid {GRID}",
                },
            ),
            html.Div(
                "SELECT A SESSION",
                style={
                    "fontSize": "14px",
                    "fontWeight": "700",
                    "letterSpacing": "3px",
                    "color": TEXT,
                },
            ),
            html.Div(
                "Choose year and GP from the sidebar, then click LOAD SESSION.",
                style={"fontSize": "11px", "color": "#555", "letterSpacing": "0.5px"},
            ),
        ],
    )


layout = html.Div(id="overview-container", children=[empty_state()])


@callback(
    Output("overview-container", "children"),
    Input("store-race", "data"),
    Input("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
@tab_timer("overview")
def render(store, selected_drivers):
    if not store:
        return empty_state()

    ev = store.get("event", {})
    weather = store.get("weather", {})
    results = store.get("results", [])
    laps = store.get("laps", [])
    fl = store.get("fastest_lap", {})
    rc = store.get("race_control", {})
    compounds = store.get("compounds", {})
    all_drvs = [d["drv"] for d in store.get("drivers", [])]
    drivers = [d for d in (selected_drivers or []) if d in all_drvs] or all_drvs

    def wfmt(k, u):
        v = weather.get(k)
        return f"{v}{u}" if v else "–"

    # Weather strip
    weather_row = html.Div(
        style={
            "display": "flex",
            "gap": "8px",
            "marginBottom": "18px",
            "flexWrap": "wrap",
        },
        children=[
            _info_card("🌍", "COUNTRY", ev.get("country", "–")),
            _info_card("🏁", "CIRCUIT", ev.get("circuit", "–")),
            _info_card("🌡", "AIR TEMP", wfmt("air_temp", "°C")),
            _info_card("🔥", "TRACK TEMP", wfmt("track_temp", "°C")),
            _info_card("💧", "HUMIDITY", wfmt("humidity", "%")),
            _info_card("💨", "WIND", wfmt("wind", " km/h")),
        ],
    )

    # Results table
    rows = []
    for r in results:
        pos = r["pos"]
        color = r["color"]
        team = r.get("team", "")

        # Delta vs grid
        grid_val = r.get("grid")
        if grid_val and grid_val > 0 and pos < 99:
            delta = grid_val - pos
            de = html.Span(
                f"↑ +{delta}" if delta > 0 else (f"↓ {delta}" if delta < 0 else "= 0"),
                className=(
                    "delta-pos"
                    if delta > 0
                    else ("delta-neg" if delta < 0 else "delta-zero")
                ),
            )
        elif grid_val == 0:
            de = html.Span("PL", style={"color": "#555", "fontSize": "10px"})
        else:
            de = html.Span("–", style={"color": "#444"})

        # Tyre dots
        comp_dots = html.Div(
            style={"display": "flex", "gap": "4px", "alignItems": "center"},
            children=[
                html.Span(
                    style={
                        "width": "11px",
                        "height": "11px",
                        "borderRadius": "50%",
                        "background": TYRE_COLORS.get(c, "#555"),
                        "display": "inline-block",
                        "boxShadow": f"0 0 4px {TYRE_COLORS.get(c,'#555')}44",
                    }
                )
                for c in compounds.get(r["drv"], [])
            ],
        )

        # Team cell with logo
        logo = team_logo_img(team)
        team_cell = html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "5px"},
            children=[logo, html.Span(team)] if logo else [html.Span(team)],
        )

        # Gap formatting
        gap_str = r.get("gap", "–")
        gap_el = html.Span(
            gap_str, className="gap-leader" if gap_str == "–" else "gap-time"
        )

        rows.append(
            html.Tr(
                style={
                    "borderBottom": f"1px solid {BG3}",
                    "transition": "background 0.12s",
                },
                children=[
                    html.Td(
                        (
                            _pos_badge(pos)
                            if pos < 99
                            else html.Div("–", style={"color": "#444"})
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
                                        "height": "34px",
                                        "background": color,
                                        "borderRadius": "2px",
                                        "flexShrink": "0",
                                    }
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            r["first"].upper(), className="drv-first"
                                        ),
                                        html.Div(
                                            r["last"].upper(),
                                            style={
                                                "fontSize": "13px",
                                                "fontWeight": "700",
                                                "color": color,
                                                "letterSpacing": "0.5px",
                                            },
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        style={"padding": "10px 12px"},
                    ),
                    html.Td(
                        team_cell,
                        style={
                            "padding": "10px 12px",
                            "color": "#888",
                            "fontSize": "10px",
                            "maxWidth": "130px",
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                    ),
                    html.Td(comp_dots, style={"padding": "10px 12px"}),
                    html.Td(gap_el, style={"padding": "10px 12px"}),
                    html.Td(
                        (
                            "PL"
                            if r.get("grid") == 0
                            else (f"P{r['grid']}" if r.get("grid") else "–")
                        ),
                        style={
                            "padding": "10px 12px",
                            "color": "#555",
                            "fontSize": "10px",
                        },
                    ),
                    html.Td(de, style={"padding": "10px 12px"}),
                ],
            )
        )

    results_table = html.Div(
        className="f1-card",
        style={"marginBottom": "0"},
        children=[
            _section("RACE RESULTS"),
            html.Div(
                style={"overflowX": "auto"},
                children=[
                    html.Table(
                        className="f1-table",
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
                                                "whiteSpace": "nowrap",
                                            },
                                        )
                                        for h in [
                                            "POS",
                                            "DRIVER",
                                            "TEAM",
                                            "TYRES",
                                            "GAP",
                                            "GRID",
                                            "+/–",
                                        ]
                                    ]
                                )
                            ),
                            html.Tbody(rows),
                        ],
                    ),
                ],
            ),
        ],
    )

    # Race stat
    try:
        leader = results[0]["drv"] if results else None
        total = sum(l.get("LapTimeSec", 0) or 0 for l in laps if l["Driver"] == leader)
        h, m, s = int(total // 3600), int((total % 3600) // 60), int(total % 60)
        dur = f"{h}h {m:02d}m {s:02d}s" if total > 0 else "–"
    except:
        dur = "–"

    ret = sum(
        1
        for r in results
        if any(
            kw in r.get("status", "").lower()
            for kw in [
                "accident",
                "retired",
                "dnf",
                "engine",
                "collision",
                "mechanical",
            ]
        )
    )

    fl_str = f"{fl.get('driver','–')}  {fl.get('time','–')}"

    stats_panel = html.Div(
        className="f1-card",
        children=[
            _section("RACE STATISTICS"),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "8px",
                },
                children=[
                    _stat_card("🏆", "FASTEST LAP", fl_str, "#a855f7"),
                    _stat_card("⏱", "RACE DURATION", dur, "#f97316"),
                    _stat_card("🔴", "RETIREMENTS", str(ret), ACCENT),
                    _stat_card(
                        "🅿", "SAFETY CAR", f"{rc.get('sc',0)} deploy.", "#f97316"
                    ),
                ],
            ),
        ],
    )

    return html.Div(
        [
            weather_row,
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 300px",
                    "gap": "14px",
                },
                children=[results_table, stats_panel],
            ),
        ]
    )
