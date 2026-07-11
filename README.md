# 🎁 Yearbook

Turn messy personal-data exports into a shareable year-in-review. A Streamlit
**multipage** app whose dashboards share one idea: normalize wildly different
export formats into a single clean schema, then visualize it.

- **🎧 Music** — Spotify, Apple Music, YouTube Music: top artists/tracks/albums,
  listening habits by month/day/hour, superlatives. **Connect Spotify** for
  instant charts, or upload exports for full history.
- **📚 Reading** — Goodreads, StoryGraph, Kindle: books read, pages, ratings,
  reading pace, and superlatives. Upload-first (reading exports are instant).
- **💬 Social** — Reddit: posts/comments over time, top subreddits, when you post,
  superlatives. **Connect Reddit** for live data (its free API allows personal
  use), or upload a data-request export.
- **🛍️ Shopping** — Amazon & Walmart order history: total spend, spend over time,
  top categories, biggest purchase. Upload-first (no personal-purchase API exists).

## Structure

```
Home.py                    # landing page + Spotify/Reddit OAuth callback handlers
pages/1_🎧_Music.py        # music dashboard
pages/2_📚_Reading.py      # reading dashboard
pages/3_💬_Social.py       # reddit dashboard
pages/4_🛍️_Shopping.py     # shopping dashboard
parsers.py / sample_data.py / spotify_auth.py          # music
reading_parsers.py / reading_sample.py                 # reading
reddit_parsers.py / reddit_sample.py / reddit_auth.py  # social (Reddit)
shopping_parsers.py / shopping_sample.py               # shopping (Amazon/Walmart)
requirements.txt
secrets.toml.example       # template for Spotify + Reddit credentials
```

## Run locally

```bash
pip install -r requirements.txt
python3 -m streamlit run Home.py
```

Both pages default to **sample data**, so it works immediately.

## Getting your data

**Music**
- Spotify — Account → Privacy → *Extended streaming history* (`*.json`), or just
  use **Connect Spotify** for live top charts.
- Apple Music — privacy.apple.com → *Apple Media Services* → `Apple Music Play Activity.csv`.
- YouTube Music — takeout.google.com → *YouTube and YouTube Music* → history → JSON.

**Reading**
- Goodreads — My Books → Import/Export → **Export Library** (CSV). This is the
  de-facto standard; StoryGraph and Fable both import it.
- StoryGraph — Manage Account → **Export StoryGraph library** (CSV).
- Kindle — Amazon's *Request Your Data* (Kindle) export; the generic CSV parser
  maps it best-effort.

There's no live API for any reading service (Goodreads' is deprecated; StoryGraph
and Fable have none), but every reading export downloads instantly, so upload is
all you need.

**Social (Reddit)**
- **Connect Reddit** — live login (its free API tier allows personal, non-commercial
  use). Create a *web app* at reddit.com/prefs/apps and add the `[reddit]` secrets.
- Export — reddit.com/settings/data-request → unzip → `posts.csv` + `comments.csv`.

**Shopping**
- Amazon — *Request My Data* → `Retail.OrderHistory` CSV.
- Walmart — account/order-history export. Note: X/Instagram/Amazon/Walmart have no
  personal-data API, so shopping is upload-only.

## Connect Spotify (optional, music page)

1. developer.spotify.com/dashboard → **Create app**.
2. Add a Redirect URI matching where the app runs, exactly:
   - Local: `http://127.0.0.1:8501`  (Spotify no longer allows `http://localhost`)
   - Deployed: `https://your-app-name.streamlit.app`
3. Put the Client ID/secret in secrets (see `secrets.toml.example`): create
   `.streamlit/secrets.toml` locally, or paste into the Secrets box on Streamlit Cloud.

New Spotify apps run in development mode: only accounts you allowlist can log in
(up to 25) and the owner needs Premium — fine for your own demo + a few testers.

## Connect Reddit (optional, social page)

1. reddit.com/prefs/apps → **create another app** → type **web app**.
2. Set the **redirect uri** to where the app runs (e.g. `http://localhost:8501`
   locally, or `https://your-app-name.streamlit.app` deployed).
3. Copy the client ID (under the app name) and secret into the `[reddit]` block in
   your secrets (see `secrets.toml.example`), plus a descriptive `user_agent`.

Reddit's free tier covers personal, non-commercial use, so no billing is needed.

## Deploy free on Streamlit Community Cloud

1. Push the whole folder to a GitHub repo (keep `secrets.toml` out — see `.gitignore`).
2. share.streamlit.io → New app → main file `Home.py` → Deploy.
3. Add your Spotify secrets in the app's Secrets box (optional).

Everything runs in memory; nothing is uploaded or stored — worth noting since it
handles personal data.
