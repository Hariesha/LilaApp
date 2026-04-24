"""
LILA BLACK – Player Journey Visualization Tool
Streamlit app for Level Designers to explore player behavior on maps.
"""

import os
import base64
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from PIL import Image

from data_pipeline import load_all_data

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LILA BLACK – Player Journey Viz",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide anchor links on headings
st.html("""
<style>
    /* Hide Streamlit heading anchor/link icons */
    a.headerlink,
    .stMarkdown a[href^="#"],
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
</style>
""")

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MINIMAP_DIR = os.path.join(BASE_DIR, "..", "player_data", "minimaps")

MINIMAP_FILES = {
    "AmbroseValley": "AmbroseValley_Minimap.png",
    "GrandRift":     "GrandRift_Minimap.png",
    "Lockdown":      "Lockdown_Minimap.jpg",
}

# ── Event styling ──────────────────────────────────────────────────────────────
EVENT_COLORS = {
    "Position":      "#3b82f6",   # blue
    "BotPosition":   "#6b7280",   # gray
    "Kill":          "#ef4444",   # red
    "Killed":        "#f97316",   # orange
    "BotKill":       "#eab308",   # yellow       — human killed a bot
    "BotKilled":     "#a855f7",   # purple       — human was killed by a bot
    "KilledByStorm": "#06b6d4",   # cyan
    "Loot":          "#22c55e",   # green
}

EVENT_SYMBOLS = {
    "Position":      "circle",
    "BotPosition":   "circle-open",
    "Kill":          "x",
    "Killed":        "x-open",
    "BotKill":       "star",
    "BotKilled":     "star",
    "KilledByStorm": "diamond",
    "Loot":          "square",
}

EVENT_SIZES = {
    "Position":      4,
    "BotPosition":   3,
    "Kill":          12,
    "Killed":        12,
    "BotKill":       10,
    "BotKilled":     12,
    "KilledByStorm": 14,
    "Loot":          8,
}

