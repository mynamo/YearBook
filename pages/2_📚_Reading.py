#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📚 Reading Wrapped — books read, pace, and superlatives from your Goodreads /
StoryGraph / Kindle exports. Upload-first (reading exports are instant, so no
login flow is needed), with sample data for an immediate demo.
"""

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

from reading_parsers import load_reading_files
from reading_sample import generate

st.set_page_config(page_title="Reading · Yearbook", page_icon="📚", layout="wide")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.title("📚 Reading")
st.caption("Goodreads, StoryGraph, and Kindle — one shelf-to-stats dashboard.")


# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------
st.sidebar.header("📚 Your books")
mode = st.sidebar.radio(
    "Data source", ["Use sample data", "Upload my exports"],
    help="Goodreads: My Books → Import/Export. StoryGraph: Manage Account → Export.",
)

raw = None
report = None
if mode == "Upload my exports":
    uploads = st.sidebar.file_uploader(
        "Drop your Goodreads / StoryGraph / Kindle CSV(s)",
        type=["csv"], accept_multiple_files=True,
    )
    if uploads:
        raw, report = load_reading_files(uploads)
    else:
        st.sidebar.info("Waiting for files — or switch to sample data.")
else:
    raw = generate()

st.sidebar.markdown("---")
st.sidebar.caption(
    "No reading service offers a live API, but every export downloads instantly — "
    "so upload is all you need."
)

if raw is None or len(raw) == 0:
    if mode == "Upload my exports":
        st.info("Upload a Goodreads or StoryGraph CSV, or switch to **Use sample data**.")
    else:
        st.info("Loading sample data...")
    if report:
        st.table(pd.DataFrame(report, columns=["File", "Books parsed", "Detected as"]))
    st.stop()

if report:
    with st.expander("File read results"):
        st.table(pd.DataFrame(report, columns=["File", "Books parsed", "Detected as"]))


# ---------------------------------------------------------------------------
# Split shelves + year filter
# ---------------------------------------------------------------------------
raw = raw.copy()
finished = raw[raw["shelf"] == "read"].copy()
finished["date_read"] = pd.to_datetime(finished["date_read"], errors="coerce")
finished_dated = finished.dropna(subset=["date_read"])

years = sorted(finished_dated["date_read"].dt.year.unique().tolist())
year_opts = ["All time"] + [str(y) for y in years]
chosen = st.sidebar.selectbox("Year", year_opts, index=0)

view = finished.copy()
if chosen != "All time":
    view = finished_dated[finished_dated["date_read"].dt.year == int(chosen)].copy()

label = "all time" if chosen == "All time" else chosen

if view.empty:
    st.warning("No finished books in this period. Try a different year.")
    st.stop()


# ---------------------------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------------------------
books_read = len(view)
total_pages = int(view["pages"].fillna(0).sum())
avg_rating = view["rating"].mean(skipna=True)
currently = int((raw["shelf"] == "currently-reading").sum())
backlog = int((raw["shelf"] == "to-read").sum())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Books read", f"{books_read:,}")
c2.metric("Pages read", f"{total_pages:,}")
c3.metric("Avg rating", f"{avg_rating:.2f}★" if not np.isnan(avg_rating) else "—")
c4.metric("Currently reading", f"{currently}")
c5.metric("On the to-read pile", f"{backlog}")

plat = raw["platform"].value_counts()
st.caption("Source mix: " + " · ".join(f"{k} {v}" for k, v in plat.items()))
st.markdown("---")


# ---------------------------------------------------------------------------
# Top authors + rating distribution
# ---------------------------------------------------------------------------
st.subheader(f"🏆 Your shelves — {label}")
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Most-read authors**")
    authors = (view.groupby("author").size().sort_values(ascending=False)
               .head(10).rename("books").reset_index())
    authors = authors[authors["author"].str.strip() != ""]
    ch = (alt.Chart(authors).mark_bar()
          .encode(x=alt.X("books:Q", title="Books"),
                  y=alt.Y("author:N", sort="-x", title=None),
                  tooltip=["author", "books"])
          .properties(height=300))
    st.altair_chart(ch, use_container_width=True)

with col_b:
    st.markdown("**How you rate**")
    rated = view.dropna(subset=["rating"])
    if rated.empty:
        st.caption("No ratings in this data.")
    else:
        dist = (rated["rating"].round().astype(int).value_counts()
                .reindex([1, 2, 3, 4, 5]).fillna(0).rename("books").reset_index())
        dist.columns = ["stars", "books"]
        ch = (alt.Chart(dist).mark_bar()
              .encode(x=alt.X("stars:O", title="Stars"),
                      y=alt.Y("books:Q", title="Books"),
                      tooltip=["stars", "books"])
              .properties(height=300))
        st.altair_chart(ch, use_container_width=True)

# Optional genre view (present in sample data / when derivable)
if "genre" in view.columns and view["genre"].notna().any():
    st.markdown("**By genre**")
    genres = (view.dropna(subset=["genre"]).groupby("genre").size()
              .sort_values(ascending=False).rename("books").reset_index())
    ch = (alt.Chart(genres).mark_bar()
          .encode(x=alt.X("books:Q", title="Books"),
                  y=alt.Y("genre:N", sort="-x", title=None),
                  tooltip=["genre", "books"])
          .properties(height=240))
    st.altair_chart(ch, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------------------------------
# Reading pace over time
# ---------------------------------------------------------------------------
st.subheader("📈 Your reading pace")
dated = view.dropna(subset=["date_read"]).copy()
if dated.empty:
    st.caption("No dated finish dates in this data, so the pace chart is unavailable.")
else:
    if chosen == "All time":
        dated["period"] = dated["date_read"].dt.to_period("M").astype(str)
        x_title = "Month"
    else:
        dated["period"] = dated["date_read"].dt.month.map(lambda m: MONTHS[m - 1])
    grp = dated.groupby("period").agg(books=("title", "size"),
                                      pages=("pages", "sum")).reset_index()
    if chosen != "All time":
        grp["period"] = pd.Categorical(grp["period"], categories=MONTHS, ordered=True)
        grp = grp.sort_values("period")

    col_x, col_y = st.columns(2)
    with col_x:
        ch = (alt.Chart(grp).mark_bar()
              .encode(x=alt.X("period:N", sort=None, title=None),
                      y=alt.Y("books:Q", title="Books finished"),
                      tooltip=["period", "books"])
              .properties(height=240, title="Books finished"))
        st.altair_chart(ch, use_container_width=True)
    with col_y:
        ch = (alt.Chart(grp).mark_area(opacity=0.5, line=True)
              .encode(x=alt.X("period:N", sort=None, title=None),
                      y=alt.Y("pages:Q", title="Pages"),
                      tooltip=["period", "pages"])
              .properties(height=240, title="Pages read"))
        st.altair_chart(ch, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------------------------------
# Superlatives
# ---------------------------------------------------------------------------
st.subheader("✨ Superlatives")

paged = view.dropna(subset=["pages"])
paged = paged[paged["pages"] > 0]
longest = paged.loc[paged["pages"].idxmax()] if not paged.empty else None
shortest = paged.loc[paged["pages"].idxmin()] if not paged.empty else None

top_author_counts = view.groupby("author").size().sort_values(ascending=False)
top_author = top_author_counts.index[0] if not top_author_counts.empty else "—"
top_author_n = int(top_author_counts.iloc[0]) if not top_author_counts.empty else 0

rated = view.dropna(subset=["rating"])
five_stars = int((rated["rating"].round() == 5).sum())

avg_len = paged["pages"].mean() if not paged.empty else np.nan

# Best month (most books) if dated
best_month = "—"
if not dated.empty:
    bm = dated.groupby(dated["date_read"].dt.to_period("M")).size().sort_values(ascending=False)
    best_month = str(bm.index[0]) if not bm.empty else "—"

g1, g2, g3 = st.columns(3)
g1.metric("Most-read author", top_author, f"{top_author_n} books")
g2.metric("Longest book",
          longest["title"][:28] if longest is not None else "—",
          f"{int(longest['pages'])} pages" if longest is not None else "")
g3.metric("Shortest book",
          shortest["title"][:28] if shortest is not None else "—",
          f"{int(shortest['pages'])} pages" if shortest is not None else "")

g4, g5, g6 = st.columns(3)
g4.metric("5-star reads", f"{five_stars}")
g5.metric("Average book length", f"{avg_len:.0f} pages" if not np.isnan(avg_len) else "—")
g6.metric("Biggest reading month", best_month)

if backlog:
    est_pages = int(raw[raw["shelf"] == "to-read"]["pages"].fillna(avg_len if not np.isnan(avg_len) else 300).sum())
    st.markdown(
        f"**Your to-read pile:** {backlog} books (~{est_pages:,} pages). "
        f"At {label}'s pace of {books_read} books, that's a while — better start reading. 📖"
    )

st.markdown("---")
st.caption("Built with Streamlit + Altair. Pages/ratings shown where the export "
           "includes them (Goodreads and StoryGraph both do).")
