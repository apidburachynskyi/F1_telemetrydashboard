# F1 Telemetry Dashboard

![Python](https://img.shields.io/badge/python-3.11-blue)
![Dash](https://img.shields.io/badge/Dash-dashboard-0b7285)
![FastF1](https://img.shields.io/badge/FastF1-telemetry-e10600)
![Plotly](https://img.shields.io/badge/Plotly-visualization-3f4f75)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)
![ArgoCD](https://img.shields.io/badge/ArgoCD-deployed-orange)

- **Primary deployment (SSP Cloud):** [https://f1-dashboard.user.lab.sspcloud.fr/](https://f1-dashboard.user.lab.sspcloud.fr/)
- **Alternative deployment (Railway):** [https://www.f1telemetry.live/](https://www.f1telemetry.live/)

An interactive Formula 1 analytics dashboard built with **Dash**, **FastF1**, and **Plotly**, deployed on **SSP Cloud** via **ArgoCD**.

This project transforms raw F1 telemetry and race data into an accessible visual interface, allowing users to explore race performance, qualifying sessions, tyre behaviour, lap consistency, pit stop strategy, and championship standings without working directly with APIs or raw datasets.

---

## Overview

Modern Formula 1 generates large volumes of data: speed, throttle, braking, GPS position, lap times, tyre usage, weather conditions, and more. While part of this information is publicly available through tools such as **FastF1**, it is not straightforward to inspect or interpret in a useful way.

This dashboard was built to bridge that gap. It provides an interactive environment for answering questions such as:

- How do drivers approach specific corners?
- Where do they brake, accelerate, or gain time?
- How do tyre compounds and stint length affect performance?
- How consistent are drivers during a race?
- What impact do pit stops have on race progression?

---

## Main Features

### Overview
- Race classification and results
- Weather conditions
- Fastest lap and safety car information

### Qualifying
- Q1 / Q2 / Q3 results tables
- Visual lap time comparison

### Race Replay
- 2D animated replay using positional data
- Adjustable playback speed from **0.5× to 4×**

### Corner Analysis
- Driver racing lines using GPS data
- Telemetry comparison across drivers
- Entry, apex, and exit speed metrics

### Lap Analysis
- Sector time comparison with best-sector highlighting
- Detailed telemetry including speed, throttle, brake, gear, and RPM

### Race Progression
- Lap time evolution
- Position changes during the race
- Consistency and distribution analysis

### Tyre Analysis
- Stint breakdown and degradation estimation
- Lap time evolution by compound and tyre age

### Pit Stops
- Pit stop timeline
- Team performance comparison
- Average, best, and worst stop durations

### Championship
- Driver standings
- Constructor standings
- Season calendar and race results

---

## Running Locally



Clone the repository and start the dashboard locally.

### 1. Clone the project

```bash
git clone https://github.com/apidburachynskyi/F1_telemetrydashboard.git
cd F1_telemetrydashboard
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

### 5. Open the dashboard

Visit `http://localhost:8050`

---


## Notes

- The app uses a local cache directory at `./cache/`
- The first session load may take longer if data is not cached yet
- Some features depend on available FastF1 session data
---
## Architecture

The application follows this flow:

- **S3 (MinIO SSP Cloud)** stores the FastF1 cache
- On **pod startup**, `entrypoint.sh` downloads cached data
- The app uses the local **FastF1 cache** in `./cache/`
- When the user clicks **Load**, `session_to_store()` prepares the session data
- The data is passed into `dcc.Store` and then consumed by Dash callbacks to render charts

The application is built around a simple idea: keep heavy race and session data close to the app through caching, then expose a lightweight interactive layer in Dash.

### Data Flow

1. **Sync**  
   `scripts/sync_races.py` downloads Formula 1 sessions through the FastF1 API and uploads the cache to S3 at `mascret/f1-dashboard-cache/`.  
   At the moment, this process is launched manually from VS Code on SSP Cloud after each race weekend.

2. **Startup**  
   On pod startup, `entrypoint.sh` downloads the cached data from S3 so that common sessions are already available when users access the dashboard.

3. **Session Load**  
   When the user selects a race, `session_to_store()` loads the relevant session from local cache and serializes it into a format used by Dash callbacks.

4. **Interactive Rendering**  
   The serialized session data is stored in `dcc.Store`, then consumed by the different analytics pages to generate charts and views dynamically.

5. **Race Calendar**  
   `data/races.json` stores the GP calendar for **2024**, **2025**, and **2026**. Future races are displayed in the interface but disabled until data becomes available.

### Planned Improvement

The next step is to automate race cache synchronization through a **Kubernetes CronJob** running every Monday after a race weekend.

At the moment, SSP Cloud namespace permissions prevent creation of the required `s3-credentials` secret, so this automation is not yet enabled.

---

## Monitoring

The application includes a hidden monitoring page protected with HTTP Basic Auth.

It displays:

- tab render times
- RAM usage
- CPU usage

**Monitoring URL:** [https://f1-dashboard.user.lab.sspcloud.fr/monitoring](https://f1-dashboard.user.lab.sspcloud.fr/monitoring)

- Login: `admin`
- Password: `f1admin2026`

---

## Project Structure

```text
## Project Structure

```text
f1-dashboard/
│
├── app.py                  # Main Dash app: app/server setup, Flask routes, cache, callbacks
├── entrypoint.sh           # Container startup: optional cache warmup + gunicorn
├── Dockerfile              # Container image definition
├── requirements.txt        # Python dependencies
│
├── data/
│   └── races.json          # Race calendar with dates
│
├── scripts/
│   └── sync_races.py       # Manual sync/update helper for race data / cache
│
├── assets/                 # Static files (CSS, logos, images)
│
├── views/                  # High-level UI builders extracted from app.py
│   ├── championship.py     # Championship page wrapper
│   ├── landing.py          # Landing page view
│   ├── root_layout.py      # Global app layout and dcc.Store setup
│   └── telemetry.py        # Telemetry dashboard shell + tab definitions
│
├── pages/                  # One file per analysis page/tab
│   ├── __init__.py
│   ├── championship.py
│   ├── corner_analysis.py
│   ├── lap_analysis.py
│   ├── overview.py
│   ├── pit_stops.py
│   ├── qualifying.py
│   ├── race_progression.py
│   ├── race_replay.py
│   └── tyre_analysis.py
│
├── components/
│   ├── __init__.py
│   ├── monitoring.py       # Monitoring route helpers and HTML rendering
│   ├── perf_metrics.py     # Tab render timing / monitoring helpers
│   ├── sidebar.py          # Session selector + driver checklist UI
│   │
│   ├── charts/             # Visualization modules
│   │   ├── __init__.py
│   │   ├── lap_time.py
│   │   ├── pit_stops.py
│   │   ├── position_flow.py
│   │   ├── race_replay.py
│   │   ├── racing_line.py
│   │   ├── telemetry.py
│   │   └── tyre_deg.py
│   │
│   ├── core/               # Core constants, formatting, theme, and session logic
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── formatting.py
│   │   ├── sessions.py
│   │   └── theme.py
│   │
│   ├── data/               # Data loading / external API helpers
│   │   ├── __init__.py
│   │   ├── jolpica.py
│   │   ├── results_loader.py
│   │   └── session_loader.py
│   │
│   └── ui/                 # Shared UI and chart styling helpers
│       ├── __init__.py
│       ├── hidden_ids.py
│       ├── plot_theme.py
│       └── primitives.py
│
└── k8s/                    # Kubernetes manifests for deployment
    ├── deployment.yaml
    ├── ingress.yaml
    └── service.yaml
```
```
