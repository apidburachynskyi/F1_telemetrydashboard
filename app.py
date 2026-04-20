import os
import json
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, ALL
from flask_caching import Cache
from flask import request, Response
from functools import wraps
import fastf1
from pathlib import Path

# Page imports
import pages.overview as pg_overview
import pages.qualifying as pg_qualifying
import pages.race_replay as pg_replay
import pages.corner_analysis as pg_corner
import pages.tyre_analysis as pg_tyre
import pages.lap_analysis as pg_lap
import pages.race_progression as pg_progression
import pages.pit_stops as pg_pitstops
import pages.championship as pg_championship

from components.sidebar import build_sidebar
from components.shared import (
    AVAILABLE_YEARS,
    PRELOADED_RACES,
    RACE_DATES,
    BG2,
    GRID,
    TEXT,
    ACCENT,
    MUTED,
    FONT,
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
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server


@server.route("/health")
def health():
    return {"status": "ok"}, 200


_MONITORING_USER = os.environ.get("MONITORING_USER", "admin")
_MONITORING_PASSWORD = os.environ.get("MONITORING_PASSWORD", "f1admin2026")


def _require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if (
            not auth
            or auth.username != _MONITORING_USER
            or auth.password != _MONITORING_PASSWORD
        ):
            return Response(
                "Access denied",
                401,
                {"WWW-Authenticate": 'Basic realm="F1 Monitoring"'},
            )
        return f(*args, **kwargs)

    return decorated


@server.route("/monitoring")
@_require_auth
def monitoring_page():
    import psutil
    from components.perf_metrics import RENDER_HISTORY
    from prometheus_client import REGISTRY

    proc = psutil.Process()
    ram_mb = proc.memory_info().rss / 1024 / 1024
    cpu_pct = proc.cpu_percent(interval=0.1)

    tab_labels = {
        "overview": "Overview",
        "qualifying": "Qualifying",
        "replay": "Race Replay",
        "corner": "Corner Analysis",
        "tyre": "Tyre Analysis",
        "lap": "Lap Analysis",
        "progression": "Race Progression",
        "pitstops": "Pit Stops",
    }
    total_req = 0
    for metric in REGISTRY.collect():
        if metric.name == "f1_tab_render_seconds":
            for s in metric.samples:
                if s.name == "f1_tab_render_seconds_count":
                    total_req += s.value

    counts, sums = {}, {}
    for metric in REGISTRY.collect():
        if metric.name != "f1_tab_render_seconds":
            continue
        for s in metric.samples:
            tab = s.labels.get("tab", "?")
            if s.name == "f1_tab_render_seconds_count":
                counts[tab] = s.value
            elif s.name == "f1_tab_render_seconds_sum":
                sums[tab] = s.value
    rows = sorted(
        [
            {
                "tab": tab_labels.get(t, t),
                "calls": int(counts[t]),
                "avg": round(sums.get(t, 0) / counts[t], 2) if counts[t] else 0,
            }
            for t in counts
        ],
        key=lambda r: r["avg"],
        reverse=True,
    )
    last_render = f"{RENDER_HISTORY[-1]['duration']:.2f}s" if RENDER_HISTORY else "—"

    def color(avg):
        if avg > 5:
            return "#e8002d"
        if avg > 1:
            return "#00d2be"
        return "#39b54a"

    rows_html = "".join(
        f"<tr><td>{r['tab']}</td><td>{r['calls']}</td>"
        f"<td style='color:{color(r['avg'])};font-weight:700'>{r['avg']:.2f}s</td></tr>"
        for r in rows
    )
    html_page = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>F1 Dashboard — Monitoring</title>
  <meta http-equiv="refresh" content="15">
  <style>
    body{{background:#08090d;color:#ccc;font-family:sans-serif;padding:32px;}}
    h1{{font-size:18px;letter-spacing:3px;color:#fff;margin-bottom:24px;}}
    .cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:28px;}}
    .card{{background:#0d0f14;border:1px solid #1e2229;border-radius:8px;padding:16px 22px;min-width:140px;}}
    .label{{font-size:10px;color:#555;letter-spacing:1.5px;font-weight:700;margin-bottom:6px;}}
    .value{{font-size:26px;font-weight:700;color:#fff;}}
    table{{width:100%;border-collapse:collapse;background:#0d0f14;border:1px solid #1e2229;border-radius:8px;}}
    th{{font-size:10px;color:#555;letter-spacing:1px;padding:10px 16px;text-align:left;border-bottom:1px solid #1e2229;}}
    td{{padding:10px 16px;font-size:13px;border-bottom:1px solid #12141a;}}
    tr:last-child td{{border-bottom:none;}}
    .legend{{font-size:11px;color:#555;margin-top:10px;}}
    .note{{font-size:10px;color:#333;margin-top:24px;}}
  </style>
</head>
<body>
  <h1>F1 DASHBOARD — MONITORING</h1>
  <div class="cards">
    <div class="card"><div class="label">LAST RENDER</div>
      <div class="value">{last_render}</div></div>
    <div class="card"><div class="label">TOTAL RENDERS</div>
      <div class="value">{int(total_req)}</div></div>
    <div class="card"><div class="label">RAM USAGE</div>
      <div class="value" style="color:{'#e8002d' if ram_mb > 3000 else '#fff'}">{ram_mb:.0f} MB</div></div>
    <div class="card"><div class="label">CPU</div>
      <div class="value" style="color:{'#e8002d' if cpu_pct > 80 else '#fff'}">{cpu_pct:.1f}%</div></div>
  </div>
  <table>
    <thead><tr><th>TAB</th><th>CALLS</th><th>AVG RENDER</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class="legend">&#x1F7E2; &lt;1s &nbsp; &#x1F535; 1–5s &nbsp; &#x1F534; &gt;5s</div>
  <div class="note">Auto-refresh every 15s</div>
</body>
</html>"""
    return html_page, 200, {"Content-Type": "text/html"}


# Server-side session cache
_server_cache = Cache(
    app.server,
    config={
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 7200,
    },
)


def get_cached_session(year, gp, session_type):
    """Load FastF1 session returns from RAM on subsequent calls."""
    key = f"ff1_{year}_{gp}_{session_type}".replace(" ", "_")
    session = _server_cache.get(key)
    if session is None:
        session = fastf1.get_session(int(year), gp, session_type)
        session.load()
        _server_cache.set(key, session)
    return session


_shared.get_cached_session = get_cached_session


# Tab definitions (telemetry)
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


# Landing
def landing_page():
    """Initial screen — two choices."""
    card_style = {
        "flex": "1",
        "maxWidth": "380px",
        "background": BG2,
        "border": f"1px solid {GRID}",
        "borderRadius": "10px",
        "padding": "40px 36px",
        "cursor": "pointer",
        "transition": "border-color 0.2s",
        "textAlign": "center",
    }
    return html.Div(
        style={
            "minHeight": "100vh",
            "background": "#08090d",
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
            "gap": "16px",
            "fontFamily": FONT,
        },
        children=[
            # Top bar
            html.Div(
                style={
                    "height": "3px",
                    "width": "100%",
                    "position": "absolute",
                    "top": 0,
                    "left": 0,
                    "background": "linear-gradient(90deg,#e8002d,#ff4d6d)",
                }
            ),
            # Hidden dummies
            html.Button(
                id="btn-back-from-champ", n_clicks=0, style={"display": "none"}
            ),
            html.Button(id="btn-back-from-dash", n_clicks=0, style={"display": "none"}),
            html.Button(id="quali-seg-Q1", n_clicks=0, style={"display": "none"}),
            html.Button(id="quali-seg-Q2", n_clicks=0, style={"display": "none"}),
            html.Button(id="quali-seg-Q3", n_clicks=0, style={"display": "none"}),
            html.Div(id="quali-timeline-chart", style={"display": "none"}),
            dcc.Checklist(
                id="driver-checklist", options=[], value=[], style={"display": "none"}
            ),
            html.Div("🏎", style={"fontSize": "48px"}),
            html.Div(
                "F1 DASHBOARD",
                style={
                    "fontSize": "28px",
                    "fontWeight": "700",
                    "letterSpacing": "4px",
                    "color": TEXT,
                },
            ),
            html.Div(
                "Choose a mode to get started",
                style={"fontSize": "13px", "color": "#555", "marginBottom": "24px"},
            ),
            # Two choice cards
            html.Div(
                style={
                    "display": "flex",
                    "gap": "24px",
                    "flexWrap": "wrap",
                    "justifyContent": "center",
                },
                children=[
                    html.Div(
                        id="btn-go-telemetry",
                        n_clicks=0,
                        style={**card_style, "borderColor": ACCENT},
                        children=[
                            html.Div(
                                "📊", style={"fontSize": "40px", "marginBottom": "16px"}
                            ),
                            html.Div(
                                "TELEMETRY ANALYSIS",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": "700",
                                    "letterSpacing": "2px",
                                    "color": TEXT,
                                    "marginBottom": "10px",
                                },
                            ),
                            html.Div(
                                "Race & qualifying data, corner analysis, "
                                "lap times, tyre strategy, pit stops",
                                style={
                                    "fontSize": "12px",
                                    "color": "#888",
                                    "lineHeight": "1.6",
                                },
                            ),
                            html.Div(
                                "SELECT SESSION →",
                                style={
                                    "marginTop": "20px",
                                    "fontSize": "11px",
                                    "fontWeight": "700",
                                    "letterSpacing": "1.5px",
                                    "color": ACCENT,
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        id="btn-go-championship",
                        n_clicks=0,
                        style={**card_style},
                        children=[
                            html.Div(
                                "🏆", style={"fontSize": "40px", "marginBottom": "16px"}
                            ),
                            html.Div(
                                "CHAMPIONSHIP",
                                style={
                                    "fontSize": "16px",
                                    "fontWeight": "700",
                                    "letterSpacing": "2px",
                                    "color": TEXT,
                                    "marginBottom": "10px",
                                },
                            ),
                            html.Div(
                                "Driver & constructor standings, "
                                "race calendar, season overview",
                                style={
                                    "fontSize": "12px",
                                    "color": "#888",
                                    "lineHeight": "1.6",
                                },
                            ),
                            html.Div(
                                "VIEW STANDINGS →",
                                style={
                                    "marginTop": "20px",
                                    "fontSize": "11px",
                                    "fontWeight": "700",
                                    "letterSpacing": "1.5px",
                                    "color": "#888",
                                },
                            ),
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
            # Top bar with back button and year selector
            html.Div(
                style={
                    "background": BG2,
                    "borderBottom": f"1px solid {GRID}",
                    "padding": "12px 20px",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "16px",
                },
                children=[
                    html.Button(
                        "← BACK",
                        id="btn-back-from-champ",
                        n_clicks=0,
                        style={
                            "background": "transparent",
                            "border": f"1px solid {GRID}",
                            "color": "#888",
                            "padding": "6px 14px",
                            "borderRadius": "4px",
                            "fontSize": "11px",
                            "fontWeight": "700",
                            "letterSpacing": "1px",
                            "cursor": "pointer",
                        },
                    ),
                    html.Div(
                        "🏆 CHAMPIONSHIP",
                        style={
                            "fontSize": "14px",
                            "fontWeight": "700",
                            "letterSpacing": "2px",
                            "color": TEXT,
                        },
                    ),
                    html.Div(
                        style={
                            "marginLeft": "auto",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "10px",
                        },
                        children=[
                            html.Span(
                                "SEASON:",
                                style={
                                    "fontSize": "11px",
                                    "color": "#555",
                                    "fontWeight": "700",
                                },
                            ),
                            dcc.Dropdown(
                                id="champ-year-dd",
                                options=[
                                    {"label": str(y), "value": y}
                                    for y in [2026, 2025, 2024]
                                ],
                                value=2026,
                                clearable=False,
                                style={"width": "100px"},
                            ),
                        ],
                    ),
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


# Main layout
app.layout = html.Div(
    style={"fontFamily": FONT},
    children=[
        # Global stores always alive regardless of which view is shown
        dcc.Store(id="store-race", data=None),
        dcc.Store(id="store-quali", data=None),
        dcc.Store(id="store-session-key", data=None),
        dcc.Store(id="store-selected-drivers", data=[]),
        dcc.Store(id="active-tab", data="overview"),
        html.Div(id="app-root", children=[landing_page()]),
    ],
)


# Navigation callbacks
@app.callback(
    Output("app-root", "children"),
    Input("btn-go-telemetry", "n_clicks"),
    Input("btn-go-championship", "n_clicks"),
    Input("btn-back-from-champ", "n_clicks"),
    Input("btn-back-from-dash", "n_clicks"),
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
    from datetime import date

    today = str(date.today())
    races = PRELOADED_RACES.get(int(year), [])
    dates = RACE_DATES.get(int(year), {})
    options = []
    first_available = None
    for r in races:
        race_date = dates.get(r, "")
        past = not race_date or race_date <= today
        if past and first_available is None:
            first_available = r
        options.append(
            {
                "label": r if past else f"{r} — {race_date}",
                "value": r,
                "disabled": not past,
            }
        )
    return options, first_available


# Load session
@app.callback(
    Output("store-race", "data"),
    Output("store-quali", "data"),
    Output("store-session-key", "data"),
    Output("load-status", "children"),
    Output("driver-checklist-wrap", "children"),
    Output("driver-count", "children", allow_duplicate=True),
    Output("store-selected-drivers", "data", allow_duplicate=True),
    Output("active-tab", "data", allow_duplicate=True),
    *[Output(f"page-{tid}", "style", allow_duplicate=True) for tid, _, _ in TABS],
    *[Output(f"tab-btn-{tid}", "style", allow_duplicate=True) for tid, _, _ in TABS],
    Input("btn-load", "n_clicks"),
    State("dd-year", "value"),
    State("dd-gp", "value"),
    prevent_initial_call=True,
)
def load_session(_, year, gp):
    n_outputs = 7 + 1 + len(TABS) + len(TABS)  # 2 stores + key + 4 ui + tab outputs
    no_change = [dash.no_update] * n_outputs

    if not all([year, gp]):
        no_change[3] = "Select year and GP."
        return no_change

    try:
        store_race = session_to_store(get_cached_session(year, gp, "R"))
    except Exception:
        store_race = None

    try:
        store_quali = session_to_store(get_cached_session(year, gp, "Q"))
    except Exception:
        store_quali = None

    if store_race is None and store_quali is None:
        no_change[3] = "Could not load Race or Qualifying for this event."
        return no_change

    # Use race store for driver list; fall back to quali
    primary = store_race or store_quali

    drivers_data = primary.get("drivers", [])
    default_sel = [drivers_data[0]["drv"]] if drivers_data else []

    checklist_options = []
    for d in drivers_data:
        drv = d["drv"]
        color = d["color"]
        pos = str(d["pos"]) if d["pos"] < 99 else "–"
        checklist_options.append(
            {
                "label": html.Div(
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "padding": "4px 0",
                    },
                    children=[
                        html.Span(
                            pos,
                            style={
                                "fontSize": "10px",
                                "color": "#555",
                                "minWidth": "16px",
                                "fontWeight": "700",
                            },
                        ),
                        html.Div(
                            style={
                                "width": "3px",
                                "height": "18px",
                                "background": color,
                                "borderRadius": "2px",
                            }
                        ),
                        html.Span(
                            drv,
                            style={
                                "fontSize": "12px",
                                "fontWeight": "600",
                                "color": color,
                            },
                        ),
                    ],
                ),
                "value": drv,
            }
        )

    checklist = dcc.Checklist(
        id="driver-checklist",
        options=checklist_options,
        value=default_sel,
        style={"maxHeight": "420px", "overflowY": "auto"},
        inputStyle={"marginRight": "8px", "accentColor": ACCENT},
        labelStyle={
            "display": "flex",
            "alignItems": "center",
            "cursor": "pointer",
            "marginBottom": "4px",
            "padding": "4px 6px",
            "borderRadius": "4px",
            "background": "#12151c",
            "border": f"1px solid {GRID}",
        },
    )

    key = f"{year}|{gp}|R"  # session-key always points to Race for telemetry pages
    quali_ok = "✓ Q" if store_quali else "✗ Q"
    race_ok = "✓ R" if store_race else "✗ R"
    status = f"{gp} {year}  {race_ok}  {quali_ok}"
    count = f"{len(default_sel)}/{len(drivers_data)}"

    # Always open to Overview (race-based)
    active_tab = "overview"
    page_styles = [
        {"display": "block"} if tid == active_tab else {"display": "none"}
        for tid, _, _ in TABS
    ]
    btn_styles = [_tab_style(tid == active_tab) for tid, _, _ in TABS]

    return (
        [
            store_race,
            store_quali,
            key,
            status,
            checklist,
            count,
            default_sel,
            active_tab,
        ]
        + page_styles
        + btn_styles
    )


# Sync checklist
# This is the single source of truth: every tick/untick insta
@app.callback(
    Output("store-selected-drivers", "data", allow_duplicate=True),
    Input("driver-checklist", "value"),
    prevent_initial_call=True,
)
def sync_driver_selection(selected):
    return selected or []


TAB_IDS = [tid for tid, _, _ in TABS]

# Tab switch — clientside so nginx never blocks it
app.clientside_callback(
    """
    function() {
        var args = Array.prototype.slice.call(arguments);
        var n_clicks = args.slice(0, args.length - 1);
        var active = args[args.length - 1];
        var tab_ids = """
    + str(TAB_IDS)
    + """;

        var triggered = window.dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) {
            return window.dash_clientside.no_update;
        }

        var prop_id = triggered[0].prop_id;
        var new_tab = prop_id.replace('tab-btn-', '').replace('.n_clicks', '');

        var page_styles = tab_ids.map(function(tid) {
            return tid === new_tab ? {display: 'block'} : {display: 'none'};
        });

        var accent = '"""
    + ACCENT
    + """';
        var text = '"""
    + TEXT
    + """';
        var btn_styles = tab_ids.map(function(tid) {
            var active = tid === new_tab;
            return {
                padding: '12px 14px',
                fontSize: '11px', fontWeight: '700', letterSpacing: '1px',
                color: active ? text : '#555',
                background: 'transparent', border: 'none',
                borderBottom: active ? '2px solid ' + accent : '2px solid transparent',
                cursor: 'pointer', whiteSpace: 'nowrap'
            };
        });

        return [new_tab].concat(page_styles).concat(btn_styles);
    }
    """,
    Output("active-tab", "data"),
    *[Output(f"page-{tid}", "style") for tid, _, _ in TABS],
    *[Output(f"tab-btn-{tid}", "style") for tid, _, _ in TABS],
    *[Input(f"tab-btn-{tid}", "n_clicks") for tid, _, _ in TABS],
    State("active-tab", "data"),
    prevent_initial_call=True,
)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
