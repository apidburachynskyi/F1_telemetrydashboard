from dash import html
import pages.overview as pg_overview
import pages.qualifying as pg_qualifying
import pages.race_replay as pg_replay
import pages.corner_analysis as pg_corner
import pages.tyre_analysis as pg_tyre
import pages.lap_analysis as pg_lap
import pages.race_progression as pg_progression
import pages.pit_stops as pg_pitstops

from components.sidebar import build_sidebar
from components.shared import GRID, TEXT, ACCENT, FONT

TABS = [
    ("overview", "OVERVIEW", pg_overview.layout),
    ("qualifying", "QUALIFYING", pg_qualifying.layout),
    ("replay", "RACE REPLAY", pg_replay.layout),
    ("corner", "CORNER ANALYSIS", pg_corner.layout),
    ("tyre", "TYRE ANALYSIS", pg_tyre.layout),
    ("lap", "LAP ANALYSIS", pg_lap.layout),
    ("progression", "RACE PROGRESSION", pg_progression.layout),
    ("pitstops", "PIT STOPS", pg_pitstops.layout),
]


def _tab_style(active):
    return {
        "padding": "12px 14px",
        "fontSize": "11px",
        "fontWeight": "700",
        "letterSpacing": "1px",
        "color": TEXT if active else "#555",
        "background": "transparent",
        "border": "none",
        "borderBottom": f"2px solid {ACCENT}" if active else "2px solid transparent",
        "cursor": "pointer",
        "whiteSpace": "nowrap",
    }


def telemetry_view():
    return html.Div(
        style={"background": "#08090d", "minHeight": "100vh", "fontFamily": FONT},
        children=[
            # Hidden nav buttons + dummy checklist — ensure all IDs exist at startup
            html.Button(id="btn-go-telemetry", n_clicks=0, style={"display": "none"}),
            html.Button(
                id="btn-go-championship", n_clicks=0, style={"display": "none"}
            ),
            html.Button(
                id="btn-back-from-champ", n_clicks=0, style={"display": "none"}
            ),
            html.Button(id="btn-back-from-dash", n_clicks=0, style={"display": "none"}),
            html.Button(id="quali-seg-Q1", n_clicks=0, style={"display": "none"}),
            html.Button(id="quali-seg-Q2", n_clicks=0, style={"display": "none"}),
            html.Button(id="quali-seg-Q3", n_clicks=0, style={"display": "none"}),
            html.Div(id="quali-timeline-chart", style={"display": "none"}),
            html.Div(
                style={
                    "height": "3px",
                    "background": "linear-gradient(90deg,#e8002d,#ff4d6d)",
                }
            ),
            html.Div(
                style={"display": "flex", "minHeight": "calc(100vh - 3px)"},
                children=[
                    build_sidebar(),
                    html.Div(
                        style={
                            "flex": "1",
                            "display": "flex",
                            "flexDirection": "column",
                            "minWidth": "0",
                        },
                        children=[
                            # Tab bar
                            html.Div(
                                style={
                                    "background": "#0d0f14",
                                    "borderBottom": f"1px solid {GRID}",
                                    "display": "flex",
                                    "gap": "2px",
                                    "padding": "0 12px",
                                    "flexWrap": "wrap",
                                    "alignItems": "center",
                                },
                                children=[
                                    *[
                                        html.Button(
                                            label,
                                            id=f"tab-btn-{tid}",
                                            n_clicks=0,
                                            style=_tab_style(i == 0),
                                        )
                                        for i, (tid, label, _) in enumerate(TABS)
                                    ],
                                    # Back to landing
                                    html.Button(
                                        "← HOME",
                                        id="btn-back-from-dash",
                                        n_clicks=0,
                                        style={
                                            "marginLeft": "auto",
                                            "background": "transparent",
                                            "border": f"1px solid {GRID}",
                                            "color": "#555",
                                            "padding": "6px 12px",
                                            "borderRadius": "4px",
                                            "fontSize": "10px",
                                            "fontWeight": "700",
                                            "cursor": "pointer",
                                        },
                                    ),
                                ],
                            ),
                            # All pages mounted and on with display
                            html.Div(
                                style={
                                    "flex": "1",
                                    "overflowY": "auto",
                                    "padding": "16px",
                                },
                                children=[
                                    html.Div(
                                        id=f"page-{tid}",
                                        style={
                                            "display": "block" if i == 0 else "none"
                                        },
                                        children=[page_layout],
                                    )
                                    for i, (tid, _, page_layout) in enumerate(TABS)
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # (stores are in app.layout)
        ],
    )
