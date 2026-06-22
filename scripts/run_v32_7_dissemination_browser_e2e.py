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

USER = "v32-e2e-admin"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v32-browser-e2e-stable-secret-key-32chars-minimum"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint import database
    from src.socmint import dissemination_product_review_routes_v32_7 as review_routes
    from src.socmint.wsgi import app

    review_routes.actor_is_administrator = lambda actor: actor == USER
    app.config.update(TESTING=True)
    database.ensure_configured()
    dbs = database.Session()
    try:
        if not dbs.query(database.User).filter(database.User.username == USER).first():
            dbs.add(
                database.User(
                    username=USER,
                    password_hash=generate_password_hash("v32-e2e-internal"),
                    is_admin=True,
                    role="admin",
                    is_active=True,
                )
            )
            dbs.commit()
    finally:
        dbs.close()

    @app.get("/_v32_e2e_login")
    def _login():
        session["user"] = USER
        session["is_admin"] = True
        session["role"] = "admin"
        return redirect("/dissemination-governance/product-review")

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
        "schema": "socmint.dissemination_browser_e2e.v32_7",
        "version": "v32.7.0",
        "checks": [],
    }
    temp = Path(tempfile.mkdtemp(prefix="socmint-v32-e2e-"))
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
        driver.get(base + "/_v32_e2e_login")

        driver.get(base + "/dissemination-governance/product-review")
        _check(
            report,
            "product_review",
            "dissemination product review" in driver.page_source.lower(),
            driver.current_url,
        )

        for key, path in [
            ("audience_contracts_api", "/api/v1/dissemination-governance/audience-contracts"),
            ("packages_api", "/api/v1/dissemination-governance/packages"),
            ("authorization_api", "/api/v1/dissemination-governance/authorization-decisions"),
            ("attempts_api", "/api/v1/dissemination-governance/delivery-attempts"),
            ("receipts_api", "/api/v1/dissemination-governance/delivery-receipts"),
            ("feedback_api", "/api/v1/dissemination-governance/recipient-feedback"),
            ("corrections_api", "/api/v1/dissemination-governance/correction-intakes"),
            ("recalls_api", "/api/v1/dissemination-governance/recall-decisions"),
            ("retention_api", "/api/v1/dissemination-governance/retention-decisions"),
            ("lifecycle_api", "/api/v1/dissemination-governance/lifecycle-history"),
        ]:
            result = _get_json(driver, base + path)
            _check(
                report,
                key,
                result.get("status") == 200,
                json.dumps(result, sort_keys=True),
            )

        checkpoint = _get_json(
            driver,
            base + "/api/v1/dissemination-governance/product-review-checkpoint",
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
            "v32_closed": False,
            "next_action": (
                "confirm_test_gates_and_close_v32"
                if not failed
                else "resolve_v32_browser_e2e_failures"
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
