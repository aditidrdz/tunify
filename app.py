"""
Spotify-style same-artist recommendation system.

- Local catalog: 56 curated songs in data/songs.py (used as the "home" page).
- Live catalog: the entire iTunes Search API — used to power both search
  AND same-artist recommendations so the system works for ANY song,
  not just the 56 we curated.

Core rule (per user requirement):
  When a user picks a song, the next songs queued must all be by the
  SAME artist as the picked song. We pull from local first, then top up
  via iTunes so the queue always has 20+ songs by that artist.
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from functools import wraps
from threading import Lock
from typing import Any

from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from data import users as users_store
from data.enrich import enrich_all
from data.songs import SIMILAR_ARTISTS, SONGS
from data.youtube import extract_audio_url, find_video_id

app = Flask(__name__)
# Session signing key. In production set TUNIFY_SECRET to a random value.
app.secret_key = os.environ.get(
    "TUNIFY_SECRET",
    "tunify-dev-not-for-production-change-me",
)


def login_required(view):
    """Redirect to /login when not authenticated; return 401 JSON for API calls."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "auth required"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper

# ---------- enrich local songs with real artwork + previews -----------------
_ENRICHED = enrich_all(SONGS)
for _s in SONGS:
    _info = _ENRICHED.get(str(_s["id"]), {})
    _s["artwork_url"] = _info.get("artwork_url")
    _s["preview_url"] = _info.get("preview_url")
    _s["external"] = False

SONGS_BY_ID: dict[int, dict[str, Any]] = {s["id"]: s for s in SONGS}


# ============================================================================
# iTunes live catalog — songs found via the public iTunes Search API are
# given a NEGATIVE id and stashed in an in-memory cache so we can look them
# up later when the user clicks them.
# ============================================================================

_ITUNES_LOCK = Lock()
_ITUNES_BY_ID: dict[int, dict[str, Any]] = {}
_ITUNES_BY_KEY: dict[str, dict[str, Any]] = {}  # "title|artist" -> song
_NEXT_ITUNES_ID = [-1]

# Tiny TTL cache so we don't hammer iTunes for the same query repeatedly.
_REQ_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_REQ_CACHE_TTL = 600  # 10 minutes
_REQ_TIMEOUT = 8

PALETTE = [
    "#7c3aed", "#0ea5e9", "#10b981", "#f97316", "#ec4899",
    "#facc15", "#22c55e", "#dc2626", "#8b5cf6", "#06b6d4",
]


def _color_for(name: str) -> str:
    return PALETTE[sum(ord(c) for c in (name or "x")) % len(PALETTE)]


def _ms_to_mmss(ms: int | None) -> str:
    s = int(ms or 0) // 1000
    return f"{s // 60}:{s % 60:02d}"


def _itunes_request(query: str, limit: int = 20, country: str = "us",
                    attribute: str | None = None) -> list[dict[str, Any]]:
    """Hit the iTunes Search API with a tiny TTL cache."""
    params: dict[str, Any] = {
        "term": query,
        "entity": "song",
        "limit": limit,
        "country": country,
    }
    if attribute:
        params["attribute"] = attribute
    cache_key = json.dumps(params, sort_keys=True)
    now = time.time()
    cached = _REQ_CACHE.get(cache_key)
    if cached and now - cached[0] < _REQ_CACHE_TTL:
        return cached[1]

    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tunify/1.0"})
        with urllib.request.urlopen(req, timeout=_REQ_TIMEOUT) as resp:
            results = json.loads(resp.read()).get("results", []) or []
    except Exception as exc:
        print(f"[itunes] {query!r} ({country}) failed: {exc}", file=sys.stderr)
        results = []

    _REQ_CACHE[cache_key] = (now, results)
    return results


