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

USER = "v28-e2e-admin"
CSRF = "v28-e2e-csrf"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _admin_payloads():
    return {
        "administration": {"status":"ready","user_summary":{},"role_summary":{},"team_summary":{},"active_sessions":[],"active_session_count":0,"access_grant_summary":{},"policy_summary":{},"connector_summary":{},"system_health":{},"pending_admin_actions":[],"pending_admin_action_count":0,"recent_governance_events":[],"read_only":True},
        "users": {"status":"ready","users":[],"user_count":0,"active_user_count":0,"suspended_user_count":0,"administrator_count":1,"account_history":[],"account_event_count":0,"credentials_visible":False,"credential_hashes_visible":False},
        "policy": {"status":"ready","roles":[],"active_roles":[],"role_count":0,"active_role_count":0,"permission_matrix":[],"access_rules":[],"active_access_rules":[],"access_rule_count":0,"active_access_rule_count":0,"explicit_deny_rule_count":0,"least_privilege_findings":[],"least_privilege_finding_count":0,"access_policy_history":[],"access_policy_event_count":0},
        "teams": {"status":"ready","teams":[],"active_teams":[],"team_count":0,"active_team_count":0,"member_assignment_count":0,"supervised_team_count":0,"organizational_scope_counts":{},"workload_group_counts":{},"organization_findings":[],"organization_finding_count":0,"team_history":[],"team_event_count":0},
        "reviews": {"status":"ready","reviews":[],"open_reviews":[],"closed_reviews":[],"review_count":0,"open_review_count":0,"closed_review_count":0,"pending_assignments":[],"pending_assignment_count":0,"decision_counts":{},"certification_decisions":[],"certification_decision_count":0,"expired_access_findings":[],"excessive_access_findings":[],"remediation_queue":[],"remediation_queue_count":0,"access_review_history":[],"access_review_event_count":0},
        "connectors": {"status":"ready","connector_summaries":[],"connector_count":0,"active_connector_count":0,"disabled_connector_count":0,"auth_readiness_counts":{},"connector_health":{},"administration_findings":[],"administration_finding_count":0,"connector_history":[],"connector_event_count":0},
        "operations": {"status":"ready","overall_status":"healthy","database_health":{"ready":True},"storage_health":{},"configuration_state":{},"job_health":{},"connector_run_health":{},"audit_log_continuity":{},"operational_findings":[],"operational_finding_count":0,"operational_incidents":[],"open_operational_incidents":[],"open_operational_incident_count":0,"operational_history":[],"operational_event_count":0},
    }


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v28-browser-e2e-stable-secret-key-32chars-minimum"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0
    from src.socmint import database
    from src.socmint import administration_workspace_routes_v28_0 as admin_routes
    from src.socmint import user_account_routes_v28_1 as user_routes
    from src.socmint import access_policy_routes_v28_2 as policy_routes
    from src.socmint import access_policy_write_routes_v28_2 as policy_writes
    from src.socmint import team_organization_routes_v28_3 as team_routes
    from src.socmint import access_review_routes_v28_4 as review_routes
    from src.socmint import connector_administration_routes_v28_5 as connector_routes
    from src.socmint import platform_operations_routes_v28_6 as operations_routes

    payloads = _admin_payloads()
    admin_routes.build_administration_workspace = lambda: payloads["administration"]
    user_routes.build_user_account_workspace = lambda: payloads["users"]
    user_routes.actor_is_administrator = lambda actor: actor == USER
    policy_routes.build_access_policy_workspace = lambda: payloads["policy"]
    policy_routes.actor_is_administrator = lambda actor: actor == USER
    policy_routes.evaluate_effective_access = lambda username, case_id: {"status":"ready","username":username,"case_id":case_id,"effective_permissions":["case.read"],"deny_overrides_allow":True}
    policy_writes.actor_is_administrator = lambda actor: actor == USER
    policy_writes.define_role = lambda **kwargs: {"status":"role_defined","role_id":"role-e2e"}
    team_routes.build_team_organization_workspace = lambda: payloads["teams"]
    team_routes.actor_is_administrator = lambda actor: actor == USER
    team_routes.create_team = lambda **kwargs: {"status":"team_created","team_id":"team-e2e"}
    review_routes.build_access_review_workspace = lambda: payloads["reviews"]
    review_routes.actor_is_administrator = lambda actor: actor == USER
    review_routes.create_review = lambda **kwargs: {"status":"access_review_created","review_id":"review-e2e"}
    connector_routes.build_connector_administration_workspace = lambda: payloads["connectors"]
    connector_routes.actor_is_administrator = lambda actor: actor == USER
    connector_routes.register_connector = lambda **kwargs: {"status":"connector_registered","connector_id":"connector-e2e"}
    operations_routes.build_platform_operations_workspace = lambda **kwargs: payloads["operations"]
    operations_routes.actor_is_administrator = lambda actor: actor == USER
    operations_routes.open_incident = lambda **kwargs: {"status":"operational_incident_opened","incident_id":"incident-e2e"}

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)
    database.ensure_configured()
    dbs = database.Session()
    try:
        if not dbs.query(database.User).filter(database.User.username == USER).first():
            dbs.add(database.User(username=USER, password_hash=generate_password_hash("v28-e2e-internal"), is_admin=True, role="admin", is_active=True))
            dbs.commit()
    finally:
        dbs.close()

    @app.get("/_v28_e2e_login")
    def _login():
        session["user"] = USER
        session["_csrf_token"] = CSRF
        return redirect("/administration")

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
        """, url,
    )


def _post(driver, url: str, payload: dict) -> dict:
    return driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        fetch(arguments[0], {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRF-Token':'v28-e2e-csrf'}, body:JSON.stringify(arguments[1])})
          .then(async r => done({status:r.status, body:await r.json()}))
          .catch(e => done({status:0, body:{error:String(e)}}));
        """, url, payload,
    )


