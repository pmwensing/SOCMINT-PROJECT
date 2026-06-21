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

USER = "v31-e2e-admin"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v31-browser-e2e-stable-secret-key-32chars-minimum"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"
    from src.socmint.dashboard import create_app
    from src.socmint import database
    from src.socmint import publication_product_review_routes_v31_7 as review_routes
    from src.socmint.publication_review_routes_v31_0 import (
        register_publication_review_routes_v31_0,
    )

    review_routes.actor_is_administrator = lambda actor: actor == USER
    app = create_app()
    app.config.update(TESTING=True)
    route_rules = {rule.rule for rule in app.url_map.iter_rules()}
    if "/publication-review" not in route_rules:
        register_publication_review_routes_v31_0(app)
    database.ensure_configured()
    dbs = database.Session()
    try:
        if not dbs.query(database.User).filter(database.User.username == USER).first():
            dbs.add(
                database.User(
                    username=USER,
                    password_hash=generate_password_hash("v31-e2e-internal"),
                    is_admin=True,
                    role="admin",
                    is_active=True,
                )
            )
            dbs.commit()
    finally:
        dbs.close()

    @app.get("/_v31_e2e_login")
    def _login():
        session["user"] = USER
        session["is_admin"] = True
        session["role"] = "admin"
        return redirect("/publication-review")

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
        "schema": "socmint.publication_browser_e2e.v31_7",
        "version": "v31.7.0",
        "checks": [],
    }
    temp = Path(tempfile.mkdtemp(prefix="socmint-v31-e2e-"))
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
        service = ChromeService(executable_path=executable) if executable else ChromeService()
        driver = webdriver.Chrome(service=service, options=options)
        base = f"http://127.0.0.1:{port}"
        driver.get(base + "/_v31_e2e_login")

        for key, path, phrase in [
            ("workspace", "/publication-review", "Publication Review Workspace"),
            ("product_review", "/publication-review/product-review", "Publication Product Review"),
        ]:
            driver.get(base + path)
            _check(report, key, phrase.lower() in driver.page_source.lower(), driver.current_url)

        for key, path in [
            ("workspace_api", "/api/v1/publication-review"),
            ("candidates_api", "/api/v1/publication-review/candidates"),
            ("draft_revisions_api", "/api/v1/publication-review/draft-revisions"),
            ("editorial_validations_api", "/api/v1/publication-review/editorial-validations"),
            ("release_approvals_api", "/api/v1/publication-review/release-approvals"),
            ("published_revisions_api", "/api/v1/publication-review/published-revisions"),
            ("supersessions_api", "/api/v1/publication-review/supersessions"),
        ]:
            result = _get_json(driver, base + path)
            _check(report, key, result.get("status") == 200, json.dumps(result, sort_keys=True))

        checkpoint = _get_json(driver, base + "/api/v1/publication-review/product-review-checkpoint")
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
            "v31_closed": False,
            "next_action": (
                "confirm_test_gates_and_close_v31"
                if not failed
                else "resolve_v31_browser_e2e_failures"
            ),
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
