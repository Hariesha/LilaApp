# ARCHITECTURE.md

## What We Built & Why

### Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend + App | **Streamlit** | Python-only, fast iteration, native data viz, free hosting on Streamlit Community Cloud |
| Data loading | **PyArrow + Pandas** | Native Parquet support, fast columnar reads, familiar API |
| Visualisation | **Plotly** | Interactive scatter/heatmaps that work in Streamlit; supports image overlays via `add_layout_image` |
| Image handling | **Pillow** | Encode minimap PNGs to base64 data URIs for Plotly embedding |
| Hosting | **Streamlit Community Cloud** | Free, git-connected, no Docker needed |

---

## Data Flow

```
player_data/{day}/*.nakama-0   (Apache Parquet)
          │
          ▼
data_pipeline.py :: load_all_data()
  - Read each parquet file with pyarrow
  - Decode event bytes → str
  - Tag date (from folder name)
  - Detect bot vs human (numeric user_id = bot)
  - Concatenate all frames → single DataFrame (~89,000 rows)
  - Cache with @st.cache_data (loaded once per session)
          │
          ▼
coordinate_utils.py :: add_pixel_coords_vectorized()
  - Apply per-map coordinate formula (vectorized)
  - Add pixel_x, pixel_y columns
          │
          ▼
app.py :: Streamlit UI
  - Sidebar filters (map, date, match, player type, events)
  - Tab 1: Journey view   → make_journey_figure()
  - Tab 2: Heatmap        → make_heatmap_figure()
  - Tab 3: Timeline       → make_timeline_figure()
  - Tab 4: Stats charts
```

---

## Coordinate Mapping — The Tricky Part

Each map has a **scale** (world units per 1024 pixels) and a **world origin** `(origin_x, origin_z)` that corresponds to pixel `(0, 1024)` — i.e., the bottom-left of the minimap image.

### Formula (from README)

```
u = (x  - origin_x) / scale        # 0→1 across the image width
v = (z  - origin_z) / scale        # 0→1 across the image height (world space)

pixel_x =  u        * 1024
pixel_y = (1 - v)   * 1024         # flip: image Y=0 is TOP, but world v=0 is BOTTOM
```

### Map parameters

| Map | scale | origin_x | origin_z |
|---|---|---|---|
| AmbroseValley | 900 | -370 | -473 |
| GrandRift | 581 | -290 | -290 |
| Lockdown | 1000 | -500 | -500 |

### Plotly y-axis flip

Plotly's y-axis defaults to increasing upward. Because our `pixel_y` already encodes the image flip, we invert the Plotly axis:

```python
fig.update_yaxes(range=[1024, 0])   # 0 at top, 1024 at bottom — matches image space
```

The minimap image is placed at `x=0, y=0, sizex=1024, sizey=1024` as a layout image, which with the flipped axis puts it exactly behind the data points.

---

## Assumptions

| Situation | Assumption Made |
|---|---|
| Timestamps look like epoch 1970-01-21 | They represent elapsed match time in ms from game engine epoch, not wall-clock time. Used for relative ordering within a match. |
| `user_id` detection | Users whose filename segment before `_` is pure digits are bots; UUID format = human. |
| `.nakama-0` suffix on `match_id` | Stripped for display, retained internally for grouping. |
| February_14 partial day | Included as-is with no special treatment; metrics naturally reflect fewer events. |
| Out-of-bounds coordinates | Coordinates outside `[0, 1024]` pixel range are plotted; Plotly clips them at the axis boundary. |

---

## Major Tradeoffs

| Decision | Considered | Chose | Why |
|---|---|---|---|
| Data storage | Pre-process to single parquet vs load all files at runtime | Load at runtime + `@st.cache_data` | Keeps repo simpler; cache makes it fast after first load |
| Frontend framework | React + Deck.gl vs Streamlit | Streamlit | Faster to build; Level Designers don't need a SPA |
| Heatmap rendering | Plotly `Histogram2dContour` vs raster overlay on image | `Histogram2dContour` | Interactive, no complex image compositing; renders in-browser |
| Timeline playback | Animated frames vs slider | Slider | More control, less complexity, works well in Streamlit |
| Hosting | Vercel + FastAPI vs Streamlit Cloud | Streamlit Cloud | Zero-config git deploy for Streamlit apps |
