# F1 Telemetry Dashboard

An interactive Formula 1 analytics dashboard built with Dash, FastF1, and Plotly.

The goal of this project is to make Formula 1 telemetry data accessible and understandable, without requiring users to work directly with APIs or raw datasets.

---

## Project Idea

Modern Formula 1 generates large amounts of telemetry data: speed, throttle, braking, position, tyre usage, and more. While part of this data is publicly available through tools like FastF1, it is not easy to explore or interpret for most users.

This project aims to solve that by providing a complete dashboard that transforms raw data into visual insights.

Instead of organizing the interface around data structures, the dashboard is built around questions that naturally arise when watching a race, such as:

- How do drivers approach corners?
- Where do they brake or accelerate?
- How much do tyres affect performance?
- How consistent are drivers during a race?
- What role do pit stops play?

Each section of the dashboard is designed to answer one of these questions.

---

## Features

After loading a session, the dashboard provides multiple analysis modules:

### Overview
- Race results and classification  
- Weather conditions  
- Fastest lap  
- Safety car information  

### Qualifying
- Q1 / Q2 / Q3 results tables  
- Visual comparison of lap times  

### Race Replay
- 2D animated replay using positional data  
- Based on cumulative race time for realistic progression  

### Corner Analysis
- Driver racing lines using GPS data  
- Telemetry comparison (speed, throttle, braking)  
- Entry / apex / exit speed metrics  

### Lap Analysis
- Sector time comparison  
- Best sector highlighting  
- Detailed telemetry (speed, throttle, brake, gear, RPM)  

### Race Progression
- Lap time evolution  
- Position changes  
- Consistency and distribution analysis  

### Tyre Analysis
- Stint breakdown  
- Tyre degradation estimation  
- Lap time evolution with compound and tyre age  

### Pit Stops
- Pit stop timeline  
- Team performance comparison  
- Average, best, and worst stop durations  

### Championship
- Driver standings  
- Constructor standings  
- Season calendar with race results  

---

## How It Works

The dashboard relies on a combination of data retrieval, processing, and visualization:

1. **Data Loading**
   - Sessions are loaded using FastF1
   - Race and qualifying data are fetched automatically

2. **Processing**
   - Telemetry data is cleaned and structured
   - Derived metrics (sector times, degradation, etc.) are computed

3. **Caching**
   - Data is cached locally after first load (`./cache`)
   - Subsequent loads are significantly faster

4. **Visualization**
   - Dash callbacks update visual components dynamically
   - Plotly is used for interactive charts

---

## Running the Application

### Requirements

- Python 3.11+

---

### Run Locally

Install dependencies:

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python app.py
```


Open in browser :

http://localhost:8050