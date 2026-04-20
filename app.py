import os
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx
from flask_caching import Cache
from flask import request, Response
from functools import wraps
import fastf1
from pathlib import Path

from views.landing import landing_page
from views.championship import championship_view
from views.telemetry import telemetry_view, TABS, _tab_style
from views.root_layout import build_root_layout

from components.shared import (
    PRELOADED_RACES,
    RACE_DATES,
    GRID,
    TEXT,
    ACCENT,
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


# Main layout
app.layout = build_root_layout()


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
