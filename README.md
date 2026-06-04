# 🎵 Tunify — Same-Artist Music Recommendation System

A Spotify-style web app where **picking any song queues up only songs by the same artist next**. Pick a Darshan Raval song → the whole queue is Darshan Raval. Pick an Arijit Singh song → the whole queue is Arijit Singh. No mixing, no surprises.

Built with **Flask + vanilla JS + CSS**. Uses the **iTunes Search API** for album art and the **YouTube** catalog (via `yt-dlp`) for full-length audio playback.

🔗 **Repo:** https://github.com/aditidrdz/tunify

---

## 📸 Screenshots

### Logged-in home — 56 songs across 10 artists, real album art from iTunes
![Home page](docs/screenshots/home.png)

### Same-artist queue in action — pick *Tera Zikr*, get 18 more Darshan Raval songs
![Slide-in queue panel](docs/screenshots/queue.png)

### Now playing with full-length audio (streamed from YouTube)
![Now playing](docs/screenshots/player.png)

<table>
<tr>
<td width="50%">

**Live search across iTunes**
![Search results](docs/screenshots/search.png)

</td>
<td width="50%">

**Liked Songs — per-user, server-side**
![Liked songs](docs/screenshots/liked.png)

</td>
</tr>
<tr>
<td width="50%">

**Sign in**
![Login page](docs/screenshots/login.png)

</td>
<td width="50%">

**Sign up**
![Signup page](docs/screenshots/signup.png)

</td>
</tr>
</table>

---

## ✨ Features

- 🎯 **Strict same-artist recommendations** — once you pick a song, every recommendation is by that same artist.
- 🌐 **Live iTunes catalog search** — works for any song/artist in the world, not just a hardcoded list.
- 🖼️ **Real album art** via the [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) (no key required).
- ▶️ **Full-length audio playback** by extracting direct audio streams from YouTube using `yt-dlp` (audio-only — no video popup).
- 🔁 **Smart fallback** — if YouTube audio fails, it gracefully drops to the iTunes 30-second preview.
- 👤 **User accounts** — sign up / log in / log out. Passwords are hashed with Werkzeug (never plaintext).
- ❤️ **Liked Songs** — heart any song and find it later in a dedicated sidebar tab. Liked songs are stored per-user, server-side.
- 🗃️ **Pluggable user storage** — uses MongoDB if `MONGODB_URI` is set, otherwise falls back to a JSON file. No code change required.
- 🎨 **Spotify-inspired dark UI** — sidebar, top search, hero card, song grid, slide-in queue panel, and a bottom player bar.

---

## 🚀 Quick start (for anyone cloning this repo)

