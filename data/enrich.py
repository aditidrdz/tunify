"""
Enrich our songs dataset with REAL album artwork + 30-second audio previews
from the free public iTunes Search API.

  https://itunes.apple.com/search?term=<query>&entity=song

No API key, no auth. Results are cached to data/enriched.json so the
network call only happens once per song.

Each cache entry looks like:
  { "artwork_url": "https://.../600x600.jpg", "preview_url": "https://.../30s.m4a" }
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from data.paths import data_dir

CACHE_PATH = data_dir() / "enriched.json"
ITUNES_ENDPOINT = "https://itunes.apple.com/search"
TIMEOUT_SEC = 8


def _search_itunes(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Run an iTunes Search API call. Returns list of song results, or []."""
    params = urllib.parse.urlencode({
        "term": query,
        "entity": "song",
        "limit": limit,
    })
    url = f"{ITUNES_ENDPOINT}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Tunify/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            data = json.loads(resp.read())
            return data.get("results", []) or []
    except Exception as exc:
        print(f"    iTunes search failed for '{query}': {exc}", file=sys.stderr)
        return []


def _best_match(results: list[dict[str, Any]], song: dict[str, Any]) -> dict[str, Any] | None:
    """Pick the best iTunes result for a given song based on artist match."""
    if not results:
        return None
    artist_lower = song["artist"].lower()
    title_lower = song["title"].lower()

    # Prefer exact artist match
    for r in results:
        if r.get("artistName", "").lower() == artist_lower:
            return r
    # Then partial artist match (handles "Arijit Singh" vs "Arijit Singh & Others")
    for r in results:
        if artist_lower in r.get("artistName", "").lower():
            return r
    # Then any result whose track name matches our title
    for r in results:
        if title_lower in r.get("trackName", "").lower():
            return r
    # Fallback to first
    return results[0]


def _enrich_one(song: dict[str, Any]) -> dict[str, Any]:
    queries = [
        f"{song['title']} {song['artist']}",
        f"{song['artist']} {song['title']}",
        f"{song['title']} {song['album']}",
        song["title"],
    ]
    for q in queries:
        results = _search_itunes(q, limit=8)
        match = _best_match(results, song)
        if match and match.get("artworkUrl100"):
            artwork = match["artworkUrl100"].replace("100x100", "600x600")
            return {
                "artwork_url": artwork,
                "preview_url": match.get("previewUrl"),
                "itunes_track": match.get("trackName"),
                "itunes_artist": match.get("artistName"),
            }
    return {"artwork_url": None, "preview_url": None}


def enrich_all(songs: list[dict[str, Any]], force: bool = False) -> dict[str, dict[str, Any]]:
    """
    Enrich every song with iTunes artwork + preview URL.

    On first run this hits the network for each song; results are cached
    to data/enriched.json so subsequent boots are instant.
    Pass force=True to refresh the cache.
    """
    if CACHE_PATH.exists() and not force:
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("Cache file corrupt, rebuilding...", file=sys.stderr)

    print(f"\n  Enriching {len(songs)} songs from iTunes (one-time setup)...")
    cache: dict[str, dict[str, Any]] = {}
    for i, song in enumerate(songs, 1):
        info = _enrich_one(song)
        status = "OK " if info.get("artwork_url") else "-- "
        print(f"   [{i:2d}/{len(songs)}] {status} {song['title']} - {song['artist']}")
        cache[str(song["id"])] = info

    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Cached to {CACHE_PATH.name}\n")
    return cache


if __name__ == "__main__":
    # Allow running this file directly to (re)build the cache:
    #   python -m data.enrich
    from data.songs import SONGS  # type: ignore[import-not-found]
    force = "--force" in sys.argv
    enrich_all(SONGS, force=force)
