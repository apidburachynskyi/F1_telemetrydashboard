"""
preload.py
===========
Run this once to pre-download FastF1 session data into the local cache.

    python preload.py

Data is saved to ./cache (or FF1_CACHE_DIR if set).
Run time: ~10-20 minutes on first run.
Subsequent runs skip already-cached sessions instantly.
"""

import fastf1
import os
from pathlib import Path

CACHE_DIR = os.environ.get("FF1_CACHE_DIR", "./cache")
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

SESSIONS = [
    # 2025
    (2025, "Bahrain",      "R"), (2025, "Bahrain",      "Q"),
    (2025, "Saudi Arabia", "R"), (2025, "Saudi Arabia", "Q"),
    (2025, "Australia",    "R"), (2025, "Australia",    "Q"),
    (2025, "Monaco",       "R"), (2025, "Monaco",       "Q"),
    (2025, "Silverstone",  "R"), (2025, "Silverstone",  "Q"),
    # 2024
    (2024, "Bahrain",      "R"), (2024, "Bahrain",      "Q"),
    (2024, "Monaco",       "R"), (2024, "Monaco",       "Q"),
    (2024, "Silverstone",  "R"), (2024, "Silverstone",  "Q"),
    (2024, "Monza",        "R"), (2024, "Monza",        "Q"),
    (2024, "Abu Dhabi",    "R"), (2024, "Abu Dhabi",    "Q"),
]

total   = len(SESSIONS)
success = 0
failed  = []

print(f"Pre-loading {total} sessions into {CACHE_DIR}\n")

for i, (year, gp, stype) in enumerate(SESSIONS, 1):
    label = f"{year} {gp} {stype}"
    print(f"[{i:02d}/{total}] {label}", end=" ... ", flush=True)
    try:
        s = fastf1.get_session(year, gp, stype)
        s.load()
        success += 1
        print("✓")
    except Exception as e:
        failed.append(label)
        print(f"✗  {e}")

print(f"\nDone: {success}/{total} sessions loaded.")
if failed:
    print("Failed:")
    for f in failed:
        print(f"  - {f}")
