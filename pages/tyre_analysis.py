import numpy as np
import pandas as pd
from dash import html, dcc, Input, Output, callback

from components.shared import (
    TYRE_COLORS, BG2, BG3, GRID, TEXT, MUTED, ACCENT,
)
from components.charts import lap_time, tyre_deg


# Stint data computation

def compute_stint_stats(laps: list, drivers: list) -> pd.DataFrame:
    """
    Compute degradation statistics per driver per stint, use linear regression.
    - DegPerLap: seconds lost per lap (positive = getting slower)
    - TotalDeg: total time lost over the stint
    - Median: median lap time (clean laps only)
    """
    rows = []

    for drv in drivers:
        drv_laps = [l for l in laps if l["Driver"] == drv and l.get("LapTimeSec")]

        for stint_num in set(l["Stint"] for l in drv_laps):
            stint_laps = sorted(
                [l for l in drv_laps if l["Stint"] == stint_num],
                key=lambda l: l["LapNumber"],
            )
            if len(stint_laps) < 3:
                continue

            compound = _most_common([l["Compound"] for l in stint_laps])

            # Remove in/out laps and safety car laps for clean stats
            inner = stint_laps[1:-1] if len(stint_laps) > 4 else stint_laps
            times = [l["LapTimeSec"] for l in inner]
            if not times:
                continue
            median_time = float(np.median(times))
            clean_inner = [l for l in inner if l["LapTimeSec"] < median_time * 1.07]

            if len(clean_inner) < 2:
                continue

            ages  = np.array([l["TyreLife"] for l in clean_inner], dtype=float)
            times = np.array([l["LapTimeSec"] for l in clean_inner])

            # Linear regression: time = a + b * tyre_age ===> b = degradation rate
            if ages.std() > 0:
                deg_per_lap = float(np.polyfit(ages, times, 1)[0])
            else:
                deg_per_lap = 0.0

            total_deg = deg_per_lap * max(ages[-1] - ages[0], 1)

            rows.append({
                "Driver":    drv,
                "Stint":     stint_num,
                "Compound":  compound,
                "Laps":      len(stint_laps),
                "DegPerLap": round(deg_per_lap, 3),
                "TotalDeg":  round(total_deg, 3),
                "Median":    round(median_time, 3),
            })

    return pd.DataFrame(rows)


def filter_clean_laps(laps: list, drivers: list) -> pd.DataFrame:
    """
    Return a DataFrame of clean laps (SC laps removed) for box plots.
    Removes laps > 112% of median lap time.
    """
    rows = [
        {
            "Driver":   l["Driver"],
            "Compound": l.get("Compound", "UNKNOWN"),
            "LapTime":  l["LapTimeSec"],
            "Lap":      l["LapNumber"],
        }
        for l in laps
        if l["Driver"] in drivers and l.get("LapTimeSec")
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    median = df["LapTime"].median()
    return df[df["LapTime"] < median * 1.12]


def _most_common(lst):
    """Return the most frequent element in a list."""
    return max(set(lst), key=lst.count)


# Stint degradation cards HTML─

def _stint_cards(drivers, stints_df, driver_meta):
    """Build the degradation rate cards section."""
    if stints_df.empty:
        return html.Div("No stint data available.",
                        style={"color": "#555", "padding": "12px"})

    cards = []
    for drv in drivers:
        drv_stints = stints_df[stints_df["Driver"] == drv].sort_values("Stint")
        if drv_stints.empty:
            continue

        meta  = driver_meta.get(drv, {})
        color = meta.get("color", "#AAAAAA")
        team  = meta.get("team", "")

        stint_cols = []
        for i, (_, s) in enumerate(drv_stints.iterrows()):
            compound_color = TYRE_COLORS.get(s["Compound"], "#444")
            # Color-code the per-lap rate: red = bad, yellow = moderate, teal = good
            if s["DegPerLap"] > 0.3:
                deg_color = "#e8002d"
            elif s["DegPerLap"] > 0.08:
                deg_color = "#ffd700"
            else:
                deg_color = "#00d2be"

            border_left = f"1px solid {GRID}" if i > 0 else "none"

            stint_cols.append(html.Div(
                style={
                    "padding": "12px 14px",
                    "borderLeft": f"3px solid {compound_color}",
                    "borderTop": f"1px solid {GRID}",
                    "flex": "1",
                },
                children=[
                    # Stint header number on left, compound on right
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between",
                               "alignItems": "center", "marginBottom": "10px"},
                        children=[
                            html.Span(f"STINT {s['Stint']}",
                                      style={"fontSize": "10px", "color": "#444",
                                             "letterSpacing": "1px"}),
                            html.Span(s["Compound"],
                                      style={"fontSize": "10px", "fontWeight": "700",
                                             "color": compound_color, "letterSpacing": "1px"}),
                        ],
                    ),
                    # Stats rows
                    *[
                        html.Div(
                            style={"display": "flex", "justifyContent": "space-between",
                                   "marginBottom": "4px"},
                            children=[
                                html.Span(label, style={"fontSize": "11px", "color": "#666"}),
                                html.Span(value, style={"fontSize": "12px",
                                                         "color": vc, "fontWeight": fw}),
                            ],
                        )
                        for label, value, vc, fw in [
                            ("Total deg:",  f"{s['TotalDeg']:+.3f}s",  TEXT,      "normal"),
                            ("Per lap:",    f"{s['DegPerLap']:+.3f}s", deg_color, "700"),
                            ("Median:",     f"{s['Median']:.2f}s",     TEXT,      "normal"),
                            ("Laps:",       str(s["Laps"]),            TEXT,      "normal"),
                        ]
                    ],
                ],
            ))

        cards.append(html.Div(
            style={"background": BG2, "border": f"1px solid {GRID}",
                   "borderRadius": "8px", "marginBottom": "10px", "overflow": "hidden",
                   "boxShadow": "0 2px 10px rgba(0,0,0,0.3)"},
            children=[
                # Driver header
                html.Div(
                    style={"padding": "10px 16px", "borderBottom": f"1px solid {GRID}",
                           "display": "flex", "alignItems": "center", "gap": "10px"},
                    children=[
                        html.Div(style={"width": "3px", "height": "22px",
                                        "background": color, "borderRadius": "2px"}),
                        html.Span(drv, style={"fontSize": "18px", "fontWeight": "800",
                                               "letterSpacing": "2.5px", "color": TEXT}),
                        html.Span(f"{team}", style={"fontSize": "11px", "color": "#555"}),
                    ],
                ),
                html.Div(style={"display": "flex"}, children=stint_cols),
            ],
        ))

    return html.Div(cards)


