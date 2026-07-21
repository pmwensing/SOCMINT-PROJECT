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

USER = "v38-8-e2e-admin"


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
    from src.socmint import public_discovery_capture_workspace_routes_v38_8 as routes
    from src.socmint.wsgi import app

    routes.actor_is_administrator = lambda actor: actor == USER
    app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
    database.ensure_configured()

    @app.get("/_v38_8_e2e_login")
    def _login():
        session["user"] = USER
        session["is_admin"] = True
        return redirect("/public-discovery-capture")

    return app


def run() -> dict:
    temp_dir = Path(tempfile.mkdtemp(prefix="socmint-v38-8-e2e-"))
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
        service = (
            ChromeService(executable_path=executable)
            if executable
            else ChromeService()
        )
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(f"http://127.0.0.1:{port}/_v38_8_e2e_login")
        source = driver.page_source.lower()
        required = (
            'data-public-discovery-capture-workspace="v38.8"',
            'data-read-only="true"',
            'data-safe-projection-only="true"',
            'data-raw-content-exposed="false"',
            'data-credentials-exposed="false"',
            'data-cookies-exposed="false"',
            'data-private-storage-paths-exposed="false"',
            'data-runtime-commands-exposed="false"',
            'data-automatic-collection="false"',
            'data-automatic-retry="false"',
            'data-automatic-artifact-acceptance="false"',
            'data-automatic-source-independence="false"',
            'data-automatic-observation-promotion="false"',
            'data-automatic-truth-assignment="false"',
            'data-automatic-entity-merge="false"',
            'data-automatic-claim-approval="false"',
            'data-automatic-dossier-mutation="false"',
            'data-automatic-import-staging="false"',
            'data-automatic-export="false"',
            'data-automatic-publication="false"',
            'data-write-actions="none"',
            'data-execution-recovery="true"',
            'data-capture-provenance="true"',
            'data-duplicate-change-triage="true"',
            'data-v37-handoff-visibility="true"',
            "no uncertain execution outcomes. automatic replay remains unavailable.",
        )
        for key in required:
            checks.append({"key": key, "ok": key in source})
        forbidden = (
            "<form",
            "<button",
            'method="post"',
            'name="collect"',
            'name="execute"',
            'name="retry"',
            'name="accept_artifact"',
            'name="assess_independence"',
            'name="promote"',
            'name="merge"',
            'name="approve"',
            'name="mutate_dossier"',
            'name="export"',
            'name="publish"',
            "authorization_binding",
            "authorization_reference",
            "confirmation_sha256",
            "approved_storage_root",
            "runtime_command",
        )
        for key in forbidden:
            checks.append({"key": f"absent:{key}", "ok": key not in source})

        driver.get(
            f"http://127.0.0.1:{port}/api/v1/public-discovery-capture/workspace"
        )
        api_source = driver.page_source.lower()
        for key in (
            '"read_only":true',
            '"safe_projection_only":true',
            '"write_actions_exposed_by_workspace":[]',
        ):
            checks.append({"key": f"api:{key}", "ok": key in api_source})
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        shutil.rmtree(temp_dir, ignore_errors=True)

    failed = [item for item in checks if not item["ok"]]
    return {
        "schema": "socmint.public_discovery_capture_browser_e2e.v38_8",
        "version": "v38.8.0",
        "checks": checks,
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "status": "passed" if not failed else "failed",
        "write_control_present": False if not failed else None,
        "sensitive_value_present": False if not failed else None,
    }


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
