import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback, ctx

from components.perf_metrics import tab_timer
from components.shared import (
    BG2,
    BG3,
    GRID,
    TEXT,
    MUTED,
    ACCENT,
    FONT,
    team_logo_img,
)


# Usefull


def _to_seconds(t_str):
    """Convert 'M:SS.mmm' string to float seconds."""
    try:
        parts = str(t_str).split(":")
        return float(parts[0]) * 60 + float(parts[1])
    except Exception:
        return None


def parse_segment(results, segment):
    """Return sorted rows for one Q segment with gap to P1."""
    key = segment.lower()
    rows = []
    for r in results:
        t = r.get(key)
        if t and t != "–":
            s = _to_seconds(t)
            if s:
                rows.append({**r, "seg_time": t, "seg_secs": s})
    rows.sort(key=lambda r: r["seg_secs"])
    if rows:
        leader = rows[0]["seg_secs"]
        for i, r in enumerate(rows):
            r["seg_gap"] = "–" if i == 0 else f"+{r['seg_secs']-leader:.3f}s"
            r["seg_pos"] = i + 1
    return rows


# UI


def _th(text):
    return html.Th(
        text,
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


def _td(content, bold=False, color=None, size="12px"):
    return html.Td(
        content,
        style={
            "padding": "7px 10px",
            "fontSize": size,
            "color": color or TEXT,
            "borderBottom": f"1px solid {BG3}",
            "fontWeight": "700" if bold else "400",
        },
    )


def _pos_badge(pos, elim=False):
    colors = {1: "#ffd700", 2: "#c0c0c0", 3: "#cd7f32"}
    if elim:
        bg, tc = "#1a0508", ACCENT
    elif pos in colors:
        bg, tc = colors[pos], "#000"
    else:
        bg, tc = BG3, TEXT
    border = (
        f"1px solid {ACCENT}"
        if elim
        else ("none" if pos in colors else f"1px solid {GRID}")
    )
    return html.Div(
        str(pos),
        style={
            "width": "28px",
            "height": "28px",
            "borderRadius": "5px",
            "background": bg,
            "color": tc,
            "fontWeight": "700",
            "fontSize": "12px",
            "display": "flex",
            "border": border,
            "alignItems": "center",
            "justifyContent": "center",
        },
    )


def _driver_cell(r):
    color = r["color"]
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "7px"},
        children=[
            html.Div(
                style={
                    "width": "3px",
                    "height": "26px",
                    "background": color,
                    "borderRadius": "2px",
                }
            ),
            html.Div(
                [
                    html.Div(
                        r["first"].upper(), style={"fontSize": "9px", "color": "#555"}
                    ),
                    html.Div(
                        r["last"].upper(),
                        style={"fontSize": "12px", "fontWeight": "700", "color": color},
                    ),
                ]
            ),
        ],
    )


def _segment_table(rows, advance_count=None):
    table_rows = []
    for r in rows:
        pos = r["seg_pos"]
        elim = advance_count is not None and pos > advance_count
        table_rows.append(
            html.Tr(
                style={
                    "opacity": "0.4" if elim else "1",
                    "transition": "background 0.12s",
                    "borderBottom": f"1px solid {BG3}",
                },
                children=[
                    html.Td(
                        _pos_badge(pos, elim),
                        style={"padding": "7px 8px", "width": "32px"},
                    ),
                    html.Td(_driver_cell(r), style={"padding": "7px 8px"}),
                    html.Td(
                        html.Div(
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "4px",
                            },
                            children=[
                                logo
                                for logo in [team_logo_img(r["team"], "14px")]
                                if logo
                            ]
                            + [html.Span(r["team"])],
                        ),
                        style={
                            "padding": "7px 10px",
                            "fontSize": "10px",
                            "color": "#888",
                            "borderBottom": f"1px solid {BG3}",
                            "maxWidth": "110px",
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                    ),
                    html.Td(
                        r["seg_time"],
                        style={
                            "padding": "7px 10px",
                            "fontSize": "12px",
                            "fontWeight": "600",
                            "color": TEXT,
                            "borderBottom": f"1px solid {BG3}",
                        },
                    ),
                    html.Td(
                        r["seg_gap"],
                        style={
                            "padding": "7px 10px",
                            "fontSize": "11px",
                            "color": "#888",
                            "borderBottom": f"1px solid {BG3}",
                        },
                    ),
                ],
            )
        )
    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse"},
        children=[
            html.Thead(
                html.Tr([_th(h) for h in ["P", "DRIVER", "TEAM", "TIME", "GAP"]])
            ),
            html.Tbody(table_rows),
        ],
    )


