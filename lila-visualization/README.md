# LILA BLACK – Player Journey Visualization Tool

A web-based tool for Level Designers to explore player behaviour across LILA BLACK's three maps using 5 days of production telemetry data.

**Live deployment:** [https://lilavisualization.streamlit.app/](https://lilavisualization.streamlit.app/)

---

## Features

| Feature | Description |
|---|---|
| 🗺️ **Player Journeys** | Movement paths and event markers overlaid on the correct minimap |
| 🔥 **Heatmaps** | Kill zones, death zones, loot hot spots, and traffic density |
| ⏱️ **Timeline Playback** | Slider to watch a match unfold event by event |
| 📊 **Stats** | Event distribution, daily trends, top killers |
| 🔍 **Filters** | By map, date, match, player type (human/bot), event type |
| 👤 **Human vs Bot** | Visually distinct — blue paths for humans, gray for bots |

---

## Tech Stack

- **[Streamlit](https://streamlit.io)** — app framework
- **[Plotly](https://plotly.com/python/)** — interactive charts and minimap overlays
- **[Pandas](https://pandas.pydata.org) + [PyArrow](https://arrow.apache.org/docs/python/)** — data loading from Parquet
- **[Pillow](https://python-pillow.org)** — minimap image encoding

---

## Setup

### Prerequisites

- Python 3.11+
- The `player_data/` folder (with one or more date subfolders and `minimaps/`) must be present as a sibling of this `lila-visualization/` folder. Date folders are discovered automatically — no code changes needed when new days are added.

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run locally

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Project Structure

```
lila-visualization/
├── app.py                  ← Streamlit application (UI + charts)
├── data_pipeline.py        ← Parquet loader with Streamlit cache
├── coordinate_utils.py     ← World-to-pixel coordinate conversion
├── requirements.txt
├── README.md               ← This file
├── ARCHITECTURE.md         ← Technical design doc
└── INSIGHTS.md             ← Three data-backed game insights

player_data/                ← Raw data (sibling folder)
├── February_10/ … February_14/   ← .nakama-0 Parquet files
└── minimaps/
    ├── AmbroseValley_Minimap.png
    ├── GrandRift_Minimap.png
    └── Lockdown_Minimap.jpg
```

---

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (include `player_data/` or set the data path via env var).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Set:
   - **Repository:** `<your-github-username>/lila-visualization`
   - **Branch:** `main`
   - **Main file path:** `lila-visualization/app.py`
4. Click **Deploy**. Streamlit Cloud installs requirements automatically.

> **Note:** If the `player_data/` folder exceeds GitHub's 100 MB file limit, store the data in a cloud bucket (S3, GCS) and update `DATA_DIR` in `data_pipeline.py` to pull from there, or pre-process to a single `data/all_events.parquet` file.

---

## Feature Walkthrough

### Sidebar Filters
Every tab is controlled by the sidebar on the left:
- **Map** — switch between AmbroseValley, GrandRift, Lockdown; the minimap image and data update instantly.
- **Date** — narrow to a single day or keep "All" for the full dataset.
- **Player type** — toggle Humans, Bots, or both.
- **Event types** — individually toggle any of the 8 event types (Position, BotPosition, Kill, Killed, BotKill, BotKilled, KilledByStorm, Loot).
- **Show movement paths** — toggle the line trails connecting position events.

### Tab 1 — 🗺️ Player Journeys
- Minimap image rendered as background at full 1024×1024 resolution.
- **Human player paths** in blue lines; **Bot paths** in gray lines.
- All non-movement events (kills, deaths, loot, storm deaths) plotted as distinct *shape + color* markers on top:
  - 🔴 Kill (×), 🟠 Killed (×-open), ⭐ BotKill (yellow star), 💜 BotKilled (purple star), 💠 KilledByStorm (diamond), 🟩 Loot (square)
- Hover any marker to see the event type, player ID, and pixel coordinates.
- Fully interactive: pan, zoom, click-to-isolate via Plotly toolbar.

### Tab 2 — 🔥 Heatmaps
- Four modes selectable via radio button: **Traffic** (all movement), **Kills**, **Deaths**, **Loot**.
- Rendered as a contour density heatmap (Plotly `Histogram2dContour`) overlaid semi-transparently on the minimap.
- Color scales: blue (traffic), red (kills), orange (deaths), green (loot).
- Best used with a single map selected; filter by date or match to compare time periods.

### Tab 3 — ⏱️ Match Timeline / Playback
1. Select a specific **match** from the sidebar.
2. A slider appears showing the match duration in seconds.
3. Drag the slider to scrub through the match — only events up to that timestamp are shown.
4. Movement paths grow as you advance the slider, letting you watch the match unfold spatially.
5. A caption shows how many events are visible at the current time.

### Tab 4 — 📊 Stats
- **Event distribution bar chart** — breakdown of all event types in the current filter.
- **Events per day stacked bar** — volume trend by event type across the 5 days.
- **Top players by kills table** — human-vs-bot kill breakdown per player.
- **Human vs Bot pie chart** — proportion of event rows by player type.

### Header Metrics
Five KPI tiles always show at the top: total events shown, unique players, matches, kills, and loot pickups — all reflecting the current filter state.

---

## Changelog

- **v1.0.0** — Initial release: journey view, heatmaps, timeline, stats, all 5 days of data.
