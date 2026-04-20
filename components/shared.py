import os
import math
import time
import fastf1
import pandas as pd
import numpy as np
from pathlib import Path


# FastF1 cache
CACHE_DIR = os.environ.get("FF1_CACHE_DIR", "./cache")
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


# Available races─
_FALLBACK_RACES = {
    2026: [
        "Melbourne",
        "Shanghai",
        "Suzuka",
    ],
    2025: [
        "Melbourne",
        "Shanghai",
        "Suzuka",
        "Sakhir",
        "Jeddah",
        "Miami Gardens",
        "Imola",
        "Monte Carlo",
        "Barcelona",
        "Montreal",
        "Spielberg",
        "Silverstone",
        "Spa-Francorchamps",
        "Budapest",
        "Zandvoort",
        "Monza",
        "Baku",
        "Marina Bay",
        "Austin",
        "Mexico City",
        "São Paulo",
        "Las Vegas",
        "Lusail",
        "Yas Marina",
    ],
    2024: [
        "Sakhir",
        "Jeddah",
        "Melbourne",
        "Suzuka",
        "Shanghai",
        "Miami Gardens",
        "Imola",
        "Monte Carlo",
        "Montreal",
        "Barcelona",
        "Spielberg",
        "Silverstone",
        "Budapest",
        "Spa-Francorchamps",
        "Zandvoort",
        "Monza",
        "Baku",
        "Marina Bay",
        "Austin",
        "Mexico City",
        "São Paulo",
        "Las Vegas",
        "Lusail",
        "Yas Marina",
    ],
}


def _load_races() -> tuple[dict, dict]:
    """
    Read races.json if available, else fall back to hardcoded list.
    Returns (PRELOADED_RACES, RACE_DATES).
    PRELOADED_RACES: {year: [name, ...]}
    RACE_DATES:      {year: {name: "YYYY-MM-DD"}}
    """
    races_json = Path(__file__).parent.parent / "data" / "races.json"
    if races_json.exists():
        try:
            import json as _json

            raw = _json.loads(races_json.read_text())
            races, dates = {}, {}
            for k, entries in raw.items():
                year = int(k)
                # entries can be list of str (old) or list of {name, date} (new)
                if entries and isinstance(entries[0], dict):
                    races[year] = [e["name"] for e in entries]
                    dates[year] = {e["name"]: e["date"] for e in entries}
                else:
                    races[year] = entries
                    dates[year] = {}
            return races, dates
        except Exception:
            pass
    return _FALLBACK_RACES, {}


PRELOADED_RACES, RACE_DATES = _load_races()
AVAILABLE_YEARS = sorted(PRELOADED_RACES.keys(), reverse=True)
AVAILABLE_SESSIONS = [
    {"label": "Race", "value": "R"},
    {"label": "Qualifying", "value": "Q"},
]


# Colors
BG = "#08090d"
BG2 = "#0d0f14"
BG3 = "#12151c"
GRID = "#1a1d24"
TEXT = "#e0e0e0"
MUTED = "#555555"
ACCENT = "#e8002d"
FONT = "Arial, sans-serif"

TYRE_COLORS = {
    "SOFT": "#e8002d",
    "MEDIUM": "#ffd700",
    "HARD": "#f0f0f0",
    "INTERMEDIATE": "#39b54a",
    "WET": "#0067ff",
    "UNKNOWN": "#888888",
}

# Team → logo slug mapping
TEAM_LOGO = {
    "mclaren": "mclaren",
    "ferrari": "ferrari",
    "scuderia ferrari": "ferrari",
    "red bull": "redbull",
    "red bull racing": "redbull",
    "oracle red bull": "redbull",
    "mercedes": "mercedes",
    "aston martin": "astonmartin",
    "aston martin f1": "astonmartin",
    "alpine": "alpine",
    "alpine f1": "alpine",
    "williams": "williams",
    "racing bulls": "racingbulls",
    "rb": "racingbulls",
    "visa cashapp rb": "racingbulls",
    "kick sauber": "sauber",
    "sauber": "sauber",
    "haas": "haas",
    "haas f1 team": "haas",
    "haas f1": "haas",
    # FastF1 TeamName variants
    "mclaren f1 team": "mclaren",
    "scuderia ferrari hp": "ferrari",
    "oracle red bull racing": "redbull",
    "mercedes-amg petronas": "mercedes",
    "mercedes amg petronas": "mercedes",
    "aston martin aramco": "astonmartin",
    "bt sport alpine f1": "alpine",
    "williams racing": "williams",
    "visa cash app rb": "racingbulls",
    "stake f1 team kick sauber": "sauber",
    "moneygramm haas f1": "haas",
    "moneygram haas f1": "haas",
}


