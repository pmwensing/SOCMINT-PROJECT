from __future__ import annotations

import json
import shutil
import socket
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import redirect, session  # noqa: E402
from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service as ChromeService  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

USER = "v33-e2e-admin"
CASE_ID = "v33-e2e-case"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _app():
    from src.socmint import case_centric_operator_workspace_routes_v33_6 as routes
    from src.socmint.wsgi import app

    routes.actor_is_administrator = lambda actor: actor == USER
    routes.build_case_centric_operator_workspace = lambda case_id: {
        "status": "ready",
        "case_id": case_id,
        "summary": {
            "blocker_count": 0,
            "action_count": 0,
            "current_stage": "review",
            "next_action": "review_case_governance",
            "retention_state": "retained",
        },
        "sections": {
            "action_queue": {"action_queue": []},
            "audience_package_authorization": {"panels": {}},
            "delivery_receipt_feedback": {"panels": {}},
            "recall_retention_lifecycle": {"timeline": []},
        },
    }
    app.config.update(TESTING=True)

    @app.get("/_v33_e2e_login")
    def _login():
        session["user"] = USER
        return redirect(f"/dissemination-governance/cases/{CASE_ID}/workspace")

    return app


def run() -> dict:
    port = _port()
    server = make_server("127.0.0.1", port, _app())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    driver = None
    checks = []
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        binary = shutil.which("chromium") or shutil.which("google-chrome")
        executable = shutil.which("chromedriver")
        if binary:
            options.binary_location = binary
        service = ChromeService(executable_path=executable) if executable else ChromeService()
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(f"http://127.0.0.1:{port}/_v33_e2e_login")
        source = driver.page_source
        for key in (
            "governance-summary",
            "action-queue",
            "audience_package_authorization",
            "delivery_receipt_feedback",
            "lifecycle-timeline",
        ):
            checks.append({"key": key, "ok": f'id="{key}"' in source})
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()

    failed = [item for item in checks if not item["ok"]]
    return {
        "schema": "socmint.case_governance_browser_e2e.v33_7",
        "version": "v33.7.0",
        "checks": checks,
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "status": "passed" if not failed else "failed",
        "v33_closed": not failed,
    }


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