def _itunes_to_song(r: dict[str, Any]) -> dict[str, Any]:
    title = (r.get("trackName") or "").strip()
    artist = (r.get("artistName") or "").strip()
    artwork = (r.get("artworkUrl100") or "").replace("100x100", "600x600")
    return {
        "title": title,
        "artist": artist,
        "album": r.get("collectionName") or "",
        "language": "",
        "genre": r.get("primaryGenreName") or "",
        "year": int((r.get("releaseDate") or "0000")[:4] or 0),
        "duration": _ms_to_mmss(r.get("trackTimeMillis")),
        "color": _color_for(artist),
        "artwork_url": artwork or None,
        "preview_url": r.get("previewUrl"),
        "external": True,
    }


def _register_itunes(song: dict[str, Any]) -> dict[str, Any] | None:
    """
    Give an iTunes-sourced song a stable negative id so it can later be looked
    up by the recommendation/playback routes. Dedupes by (title|artist).
    Returns None if the song is unplayable (no preview).
    """
    if not song.get("preview_url") or not song.get("title") or not song.get("artist"):
        return None
    key = f"{song['title'].lower()}|{song['artist'].lower()}"

    with _ITUNES_LOCK:
        existing = _ITUNES_BY_KEY.get(key)
        if existing:
            return existing
        sid = _NEXT_ITUNES_ID[0]
        _NEXT_ITUNES_ID[0] -= 1
        song["id"] = sid
        _ITUNES_BY_ID[sid] = song
        _ITUNES_BY_KEY[key] = song
        return song


