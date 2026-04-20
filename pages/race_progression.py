import numpy as np
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback

from components.perf_metrics import tab_timer
from components.shared import (
    BG2,
    BG3,
    GRID,
    TEXT,
    MUTED,
    ACCENT,
    FONT,
    chart_theme,
    axis_label,
    format_laptime,
)
from components.charts import position_flow


def _section(title):
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
                    "height": "18px",
                    "background": ACCENT,
                    "borderRadius": "2px",
                    "flexShrink": "0",
                }
            ),
            html.Div(
                title,
                style={
                    "fontSize": "11px",
                    "fontWeight": "700",
                    "letterSpacing": "2.5px",
                    "color": TEXT,
                },
            ),
        ],
    )


def _chart_card(title, fig):
    return html.Div(
        style={
            "background": BG2,
            "border": f"1px solid {GRID}",
            "borderRadius": "8px",
            "padding": "18px 20px",
            "marginBottom": "14px",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.3)",
        },
        children=[
            _section(title),
            dcc.Graph(figure=fig, config={"displayModeBar": True}),
        ],
    )


# builders


def lap_time_comparison(laps, drivers, drv_colors):
    """Line chart: lap time per lap number for each driver."""
    fig = go.Figure()
    for drv in drivers:
        drv_laps = sorted(
            [l for l in laps if l["Driver"] == drv and l.get("LapTimeSec")],
            key=lambda l: l["LapNumber"],
        )
        if not drv_laps:
            continue
        color = drv_colors.get(drv, "#AAAAAA")
        fig.add_trace(
            go.Scatter(
                x=[l["LapNumber"] for l in drv_laps],
                y=[l["LapTimeSec"] for l in drv_laps],
                mode="lines+markers",
                marker=dict(size=5, color=color),
                line=dict(color=color, width=2.2),
                name=drv,
                hovertemplate=f"<b>{drv}</b>  Lap %{{x}}<br>%{{y:.3f}}s<extra></extra>",
            )
        )
    fig.update_layout(
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0a0c11",
        font=dict(color="#888", size=10),
        height=440,
        margin=dict(l=60, r=80, t=24, b=52),
        hoverlabel=dict(
            bgcolor="#13161e",
            bordercolor="#252830",
            font=dict(color="#e0e0e0", size=11),
        ),
        legend=dict(
            bgcolor="rgba(13,15,20,0.9)",
            bordercolor="#1a1d24",
            borderwidth=1,
            font=dict(size=11, color="#ccc"),
            orientation="h",
            x=0,
            y=1.06,
        ),
        xaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            showline=True,
            linecolor="#1a1d24",
        ),
        yaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            showline=True,
            linecolor="#1a1d24",
        ),
        hovermode="x unified",
        xaxis_title=dict(text="Lap", font=dict(size=10, color="#666")),
        yaxis_title=dict(text="Time (s)", font=dict(size=10, color="#666")),
    )
    return fig


def driver_stat_cards(laps, drivers, driver_meta):
    """Small cards below the lap time chart fastest + average."""
    cards = []
    for drv in drivers:
        meta = driver_meta.get(drv, {})
        color = meta.get("color", "#AAAAAA")
        drv_laps = [
            l["LapTimeSec"] for l in laps if l["Driver"] == drv and l.get("LapTimeSec")
        ]
        if not drv_laps:
            continue
        med = float(np.median(drv_laps))
        clean = [t for t in drv_laps if t < med * 1.07]
        if not clean:
            continue
        fastest = min(clean)
        avg = float(np.mean(clean))
        fastest_lap = next(
            (
                l["LapNumber"]
                for l in laps
                if l["Driver"] == drv and l.get("LapTimeSec") == fastest
            ),
            "?",
        )
        cards.append(
            html.Div(
                style={
                    "flex": "1",
                    "background": BG2,
                    "border": f"1px solid {GRID}",
                    "borderRadius": "6px",
                    "padding": "14px 16px",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "8px",
                            "marginBottom": "10px",
                        },
                        children=[
                            html.Div(
                                style={
                                    "width": "10px",
                                    "height": "10px",
                                    "borderRadius": "50%",
                                    "background": color,
                                }
                            ),
                            html.Span(
                                drv,
                                style={
                                    "fontSize": "14px",
                                    "fontWeight": "700",
                                    "color": TEXT,
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        [
                            html.Span(
                                "FASTEST ",
                                style={
                                    "fontSize": "9px",
                                    "color": "#444",
                                    "letterSpacing": "1px",
                                },
                            ),
                            html.Span(
                                format_laptime(fastest),
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": TEXT,
                                },
                            ),
                            html.Span(
                                f" (L{fastest_lap})",
                                style={"fontSize": "10px", "color": "#555"},
                            ),
                        ],
                        style={"marginBottom": "4px"},
                    ),
                    html.Div(
                        [
                            html.Span(
                                "AVG ",
                                style={
                                    "fontSize": "9px",
                                    "color": "#444",
                                    "letterSpacing": "1px",
                                },
                            ),
                            html.Span(
                                format_laptime(avg),
                                style={
                                    "fontSize": "13px",
                                    "fontWeight": "700",
                                    "color": "#888",
                                },
                            ),
                        ]
                    ),
                ],
            )
        )
    return html.Div(
        style={"display": "flex", "gap": "8px", "marginTop": "10px"}, children=cards
    )


