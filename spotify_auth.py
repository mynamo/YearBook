#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spotify "Connect" — live listening data via OAuth (Authorization Code flow).

No export needed: the user clicks a link, logs into Spotify, and we fetch their
top artists/tracks (last 4 weeks / 6 months / all time) and last 50 plays
straight from the Web API.

Credentials live in Streamlit secrets (never in code). Add a [spotify] section
to .streamlit/secrets.toml locally, or the Secrets box on Streamlit Cloud:

    [spotify]
    client_id = "your_client_id"
    client_secret = "your_client_secret"
    redirect_uri = "https://your-app.streamlit.app"

Scopes used: user-top-read, user-read-recently-played.
"""

import base64
import secrets as pysecrets
import time
import urllib.parse

import requests
import pandas as pd
import streamlit as st

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"
SCOPES = "user-top-read user-read-recently-played"

TIME_RANGES = {
    "Last 4 weeks": "short_term",
    "Last 6 months": "medium_term",
    "All time": "long_term",
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def get_config():
    """Return (client_id, client_secret, redirect_uri) or None if not set up."""
    try:
        cfg = st.secrets["spotify"]
        cid = cfg["client_id"]
        secret = cfg["client_secret"]
        redirect = cfg["redirect_uri"]
        if cid and secret and redirect:
            return cid, secret, redirect
    except Exception:
        pass
    return None


def is_configured():
    return get_config() is not None


# ---------------------------------------------------------------------------
# Auth URL + token exchange
# ---------------------------------------------------------------------------
def build_auth_url():
    cid, _, redirect = get_config()
    state = pysecrets.token_urlsafe(16)
    st.session_state["spotify_oauth_state"] = state
    params = {
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": redirect,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "false",
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def _basic_auth_header():
    cid, secret, _ = get_config()
    raw = f"{cid}:{secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def exchange_code(code):
    """Trade an authorization code for tokens. Returns token dict or raises."""
    _, _, redirect = get_config()
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
        },
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=15,
    )
    resp.raise_for_status()
    tok = resp.json()
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    return tok


def refresh_token(tok):
    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]},
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=15,
    )
    resp.raise_for_status()
    new = resp.json()
    tok["access_token"] = new["access_token"]
    tok["expires_at"] = time.time() + new.get("expires_in", 3600) - 60
    if "refresh_token" in new:
        tok["refresh_token"] = new["refresh_token"]
    return tok


def valid_access_token():
    """Return a currently-valid access token from session, refreshing if needed."""
    tok = st.session_state.get("spotify_token")
    if not tok:
        return None
    if time.time() >= tok.get("expires_at", 0) and "refresh_token" in tok:
        try:
            tok = refresh_token(tok)
            st.session_state["spotify_token"] = tok
        except Exception:
            return None
    return tok.get("access_token")


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------
def _get(path, token, params=None):
    resp = requests.get(
        API_BASE + path,
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_top_artists(token, time_range="medium_term", limit=20):
    data = _get("/me/top/artists", token, {"time_range": time_range, "limit": limit})
    out = []
    for rank, a in enumerate(data.get("items", []), start=1):
        out.append({
            "rank": rank,
            "artist": a.get("name", ""),
            "genres": ", ".join(a.get("genres", [])[:3]),
            "popularity": a.get("popularity"),
        })
    return pd.DataFrame(out)


def fetch_top_tracks(token, time_range="medium_term", limit=20):
    data = _get("/me/top/tracks", token, {"time_range": time_range, "limit": limit})
    out = []
    for rank, t in enumerate(data.get("items", []), start=1):
        artists = ", ".join(a["name"] for a in t.get("artists", []))
        out.append({
            "rank": rank,
            "track": t.get("name", ""),
            "artist": artists,
            "album": t.get("album", {}).get("name", ""),
            "popularity": t.get("popularity"),
        })
    return pd.DataFrame(out)


def fetch_me(token):
    try:
        me = _get("/me", token)
        return me.get("display_name") or me.get("id") or "your account"
    except Exception:
        return "your account"


def fetch_recently_played(token, limit=50):
    """Return the last <=50 plays normalized to the dashboard schema."""
    data = _get("/me/player/recently-played", token, {"limit": limit})
    rows = []
    for item in data.get("items", []):
        t = item.get("track", {}) or {}
        artists = ", ".join(a["name"] for a in t.get("artists", []))
        rows.append({
            "ts": item.get("played_at"),
            "artist": artists,
            "track": t.get("name", ""),
            "album": t.get("album", {}).get("name", ""),
            "ms_played": t.get("duration_ms"),
            "platform": "Spotify (recent)",
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True).dt.tz_localize(None)
    df["ms_played"] = pd.to_numeric(df["ms_played"], errors="coerce")
    return df[["ts", "artist", "track", "album", "ms_played", "platform"]]


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def handle_callback():
    """Call once near the top of the app. Exchanges ?code=... for a token."""
    if st.session_state.get("spotify_token"):
        return
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    if not code:
        return
    expected = st.session_state.get("spotify_oauth_state")
    if expected and state and state != expected:
        st.error("Spotify login state mismatch — please try connecting again.")
        st.query_params.clear()
        return
    try:
        tok = exchange_code(code)
        st.session_state["spotify_token"] = tok
    except Exception as e:
        st.error(f"Could not complete Spotify login: {e}")
    finally:
        st.query_params.clear()


def disconnect():
    st.session_state.pop("spotify_token", None)
    st.session_state.pop("spotify_oauth_state", None)
