"""Quick mobile screenshot verifier - takes 2 shots at 390x844 (iPhone-ish)."""
from __future__ import annotations
import secrets
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

USER = f"mobile_{secrets.token_hex(3)}"
PASS = "demo-password-1234"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
    )
    page = ctx.new_page()

    # Sign up
    page.goto("http://127.0.0.1:5000/login")
    page.wait_for_load_state("networkidle")
    page.locator("a[href*='register']").first.click()
    page.wait_for_load_state("networkidle")
    page.locator("input[name='username']").fill(USER)
    page.locator("input[name='password']").fill(PASS)
    page.locator("button[type='submit']").click()
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Mobile home view
    page.screenshot(path=str(OUT / "mobile_home.png"), full_page=False)
    print("OK  mobile_home.png")

    # Open the drawer
    page.locator("#menu-btn").click()
    time.sleep(0.6)
    page.screenshot(path=str(OUT / "mobile_drawer.png"), full_page=False)
    print("OK  mobile_drawer.png")

    # Close drawer and start a song
    page.locator("#drawer-backdrop").click()
    time.sleep(0.4)
    page.wait_for_selector(".song-card", timeout=15000)
    page.locator(".song-card").first.click()
    time.sleep(5)
    page.screenshot(path=str(OUT / "mobile_playing.png"), full_page=False)
    print("OK  mobile_playing.png")

    browser.close()
print("Done.")
