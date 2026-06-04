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

# Bind to all network interfaces so phones / other devices on the same
# WiFi can reach the server at http://<this-computer's-LAN-IP>:5000.
# To restrict to localhost only, change BIND_HOST to "127.0.0.1".
BIND_HOST = "0.0.0.0"
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


def _detect_lan_ip() -> str:
    """Best-effort detection of this machine's LAN IPv4 address."""
    try:
        # Trick: open a UDP socket to an external host; the kernel picks
        # the local interface we'd use to route there, which is the LAN IP.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _open_browser_when_ready() -> None:
    if _wait_for_port("127.0.0.1", PORT):
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    else:
        print(
            f"[launch] Server didn't open port {PORT} in time -- "
            f"open http://127.0.0.1:{PORT} in your browser manually."
        )


def main() -> None:
    lan_ip = _detect_lan_ip()
    print(
        "\n  Starting Tunify...\n"
        f"  - On this computer:  http://127.0.0.1:{PORT}\n"
        f"  - On any device on the same WiFi:  http://{lan_ip}:{PORT}\n"
        "  Press Ctrl+C in this window to stop the server.\n"
    )
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    # Import after we've kicked off the browser-watcher thread so any slow
    # imports (yt-dlp, pymongo) don't delay the watcher.
    from app import app
    app.run(host=BIND_HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
