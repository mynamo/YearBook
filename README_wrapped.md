# 🎧 Streaming Wrapped — platform-agnostic listening dashboard

Upload your **Spotify**, **Apple Music**, and/or **YouTube Music** history exports —
mix and match all three at once — and get a personal "Wrapped": top artists, tracks
and albums; how your listening moves through the year, week, and day; and a set of
fun superlatives. Comes with realistic sample data so it works before you export
anything.

The interesting engineering here is that every service exports a **different messy
format**, and the app normalizes them into one schema
(`ts, artist, track, album, ms_played, platform`) before any analysis runs.

## Files

Three ways to feed it data: **sample mode** (instant demo), **Connect Spotify**
(live top charts via login — no export needed), and **file upload** (full history
for any of the three platforms).

## Files

| File | Purpose |
|------|---------|
| `streaming_wrapped.py` | The Streamlit dashboard (charts + superlatives + Spotify live). |
| `parsers.py` | Normalizes each platform's export into the common schema. |
| `sample_data.py` | Generates realistic listening data for the demo mode. |
| `spotify_auth.py` | Spotify OAuth login + live top-artists/tracks/recent-plays. |
| `requirements_wrapped.txt` | Dependencies (rename to `requirements.txt` in your repo). |
| `secrets.toml.example` | Template for your Spotify credentials. |

## Run locally

```bash
pip install -r requirements_wrapped.txt
streamlit run streaming_wrapped.py
```

Opens at http://localhost:8501. Pick **Use sample data** in the sidebar to explore instantly.

## How to get each export

**Spotify** — Account → Privacy settings → request **Extended streaming history**.
Arrives by email in a few days as `Streaming_History_Audio_*.json`. (The older basic
`StreamingHistory*.json` also works.)

**Apple Music** — Go to **privacy.apple.com** → *Request a copy of your data* →
select **Apple Media Services information**. Unzip and find
`Apple Music Play Activity.csv`.

**YouTube Music** — Go to **takeout.google.com** → Deselect all → check only
**YouTube and YouTube Music** → *All YouTube data included* → keep only **history** →
set the format to **JSON** → export. Your file is
`Takeout/YouTube and YouTube Music/history/watch-history.json`.

Then in the app choose **Upload my exports** and drop in any combination of these files.

## Connect Spotify (instant, no export)

Lets a user log in and see their top artists/tracks (last 4 weeks / 6 months / all
time) plus last 50 plays immediately. One-time setup:

1. Go to **developer.spotify.com/dashboard** → **Create app**.
2. Add a **Redirect URI** that matches where the app runs, exactly:
   - Local: `http://127.0.0.1:8501` (Spotify no longer allows `http://localhost`)
   - Deployed: `https://your-app-name.streamlit.app`
3. Copy the **Client ID** and **Client secret** into your secrets:
   - Local: create `.streamlit/secrets.toml` from `secrets.toml.example`.
   - Cloud: paste the same `[spotify]` block into the app's **Secrets** box.
4. Reload the app and pick **Connect Spotify (live)** in the sidebar.

Two limits worth knowing (Spotify's rules, not the app's): a new app runs in
**development mode**, so only Spotify accounts you add under *User Management* in the
dashboard can log in (up to 25) until you request extended quota; and the app owner
needs a **Spotify Premium** account. Perfect for demoing with your own account and a
few testers.

## Deploy free on Streamlit Community Cloud

1. Create a GitHub repo and add `streaming_wrapped.py`, `parsers.py`, `sample_data.py`,
   and a `requirements.txt` (rename `requirements_wrapped.txt` to exactly `requirements.txt`).
2. Go to **share.streamlit.io** → sign in with GitHub → **New app**.
3. Choose the repo, branch `main`, main file `streaming_wrapped.py`, **Deploy**.

A note for your portfolio writeup: everything runs in-memory and nothing is uploaded
anywhere, so it's safe to share publicly — a good thing to mention since it uses personal data.

## Notes

- Hours listened use each play's reported duration. YouTube Music exports have no
  duration, so those plays are estimated from your median track length.
- The "min seconds to count as a play" slider filters quick skips.
