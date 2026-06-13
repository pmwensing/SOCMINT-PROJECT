from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service as ChromeService  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v18-browser-e2e-secret-key-2026"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"
    from src.socmint.case_intelligence_review_routes_v18 import register_case_intelligence_review_routes_v18
    from src.socmint.dashboard import create_app
    app = create_app()
    app.config.update(TESTING=True)
    register_case_intelligence_review_routes_v18(app)
    return app


def run(output: Path) -> dict:
    report = {"schema": "socmint.case_intelligence_browser_e2e.v18_7", "version": "v18.7.0", "status": "passed", "checks": []}
    with tempfile.TemporaryDirectory(prefix="socmint-v18-") as temp:
        app = _app(Path(temp) / "v18.db")
        server = make_server("127.0.0.1", _port(), app)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        chromium = shutil.which("chromium") or shutil.which("google-chrome")
        if chromium:
            options.binary_location = chromium
        driver_path = shutil.which("chromedriver")
        browser = webdriver.Chrome(options=options, service=ChromeService(driver_path) if driver_path else None)
        try:
            base = f"http://127.0.0.1:{port}"
            browser.get(base + "/")
            serializer = app.session_interface.get_signing_serializer(app)
            browser.add_cookie({"name": app.config.get("SESSION_COOKIE_NAME", "session"), "value": serializer.dumps({"user": "analyst", "_csrf_token": "v18-csrf"}), "path": "/"})
            browser.get(base + "/case-intelligence-review/case-v18")
            wait = WebDriverWait(browser, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-case-intelligence-review]")))
            report["checks"].append({"key": "workspace_render", "ok": "Case Intelligence Review Workspace" in browser.page_source})
            browser.execute_script("window.confirm = () => true;")
            browser.find_element(By.ID, "record-review-decision").click()
            wait.until(EC.text_to_be_present_in_element((By.ID, "case-review-feedback"), "Decision recorded"))
            report["checks"].append({"key": "decision_feedback", "ok": True})
            wait.until(lambda drv: len(drv.find_elements(By.CSS_SELECTOR, "#case-review-history-body tr")) == 1)
            report["checks"].append({"key": "history_update", "ok": True})
            browser.find_element(By.ID, "refresh-review-history").click()
            wait.until(EC.text_to_be_present_in_element((By.ID, "case-review-feedback"), "history refreshed"))
            report["checks"].append({"key": "history_refresh", "ok": True})
        except Exception as exc:
            report["status"] = "failed"
            report["checks"].append({"key": "browser_exception", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
        finally:
            browser.quit()
            server.shutdown()
            thread.join(timeout=5)
    report["passed_count"] = sum(1 for item in report["checks"] if item.get("ok"))
    report["failed_count"] = len(report["checks"]) - report["passed_count"]
    if report["failed_count"]:
        report["status"] = "failed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/v18_7_case_intelligence_browser_e2e.json")
    args = parser.parse_args()
    report = run(Path(args.output))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
