"""
End-to-End Test Suite for LILA BLACK Player Journey Visualization
=================================================================
Tests every layer: coordinate math, data pipeline, figure builders,
sidebar logic, and Streamlit AppTest rendering.
"""

import os
import sys
import math
import traceback

import numpy as np
import pandas as pd

# Ensure the lila-visualization dir is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coordinate_utils import (
    world_to_pixel,
    add_pixel_coords,
    add_pixel_coords_vectorized,
    MAP_CONFIG,
    IMAGE_SIZE,
)
from data_pipeline import load_all_data, _is_bot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = 0
FAIL = 0
WARN = 0
results = []


def report(name, passed, detail=""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    results.append((status, name, detail))
    mark = "✅" if passed else "❌"
    print(f"  {mark} {name}" + (f"  — {detail}" if detail else ""))


def warn(name, detail=""):
    global WARN
    WARN += 1
    results.append(("WARN", name, detail))
    print(f"  ⚠️  {name}" + (f"  — {detail}" if detail else ""))


# ===========================================================================
# 1. COORDINATE UTILITIES
# ===========================================================================
print("\n" + "=" * 70)
print("1. COORDINATE UTILITIES")
print("=" * 70)


# 1a. Origin mapping — bottom‐left of the image should be pixel (0, 1024)
print("\n--- 1a. Origin → (0, 1024) mapping ---")
for map_id, cfg in MAP_CONFIG.items():
    px, py = world_to_pixel(cfg["origin_x"], cfg["origin_z"], map_id)
    ok = abs(px) < 0.01 and abs(py - IMAGE_SIZE) < 0.01
    report(
        f"{map_id}: origin → (0, 1024)",
        ok,
        f"got ({px:.4f}, {py:.4f})",
    )


# 1b. Top-right corner — world coords that map to (1024, 0)
print("\n--- 1b. Top‐right corner → (1024, 0) ---")
for map_id, cfg in MAP_CONFIG.items():
    x_tr = cfg["origin_x"] + cfg["scale"]
    z_tr = cfg["origin_z"] + cfg["scale"]
    px, py = world_to_pixel(x_tr, z_tr, map_id)
    ok = abs(px - IMAGE_SIZE) < 0.01 and abs(py) < 0.01
    report(
        f"{map_id}: top-right → (1024, 0)",
        ok,
        f"got ({px:.4f}, {py:.4f})",
    )


# 1c. Centre mapping — should be (512, 512)
print("\n--- 1c. Centre → (512, 512) ---")
for map_id, cfg in MAP_CONFIG.items():
    xc = cfg["origin_x"] + cfg["scale"] / 2
    zc = cfg["origin_z"] + cfg["scale"] / 2
    px, py = world_to_pixel(xc, zc, map_id)
    ok = abs(px - 512) < 0.01 and abs(py - 512) < 0.01
    report(
        f"{map_id}: centre → (512, 512)",
        ok,
        f"got ({px:.4f}, {py:.4f})",
    )


# 1d. Vectorized vs row-wise consistency
print("\n--- 1d. Vectorized vs row‐wise consistency ---")
test_data = []
for map_id, cfg in MAP_CONFIG.items():
    for _ in range(50):
        x = cfg["origin_x"] + np.random.rand() * cfg["scale"]
        z = cfg["origin_z"] + np.random.rand() * cfg["scale"]
        test_data.append({"x": x, "z": z, "map_id": map_id})

test_df = pd.DataFrame(test_data)
df_row = add_pixel_coords(test_df)
df_vec = add_pixel_coords_vectorized(test_df)

max_diff_x = (df_row["pixel_x"] - df_vec["pixel_x"]).abs().max()
max_diff_y = (df_row["pixel_y"] - df_vec["pixel_y"]).abs().max()
ok = max_diff_x < 1e-10 and max_diff_y < 1e-10
report(
    "Row‐wise vs vectorized match (150 random pts)",
    ok,
    f"max Δx={max_diff_x:.2e}, max Δy={max_diff_y:.2e}",
)


# 1e. Pixel bounds — random world coords within map extents → pixels inside [0, 1024]
print("\n--- 1e. Pixel output within [0, 1024] ---")
ok = (
    df_vec["pixel_x"].between(0, IMAGE_SIZE).all()
    and df_vec["pixel_y"].between(0, IMAGE_SIZE).all()
)
report("All random in‐bounds coords → pixels in [0, 1024]", ok)


# ===========================================================================
# 2. DATA PIPELINE
# ===========================================================================
print("\n" + "=" * 70)
print("2. DATA PIPELINE")
print("=" * 70)

# 2a. Bot detection
print("\n--- 2a. Bot / human detection ---")
report("UUID is Human", not _is_bot("0019c582-574d-4a53-9f77-554519b75b4c"))
report("Numeric is Bot", _is_bot("12345"))
report("Short numeric is Bot", _is_bot("7"))
report("Mixed is Bot (not UUID4)", _is_bot("abc123"))

# 2b. Load all data
print("\n--- 2b. Load all data ---")
try:
    df = load_all_data()
    report("load_all_data() succeeds", True, f"{len(df):,} rows")
except Exception as e:
    df = None
    report("load_all_data() succeeds", False, str(e))

if df is not None:

    # 2c. Required columns
    print("\n--- 2c. Required columns present ---")
    required_cols = [
        "event", "user_id", "match_id", "map_id",
        "x", "z", "ts",
        "date", "is_bot", "player_type",
        "pixel_x", "pixel_y", "match_id_clean",
    ]
    for col in required_cols:
        report(f"Column '{col}' exists", col in df.columns)

    # 2d. No nulls in critical columns
    print("\n--- 2d. Null check on critical columns ---")
    critical = ["event", "user_id", "match_id", "map_id", "pixel_x", "pixel_y"]
    for col in critical:
        nulls = int(df[col].isna().sum())
        report(f"No nulls in '{col}'", nulls == 0, f"{nulls} nulls" if nulls else "")

    # 2e. event column is str not bytes
    print("\n--- 2e. Event dtype is string ---")
    sample_types = df["event"].apply(type).unique()
    ok = all(t == str for t in sample_types)
    report("All event values are str", ok, f"types found: {sample_types}")

    # 2f. Known map IDs only
    print("\n--- 2f. Map IDs ---")
    known_maps = set(MAP_CONFIG.keys())
    actual_maps = set(df["map_id"].unique())
    report(
        "All map_id values are known",
        actual_maps.issubset(known_maps),
        f"actual={actual_maps}, known={known_maps}",
    )

    # 2g. Dates
    print("\n--- 2g. Date values ---")
    expected_dates = {"February_10", "February_11", "February_12", "February_13", "February_14"}
    actual_dates = set(df["date"].unique())
    report(
        "Expected dates present",
        actual_dates == expected_dates or actual_dates.issubset(expected_dates),
        f"found {actual_dates}",
    )

    # 2h. player_type only Human/Bot
    print("\n--- 2h. Player type values ---")
    ptypes = set(df["player_type"].unique())
    report("player_type ⊆ {Human, Bot}", ptypes.issubset({"Human", "Bot"}), str(ptypes))

    # 2i. match_id_clean has no .nakama-0
    print("\n--- 2i. match_id_clean stripped ---")
    has_suffix = df["match_id_clean"].str.contains(r"\.nakama-0", regex=True, na=False).any()
    report("match_id_clean has no '.nakama-0'", not has_suffix)

    # 2j. Sorted by (match_id, ts)
    print("\n--- 2j. Sorted by match_id, ts ---")
    sorted_ok = df.equals(df.sort_values(["match_id", "ts"]).reset_index(drop=True))
    report("DataFrame is sorted by [match_id, ts]", sorted_ok)

    # 2k. Pixel coordinates within reasonable bounds
    print("\n--- 2k. Pixel coordinate range sanity ---")
    px_min, px_max = df["pixel_x"].min(), df["pixel_x"].max()
    py_min, py_max = df["pixel_y"].min(), df["pixel_y"].max()
    # Allow some out-of-bounds (noted in ARCHITECTURE.md) but most should be in range
    in_range_x = df["pixel_x"].between(0, 1024).mean()
    in_range_y = df["pixel_y"].between(0, 1024).mean()
    report(
        "≥95% of pixel_x in [0, 1024]",
        in_range_x >= 0.95,
        f"{in_range_x*100:.1f}% in range, min={px_min:.1f}, max={px_max:.1f}",
    )
    report(
        "≥95% of pixel_y in [0, 1024]",
        in_range_y >= 0.95,
        f"{in_range_y*100:.1f}% in range, min={py_min:.1f}, max={py_max:.1f}",
    )

    # 2l. Row count sanity (~89k per ARCHITECTURE.md)
    print("\n--- 2l. Row count sanity ---")
    report(
        "Row count > 10,000",
        len(df) > 10_000,
        f"{len(df):,} rows",
    )

    # ===========================================================================
    # 3. MINIMAP FILES
    # ===========================================================================
    print("\n" + "=" * 70)
    print("3. MINIMAP FILES")
    print("=" * 70)

    from PIL import Image

    MINIMAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "player_data", "minimaps")
    MINIMAP_FILES = {
        "AmbroseValley": "AmbroseValley_Minimap.png",
        "GrandRift":     "GrandRift_Minimap.png",
        "Lockdown":      "Lockdown_Minimap.jpg",
    }

    for map_id, fname in MINIMAP_FILES.items():
        path = os.path.join(MINIMAP_DIR, fname)
        exists = os.path.isfile(path)
        report(f"Minimap exists: {fname}", exists)
        if exists:
            img = Image.open(path)
            w, h = img.size
            report(
                f"Minimap size: {fname}",
                w == 1024 and h == 1024,
                f"{w}x{h}",
            )

    # ===========================================================================
    # 4. FIGURE BUILDERS (app.py functions)
    # ===========================================================================
    print("\n" + "=" * 70)
    print("4. FIGURE BUILDERS")
    print("=" * 70)

    from app import (
        make_journey_figure,
        make_heatmap_figure,
        make_timeline_figure,
        load_minimap_b64,
        EVENT_COLORS,
        EVENT_SYMBOLS,
        EVENT_SIZES,
    )

    # 4a. load_minimap_b64
    print("\n--- 4a. Minimap base64 encoding ---")
    for map_id in MAP_CONFIG:
        try:
            b64 = load_minimap_b64(map_id)
            ok = b64.startswith("data:image/png;base64,") and len(b64) > 1000
            report(f"load_minimap_b64('{map_id}')", ok, f"length={len(b64)}")
        except Exception as e:
            report(f"load_minimap_b64('{map_id}')", False, str(e))

    # 4b. make_journey_figure  — both with and without paths
    print("\n--- 4b. Journey figure ---")
    sample_map = df["map_id"].iloc[0]
    sample = df[df["map_id"] == sample_map].head(500)
    for show_paths in [True, False]:
        try:
            fig = make_journey_figure(sample, sample_map, show_paths)
            has_data = len(fig.data) > 0
            has_image = len(fig.layout.images) > 0
            y_range = fig.layout.yaxis.range
            y_flipped = y_range is not None and y_range[0] > y_range[1]
            report(
                f"Journey figure (paths={show_paths})",
                has_data and has_image and y_flipped,
                f"traces={len(fig.data)}, images={len(fig.layout.images)}, y_range={y_range}",
            )
        except Exception as e:
            report(f"Journey figure (paths={show_paths})", False, traceback.format_exc())

    # 4c. make_journey_figure with empty DataFrame
    print("\n--- 4c. Journey figure with empty data ---")
    try:
        empty_df = sample.iloc[:0]
        fig = make_journey_figure(empty_df, sample_map, False)
        report("Journey figure with empty df", True, f"traces={len(fig.data)}")
    except Exception as e:
        report("Journey figure with empty df", False, str(e))

    # 4d. make_heatmap_figure for each type
    print("\n--- 4d. Heatmap figures ---")
    for htype in ["traffic", "kills", "deaths", "loot"]:
        try:
            fig = make_heatmap_figure(sample, sample_map, htype)
            has_image = len(fig.layout.images) > 0
            report(f"Heatmap '{htype}'", has_image, f"traces={len(fig.data)}")
        except Exception as e:
            report(f"Heatmap '{htype}'", False, traceback.format_exc())

    # 4e. make_heatmap_figure with empty df
    print("\n--- 4e. Heatmap with empty data ---")
    for htype in ["traffic", "kills", "deaths", "loot"]:
        try:
            fig = make_heatmap_figure(empty_df, sample_map, htype)
            report(f"Heatmap '{htype}' (empty)", True)
        except Exception as e:
            report(f"Heatmap '{htype}' (empty)", False, str(e))

    # 4f. make_timeline_figure
    print("\n--- 4f. Timeline figure ---")
    first_match = df["match_id"].iloc[0]
    match_df = df[df["match_id"] == first_match].copy()
    match_map = match_df["map_id"].iloc[0]
    t_min = match_df["ts"].min()
    t_max = match_df["ts"].max()
    duration_ms = int((t_max - t_min).total_seconds() * 1000)
    try:
        # Full timeline
        fig = make_timeline_figure(match_df, match_map, duration_ms)
        report("Timeline (full)", len(fig.data) > 0, f"traces={len(fig.data)}")
        # Halfway
        fig2 = make_timeline_figure(match_df, match_map, duration_ms // 2)
        report("Timeline (half)", len(fig2.data) >= 0)
        # Zero
        fig0 = make_timeline_figure(match_df, match_map, 0)
        report("Timeline (t=0)", True, f"traces={len(fig0.data)}")
    except Exception as e:
        report("Timeline figure", False, traceback.format_exc())

    # 4g. EVENT_COLORS / EVENT_SYMBOLS / EVENT_SIZES cover all event types
    print("\n--- 4g. Event styling completeness ---")
    all_events = set(df["event"].unique())
    for name, mapping in [("COLORS", EVENT_COLORS), ("SYMBOLS", EVENT_SYMBOLS), ("SIZES", EVENT_SIZES)]:
        missing = all_events - set(mapping.keys())
        report(f"EVENT_{name} covers all events", len(missing) == 0, f"missing={missing}" if missing else "")

    # ===========================================================================
    # 5. STREAMLIT APP RENDERING (AppTest)
    # ===========================================================================
    print("\n" + "=" * 70)
    print("5. STREAMLIT AppTest (simulated UI)")
    print("=" * 70)

    try:
        from streamlit.testing.v1 import AppTest

        print("\n--- 5a. App boots without error ---")
        try:
            at = AppTest.from_file("app.py", default_timeout=120)
            at.run()
            report("App boots without exception", not at.exception, 
                   str(at.exception[0].value) if at.exception else "")
        except Exception as e:
            report("App boots without exception", False, str(e))

        if not at.exception:
            # 5b. Metrics rendered
            print("\n--- 5b. Header metrics ---")
            metrics = at.metric
            report(f"Metrics rendered", len(metrics) >= 5, f"count={len(metrics)}")

            # Check metric labels
            metric_labels = [m.label for m in metrics]
            for expected_label in ["Events shown", "Unique players", "Matches", "Kills", "Loot pickups"]:
                found = expected_label in metric_labels
                report(f"Metric '{expected_label}' present", found, f"labels={metric_labels}")

            # 5c. Tabs present
            print("\n--- 5c. Tabs ---")
            tabs = at.tabs
            report(f"Tabs rendered", len(tabs) >= 1, f"count={len(tabs)}")

            # 5d. Sidebar elements
            print("\n--- 5d. Sidebar ---")
            sb_selectboxes = at.sidebar.selectbox
            report(f"Sidebar selectboxes", len(sb_selectboxes) >= 2, f"count={len(sb_selectboxes)}")

            sb_multiselects = at.sidebar.multiselect
            report(f"Sidebar multiselects", len(sb_multiselects) >= 2, f"count={len(sb_multiselects)}")

            sb_toggles = at.sidebar.toggle
            report(f"Sidebar toggle (show paths)", len(sb_toggles) >= 1, f"count={len(sb_toggles)}")

            # 5e. No warnings when data is present
            print("\n--- 5e. Warning/error states ---")
            warnings = at.warning
            report(f"No unexpected warnings", len(warnings) == 0, 
                   f"warnings={[w.value for w in warnings]}" if warnings else "")

            errors = at.error
            report(f"No errors", len(errors) == 0,
                   f"errors={[e.value for e in errors]}" if errors else "")

            # 5f. Sidebar map interaction — change map and rerun
            print("\n--- 5f. Map switching ---")
            try:
                map_options = sorted(df["map_id"].unique())
                if len(map_options) > 1:
                    second_map = map_options[1]
                    at.sidebar.selectbox[0].set_value(second_map).run()
                    report(
                        f"Switch to '{second_map}' — no exception",
                        not at.exception,
                        str(at.exception[0].value) if at.exception else "",
                    )
                else:
                    warn("Only one map available, skipping map-switch test")
            except Exception as e:
                report("Map switching", False, str(e))

            # 5g. Toggle movement paths off and rerun
            print("\n--- 5g. Toggle paths off ---")
            try:
                at.sidebar.toggle[0].set_value(False).run()
                report("Paths toggle off — no exception", not at.exception,
                       str(at.exception[0].value) if at.exception else "")
            except Exception as e:
                report("Toggle paths off", False, str(e))

            # 5h. Filter to Human only
            print("\n--- 5h. Filter Human only ---")
            try:
                at.sidebar.multiselect[0].set_value(["Human"]).run()
                report("Filter Human only — no exception", not at.exception,
                       str(at.exception[0].value) if at.exception else "")
            except Exception as e:
                report("Filter Human only", False, str(e))

            # 5i. Filter to specific events only
            print("\n--- 5i. Filter Kill events only ---")
            try:
                at.sidebar.multiselect[1].set_value(["Kill"]).run()
                report("Filter Kill only — no exception", not at.exception,
                       str(at.exception[0].value) if at.exception else "")
            except Exception as e:
                report("Filter Kill only", False, str(e))

            # 5j. Empty filter — should show warning
            print("\n--- 5j. Empty event filter → warning ---")
            try:
                at.sidebar.multiselect[1].set_value([]).run()
                # With empty filter, view should be empty, tabs should show warnings
                report("Empty event filter — no crash", not at.exception,
                       str(at.exception[0].value) if at.exception else "")
            except Exception as e:
                report("Empty event filter", False, str(e))

    except ImportError:
        warn("streamlit.testing.v1.AppTest not available (need Streamlit ≥ 1.28)", "Skipping UI tests")
    except Exception as e:
        report("AppTest suite", False, traceback.format_exc())

    # ===========================================================================
    # 6. EDGE CASES & ROBUSTNESS
    # ===========================================================================
    print("\n" + "=" * 70)
    print("6. EDGE CASES & ROBUSTNESS")
    print("=" * 70)

    # 6a. Unknown map_id in world_to_pixel — should raise KeyError
    print("\n--- 6a. Unknown map_id raises KeyError ---")
    try:
        world_to_pixel(0, 0, "NonExistentMap")
        report("Unknown map → KeyError", False, "No exception raised")
    except KeyError:
        report("Unknown map → KeyError", True)
    except Exception as e:
        report("Unknown map → KeyError", False, f"Wrong exception: {type(e).__name__}: {e}")

    # 6b. NaN handling in vectorized coords
    print("\n--- 6b. NaN input handling ---")
    nan_df = pd.DataFrame({
        "x": [100, np.nan, 200],
        "z": [100, 200, np.nan],
        "map_id": ["AmbroseValley"] * 3,
    })
    result = add_pixel_coords_vectorized(nan_df)
    report("NaN x → NaN pixel_x", pd.isna(result["pixel_x"].iloc[1]))
    report("NaN z → NaN pixel_y", pd.isna(result["pixel_y"].iloc[2]))
    report("Valid row unaffected", not pd.isna(result["pixel_x"].iloc[0]))

    # 6c. Extreme coordinates (far outside map)
    print("\n--- 6c. Extreme coordinates ---")
    try:
        px, py = world_to_pixel(99999, -99999, "AmbroseValley")
        report("Extreme coords don't crash", True, f"({px:.0f}, {py:.0f})")
    except Exception as e:
        report("Extreme coords don't crash", False, str(e))

    # 6d. Single-row DataFrame
    print("\n--- 6d. Single-row DataFrame ---")
    single = df.head(1).copy()
    try:
        fig = make_journey_figure(single, single["map_id"].iloc[0], True)
        report("Single-row journey figure", True)
    except Exception as e:
        report("Single-row journey figure", False, str(e))

    # 6e. Single match with 1 event in timeline
    print("\n--- 6e. Single-event timeline ---")
    try:
        fig = make_timeline_figure(single, single["map_id"].iloc[0], 0)
        report("Single-event timeline", True)
    except Exception as e:
        report("Single-event timeline", False, str(e))

# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  PASSED : {PASS}")
print(f"  FAILED : {FAIL}")
print(f"  WARNINGS: {WARN}")
print("=" * 70)

if FAIL > 0:
    print("\n❌ FAILURES:")
    for status, name, detail in results:
        if status == "FAIL":
            print(f"   • {name}: {detail}")

if WARN > 0:
    print("\n⚠️  WARNINGS:")
    for status, name, detail in results:
        if status == "WARN":
            print(f"   • {name}: {detail}")

print()
sys.exit(1 if FAIL > 0 else 0)
