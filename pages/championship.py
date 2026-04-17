import requests
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback, ctx

from components.shared import (
    BG2, BG3, GRID, TEXT, MUTED, ACCENT, FONT,
    chart_theme, AVAILABLE_YEARS, team_logo_img,
)

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"


# ── API calls ─────────────────────────────────────────────────

def _get(url: str, timeout: int = 8) -> dict:
    """Make a GET request to Jolpica. Returns empty dict on failure."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Jolpica] {url} → {e}")
        return {}


def fetch_driver_standings(year: int) -> list:
    """Return driver championship standings for a given year."""
    data = _get(f"{JOLPICA_BASE}/{year}/driverstandings.json")
    try:
        entries = (data["MRData"]["StandingsTable"]
                       ["StandingsLists"][0]["DriverStandings"])
        rows = []
        for e in entries:
            drv = e["Driver"]
            con = e["Constructors"][0] if e["Constructors"] else {}
            rows.append({
                "pos":        int(e["position"]),
                "code":       drv.get("code", "???"),
                "first":      drv.get("givenName", ""),
                "last":       drv.get("familyName", ""),
                "team":       con.get("name", "–"),
                "points":     float(e["points"]),
                "wins":       int(e["wins"]),
                "nationality": drv.get("nationality", ""),
            })
        return rows
    except Exception:
        return []


def fetch_constructor_standings(year: int) -> list:
    """Return constructor championship standings for a given year."""
    data = _get(f"{JOLPICA_BASE}/{year}/constructorstandings.json")
    try:
        entries = (data["MRData"]["StandingsTable"]
                       ["StandingsLists"][0]["ConstructorStandings"])
        return [{
            "pos":    int(e["position"]),
            "name":   e["Constructor"]["name"],
            "points": float(e["points"]),
            "wins":   int(e["wins"]),
        } for e in entries]
    except Exception:
        return []


def fetch_calendar(year: int) -> list:
    """Return the race calendar for a given year."""
    data = _get(f"{JOLPICA_BASE}/{year}.json")
    try:
        races = data["MRData"]["RaceTable"]["Races"]
        return [{
            "round":   int(r["round"]),
            "name":    r["raceName"],
            "circuit": r["Circuit"]["circuitName"],
            "country": r["Circuit"]["Location"]["country"],
            "date":    r["date"],
            "time":    r.get("time", "–"),
        } for r in races]
    except Exception:
        return []


def fetch_race_results(year: int) -> dict:
    """Return {round: {winner, winner_team, pole, fastest_lap}} for past races."""
    out = {}
    # Results endpoint returns all races in one call
    data = _get(f"{JOLPICA_BASE}/{year}/results/1.json?limit=100")
    try:
        for r in data["MRData"]["RaceTable"]["Races"]:
            rnd = int(r["round"])
            res = r.get("Results", [{}])[0]
            driver = res.get("Driver", {})
            out.setdefault(rnd, {})["winner"] = (
                driver.get("code") or
                driver.get("familyName", "–")[:3].upper()
            )
            out[rnd]["winner_team"] = res.get("Constructor", {}).get("name", "–")
    except Exception:
        pass

    # Qualifying / pole
    data = _get(f"{JOLPICA_BASE}/{year}/qualifying/1.json?limit=100")
    try:
        for r in data["MRData"]["RaceTable"]["Races"]:
            rnd = int(r["round"])
            res = r.get("QualifyingResults", [{}])[0]
            driver = res.get("Driver", {})
            out.setdefault(rnd, {})["pole"] = (
                driver.get("code") or
                driver.get("familyName", "–")[:3].upper()
            )
    except Exception:
        pass

    # Fastest lap (rank=1 in results)
    data = _get(f"{JOLPICA_BASE}/{year}/fastest/1/results.json?limit=100")
    try:
        for r in data["MRData"]["RaceTable"]["Races"]:
            rnd = int(r["round"])
            res = r.get("Results", [{}])[0]
            driver = res.get("Driver", {})
            out.setdefault(rnd, {})["fastest_lap"] = (
                driver.get("code") or
                driver.get("familyName", "–")[:3].upper()
            )
    except Exception:
        pass

    return out


# UI

def _section(title):
    return html.Div(
        style={"display":"flex","alignItems":"center","gap":"8px",
               "marginBottom":"16px","paddingBottom":"10px",
               "borderBottom":f"1px solid {GRID}"},
        children=[
            html.Div(style={"width":"3px","height":"18px","background":ACCENT,
                             "borderRadius":"2px","flexShrink":"0"}),
            html.Div(title, style={"fontSize":"11px","fontWeight":"700",
                                    "letterSpacing":"2.5px","color":TEXT}),
        ])


def _th(text):
    return html.Th(text, style={"fontSize": "9px", "fontWeight": "700",
                                  "letterSpacing": "1.8px", "color": "#444",
                                  "padding": "8px 12px", "textAlign": "left",
                                  "borderBottom": f"1px solid {GRID}",
                                  "textTransform": "uppercase", "whiteSpace": "nowrap"})


def _td(content, bold=False, color=None):
    return html.Td(
        content,
        style={"padding": "10px 12px", "fontSize": "12px",
               "color": color or TEXT, "borderBottom": f"1px solid {BG3}",
               "fontWeight": "700" if bold else "400"},
    )


def _pos_badge(pos):
    colors = {1: "#ffd700", 2: "#c0c0c0", 3: "#cd7f32"}
    bg = colors.get(pos, BG3)
    tc = "#000" if pos <= 3 else TEXT
    return html.Div(
        str(pos),
        style={"width": "30px", "height": "30px", "borderRadius": "5px",
               "background": bg, "color": tc, "fontWeight": "700",
               "fontSize": "12px", "display": "flex",
               "alignItems": "center", "justifyContent": "center"},
    )


# Standings

def _driver_standings_table(rows: list) -> html.Div:
    table_rows = []
    for r in rows:
        table_rows.append(html.Tr(
            style={"borderBottom": f"1px solid {BG3}"},
            children=[
                html.Td(_pos_badge(r["pos"]),
                        style={"padding": "10px 12px", "width": "40px"}),
                html.Td(
                    html.Div([
                        html.Div(r["first"].upper(),
                                 style={"fontSize": "9px", "color": "#555"}),
                        html.Div(r["last"].upper(),
                                 style={"fontSize": "13px", "fontWeight": "700",
                                        "color": TEXT}),
                    ]),
                    style={"padding": "10px 12px"},
                ),
                _td(r["team"], color="#888"),
                _td(str(int(r["points"])), bold=True),
                _td(str(r["wins"]) if r["wins"] else "–", color="#888"),
            ],
        ))

    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse"},
        children=[
            html.Thead(html.Tr([_th(h) for h in
                                ["POS", "DRIVER", "TEAM", "PTS", "WINS"]])),
            html.Tbody(table_rows),
        ],
    )


def _constructor_standings_table(rows: list) -> html.Div:
    table_rows = []
    for r in rows:
        table_rows.append(html.Tr(
            style={"borderBottom": f"1px solid {BG3}"},
            children=[
                html.Td(_pos_badge(r["pos"]),
                        style={"padding": "10px 12px", "width": "40px"}),
                html.Td(r["name"].upper(),
                        style={"padding": "10px 12px", "fontSize": "13px",
                               "fontWeight": "700", "color": TEXT}),
                _td(str(int(r["points"])), bold=True),
                _td(str(r["wins"]) if r["wins"] else "–", color="#888"),
            ],
        ))

    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse"},
        children=[
            html.Thead(html.Tr([_th(h) for h in ["POS", "TEAM", "PTS", "WINS"]])),
            html.Tbody(table_rows),
        ],
    )


# Calendar

def _calendar_table(races: list, results: dict, highlight_next: bool = True) -> html.Table:
    """Table of races with next upcoming race highlighted and past-race results."""
    from datetime import date
    today = date.today()

    rows = []
    for r in races:
        try:
            race_date = date.fromisoformat(r["date"])
            is_past   = race_date < today
            is_next   = (highlight_next and not is_past and
                         all(date.fromisoformat(rr["date"]) >= race_date
                             for rr in races
                             if not date.fromisoformat(rr["date"]) < today))
        except Exception:
            is_past = False
            is_next = False

        row_style = {
            "borderBottom": f"1px solid {BG3}",
            "opacity":      "0.45" if is_past else "1",
            "background":   "#1a0508" if is_next else "transparent",
        }

        rnd_data = results.get(r["round"], {})

        # Results cell only for past races
        if is_past and rnd_data:
            winner = rnd_data.get("winner", "–")
            team   = rnd_data.get("winner_team", "–")
            pole   = rnd_data.get("pole", "–")
            fl     = rnd_data.get("fastest_lap", "–")
            results_cell = html.Td(
                html.Div([
                    html.Div([
                        html.Span("🏆 ", style={"fontSize": "9px"}),
                        html.Span(winner, style={"fontWeight": "700", "color": TEXT,
                                                   "fontSize": "11px"}),
                        html.Span(f"  {team}", style={"color": "#555", "fontSize": "10px"}),
                    ], style={"marginBottom": "2px"}),
                    html.Div([
                        html.Span("PP ", style={"color": "#a855f7", "fontSize": "9px",
                                                 "fontWeight": "700"}),
                        html.Span(pole, style={"color": "#888", "fontSize": "10px"}),
                        html.Span("  FL ", style={"color": "#00d2be", "fontSize": "9px",
                                                   "fontWeight": "700"}),
                        html.Span(fl, style={"color": "#888", "fontSize": "10px"}),
                    ]),
                ]),
                style={"padding": "10px 12px"},
            )
        elif is_next:
            results_cell = html.Td("▶ NEXT",
                style={"padding": "10px 12px", "fontSize": "10px",
                       "color": ACCENT, "fontWeight": "700"})
        else:
            results_cell = html.Td("",
                style={"padding": "10px 12px"})

        rows.append(html.Tr(
            style=row_style,
            children=[
                html.Td(f"R{r['round']}",
                        style={"padding": "10px 12px", "fontSize": "11px",
                               "color": ACCENT if is_next else "#555",
                               "fontWeight": "700", "width": "44px"}),
                html.Td(
                    html.Div([
                        html.Div(r["name"],
                                 style={"fontSize": "12px", "fontWeight": "700",
                                        "color": TEXT}),
                        html.Div(r["circuit"],
                                 style={"fontSize": "10px", "color": "#555"}),
                    ]),
                    style={"padding": "10px 12px"},
                ),
                html.Td(r["country"],
                        style={"padding": "10px 12px", "fontSize": "11px", "color": "#888"}),
                html.Td(r["date"],
                        style={"padding": "10px 12px", "fontSize": "11px",
                               "color": ACCENT if is_next else TEXT,
                               "fontWeight": "700" if is_next else "400"}),
                results_cell,
            ],
        ))

    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse"},
        children=[
            html.Thead(html.Tr([_th(h) for h in
                                ["ROUND", "RACE", "COUNTRY", "DATE", "RESULTS"]])),
            html.Tbody(rows),
        ],
    )


# Layout + callback

layout = html.Div(id="championship-container",
                   children=[html.Div("Loading...",
                                      style={"color": "#555", "padding": "20px"})])


@callback(
    Output("championship-container", "children"),
    Input("champ-year-dd", "value"),
    prevent_initial_call=False,
)
def render(year):
    year = year or AVAILABLE_YEARS[0]

    driver_rows      = fetch_driver_standings(year)
    constructor_rows = fetch_constructor_standings(year)
    calendar         = fetch_calendar(year)
    race_results     = fetch_race_results(year)

    # Standings side by side
    standings_section = html.Div(
        style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
               "gap": "12px", "marginBottom": "16px"},
        children=[
            html.Div(
                style={"background": BG2, "border": f"1px solid {GRID}",
                       "borderRadius": "8px", "padding": "18px 20px", "boxShadow": "0 2px 12px rgba(0,0,0,0.3)"},
                children=[
                    _section("DRIVERS CHAMPIONSHIP"),
                    _driver_standings_table(driver_rows)
                    if driver_rows
                    else html.Div("No data available.",
                                  style={"color": "#555", "fontSize": "12px"}),
                ],
            ),
            html.Div(
                style={"background": BG2, "border": f"1px solid {GRID}",
                       "borderRadius": "8px", "padding": "18px 20px", "boxShadow": "0 2px 12px rgba(0,0,0,0.3)"},
                children=[
                    _section("CONSTRUCTORS CHAMPIONSHIP"),
                    _constructor_standings_table(constructor_rows)
                    if constructor_rows
                    else html.Div("No data available.",
                                  style={"color": "#555", "fontSize": "12px"}),
                ],
            ),
        ],
    )

    # Calendar
    calendar_section = html.Div(
        style={"background": BG2, "border": f"1px solid {GRID}",
               "borderRadius": "8px", "padding": "18px 20px", "boxShadow": "0 2px 12px rgba(0,0,0,0.3)"},
        children=[
            _section("RACE CALENDAR"),
            _calendar_table(calendar, race_results)
            if calendar
            else html.Div("No calendar data.", style={"color": "#555"}),
        ],
    )

    return html.Div([standings_section, calendar_section])
