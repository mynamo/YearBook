#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform-agnostic parsers for music streaming history exports.

Each service exports a different messy format. These functions normalize
Spotify, Apple Music, and YouTube Music exports into one common schema:

    ts         : pandas datetime (UTC-naive)
    artist     : str
    track      : str
    album      : str  (may be "" if the export doesn't include it)
    ms_played  : float (milliseconds; NaN if the export doesn't report it)
    platform   : str  ("Spotify" | "Apple Music" | "YouTube Music")

The public entry point is `parse_any(filename, raw_bytes)`, which sniffs the
format and dispatches to the right parser. `load_files(list_of_uploads)` runs
`parse_any` over several files and concatenates the result.
"""

import io
import json
import re

import pandas as pd

COLUMNS = ["ts", "artist", "track", "album", "ms_played", "platform"]


def _empty():
    return pd.DataFrame(columns=COLUMNS)


# ---------------------------------------------------------------------------
# Spotify
# ---------------------------------------------------------------------------
# Two shapes exist:
#   * "Extended Streaming History": ts, ms_played,
#       master_metadata_track_name / _album_artist_name / _album_album_name
#   * Basic "Account data" StreamingHistory*.json:
#       endTime, artistName, trackName, msPlayed
def parse_spotify(records):
    rows = []
    for r in records:
        if not isinstance(r, dict):
            continue
        if "master_metadata_track_name" in r or "ms_played" in r:
            track = r.get("master_metadata_track_name")
            if not track:  # podcast episodes / empty rows -> skip
                continue
            rows.append({
                "ts": r.get("ts"),
                "artist": r.get("master_metadata_album_artist_name") or "",
                "track": track,
                "album": r.get("master_metadata_album_album_name") or "",
                "ms_played": r.get("ms_played"),
                "platform": "Spotify",
            })
        elif "trackName" in r or "endTime" in r:
            rows.append({
                "ts": r.get("endTime"),
                "artist": r.get("artistName") or "",
                "track": r.get("trackName") or "",
                "album": "",
                "ms_played": r.get("msPlayed"),
                "platform": "Spotify",
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return _empty()
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True).dt.tz_localize(None)
    df["ms_played"] = pd.to_numeric(df["ms_played"], errors="coerce")
    return df[COLUMNS]


# ---------------------------------------------------------------------------
# Apple Music
# ---------------------------------------------------------------------------
# "Apple Music Play Activity.csv". Column names vary across exports, so match
# them case/space-insensitively rather than assuming exact headers.
def _find_col(cols, *candidates):
    norm = {re.sub(r"[^a-z0-9]", "", c.lower()): c for c in cols}
    for cand in candidates:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        if key in norm:
            return norm[key]
    # loose contains-match fallback
    for cand in candidates:
        key = re.sub(r"[^a-z0-9]", "", cand.lower())
        for nk, orig in norm.items():
            if key in nk:
                return orig
    return None


def parse_apple(text):
    df = pd.read_csv(io.StringIO(text))
    cols = list(df.columns)

    c_song = _find_col(cols, "Song Name", "Track Name", "Content Name", "Title")
    c_artist = _find_col(cols, "Artist Name", "Artist")
    c_album = _find_col(cols, "Album Name", "Album")
    c_ms = _find_col(cols, "Play Duration Milliseconds", "Media Duration In Milliseconds")
    c_ts = _find_col(cols, "Event Start Timestamp", "Event End Timestamp",
                     "Play Date Time", "Last Played Date")

    if c_song is None or c_ts is None:
        return _empty()

    out = pd.DataFrame({
        "ts": pd.to_datetime(df[c_ts], errors="coerce", utc=True).dt.tz_localize(None),
        "artist": df[c_artist].astype(str) if c_artist else "",
        "track": df[c_song].astype(str),
        "album": df[c_album].astype(str) if c_album else "",
        "ms_played": pd.to_numeric(df[c_ms], errors="coerce") if c_ms else float("nan"),
        "platform": "Apple Music",
    })
    out = out[out["track"].notna() & (out["track"].str.strip() != "") & (out["track"] != "nan")]
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# YouTube Music (Google Takeout watch-history.json)
# ---------------------------------------------------------------------------
# Music entries have header == "YouTube Music". Title looks like
# "Watched <song>"; the first subtitle is the artist/channel. No play duration.
def parse_youtube(records):
    rows = []
    for r in records:
        if not isinstance(r, dict):
            continue
        if r.get("header") != "YouTube Music":
            continue
        title = r.get("title", "")
        track = re.sub(r"^Watched\s+", "", title).strip()
        if not track:
            continue
        artist = ""
        subs = r.get("subtitles")
        if isinstance(subs, list) and subs:
            artist = subs[0].get("name", "")
        # channel names often end in " - Topic" for auto-generated artist channels
        artist = re.sub(r"\s*-\s*Topic$", "", artist).strip()
        rows.append({
            "ts": r.get("time"),
            "artist": artist,
            "track": track,
            "album": "",
            "ms_played": float("nan"),  # Takeout doesn't report duration
            "platform": "YouTube Music",
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return _empty()
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True).dt.tz_localize(None)
    return df[COLUMNS]


# ---------------------------------------------------------------------------
# YouTube (Music) — CSV from converting Takeout watch-history.html
# Columns: platform, title, channel, url, timestamp
# ---------------------------------------------------------------------------
def parse_youtube_csv(df):
    cols = {c.lower(): c for c in df.columns}
    c_title = cols.get("title")
    c_ts = cols.get("timestamp") or cols.get("time") or cols.get("date")
    c_channel = cols.get("channel")
    c_plat = cols.get("platform")
    if c_title is None or c_ts is None:
        return _empty()

    # Timestamps look like "Jul 10, 2026, 12:18:32 PM PDT" — drop the trailing
    # timezone abbreviation (pandas can't parse named zones) then parse.
    ts_raw = df[c_ts].astype(str).str.replace(r"\s+[A-Z]{2,4}$", "", regex=True)
    ts = pd.to_datetime(ts_raw, errors="coerce")

    if c_channel:
        artist = (df[c_channel].fillna("").astype(str)
                  .str.replace(r"\s*-\s*Topic$", "", regex=True).str.strip())
        artist = artist.mask(artist == "", "(unknown channel)")
    else:
        artist = "(unknown channel)"

    out = pd.DataFrame({
        "ts": ts,
        "artist": artist,
        "track": df[c_title].astype(str),
        "album": "",
        "ms_played": float("nan"),   # watch history has no duration
        "platform": df[c_plat].fillna("YouTube").astype(str) if c_plat else "YouTube",
    })
    out = out[out["track"].notna() & (out["track"].str.strip() != "") & (out["track"] != "nan")]
    out = out.dropna(subset=["ts"])

    # This is the Music page — keep just the YouTube Music rows so the dashboard
    # is actual music, not talk shows/ads. Fall back to everything if the export
    # has no music rows tagged.
    music = out[out["platform"] == "YouTube Music"]
    if not music.empty:
        out = music
    return out[COLUMNS]


# ---------------------------------------------------------------------------
# Auto-detect + dispatch
# ---------------------------------------------------------------------------
def parse_any(filename, raw):
    """filename: str, raw: bytes. Returns a normalized DataFrame (may be empty)."""
    name = (filename or "").lower()
    text = raw.decode("utf-8-sig", errors="ignore")

    # CSV -> YouTube watch-history CSV, else Apple Music
    if name.endswith(".csv"):
        try:
            df = pd.read_csv(io.StringIO(text))
        except Exception:
            return _empty()
        cl = {c.lower() for c in df.columns}
        if {"title", "timestamp"} <= cl or {"platform", "channel"} <= cl:
            return parse_youtube_csv(df)
        return parse_apple(text)

    # JSON -> Spotify or YouTube
    if name.endswith(".json"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # some Spotify basic exports are JSON-lines
            data = []
            for line in text.splitlines():
                line = line.strip().rstrip(",")
                if line and line[0] == "{":
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data:
            return _empty()
        sample = next((r for r in data if isinstance(r, dict)), {})
        if "header" in sample or "titleUrl" in sample:
            return parse_youtube(data)
        return parse_spotify(data)

    return _empty()


def load_files(uploads):
    """uploads: list of objects with .name and .read(). Returns combined df + report."""
    frames = []
    report = []
    for up in uploads:
        raw = up.read()
        df = parse_any(up.name, raw)
        report.append((up.name, len(df),
                       df["platform"].iloc[0] if len(df) else "unrecognized"))
        if len(df):
            frames.append(df)
    if not frames:
        return _empty(), report
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["ts"])
    combined = combined[combined["track"].astype(str).str.strip() != ""]
    combined = combined.sort_values("ts").reset_index(drop=True)
    return combined, report
