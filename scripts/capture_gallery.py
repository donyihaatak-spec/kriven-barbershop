"""Capture real Mini App screenshots for kwork/gallery/."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "kwork" / "gallery"
BASE = "http://127.0.0.1:8765"

MINI_APP_SHOTS = [
    ("01-calendar.png", "/?demo=calendar", 390, 844),
    ("02-summary.png", "/?demo=summary", 390, 844),
    ("03-payment.png", "/?demo=payment", 390, 844),
    ("04-confirmed.png", "/?demo=confirmed", 390, 844),
    ("05-bookings.png", "/?demo=bookings", 390, 844),
]

ADMIN_SHOT = ("05-admin.png", "/admin/demo", 1100, 900)


def ensure_playwright():
    try:
        import playwright  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def capture():
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for filename, path, width, height in MINI_APP_SHOTS:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(BASE + path, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / filename))
            page.close()

        name, path, width, height = ADMIN_SHOT
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(BASE + path, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / name))
        page.close()
        browser.close()


def main():
    ensure_playwright()
    server = subprocess.Popen(
        [sys.executable, "-c", "from server import run_server; run_server(8765)"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(2)
        capture()
        print(f"Saved screenshots to {OUT}")
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    main()
