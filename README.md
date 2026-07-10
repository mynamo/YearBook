# 🎁 Yearbook

Turn messy personal-data exports into a shareable year-in-review. A Streamlit
**multipage** app with two dashboards that share one idea: normalize wildly
different export formats into a single clean schema, then visualize it.

- **🎧 Music** — Spotify, Apple Music, YouTube Music: top artists/tracks/albums,
  listening habits by month/day/hour, superlatives. **Connect Spotify** for
  instant charts, or upload exports for full history.
- **📚 Reading** — Goodreads, StoryGraph, Kindle: books read, pages, ratings,
  reading pace, and superlatives. Upload-first (reading exports are instant).

## Structure

```
Home.py                    # landing page + Spotify OAuth callback handler
pages/1_🎧_Music.py        # music dashboard
pages/2_📚_Reading.py      # reading dashboard
parsers.py                 # music export parsers (Spotify/Apple/YouTube)
sample_data.py             # music demo data
spotify_auth.py            # Spotify OAuth + live top charts
reading_parsers.py         # reading export parsers (Goodreads/StoryGraph/Kindle)
reading_sample.py          # reading demo data
requirements.txt
secrets.toml.example       # template for Spotify credentials
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run Home.py
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

## Connect Spotify (optional, music page)

1. developer.spotify.com/dashboard → **Create app**.
2. Add a Redirect URI matching where the app runs, exactly:
   - Local: `http://127.0.0.1:8501`  (Spotify no longer allows `http://localhost`)
   - Deployed: `https://your-app-name.streamlit.app`
3. Put the Client ID/secret in secrets (see `secrets.toml.example`): create
   `.streamlit/secrets.toml` locally, or paste into the Secrets box on Streamlit Cloud.

New Spotify apps run in development mode: only accounts you allowlist can log in
(up to 25) and the owner needs Premium — fine for your own demo + a few testers.

## Deploy free on Streamlit Community Cloud

1. Push the whole folder to a GitHub repo (keep `secrets.toml` out — see `.gitignore`).
2. share.streamlit.io → New app → main file `Home.py` → Deploy.
3. Add your Spotify secrets in the app's Secrets box (optional).

Everything runs in memory; nothing is uploaded or stored — worth noting since it
handles personal data.