def _seg_header(title, color=ACCENT):
    return html.Div(
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "7px",
            "marginBottom": "12px",
            "paddingBottom": "8px",
            "borderBottom": f"1px solid {GRID}",
        },
        children=[
            html.Div(
                style={
                    "width": "3px",
                    "height": "18px",
                    "background": color,
                    "borderRadius": "2px",
                    "flexShrink": "0",
                }
            ),
            html.Div(
                title,
                style={
                    "fontSize": "11px",
                    "fontWeight": "700",
                    "letterSpacing": "2px",
                    "color": color,
                },
            ),
        ],
    )


# Timeline chart


def build_timeline(results, segment="Q1"):
    """Bubble chart: position vs lap time for one segment."""
    rows = parse_segment(results, segment)
    if not rows:
        return go.Figure()

    advance_map = {"Q1": 15, "Q2": 10, "Q3": None}
    advance = advance_map.get(segment)

    fig = go.Figure()

    for r in rows:
        pos = r["seg_pos"]
        color = r["color"]
        t_sec = r["seg_secs"]
        advanced = advance is None or pos <= advance

        fig.add_trace(
            go.Scatter(
                x=[f"P{pos} {r['drv']}"],
                y=[t_sec],
                mode="markers",
                marker=dict(
                    size=20,
                    color=color if advanced else "rgba(0,0,0,0)",
                    line=dict(color=color, width=3 if not advanced else 0),
                    symbol="circle",
                ),
                showlegend=False,
                hovertemplate=(
                    f"<b>{r['first']} {r['last']}</b><br>"
                    f"P{pos}  {r['seg_time']}<br>"
                    f"{'✓ Advanced' if advanced else '✗ Eliminated'}<extra></extra>"
                ),
            )
        )

    # Cutoff line
    if advance and len(rows) >= advance:
        cutoff = rows[advance - 1]["seg_secs"]
        fig.add_hline(
            y=cutoff,
            line=dict(color=ACCENT, width=1.5, dash="dash"),
            annotation_text=f"Cutoff (P{advance})",
            annotation_font=dict(color=ACCENT, size=9),
        )

    # Format Y ticks as M:SS.mmm
    tick_vals = [r["seg_secs"] for r in rows]
    tick_text = [r["seg_time"] for r in rows]

    fig.update_layout(
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0a0c11",
        font=dict(color="#888", family=FONT, size=10),
        height=440,
        margin=dict(l=84, r=28, t=20, b=88),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#13161e", bordercolor="#252830", font=dict(color=TEXT, size=11)
        ),
        showlegend=False,
        xaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            tickangle=-42,
            showline=True,
            linecolor="#1a1d24",
            title=dict(text="Driver", font=dict(size=10, color="#666")),
        ),
        yaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#777"),
            tickvals=tick_vals,
            ticktext=tick_text,
            autorange="reversed",
            showline=True,
            linecolor="#1a1d24",
            title=dict(text="Lap Time", font=dict(size=10, color="#666")),
        ),
    )
    return fig


# Weather car


def _wcard(icon, label, value):
    return html.Div(
        style={
            "background": BG2,
            "border": f"1px solid {GRID}",
            "borderRadius": "6px",
            "padding": "10px 14px",
            "flex": "1",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "5px",
                    "marginBottom": "3px",
                },
                children=[
                    html.Span(icon, style={"fontSize": "12px"}),
                    html.Span(
                        label,
                        style={
                            "fontSize": "9px",
                            "fontWeight": "700",
                            "letterSpacing": "1.5px",
                            "color": "#444",
                        },
                    ),
                ],
            ),
            html.Div(
                value, style={"fontSize": "15px", "fontWeight": "700", "color": TEXT}
            ),
        ],
    )


# Layout + callback─


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
                "🏎",
                style={
                    "fontSize": "36px",
                    "background": "#1a0508",
                    "borderRadius": "12px",
                    "padding": "12px 16px",
                },
            ),
            html.Div(
                "LOAD A QUALIFYING SESSION",
                style={
                    "fontSize": "14px",
                    "fontWeight": "700",
                    "letterSpacing": "2px",
                    "color": TEXT,
                },
            ),
            html.Div(
                "Select Qualifying from the session type dropdown.",
                style={"fontSize": "12px", "color": "#555"},
            ),
        ],
    )


layout = html.Div(id="quali-container", children=[empty()])


