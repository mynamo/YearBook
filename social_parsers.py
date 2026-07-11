#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parsers for social-media exports — Reddit, Twitter/X, and Instagram.

None of these offer a usable personal-data API (Reddit's works but is handled by
reddit_auth for live login; X is paywalled; Instagram has no personal API), so
this module reads their **export files** and normalizes them into one schema:

    ts          : datetime (UTC-naive)
    platform    : "Reddit" | "Twitter" | "Instagram"
    kind        : reddit post/comment · twitter tweet/reply/retweet · instagram post
    channel     : subreddit (Reddit) or "" (others)
    text        : post title / comment / tweet / caption
    engagement  : score or like count (NaN if the export omits it)
    permalink   : str
    source      : "<Platform> export"

Handles: Reddit `posts.csv` / `comments.csv`, Twitter `tweets.js` (or .json),
Instagram `posts_1.json` (Download-Your-Information).
"""

import io
import json
import re

import pandas as pd

COLUMNS = ["ts", "platform", "kind", "channel", "text", "engagement", "permalink", "source"]


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


# ---------------------------------------------------------------------------
# Reddit (posts.csv / comments.csv from the data-request export)
# ---------------------------------------------------------------------------
def _clean_sub(v):
    return re.sub(r"^/?r/", "", str(v).strip(), flags=re.I)


def parse_reddit_csv(df, filename=""):
    cols = list(df.columns)
    c_date = _find_col(cols, "date", "created", "timestamp")
    c_sub = _find_col(cols, "subreddit")
    c_link = _find_col(cols, "permalink", "url", "link")
    if c_date is None:
        return _empty()
    name = filename.lower()
    is_comment = ("comment" in name) or (
        _find_col(cols, "body") is not None and _find_col(cols, "title") is None)
    c_text = _find_col(cols, "body") if is_comment else _find_col(cols, "title", "body")
    out = pd.DataFrame({
        "ts": pd.to_datetime(df[c_date], errors="coerce", utc=True).dt.tz_localize(None),
        "platform": "Reddit",
        "kind": "comment" if is_comment else "post",
        "channel": df[c_sub].map(_clean_sub) if c_sub else "",
        "text": df[c_text].astype(str) if c_text else "",
        "engagement": float("nan"),
        "permalink": df[c_link].astype(str) if c_link else "",
        "source": "Reddit export",
    })
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Twitter / X  (tweets.js — a JS assignment wrapping a JSON array)
# ---------------------------------------------------------------------------
def parse_twitter(text):
    # tweets.js looks like: window.YTD.tweets.part0 = [ {...}, ... ]
    stripped = text.strip()
    if not stripped.startswith("["):
        eq = stripped.find("=")
        if eq != -1:
            stripped = stripped[eq + 1:]
    stripped = stripped.strip().rstrip(";").strip()
    try:
        data = json.loads(stripped)
    except Exception:
        return _empty()
    rows = []
    for entry in data:
        t = entry.get("tweet", entry) if isinstance(entry, dict) else {}
        created = t.get("created_at")
        full = t.get("full_text") or t.get("text") or ""
        if full.startswith("RT @"):
            kind = "retweet"
        elif t.get("in_reply_to_status_id_str") or t.get("in_reply_to_user_id"):
            kind = "reply"
        else:
            kind = "tweet"
        rows.append((created, "Twitter", kind, "", full,
                     pd.to_numeric(t.get("favorite_count"), errors="coerce"),
                     "", "Twitter export"))
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=COLUMNS)
    # Twitter archive uses e.g. "Wed Jun 01 20:15:00 +0000 2025"
    df["ts"] = pd.to_datetime(df["ts"], format="%a %b %d %H:%M:%S %z %Y",
                              errors="coerce", utc=True).dt.tz_localize(None)
    df["engagement"] = pd.to_numeric(df["engagement"], errors="coerce")
    return df.dropna(subset=["ts"])[COLUMNS]


# ---------------------------------------------------------------------------
# Instagram  (Download-Your-Information posts_*.json)
# ---------------------------------------------------------------------------
def parse_instagram(data):
    # Accept a top-level list, or {"posts": [...]}, etc.
    if isinstance(data, dict):
        for key in ("posts", "photos", "ig_posts"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        return _empty()

    rows = []
    for post in data:
        if not isinstance(post, dict):
            continue
        ts = post.get("creation_timestamp")
        caption = post.get("title") or ""
        media = post.get("media")
        if isinstance(media, list) and media:
            if ts is None:
                ts = media[0].get("creation_timestamp")
            if not caption:
                caption = media[0].get("title", "")
        if ts is None:
            continue
        rows.append((ts, "Instagram", "post", "", caption, float("nan"), "", "Instagram export"))
    if not rows:
        return _empty()
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["ts"] = pd.to_datetime(pd.to_numeric(df["ts"], errors="coerce"), unit="s", errors="coerce")
    return df.dropna(subset=["ts"])[COLUMNS]


# ---------------------------------------------------------------------------
# Detect + dispatch
# ---------------------------------------------------------------------------
def parse_social(filename, raw):
    name = (filename or "").lower()
    text = raw.decode("utf-8-sig", errors="ignore")

    if name.endswith(".csv"):
        try:
            df = pd.read_csv(io.StringIO(text))
        except Exception:
            return _empty()
        return parse_reddit_csv(df, name).dropna(subset=["ts"]).reset_index(drop=True)

    if name.endswith(".js") or "tweet" in name:
        return parse_twitter(text).reset_index(drop=True)

    if name.endswith(".json"):
        # could be Twitter (tweets.json) or Instagram
        try:
            data = json.loads(text)
        except Exception:
            return parse_twitter(text).reset_index(drop=True)  # maybe a JS-wrapped file
        if isinstance(data, list) and data and isinstance(data[0], dict) and "tweet" in data[0]:
            return parse_twitter(text).reset_index(drop=True)
        return parse_instagram(data).reset_index(drop=True)

    return _empty()


def load_social_files(uploads):
    frames, report = [], []
    for up in uploads:
        raw = up.read()
        df = parse_social(up.name, raw)
        plat = df["platform"].iloc[0] if len(df) else "unrecognized"
        report.append((up.name, len(df), plat))
        if len(df):
            frames.append(df)
    if not frames:
        return _empty(), report
    combined = pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)
    return combined, report
