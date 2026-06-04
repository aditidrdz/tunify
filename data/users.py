"""
User account + per-user liked-songs storage for Tunify.

This module exposes the SAME functions regardless of backend:
    user_exists(username) -> bool
    create_user(username, password) -> bool
    verify_user(username, password) -> bool
    get_likes(username) -> list[dict]
    add_like(username, song) -> bool
    remove_like(username, song_id=None, title=None, artist=None) -> bool

Two backends are supported, chosen automatically at import time:

1. MongoDB  -- used when the MONGODB_URI environment variable is set AND
               we can successfully ping the cluster. Recommended for prod.
               Schema (collection "users"):
                   {
                     "_id":           <username>,
                     "password_hash": "scrypt:...",
                     "likes":         [ { ...song dict... }, ... ],
                   }

2. JSON file -- the previous behaviour. Stored at data/users.json. Used as a
               graceful fallback so the app keeps working even before you
               set up Atlas / while Mongo is unreachable.

Passwords are always hashed with Werkzeug (never plaintext).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from threading import Lock
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from data.paths import data_dir, project_root

# Load .env if present so MONGODB_URI etc. just work in dev.
try:
    from dotenv import load_dotenv
    load_dotenv(project_root() / ".env")
except Exception:
    pass


USERS_PATH = data_dir() / "users.json"
_LOCK = Lock()


# ============================================================================
# Backend selection
# ============================================================================

_MONGO_URI = os.environ.get("MONGODB_URI", "").strip()
_MONGO_DB_NAME = os.environ.get("MONGODB_DB", "tunify").strip() or "tunify"

_mongo_client = None
_users_collection = None
BACKEND = "json"  # "mongo" or "json"


def _try_init_mongo() -> bool:
    """Connect to MongoDB. Returns True on success, False on any failure."""
    global _mongo_client, _users_collection, BACKEND
    if not _MONGO_URI:
        return False
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError

        client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=5000)
        # Force a round-trip so we fail fast if URI / network / auth is bad.
        client.admin.command("ping")
        db = client[_MONGO_DB_NAME]
        users = db["users"]
        # Username is the _id, so it's automatically unique. No extra index
        # required, but we ensure one for clarity / future-proofing.
        _mongo_client = client
        _users_collection = users
        BACKEND = "mongo"
        print(f"[users] Using MongoDB backend (db={_MONGO_DB_NAME})",
              file=sys.stderr)
        return True
    except Exception as exc:  # noqa: BLE001  (any error -> fall back to JSON)
        print(
            f"[users] MongoDB unavailable ({exc.__class__.__name__}: {exc}). "
            "Falling back to JSON file storage.",
            file=sys.stderr,
        )
        return False


if not _try_init_mongo():
    BACKEND = "json"
    print("[users] Using JSON file backend at data/users.json", file=sys.stderr)


# ============================================================================
# JSON helpers (used when BACKEND == "json")
# ============================================================================

def _load_json() -> dict[str, Any]:
    if not USERS_PATH.exists():
        return {}
    try:
        return json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(data: dict[str, Any]) -> None:
    USERS_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ============================================================================
# Public API
# ============================================================================

def _song_key(song: dict[str, Any]) -> tuple[str, str]:
    return (
        (song.get("title") or "").strip().lower(),
        (song.get("artist") or "").strip().lower(),
    )


def user_exists(username: str) -> bool:
    if BACKEND == "mongo":
        return _users_collection.find_one(
            {"_id": username}, {"_id": 1}
        ) is not None
    with _LOCK:
        return username in _load_json()


def create_user(username: str, password: str) -> bool:
    """Return True on success, False if the username is already taken."""
    if not username or not password:
        return False
    pw_hash = generate_password_hash(password)

    if BACKEND == "mongo":
        from pymongo.errors import DuplicateKeyError
        try:
            _users_collection.insert_one({
                "_id": username,
                "password_hash": pw_hash,
                "likes": [],
            })
            return True
        except DuplicateKeyError:
            return False

    with _LOCK:
        data = _load_json()
        if username in data:
            return False
        data[username] = {"password_hash": pw_hash, "likes": []}
        _save_json(data)
        return True


def verify_user(username: str, password: str) -> bool:
    if BACKEND == "mongo":
        doc = _users_collection.find_one(
            {"_id": username}, {"password_hash": 1}
        )
        if not doc:
            return False
        return check_password_hash(doc.get("password_hash", ""), password)

    with _LOCK:
        user = _load_json().get(username)
        if not user:
            return False
        return check_password_hash(user.get("password_hash", ""), password)


# ---------- per-user likes ---------------------------------------------------

def get_likes(username: str) -> list[dict[str, Any]]:
    if BACKEND == "mongo":
        doc = _users_collection.find_one(
            {"_id": username}, {"likes": 1}
        )
        return list((doc or {}).get("likes", []))

    with _LOCK:
        return list(_load_json().get(username, {}).get("likes", []))


def add_like(username: str, song: dict[str, Any]) -> bool:
    """Add a song to the user's likes. Dedupes on (title, artist)."""
    if not song.get("title") or not song.get("artist"):
        return False

    if BACKEND == "mongo":
        # Make sure user exists.
        doc = _users_collection.find_one({"_id": username}, {"likes": 1})
        if not doc:
            return False
        key = _song_key(song)
        for existing in doc.get("likes", []):
            if _song_key(existing) == key:
                return True  # already liked
        _users_collection.update_one(
            {"_id": username},
            {"$push": {"likes": song}},
        )
        return True

    with _LOCK:
        data = _load_json()
        if username not in data:
            return False
        likes = data[username].setdefault("likes", [])
        key = _song_key(song)
        for existing in likes:
            if _song_key(existing) == key:
                return True
        likes.append(song)
        _save_json(data)
        return True


def remove_like(username: str, song_id: Any = None,
                title: str | None = None, artist: str | None = None) -> bool:
    """Remove a song from likes. Match by id when given, otherwise title+artist."""
    if BACKEND == "mongo":
        doc = _users_collection.find_one({"_id": username}, {"likes": 1})
        if not doc:
            return False
        likes = doc.get("likes", [])

        def keep(s: dict[str, Any]) -> bool:
            if song_id is not None and s.get("id") == song_id:
                return False
            if title is not None and artist is not None:
                if _song_key(s) == (
                    (title or "").lower(), (artist or "").lower()
                ):
                    return False
            return True

        new_likes = [s for s in likes if keep(s)]
        if len(new_likes) != len(likes):
            _users_collection.update_one(
                {"_id": username},
                {"$set": {"likes": new_likes}},
            )
        return True

    with _LOCK:
        data = _load_json()
        if username not in data:
            return False
        likes = data[username].setdefault("likes", [])
        before = len(likes)

        def keep(s: dict[str, Any]) -> bool:
            if song_id is not None and s.get("id") == song_id:
                return False
            if title is not None and artist is not None:
                if _song_key(s) == (
                    (title or "").lower(), (artist or "").lower()
                ):
                    return False
            return True

        data[username]["likes"] = [s for s in likes if keep(s)]
        if len(data[username]["likes"]) != before:
            _save_json(data)
        return True
