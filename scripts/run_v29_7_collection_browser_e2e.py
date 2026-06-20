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

from flask import redirect, session  # noqa: E402
from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service as ChromeService  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

USER = "v29-e2e-admin"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = (
        "v29-browser-e2e-stable-secret-key-32chars-minimum"
    )
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import (
        register_dossier_assembly_routes_v21_0,
    )
    from src.socmint import database
    from src.socmint import collection_product_review_routes_v29_7 as review_routes

    review_routes.actor_is_administrator = lambda actor: actor == USER
    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)
    database.ensure_configured()
    dbs = database.Session()
    try:
        if not dbs.query(database.User).filter(database.User.username == USER).first():
            dbs.add(
                database.User(
                    username=USER,
                    password_hash=generate_password_hash("v29-e2e-internal"),
                    is_admin=True,
                    role="admin",
                    is_active=True,
                )
            )
            dbs.commit()
    finally:
        dbs.close()

    @app.get("/_v29_e2e_login")
    def _login():
        session["user"] = USER
        return redirect("/collection-operations")

    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def _get_json(driver, url: str) -> dict:
    return driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        fetch(arguments[0], {credentials:'same-origin'})
          .then(async r => done({status:r.status, body:await r.json()}))
          .catch(e => done({status:0, body:{error:String(e)}}));
        """,
        url,
    )


def run() -> dict:
    report = {
        "schema": "socmint.collection_browser_e2e.v29_7",
        "version": "v29.7.0",
        "checks": [],
    }
    temp = Path(tempfile.mkdtemp(prefix="socmint-v29-e2e-"))
    port = _port()
    server = make_server("127.0.0.1", port, _app(temp / "e2e.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        binary = (
            os.getenv("SOCMINT_CHROME_BINARY")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
            or shutil.which("google-chrome")
        )
        executable = os.getenv("SOCMINT_CHROMEDRIVER") or shutil.which("chromedriver")
        if binary:
            options.binary_location = binary
        service = (
            ChromeService(executable_path=executable) if executable else ChromeService()
        )
        driver = webdriver.Chrome(service=service, options=options)
        base = f"http://127.0.0.1:{port}"
        driver.get(base + "/_v29_e2e_login")

        pages = [
            ("operations", "/collection-operations", "Collection Operations"),
            ("jobs", "/collection-operations/jobs", "Collection Job"),
            ("policy", "/collection-operations/policies", "Collection Policy"),
            ("adapters", "/collection-operations/adapters", "Adapter"),
            ("evidence", "/collection-operations/evidence", "Evidence-Safe Ingestion"),
            ("recovery", "/collection-operations/recovery", "Retry, Recovery"),
            ("quality", "/collection-operations/quality", "Collection Quality"),
            (
                "product_review",
                "/collection-operations/product-review",
                "Collection Product Review",
            ),
        ]
        for key, path, phrase in pages:
            driver.get(base + path)
            _check(
                report,
                key,
                phrase.lower() in driver.page_source.lower(),
                driver.current_url,
            )

        checkpoint = _get_json(
            driver, base + "/api/v1/collection-operations/product-review-checkpoint"
        )
        _check(
            report,
            "checkpoint_ready",
            checkpoint.get("status") == 200
            and checkpoint.get("body", {}).get("ready") is True,
            json.dumps(checkpoint, sort_keys=True),
        )
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        shutil.rmtree(temp, ignore_errors=True)

    failed = [item for item in report["checks"] if not item["ok"]]
    report.update(
        {
            "passed_count": len(report["checks"]) - len(failed),
            "failed_count": len(failed),
            "status": "passed" if not failed else "failed",
            "v29_closed": not failed,
            "next_action": "begin_v30"
            if not failed
            else "resolve_v29_browser_e2e_failures",
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run()
    print(json.dumps(report, indent=2 if args.json else None, sort_keys=True))
    return 0 if report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