@callback(
    Output("quali-container", "children"),
    Input("store-quali", "data"),
    prevent_initial_call=True,
)
@tab_timer("qualifying")
def render(store):
    if not store:
        return empty()
    if store.get("session_type", "Race") == "Race":
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
                html.Div("🏁", style={"fontSize": "36px"}),
                html.Div(
                    "Race session loaded.",
                    style={"fontSize": "14px", "fontWeight": "700", "color": TEXT},
                ),
                html.Div(
                    "Switch to the Overview tab to see race results.",
                    style={"fontSize": "12px", "color": "#555"},
                ),
            ],
        )

    results = store.get("results", [])
    if not results:
        return html.Div(
            "No qualifying data available.", style={"color": "#555", "padding": "20px"}
        )

    ev = store.get("event", {})
    w = store.get("weather", {})

    def wfmt(key, unit):
        v = w.get(key)
        return f"{v}{unit}" if v else "–"

    weather_row = html.Div(
        style={
            "display": "flex",
            "gap": "8px",
            "marginBottom": "14px",
            "flexWrap": "wrap",
        },
        children=[
            _wcard("🌍", "COUNTRY", ev.get("country", "–")),
            _wcard("🏁", "CIRCUIT", ev.get("circuit", "–")),
            _wcard("🌡", "AIR TEMP", wfmt("air_temp", "°C")),
            _wcard("🔥", "TRACK TEMP", wfmt("track_temp", "°C")),
            _wcard("💧", "HUMIDITY", wfmt("humidity", "%")),
            _wcard("💨", "WIND", wfmt("wind", " km/h")),
        ],
    )

    q3 = parse_segment(results, "Q3")
    q2 = parse_segment(results, "Q2")
    q1 = parse_segment(results, "Q1")

    # Section 1: Results tables─
    results_section = html.Div(
        style={
            "background": BG2,
            "border": f"1px solid {GRID}",
            "borderRadius": "6px",
            "padding": "16px",
            "marginBottom": "14px",
        },
        children=[
            html.Div(
                "QUALIFYING RESULTS",
                style={
                    "fontSize": "12px",
                    "fontWeight": "700",
                    "letterSpacing": "2px",
                    "color": TEXT,
                    "borderLeft": f"3px solid {ACCENT}",
                    "paddingLeft": "10px",
                    "marginBottom": "16px",
                },
            ),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr 1fr",
                    "gap": "16px",
                },
                children=[
                    html.Div(
                        [_seg_header("Q3"), _segment_table(q3, advance_count=None)]
                    ),
                    html.Div([_seg_header("Q2"), _segment_table(q2, advance_count=10)]),
                    html.Div([_seg_header("Q1"), _segment_table(q1, advance_count=15)]),
                ],
            ),
        ],
    )

    # Section 2: Timeline chart─
    # Segment selector
    seg_selector = html.Div(
        style={"display": "flex", "gap": "8px", "marginBottom": "12px"},
        children=[
            html.Button(
                seg,
                id=f"quali-seg-{seg}",
                n_clicks=0,
                style={
                    "flex": "1",
                    "padding": "8px",
                    "cursor": "pointer",
                    "fontSize": "11px",
                    "fontWeight": "700",
                    "letterSpacing": "1px",
                    "background": "#1a1d24" if seg == "Q1" else BG3,
                    "color": TEXT if seg == "Q1" else "#555",
                    "border": f"1px solid {ACCENT if seg=='Q1' else GRID}",
                    "borderRadius": "4px",
                },
            )
            for seg in ["Q1", "Q2", "Q3"]
        ],
    )

    timeline_section = html.Div(
        style={
            "background": BG2,
            "border": f"1px solid {GRID}",
            "borderRadius": "6px",
            "padding": "16px",
        },
        children=[
            html.Div(
                "QUALIFYING TIMELINE",
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
            seg_selector,
            html.Div(
                id="quali-timeline-chart",
                children=[
                    dcc.Graph(
                        figure=build_timeline(results, "Q1"),
                        config={"displayModeBar": True},
                    )
                ],
            ),
            html.Div(
                "● advanced  ○ eliminated  — red line = cutoff",
                style={"fontSize": "10px", "color": "#444", "marginTop": "8px"},
            ),
        ],
    )

    return html.Div([weather_row, results_section, timeline_section])


@callback(
    Output("quali-timeline-chart", "children"),
    Input("quali-seg-Q1", "n_clicks"),
    Input("quali-seg-Q2", "n_clicks"),
    Input("quali-seg-Q3", "n_clicks"),
    Input("store-quali", "data"),
    prevent_initial_call=True,
)
def update_timeline(q1c, q2c, q3c, store):
    import dash

    if not store or store.get("session_type", "Race") == "Race":
        raise dash.exceptions.PreventUpdate

    triggered = (
        ctx.triggered[0]["prop_id"] if ctx.triggered else "quali-seg-Q1.n_clicks"
    )
    if "Q3" in triggered:
        seg = "Q3"
    elif "Q2" in triggered:
        seg = "Q2"
    else:
        seg = "Q1"

    results = store.get("results", [])
    return dcc.Graph(
        figure=build_timeline(results, seg), config={"displayModeBar": True}
    )
