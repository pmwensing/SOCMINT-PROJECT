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
    os.environ["SOCMINT_SECRET_KEY"] = (
        "v20-browser-e2e-test-secret-key-2026-"
        "4f13796cc8e744c6a741d55903be50d5"
    )
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"
    from src.socmint.case_findings_routes_v20 import register_case_findings_routes_v20
    from src.socmint.dashboard import create_app

    app = create_app()
    app.config.update(TESTING=True)
    register_case_findings_routes_v20(app)
    return app


def run(output: Path) -> dict:
    report = {
        "schema": "socmint.case_findings_browser_e2e.v20_7",
        "version": "v20.7.0",
        "status": "passed",
        "checks": [],
    }
    with tempfile.TemporaryDirectory(prefix="socmint-v20-") as temp:
        app = _app(Path(temp) / "v20.db")
        server = make_server("127.0.0.1", _port(), app)
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
        browser = webdriver.Chrome(
            options=options,
            service=ChromeService(driver_path) if driver_path else None,
        )
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            browser.get(base + "/")
            serializer = app.session_interface.get_signing_serializer(app)
            browser.add_cookie(
                {
                    "name": app.config.get("SESSION_COOKIE_NAME", "session"),
                    "value": serializer.dumps(
                        {"user": "supervisor", "_csrf_token": "v20-csrf"}
                    ),
                    "path": "/",
                }
            )
            wait = WebDriverWait(browser, 10)
            browser.get(base + "/case-findings/case-v20")
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-case-findings-workspace]")
                )
            )
            report["checks"].append(
                {
                    "key": "workspace_render",
                    "ok": "Case Findings Workspace" in browser.page_source,
                }
            )
            browser.find_element(By.ID, "finding-text").send_keys(
                "The reviewed account is attributable to the subject."
            )
            browser.find_element(By.ID, "finding-claim-ids").send_keys("claim-1")
            browser.find_element(By.ID, "finding-evidence-ids").send_keys(
                "evidence-1"
            )
            browser.find_element(By.ID, "propose-case-finding").click()
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "save-finding-decision"))
            )
            report["checks"].append({"key": "finding_proposal", "ok": True})
            browser.find_element(By.CLASS_NAME, "save-finding-decision").click()
            wait.until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, ".finding-status"), "approved"
                )
            )
            report["checks"].append({"key": "supervisor_approval", "ok": True})
            browser.find_element(By.ID, "preview-dossier-package").click()
            wait.until(
                lambda drv: "dossier-findings-"
                in drv.find_element(By.ID, "dossier-package-output").text
            )
            report["checks"].append({"key": "package_preview", "ok": True})
            browser.execute_script("window.confirm = () => true;")
            browser.find_element(By.ID, "promote-dossier-package").click()
            wait.until(
                lambda drv: "promoted"
                in drv.find_element(By.ID, "dossier-package-output").text
            )
            report["checks"].append({"key": "dossier_promotion", "ok": True})
        except Exception as exc:
            report["status"] = "failed"
            report["checks"].append(
                {
                    "key": "browser_exception",
                    "ok": False,
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
        finally:
            browser.quit()
            server.shutdown()
            thread.join(timeout=5)
    report["passed_count"] = sum(1 for item in report["checks"] if item.get("ok"))
    report["failed_count"] = len(report["checks"]) - report["passed_count"]
    if report["failed_count"]:
        report["status"] = "failed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", default="artifacts/v20_7_case_findings_browser_e2e.json"
    )
    args = parser.parse_args()
    report = run(Path(args.output))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
