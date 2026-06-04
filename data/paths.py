"""
Path helpers for Tunify.

When running normally (from source), data files live alongside the Python
source under data/.

When running as a PyInstaller-bundled .exe, the bundle is read-only, so we
need to put writable data files (user accounts, caches) somewhere persistent.
We use a `tunify_data/` folder next to the .exe -- that way the user can
see, back up, or delete their data easily.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def data_dir() -> Path:
    """
    Return a writable directory for runtime files (users.json, caches, ...).

    - Dev mode: the directory containing this file (i.e. <repo>/data/)
    - Frozen mode: <folder containing the .exe>/tunify_data/
    """
    if is_frozen():
        base = Path(sys.executable).resolve().parent / "tunify_data"
    else:
        base = Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)
    return base


def project_root() -> Path:
    """Project root (one level up from this file, or the exe folder)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
