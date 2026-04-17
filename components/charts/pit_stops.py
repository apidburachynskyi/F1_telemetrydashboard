import plotly.graph_objects as go
import pandas as pd
import numpy as np
from components.shared import (
    GRID, TEXT,
    chart_theme, axis_label,
)


# Data preparation

def prepare_pit_data(laps: list, team_colors: dict) -> pd.DataFrame:
    """
    Extract pit stop events from the laps list.
    Returns a DataFrame with one row per pit stop:
        pilote, komanda, color, Lap, scbds
    """
    rows = []
    for lap in laps:
        pit_in  = lap.get("PitInTimeSec")
        pit_out = lap.get("PitOutTimeSec")
        team    = lap.get("Team", "")

        # Skip laps without a pit stop
        if pit_in is None or pit_out is None:
            continue

        try:
            duration = float(pit_out) - float(pit_in)
        except (TypeError, ValueError):
            continue

        #real pit stops are between 5 and 120 seconds
        if not (5 < duration < 120):
            continue

        rows.append({
            "Driver":    lap["Driver"],
            "Team":      team,
            "TeamColor": team_colors.get(team, "#AAAAAA"),
            "Lap":       int(lap["LapNumber"]),
            "Duration":  round(duration, 1),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        # Number stops per team (1,2,..)
        df["StopNumber"] = df.groupby("Team").cumcount() + 1

    return df


def build_team_colors(store: dict) -> dict:
    """
    Build a team color mapping from the drivers store data.
    Uses the first driver found per team.
    """
    team_colors = {}
    for d in store.get("drivers", []):
        team = d.get("team", "")
        if team and team not in team_colors:
            team_colors[team] = d["color"]
    return team_colors


# Chart 1: Timeline

def timeline(pit_df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot: x = lap number, y = stop duration.
    One marker per pit stop, colored by team.
    Labels show the duration in seconds.
    """
    fig = go.Figure()

    for team, group in pit_df.groupby("Team"):
        color = group.iloc[0]["TeamColor"]

        fig.add_trace(go.Scatter(
            x=group["Lap"],
            y=group["Duration"],
            mode="markers+text",
            marker=dict(size=18, color=color, line=dict(width=2, color="#fff")),
            text=[f"{d}s" for d in group["Duration"]],
            textposition="top center",
            textfont=dict(size=10, color=color),
            name=team,
            hovertemplate=(
                f"<b>{team}</b><br>"
                "Lap %{x}<br>"
                "Duration: <b>%{y:.1f}s</b><extra></extra>"
            ),
        ))

    fig.update_layout(
        paper_bgcolor="#0d0f14", plot_bgcolor="#0a0c11",
        font=dict(color="#888", size=10),
        height=400, margin=dict(l=56, r=28, t=24, b=52),
        hovermode="closest",
        hoverlabel=dict(bgcolor="#13161e", bordercolor="#252830", font=dict(color="#e0e0e0", size=11)),
        legend=dict(bgcolor="rgba(13,15,20,0.9)", bordercolor="#1a1d24", borderwidth=1,
                    font=dict(size=11, color="#ccc"), orientation="h", x=0, y=1.06),
        xaxis=dict(gridcolor="#161920", zeroline=False, tickfont=dict(size=10, color="#777"),
                   title=dict(text="Lap Number", font=dict(size=10, color="#666")),
                   showline=True, linecolor="#1a1d24"),
        yaxis=dict(gridcolor="#161920", zeroline=False, tickfont=dict(size=10, color="#777"),
                   title=dict(text="Duration (s)", font=dict(size=10, color="#666")),
                   showline=True, linecolor="#1a1d24"),
    )
    return fig


# Chart Average stop duration per team

def avg_duration(pit_df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart: average pit stop duration per team.
    Sorted from fastest to slowest.
    """
    avg = (pit_df.groupby("Team")["Duration"]
           .mean()
           .reset_index()
           .sort_values("Duration", ascending=True))

    # Map team names back to colors
    color_map = dict(zip(pit_df["Team"], pit_df["TeamColor"]))
    bar_colors = [color_map.get(t, "#AAAAAA") for t in avg["Team"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=avg["Team"],
        x=avg["Duration"],
        orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0), opacity=0.88),
        text=[f"{v:.2f}s" for v in avg["Duration"]],
        textposition="outside",
        textfont=dict(color="#e0e0e0", size=12, family="Arial"),
        width=0.55,
        showlegend=False,
        hovertemplate="<b>%{y}</b><br>Average: %{x:.2f}s<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="#0d0f14", plot_bgcolor="#0a0c11",
        font=dict(color="#888", size=10),
        height=360, margin=dict(l=130, r=70, t=16, b=44),
        hovermode="closest",
        hoverlabel=dict(bgcolor="#13161e", bordercolor="#252830", font=dict(color="#e0e0e0", size=11)),
        xaxis=dict(gridcolor="#161920", zeroline=False, tickfont=dict(size=10, color="#777"),
                   title=dict(text="Seconds", font=dict(size=10, color="#666")),
                   showline=True, linecolor="#1a1d24"),
        yaxis=dict(gridcolor="#161920", zeroline=False, tickfont=dict(size=11, color="#ccc"),
                   showline=True, linecolor="#1a1d24"),
    )
    return fig


# Chart 3 Stop-by-stop comparison across teams

def stop_comparison(pit_df: pd.DataFrame) -> go.Figure:

    fig  = go.Figure()
    seen = set()

    for _, row in pit_df.iterrows():
        team        = row["Team"]
        show_legend = team not in seen
        seen.add(team)

        fig.add_trace(go.Bar(
            x=[f"Stop {row['StopNumber']}"],
            y=[row["Duration"]],
            name=team,
            marker=dict(color=row["TeamColor"], line=dict(width=0)),
            text=[f"L{row['Lap']}"],
            textposition="outside",
            textfont=dict(color=TEXT, size=9),
            legendgroup=team,
            showlegend=show_legend,
            hovertemplate=(
                f"<b>{team}</b>  Stop {row['StopNumber']}<br>"
                f"Lap {row['Lap']}<br>"
                f"Duration: <b>{row['Duration']:.1f}s</b><extra></extra>"
            ),
        ))

    fig.update_layout(
        paper_bgcolor="#0d0f14", plot_bgcolor="#0a0c11",
        font=dict(color="#888", size=10),
        height=380, margin=dict(l=56, r=28, t=28, b=48),
        barmode="group", bargap=0.25, bargroupgap=0.08,
        hoverlabel=dict(bgcolor="#13161e", bordercolor="#252830", font=dict(color="#e0e0e0", size=11)),
        legend=dict(bgcolor="rgba(13,15,20,0.9)", bordercolor="#1a1d24", borderwidth=1,
                    font=dict(size=11, color="#ccc"), orientation="h", x=0, y=1.06),
        xaxis=dict(gridcolor="#161920", zeroline=False, tickfont=dict(size=11, color="#ccc"),
                   showline=True, linecolor="#1a1d24"),
        yaxis=dict(gridcolor="#161920", zeroline=False, tickfont=dict(size=10, color="#777"),
                   title=dict(text="Duration (s)", font=dict(size=10, color="#666")),
                   showline=True, linecolor="#1a1d24"),
    )
    return fig



def team_stats_table(pit_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a summary DataFrame with per-team pit stop statistics
    """
    rows = []
    for team, group in pit_df.groupby("Team"):
        rows.append({
            "Team":        team,
            "Stops":       len(group),
            "Best (s)":    round(group["Duration"].min(), 2),
            "Average (s)": round(group["Duration"].mean(), 2),
            "Worst (s)":   round(group["Duration"].max(), 2),
            "Total (s)":   round(group["Duration"].sum(), 2),
        })
    return pd.DataFrame(rows).sort_values("Average (s)")
