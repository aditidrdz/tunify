"""
One-time migration: copy users from data/users.json into MongoDB.

Run this AFTER you have set MONGODB_URI in your .env file.

Usage (from project root):
    python -m data.migrate_users_to_mongo
or
    python data/migrate_users_to_mongo.py

Behaviour:
- Skips users that already exist in MongoDB (so it's safe to re-run).
- Preserves the existing password hash (no need to reset passwords).
- Preserves all liked songs.
- Does NOT delete data/users.json - you can do that manually once you've
  confirmed the migration worked.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


def main() -> int:
    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        print("ERROR: MONGODB_URI is not set. Put it in your .env file first.",
              file=sys.stderr)
        return 2

    db_name = os.environ.get("MONGODB_DB", "tunify").strip() or "tunify"

    from pymongo import MongoClient

    users_path = Path(__file__).parent / "users.json"
    if not users_path.exists():
        print("Nothing to migrate -- data/users.json does not exist.")
        return 0

    try:
        data = json.loads(users_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: could not parse users.json: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, dict) or not data:
        print("Nothing to migrate -- users.json is empty.")
        return 0

    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    coll = client[db_name]["users"]

    inserted = 0
    skipped = 0
    for username, info in data.items():
        if not isinstance(info, dict):
            continue
        if coll.find_one({"_id": username}, {"_id": 1}):
            print(f"  - {username}: already exists in MongoDB, skipping")
            skipped += 1
            continue
        doc = {
            "_id": username,
            "password_hash": info.get("password_hash", ""),
            "likes": info.get("likes", []),
        }
        coll.insert_one(doc)
        print(f"  + {username}: migrated ({len(doc['likes'])} liked songs)")
        inserted += 1

    print()
    print(f"Done. Inserted={inserted}  Skipped={skipped}  "
          f"(database='{db_name}', collection='users')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
