#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎁 Wrapped — a personal-data dashboard suite.

Landing page for a Streamlit multipage app with two "wrapped" experiences:
  • 🎧 Music   — Spotify / Apple Music / YouTube Music listening history
  • 📚 Reading — Goodreads / StoryGraph / Kindle reading history

Run:  streamlit run Home.py
"""

import streamlit as st
import spotify_auth as sp

st.set_page_config(page_title="Yearbook", page_icon="🎁", layout="wide")

# The Spotify OAuth redirect returns to the app root — process it here so the
# token is ready when the user opens the Music page.
sp.handle_callback()

st.title("🎁 Yearbook")
st.subheader("Turn your messy data exports into a personal year-in-review.")

st.markdown(
    "One reusable idea, two domains: take an unwieldy export from *any* of several "
    "services, normalize the wildly different formats into a single clean schema, "
    "and render a shareable dashboard."
)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🎧 Music")
    st.markdown(
        "Spotify, Apple Music, and YouTube Music in one view — top artists, tracks "
        "and albums, listening habits by month/day/hour, and fun superlatives. "
        "**Connect Spotify** for instant charts, or upload exports for full history."
    )
    st.page_link("pages/1_🎧_Music.py", label="Open Music →")
with col2:
    st.markdown("### 📚 Reading")
    st.markdown(
        "Goodreads, StoryGraph, and Kindle — books read, pages, ratings, reading "
        "pace over the year, and superlatives like your longest book and to-read "
        "backlog. Reading exports are instant, so just upload."
    )
    st.page_link("pages/2_📚_Reading.py", label="Open Reading →")

st.markdown("---")
st.markdown(
    "**Why it's built this way:** every service exports a different messy format "
    "(Spotify JSON, Apple Music CSV, YouTube Takeout JSON, Goodreads/StoryGraph CSV). "
    "Each page has platform-specific parsers that map onto one shared schema before "
    "any analysis runs — so adding a new service is just another parser."
)

st.caption("Built by Aditi Kulkarni · github.com/mynamo · Streamlit + Altair")
