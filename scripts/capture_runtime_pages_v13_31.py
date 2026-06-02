from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE = os.getenv("SOCMINT_BASE_URL", "http://127.0.0.1:5000")
USER = os.getenv("SOCMINT_CAPTURE_USER", "admin")
PASSWORD = os.getenv("SOCMINT_CAPTURE_PASSWORD", "")
SUBJECT_ID = os.getenv("SOCMINT_CAPTURE_SUBJECT_ID", "4")
OUT = Path(os.getenv("SOCMINT_CAPTURE_OUT", "runtime_screenshots_v13_31"))

PAGES = [
    ("/command-center", "command-center"),
    ("/review/normalization-queue", "normalization-review"),
    (f"/subjects/{SUBJECT_ID}/dossier/readiness", "dossier-readiness"),
    (f"/subjects/{SUBJECT_ID}/claim-evidence-ledger", "claim-evidence-ledger"),
    (f"/spine/subjects/{SUBJECT_ID}/dossier", "full-dossier-v2"),
    (f"/spine/subjects/{SUBJECT_ID}/full-report/history", "full-report-history"),
    (f"/spine/subjects/{SUBJECT_ID}/full-report/view", "full-report-view"),
    (f"/spine/subjects/{SUBJECT_ID}/full-report/retention", "full-report-retention"),
]


def capture_viewports(page, name: str) -> None:
    page.screenshot(path=str(OUT / f"{name}-top.png"), full_page=False, timeout=90000, animations="disabled")
    height = page.evaluate("() => document.body.scrollHeight")
    viewport = page.viewport_size or {"width": 1440, "height": 1600}
    if height > viewport["height"]:
        page.evaluate("(y) => window.scrollTo(0, y)", min(height // 2, height - viewport["height"]))
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / f"{name}-middle.png"), full_page=False, timeout=90000, animations="disabled")
        page.evaluate("(y) => window.scrollTo(0, y)", max(0, height - viewport["height"]))
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / f"{name}-bottom.png"), full_page=False, timeout=90000, animations="disabled")


def main() -> None:
    if not PASSWORD:
        raise SystemExit("SOCMINT_CAPTURE_PASSWORD is required")
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--disable-gpu", "--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1600})
        page.set_default_timeout(90000)

        page.goto(BASE + "/login", wait_until="domcontentloaded", timeout=90000)
        page.fill("input[name='username']", USER)
        page.fill("input[name='password']", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_load_state("domcontentloaded", timeout=90000)

        for path, name in PAGES:
            print(f"[+] Capture {path}")
            page.goto(BASE + path, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(1000)
            try:
                capture_viewports(page, name)
            except PlaywrightTimeoutError as exc:
                print(f"[!] screenshot timeout for {path}: {exc}")
                (OUT / f"{name}.html").write_text(page.content(), encoding="utf-8")
        browser.close()


if __name__ == "__main__":
    main()
