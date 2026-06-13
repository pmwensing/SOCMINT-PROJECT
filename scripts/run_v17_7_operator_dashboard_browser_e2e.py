from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from selenium import webdriver  # noqa: E402
from selenium.common.exceptions import WebDriverException  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402


SCHEMA = "socmint.operator_workflow_browser_e2e.v17_7"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _build_app(database_path: Path):
    os.environ["SOCMINT_DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["SOCMINT_SECRET_KEY"] = "v17-7-browser-e2e-secret-key-2026"

    from src.socmint.case_delivery_workspace_routes_v15 import (
        register_case_delivery_workspace_routes_v15,
    )
    from src.socmint.dashboard import create_app
    from src.socmint.operator_release_console_routes_v14 import (
        register_operator_release_console_routes_v14,
    )
    from src.socmint.unified_operator_workflow_dashboard_routes_v17_1 import (
        register_unified_operator_workflow_dashboard_routes_v17_1,
    )

    app = create_app()
    app.config.update(TESTING=True)
    register_operator_release_console_routes_v14(app)
    register_case_delivery_workspace_routes_v15(app)
    register_unified_operator_workflow_dashboard_routes_v17_1(app)
    return app


def _driver(name: str):
    if name == "firefox":
        options = webdriver.FirefoxOptions()
        options.add_argument("-headless")
        return webdriver.Firefox(options=options)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,1200")
    return webdriver.Chrome(options=options)


def _session_cookie(app, user: str = "operator") -> str:
    serializer = app.session_interface.get_signing_serializer(app)
    if serializer is None:
        raise RuntimeError("Flask session serializer is unavailable")
    return serializer.dumps({"user": user, "_csrf_token": "browser-e2e-csrf"})


def _check(report: dict[str, Any], key: str, ok: bool, detail: str) -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})
    if not ok:
        report["status"] = "failed"


def run_browser_validation(driver_name: str, output: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "v17.7.0",
        "driver": driver_name,
        "status": "passed",
        "checks": [],
    }
    with tempfile.TemporaryDirectory(prefix="socmint-v17-7-") as temp_dir:
        app = _build_app(Path(temp_dir) / "browser-e2e.db")
        port = _free_port()
        server = make_server("127.0.0.1", port, app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{port}"
        browser = None
        try:
            browser = _driver(driver_name)
            browser.get(base_url + "/")
            browser.add_cookie(
                {
                    "name": app.config.get("SESSION_COOKIE_NAME", "session"),
                    "value": _session_cookie(app),
                    "path": "/",
                    "httpOnly": True,
                }
            )
            browser.get(base_url + "/operator/workflow-dashboard?case_id=case-v17-7")
            wait = WebDriverWait(browser, 10)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-operator-workflow-dashboard]")
                )
            )

            _check(
                report,
                "authenticated_dashboard_render",
                "Unified Operator Workflow Dashboard" in browser.page_source,
                browser.current_url,
            )
            dispatch = browser.find_element(
                By.CSS_SELECTOR, '[data-action="dispatch_delivery_operations"]'
            )
            _check(
                report,
                "unsafe_dispatch_disabled",
                not dispatch.is_enabled(),
                "dispatch disabled on unready preview case",
            )

            refresh = browser.find_element(
                By.CSS_SELECTOR, '[data-action="refresh_release_health"]'
            )
            browser.execute_script("window.confirm = () => true;")
            refresh.click()
            wait.until(
                EC.visibility_of_element_located((By.ID, "operator-action-feedback"))
            )
            banner_text = browser.find_element(By.ID, "operator-action-feedback").text
            _check(
                report,
                "action_result_feedback",
                bool(banner_text.strip()),
                banner_text,
            )

            wait.until(
                lambda drv: "1 event(s)"
                in drv.find_element(By.ID, "operator-action-history-count").text
            )
            _check(
                report,
                "history_updates_after_action",
                True,
                browser.find_element(By.ID, "operator-action-history-count").text,
            )

            browser.find_element(By.ID, "refresh-action-history").click()
            wait.until(
                EC.text_to_be_present_in_element(
                    (By.ID, "operator-action-feedback"),
                    "Action history refreshed",
                )
            )
            _check(
                report,
                "manual_history_refresh",
                True,
                browser.find_element(By.ID, "operator-action-feedback").text,
            )

            blocker_button = browser.find_element(
                By.CSS_SELECTOR, '[data-action="review_blockers"]'
            )
            blocker_button.click()
            wait.until(lambda drv: "#active-blockers" in drv.current_url)
            _check(
                report,
                "navigation_action",
                browser.current_url.endswith("#active-blockers"),
                browser.current_url,
            )
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
            if browser is not None:
                browser.quit()
            server.shutdown()
            thread.join(timeout=5)

    report["check_count"] = len(report["checks"])
    report["passed_count"] = sum(1 for item in report["checks"] if item["ok"])
    report["failed_count"] = report["check_count"] - report["passed_count"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run v17.7 browser-level operator dashboard validation"
    )
    parser.add_argument(
        "--driver",
        choices=("chrome", "firefox"),
        default=os.getenv("SOCMINT_BROWSER_DRIVER", "chrome"),
    )
    parser.add_argument(
        "--output",
        default="artifacts/v17_7_operator_dashboard_browser_e2e.json",
    )
    args = parser.parse_args()
    try:
        report = run_browser_validation(args.driver, Path(args.output))
    except WebDriverException as exc:
        print(json.dumps({"status": "driver_unavailable", "detail": str(exc)}, indent=2))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