### Prerequisites
- **Python 3.10 or newer** ([download](https://www.python.org/downloads/))
- **Git** ([download](https://git-scm.com/downloads))
- An internet connection on first run (to fetch album art and YouTube audio)
- *Optional:* a free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) account if you want cloud-stored user accounts

### 1. Clone the repo
```bash
git clone https://github.com/aditidrdz/tunify.git
cd tunify
```

### 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

> If PowerShell blocks the activation script, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure MongoDB
If you want user accounts stored in MongoDB Atlas instead of a local JSON file:

1. Copy `.env.example` to `.env`
2. Set `MONGODB_URI` to your Atlas connection string
3. (Skip this step entirely if you just want to try the app locally — it'll use `data/users.json`.)

### 5. Run the app
```bash
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

> **First-run note:** The first time you start the app, it spends ~30–60 seconds fetching album art and audio previews for the 56 bundled songs from the iTunes API. Results are cached to `data/enriched.json` so subsequent restarts are instant.

### 6. Sign up and start playing
- Click **"Don't have an account? Sign up"** on the login page
- Pick any artist or song
- Watch the queue auto-fill with songs by that same artist

---

## 📁 Project structure

```
tunify/
├── app.py                          # Flask app + routes + recommendation logic
├── requirements.txt                # Python dependencies
├── .env.example                    # Template for environment variables
├── .gitignore                      # Excludes secrets, caches, __pycache__
├── README.md
│
├── data/
│   ├── songs.py                    # 56-song seed dataset + similar-artist map
│   ├── enrich.py                   # iTunes API → album art + 30s previews
│   ├── youtube.py                  # yt-dlp → YouTube video IDs + audio URLs
│   ├── users.py                    # User auth + liked songs (Mongo OR JSON)
│   ├── migrate_users_to_mongo.py   # One-time JSON → Mongo migration script
│   └── (generated at runtime)      # enriched.json, youtube_ids.json, users.json
│
├── templates/
│   ├── index.html                  # Main player UI
│   └── login.html                  # Login / signup page
│
├── static/
│   ├── css/style.css               # Spotify-style dark theme
│   └── js/app.js                   # Frontend logic (fetch, render, playback)
│
├── tools/
│   └── take_screenshots.py         # Playwright script that regenerates README images
│
└── docs/
    └── screenshots/                # PNGs embedded in this README
```

---

## 🧠 How the recommendation logic works

When you click a song, the frontend calls `GET /api/recommend/<song_id>`:

1. The seed song's **artist** is identified (handles multi-artist credits like *"A, B & C"* by splitting them).
2. The local 56-song catalog is searched for **other songs by the same artist**.
3. The iTunes Search API is queried for **more songs by that same artist** to top up the queue (target: ~20+ songs).
4. Results are deduplicated by `(title, artist)` and returned.
5. The queue UI labels it **"More from \<Artist\>"** and plays them in sequence.

**No similar-artist fallback** — by user requirement, the queue is strictly same-artist. When the artist's catalog is exhausted, the queue simply ends.

---

## 🎧 How audio playback works

```
User clicks a song
  ↓
Backend: GET /api/play/<song_id>
  ↓
1. Look up the song's title + artist
2. yt-dlp searches YouTube for "<title> <artist> audio"
3. yt-dlp extracts the direct audio stream URL (m4a preferred)
4. Return the URL to the frontend
  ↓
Frontend: <audio src="..."> plays it natively in the browser
  ↓
If YouTube audio fails → fall back to iTunes 30-second preview
```

No YouTube IFrame player, no visible video popup — just clean audio.

---

## 🔌 API reference

All `/api/*` routes require an authenticated session.

| Method | Path                       | Description                                     |
|-------:|----------------------------|-------------------------------------------------|
| GET    | `/`                        | Main UI (redirects to `/login` if not signed in)|
| GET    | `/login`                   | Login / signup page                             |
| POST   | `/login`                   | Submit credentials                              |
| POST   | `/register`                | Create a new account                            |
| GET    | `/logout`                  | End session                                     |
| GET    | `/api/songs?q=<query>`     | List or search local + iTunes catalog           |
| GET    | `/api/artists`             | Distinct artists with song counts               |
| GET    | `/api/recommend/<song_id>` | Same-artist recommendations for a song          |
| POST   | `/api/rediscover`          | Re-find an iTunes song by `{title, artist}`     |
| GET    | `/api/play/<song_id>`      | Get a direct YouTube audio stream URL           |
| GET    | `/api/likes`               | Current user's liked songs                      |
| POST   | `/api/likes`               | Like a song (body: full song object)            |
| DELETE | `/api/likes/<song_id>`     | Unlike a song                                   |

---

## 🛢️ Switching to MongoDB Atlas

By default, user accounts and liked songs are stored in `data/users.json`. To use MongoDB instead:

1. Sign up at https://www.mongodb.com/cloud/atlas/register (free M0 tier).
2. Create a cluster, a database user, and add `0.0.0.0/0` to Network Access.
3. Copy your connection string (looks like `mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/`).
4. Create a `.env` file in the project root:
   ```env
   MONGODB_URI=mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   MONGODB_DB=tunify
   TUNIFY_SECRET=some-random-string
   ```
5. *(Optional)* Migrate existing users from the JSON file:
   ```bash
   python -m data.migrate_users_to_mongo
   ```
6. Restart the app:
   ```bash
   python app.py
   ```
   On startup you should see `[users] Using MongoDB backend (db=tunify)`.

If the URI is wrong or Mongo is unreachable, the app automatically falls back to JSON storage so it never crashes.

---

## 🛠️ Tech stack

- **Backend:** Flask 3.0, Werkzeug (password hashing), `yt-dlp`, `pymongo`, `python-dotenv`
- **Frontend:** Vanilla JavaScript, CSS Grid + Flexbox, Inter font, HTML5 `<audio>`
- **External APIs:** iTunes Search API (no key), YouTube (via `yt-dlp`)
- **Storage:** MongoDB Atlas *or* local JSON file (auto-detected)

---

## 🐛 Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` on startup | Activate your virtualenv, then `pip install -r requirements.txt` |
| First request hangs ~60 seconds | Normal — iTunes enrichment runs on first launch. Watch the terminal. |
| "Audio failed, using preview" | YouTube extraction failed for that song. The 30-second iTunes preview is being played instead. |
| Can't log in | Delete `data/users.json` to reset all accounts, then sign up again |
| Want a fresh iTunes cache | `python -m data.enrich --force` |
| Port 5000 already in use | Edit the last line of `app.py` to use a different port |

---

## 📄 License

MIT — do whatever you want with this code.
