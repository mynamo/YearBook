#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛍️ Shopping Wrapped — your Amazon & Walmart order history. Upload the export
CSVs (there's no personal-purchase API for either), or explore the sample.
Shows total spend, spend over time, top categories, and superlatives.
"""

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

from shopping_parsers import load_shopping_files
from shopping_sample import generate

st.set_page_config(page_title="Shopping · Yearbook", page_icon="🛍️", layout="wide")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.title("🛍️ Shopping")
st.caption("Your Amazon & Walmart year — what you bought and what it cost.")

st.sidebar.header("🛍️ Your orders")
mode = st.sidebar.radio(
    "Data source", ["Use sample data", "Upload my exports"],
    help="Amazon: Request My Data. Walmart: account/order-history export.",
)

raw = None
report = None
if mode == "Upload my exports":
    uploads = st.sidebar.file_uploader(
        "Drop your Amazon / Walmart order-history CSV(s)", type=["csv"], accept_multiple_files=True)
    if uploads:
        raw, report = load_shopping_files(uploads)
    else:
        st.sidebar.info("Waiting for files — or switch to sample data.")
else:
    raw = generate()

st.sidebar.markdown("---")
st.sidebar.caption("Neither Amazon nor Walmart offers a personal-purchase API, "
                   "so this is upload-first — but their exports download quickly.")

if raw is None or len(raw) == 0:
    if mode == "Upload my exports":
        st.info("Upload an Amazon or Walmart order-history CSV, or switch to sample data.")
    else:
        st.info("Loading sample data…")
    if report:
        st.table(pd.DataFrame(report, columns=["File", "Orders", "Detected as"]))
    st.stop()

if report:
    with st.expander("File read results"):
        st.table(pd.DataFrame(report, columns=["File", "Orders", "Detected as"]))

# ---------------------------------------------------------------------------
df = raw.copy()
df = df.dropna(subset=["date"])
df["year"] = df["date"].dt.year
df["month_num"] = df["date"].dt.month

years = sorted(df["year"].unique())
opts = ["All time"] + [str(y) for y in years]
chosen = st.sidebar.selectbox("Year", opts, index=0)
if chosen != "All time":
    df = df[df["year"] == int(chosen)]
label = "all time" if chosen == "All time" else chosen

if df.empty:
    st.warning("No orders in this period.")
    st.stop()

total_spend = df["price"].fillna(0).sum()
n_orders = len(df)
items_bought = int(df["quantity"].fillna(1).sum())
avg_order = df["price"].mean(skipna=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total spend", f"${total_spend:,.0f}")
c2.metric("Orders", f"{n_orders:,}")
c3.metric("Items", f"{items_bought:,}")
c4.metric("Avg order", f"${avg_order:,.2f}" if not np.isnan(avg_order) else "—")
st.caption("Source: " + " · ".join(f"{k} {v}" for k, v in df["platform"].value_counts().items()))
st.markdown("---")

# Spend over time + by category
st.subheader(f"📈 Where the money went — {label}")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Spend by month**")
    m = df.groupby("month_num")["price"].sum().reindex(range(1, 13)).fillna(0).reset_index()
    m["Month"] = m["month_num"].map(lambda i: MONTHS[i - 1])
    ch = (alt.Chart(m).mark_bar()
          .encode(x=alt.X("Month:N", sort=MONTHS, title=None),
                  y=alt.Y("price:Q", title="Spend ($)"),
                  tooltip=["Month", "price"]).properties(height=280))
    st.altair_chart(ch, use_container_width=True)
with col_b:
    st.markdown("**Spend by category**")
    cat = df[df["category"].astype(str).str.strip() != ""]
    if cat.empty:
        st.caption("No category info in this export.")
    else:
        g = cat.groupby("category")["price"].sum().sort_values(ascending=False).reset_index()
        ch = (alt.Chart(g).mark_bar()
              .encode(x=alt.X("price:Q", title="Spend ($)"),
                      y=alt.Y("category:N", sort="-x", title=None),
                      tooltip=["category", "price"]).properties(height=280))
        st.altair_chart(ch, use_container_width=True)

st.markdown("---")

# Superlatives
st.subheader("✨ Superlatives")
priced = df.dropna(subset=["price"])
biggest = priced.loc[priced["price"].idxmax()] if not priced.empty else None
top_cat = (df[df["category"].astype(str).str.strip() != ""]
           .groupby("category")["price"].sum().sort_values(ascending=False))
by_month = df.groupby("month_num")["price"].sum().sort_values(ascending=False)
busiest_month = MONTHS[int(by_month.index[0]) - 1] if not by_month.empty else "—"

g1, g2, g3 = st.columns(3)
g1.metric("Biggest purchase",
          (biggest["item"][:26] if biggest is not None else "—"),
          f"${biggest['price']:,.2f}" if biggest is not None else "")
g2.metric("Top category", top_cat.index[0] if not top_cat.empty else "—",
          f"${top_cat.iloc[0]:,.0f}" if not top_cat.empty else "")
g3.metric("Biggest spend month", busiest_month,
          f"${by_month.iloc[0]:,.0f}" if not by_month.empty else "")

# Most-bought item
item_counts = df.groupby("item")["quantity"].sum().sort_values(ascending=False)
if not item_counts.empty:
    st.markdown(f"**Most-bought item:** {item_counts.index[0]} "
                f"(×{int(item_counts.iloc[0])})")

st.markdown("---")
st.caption("Built with Streamlit + Altair. Everything runs in memory — nothing is uploaded or stored.")
