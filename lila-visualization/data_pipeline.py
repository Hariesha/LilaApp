"""
Data pipeline: loads and caches all parquet files from player_data/.

Produces a single clean DataFrame with added columns:
  - date          : e.g. "February_10"
  - is_bot        : True if user_id is numeric (bot), False for human
  - player_type   : "Bot" or "Human"
  - pixel_x/y     : minimap pixel coordinates
"""

import os
import re
import pandas as pd
import pyarrow.parquet as pq
import streamlit as st

from coordinate_utils import add_pixel_coords_vectorized

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "player_data")

def _discover_days() -> list[str]:
    """Dynamically find all date folders under the player_data directory."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        d for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d)) and d not in {"minimaps", "__pycache__"}
    )

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_bot(user_id: str) -> bool:
    """Return True if user_id is a numeric bot ID rather than a UUID."""
    return not bool(_UUID_RE.match(user_id))


@st.cache_data(show_spinner="Loading match data…")
def load_all_data() -> pd.DataFrame:
    """Load all parquet files across all days into a single DataFrame."""
    frames = []
    for day in _discover_days():
        folder = os.path.join(DATA_DIR, day)
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            try:
                df = pq.read_table(fpath).to_pandas()
            except Exception:
                continue

            # Decode event bytes → str
            df["event"] = df["event"].apply(
                lambda v: v.decode("utf-8") if isinstance(v, bytes) else v
            )

            df["date"] = day

            # Determine bot vs human from filename (first segment before _)
            uid_from_filename = fname.split("_")[0]
            df["is_bot"] = _is_bot(uid_from_filename)
            df["player_type"] = df["is_bot"].map({True: "Bot", False: "Human"})

            frames.append(df)

    if not frames:
        raise RuntimeError(f"No data files found under {DATA_DIR}")

    all_df = pd.concat(frames, ignore_index=True)

    # Strip .nakama-0 suffix from match_id for cleaner display
    all_df["match_id_clean"] = all_df["match_id"].str.replace(
        r"\.nakama-0$", "", regex=True
    )

    # Add minimap pixel coordinates
    all_df = add_pixel_coords_vectorized(all_df)

    # Sort by timestamp within each match
    all_df.sort_values(["match_id", "ts"], inplace=True)
    all_df.reset_index(drop=True, inplace=True)

    return all_df
