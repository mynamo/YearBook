#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streaming Wrapped — a platform-agnostic listening dashboard.

Upload your Spotify, Apple Music, and/or YouTube Music history exports (mix and
match — you can drop in all three at once) and get a personal "Wrapped": top
artists, tracks and albums; how your listening moves through the year, week and
day; and a set of fun superlatives.

Built by Aditi Kulkarni. Companion to my data projects at github.com/mynamo.

Run:  streamlit run streaming_wrapped.py
"""

import calendar

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

from parsers import load_files
from sample_data import generate
import spotify_auth as sp

st.set_page_config(page_title="Music · Yearbook", page_icon="🎧", layout="wide")

# Handle a returning Spotify OAuth redirect (?code=...) before anything renders.
sp.handle_callback()

DOW_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------
def enrich(df, min_seconds):
    """Add derived time columns and a 'counts as a play' filter."""
    df = df.copy()
    df = df.dropna(subset=["ts"])
    # A play counts if it isn't a quick skip. YouTube has no duration, so
    # those always count.
    ms = df["ms_played"]
    df["is_play"] = ms.isna() | (ms >= min_seconds * 1000)
    df = df[df["is_play"]].copy()

    # For time totals, fill unknown durations with the median known duration.
    known_median = df["ms_played"].median()
    if pd.isna(known_median):
        known_median = 200_000
    df["ms_est"] = df["ms_played"].fillna(known_median)

    df["date"] = df["ts"].dt.date
    df["year"] = df["ts"].dt.year
    df["month"] = df["ts"].dt.to_period("M").astype(str)
    df["dow"] = df["ts"].dt.dayofweek.map(lambda i: DOW_ORDER[i])
    df["hour"] = df["ts"].dt.hour
    return df


def fmt_hours(ms_sum):
    hours = ms_sum / 1000 / 3600
    return f"{hours:,.0f}"


# ---------------------------------------------------------------------------
# Sidebar — data source
# ---------------------------------------------------------------------------
st.sidebar.header("🎧 Your data")

sources = ["Use sample data", "Connect Spotify (live)", "Upload my exports"]
mode = st.sidebar.radio(
    "Data source",
    sources,
    help="Connect Spotify for instant charts, or upload exports for full history.",
)

raw = None
report = None
spotify_token = None  # set when connected; drives the live top-charts panel

if mode == "Connect Spotify (live)":
    if not sp.is_configured():
        st.sidebar.warning(
            "Spotify isn't configured yet. Add your app credentials to "
            "`.streamlit/secrets.toml` (see the README), then reload."
        )
    else:
        spotify_token = sp.valid_access_token()
        if spotify_token:
            who = sp.fetch_me(spotify_token)
            st.sidebar.success(f"Connected as {who}")
            if st.sidebar.button("Disconnect Spotify"):
                sp.disconnect()
                st.rerun()
            try:
                raw = sp.fetch_recently_played(spotify_token)
            except Exception as e:
                st.sidebar.error(f"Couldn't load recent plays: {e}")
        else:
            st.sidebar.link_button("🔗 Connect Spotify", sp.build_auth_url(),
                                    type="primary", use_container_width=True)
            st.sidebar.caption("You'll be sent to Spotify to log in, then back here.")

elif mode == "Upload my exports":
    uploads = st.sidebar.file_uploader(
        "Drop Spotify (.json), Apple Music (.csv), and/or YouTube Music (.json) files",
        type=["json", "csv"],
        accept_multiple_files=True,
    )
    if uploads:
        raw, report = load_files(uploads)
    else:
        st.sidebar.info("Waiting for files — or switch to sample data.")
else:
    raw = generate()

min_seconds = st.sidebar.slider(
    "Min seconds to count as a play", 0, 60, 30,
    help="Filters out quick skips. YouTube Music has no duration, so those always count.",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Exports: Spotify → Extended Streaming History (privacy settings). "
    "Apple Music → privacy.apple.com. YouTube Music → Google Takeout (JSON)."
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🎧 Music")
st.caption("One dashboard for Spotify, Apple Music, and YouTube Music — mix and match your exports.")


def render_spotify_live(token):
    """Live top charts straight from the Spotify API (richer than recent plays)."""
    st.subheader("🟢 Your Spotify — live")
    range_label = st.radio(
        "Time range", list(sp.TIME_RANGES.keys()), horizontal=True, index=1,
        key="sp_range",
    )
    tr = sp.TIME_RANGES[range_label]
    try:
        top_artists = sp.fetch_top_artists(token, tr, limit=20)
        top_tracks = sp.fetch_top_tracks(token, tr, limit=20)
    except Exception as e:
        st.error(f"Couldn't load Spotify charts: {e}")
        return

    col_a, col_t = st.columns(2)
    with col_a:
        st.markdown(f"**Top artists — {range_label.lower()}**")
        if top_artists.empty:
            st.caption("Not enough data for this range yet.")
        else:
            ch = (alt.Chart(top_artists.head(10)).mark_bar()
                  .encode(x=alt.X("popularity:Q", title="Popularity"),
                          y=alt.Y("artist:N", sort=top_artists.head(10)["artist"].tolist(),
                                  title=None),
                          tooltip=["rank", "artist", "genres"])
                  .properties(height=300))
            st.altair_chart(ch, use_container_width=True)
            st.dataframe(top_artists[["rank", "artist", "genres"]],
                         hide_index=True, use_container_width=True)
    with col_t:
        st.markdown(f"**Top tracks — {range_label.lower()}**")
        if top_tracks.empty:
            st.caption("Not enough data for this range yet.")
        else:
            st.dataframe(top_tracks[["rank", "track", "artist", "album"]],
                         hide_index=True, use_container_width=True, height=360)
    st.markdown("---")


if spotify_token:
    render_spotify_live(spotify_token)

if raw is None or len(raw) == 0:
    if spotify_token:
        st.info("Your live top charts are above. The time-based dashboard needs "
                "play history — Spotify's API only returns your **last 50 plays**, "
                "so upload an export for the full year view.")
    elif mode == "Connect Spotify (live)":
        st.info("Click **Connect Spotify** in the sidebar to load your top charts instantly.")
    else:
        st.info("Upload at least one export file, or switch to **Use sample data** in the sidebar.")
    if report:
        st.write("File read results:")
        st.table(pd.DataFrame(report, columns=["File", "Rows parsed", "Detected as"]))
    st.stop()

if report:
    with st.expander("File read results"):
        st.table(pd.DataFrame(report, columns=["File", "Rows parsed", "Detected as"]))

# Year filter
all_years = sorted(raw["ts"].dropna().dt.year.unique())
year_opts = ["All time"] + [str(y) for y in all_years]
chosen = st.sidebar.selectbox("Year", year_opts, index=len(year_opts) - 1 if len(all_years) == 1 else 0)

df = enrich(raw, min_seconds)
if chosen != "All time":
    df = df[df["year"] == int(chosen)]

if df.empty:
    st.warning("No plays match the current filters. Lower the 'min seconds' or change the year.")
    st.stop()

label = "all time" if chosen == "All time" else chosen


# ---------------------------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------------------------
total_plays = len(df)
total_ms = df["ms_est"].sum()
minutes = total_ms / 1000 / 60
c1, c2, c3, c4 = st.columns(4)
c1.metric("Plays", f"{total_plays:,}")
c2.metric("Hours listened", fmt_hours(total_ms))
c3.metric("Unique artists", f"{df['artist'].nunique():,}")
c4.metric("Unique tracks", f"{df['track'].nunique():,}")

# Platform mix
plat = df["platform"].value_counts()
st.caption("Source mix: " + " · ".join(f"{k} {v:,}" for k, v in plat.items()))

st.markdown("---")


# ---------------------------------------------------------------------------
# Top artists / tracks / albums
# ---------------------------------------------------------------------------
st.subheader(f"🏆 Your top charts — {label}")

def top_bar(series_df, label_col, title, n=10):
    counts = (series_df.groupby(label_col)
              .size().sort_values(ascending=False).head(n)
              .rename("plays").reset_index())
    chart = (alt.Chart(counts)
             .mark_bar()
             .encode(
                 x=alt.X("plays:Q", title="Plays"),
                 y=alt.Y(f"{label_col}:N", sort="-x", title=None),
                 tooltip=[label_col, "plays"],
             )
             .properties(height=280, title=title))
    return chart, counts

t1, t2, t3 = st.tabs(["Artists", "Tracks", "Albums"])
with t1:
    ch, tbl = top_bar(df, "artist", "Top artists")
    st.altair_chart(ch, use_container_width=True)
with t2:
    tmp = df.copy()
    tmp["track_artist"] = tmp["track"] + " — " + tmp["artist"]
    ch, tbl = top_bar(tmp, "track_artist", "Top tracks")
    st.altair_chart(ch, use_container_width=True)
with t3:
    albums = df[df["album"].astype(str).str.strip() != ""]
    if albums.empty:
        st.info("No album info in this data (YouTube Music exports don't include albums).")
    else:
        ch, tbl = top_bar(albums, "album", "Top albums")
        st.altair_chart(ch, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------------------------------
# Listening over time
# ---------------------------------------------------------------------------
st.subheader("📈 How you listened over time")

# Monthly trend
monthly = df.groupby("month").size().rename("plays").reset_index()
line = (alt.Chart(monthly)
        .mark_area(opacity=0.5, line=True)
        .encode(x=alt.X("month:N", title=None),
                y=alt.Y("plays:Q", title="Plays"),
                tooltip=["month", "plays"])
        .properties(height=220, title="Plays per month"))
st.altair_chart(line, use_container_width=True)

col_a, col_b = st.columns(2)

# Day of week
with col_a:
    dow = (df.groupby("dow").size().reindex(DOW_ORDER).fillna(0)
           .rename("plays").reset_index())
    ch = (alt.Chart(dow).mark_bar()
          .encode(x=alt.X("dow:N", sort=DOW_ORDER, title=None),
                  y=alt.Y("plays:Q", title="Plays"),
                  tooltip=["dow", "plays"])
          .properties(height=240, title="By day of week"))
    st.altair_chart(ch, use_container_width=True)

# Hour x weekday heatmap
with col_b:
    heat = df.groupby(["dow", "hour"]).size().rename("plays").reset_index()
    ch = (alt.Chart(heat).mark_rect()
          .encode(
              x=alt.X("hour:O", title="Hour of day"),
              y=alt.Y("dow:N", sort=DOW_ORDER, title=None),
              color=alt.Color("plays:Q", title="Plays", scale=alt.Scale(scheme="greens")),
              tooltip=["dow", "hour", "plays"])
          .properties(height=240, title="When you press play"))
    st.altair_chart(ch, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------------------------------
# Fun superlatives
# ---------------------------------------------------------------------------
st.subheader("✨ Superlatives")

# Top artist share
artist_counts = df.groupby("artist").size().sort_values(ascending=False)
top_artist = artist_counts.index[0]
top_artist_share = artist_counts.iloc[0] / total_plays

# Favorite hour
fav_hour = int(df.groupby("hour").size().idxmax())
fav_hour_label = f"{fav_hour % 12 or 12}{'am' if fav_hour < 12 else 'pm'}"

# Busiest single day
by_day = df.groupby("date").size().sort_values(ascending=False)
busiest_day = by_day.index[0]
busiest_day_plays = int(by_day.iloc[0])

# Most-skipped track (needs durations)
skip_txt = "—"
if df["ms_played"].notna().any():
    d2 = df[df["ms_played"].notna()].copy()
    d2["skipped"] = d2["ms_played"] < 30_000
    grp = d2.groupby(["track", "artist"]).agg(plays=("skipped", "size"),
                                              skips=("skipped", "sum"))
    grp = grp[grp["plays"] >= 5]
    if not grp.empty:
        grp["rate"] = grp["skips"] / grp["plays"]
        top_skip = grp.sort_values("rate", ascending=False).iloc[0]
        name = grp.sort_values("rate", ascending=False).index[0]
        skip_txt = f"{name[0]} — {name[1]} ({top_skip['rate']:.0%} skipped)"

# Longest binge: max consecutive plays of the same artist (chronological)
df_sorted = df.sort_values("ts")
streak_artist, streak_len = None, 0
cur_artist, cur_len = None, 0
for a in df_sorted["artist"]:
    if a == cur_artist:
        cur_len += 1
    else:
        cur_artist, cur_len = a, 1
    if cur_len > streak_len:
        streak_len, streak_artist = cur_len, cur_artist

# New artists discovered this period (first-ever appearance within window)
first_seen = raw.sort_values("ts").groupby("artist")["ts"].first()
if chosen != "All time":
    discovered = first_seen[first_seen.dt.year == int(chosen)]
else:
    discovered = first_seen
n_discovered = int(discovered.shape[0])

g1, g2, g3 = st.columns(3)
g1.metric("Top artist", top_artist, f"{top_artist_share:.0%} of all plays")
g2.metric("Favorite listening hour", fav_hour_label)
g3.metric("Artists in rotation", f"{df['artist'].nunique():,}")

g4, g5, g6 = st.columns(3)
g4.metric("Longest binge", f"{streak_len} in a row", streak_artist)
g5.metric("Busiest day", str(busiest_day), f"{busiest_day_plays} plays")
g6.metric("New artists discovered", f"{n_discovered:,}")

st.markdown(f"**Most-skipped track:** {skip_txt}")

st.markdown("---")
st.caption(
    "Hours use each play's reported duration; YouTube Music plays (no duration) "
    "are estimated from your median track length. Built with Streamlit + Altair."
)
