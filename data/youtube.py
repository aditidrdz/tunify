"""
Find YouTube video IDs for songs using yt-dlp.

No API key needed — uses YouTube's public search.
Results are persisted to data/youtube_ids.json so each song is only
looked up once.

The lookup key is the lowercase "title|artist" string so iTunes-sourced
songs and local songs share the same cache.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any

from data.paths import data_dir

try:
    import yt_dlp  # type: ignore
    YT_DLP_AVAILABLE = True
except Exception as exc:  # pragma: no cover - import guard
    print(f"[youtube] yt-dlp not available: {exc}", file=sys.stderr)
    yt_dlp = None
    YT_DLP_AVAILABLE = False


CACHE_PATH = data_dir() / "youtube_ids.json"
_LOCK = Lock()
_CACHE: dict[str, str | None] = {}

# Audio URL cache: video_id -> (expires_at_epoch, url).
# Audio URLs from YouTube CDN are time-signed and only valid for a few hours,
# so we keep this in-memory and short-TTL rather than persisting to disk.
_AUDIO_URL_TTL_SEC = 4 * 3600  # 4 hours
_AUDIO_URL_CACHE: dict[str, tuple[float, str]] = {}


def _load_cache() -> None:
    global _CACHE
    if CACHE_PATH.exists():
        try:
            _CACHE = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            _CACHE = {}
    else:
        _CACHE = {}


def _save_cache() -> None:
    try:
        CACHE_PATH.write_text(
            json.dumps(_CACHE, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"[youtube] cache save failed: {exc}", file=sys.stderr)


_load_cache()


# yt-dlp options for fast, metadata-only search
_YDL_OPTS: dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",  # don't fetch full video info, just basics
    "skip_download": True,
    "default_search": "ytsearch1:",
    "noplaylist": True,
    "socket_timeout": 10,
    "geo_bypass": True,
}


def _build_query(title: str, artist: str) -> str:
    """Build a YouTube search query for a song."""
    parts = [title or "", artist or ""]
    return " ".join(p for p in parts if p).strip()


def find_video_id(title: str, artist: str) -> str | None:
    """
    Return the first YouTube video id matching this song, or None.
    Cached persistently to data/youtube_ids.json.
    """
    if not YT_DLP_AVAILABLE:
        return None

    key = f"{(title or '').strip().lower()}|{(artist or '').strip().lower()}"
    if not key.strip("|"):
        return None

    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]  # may be None if previously not found

    query = _build_query(title, artist)
    video_id: str | None = None

    try:
        with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info:
                entries = info.get("entries") or []
                if entries:
                    candidate = entries[0]
                    video_id = candidate.get("id") or None
    except Exception as exc:
        print(f"[youtube] search failed for {query!r}: {exc}", file=sys.stderr)
        video_id = None

    with _LOCK:
        _CACHE[key] = video_id
        _save_cache()

    return video_id


# yt-dlp options for extracting a direct audio stream URL (no download).
# We prefer m4a (AAC) since every modern browser plays it natively.
_AUDIO_OPTS: dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    "socket_timeout": 15,
    "geo_bypass": True,
    "format": "bestaudio[ext=m4a]/bestaudio[acodec=aac]/bestaudio",
}


def extract_audio_url(video_id: str) -> str | None:
    """
    Resolve a YouTube video id to a direct audio stream URL that a browser
    HTML5 <audio> element can play.

    YouTube CDN URLs are signed with a short expiry (~6 hours), so we cache
    in-memory with a 4-hour TTL and re-extract when expired.
    """
    if not YT_DLP_AVAILABLE or not video_id:
        return None

    now = time.time()
    with _LOCK:
        cached = _AUDIO_URL_CACHE.get(video_id)
        if cached and cached[0] > now:
            return cached[1]

    url: str | None = None
    try:
        with yt_dlp.YoutubeDL(_AUDIO_OPTS) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=False,
            )
            if info:
                # Single-video extract puts the chosen format's url at top level.
                url = info.get("url") or None
                # As a backup, scan formats for an audio-only entry.
                if not url:
                    for fmt in info.get("formats") or []:
                        if fmt.get("vcodec") in (None, "none") and fmt.get("url"):
                            url = fmt["url"]
                            break
    except Exception as exc:
        print(f"[youtube] audio extract failed for {video_id}: {exc}", file=sys.stderr)

    if url:
        with _LOCK:
            _AUDIO_URL_CACHE[video_id] = (now + _AUDIO_URL_TTL_SEC, url)
    return url
