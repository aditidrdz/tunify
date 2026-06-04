"""
Generate screenshots of the Tunify app for the README.

Captures:
  1. login.png       - Login page
  2. signup.png      - Signup form (toggled)
  3. home.png        - Logged-in home page with song grid
  4. player.png      - Same view with bottom player visible playing a song
  5. queue.png       - Slide-in queue panel showing same-artist queue
  6. liked.png       - Liked Songs sidebar view
  7. search.png      - Search results page

Output: docs/screenshots/*.png

Run after starting the Flask server (python app.py).
Usage:  python tools/take_screenshots.py
"""

from __future__ import annotations

import secrets
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = "http://127.0.0.1:5000"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Use a fresh demo account so screenshots show a clean state.
DEMO_USER = f"demo_{secrets.token_hex(3)}"
DEMO_PASS = "demo-password-1234"


def shoot(page: Page, name: str) -> None:
    path = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  OK  {name}.png  ({path})")


def signup(page: Page) -> None:
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)
    shoot(page, "login")

    # Toggle to signup by clicking the "Create an account" link.
    link = page.locator("a[href*='register'], a:has-text('Create an account')").first
    if link.count() > 0:
        link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.6)
    shoot(page, "signup")

    page.locator("input[name='username']").fill(DEMO_USER)
    page.locator("input[name='password']").fill(DEMO_PASS)
    page.locator("button[type='submit']").click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print(f"  After signup, URL = {page.url}")
    if "/login" in page.url:
        raise RuntimeError(
            "Signup did not log us in. Check Flask logs / form action."
        )


def shoot_home(page: Page) -> None:
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(3)  # let song grid render
    shoot(page, "home")


def shoot_player_and_queue(page: Page) -> None:
    # Wait for the song grid to populate.
    page.wait_for_selector(".song-card", timeout=15000)
    cards = page.locator(".song-card")
    if cards.count() == 0:
        print("  WARN no song cards found, skipping player/queue shots")
        return
    cards.first.click()
    time.sleep(5)  # recommendation queue + YouTube audio URL fetch
    shoot(page, "player")

    queue_btn = page.locator("#queue-btn").first
    if queue_btn.count() > 0:
        queue_btn.click()
        time.sleep(0.8)
        shoot(page, "queue")
        queue_btn.click()
        time.sleep(0.4)


def shoot_liked(page: Page) -> None:
    # Like the currently-playing song so the Liked view has content.
    like_btn = page.locator("#player-like-btn, .like-btn-player").first
    if like_btn.count() > 0:
        try:
            like_btn.click()
            time.sleep(0.4)
        except Exception:
            pass

    liked_nav = page.locator(".nav-item[data-view='liked']").first
    if liked_nav.count() > 0:
        liked_nav.click()
        time.sleep(1.0)
        shoot(page, "liked")


def shoot_search(page: Page) -> None:
    # Make sure we're on a view that has the search input visible.
    home_nav = page.locator(".nav-item[data-view='home']").first
    if home_nav.count() > 0:
        home_nav.click()
        time.sleep(0.4)
    search = page.locator("#search-input").first
    if search.count() == 0:
        return
    search.fill("Arijit Singh")
    time.sleep(3)  # debounce + iTunes fetch + render
    shoot(page, "search")


def main() -> int:
    print(f"Saving screenshots to: {OUT_DIR}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            signup(page)
            shoot_home(page)
            shoot_player_and_queue(page)
            shoot_search(page)
            shoot_liked(page)
        finally:
            ctx.close()
            browser.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