def _section(title, subtitle=""):
    """Section header with optional subtitle."""
    return html.Div(
        style={"marginBottom": "16px", "paddingBottom": "10px",
               "borderBottom": f"1px solid {GRID}"},
        children=[
            html.Div(style={"display":"flex","alignItems":"center","gap":"8px",
                             "marginBottom":"3px" if subtitle else "0"},
                     children=[
                html.Div(style={"width":"3px","height":"18px","background":ACCENT,
                                 "borderRadius":"2px","flexShrink":"0"}),
                html.Div(title, style={"fontSize":"11px","fontWeight":"700",
                                        "letterSpacing":"2.5px","color":TEXT}),
            ]),
            html.Div(subtitle, style={"fontSize": "10px", "color": "#555",
                                       "marginTop": "3px", "paddingLeft":"11px"}) if subtitle else None,
        ],
    )


def _chart_card(title, fig, subtitle=""):
    """Wrapper card around a Plotly chart."""
    return html.Div(
        style={"background": BG2, "border": f"1px solid {GRID}",
               "borderRadius": "8px", "padding": "18px 20px", "marginBottom": "14px",
               "boxShadow": "0 2px 12px rgba(0,0,0,0.3)"},
        children=[
            _section(title, subtitle),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ],
    )


def empty():
    return html.Div(
        style={"display": "flex", "flexDirection": "column", "alignItems": "center",
               "justifyContent": "center", "minHeight": "50vh", "gap": "12px"},
        children=[
            html.Div("🛞", style={"fontSize": "36px", "background": "#1a0508",
                                   "borderRadius": "12px", "padding": "12px 16px"}),
            html.Div("NO SESSION LOADED",
                     style={"fontSize": "14px", "fontWeight": "700",
                             "letterSpacing": "2px", "color": TEXT}),
        ],
    )


# Layout + callback

layout = html.Div(id="tyre-container", children=[empty()])


@callback(
    Output("tyre-container", "children"),
    Input("store-race",          "data"),
    Input("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
def render(store, selected_drivers):
    if not store:
        return empty()

    drivers = selected_drivers or [d["drv"] for d in store.get("drivers", [])]
    if not drivers:
        return html.Div("Select drivers from the sidebar.",
                        style={"color": "#555", "padding": "20px"})

    laps        = store.get("laps", [])
    driver_meta = {d["drv"]: d for d in store.get("drivers", [])}
    drv_colors  = {d["drv"]: d["color"] for d in store.get("drivers", [])}

    # Compute data
    stints_df  = compute_stint_stats(laps, drivers)
    clean_df   = filter_clean_laps(laps, drivers)

    return html.Div([
        # Section 1 degradation cards
        _section("DEGRADATION RATES"),
        _stint_cards(drivers, stints_df, driver_meta),

        html.Div(style={"height": "16px"}),

        # Section 2 lap time per lap
        _chart_card(
            "LAP TIME PER LAP",
            lap_time.build(laps, drivers, drv_colors),
            "Color = tyre compound · Label at end of each driver's line",
        ),

        # Section 3degradation rate bar chart
        _chart_card(
            "DEGRADATION RATE PER STINT",
            tyre_deg.deg_rate_bar(stints_df) if not stints_df.empty else _empty_fig(),
            "+ = degrading (slower)  ·  − = fuel burn / track evolution",
        ),

        # Section 4 lap time diststribution
        _chart_card(
            "LAP TIME DISTRIBUTION PER COMPOUND",
            tyre_deg.laptime_boxplot(clean_df, drivers) if not clean_df.empty else _empty_fig(),
            "Safety car laps excluded  ·  Dots = outliers",
        ),
    ])


def _empty_fig():
    """Return a blank figre when no data is availab"""
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="#0d0f14", plot_bgcolor="#0a0c11",
        height=200,
        annotations=[dict(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False,
                          font=dict(color="#444", size=13))],
    )
    return fig
