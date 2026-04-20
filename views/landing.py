from dash import html, dcc
from components.shared import BG2, GRID, TEXT, ACCENT, FONT


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