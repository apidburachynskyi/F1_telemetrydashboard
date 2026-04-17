import os
import json
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, ALL
from flask_caching import Cache
import fastf1
from pathlib import Path

#Page imports
import pages.overview          as pg_overview
import pages.qualifying        as pg_qualifying
import pages.race_replay       as pg_replay
import pages.corner_analysis   as pg_corner
import pages.tyre_analysis     as pg_tyre
import pages.lap_analysis      as pg_lap
import pages.race_progression  as pg_progression
import pages.pit_stops         as pg_pitstops
import pages.championship      as pg_championship

from components.sidebar import build_sidebar
from components.shared  import (
    AVAILABLE_YEARS, PRELOADED_RACES,
    BG2, GRID, TEXT, ACCENT, MUTED, FONT,
    session_to_store,
)
import components.shared as _shared


# FastF1 cache
CACHE_DIR = os.environ.get("FF1_CACHE_DIR", "./cache")
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


# App
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="F1 Dashboard",
    meta_tags=[{"name": "viewport",
                "content": "width=device-width, initial-scale=1"}],
)
server = app.server


# Server-side session cache
_server_cache = Cache(app.server, config={
    "CACHE_TYPE":            "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 7200,
})


def get_cached_session(year, gp, session_type):
    """Load FastF1 session returns from RAM on subsequent calls."""
    key     = f"ff1_{year}_{gp}_{session_type}".replace(" ", "_")
    session = _server_cache.get(key)
    if session is None:
        session = fastf1.get_session(int(year), gp, session_type)
        session.load()
        _server_cache.set(key, session)
    return session


_shared.get_cached_session = get_cached_session


# Tab definitions (telemetry)
TABS = [
    ("overview",    "OVERVIEW",         pg_overview.layout),
    ("qualifying",  "QUALIFYING",        pg_qualifying.layout),
    ("replay",      "RACE REPLAY",       pg_replay.layout),
    ("corner",      "CORNER ANALYSIS",   pg_corner.layout),
    ("tyre",        "TYRE ANALYSIS",     pg_tyre.layout),
    ("lap",         "LAP ANALYSIS",      pg_lap.layout),
    ("progression", "RACE PROGRESSION",  pg_progression.layout),
    ("pitstops",    "PIT STOPS",         pg_pitstops.layout),
]


def _tab_style(active):
    return {
        "padding": "12px 14px",
        "fontSize": "11px", "fontWeight": "700", "letterSpacing": "1px",
        "color": TEXT if active else "#555",
        "background": "transparent", "border": "none",
        "borderBottom": f"2px solid {ACCENT}" if active else "2px solid transparent",
        "cursor": "pointer", "whiteSpace": "nowrap",
    }