def distribution_scatter(laps, drivers, drv_colors):
    """Scatt all lap times per driver, one column per driver"""
    fig = go.Figure()
    for drv in drivers:
        times = [
            l["LapTimeSec"] for l in laps if l["Driver"] == drv and l.get("LapTimeSec")
        ]
        if not times:
            continue
        color = drv_colors.get(drv, "#AAAAAA")
        fig.add_trace(
            go.Scatter(
                x=[drv] * len(times),
                y=times,
                mode="markers",
                marker=dict(size=8, color=color, opacity=0.75),
                name=drv,
                hovertemplate=f"<b>{drv}</b><br>%{{y:.3f}}s<extra></extra>",
            )
        )
    fig.update_layout(
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0a0c11",
        font=dict(color="#888", size=10),
        height=440,
        margin=dict(l=60, r=80, t=24, b=52),
        hoverlabel=dict(
            bgcolor="#13161e",
            bordercolor="#252830",
            font=dict(color="#e0e0e0", size=11),
        ),
        legend=dict(
            bgcolor="rgba(13,15,20,0.9)",
            bordercolor="#1a1d24",
            borderwidth=1,
            font=dict(size=11, color="#ccc"),
            orientation="h",
            x=0,
            y=1.06,
        ),
        xaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            showline=True,
            linecolor="#1a1d24",
        ),
        yaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            showline=True,
            linecolor="#1a1d24",
        ),
        hovermode="closest",
        showlegend=False,
        xaxis_title=dict(text="Driver", font=dict(size=10, color="#666")),
        yaxis_title=dict(text="Time (s)", font=dict(size=10, color="#666")),
    )
    return fig


def consistency_iqr(laps, drivers, drv_colors):
    """IQR shows pace spread per drive"""
    fig = go.Figure()
    for drv in drivers:
        times = np.array(
            [
                l["LapTimeSec"]
                for l in laps
                if l["Driver"] == drv and l.get("LapTimeSec")
            ]
        )
        if len(times) < 4:
            continue
        color = drv_colors.get(drv, "#AAAAAA")
        med = float(np.median(times))
        clean = times[times < med * 1.07]
        if len(clean) < 2:
            continue
        q1, q3 = np.percentile(clean, 25), np.percentile(clean, 75)
        # All points
        fig.add_trace(
            go.Scatter(
                x=[drv] * len(times),
                y=times,
                mode="markers",
                marker=dict(size=5, color=color, opacity=0.35),
                showlegend=False,
                hovertemplate=f"<b>{drv}</b><br>%{{y:.3f}}s<extra></extra>",
            )
        )
        # IQR bar
        fig.add_trace(
            go.Scatter(
                x=[drv, drv],
                y=[q1, q3],
                mode="lines",
                line=dict(color=color, width=12),
                name=drv,
                hovertemplate=(
                    f"<b>{drv}</b>  IQR<br>"
                    f"Q1: {q1:.3f}s  Q3: {q3:.3f}s<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0a0c11",
        font=dict(color="#888", size=10),
        height=440,
        margin=dict(l=60, r=80, t=24, b=52),
        hoverlabel=dict(
            bgcolor="#13161e",
            bordercolor="#252830",
            font=dict(color="#e0e0e0", size=11),
        ),
        legend=dict(
            bgcolor="rgba(13,15,20,0.9)",
            bordercolor="#1a1d24",
            borderwidth=1,
            font=dict(size=11, color="#ccc"),
            orientation="h",
            x=0,
            y=1.06,
        ),
        xaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            showline=True,
            linecolor="#1a1d24",
        ),
        yaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            showline=True,
            linecolor="#1a1d24",
        ),
        hovermode="closest",
        xaxis_title=dict(text="Driver", font=dict(size=10, color="#666")),
        yaxis_title=dict(text="Time (s)", font=dict(size=10, color="#666")),
    )
    return fig


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
                "📈",
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
    type="circle",
    color="#e8002d",
    children=html.Div(id="progression-container", children=[empty()]),
)


@callback(
    Output("progression-container", "children"),
    Input("store-race", "data"),
    Input("store-selected-drivers", "data"),
    prevent_initial_call=True,
)
@tab_timer("progression")
def render(store, selected_drivers):
    if not store:
        return empty()

    drivers = selected_drivers or [d["drv"] for d in store.get("drivers", [])]
    if not drivers:
        return html.Div(
            "Select drivers from the sidebar.",
            style={"color": "#555", "padding": "20px"},
        )

    laps = store.get("laps", [])
    driver_meta = {d["drv"]: d for d in store.get("drivers", [])}
    drv_colors = {d["drv"]: d["color"] for d in store.get("drivers", [])}
    total_laps = max((l["LapNumber"] for l in laps), default=0)

    return html.Div(
        [
            # Lap time comprison + stat cards
            html.Div(
                style={
                    "background": BG2,
                    "border": f"1px solid {GRID}",
                    "borderRadius": "6px",
                    "padding": "16px",
                    "marginBottom": "12px",
                },
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                        },
                        children=[
                            _section("LAP-BY-LAP PROGRESSION"),
                            html.Span(
                                f"{total_laps} LAPS",
                                style={
                                    "fontSize": "10px",
                                    "color": "#555",
                                    "letterSpacing": "1px",
                                    "fontWeight": "700",
                                },
                            ),
                        ],
                    ),
                    dcc.Graph(
                        figure=lap_time_comparison(laps, drivers, drv_colors),
                        config={"displayModeBar": True},
                    ),
                    driver_stat_cards(laps, drivers, driver_meta),
                ],
            ),
            # Distriution + consistetncy side by side
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "12px",
                    "marginBottom": "12px",
                },
                children=[
                    _chart_card(
                        "LAP TIME DISTRIBUTION",
                        distribution_scatter(laps, drivers, drv_colors),
                    ),
                    _chart_card(
                        "CONSISTENCY (IQR)", consistency_iqr(laps, drivers, drv_colors)
                    ),
                ],
            ),
            # Position flow
            _chart_card(
                "POSITION FLOW",
                position_flow.build(laps, drivers, drv_colors),
            ),
        ]
    )
