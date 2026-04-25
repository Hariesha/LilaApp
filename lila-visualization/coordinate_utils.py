"""
Coordinate utilities for mapping LILA BLACK world coordinates
to minimap pixel coordinates.

Minimap images are 1024x1024 px. Image origin is top-left (Y flipped).
"""

import numpy as np
import pandas as pd

# Map configuration from the README
MAP_CONFIG = {
    "AmbroseValley": {"scale": 900,  "origin_x": -370, "origin_z": -473},
    "GrandRift":     {"scale": 581,  "origin_x": -290, "origin_z": -290},
    "Lockdown":      {"scale": 1000, "origin_x": -500, "origin_z": -500},
}

IMAGE_SIZE = 1024  # minimap images are 1024x1024


def add_pixel_coords_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized version of add_pixel_coords (much faster for large DataFrames)."""
    df = df.copy()
    df["pixel_x"] = np.nan
    df["pixel_y"] = np.nan
    for map_id, cfg in MAP_CONFIG.items():
        mask = df["map_id"] == map_id
        u = (df.loc[mask, "x"] - cfg["origin_x"]) / cfg["scale"]
        v = (df.loc[mask, "z"] - cfg["origin_z"]) / cfg["scale"]
        df.loc[mask, "pixel_x"] = u * IMAGE_SIZE
        df.loc[mask, "pixel_y"] = (1 - v) * IMAGE_SIZE
    return df
