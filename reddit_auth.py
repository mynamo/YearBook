#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reddit "Connect" — live personal data via OAuth (Authorization Code flow).

Reddit's free API tier allows non-commercial, personal use, so a visitor can log
in and we read *their own* recent posts and comments — no export/wait needed.

Credentials live in Streamlit secrets (never in code). Add a [reddit] section to
.streamlit/secrets.toml locally, or the Secrets box on Streamlit Cloud:

    [reddit]
    client_id = "your_app_client_id"
    client_secret = "your_app_secret"
    redirect_uri = "http://localhost:8501"      # must match your Reddit app
    user_agent = "yearbook-wrapped/1.0 by u/yourname"

Create the app at https://www.reddit.com/prefs/apps (type: "web app").
Scopes used: identity, history, read.
"""

import base64
import secrets as pysecrets
import time
import urllib.parse

import requests
import pandas as pd
import streamlit as st

AUTH_URL = "https://www.reddit.com/api/v1/authorize"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"
SCOPES = "identity history read"

SOCIAL_COLUMNS = ["ts", "subreddit", "kind", "text", "score", "permalink", "source"]


def get_config():
    try:
        cfg = st.secrets["reddit"]
        cid, secret, redirect = cfg["client_id"], cfg["client_secret"], cfg["redirect_uri"]
        if cid and secret and redirect:
            ua = cfg.get("user_agent", "yearbook-wrapped/1.0")
            return cid, secret, redirect, ua
    except Exception:
        pass
    return None


def is_configured():
    return get_config() is not None


def _ua():
    cfg = get_config()
    return cfg[3] if cfg else "yearbook-wrapped/1.0"


def build_auth_url():
    cid, _, redirect, _ = get_config()
    state = pysecrets.token_urlsafe(16)
    st.session_state["reddit_oauth_state"] = state
    params = {
        "client_id": cid,
        "response_type": "code",
        "state": state,
        "redirect_uri": redirect,
        "duration": "temporary",
        "scope": SCOPES,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def _basic_auth():
    cid, secret, _, _ = get_config()
    return "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode()


def exchange_code(code):
    _, _, redirect, ua = get_config()
    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect},
        headers={"Authorization": _basic_auth(), "User-Agent": ua},
        timeout=15,
    )
    resp.raise_for_status()
    tok = resp.json()
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    return tok


def valid_access_token():
    tok = st.session_state.get("reddit_token")
    if not tok:
        return None
    if time.time() >= tok.get("expires_at", 0):
        return None  # temporary token expired — reconnect
    return tok.get("access_token")


def _get(path, token, params=None):
    resp = requests.get(
        API_BASE + path,
        headers={"Authorization": f"bearer {token}", "User-Agent": _ua()},
        params=params or {},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_me(token):
    try:
        return _get("/api/v1/me", token).get("name", "your account")
    except Exception:
        return "your account"


def _rows_from_listing(listing):
    rows = []
    for child in listing.get("data", {}).get("children", []):
        kind = child.get("kind")
        d = child.get("data", {})
        ts = d.get("created_utc")
        sub = d.get("subreddit", "")
        permalink = "https://www.reddit.com" + d.get("permalink", "") if d.get("permalink") else ""
        if kind == "t3":       # post
            rows.append((ts, sub, "post", d.get("title", ""), d.get("score"), permalink))
        elif kind == "t1":     # comment
            rows.append((ts, sub, "comment", d.get("body", ""), d.get("score"), permalink))
    return rows


def fetch_recent(token, username, limit=100):
    """Fetch the user's recent posts + comments, normalized to the social schema."""
    rows = []
    for path in (f"/user/{username}/submitted", f"/user/{username}/comments"):
        try:
            data = _get(path, token, {"limit": limit})
            rows += _rows_from_listing(data)
        except Exception:
            continue
    if not rows:
        return pd.DataFrame(columns=SOCIAL_COLUMNS)
    df = pd.DataFrame(rows, columns=["ts", "subreddit", "kind", "text", "score", "permalink"])
    df["ts"] = pd.to_datetime(df["ts"], unit="s", errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["source"] = "Reddit (live)"
    return df[SOCIAL_COLUMNS].dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)


def handle_callback():
    """Call once near the top of the app to complete the OAuth redirect."""
    if st.session_state.get("reddit_token"):
        return
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    if not code:
        return
    expected = st.session_state.get("reddit_oauth_state")
    if expected and state and state != expected:
        st.error("Reddit login state mismatch — please try connecting again.")
        st.query_params.clear()
        return
    try:
        st.session_state["reddit_token"] = exchange_code(code)
    except Exception as e:
        st.error(f"Could not complete Reddit login: {e}")
    finally:
        st.query_params.clear()


def disconnect():
    st.session_state.pop("reddit_token", None)
    st.session_state.pop("reddit_oauth_state", None)
