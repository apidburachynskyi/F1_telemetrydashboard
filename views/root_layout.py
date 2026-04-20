from dash import html, dcc
from components.shared import FONT
from views.landing import landing_page


def build_root_layout():
    return html.Div(
        style={"fontFamily": FONT},
        children=[
            dcc.Store(id="store-race", data=None),
            dcc.Store(id="store-quali", data=None),
            dcc.Store(id="store-session-key", data=None),
            dcc.Store(id="store-selected-drivers", data=[]),
            dcc.Store(id="active-tab", data="overview"),
            html.Div(id="app-root", children=[landing_page()]),
        ],
    )
