#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💬 Social Wrapped — Reddit, Twitter/X, and Instagram in one view.

All three are upload-first: none currently offers a usable personal-data API
(Reddit ended self-serve API access in 2026; X is paywalled; Instagram's died in
2024). Every platform's export is free, though — or explore the mixed sample.
"""

import re

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

from social_parsers import load_social_files
from social_sample import generate

st.set_page_config(page_title="Social · Yearbook", page_icon="💬", layout="wide")

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.title("💬 Social")
st.caption("Your year across Reddit, Twitter/X, and Instagram.")

st.sidebar.header("💬 Your socials")
mode = st.sidebar.radio(
    "Data source", ["Use sample data", "Upload my exports"],
    help="Upload your Reddit / Twitter / Instagram exports, or explore the sample.",
)

raw = None
report = None

if mode == "Upload my exports":
    uploads = st.sidebar.file_uploader(
        "Reddit posts.csv/comments.csv · Twitter tweets.js · Instagram posts_1.json",
        type=["csv", "js", "json"], accept_multiple_files=True)
    if uploads:
        raw, report = load_social_files(uploads)
    else:
        st.sidebar.info("Waiting for files — or switch to sample data.")
else:
    raw = generate()

st.sidebar.markdown("---")
st.sidebar.caption("Reddit: reddit.com/settings/data-request (posts.csv, comments.csv). "
                   "Twitter: your X archive (tweets.js). Instagram: Download Your Information (JSON).")

if raw is None or len(raw) == 0:
    if mode == "Upload my exports":
        st.info("Upload a Reddit / Twitter / Instagram export, or switch to sample data.")
    else:
        st.info("Loading sample data…")
    if report:
        st.table(pd.DataFrame(report, columns=["File", "Rows", "Detected as"]))
    st.stop()

if report:
    with st.expander("File read results"):
        st.table(pd.DataFrame(report, columns=["File", "Rows", "Detected as"]))

# ---------------------------------------------------------------------------
df = raw.copy().dropna(subset=["ts"])
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

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total activity", f"{len(df):,}")
c2.metric("Platforms", f"{df['platform'].nunique()}")
c3.metric("Posts/Tweets", f"{int(df['kind'].isin(['post','tweet']).sum()):,}")
c4.metric("Replies/Comments", f"{int(df['kind'].isin(['comment','reply']).sum()):,}")
st.caption("Source: " + " · ".join(f"{k} {v}" for k, v in df["platform"].value_counts().items()))
st.markdown("---")

# Platform split + posting time
st.subheader(f"🏆 Your footprint — {label}")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Activity by platform**")
    plat = df.groupby("platform").size().rename("n").reset_index()
    ch = (alt.Chart(plat).mark_bar()
          .encode(x=alt.X("n:Q", title="Activity"),
                  y=alt.Y("platform:N", sort="-x", title=None),
                  color=alt.Color("platform:N", legend=None),
                  tooltip=["platform", "n"]).properties(height=200))
    st.altair_chart(ch, use_container_width=True)
with col_b:
    st.markdown("**When you post**")
    heat = df.groupby(["dow", "hour"]).size().rename("n").reset_index()
    ch = (alt.Chart(heat).mark_rect()
          .encode(x=alt.X("hour:O", title="Hour"),
                  y=alt.Y("dow:N", sort=DOW, title=None),
                  color=alt.Color("n:Q", title="Activity", scale=alt.Scale(scheme="purples")),
                  tooltip=["dow", "hour", "n"]).properties(height=200))
    st.altair_chart(ch, use_container_width=True)

# Reddit subreddits + Twitter hashtags (whichever platforms are present)
reddit = df[df["platform"] == "Reddit"]
twitter = df[df["platform"] == "Twitter"]
col_c, col_d = st.columns(2)
with col_c:
    if not reddit.empty:
        st.markdown("**Top subreddits**")
        top = (reddit[reddit["channel"].astype(str).str.strip() != ""]
               .groupby("channel").size().sort_values(ascending=False).head(8)
               .rename("n").reset_index())
        ch = (alt.Chart(top).mark_bar()
              .encode(x=alt.X("n:Q", title="Activity"),
                      y=alt.Y("channel:N", sort="-x", title=None),
                      tooltip=["channel", "n"]).properties(height=260))
        st.altair_chart(ch, use_container_width=True)
with col_d:
    if not twitter.empty:
        st.markdown("**Top hashtags**")
        tags = []
        for t in twitter["text"].astype(str):
            tags += re.findall(r"#(\w+)", t.lower())
        if tags:
            tag_df = pd.Series(tags).value_counts().head(8).rename("n").reset_index()
            tag_df.columns = ["hashtag", "n"]
            ch = (alt.Chart(tag_df).mark_bar()
                  .encode(x=alt.X("n:Q", title="Uses"),
                          y=alt.Y("hashtag:N", sort="-x", title=None),
                          tooltip=["hashtag", "n"]).properties(height=260))
            st.altair_chart(ch, use_container_width=True)
        else:
            st.caption("No hashtags found in your tweets.")

st.markdown("---")

# Activity over time
st.subheader("📈 Activity over time")
monthly = df.groupby(["month", "platform"]).size().rename("n").reset_index()
ch = (alt.Chart(monthly).mark_bar()
      .encode(x=alt.X("month:N", title=None), y=alt.Y("n:Q", title="Activity"),
              color=alt.Color("platform:N", title="Platform"),
              tooltip=["month", "platform", "n"]).properties(height=260))
st.altair_chart(ch, use_container_width=True)

st.markdown("---")

# Superlatives
st.subheader("✨ Superlatives")
fav_hour = int(df.groupby("hour").size().idxmax())
fav_hour_lbl = f"{fav_hour % 12 or 12}{'am' if fav_hour < 12 else 'pm'}"
by_day = df.groupby("date").size().sort_values(ascending=False)
top_platform = df["platform"].value_counts().index[0]

g1, g2, g3 = st.columns(3)
g1.metric("Top platform", top_platform,
          f"{int(df['platform'].value_counts().iloc[0])} posts")
g2.metric("Favorite hour", fav_hour_lbl)
g3.metric("Busiest day", str(by_day.index[0]), f"{int(by_day.iloc[0])} interactions")

if not reddit.empty:
    subs = reddit[reddit["channel"].astype(str).str.strip() != ""].groupby("channel").size()
    if not subs.empty:
        st.markdown(f"**Home subreddit:** r/{subs.idxmax()} ({int(subs.max())} interactions)")

if df["engagement"].notna().any():
    scored = df[df["engagement"].notna()].sort_values("engagement", ascending=False).iloc[0]
    preview = str(scored["text"])[:70] + ("…" if len(str(scored["text"])) > 70 else "")
    where = f"r/{scored['channel']}" if scored["channel"] else scored["platform"]
    st.markdown(f"**Most engagement ({int(scored['engagement'])}, {where}):** {preview}")

st.markdown("---")
st.caption("Built with Streamlit + Altair. Reddit uses its free personal-use API; "
           "Twitter/Instagram are read from export files (no personal API exists).")