def team_logo_img(team_name, height="16px"):
    """Return an html.Img for the team logo, or None if not found"""
    from dash import html

    slug = TEAM_LOGO.get((team_name or "").lower().strip())
    if not slug:
        return None
    return html.Img(
        src=f"/assets/logos/{slug}.svg",
        style={
            "height": height,
            "width": "auto",
            "opacity": "0.9",
            "verticalAlign": "middle",
            "marginRight": "5px",
        },
    )


def chart_theme(
    height=380, margin_left=56, margin_right=28, margin_top=24, margin_bottom=52
):
    return dict(
        paper_bgcolor=BG2,
        plot_bgcolor="#0a0c11",
        font=dict(color="#888", family=FONT, size=10),
        height=height,
        margin=dict(l=margin_left, r=margin_right, t=margin_top, b=margin_bottom),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#13161e", bordercolor="#252830", font=dict(color=TEXT, size=11)
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=10, color="#aaa"),
            orientation="h",
            x=0,
            y=1.10,
        ),
        xaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#666"),
            showline=True,
            linecolor="#1a1d24",
        ),
        yaxis=dict(
            gridcolor="#161920",
            zeroline=False,
            tickfont=dict(size=10, color="#666"),
            showline=True,
            linecolor="#1a1d24",
        ),
    )


def axis_label(text):
    return dict(text=text, font=dict(size=9, color="#444", family=FONT))


def hex_to_rgba(hex_color, alpha=0.08):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# Safe formatting
def safe_str(value, fallback="–"):
    s = str(value) if value is not None else ""
    return fallback if s in ("", "nan", "NaT", "None", "NaN", "<NA>") else s


def format_gap(value, is_leader=False):
    """Format time gap — returns '–' for leader or invalid values."""
    if is_leader:
        return "–"
    try:
        if pd.isna(value):
            return "–"
        seconds = (
            value.total_seconds() if hasattr(value, "total_seconds") else float(value)
        )
        if math.isnan(seconds) or seconds < 0:
            return "–"
        return f"+{seconds:.3f}s"
    except Exception:
        return "–"


