"""
Tunify launcher.

Starts the Flask server and opens the user's default browser to
http://127.0.0.1:5000 once the server is up. Used by `run.bat` and
`run.sh` so anyone can launch the app with a single double-click.

To launch the app the "developer" way, you can still just run:
    python app.py
"""

from __future__ import annotations

import socket
import threading
import time
import webbrowser

HOST = "127.0.0.1"
PORT = 5000


def _wait_for_port(host: str, port: int, timeout: float = 180.0) -> bool:
    """Block until the given TCP port accepts connections, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def _open_browser_when_ready() -> None:
    if _wait_for_port(HOST, PORT):
        webbrowser.open(f"http://{HOST}:{PORT}")
    else:
        print(
            f"[launch] Server didn't open port {PORT} in time -- "
            f"open http://{HOST}:{PORT} in your browser manually."
        )


def main() -> None:
    print(
        "\n  Starting Tunify...\n"
        f"  Once ready, your browser will open at http://{HOST}:{PORT}\n"
        "  Press Ctrl+C in this window to stop the server.\n"
    )
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    # Import after we've kicked off the browser-watcher thread so any slow
    # imports (yt-dlp, pymongo) don't delay the watcher.
    from app import app
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
