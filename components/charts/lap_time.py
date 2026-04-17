"""
components/charts/lap_time.py
Lap time vs lap number, colored by tyre compound.
Improved: thicker lines, bigger markers, driver labels, better axes.
"""
import plotly.graph_objects as go
from components.shared import TYRE_COLORS, GRID, FONT, hex_to_rgba


def build(laps: list, drivers: list, drv_colors: dict) -> go.Figure:
    fig  = go.Figure()
    seen = set()

    for drv in drivers:
        drv_laps = sorted(
            [l for l in laps if l["Driver"] == drv and l.get("LapTimeSec")],
            key=lambda l: l["LapNumber"],
        )
        if not drv_laps:
            continue
        driver_color = drv_colors.get(drv, "#AAAAAA")
        segments = _split_segments(drv_laps)

        for compound, lap_numbers, lap_times in segments:
            comp_color = TYRE_COLORS.get(compound, "#555")
            show_leg   = compound not in seen
            seen.add(compound)
            fig.add_trace(go.Scatter(
                x=lap_numbers, y=lap_times,
                mode="markers+lines",
                marker=dict(size=6, color=comp_color,
                            line=dict(width=1, color=driver_color)),
                line=dict(color=comp_color, width=2.2),
                name=compound, legendgroup=compound,
                showlegend=show_leg,
                hovertemplate=(
                    f"<b>{drv}</b>  Lap %{{x}}<br>"
                    f"<span style='color:{comp_color}'>{compound}</span>"
                    "  %{y:.3f}s<extra></extra>"
                ),
            ))

        last = drv_laps[-1]
        fig.add_annotation(
            x=last["LapNumber"], y=last["LapTimeSec"],
            text=f"<b>{drv}</b>",
            showarrow=False,
            font=dict(size=11, color=driver_color, family=FONT),
            xanchor="left", xshift=9,
        )

    _PLOT_BG = "#0a0c11"
    fig.update_layout(
        paper_bgcolor="#0d0f14", plot_bgcolor=_PLOT_BG,
        font=dict(color="#888", family=FONT, size=10),
        height=420, margin=dict(l=58, r=80, t=28, b=52),
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
                   tickfont=dict(size=10, color="#777"),
                   title=dict(text="Lap time (s)", font=dict(size=10, color="#666")),
                   showline=True, linecolor="#1a1d24"),
    )
    return fig


def _split_segments(drv_laps):
    segs, cur_comp, cur_laps, cur_times = [], None, [], []
    for lap in drv_laps:
        c = lap.get("Compound", "UNKNOWN")
        if c != cur_comp:
            if cur_laps:
                segs.append((cur_comp, cur_laps, cur_times))
            cur_comp, cur_laps, cur_times = c, [], []
        cur_laps.append(lap["LapNumber"])
        cur_times.append(lap["LapTimeSec"])
    if cur_laps:
        segs.append((cur_comp, cur_laps, cur_times))
    return segs
