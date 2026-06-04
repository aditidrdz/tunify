# Tunify — Same-Artist Music Recommendation System

A Spotify-style web app where **picking any song queues up only songs by that same artist next**. When the same-artist pool runs out, it smartly falls back to similar artists so the queue never feels empty.

Built with **Flask + Vanilla JS + CSS** — no external services, runs fully offline.

---

## Features

- **Strict same-artist recommendations** — pick a Darshan Raval song, get only Darshan Raval next.
- **Smart fallback** — when same-artist songs are exhausted, similar artists fill the queue.
- **Real album art + 30s previews** via the free [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) (no key needed). Cached locally to `data/enriched.json` after first run.
- **Real audio playback** with a HTML5 `<audio>` element — play/pause, next/prev, scrub bar, auto-advance to next song.
- **Spotify-inspired dark UI** — sidebar, top search, hero card, song grid, queue list, bottom player.
- **Search** songs / artists / albums in real time.
- **Browse by artist** — click any artist in the sidebar to see all their songs.
- **56 songs** across 10 popular artists (Indian + international) including Darshan Raval, Arijit Singh, Atif Aslam, Jubin Nautiyal, Armaan Malik, B Praak, Neha Kakkar, Ed Sheeran, Taylor Swift, The Weeknd.

---

## Project structure

```
recommdations system/
├── app.py                  # Flask app + recommendation logic
├── requirements.txt
├── README.md
├── data/
│   ├── songs.py            # Sample songs dataset + similar-artist map
│   ├── enrich.py           # iTunes Search API enrichment (artwork + previews)
│   └── enriched.json       # Generated cache (artwork + preview URLs per song)
├── templates/
│   └── index.html          # Main page
└── static/
    ├── css/style.css       # Spotify-style dark theme
    └── js/app.js           # Frontend logic (fetch, render, player)
```

---

## Setup & run (Windows / PowerShell)

```powershell
# 1. Create a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Then open <http://127.0.0.1:5000> in your browser.

> On macOS / Linux, replace step 1 with `python3 -m venv .venv && source .venv/bin/activate`.

### First-run note

On the very first start, the app fetches album artwork and 30-second audio previews
from the iTunes Search API for all 56 songs. This takes ~30–60 seconds and only
happens **once** — results are cached to `data/enriched.json` so subsequent
restarts are instant.

To rebuild the cache from scratch:

```powershell
python -m data.enrich --force
```

---

## How the recommendation logic works

The endpoint `GET /api/recommend/<song_id>` does the following:

1. Look up the seed song's **artist**.
2. Collect **all other songs by the same artist** (shuffled) → `same_artist`.
3. If still under the limit, walk the **`SIMILAR_ARTISTS` map** in `data/songs.py` and append their songs → `similar_artists`.
4. Return both lists separately so the UI can label them clearly:
   - **"More from <Artist>"** — strict same-artist recommendations
   - **"You might also like"** — similar-artist fallback

Example call:

```
GET /api/recommend/1
→ seed = "Tera Zikr" by Darshan Raval
→ same_artist = [Hawa Banke, Ek Tarfa, Baarish, Kaash Aisa Hota, Asal Mein, Naseeb Se, Chogada, Kamariya]
→ similar_artists = [songs by Jubin Nautiyal / Armaan Malik / Atif Aslam / Arijit Singh]
```

---

## API reference

| Method | Path                          | Description                                              |
|-------:|-------------------------------|----------------------------------------------------------|
| GET    | `/`                           | Main UI                                                  |
| GET    | `/api/songs?q=<query>`        | All songs (or filtered by `q`)                           |
| GET    | `/api/artists`                | All artists with song counts                             |
| GET    | `/api/recommend/<song_id>`    | Same-artist recommendations for the given song           |

---

## Extending it

- **Add more songs** — append to the `SONGS` list in `data/songs.py` (keep `id` unique), then run `python -m data.enrich` to fetch artwork + preview for the new entries.
- **Full-length audio** — iTunes only gives 30s previews. For full songs, plug in the Spotify Web Playback SDK or YouTube IFrame Player. Both require login/keys.
- **Switch to strict mode** — set `limit` very high and ignore `similar_artists` in the frontend.
- **Use a real dataset** — point `app.py` at a CSV / SQLite / Spotify API instead of the static list.

---

## Tech stack

- **Backend:** Flask 3.0
- **Frontend:** Vanilla JavaScript, CSS Grid + Flexbox, Inter font
- **Data:** In-memory Python list (no DB needed)
