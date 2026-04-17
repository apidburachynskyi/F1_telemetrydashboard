from dash import html, dcc
from components.shared import (
    AVAILABLE_YEARS, PRELOADED_RACES,
    BG2, GRID, TEXT, ACCENT, MUTED,
)


def _label(text):
    return html.Div(text, style={
        "fontSize": "10px", "fontWeight": "700",
        "letterSpacing": "1.5px", "color": MUTED, "marginBottom": "6px",
    })


def _section_title(text):
    return html.Div(text, style={
        "fontSize": "11px", "fontWeight": "700", "letterSpacing": "2px",
        "color": TEXT, "borderLeft": f"3px solid {ACCENT}",
        "paddingLeft": "8px", "marginBottom": "12px",
    })


def build_sidebar():
    return html.Div(
        style={
            "width": "220px", "minWidth": "220px",
            "background": BG2, "borderRight": f"1px solid {GRID}",
            "minHeight": "100vh", "padding": "16px 12px", "flexShrink": "0",
        },
        children=[
            _section_title("SESSION"),

            _label("YEAR"),
            dcc.Dropdown(id="dd-year",
                options=[{"label": str(y), "value": y} for y in AVAILABLE_YEARS],
                value=AVAILABLE_YEARS[0], clearable=False,
                style={"marginBottom": "10px"}),

            _label("GRAND PRIX"),
            dcc.Dropdown(id="dd-gp", placeholder="Select Grand Prix",
                clearable=False, style={"marginBottom": "10px"}),



            html.Button("LOAD SESSION", id="btn-load", n_clicks=0, style={
                "width": "100%", "padding": "9px",
                "background": ACCENT, "border": "none", "borderRadius": "4px",
                "color": "#fff", "fontSize": "11px", "fontWeight": "700",
                "letterSpacing": "1.5px", "cursor": "pointer",
            }),

            dcc.Loading(
                type="circle",
                color="#e8002d",
                children=html.Div(id="load-status", style={
                    "marginTop": "8px", "fontSize": "10px",
                    "color": "#555", "minHeight": "16px",
                }),
            ),

            html.Div(style={"borderTop": f"1px solid {GRID}", "margin": "14px 0"}),

            # Drivers header
            html.Div(style={"display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "8px"}, children=[
                _section_title("DRIVERS"),
                html.Div(id="driver-count", style={"fontSize": "10px", "color": "#555"}),
            ]),

            # Driver checklist — instant selection, no callback delay
            # Populated by load_session callback
            html.Div(
                id="driver-checklist-wrap",
                children=[
                    html.Div("Load a session to see drivers.",
                             style={"fontSize": "11px", "color": "#333", "padding": "8px 0"})
                ],
            ),

            html.Div(
                "Add one driver at a time and wait for pages to update.",
                style={
                    "fontSize": "10px", "color": "#444",
                    "marginTop": "10px", "lineHeight": "1.5",
                    "borderTop": f"1px solid {GRID}", "paddingTop": "8px",
                },
            ),
        ],
    )
