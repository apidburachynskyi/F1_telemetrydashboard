#!/usr/bin/env python
"""
Weekly sync script — downloads completed race/qualifying sessions into
the FastF1 cache, updates races.json, then uploads everything to S3.

Usage:
    python scripts/sync_races.py [--years 2024 2025 2026] [--no-download] [--no-upload]

Kubernetes CronJob runs this every Monday:
  1. Downloads new sessions from F1 API → local cache
  2. Uploads cache to S3 (bucket mascret/f1-dashboard-cache/)
  3. Updates races.json

At pod startup, entrypoint.sh downloads the cache from S3 so the app
starts with all data pre-loaded (no wait for users).
"""
import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path

import fastf1

CACHE_DIR = os.environ.get("FF1_CACHE_DIR", "./cache")
RACES_JSON = Path("data/races.json")
SYNC_YEARS = [2024, 2025, 2026]

S3_ENDPOINT = os.environ.get("AWS_S3_ENDPOINT", "https://minio.lab.sspcloud.fr")
S3_BUCKET = os.environ.get("S3_BUCKET", "mascret")
S3_PREFIX = "f1-dashboard-cache"

fastf1.Cache.enable_cache(CACHE_DIR)


def download_session(year: int, location: str, session_type: str) -> bool:
    try:
        s = fastf1.get_session(year, location, session_type)
        s.load()
        return True
    except Exception as e:
        print(f"  ✗  {year} {location} {session_type}: {e}")
        return False


def upload_cache_to_s3():
    """Upload entire cache directory to S3."""
    try:
        import boto3
    except ImportError:
        print("[S3] boto3 not available, skipping upload.")
        return

    key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not key_id or not secret:
        print(
            "[S3] No credentials found (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY), skipping upload."
        )
        return

    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )

    cache_path = Path(CACHE_DIR)
    files = list(cache_path.rglob("*"))
    files = [f for f in files if f.is_file()]
    print(f"\n[S3] Uploading {len(files)} files to s3://{S3_BUCKET}/{S3_PREFIX}/")

    ok, fail = 0, 0
    for f in files:
        key = f"{S3_PREFIX}/{f.relative_to(cache_path)}"
        try:
            s3.upload_file(str(f), S3_BUCKET, key)
            ok += 1
        except Exception as e:
            print(f"  ✗  {key}: {e}")
            fail += 1

    # Also upload races.json
    if RACES_JSON.exists():
        try:
            s3.upload_file(str(RACES_JSON), S3_BUCKET, f"{S3_PREFIX}/races.json")
            print("  ✓  races.json")
            ok += 1
        except Exception as e:
            print(f"  ✗  races.json: {e}")

    print(f"[S3] Done: {ok} uploaded, {fail} failed.")


def main(years: list[int], download: bool = True, upload: bool = True):
    all_races: dict[str, list] = {}

    if RACES_JSON.exists():
        try:
            existing = json.loads(RACES_JSON.read_text())
        except Exception:
            existing = {}
    else:
        existing = {}

    for year in years:
        print(f"\n── {year} ──")
        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
        except Exception as e:
            print(f"  Could not fetch schedule: {e}")
            all_races[str(year)] = existing.get(str(year), [])
            continue

        today = date.today()
        year_races = []
        for _, row in schedule.iterrows():
            event_date = row["EventDate"].date()
            location = row["Location"]
            done = event_date <= today - timedelta(days=1)
            status = "✓" if done else "·"
            print(f"  {status}  {event_date}  {location}")
            year_races.append({"name": location, "date": str(event_date)})

            if done and download:
                for stype in ("R", "Q"):
                    ok = download_session(year, location, stype)
                    if ok:
                        print(f"       cached {stype}")

        all_races[str(year)] = year_races

    RACES_JSON.write_text(json.dumps(all_races, ensure_ascii=False, indent=2))
    total = sum(len(v) for v in all_races.values())
    print(f"\nWrote {RACES_JSON} ({total} races total)")

    if upload:
        upload_cache_to_s3()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=SYNC_YEARS,
        help="Years to sync (default: 2024 2025 2026)",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Only update races.json, skip session downloads",
    )
    parser.add_argument("--no-upload", action="store_true", help="Skip S3 upload")
    args = parser.parse_args()
    main(args.years, download=not args.no_download, upload=not args.no_upload)
