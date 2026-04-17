import plotly.graph_objects as go
from components.shared import GRID, FONT


def build(laps: list, drivers: list, drv_colors: dict) -> go.Figure:
    fig = go.Figure()

    for drv in drivers:
        drv_laps = sorted(
            [l for l in laps if l["Driver"] == drv and l.get("Position")],
            key=lambda l: l["LapNumber"],
        )
        if not drv_laps:
            continue
        color = drv_colors.get(drv, "#AAAAAA")
        xs    = [l["LapNumber"] for l in drv_laps]
        ys    = [l["Position"]  for l in drv_laps]

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line=dict(color=color, width=2.4, shape="hv"),
            name=drv,
            hovertemplate=f"<b>{drv}</b>  Lap %{{x}}  P%{{y}}<extra></extra>",
        ))

        fig.add_annotation(
            x=xs[-1], y=ys[-1],
            text=f"<b>{drv}</b>",
            showarrow=False,
            font=dict(size=11, color=color, family=FONT),
            xanchor="left", xshift=9,
        )

    fig.update_layout(
        paper_bgcolor="#0d0f14", plot_bgcolor="#0a0c11",
        font=dict(color="#888", family=FONT, size=10),
        height=420, margin=dict(l=52, r=80, t=24, b=52),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#13161e", bordercolor="#252830",
                        font=dict(color="#e0e0e0", size=11)),
        legend=dict(bgcolor="rgba(13,15,20,0.92)", bordercolor="#1a1d24",
                    borderwidth=1, font=dict(size=11, color="#ccc"),
                    orientation="h", x=0, y=1.06, itemsizing="constant"),
        xaxis=dict(gridcolor="#161920", zeroline=False,
                   tickfont=dict(size=10, color="#777"),
                   title=dict(text="Lap", font=dict(size=10, color="#666")),
                   showline=True, linecolor="#1a1d24"),
        yaxis=dict(gridcolor="#161920", zeroline=False,
                   autorange="reversed", dtick=1,
                   tickfont=dict(size=10, color="#777"),
                   title=dict(text="Position", font=dict(size=10, color="#666")),
                   showline=True, linecolor="#1a1d24"),
    )
    return fig