# ── Helpers ────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_minimap_b64(map_id: str) -> str:
    """Return a base64-encoded data URI for the minimap image (resized to 1024x1024)."""
    path = os.path.join(MINIMAP_DIR, MINIMAP_FILES[map_id])
    img = Image.open(path).convert("RGBA")
    # Resize to 1024x1024 to match IMAGE_SIZE and keep base64 payloads small
    if img.size != (1024, 1024):
        img = img.resize((1024, 1024), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def make_journey_figure(df: pd.DataFrame, map_id: str, show_paths: bool) -> go.Figure:
    """Build a Plotly figure with minimap background and event scatter markers."""
    fig = go.Figure()

    minimap_src = load_minimap_b64(map_id)
    fig.add_layout_image(
        dict(
            source=minimap_src,
            xref="x", yref="y",
            x=0, y=0,
            sizex=1024, sizey=1024,
            sizing="stretch",
            opacity=1.0,
            layer="below",
        )
    )

    if show_paths:
        # Draw movement paths per player (lines connecting Position events)
        pos_df = df[df["event"].isin(["Position", "BotPosition"])]
        for uid, grp in pos_df.groupby("user_id"):
            color = "#3b82f6" if not grp["is_bot"].iloc[0] else "#6b7280"
            fig.add_trace(
                go.Scatter(
                    x=grp["pixel_x"],
                    y=grp["pixel_y"],
                    mode="lines",
                    line=dict(color=color, width=1),
                    opacity=0.4,
                    name=f"{'Bot' if grp['is_bot'].iloc[0] else 'Human'} path",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    # Plot non-position events (combat, loot, storm) as distinct markers on top
    non_pos = df[~df["event"].isin(["Position", "BotPosition"])]
    for evt, grp in non_pos.groupby("event"):
        fig.add_trace(
            go.Scatter(
                x=grp["pixel_x"],
                y=grp["pixel_y"],
                mode="markers",
                marker=dict(
                    color=EVENT_COLORS.get(evt, "#ffffff"),
                    symbol=EVENT_SYMBOLS.get(evt, "circle"),
                    size=EVENT_SIZES.get(evt, 8),
                    line=dict(width=1, color="white"),
                ),
                name=evt,
                text=grp["user_id"],
                hovertemplate=f"<b>{evt}</b><br>Player: %{{text}}<br>px=(%{{x:.0f}}, %{{y:.0f}})<extra></extra>",
            )
        )

    fig.update_xaxes(range=[0, 1024], showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(range=[1024, 0], showgrid=False, zeroline=False, visible=False)
    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="black",
        plot_bgcolor="black",
        legend=dict(
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
            font=dict(color="white", size=11),
            x=1.01,
            y=0.92,
            xanchor="left",
            yanchor="top",
        ),
    )
    return fig


def make_heatmap_figure(df: pd.DataFrame, map_id: str, heatmap_type: str) -> go.Figure:
    """
    Overlay a 2D density heatmap on the minimap.
    heatmap_type: 'traffic' | 'kills' | 'deaths' | 'loot'
    """
    filters = {
        "traffic":  df["event"].isin(["Position", "BotPosition"]),
        "kills":    df["event"].isin(["Kill", "BotKill"]),
        "deaths":   df["event"].isin(["Killed", "BotKilled", "KilledByStorm"]),
        "loot":     df["event"] == "Loot",
    }
    sub = df[filters[heatmap_type]]

    fig = go.Figure()

    minimap_src = load_minimap_b64(map_id)
    fig.add_layout_image(
        dict(
            source=minimap_src,
            xref="x", yref="y",
            x=0, y=0,
            sizex=1024, sizey=1024,
            sizing="stretch",
            opacity=1.0,
            layer="below",
        )
    )

    # Custom colorscales: low values fully transparent → high values opaque
    colorscales = {
        "traffic": [
            [0.0, "rgba(59,  130, 246, 0.0)"],
            [0.3, "rgba(59,  130, 246, 0.25)"],
            [0.6, "rgba(37,  99,  235, 0.6)"],
            [1.0, "rgba(29,  78,  216, 0.92)"],
        ],
        "kills": [
            [0.0, "rgba(239, 68,  68,  0.0)"],
            [0.3, "rgba(239, 68,  68,  0.25)"],
            [0.6, "rgba(220, 38,  38,  0.6)"],
            [1.0, "rgba(185, 28,  28,  0.92)"],
        ],
        "deaths": [
            [0.0, "rgba(249, 115, 22,  0.0)"],
            [0.3, "rgba(249, 115, 22,  0.25)"],
            [0.6, "rgba(234, 88,  12,  0.6)"],
            [1.0, "rgba(194, 65,  12,  0.92)"],
        ],
        "loot": [
            [0.0, "rgba(34,  197, 94,  0.0)"],
            [0.3, "rgba(34,  197, 94,  0.25)"],
            [0.6, "rgba(22,  163, 74,  0.6)"],
            [1.0, "rgba(21,  128, 61,  0.92)"],
        ],
    }

    if not sub.empty:
        fig.add_trace(
            go.Histogram2dContour(
                x=sub["pixel_x"],
                y=sub["pixel_y"],
                colorscale=colorscales[heatmap_type],
                reversescale=False,
                showscale=True,
                ncontours=20,
                opacity=1.0,
                contours=dict(coloring="fill"),
                line=dict(width=0),
                name=heatmap_type.capitalize(),
            )
        )

    fig.update_xaxes(range=[0, 1024], showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(range=[1024, 0], showgrid=False, zeroline=False, visible=False)
    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="black",
        plot_bgcolor="black",
    )
    return fig


def make_timeline_figure(match_df: pd.DataFrame, map_id: str, ts_cutoff_ms: int) -> go.Figure:
    """Show all events up to ts_cutoff_ms within the match."""
    # Normalize ts relative to match start
    t_min = match_df["ts"].min()
    match_df = match_df.copy()
    match_df["ts_ms"] = (match_df["ts"] - t_min).dt.total_seconds() * 1000
    visible = match_df[match_df["ts_ms"] <= ts_cutoff_ms]
    return make_journey_figure(visible, map_id, show_paths=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────

def sidebar(df: pd.DataFrame):
    st.sidebar.title("🎮 LILA BLACK")
    st.sidebar.markdown("**Player Journey Visualization Tool**")
    st.sidebar.divider()

    map_id = st.sidebar.selectbox(
        "Map",
        options=sorted(df["map_id"].unique()),
        index=0,
    )

    available_dates = sorted(df[df["map_id"] == map_id]["date"].unique())
    date = st.sidebar.selectbox(
        "Date",
        options=["All"] + available_dates,
        format_func=lambda d: d.replace("_", " "),
    )

    filtered = df[df["map_id"] == map_id]
    if date != "All":
        filtered = filtered[filtered["date"] == date]


    player_type = st.sidebar.multiselect(
        "Player type",
        options=["Human", "Bot"],
        default=["Human", "Bot"],
    )

    all_events = sorted(df["event"].unique())
    event_filter = st.sidebar.multiselect(
        "Event types",
        options=all_events,
        default=all_events,
    )

    show_paths = st.sidebar.toggle("Show movement paths", value=True)

    st.sidebar.divider()
    st.sidebar.markdown(
        "**Legend**\n"
        + "\n".join(
            f"- <span style='color:{v}'>■</span> {k}"
            for k, v in EVENT_COLORS.items()
        ),
        unsafe_allow_html=True,
    )

    return map_id, date, player_type, event_filter, show_paths, filtered


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    df = load_all_data()

    map_id, date, player_types, event_filter, show_paths, map_filtered = sidebar(df)

    # Apply all filters — empty multiselect means nothing selected → show nothing
    view = map_filtered.copy()
    view = view[view["player_type"].isin(player_types)]
    view = view[view["event"].isin(event_filter)]

    # ── Header metrics ─────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Events shown", f"{len(view):,}")
    col2.metric("Unique players", view["user_id"].nunique())
    col3.metric("Matches", view["match_id"].nunique())
    col4.metric("Kills", int(view["event"].isin(["Kill", "BotKill"]).sum()))
    col5.metric("Loot pickups", int((view["event"] == "Loot").sum()))

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_journey, tab_heatmap, tab_timeline, tab_stats = st.tabs(
        ["🗺️ Player Journeys", "🔥 Heatmaps", "⏱️ Match Timeline", "📊 Stats"]
    )

    # ── Tab 1: Player Journeys ─────────────────────────────────────────────────
    with tab_journey:
        st.subheader(f"Player Journeys — {map_id}")
        if view.empty:
            st.warning("No data matches the current filters.")
        else:
            fig = make_journey_figure(view, map_id, show_paths)
            st.plotly_chart(fig, width="stretch", key="journey_fig")

    # ── Tab 2: Heatmaps ────────────────────────────────────────────────────────
    with tab_heatmap:
        st.subheader(f"Heatmaps — {map_id}")
        heatmap_type = st.radio(
            "Heatmap type",
            options=["traffic", "kills", "deaths", "loot"],
            horizontal=True,
            format_func=str.capitalize,
        )
        if view.empty:
            st.warning("No data matches the current filters.")
        else:
            fig = make_heatmap_figure(view, map_id, heatmap_type)
            st.plotly_chart(fig, width="stretch", key="heatmap_fig")

    # ── Tab 3: Timeline ────────────────────────────────────────────────────────
    with tab_timeline:
        st.subheader("Match Timeline / Playback")

        # Always show an in-tab match picker so users don't need the sidebar
        available_timeline_matches = sorted(
            map_filtered[map_filtered["map_id"] == map_id]["match_id_clean"].unique()
        )
        # Default to first match in the list
        default_idx = 0
        timeline_match = st.selectbox(
            "Select match to replay",
            options=available_timeline_matches,
            index=default_idx,
            key="timeline_match_picker",
        )

        match_df = map_filtered[
            (map_filtered["match_id_clean"] == timeline_match) & (map_filtered["map_id"] == map_id)
        ].copy()
        # Apply the same player type + event filters from the sidebar
        match_df = match_df[match_df["player_type"].isin(player_types)]
        match_df = match_df[match_df["event"].isin(event_filter)]

        if match_df.empty:
            st.warning("No data for this match.")
        else:
            t_min = match_df["ts"].min()
            t_max = match_df["ts"].max()
            # Use milliseconds to avoid int() truncating sub-second durations
            duration_ms = int((t_max - t_min).total_seconds() * 1000)
            duration_s_display = round((t_max - t_min).total_seconds(), 1)

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Match duration", f"{duration_s_display}s")
            col_b.metric("Total events", f"{len(match_df):,}")
            col_c.metric("Players (files)", match_df["user_id"].nunique())

            ts_cutoff_ms = st.slider(
                "Time into match (seconds)",
                min_value=0,
                max_value=max(duration_ms, 1),
                value=max(duration_ms, 1),
                step=max(duration_ms // 60, 1),
                format="%d ms",
            )
            ts_cutoff_s_display = round(ts_cutoff_ms / 1000, 1)

            n_events = int(
                ((match_df["ts"] - t_min).dt.total_seconds() * 1000 <= ts_cutoff_ms).sum()
            )
            st.caption(f"Showing {n_events:,} / {len(match_df):,} events up to {ts_cutoff_s_display}s into match")

            fig = make_timeline_figure(match_df, map_id, ts_cutoff_ms)
            st.plotly_chart(fig, width="stretch", key="timeline_fig")

    # ── Tab 4: Stats ───────────────────────────────────────────────────────────
    with tab_stats:
        st.subheader("Match & Player Statistics")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### Event distribution")
            event_counts = view["event"].value_counts().reset_index()
            event_counts.columns = ["Event", "Count"]
            fig_bar = px.bar(
                event_counts,
                x="Event",
                y="Count",
                color="Event",
                color_discrete_map=EVENT_COLORS,
                template="plotly_dark",
            )
            fig_bar.update_layout(showlegend=False, margin=dict(t=10))
            st.plotly_chart(fig_bar, width="stretch", key="stats_bar")

        with c2:
            st.markdown("#### Events per day")
            day_counts = view.groupby(["date", "event"]).size().reset_index(name="Count")
            fig_line = px.bar(
                day_counts,
                x="date",
                y="Count",
                color="event",
                color_discrete_map=EVENT_COLORS,
                barmode="stack",
                template="plotly_dark",
            )
            fig_line.update_layout(margin=dict(t=10))
            st.plotly_chart(fig_line, width="stretch", key="stats_line")

        st.markdown("#### Top players by kills")
        kills_df = view[view["event"].isin(["Kill", "BotKill"])].copy()
        if kills_df.empty:
            st.info("No kill events match the current filters.")
        else:
            top_killers = (
                kills_df.groupby(["user_id", "event"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
            top_killers.columns.name = None  # remove multi-level column name
            top_killers = top_killers.rename(columns={
                "user_id": "Player",
                "BotKill": "Bot Kill",
                "total_kills": "Total Kills",
            })
            # Rename any remaining underscored columns
            top_killers.columns = [c.replace("_", " ").title() if c != "Player" else c for c in top_killers.columns]
            top_killers["Total Kills"] = top_killers.get("Kill", 0) + top_killers.get("Bot Kill", 0)
            top_killers = top_killers.sort_values("Total Kills", ascending=False).head(15)
            top_killers = top_killers.set_index("Player")

            # Center-align numeric columns, left-align Player (index)
            numeric_cols = [c for c in top_killers.columns]
            col_config = {
                col: st.column_config.NumberColumn(col, help=None)
                for col in numeric_cols
            }
            st.dataframe(
                top_killers.style
                    .set_properties(subset=numeric_cols, **{"text-align": "center"})
                    .set_table_styles([
                        {"selector": "th", "props": [("text-align", "center")]},
                    ]),
                width="stretch",
                column_config=col_config,
            )

        st.markdown("#### Human vs Bot split")
        split = view["player_type"].value_counts().reset_index()
        split.columns = ["Type", "Events"]
        fig_pie = px.pie(
            split, names="Type", values="Events",
            color="Type",
            color_discrete_map={"Human": "#3b82f6", "Bot": "#6b7280"},
            template="plotly_dark",
        )
        st.plotly_chart(fig_pie, width="stretch", key="stats_pie")


if __name__ == "__main__":
    main()
