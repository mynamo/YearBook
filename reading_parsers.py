#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform-agnostic parsers for reading-history exports.

Normalizes Goodreads, StoryGraph, and generic/Kindle CSV exports into one
common schema:

    title      : str
    author     : str
    rating     : float  (your 1-5 rating; NaN if unrated)
    pages      : float  (page count; NaN if unknown)
    date_read  : datetime (NaN if not finished / no date)
    date_added : datetime (NaN if unknown)
    shelf      : str  ("read" | "currently-reading" | "to-read" | "dnf")
    platform   : str  ("Goodreads" | "StoryGraph" | "Kindle/Other")

Goodreads' CSV is the de-facto standard (StoryGraph and Fable both import it),
so it's the primary format. `parse_reading(filename, raw_bytes)` sniffs the
export type and dispatches. `load_reading_files(uploads)` combines several.
"""

import io
import re

import pandas as pd

COLUMNS = ["title", "author", "rating", "pages", "date_read", "date_added", "shelf", "platform"]


def _empty():
    return pd.DataFrame(columns=COLUMNS)


def _find_col(cols, *candidates):
    norm = {re.sub(r"[^a-z0-9]", "", c.lower()): c for c in cols}
    for cand in candidates:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        if key in norm:
            return norm[key]
    for cand in candidates:  # loose contains fallback
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        for nk, orig in norm.items():
            if key and key in nk:
                return orig
    return None


def _norm_shelf(val):
    s = str(val).strip().lower()
    if s in ("read", "finished"):
        return "read"
    if "currently" in s or "reading" == s:
        return "currently-reading"
    if "to-read" in s or "to read" in s or "want" in s:
        return "to-read"
    if "did-not-finish" in s or "dnf" in s or "did not finish" in s:
        return "dnf"
    return s or "read"


# ---------------------------------------------------------------------------
# Goodreads
# ---------------------------------------------------------------------------
def parse_goodreads(df):
    cols = list(df.columns)
    c_title = _find_col(cols, "Title")
    c_author = _find_col(cols, "Author", "Author l-f")
    c_rating = _find_col(cols, "My Rating")
    c_pages = _find_col(cols, "Number of Pages")
    c_read = _find_col(cols, "Date Read")
    c_added = _find_col(cols, "Date Added")
    c_shelf = _find_col(cols, "Exclusive Shelf")

    rating = pd.to_numeric(df[c_rating], errors="coerce") if c_rating else float("nan")
    if c_rating is not None:
        rating = rating.where(rating > 0)  # Goodreads uses 0 for "no rating"

    out = pd.DataFrame({
        "title": df[c_title].astype(str) if c_title else "",
        "author": df[c_author].astype(str) if c_author else "",
        "rating": rating,
        "pages": pd.to_numeric(df[c_pages], errors="coerce") if c_pages else float("nan"),
        "date_read": pd.to_datetime(df[c_read], errors="coerce") if c_read else pd.NaT,
        "date_added": pd.to_datetime(df[c_added], errors="coerce") if c_added else pd.NaT,
        "shelf": df[c_shelf].map(_norm_shelf) if c_shelf else "read",
        "platform": "Goodreads",
    })
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# StoryGraph
# ---------------------------------------------------------------------------
def parse_storygraph(df):
    cols = list(df.columns)
    c_title = _find_col(cols, "Title")
    c_author = _find_col(cols, "Authors", "Author")
    c_rating = _find_col(cols, "Star Rating")
    c_pages = _find_col(cols, "Pages", "Number of Pages")
    c_read = _find_col(cols, "Last Date Read", "Dates Read")
    c_added = _find_col(cols, "Date Added")
    c_status = _find_col(cols, "Read Status")

    out = pd.DataFrame({
        "title": df[c_title].astype(str) if c_title else "",
        "author": df[c_author].astype(str) if c_author else "",
        "rating": pd.to_numeric(df[c_rating], errors="coerce") if c_rating else float("nan"),
        "pages": pd.to_numeric(df[c_pages], errors="coerce") if c_pages else float("nan"),
        "date_read": pd.to_datetime(df[c_read], errors="coerce") if c_read else pd.NaT,
        "date_added": pd.to_datetime(df[c_added], errors="coerce") if c_added else pd.NaT,
        "shelf": df[c_status].map(_norm_shelf) if c_status else "read",
        "platform": "StoryGraph",
    })
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Generic / Kindle fallback (fuzzy column matching)
# ---------------------------------------------------------------------------
def parse_generic(df):
    cols = list(df.columns)
    c_title = _find_col(cols, "Title", "Book Name", "ASIN Title", "Product Name")
    c_author = _find_col(cols, "Author", "Authors", "Author Name")
    if c_title is None:
        return _empty()
    c_rating = _find_col(cols, "My Rating", "Rating", "Star Rating")
    c_pages = _find_col(cols, "Number of Pages", "Pages", "Page Count")
    c_read = _find_col(cols, "Date Read", "Last Read", "Read Date", "Finished")
    c_added = _find_col(cols, "Date Added", "Acquired", "Purchase Date", "Date")

    out = pd.DataFrame({
        "title": df[c_title].astype(str),
        "author": df[c_author].astype(str) if c_author else "",
        "rating": pd.to_numeric(df[c_rating], errors="coerce") if c_rating else float("nan"),
        "pages": pd.to_numeric(df[c_pages], errors="coerce") if c_pages else float("nan"),
        "date_read": pd.to_datetime(df[c_read], errors="coerce") if c_read else pd.NaT,
        "date_added": pd.to_datetime(df[c_added], errors="coerce") if c_added else pd.NaT,
        "shelf": "read",
        "platform": "Kindle/Other",
    })
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Detect + dispatch
# ---------------------------------------------------------------------------
def parse_reading(filename, raw):
    text = raw.decode("utf-8-sig", errors="ignore")
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception:
        return _empty()
    if df.empty:
        return _empty()

    cols_lower = {c.lower() for c in df.columns}
    # Goodreads signature
    if "exclusive shelf" in cols_lower or "my rating" in cols_lower:
        parsed = parse_goodreads(df)
    # StoryGraph signature
    elif "read status" in cols_lower or "star rating" in cols_lower:
        parsed = parse_storygraph(df)
    else:
        parsed = parse_generic(df)

    parsed = parsed[parsed["title"].astype(str).str.strip().replace("nan", "") != ""]
    return parsed.reset_index(drop=True)


def load_reading_files(uploads):
    frames, report = [], []
    for up in uploads:
        raw = up.read()
        df = parse_reading(up.name, raw)
        report.append((up.name, len(df),
                       df["platform"].iloc[0] if len(df) else "unrecognized"))
        if len(df):
            frames.append(df)
    if not frames:
        return _empty(), report
    combined = pd.concat(frames, ignore_index=True)
    # De-dupe the same book showing up from two services (by title+author).
    combined["_key"] = (combined["title"].str.lower().str.strip() + "|" +
                        combined["author"].str.lower().str.strip())
    combined = combined.sort_values("date_read").drop_duplicates("_key", keep="last")
    combined = combined.drop(columns="_key").reset_index(drop=True)
    return combined, report
