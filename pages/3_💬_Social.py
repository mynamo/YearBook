#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💬 Social Wrapped — your Reddit activity. Connect Reddit for live data, upload a
Reddit data-request export, or explore the sample. Shows activity over time, top
subreddits, when you post, and a few superlatives.
"""

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

from reddit_parsers import load_social_files
from reddit_sample import generate
import reddit_auth as rd

st.set_page_config(page_title="Social · Yearbook", page_icon="💬", layout="wide")

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.title("💬 Social")
st.caption("Your Reddit year — posts, comments, and the subreddits you live in.")

st.sidebar.header("💬 Your Reddit")
mode = st.sidebar.radio(
    "Data source", ["Use sample data", "Connect Reddit (live)", "Upload my export"],
    help="Reddit's free API allows personal use, so you can connect directly.",
)

raw = None
report = None

if mode == "Connect Reddit (live)":
    if not rd.is_configured():
        st.sidebar.warning("Reddit isn't configured yet. Add your app credentials to "
                           "`.streamlit/secrets.toml` (see README), then reload.")
    else:
        token = rd.valid_access_token()
        if token:
            who = rd.fetch_me(token)
            st.sidebar.success(f"Connected as u/{who}")
            if st.sidebar.button("Disconnect"):
                rd.disconnect(); st.rerun()
            try:
                raw = rd.fetch_recent(token, who)
            except Exception as e:
                st.sidebar.error(f"Couldn't load Reddit data: {e}")
        else:
            st.sidebar.link_button("🔗 Connect Reddit", rd.build_auth_url(),
                                   type="primary", use_container_width=True)
            st.sidebar.caption("You'll log in at Reddit, then come back here.")
elif mode == "Upload my export":
    uploads = st.sidebar.file_uploader(
        "Drop your Reddit posts.csv / comments.csv", type=["csv"], accept_multiple_files=True)
    if uploads:
        raw, report = load_social_files(uploads)
    else:
        st.sidebar.info("Waiting for files — or switch to sample data.")
else:
    raw = generate()

st.sidebar.markdown("---")
st.sidebar.caption("Export: reddit.com/settings/data-request (posts.csv, comments.csv). "
                   "Live: reddit.com/prefs/apps → web app.")

if raw is None or len(raw) == 0:
    if mode == "Connect Reddit (live)":
        st.info("Click **Connect Reddit** in the sidebar to load your activity.")
    elif mode == "Upload my export":
        st.info("Upload your Reddit `posts.csv` / `comments.csv`, or switch to sample data.")
    else:
        st.info("Loading sample data…")
    if report:
        st.table(pd.DataFrame(report, columns=["File", "Rows", "Detected as"]))
    st.stop()

if report:
    with st.expander("File read results"):
        st.table(pd.DataFrame(report, columns=["File", "Rows", "Detected as"]))

# ---------------------------------------------------------------------------
df = raw.copy()
df = df.dropna(subset=["ts"])
df["date"] = df["ts"].dt.date
df["year"] = df["ts"].dt.year
df["month"] = df["ts"].dt.to_period("M").astype(str)
df["dow"] = df["ts"].dt.dayofweek.map(lambda i: DOW[i])
df["hour"] = df["ts"].dt.hour

years = sorted(df["year"].unique())
opts = ["All time"] + [str(y) for y in years]
chosen = st.sidebar.selectbox("Year", opts, index=0)
if chosen != "All time":
    df = df[df["year"] == int(chosen)]
label = "all time" if chosen == "All time" else chosen

if df.empty:
    st.warning("No activity in this period.")
    st.stop()

posts = int((df["kind"] == "post").sum())
comments = int((df["kind"] == "comment").sum())
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total activity", f"{len(df):,}")
c2.metric("Posts", f"{posts:,}")
c3.metric("Comments", f"{comments:,}")
c4.metric("Subreddits", f"{df['subreddit'].nunique():,}")
st.caption("Source: " + " · ".join(f"{k} {v}" for k, v in df["source"].value_counts().items()))
st.markdown("---")

# Top subreddits + posting time
st.subheader(f"🏆 Where you spend your time — {label}")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Top subreddits**")
    top = (df.groupby("subreddit").size().sort_values(ascending=False).head(10)
           .rename("activity").reset_index())
    ch = (alt.Chart(top).mark_bar()
          .encode(x=alt.X("activity:Q", title="Posts + comments"),
                  y=alt.Y("subreddit:N", sort="-x", title=None),
                  tooltip=["subreddit", "activity"]).properties(height=300))
    st.altair_chart(ch, use_container_width=True)
with col_b:
    st.markdown("**When you post**")
    heat = df.groupby(["dow", "hour"]).size().rename("n").reset_index()
    ch = (alt.Chart(heat).mark_rect()
          .encode(x=alt.X("hour:O", title="Hour"),
                  y=alt.Y("dow:N", sort=DOW, title=None),
                  color=alt.Color("n:Q", title="Activity", scale=alt.Scale(scheme="oranges")),
                  tooltip=["dow", "hour", "n"]).properties(height=300))
    st.altair_chart(ch, use_container_width=True)

st.markdown("---")

# Activity over time
st.subheader("📈 Activity over time")
monthly = df.groupby(["month", "kind"]).size().rename("n").reset_index()
ch = (alt.Chart(monthly).mark_bar()
      .encode(x=alt.X("month:N", title=None), y=alt.Y("n:Q", title="Activity"),
              color=alt.Color("kind:N", title="Type"),
              tooltip=["month", "kind", "n"]).properties(height=260))
st.altair_chart(ch, use_container_width=True)

st.markdown("---")

# Superlatives
st.subheader("✨ Superlatives")
sub_counts = df.groupby("subreddit").size().sort_values(ascending=False)
top_sub = sub_counts.index[0]
fav_hour = int(df.groupby("hour").size().idxmax())
fav_hour_lbl = f"{fav_hour % 12 or 12}{'am' if fav_hour < 12 else 'pm'}"
by_day = df.groupby("date").size().sort_values(ascending=False)

g1, g2, g3 = st.columns(3)
g1.metric("Home subreddit", f"r/{top_sub}", f"{int(sub_counts.iloc[0])} interactions")
g2.metric("Favorite hour", fav_hour_lbl)
g3.metric("Busiest day", str(by_day.index[0]), f"{int(by_day.iloc[0])} posts/comments")

# Top-scored post only when scores exist (live data)
if df["score"].notna().any():
    scored = df[df["score"].notna()].sort_values("score", ascending=False)
    top_row = scored.iloc[0]
    preview = top_row["text"][:70] + ("…" if len(top_row["text"]) > 70 else "")
    st.markdown(f"**Top-scored ({int(top_row['score'])} pts, r/{top_row['subreddit']}):** {preview}")
else:
    st.caption("Connect Reddit (live) to see upvote scores — the export doesn't include them.")

st.markdown("---")
st.caption("Built with Streamlit + Altair. Reddit's free API is used for personal, non-commercial access.")
