from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import redirect, session  # noqa: E402
from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service as ChromeService  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

USER = "v36-8-e2e-admin"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _app(temp_dir: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_dir / 'e2e.db'}"
    os.environ["SOCMINT_DATA_DIR"] = str(temp_dir)
    os.environ["SOCMINT_SECRET_KEY"] = secrets.token_hex(32)
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint import database
    from src.socmint import entity_accuracy_workspace_routes_v36_8 as routes
    from src.socmint.wsgi import app

    routes.actor_is_administrator = lambda actor: actor == USER
    app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
    database.ensure_configured()

    @app.get("/_v36_8_e2e_login")
    def _login():
        session["user"] = USER
        session["is_admin"] = True
        return redirect("/entity-accuracy")

    return app


def run() -> dict:
    temp_dir = Path(tempfile.mkdtemp(prefix="socmint-v36-8-e2e-"))
    port = _port()
    server = make_server("127.0.0.1", port, _app(temp_dir))
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
        driver.get(f"http://127.0.0.1:{port}/_v36_8_e2e_login")
        source = driver.page_source
        required = (
            'data-entity-accuracy-workspace="v36.8"',
            'data-read-only="true"',
            'data-automatic-truth-assignment="false"',
            'data-automatic-entity-merge="false"',
            'data-automatic-dossier-publication="false"',
            'data-write-actions="none"',
            'data-integrity-findings="true"',
            'data-source-inventory="true"',
            'data-observation-inventory="true"',
            'data-candidate-inventory="true"',
            'data-verification-inventory="true"',
            'data-relationship-inventory="true"',
            'data-snapshot-inventory="true"',
        )
        for key in required:
            checks.append({"key": key, "ok": key in source})
        forbidden = (
            "<form",
            'name="merge"',
            'name="approve"',
            'name="export"',
            'name="publish"',
            'name="collect"',
            'name="mutate_dossier"',
        )
        for key in forbidden:
            checks.append({"key": f"absent:{key}", "ok": key not in source})
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        shutil.rmtree(temp_dir, ignore_errors=True)

    failed = [item for item in checks if not item["ok"]]
    return {
        "schema": "socmint.entity_accuracy_workspace_browser_e2e.v36_8",
        "version": "v36.8.0",
        "checks": checks,
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "status": "passed" if not failed else "failed",
        "write_control_present": False if not failed else None,
    }


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
