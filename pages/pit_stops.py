
import requests
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback
from components.shared import BG2, BG3, GRID, TEXT, MUTED, ACCENT, FONT
from components.charts.pit_stops import (
    prepare_pit_data, build_team_colors, timeline, avg_duration, stop_comparison, team_stats_table
)

JOLPICA = "https://api.jolpi.ca/ergast/f1"


def _jolpica_get(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[Jolpica pitstops] {url} => {e}")
    return None


def _get_round(year, gp_name):
    """find round number for a GP"""
    data = _jolpica_get(f"{JOLPICA}/{year}.json")
    if not data:
        return None
    try:
        races = data["MRData"]["RaceTable"]["Races"]
        gp_lower = gp_name.lower()
        for race in races:
            if (gp_lower in race["raceName"].lower() or
                    gp_lower in race["Circuit"].get("circuitName", "").lower() or
                    gp_lower in race["Circuit"].get("Location", {}).get("country", "").lower()):
                return int(race["round"])
    except Exception:
        pass
    return None


def fetch_jolpica_pitstops(year, gp_name, store):
    """
    
    Fetch pit stop data from Jolpica API and return a DataFrame
    with the same shape as prepare_pit_data(): Driver, Team, TeamColor, Lap, Duration, StopNumber
    """
    round_num = _get_round(year, gp_name)
    if not round_num:
        return pd.DataFrame()

    data = _jolpica_get(f"{JOLPICA}/{year}/{round_num}/pitstops.json?limit=100")
    if not data:
        return pd.DataFrame()

    try:
        stops = data["MRData"]["RaceTable"]["Races"][0]["PitStops"]
    except (KeyError, IndexError):
        return pd.DataFrame()

    if not stops:
        return pd.DataFrame()

    # Build driverId => team/color map from store results/drivers
    id_to_team  = {}
    id_to_color = {}
    id_to_code  = {}

    # Jolpica uses driverId (e.g. "max_verstappen"), store uses 3-letter codes
    # Map via store results where we have both first/last name and code
    results = store.get("results", [])
    drivers = store.get("drivers", [])
    team_colors = build_team_colors(store)

    # Build a name-fragment => driver mapping
    for d in drivers:
        last_lower = d.get("last", "").lower().replace(" ", "_")
        first_lower = d.get("first", "").lower().replace(" ", "_")
        code = d["drv"]
        id_to_code[last_lower]  = code
        id_to_code[first_lower] = code
        # e.g. "max_verstappen" => "VER"
        combined = f"{first_lower}_{last_lower}"
        id_to_code[combined] = code

    def _resolve(driver_id):
        """Map Jolpica driverId to 3-letter code."""
        dl = driver_id.lower()
        if dl in id_to_code:
            return id_to_code[dl]
        # Try partial match on last name
        for key, code in id_to_code.items():
            if key in dl or dl in key:
                return code
        return driver_id.upper()[:3]

    # Get team per driver code from drivers store
    code_to_team  = {d["drv"]: d.get("team", "–") for d in drivers}
    code_to_color = {d["drv"]: d.get("color", "#AAAAAA") for d in drivers}

    rows = []
    for s in stops:
        driver_id = s.get("driverId", "")
        code = _resolve(driver_id)
        team  = code_to_team.get(code, "–")
        color = code_to_color.get(code, "#AAAAAA")

        try:
            duration = float(s["duration"])
        except (KeyError, ValueError, TypeError):
            continue

        # Sanity check
        if not (5 < duration < 120):
            continue

        try:
            lap = int(s["lap"])
        except (KeyError, ValueError):
            continue

        rows.append({
            "Driver":    code,
            "Team":      team,
            "TeamColor": color,
            "Lap":       lap,
            "Duration":  round(duration, 1),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["StopNumber"] = df.groupby("Team").cumcount() + 1
    return df


def _section(t, sub=""):
    return html.Div(style={"marginBottom": "14px", "paddingBottom": "10px",
                            "borderBottom": f"1px solid {GRID}"}, children=[
        html.Div(style={"display":"flex","alignItems":"center","gap":"8px"},
                 children=[
            html.Div(style={"width":"3px","height":"18px","background":ACCENT,
                             "borderRadius":"2px","flexShrink":"0"}),
            html.Div(t, style={"fontSize":"11px","fontWeight":"700",
                                "letterSpacing":"2.5px","color":TEXT}),
        ]),
        html.Div(sub, style={"fontSize": "10px", "color": "#555", "marginTop": "3px",
                               "paddingLeft":"11px"}) if sub else None,
    ])


def _chart_card(title, fig, sub=""):
    return html.Div(style={"background": BG2, "border": f"1px solid {GRID}",
                            "borderRadius": "8px", "padding": "18px 20px",
                            "marginBottom": "14px",
                            "boxShadow": "0 2px 12px rgba(0,0,0,0.3)"}, children=[
        _section(title, sub),
        dcc.Graph(figure=fig, config={"displayModeBar": True}),
    ])


def _stats_html(stats_df):
    if stats_df.empty:
        return html.Div()
    th = {"fontSize": "9px", "fontWeight": "700", "letterSpacing": "1.5px", "color": "#444",
          "padding": "8px 12px", "textAlign": "left", "borderBottom": f"1px solid {GRID}", "whiteSpace":"nowrap"}
    td = {"padding": "10px 12px", "fontSize": "12px", "color": TEXT, "borderBottom": f"1px solid {BG3}"}
    rows = []
    for _, r in stats_df.iterrows():
        rows.append(html.Tr([
            html.Td(r["Team"],             style=td),
            html.Td(str(r["Stops"]),       style=td),
            html.Td(f"{r['Best (s)']}s",   style=td),
            html.Td(f"{r['Average (s)']}s", style={**td, "fontWeight": "700"}),
            html.Td(f"{r['Worst (s)']}s",  style=td),
            html.Td(f"{r['Total (s)']}s",  style=td),
        ]))
    return html.Table(style={"width": "100%", "borderCollapse": "collapse"}, children=[
        html.Thead(html.Tr([html.Th(h, style=th) for h in
                            ["TEAM", "STOPS", "BEST", "AVG", "WORST", "TOTAL"]])),
        html.Tbody(rows),
    ])


def empty():
    return html.Div(style={"display": "flex", "flexDirection": "column", "alignItems": "center",
                            "justifyContent": "center", "minHeight": "50vh", "gap": "12px"}, children=[
        html.Div("🅿", style={"fontSize": "36px", "background": "#1a0508",
                               "borderRadius": "12px", "padding": "12px 16px"}),
        html.Div("NO SESSION LOADED", style={"fontSize": "14px", "fontWeight": "700",
                                              "letterSpacing": "2px", "color": TEXT}),
    ])


layout = html.Div(id="pitstops-container", children=[empty()])


@callback(
    Output("pitstops-container", "children"),
    Input("store-race", "data"),
    prevent_initial_call=True,
)
def render(store):
    if not store:
        return empty()

    laps        = store.get("laps", [])
    team_colors = build_team_colors(store)
    pit_df      = prepare_pit_data(laps, team_colors)
    source      = "FastF1"

    # try Jolpica
    if pit_df.empty:
        ev   = store.get("event", {})
        year = ev.get("year", 0)
        gp   = ev.get("name", "")
        if year and gp and store.get("session_type") == "Race":
            pit_df = fetch_jolpica_pitstops(year, gp, store)
            source = "Jolpica API"

    if pit_df.empty:
        return html.Div(style={"background": BG2, "border": f"1px solid {GRID}",
                                "borderRadius": "6px", "padding": "24px"}, children=[
            html.Div("⚠ No pit stop data found.",
                     style={"color": "#888", "fontSize": "13px", "marginBottom": "6px"}),
            html.Div("Neither FastF1 timing nor Jolpica API returned pit stop data for this session.",
                     style={"color": "#555", "fontSize": "11px"}),
        ])

    stats_df = team_stats_table(pit_df)

    return html.Div([
        html.Div(style={"background": BG2, "border": f"1px solid {GRID}",
                        "borderRadius": "6px", "padding": "16px", "marginBottom": "12px"}, children=[
            _section("TEAM PIT STOP STATISTICS",
                     f"All teams · source: {source} · driver selection has no effect"),
            _stats_html(stats_df),
        ]),
        _chart_card("PIT STOP TIMELINE", timeline(pit_df),
                    "Each dot = one stop · labeled with duration"),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"}, children=[
            _chart_card("AVERAGE STOP DURATION", avg_duration(pit_df)),
            _chart_card("STOP-BY-STOP COMPARISON", stop_comparison(pit_df)),
        ]),
    ])
