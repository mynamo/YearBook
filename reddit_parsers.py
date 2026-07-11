#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parsers for a Reddit data-request export (reddit.com/settings/data-request).

The export is a ZIP of CSVs; the two we use are `posts.csv` and `comments.csv`.
Both are normalized into one common "social" schema:

    ts          : datetime (UTC-naive)
    subreddit   : str
    kind        : "post" | "comment"
    text        : str  (post title, or comment body)
    score       : float (NaN — the GDPR export doesn't include vote counts)
    permalink   : str
    source      : "Reddit export"

`parse_social(filename, raw)` sniffs which CSV it is; `load_social_files` combines
several uploaded files.
"""

import io
import re

import pandas as pd

COLUMNS = ["ts", "subreddit", "kind", "text", "score", "permalink", "source"]


def _empty():
    return pd.DataFrame(columns=COLUMNS)


def _find_col(cols, *cands):
    norm = {re.sub(r"[^a-z0-9]", "", c.lower()): c for c in cols}
    for cand in cands:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        if key in norm:
            return norm[key]
    for cand in cands:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        for nk, orig in norm.items():
            if key and key in nk:
                return orig
    return None


def _clean_subreddit(val):
    s = str(val).strip()
    s = re.sub(r"^/?r/", "", s, flags=re.I)   # "r/python" -> "python"
    return s


def parse_posts(df):
    cols = list(df.columns)
    c_date = _find_col(cols, "date", "created", "timestamp")
    c_sub = _find_col(cols, "subreddit")
    c_title = _find_col(cols, "title", "body")
    c_link = _find_col(cols, "permalink", "url")
    if c_date is None:
        return _empty()
    out = pd.DataFrame({
        "ts": pd.to_datetime(df[c_date], errors="coerce", utc=True).dt.tz_localize(None),
        "subreddit": df[c_sub].map(_clean_subreddit) if c_sub else "",
        "kind": "post",
        "text": df[c_title].astype(str) if c_title else "",
        "score": float("nan"),
        "permalink": df[c_link].astype(str) if c_link else "",
        "source": "Reddit export",
    })
    return out[COLUMNS]


def parse_comments(df):
    cols = list(df.columns)
    c_date = _find_col(cols, "date", "created", "timestamp")
    c_sub = _find_col(cols, "subreddit")
    c_body = _find_col(cols, "body", "text")
    c_link = _find_col(cols, "permalink", "link")
    if c_date is None:
        return _empty()
    out = pd.DataFrame({
        "ts": pd.to_datetime(df[c_date], errors="coerce", utc=True).dt.tz_localize(None),
        "subreddit": df[c_sub].map(_clean_subreddit) if c_sub else "",
        "kind": "comment",
        "text": df[c_body].astype(str) if c_body else "",
        "score": float("nan"),
        "permalink": df[c_link].astype(str) if c_link else "",
        "source": "Reddit export",
    })
    return out[COLUMNS]


def parse_social(filename, raw):
    name = (filename or "").lower()
    text = raw.decode("utf-8-sig", errors="ignore")
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception:
        return _empty()
    if df.empty:
        return _empty()

    cols_lower = {c.lower() for c in df.columns}
    if "comment" in name or "body" in cols_lower and "title" not in cols_lower:
        parsed = parse_comments(df)
    elif "post" in name or "title" in cols_lower:
        parsed = parse_posts(df)
    else:
        # unknown Reddit CSV — try posts, then comments
        parsed = parse_posts(df)
        if parsed.empty:
            parsed = parse_comments(df)
    return parsed.dropna(subset=["ts"]).reset_index(drop=True)


def load_social_files(uploads):
    frames, report = [], []
    for up in uploads:
        raw = up.read()
        df = parse_social(up.name, raw)
        kind = "unrecognized"
        if len(df):
            kind = df["kind"].iloc[0] + "s"
        report.append((up.name, len(df), kind))
        if len(df):
            frames.append(df)
    if not frames:
        return _empty(), report
    combined = pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)
    return combined, report