def itunes_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Free-text search across iTunes (US + IN to cover Bollywood). Deduped."""
    raw = _itunes_request(query, limit=limit, country="us")
    raw += _itunes_request(query, limit=limit, country="in")

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in raw:
        s = _itunes_to_song(r)
        key = f"{s['title'].lower()}|{s['artist'].lower()}"
        if not s["title"] or not s["artist"] or key in seen:
            continue
        seen.add(key)
        registered = _register_itunes(s)
        if registered:
            out.append(registered)
    return out


# Regex used to break a multi-artist credit like
#   "Shashwat Sachdev, Arijit Singh & Armaan Khan featuring X"
# into individual artists so we can do per-artist iTunes lookups.
_ARTIST_SPLIT_RE = re.compile(
    r"\s*,\s*|\s*&\s*|\s+(?:feat\.?|featuring|ft\.?|with|x)\s+",
    flags=re.IGNORECASE,
)


def _split_artist(artist: str) -> list[str]:
    """Break a multi-artist credit into ordered individual artists."""
    parts = [p.strip() for p in _ARTIST_SPLIT_RE.split(artist or "") if p.strip()]
    return parts if len(parts) > 1 else [artist]


def itunes_songs_by_artist(artist: str, limit: int = 25,
                           exclude_titles: set[str] | None = None) -> list[dict[str, Any]]:
    """
    Return up to `limit` deduplicated songs by `artist` from iTunes.
    For multi-artist credits we try each individual artist too, so a song
    credited to "A, B & C" still surfaces songs by A, by B and by C.
    Per-candidate cap prevents one artist from dominating.
    """
    exclude_titles = {t.lower() for t in (exclude_titles or set())}

    # Build candidate list: try the full credit first, then each individual artist.
    candidates: list[str] = []
    seen_candidates: set[str] = set()
    for c in [artist, *_split_artist(artist)]:
        cl = c.lower()
        if cl and cl not in seen_candidates:
            seen_candidates.add(cl)
            candidates.append(c)

    out: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    PER_CANDIDATE_CAP = 10

    for candidate in candidates:
        if len(out) >= limit:
            break

        raw = _itunes_request(candidate, limit=40, country="us", attribute="artistTerm")
        raw += _itunes_request(candidate, limit=40, country="in", attribute="artistTerm")

        cand_lower = candidate.lower()
        per = 0
        for r in raw:
            a = (r.get("artistName") or "").lower()
            t = (r.get("trackName") or "").lower()
            if cand_lower not in a:
                continue
            if not t or t in seen_titles or t in exclude_titles:
                continue
            seen_titles.add(t)
            s = _itunes_to_song(r)
            registered = _register_itunes(s)
            if registered:
                out.append(registered)
                per += 1
            if len(out) >= limit or per >= PER_CANDIDATE_CAP:
                break
    return out


# ---------- unified lookup ---------------------------------------------------

def get_song(song_id: int) -> dict[str, Any] | None:
    return SONGS_BY_ID.get(song_id) or _ITUNES_BY_ID.get(song_id)


# ---------- recommendation engine -------------------------------------------

def recommend(seed_song_id: int, limit: int = 20) -> dict[str, Any]:
    """
    Strict same-artist recommender.

    1. Take all OTHER local songs by the same artist (shuffled).
    2. Top up via iTunes for more songs by that exact artist (deduped).

    No similar-artist fallback: if the artist's catalog runs out, the queue
    just ends. The user explicitly asked that ONLY the same singer be queued.
    """
    seed = get_song(seed_song_id)
    if seed is None:
        return {"error": f"song id {seed_song_id} not found"}

    artist = seed["artist"]
    seed_title = seed["title"]

    # 1) Local same-artist songs
    local_same = [
        s for s in SONGS
        if s["artist"] == artist and s["id"] != seed_song_id
    ]
    random.shuffle(local_same)

    same_artist: list[dict[str, Any]] = list(local_same)
    used_titles = {s["title"].lower() for s in same_artist}
    used_titles.add(seed_title.lower())

    # 2) Top up with iTunes same-artist songs (deduped against local)
    if len(same_artist) < limit:
        itunes_more = itunes_songs_by_artist(
            artist, limit=limit + 5, exclude_titles=used_titles
        )
        for s in itunes_more:
            if s["title"].lower() in used_titles:
                continue
            same_artist.append(s)
            used_titles.add(s["title"].lower())
            if len(same_artist) >= limit:
                break

    parts = _split_artist(artist)
    display_artist = artist if len(parts) == 1 else f"{parts[0]} & others"
    return {
        "seed": seed,
        "artist": display_artist,
        "full_artist": artist,
        "same_artist": same_artist[:limit],
        "similar_artists": [],
        "queue": same_artist[:limit],
    }


# ============================================================================
# Flask routes
# ============================================================================

@app.route("/")
@login_required
def index() -> str:
    return render_template("index.html", username=session["user"])


# ---------- Auth ------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if "user" in session and request.method == "GET":
        return redirect(url_for("index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            return render_template("login.html", mode="login",
                                   error="Enter username and password.")
        if not users_store.verify_user(username, password):
            return render_template("login.html", mode="login",
                                   error="Invalid username or password.")
        session["user"] = username
        session.permanent = True
        return redirect(url_for("index"))

    return render_template("login.html", mode="login")


@app.route("/register", methods=["GET", "POST"])
def register() -> Any:
    if "user" in session and request.method == "GET":
        return redirect(url_for("index"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if len(username) < 2:
            return render_template("login.html", mode="register",
                                   error="Username must be at least 2 characters.")
        if len(password) < 4:
            return render_template("login.html", mode="register",
                                   error="Password must be at least 4 characters.")
        if users_store.user_exists(username):
            return render_template("login.html", mode="register",
                                   error="That username is already taken.")
        users_store.create_user(username, password)
        session["user"] = username
        session.permanent = True
        return redirect(url_for("index"))

    return render_template("login.html", mode="register")


@app.route("/logout")
def logout() -> Any:
    session.pop("user", None)
    return redirect(url_for("login"))


# ---------- Likes API (per-user, server-stored) -----------------------------

@app.route("/api/likes")
@login_required
def api_get_likes() -> Any:
    return jsonify(users_store.get_likes(session["user"]))


@app.route("/api/likes", methods=["POST"])
@login_required
def api_add_like() -> Any:
    song = request.get_json(silent=True) or {}
    if not song.get("title") or not song.get("artist"):
        return jsonify({"error": "title and artist required"}), 400
    users_store.add_like(session["user"], song)
    return jsonify({"status": "ok"})


@app.route("/api/likes/<sid>", methods=["DELETE"])
@login_required
def api_remove_like(sid: str) -> Any:
    try:
        song_id = int(sid)
    except ValueError:
        song_id = None

    # Allow removing by id; also accept ?title=&artist= for resilience
    # when iTunes ids have changed between sessions.
    title = request.args.get("title")
    artist = request.args.get("artist")
    users_store.remove_like(session["user"], song_id=song_id,
                            title=title, artist=artist)
    return jsonify({"status": "ok"})


@app.route("/api/songs")
@login_required
def api_songs() -> Any:
    """
    Return all songs, optionally filtered by ?q=<query>.
    If the local dataset has fewer than 8 matches, augment with live iTunes results.
    """
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify(SONGS)

    ql = q.lower()
    local = [
        s for s in SONGS
        if ql in s["title"].lower()
        or ql in s["artist"].lower()
        or ql in s["album"].lower()
    ]

    if len(local) >= 8:
        return jsonify(local)

    # Augment with iTunes
    external = itunes_search(q, limit=20)
    local_keys = {f"{s['title'].lower()}|{s['artist'].lower()}" for s in local}
    external = [
        e for e in external
        if f"{e['title'].lower()}|{e['artist'].lower()}" not in local_keys
    ]
    return jsonify(local + external)


@app.route("/api/artists")
@login_required
def api_artists() -> Any:
    counts: dict[str, int] = {}
    for s in SONGS:
        counts[s["artist"]] = counts.get(s["artist"], 0) + 1
    artists = sorted(
        ({"name": a, "count": c} for a, c in counts.items()),
        key=lambda x: x["name"],
    )
    return jsonify(list(artists))


# Use a string converter so negative IDs (iTunes songs) are accepted.
@app.route("/api/recommend/<sid>")
@login_required
def api_recommend(sid: str) -> Any:
    try:
        song_id = int(sid)
    except ValueError:
        return jsonify({"error": "invalid song id"}), 400
    limit = int(request.args.get("limit", 20))
    return jsonify(recommend(song_id, limit=limit))


@app.route("/api/rediscover")
@login_required
def api_rediscover() -> Any:
    """
    Re-find a song by title + artist via iTunes.
    Used by the Liked Songs feature: after a server restart, iTunes-found
    songs lose their session-cached negative ids. The frontend calls this
    with the stored title+artist to get a fresh playable song record.
    """
    title = (request.args.get("title") or "").strip()
    artist = (request.args.get("artist") or "").strip()
    if not title or not artist:
        return jsonify({"error": "title and artist required"}), 400

    # Try a focused search first, then a broader one.
    candidates = itunes_search(f"{title} {artist}", limit=10)
    if not candidates:
        candidates = itunes_search(title, limit=10)

    title_l = title.lower()
    artist_l = artist.lower()

    # Prefer an exact title + same artist match
    for s in candidates:
        if s["title"].lower() == title_l and artist_l in s["artist"].lower():
            return jsonify(s)
    # Fall back to substring match on both
    for s in candidates:
        if title_l in s["title"].lower() and artist_l in s["artist"].lower():
            return jsonify(s)
    if candidates:
        return jsonify(candidates[0])

    return jsonify({"error": "not found"}), 404


@app.route("/api/play/<sid>")
@login_required
def api_play(sid: str) -> Any:
    """
    Return playback info for a song:
      - audio_url:   direct YouTube CDN audio stream URL (plays in <audio>)
      - youtube_id:  YouTube video id (kept for reference / fallback embeds)
      - preview_url: 30s iTunes preview as last-resort fallback

    First call for a given song does a yt-dlp search (~2 sec) + audio
    extraction (~2-3 sec). Subsequent calls reuse the cached YouTube id and
    only re-extract the audio URL when it expires (every ~4 hours).
    """
    try:
        song_id = int(sid)
    except ValueError:
        return jsonify({"error": "invalid song id"}), 400

    song = get_song(song_id)
    if song is None:
        return jsonify({"error": "song not found"}), 404

    youtube_id = find_video_id(song["title"], song["artist"])
    audio_url = extract_audio_url(youtube_id) if youtube_id else None

    return jsonify({
        "song_id": song_id,
        "title": song["title"],
        "artist": song["artist"],
        "youtube_id": youtube_id,
        "audio_url": audio_url,
        "preview_url": song.get("preview_url"),
    })


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