def run() -> dict:
    report = {"schema":"socmint.administration_browser_e2e.v28_7","version":"v28.7.0","checks":[]}
    temp = Path(tempfile.mkdtemp(prefix="socmint-v28-e2e-"))
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
        binary = os.getenv("SOCMINT_CHROME_BINARY") or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        executable = os.getenv("SOCMINT_CHROMEDRIVER") or shutil.which("chromedriver")
        if binary:
            options.binary_location = binary
        service = ChromeService(executable_path=executable) if executable else ChromeService()
        driver = webdriver.Chrome(service=service, options=options)
        base = f"http://127.0.0.1:{port}"
        driver.get(base + "/_v28_e2e_login")

        pages = [
            ("administration_page", "/administration", "Administration Workspace"),
            ("users_page", "/administration/users", "User and Account Administration"),
            ("policy_page", "/administration/access-policy", "Role, Permission, and Access Policy Management"),
            ("teams_page", "/administration/teams", "Team and Organizational Structure"),
            ("reviews_page", "/administration/access-reviews", "Access Review and Certification"),
            ("connectors_page", "/administration/connectors", "Connector and Integration Administration"),
            ("operations_page", "/administration/operations", "Platform Health, Jobs, and Operational Audit"),
            ("checkpoint_page", "/administration/product-review", "Administration Product Review"),
        ]
        for key, path, phrase in pages:
            driver.get(base + path)
            _check(report, key, phrase.lower() in driver.page_source.lower())

        apis = [
            "/api/v1/administration",
            "/api/v1/administration/users",
            "/api/v1/administration/access-policy",
            "/api/v1/administration/teams",
            "/api/v1/administration/access-reviews",
            "/api/v1/administration/connectors",
            "/api/v1/administration/operations",
            "/api/v1/administration/product-review-checkpoint",
        ]
        for path in apis:
            result = _get_json(driver, base + path)
            _check(report, "api_" + path.rsplit("/", 1)[-1].replace("-", "_"), result.get("status") == 200, json.dumps(result, sort_keys=True))

        writes = [
            ("user_provision", "/api/v1/administration/users", {"username":"e2e-user","role":"analyst","reason":"e2e","confirmed":True}),
            ("role_define", "/api/v1/administration/access-policy/roles", {"name":"E2E Role","permissions":["case.read"],"inherits_role_ids":[],"reason":"e2e","confirmed":True}),
            ("team_create", "/api/v1/administration/teams", {"name":"E2E Team","reason":"e2e","confirmed":True}),
            ("review_create", "/api/v1/administration/access-reviews", {"name":"E2E Review","scope":{"users":["e2e-user"]},"reason":"e2e","confirmed":True}),
            ("connector_register", "/api/v1/administration/connectors", {"name":"E2E Connector","connector_type":"api","reason":"e2e","confirmed":True}),
            ("incident_open", "/api/v1/administration/operations/incidents", {"title":"E2E Incident","severity":"low","component":"browser","reason":"e2e","confirmed":True}),
        ]
        for key, path, payload in writes:
            result = _post(driver, base + path, payload)
            _check(report, key, result.get("status") == 200, json.dumps(result, sort_keys=True))

        checkpoint = _get_json(driver, base + "/api/v1/administration/product-review-checkpoint")
        _check(report, "checkpoint_ready", checkpoint.get("status") == 200 and checkpoint.get("body", {}).get("ready") is True, json.dumps(checkpoint, sort_keys=True))
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        shutil.rmtree(temp, ignore_errors=True)

    failed = [item for item in report["checks"] if not item["ok"]]
    report.update({
        "passed_count": len(report["checks"]) - len(failed),
        "failed_count": len(failed),
        "status": "passed" if not failed else "failed",
        "v28_closed": not failed,
        "next_action": "begin_v29" if not failed else "resolve_v28_browser_e2e_failures",
    })
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
