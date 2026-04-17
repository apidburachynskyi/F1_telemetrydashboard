import requests
import pandas as pd
import math
from components.shared import format_laptime, safe_str

JOLPICA = "https://api.jolpi.ca/ergast/f1"


def _get(url, timeout=8):
    """GET request to JolpicaReturns None on failure."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        print(f"[Jolpica] {url} → {e}")
        return None


def get_round_number(year, gp_name):
    """Find the round number for a GP name in a given yea"""
    data = _get(f"{JOLPICA}/{year}.json")
    if not data:
        return None
    try:
        races = data["MRData"]["RaceTable"]["Races"]
        gp_lower = gp_name.lower()
        for race in races:
            if (gp_lower in race["raceName"].lower() or
                gp_lower in race["Circuit"].get("Location",{}).get("country","").lower() or
                gp_lower in race["Circuit"].get("circuitName","").lower()):
                return int(race["round"])
        # Try partial match on circuit location
        for race in races:
            loc = race["Circuit"].get("Location",{})
            if (gp_lower in loc.get("locality","").lower() or
                gp_lower in loc.get("country","").lower()):
                return int(race["round"])
    except Exception:
        pass
    return None


def fetch_race_results(year, gp_name):
    """
    
    Fetch race results from Jolpica.
    Returns list of dicts with: pos, drv, first, last, team, grid, gap, status
    Returns None if unavailable
    """
    round_num = get_round_number(year, gp_name)
    if not round_num:
        return None

    data = _get(f"{JOLPICA}/{year}/{round_num}/results.json")
    if not data:
        return None

    try:
        race_results = data["MRData"]["RaceTable"]["Races"][0]["Results"]
    except (KeyError, IndexError):
        return None

    rows = []
    for r in race_results:
        drv  = r["Driver"]
        code = drv.get("code", drv.get("driverId","???").upper()[:3])

        # Gap to leader
        pos = int(r.get("position", 99))
        if pos == 1:
            gap = "–"
        else:
            time_info = r.get("Time", {})
            millis = time_info.get("millis")
            t_str  = time_info.get("time")
            if t_str:
                gap = f"+{t_str}"
            elif millis:
                s = int(millis) / 1000
                m = int(s // 60)
                gap = f"+{m}:{s%60:06.3f}" if m > 0 else f"+{s:.3f}s"
            else:
                gap = r.get("status", "–")  # DNF / Retired / +1 Lap etc.

        rows.append({
            "pos":    pos,
            "drv":    code,
            "first":  drv.get("givenName",""),
            "last":   drv.get("familyName", code),
            "team":   r.get("Constructor",{}).get("name","–"),
            "grid":   int(r.get("grid", 0)) or None,
            "gap":    gap,
            "status": r.get("status",""),
        })

    return sorted(rows, key=lambda x: x["pos"])


def fetch_quali_results(year, gp_name):
    """
    Fetch qualifying results from Jolpica.
    Returns list of dicts with: pos, drv, first, last, team, q1, q2, q3
    """
    round_num = get_round_number(year, gp_name)
    if not round_num:
        return None

    data = _get(f"{JOLPICA}/{year}/{round_num}/qualifying.json")
    if not data:
        return None

    try:
        quali = data["MRData"]["RaceTable"]["Races"][0]["QualifyingResults"]
    except (KeyError, IndexError):
        return None

    rows = []
    for r in quali:
        drv  = r["Driver"]
        code = drv.get("code", drv.get("driverId","???").upper()[:3])
        rows.append({
            "pos":   int(r.get("position", 99)),
            "drv":   code,
            "first": drv.get("givenName",""),
            "last":  drv.get("familyName", code),
            "team":  r.get("Constructor",{}).get("name","–"),
            "q1":    r.get("Q1","–") or "–",
            "q2":    r.get("Q2","–") or "–",
            "q3":    r.get("Q3","–") or "–",
        })

    return sorted(rows, key=lambda x: x["pos"])


def build_results_from_laps(session, meta_map):
    """
    Fallback: build race results from FastF1 laps data.
    Less accurate gap but always works.
    """
    laps = session.laps.copy()
    if laps.empty:
        return []

    final_pos = {}
    grid_pos  = {}
    cum_times = {}

    for drv, grp in laps.groupby("Driver"):
        grp_s = grp.sort_values("LapNumber")
        last  = grp_s[grp_s["Position"].notna()]["Position"]
        if not last.empty:
            final_pos[drv] = int(last.iloc[-1])
        lap1 = grp_s[grp_s["LapNumber"] == 1]
        if not lap1.empty and pd.notna(lap1.iloc[0].get("Position")):
            grid_pos[drv] = int(lap1.iloc[0]["Position"])
        valid = grp_s[grp_s["LapTime"].notna()]
        if not valid.empty:
            cum_times[drv] = valid["LapTime"].dt.total_seconds().sum()

    leader = min(final_pos, key=lambda d: final_pos.get(d,99)) if final_pos else None
    leader_t = cum_times.get(leader, 0)

    rows = []
    for drv in sorted(final_pos, key=lambda d: final_pos[d]):
        pos  = final_pos[drv]
        meta = meta_map.get(drv, {"color":"#AAAAAA","first":"","last":drv,
                                    "team":"–","status":""})
        if pos == 1 or drv == leader:
            gap = "–"
        elif drv in cum_times and leader_t > 0:
            diff = cum_times[drv] - leader_t
            gap  = f"+{diff:.3f}s" if diff > 0 else "–"
        else:
            gap = "–"

        rows.append({
            "pos":    pos,
            "drv":    drv,
            "first":  meta["first"],
            "last":   meta["last"],
            "team":   meta["team"],
            "color":  meta.get("color","#AAAAAA"),
            "grid":   grid_pos.get(drv),
            "gap":    gap,
            "status": meta.get("status",""),
            "q1":"–","q2":"–","q3":"–",
        })

    return rows
