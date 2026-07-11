#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎁 Yearbook — a personal-data dashboard suite.

Landing page for a Streamlit multipage app with four "wrapped" experiences:
  • 🎧 Music    — Spotify / Apple Music / YouTube Music listening history
  • 📚 Reading  — Goodreads / StoryGraph / Kindle reading history
  • 💬 Social   — Reddit activity (live connect or export)
  • 🛍️ Shopping — Amazon / Walmart order history

Run:  streamlit run Home.py
"""

import streamlit as st
import spotify_auth as sp
import reddit_auth as rd

st.set_page_config(page_title="Yearbook", page_icon="🎁", layout="wide")

# OAuth redirects (Spotify, Reddit) return to the app root — process them here so
# the token is ready when the user opens the relevant page.
sp.handle_callback()
rd.handle_callback()

st.title("🎁 Yearbook")
st.subheader("Turn your messy data exports into a personal year-in-review.")

st.markdown(
    "One reusable idea, many domains: take an unwieldy export (or a live login) from "
    "*any* of several services, normalize the wildly different formats into a single "
    "clean schema, and render a shareable dashboard."
)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🎧 Music")
    st.markdown(
        "Spotify, Apple Music, and YouTube Music — top artists, tracks and albums, "
        "listening habits by month/day/hour, and fun superlatives. **Connect Spotify** "
        "for instant charts, or upload exports for full history."
    )
    st.page_link("pages/1_🎧_Music.py", label="Open Music →")

    st.markdown("### 💬 Social")
    st.markdown(
        "Your Reddit year — posts, comments, top subreddits, and when you post. "
        "**Connect Reddit** for live data (its free API allows personal use), or "
        "upload a data-request export."
    )
    st.page_link("pages/3_💬_Social.py", label="Open Social →")
with col2:
    st.markdown("### 📚 Reading")
    st.markdown(
        "Goodreads, StoryGraph, and Kindle — books read, pages, ratings, reading pace, "
        "and superlatives like your longest book and to-read backlog. Reading exports "
        "are instant, so just upload."
    )
    st.page_link("pages/2_📚_Reading.py", label="Open Reading →")

    st.markdown("### 🛍️ Shopping")
    st.markdown(
        "Amazon and Walmart order history — total spend, spend over time, top categories, "
        "and superlatives like your biggest purchase. No personal-purchase API exists, so "
        "this one is upload-first."
    )
    st.page_link("pages/4_🛍️_Shopping.py", label="Open Shopping →")

st.markdown("---")
st.markdown(
    "**Why it's built this way:** every service exports a different messy format, and "
    "personal-data APIs are mostly locked down (Reddit and Spotify are the exceptions "
    "that allow a live login). Each page has source-specific parsers that map onto one "
    "shared schema before any analysis runs — so adding a new service is just another parser."
)

st.caption("Built by Aditi Kulkarni · github.com/mynamo · Streamlit + Altair")