def format_laptime(value):
    """Format M:SS.mmm from timedelta or float seconds."""
    try:
        if pd.isna(value):
            return "–"
        seconds = (
            value.total_seconds() if hasattr(value, "total_seconds") else float(value)
        )
        if math.isnan(seconds) or seconds <= 0:
            return "–"
        minutes = int(seconds // 60)
        return f"{minutes}:{seconds % 60:06.3f}"
    except Exception:
        return "–"


def timedelta_to_seconds(value):
    """Convert timedelta / float to seconds. Returns None on failure."""
    try:
        if pd.isna(value):
            return None
        s = value.total_seconds() if hasattr(value, "total_seconds") else float(value)
        return None if math.isnan(s) else s
    except Exception:
        return None


# Driver metadata─
def get_driver_meta(session, driver_code):
    try:
        info = session.get_driver(driver_code)
        return {
            "color": "#" + info.get("TeamColor", "AAAAAA"),
            "team": info.get("TeamName", ""),
            "first": info.get("FirstName", ""),
            "last": info.get("LastName", driver_code),
        }
    except Exception:
        return {"color": "#AAAAAA", "team": "", "first": "", "last": driver_code}


# Retry helper
def _retry(func, retries=3, delay=2, fallback=None):
    """Retry a function up to `retries` times before returning fallback."""
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == retries:
                print(f"[F1] Failed after {retries} attempts: {e}")
                return fallback
            print(f"[F1] Attempt {attempt} failed: {e} — retry in {delay}s")
            time.sleep(delay)


# Session loading
def load_session(year, gp, session_type):
    def _load():
        s = fastf1.get_session(int(year), gp, session_type)
        s.load()
        return s

    result = _retry(_load, retries=3, delay=3)
    if result is None:
        raise RuntimeError(f"Could not load {year} {gp} {session_type}")
    return result


# Placeholder
def get_cached_session(year, gp, session_type):
    return load_session(year, gp, session_type)


# Detect session type
def is_qualifying(session):
    """Return True if this session is qualifying (Q, SQ, etc.)."""
    try:
        return session.session_info.get("Type", "") in ("Q", "SQ", "SS")
    except Exception:
        return False


# Session to dcc.Store
def session_to_store(session):
    """
    Serialize a FastF1 session to a JSON-safe dict for dcc.Store.
    """
    store = {}
    store["session_type"] = session.name  # e.g. "Race" or "Qualifying"

    # Event
    event = session.event
    store["event"] = {
        "name": safe_str(event.get("EventName", "")),
        "country": safe_str(event.get("Country", "")),
        "circuit": safe_str(event.get("Location", "")),
        "year": (
            int(event["EventDate"].year)
            if hasattr(event.get("EventDate", ""), "year")
            else 0
        ),
    }

    # Weather
    try:
        wd = _retry(lambda: session.weather_data, retries=2, fallback=None)
        if wd is not None and not wd.empty:
            w = wd.iloc[len(wd) // 2]

            def _wv(col):
                try:
                    return round(float(w[col]), 1)
                except:
                    return None

            store["weather"] = {
                "air_temp": _wv("AirTemp"),
                "track_temp": _wv("TrackTemp"),
                "humidity": _wv("Humidity"),
                "wind": _wv("WindSpeed"),
            }
        else:
            store["weather"] = {}
    except Exception:
        store["weather"] = {}

    # Results Jolpica API first, laps fallback
    try:
        from components.results_loader import (
            fetch_race_results,
            fetch_quali_results,
            build_results_from_laps,
        )

        is_race = store["session_type"] == "Race"
        res = _retry(lambda: session.results, retries=2, fallback=None)

        # Build color/name map from FastF1
        meta_map = {}
        if res is not None and not res.empty:
            for _, r in res.iterrows():
                drv = safe_str(r.get("Abbreviation", ""), "")
                if not drv:
                    continue
                raw_color = safe_str(r.get("TeamColor", "AAAAAA"), "AAAAAA")
                color = "#" + raw_color.replace("#", "").strip()
                if len(color) != 7:
                    color = "#AAAAAA"
                meta_map[drv] = {
                    "color": color,
                    "first": safe_str(r.get("FirstName", "")),
                    "last": safe_str(r.get("LastName", drv), drv),
                    "team": safe_str(r.get("TeamName", "–")),
                    "status": safe_str(r.get("Status", "")),
                }

        ev = store["event"]
        year = ev.get("year", 0)
        gp = ev.get("name", "")

        if is_race:
            # Jolpica for accurate gap + grid
            rows = fetch_race_results(year, gp)
            if rows:
                # Merge colors from FastF1 meta_map
                for row in rows:
                    if row["drv"] in meta_map:
                        row["color"] = meta_map[row["drv"]]["color"]
                    else:
                        row["color"] = "#AAAAAA"
                    row["q1"] = "–"
                    row["q2"] = "–"
                    row["q3"] = "–"
            else:
                # Fallback: build from laps
                rows = build_results_from_laps(session, meta_map)
        else:
            # Qualifying Jolpica
            rows = fetch_quali_results(year, gp)
            if rows:
                for row in rows:
                    if row["drv"] in meta_map:
                        row["color"] = meta_map[row["drv"]]["color"]
                    else:
                        row["color"] = "#AAAAAA"
                    row["gap"] = row.get("q3") or row.get("q1", "–")
                    row["grid"] = None
                    row["status"] = ""
            else:
                # Fallback from session.results ClassifiedPosition
                rows = []
                if res is not None and not res.empty:
                    for _, r in res.iterrows():
                        drv = safe_str(r.get("Abbreviation", ""), "")
                        if not drv:
                            continue
                        try:
                            pos = int(float(str(r.get("ClassifiedPosition", 99))))
                        except:
                            pos = 99
                        meta = meta_map.get(drv, {})
                        rows.append(
                            {
                                "pos": pos,
                                "drv": drv,
                                "first": meta.get("first", ""),
                                "last": meta.get("last", drv),
                                "team": meta.get("team", "–"),
                                "color": meta.get("color", "#AAAAAA"),
                                "grid": None,
                                "gap": "–",
                                "status": "",
                                "q1": format_laptime(r.get("Q1")),
                                "q2": format_laptime(r.get("Q2")),
                                "q3": format_laptime(r.get("Q3")),
                            }
                        )

        store["results"] = sorted(rows, key=lambda x: x.get("pos", 99))
    except Exception as e:
        print(f"[results] {e}")
        store["results"] = []

    # Laps ( no telemetry)
    try:
        laps = session.laps.copy()
        laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
        laps["Compound"] = laps["Compound"].fillna("UNKNOWN").str.upper()
        laps["TyreLife"] = laps["TyreLife"].fillna(0).astype(int)
        laps["Stint"] = laps["Stint"].fillna(0).astype(int)

        time_cols = [
            "Sector1Time",
            "Sector2Time",
            "Sector3Time",
            "PitInTime",
            "PitOutTime",
        ]
        for col in time_cols:
            if col in laps.columns:
                laps[col + "Sec"] = laps[col].apply(timedelta_to_seconds)

        keep = [
            "Driver",
            "Team",
            "LapNumber",
            "LapTimeSec",
            "Compound",
            "TyreLife",
            "Stint",
            "Position",
        ] + [c + "Sec" for c in time_cols if c in laps.columns]
        keep = [c for c in keep if c in laps.columns]

        float_cols = [c for c in keep if "Sec" in c or c == "LapTimeSec"]
        laps[float_cols] = laps[float_cols].round(3)
        store["laps"] = laps[keep].where(pd.notna(laps[keep]), None).to_dict("records")
    except Exception:
        store["laps"] = []

    # Driver list ordered by position
    try:
        drv_list, seen = [], set()
        for r in store.get("results", []):
            drv = r["drv"]
            if drv not in seen:
                seen.add(drv)
                drv_list.append(
                    {
                        "drv": drv,
                        "color": r["color"],
                        "team": r["team"],
                        "pos": r["pos"],
                        "first": r["first"],
                        "last": r["last"],
                    }
                )
        # Add drivers in laps but not results
        lap_drvs = {l["Driver"] for l in store["laps"]}
        for drv in sorted(lap_drvs - seen):
            meta = get_driver_meta(session, drv)
            drv_list.append(
                {
                    "drv": drv,
                    "color": meta["color"],
                    "team": meta["team"],
                    "pos": 99,
                    "first": meta["first"],
                    "last": meta["last"],
                }
            )
        store["drivers"] = drv_list
    except Exception:
        store["drivers"] = []

    # Compounds used per driver
    try:
        cmap = {}
        for l in store["laps"]:
            cmap.setdefault(l["Driver"], set()).add(l.get("Compound", "UNKNOWN"))
        store["compounds"] = {d: list(v) for d, v in cmap.items()}
    except Exception:
        store["compounds"] = {}

    # Race control safety
    try:
        rc = _retry(lambda: session.race_control_messages, retries=2, fallback=None)
        sc = vsc = 0
        if rc is not None and not rc.empty:
            sc = len(rc[rc["Message"].str.contains("SAFETY CAR DEPLOYED", na=False)])
            vsc = len(
                rc[rc["Message"].str.contains("VIRTUAL SAFETY CAR DEPLOYED", na=False)]
            )
        store["race_control"] = {"sc": sc, "vsc": vsc}
    except Exception:
        store["race_control"] = {"sc": 0, "vsc": 0}

    # Fastest lap
    try:
        fl = _retry(lambda: session.laps.pick_fastest(), retries=2, fallback=None)
        store["fastest_lap"] = {
            "driver": str(fl["Driver"]) if fl is not None else "–",
            "time": format_laptime(fl["LapTime"]) if fl is not None else "–",
        }
    except Exception:
        store["fastest_lap"] = {"driver": "–", "time": "–"}

    return store
