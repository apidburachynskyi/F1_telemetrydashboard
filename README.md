**Live site:** https://f1-dashboard.user.lab.sspcloud.fr/

# F1 Telemetry Dashboard

An interactive Formula 1 analytics dashboard built with Dash, FastF1, and Plotly, deployed on SSP Cloud via ArgoCD.

The goal of this project is to make Formula 1 telemetry data accessible and understandable, without requiring users to work directly with APIs or raw datasets.

---

## Running Locally

```bash
pip install -r requirements.txt
python app.py
```

Open in browser: http://localhost:8050

---

## Project Idea

Modern Formula 1 generates large amounts of telemetry data: speed, throttle, braking, position, tyre usage, and more. While part of this data is publicly available through tools like FastF1, it is not easy to explore or interpret for most users.

This project aims to solve that by providing a complete dashboard that transforms raw data into visual insights, built around questions that naturally arise when watching a race:

- How do drivers approach corners?
- Where do they brake or accelerate?
- How much do tyres affect performance?
- How consistent are drivers during a race?
- What role do pit stops play?

---

## Features

### Overview
- Race results and classification
- Weather conditions
- Fastest lap & safety car information

### Qualifying
- Q1 / Q2 / Q3 results tables
- Visual lap time comparison

### Race Replay
- 2D animated replay using positional data
- Adjustable playback speed (0.5× to 4×)

### Corner Analysis
- Driver racing lines using GPS data
- Telemetry comparison (speed, throttle, braking)
- Entry / apex / exit speed metrics

### Lap Analysis
- Sector time comparison with best sector highlighting
- Detailed telemetry (speed, throttle, brake, gear, RPM)

### Race Progression
- Lap time evolution and position changes
- Consistency and distribution analysis

### Tyre Analysis
- Stint breakdown and degradation estimation
- Lap time evolution per compound and tyre age

### Pit Stops
- Pit stop timeline and team performance comparison
- Average, best, and worst stop durations

### Championship
- Driver and constructor standings
- Season calendar with race results

---

## Architecture

```
S3 (MinIO SSP Cloud)
    │
    ▼ pod startup (entrypoint.sh)
FastF1 cache (./cache/)
    │
    ▼ user clicks Load
session_to_store() → dcc.Store → Dash callbacks → Charts
```

### Data Pipeline

1. **Sync** — `scripts/sync_races.py` downloads F1 sessions from the FastF1 API and uploads them to S3 (`mascret/f1-dashboard-cache/`). Currently run manually from VSCode SSP Cloud after each race weekend. The goal is to automate this via a Kubernetes CronJob (every Monday), but SSP Cloud namespace permissions currently prevent creating the required `s3-credentials` secret.

2. **Pod startup** — `entrypoint.sh` downloads the S3 cache in the background before gunicorn starts, so data is ready immediately for users.

3. **On demand** — when a user selects a session, `session_to_store()` loads from the local cache (fast) and serializes it to JSON for the Dash store.

4. **Race calendar** — `data/races.json` lists all GPs with dates for 2024/2025/2026. Future races are shown but disabled in the dropdown. Updated by `sync_races.py`.

### Monitoring

A hidden page at `/monitoring` (HTTP Basic Auth) shows tab render times, RAM, and CPU usage.

- URL: `https://f1-dashboard.user.lab.sspcloud.fr/monitoring`
- Login: `admin` / `f1admin2026`

---

## Project Structure

```
f1-dashboard/
│
├── app.py                  # Main Dash application + callbacks
├── entrypoint.sh           # Pod startup: S3 download + gunicorn
├── Dockerfile
├── requirements.txt
│
├── data/
│   └── races.json          # Race calendar with dates (2024–2026)
│
├── scripts/
│   └── sync_races.py       # Manual sync: download F1 data + upload S3
│
├── assets/                 # Static files (CSS, logos)
│
├── components/
│   ├── shared.py           # Shared constants, data loading, formatting
│   ├── sidebar.py          # Session selector + driver checklist
│   ├── perf_metrics.py     # Tab render timing (Prometheus + monitoring)
│   ├── results_loader.py   # Race/quali results from Jolpica API
│   └── charts/             # Visualization modules
│       ├── lap_time.py
│       ├── tyre_deg.py
│       ├── position_flow.py
│       ├── racing_line.py
│       ├── telemetry.py
│       └── pit_stops.py
│
├── pages/                  # One file per dashboard tab
│   ├── overview.py
│   ├── qualifying.py
│   ├── race_replay.py
│   ├── corner_analysis.py
│   ├── lap_analysis.py
│   ├── race_progression.py
│   ├── tyre_analysis.py
│   ├── pit_stops.py
│   └── championship.py
│
└── k8s/                    # Kubernetes manifests (ArgoCD)
    ├── deployment.yaml
    ├── service.yaml
    └── ingress.yaml
```
