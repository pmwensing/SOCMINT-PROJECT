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

USER = "v35-4-e2e-admin"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _seed_uncertain(database):
    from src.socmint.durable_execution_ledger_v35_1 import (
        create_execution,
        transition_execution,
    )
    from src.socmint.human_confirmation_framework_v34_2 import (
        confirmation_identity,
        record_issued_confirmation,
    )

    service = "recall_retention_lifecycle_v32_6.record_retention_decision"
    contract = {
        "status": "confirmation_required",
        "case_id": "case-v35-4-browser",
        "action": "record_retention_decision",
        "delegate_service": service,
        "eligibility_resolution_sha256": "c" * 64,
        "targets": {},
        "inputs": {
            "disposition": "retain",
            "policy_id": "policy-browser",
            "reason": "browser reconciliation test",
        },
        "impact_summary": "Confirm retention decision",
    }
    identity = confirmation_identity(contract)
    if identity is None:
        raise RuntimeError("confirmation identity unavailable")
    contract.update(identity)
    issuance = record_issued_confirmation(contract, USER)
    created = create_execution(
        confirmation_sha256=contract["confirmation_sha256"],
        actor=USER,
        case_id=contract["case_id"],
        governance_action=contract["action"],
        delegate_service=service,
    )
    running = transition_execution(
        execution_id=created["execution_id"],
        expected_state="pending",
        expected_version=created["state_version"],
        new_state="running",
        actor=USER,
        reason="authoritative_delegate_invocation_started",
        metadata={
            "confirmation_issue_audit_id": issuance["audit_record_id"],
            "contract_validation_sha256": "a" * 64,
        },
    )
    transition_execution(
        execution_id=created["execution_id"],
        expected_state="running",
        expected_version=running["state_version"],
        new_state="uncertain",
        actor=USER,
        reason="delegate_result_atomic_commit_failed",
        metadata={
            "result_reference_sha256": "b" * 64,
            "authoritative_record_ids": {"decision_id": "decision-browser"},
        },
    )


def _app(temp_dir: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_dir / 'e2e.db'}"
    os.environ["SOCMINT_DATA_DIR"] = str(temp_dir)
    os.environ["SOCMINT_SECRET_KEY"] = secrets.token_hex(32)
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint import database
    from src.socmint import execution_reconciliation_routes_v35_4 as routes
    from src.socmint.wsgi import app

    routes.actor_is_administrator = lambda actor: actor == USER
    app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
    database.ensure_configured()
    _seed_uncertain(database)

    @app.get("/_v35_4_e2e_login")
    def _login():
        session["user"] = USER
        session["is_admin"] = True
        return redirect("/dissemination-governance/execution-reconciliation")

    return app


def run() -> dict:
    temp_dir = Path(tempfile.mkdtemp(prefix="socmint-v35-4-e2e-"))
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
        driver.get(f"http://127.0.0.1:{port}/_v35_4_e2e_login")
        source = driver.page_source
        required = (
            'data-execution-reconciliation="v35.4"',
            'data-execution-id=',
            'data-reconciliation-form="true"',
            'name="authoritative_record_ids"',
            'name="result_reference_sha256"',
            'name="workspace_sha256"',
            'name="reconciliation_reason"',
            'name="evidence_references"',
            'data-automatic-retry="false"',
        )
        for key in required:
            checks.append({"key": key, "ok": key in source})
        forbidden = (
            'name="retry"',
            'name="automatic_retry"',
            'name="delegate_service"',
            'name="confirmation_sha256"',
            'name="actor"',
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
        "schema": "socmint.execution_reconciliation_browser_e2e.v35_4",
        "version": "v35.4.0",
        "checks": checks,
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "status": "passed" if not failed else "failed",
        "delegate_retry_control_present": False if not failed else None,
    }


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
