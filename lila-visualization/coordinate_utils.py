"""
Coordinate utilities for mapping LILA BLACK world coordinates
to minimap pixel coordinates.

Minimap images are 1024x1024 px. Image origin is top-left (Y flipped).
Map parameters are loaded dynamically from map_config.json.
"""

import os
import json
from typing import Tuple
import numpy as np
import pandas as pd

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map_config.json")


def _load_map_config() -> dict:
    """Load map configuration from map_config.json."""
    with open(_CONFIG_PATH, "r") as f:
        return json.load(f)


MAP_CONFIG = _load_map_config()

IMAGE_SIZE = 1024  # minimap images are 1024x1024


def world_to_pixel(x: float, z: float, map_id: str) -> Tuple[float, float]:
    """Convert a single world (x, z) pair to minimap (pixel_x, pixel_y)."""
    cfg = MAP_CONFIG[map_id]
    u = (x - cfg["origin_x"]) / cfg["scale"]
    v = (z - cfg["origin_z"]) / cfg["scale"]
    pixel_x = u * IMAGE_SIZE
    pixel_y = (1 - v) * IMAGE_SIZE  # Y axis is flipped in image space
    return pixel_x, pixel_y


def add_pixel_coords(df: pd.DataFrame) -> pd.DataFrame:
    """Add pixel_x and pixel_y columns to a DataFrame that has x, z, and map_id."""
    px_list, py_list = [], []
    for _, row in df.iterrows():
        px, py = world_to_pixel(row["x"], row["z"], row["map_id"])
        px_list.append(px)
        py_list.append(py)
    df = df.copy()
    df["pixel_x"] = px_list
    df["pixel_y"] = py_list
    return df


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
