#!/usr/bin/env bash
# =============================================================================
#  Tunify - one-click launcher for macOS / Linux
#
#  Just run:
#      chmod +x run.sh   (only the first time)
#      ./run.sh
# =============================================================================

set -e
cd "$(dirname "$0")"

echo
echo "  ============================================================"
echo "   Tunify - Same-artist music recommendation system"
echo "  ============================================================"
echo

# ---- Step 1: Find Python -----------------------------------------------------
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "  ERROR: Python is not installed."
    echo
    echo "  Please install Python 3.10+ from https://www.python.org/downloads/"
    echo "  Or on macOS:   brew install python"
    echo "  Or on Ubuntu:  sudo apt install python3 python3-venv"
    exit 1
fi
echo "  Found $($PYTHON --version)"
echo

# ---- Step 2: Create venv if missing ------------------------------------------
if [ ! -f ".venv/bin/python" ]; then
    echo "  First-time setup: creating virtual environment in .venv/ ..."
    $PYTHON -m venv .venv
    rm -f .venv/.last_install
fi

# ---- Step 3: Install / update dependencies -----------------------------------
NEED_INSTALL=1
REQ_HASH_FILE=".venv/.last_install"

# Pick a hashing tool (sha256sum on Linux, shasum on macOS).
if command -v sha256sum &>/dev/null; then
    HASH_CMD="sha256sum"
elif command -v shasum &>/dev/null; then
    HASH_CMD="shasum -a 256"
else
    HASH_CMD=""
fi

if [ -n "$HASH_CMD" ] && [ -f "$REQ_HASH_FILE" ]; then
    REQ_NOW=$($HASH_CMD requirements.txt | awk '{print $1}')
    REQ_OLD=$(cat "$REQ_HASH_FILE")
    if [ "$REQ_NOW" = "$REQ_OLD" ]; then
        NEED_INSTALL=0
    fi
fi

if [ "$NEED_INSTALL" = "1" ]; then
    echo "  Installing/updating dependencies (this may take a minute)..."
    .venv/bin/python -m pip install --upgrade pip --quiet
    .venv/bin/python -m pip install -r requirements.txt --quiet
    if [ -n "$HASH_CMD" ]; then
        $HASH_CMD requirements.txt | awk '{print $1}' >"$REQ_HASH_FILE"
    fi
    echo "  Dependencies ready."
else
    echo "  Dependencies up to date."
fi
echo

# ---- Step 4: Launch ----------------------------------------------------------
.venv/bin/python launch.py