# Landing
def landing_page():
    """Initial screen — two choices."""
    card_style = {
        "flex": "1", "maxWidth": "380px",
        "background": BG2, "border": f"1px solid {GRID}",
        "borderRadius": "10px", "padding": "40px 36px",
        "cursor": "pointer", "transition": "border-color 0.2s",
        "textAlign": "center",
    }
    return html.Div(
        style={
            "minHeight": "100vh", "background": "#08090d",
            "display": "flex", "flexDirection": "column",
            "alignItems": "center", "justifyContent": "center",
            "gap": "16px", "fontFamily": FONT,
        },
        children=[
            # Top bar
            html.Div(style={"height": "3px", "width": "100%", "position": "absolute",
                            "top": 0, "left": 0,
                            "background": "linear-gradient(90deg,#e8002d,#ff4d6d)"}),

            # Hidden dummies
            html.Button(id="btn-back-from-champ",  n_clicks=0, style={"display":"none"}),
            html.Button(id="btn-back-from-dash",   n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q1",         n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q2",         n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q3",         n_clicks=0, style={"display":"none"}),
            html.Div(id="quali-timeline-chart",    style={"display":"none"}),
            dcc.Checklist(id="driver-checklist",   options=[], value=[],
                          style={"display":"none"}),
            html.Div("🏎", style={"fontSize": "48px"}),
            html.Div("F1 DASHBOARD",
                     style={"fontSize": "28px", "fontWeight": "700",
                             "letterSpacing": "4px", "color": TEXT}),
            html.Div("Choose a mode to get started",
                     style={"fontSize": "13px", "color": "#555", "marginBottom": "24px"}),

            # Two choice cards
            html.Div(
                style={"display": "flex", "gap": "24px", "flexWrap": "wrap",
                       "justifyContent": "center"},
                children=[
                    html.Div(
                        id="btn-go-telemetry",
                        n_clicks=0,
                        style={**card_style, "borderColor": ACCENT},
                        children=[
                            html.Div("📊", style={"fontSize": "40px",
                                                   "marginBottom": "16px"}),
                            html.Div("TELEMETRY ANALYSIS",
                                     style={"fontSize": "16px", "fontWeight": "700",
                                             "letterSpacing": "2px", "color": TEXT,
                                             "marginBottom": "10px"}),
                            html.Div("Race & qualifying data, corner analysis, "
                                     "lap times, tyre strategy, pit stops",
                                     style={"fontSize": "12px", "color": "#888",
                                             "lineHeight": "1.6"}),
                            html.Div("SELECT SESSION →",
                                     style={"marginTop": "20px", "fontSize": "11px",
                                             "fontWeight": "700", "letterSpacing": "1.5px",
                                             "color": ACCENT}),
                        ],
                    ),
                    html.Div(
                        id="btn-go-championship",
                        n_clicks=0,
                        style={**card_style},
                        children=[
                            html.Div("🏆", style={"fontSize": "40px",
                                                   "marginBottom": "16px"}),
                            html.Div("CHAMPIONSHIP",
                                     style={"fontSize": "16px", "fontWeight": "700",
                                             "letterSpacing": "2px", "color": TEXT,
                                             "marginBottom": "10px"}),
                            html.Div("Driver & constructor standings, "
                                     "race calendar, season overview",
                                     style={"fontSize": "12px", "color": "#888",
                                             "lineHeight": "1.6"}),
                            html.Div("VIEW STANDINGS →",
                                     style={"marginTop": "20px", "fontSize": "11px",
                                             "fontWeight": "700", "letterSpacing": "1.5px",
                                             "color": "#888"}),
                        ],
                    ),
                ],
            ),
        ],
    )


# Leaderboard
def championship_view():
    return html.Div(
        style={"background": "#08090d", "minHeight": "100vh", "fontFamily": FONT},
        children=[
            # Hidden nav buttons + dummy checklist
            html.Button(id="btn-go-telemetry",    n_clicks=0, style={"display":"none"}),
            html.Button(id="btn-go-championship", n_clicks=0, style={"display":"none"}),
            html.Button(id="btn-back-from-champ",  n_clicks=0, style={"display":"none"}),
            html.Button(id="btn-back-from-dash",   n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q1",         n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q2",         n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q3",         n_clicks=0, style={"display":"none"}),
            html.Div(id="quali-timeline-chart",    style={"display":"none"}),
            html.Div(style={"height": "3px",
                            "background": "linear-gradient(90deg,#e8002d,#ff4d6d)"}),
            # Top bar with back button and year selector
            html.Div(
                style={"background": BG2, "borderBottom": f"1px solid {GRID}",
                       "padding": "12px 20px", "display": "flex",
                       "alignItems": "center", "gap": "16px"},
                children=[
                    html.Button(
                        "← BACK",
                        id="btn-back-from-champ",
                        n_clicks=0,
                        style={"background": "transparent", "border": f"1px solid {GRID}",
                               "color": "#888", "padding": "6px 14px", "borderRadius": "4px",
                               "fontSize": "11px", "fontWeight": "700",
                               "letterSpacing": "1px", "cursor": "pointer"},
                    ),
                    html.Div("🏆 CHAMPIONSHIP",
                             style={"fontSize": "14px", "fontWeight": "700",
                                     "letterSpacing": "2px", "color": TEXT}),
                    html.Div(style={"marginLeft": "auto", "display": "flex",
                                    "alignItems": "center", "gap": "10px"},
                             children=[
                                 html.Span("SEASON:", style={"fontSize": "11px",
                                                               "color": "#555",
                                                               "fontWeight": "700"}),
                                 dcc.Dropdown(
                                     id="champ-year-dd",
                                     options=[{"label": str(y), "value": y}
                                              for y in [2026, 2025, 2024]],
                                     value=2026,
                                     clearable=False,
                                     style={"width": "100px"},
                                 ),
                             ]),
                ],
            ),
            html.Div(
                style={"padding": "20px"},
                children=[pg_championship.layout],
            ),
        ],
    )


# Telemetry dashboard view
def telemetry_view():
    return html.Div(
        style={"background": "#08090d", "minHeight": "100vh", "fontFamily": FONT},
        children=[
            # Hidden nav buttons + dummy checklist — ensure all IDs exist at startup
            html.Button(id="btn-go-telemetry",    n_clicks=0, style={"display":"none"}),
            html.Button(id="btn-go-championship", n_clicks=0, style={"display":"none"}),
            html.Button(id="btn-back-from-champ",  n_clicks=0, style={"display":"none"}),
            html.Button(id="btn-back-from-dash",   n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q1",         n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q2",         n_clicks=0, style={"display":"none"}),
            html.Button(id="quali-seg-Q3",         n_clicks=0, style={"display":"none"}),
            html.Div(id="quali-timeline-chart",    style={"display":"none"}),
            html.Div(style={"height": "3px",
                            "background": "linear-gradient(90deg,#e8002d,#ff4d6d)"}),
            html.Div(style={"display": "flex", "minHeight": "calc(100vh - 3px)"},
                     children=[
                         build_sidebar(),
                         html.Div(
                             style={"flex": "1", "display": "flex",
                                    "flexDirection": "column", "minWidth": "0"},
                             children=[
                                 # Tab bar
                                 html.Div(
                                     style={"background": "#0d0f14",
                                            "borderBottom": f"1px solid {GRID}",
                                            "display": "flex", "gap": "2px",
                                            "padding": "0 12px", "flexWrap": "wrap",
                                            "alignItems": "center"},
                                     children=[
                                         *[html.Button(
                                             label,
                                             id=f"tab-btn-{tid}",
                                             n_clicks=0,
                                             style=_tab_style(i == 0),
                                         ) for i, (tid, label, _) in enumerate(TABS)],
                                         # Back to landing
                                         html.Button(
                                             "← HOME",
                                             id="btn-back-from-dash",
                                             n_clicks=0,
                                             style={"marginLeft": "auto",
                                                    "background": "transparent",
                                                    "border": f"1px solid {GRID}",
                                                    "color": "#555",
                                                    "padding": "6px 12px",
                                                    "borderRadius": "4px",
                                                    "fontSize": "10px",
                                                    "fontWeight": "700",
                                                    "cursor": "pointer"},
                                         ),
                                     ],
                                 ),
                                 # All pages mounted and on with display
                                 html.Div(
                                     style={"flex": "1", "overflowY": "auto",
                                            "padding": "16px"},
                                     children=[
                                         html.Div(
                                             id=f"page-{tid}",
                                             style={"display": "block"
                                                    if i == 0 else "none"},
                                             children=[page_layout],
                                         )
                                         for i, (tid, _, page_layout) in enumerate(TABS)
                                     ],
                                 ),
                             ],
                         ),
                     ]),
            # (stores are in app.layout)
        ],
    )


# Main layout
app.layout = html.Div(style={"fontFamily": FONT}, children=[
    # Global stores always alive regardless of which view is shown
    dcc.Store(id="store-race",             data=None),
    dcc.Store(id="store-quali",            data=None),
    dcc.Store(id="store-session-key",      data=None),
    dcc.Store(id="store-selected-drivers", data=[]),
    dcc.Store(id="active-tab",             data="overview"),
    html.Div(id="app-root", children=[landing_page()]),

    # Splash
    # Disapear after 15 seconds, circa time of loading
    html.Div(id="splash-overlay", style={"display": "none"}, children=[
        html.Div(style={
            "position": "fixed", "top": "0", "left": "0",
            "width": "100%", "height": "100%",
            "background": "rgba(8,9,13,0.92)",
            "display": "flex", "alignItems": "center",
            "justifyContent": "center", "zIndex": "9999",
        }, children=[
            html.Div(style={
                "background": "#0d0f14",
                "border": "1px solid #1a1d24",
                "borderRadius": "12px",
                "padding": "40px 52px",
                "display": "flex", "flexDirection": "column",
                "alignItems": "center", "gap": "20px",
                "minWidth": "280px",
            }, children=[
                dcc.Loading(
                    type="circle",
                    color="#e8002d",
                    children=html.Div(id="splash-trigger", style={"height": "8px"}),
                ),
                html.Div("BUILDING DASHBOARD", style={
                    "fontSize": "13px", "fontWeight": "700",
                    "letterSpacing": "3px", "color": "#e0e0e0",
                }),
                html.Div(id="splash-status", children="Loading session data…", style={
                    "fontSize": "11px", "color": "#555", "letterSpacing": "1px",
                }),
            ]),
        ]),
    ]),
    dcc.Interval(id="splash-timer", interval=7000, n_intervals=0,
                 max_intervals=1, disabled=True),
])


# Navigation callbacks
@app.callback(
    Output("app-root", "children"),
    Input("btn-go-telemetry",     "n_clicks"),
    Input("btn-go-championship",  "n_clicks"),
    Input("btn-back-from-champ",  "n_clicks"),
    Input("btn-back-from-dash",   "n_clicks"),
    prevent_initial_call=True,
)
def navigate(*_):
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    btn = ctx.triggered[0]["prop_id"].split(".")[0]
    if btn == "btn-go-telemetry":
        return telemetry_view()
    if btn == "btn-go-championship":
        return championship_view()
    # Both back buttons → landing
    return landing_page()


# GP list
@app.callback(
    Output("dd-gp", "options"),
    Output("dd-gp", "value"),
    Input("dd-year", "value"),
)
def update_gp_options(year):
    races   = PRELOADED_RACES.get(int(year), [])
    options = [{"label": r, "value": r} for r in races]
    return options, (races[0] if races else None)


# Load session
@app.callback(
    Output("store-race",               "data"),
    Output("store-quali",              "data"),
    Output("store-session-key",        "data"),
    Output("load-status",              "children"),
    Output("driver-checklist-wrap",    "children"),
    Output("driver-count",             "children", allow_duplicate=True),
    Output("store-selected-drivers",   "data", allow_duplicate=True),
    Output("active-tab",               "data", allow_duplicate=True),
    *[Output(f"page-{tid}", "style", allow_duplicate=True) for tid, _, _ in TABS],
    *[Output(f"tab-btn-{tid}", "style", allow_duplicate=True) for tid, _, _ in TABS],
    Input("btn-load", "n_clicks"),
    State("dd-year", "value"),
    State("dd-gp",   "value"),
    prevent_initial_call=True,
)
def load_session(_, year, gp):
    n_outputs = 7 + 1 + len(TABS) + len(TABS)  # 2 stores + key + 4 ui + tab outputs
    no_change = [dash.no_update] * n_outputs

    if not all([year, gp]):
        no_change[3] = "Select year and GP."
        return no_change

    # Load Race
    try:
        race_session = get_cached_session(year, gp, "R")
        store_race   = session_to_store(race_session)
    except Exception as e:
        no_change[0] = None
        no_change[3] = f"Race load error: {str(e)[:80]}"
        store_race   = None

    # Load Qualifying
    try:
        quali_session = get_cached_session(year, gp, "Q")
        store_quali   = session_to_store(quali_session)
    except Exception as e:
        no_change[1] = None
        store_quali  = None

    if store_race is None and store_quali is None:
        no_change[3] = "Could not load Race or Qualifying for this event."
        return no_change

    # Use race store for driver list; fall back to quali
    primary = store_race or store_quali

    drivers_data = primary.get("drivers", [])
    default_sel  = [drivers_data[0]["drv"]] if drivers_data else []

    checklist_options = []
    for d in drivers_data:
        drv   = d["drv"]
        color = d["color"]
        pos   = str(d["pos"]) if d["pos"] < 99 else "–"
        checklist_options.append({
            "label": html.Div(
                style={"display": "flex", "alignItems": "center",
                       "gap": "8px", "padding": "4px 0"},
                children=[
                    html.Span(pos, style={"fontSize": "10px", "color": "#555",
                                           "minWidth": "16px", "fontWeight": "700"}),
                    html.Div(style={"width": "3px", "height": "18px",
                                    "background": color, "borderRadius": "2px"}),
                    html.Span(drv, style={"fontSize": "12px", "fontWeight": "600",
                                           "color": color}),
                ],
            ),
            "value": drv,
        })

    checklist = dcc.Checklist(
        id="driver-checklist",
        options=checklist_options,
        value=default_sel,
        style={"maxHeight": "420px", "overflowY": "auto"},
        inputStyle={"marginRight": "8px", "accentColor": ACCENT},
        labelStyle={"display": "flex", "alignItems": "center",
                    "cursor": "pointer", "marginBottom": "4px",
                    "padding": "4px 6px", "borderRadius": "4px",
                    "background": "#12151c", "border": f"1px solid {GRID}"},
    )

    key    = f"{year}|{gp}|R"   # session-key always points to Race for telemetry pages
    quali_ok = "✓ Q" if store_quali else "✗ Q"
    race_ok  = "✓ R" if store_race  else "✗ R"
    status   = f"{gp} {year}  {race_ok}  {quali_ok}"
    count    = f"{len(default_sel)}/{len(drivers_data)}"

    # Always open to Overview (race-based)
    active_tab  = "overview"
    page_styles = [
        {"display": "block"} if tid == active_tab else {"display": "none"}
        for tid, _, _ in TABS
    ]
    btn_styles = [_tab_style(tid == active_tab) for tid, _, _ in TABS]

    return [store_race, store_quali, key, status, checklist, count, default_sel,
            active_tab] + page_styles + btn_styles




# Sync checklist
# This is the single source of truth: every tick/untick insta
@app.callback(
    Output("store-selected-drivers", "data", allow_duplicate=True),
    Input("driver-checklist", "value"),
    prevent_initial_call=True,
)
def sync_driver_selection(selected):
    return selected or []



@app.callback(
    Output("splash-trigger", "children"),
    Input("store-race", "data"),
    prevent_initial_call=True,
)
def _splash_spin(_):
    # Loading goes spinning
    return ""


# If data is there, Splash after 7 seconds gone
@app.callback(
    Output("splash-overlay",  "style"),
    Output("splash-timer",    "disabled"),
    Output("splash-timer",    "n_intervals"),
    Output("splash-status",   "children"),
    Input("splash-timer",     "n_intervals"),
    Input("store-race",       "data"),
    prevent_initial_call=True,
)
def manage_splash(n_intervals, store_race):
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    SHOW = {"display": "block"}
    HIDE = {"display": "none"}

    # If Data counter = 0
    if "store-race" in triggered and store_race:
        return SHOW, False, 0, "Finalising all tabs…"

    # Timer disapear
    if "splash-timer" in triggered and n_intervals and n_intervals > 0:
        return HIDE, True, 0, ""

    raise dash.exceptions.PreventUpdate


# Tab switch
@app.callback(
    Output("active-tab", "data"),
    *[Output(f"page-{tid}",     "style") for tid, _, _ in TABS],
    *[Output(f"tab-btn-{tid}", "style") for tid, _, _ in TABS],
    *[Input( f"tab-btn-{tid}", "n_clicks") for tid, _, _ in TABS],
    State("active-tab", "data"),
    prevent_initial_call=True,
)
def switch_tab(*args):
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    new_tab = ctx.triggered[0]["prop_id"].split(".")[0].replace("tab-btn-", "")
    page_styles = [
        {"display": "block"} if tid == new_tab else {"display": "none"}
        for tid, _, _ in TABS
    ]
    btn_styles = [_tab_style(tid == new_tab) for tid, _, _ in TABS]
    return [new_tab] + page_styles + btn_styles


if __name__ == "__main__":
    app.run(debug=True, port=8050)
