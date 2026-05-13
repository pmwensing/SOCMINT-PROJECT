from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from socmint import database as db  # noqa: E402
from socmint.dashboard import create_app  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="socmint-v1011-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1011-action-safety-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1011-action-safety-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1011-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/action-route-readiness")
            readiness = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and readiness.get("status") == "pass"
            print(("[PASS]" if ok else "[FAIL]"), "Action readiness pass gate", response.status_code)
            if not ok:
                failures.append(("Action readiness pass gate", response.status_code, response.get_data(as_text=True)[:4000]))

            response = client.get("/api/v1/product/v10/action-safety-contract")
            payload = response.get_json() if response.is_json else {}
            contracts = payload.get("contracts", [])
            ok = (
                response.status_code == 200
                and payload.get("version") == "10.1.1"
                and payload.get("status") == "pass"
                and payload.get("action_readiness_status") == "pass"
                and payload.get("contract_count", 0) > 0
                and payload.get("complete_contract_count") == payload.get("contract_count")
                and payload.get("csrf_missing_count") == 0
                and payload.get("safe_to_migrate_count") == 0
                and payload.get("migration_blocked_count") == payload.get("contract_count")
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET action safety contract API", response.status_code)
            if not ok:
                failures.append(("GET action safety contract API", response.status_code, response.get_data(as_text=True)[:7000]))

            required_enforcement = {
                "csrf_required",
                "session_required",
                "auth_required",
                "write_safety_required",
                "dashboard_fallback_required",
                "migration_blocked",
                "route_owner_must_remain_dashboard",
                "manual_approval_required",
                "audit_event_required",
                "idempotency_review_required",
                "download_path_safety_required",
                "state_change_review_required",
            }

            for item in contracts:
                enforcement = item.get("enforcement", {})
                mutating = bool(item.get("mutating_methods"))
                ok = (
                    item.get("status") == "pass"
                    and item.get("contract_complete") is True
                    and item.get("safe_to_migrate") is False
                    and item.get("migration_blocked") is True
                    and required_enforcement.issubset(enforcement)
                    and enforcement.get("session_required") is True
                    and enforcement.get("auth_required") is True
                    and enforcement.get("write_safety_required") is True
                    and enforcement.get("migration_blocked") is True
                    and (not mutating or enforcement.get("csrf_required") is True)
                )
                print(("[PASS]" if ok else "[FAIL]"), f"safety contract {item.get('route')}", item.get("status"))
                if not ok:
                    failures.append((f"safety contract {item.get('route')}", 0, str(item)[:3000]))

            response = client.post("/api/v1/product/v10/action-safety-contract/write", headers={"X-CSRF-Token": "v1011-csrf"})
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and written.get("version") == "10.1.1"
                and written.get("status") == "pass"
                and Path("release/V10_1_1_ACTION_SAFETY_CONTRACT_MATRIX.json").exists()
                and Path("release/V10_1_1_ACTION_SAFETY_CONTRACT_MATRIX.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "write action safety contract report", response.status_code)
            if not ok:
                failures.append(("write action safety contract report", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.get("/product/v10/action-safety-contract")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Action Route Safety Contract" in body and "CSRF / Session / Auth / Write-Safety Matrix" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET action safety contract UI", response.status_code)
            if not ok:
                failures.append(("GET action safety contract UI", response.status_code, body[:2500]))

            for route in ["/product/v10", "/product/v10/action-route-readiness", "/product/v10/blueprint-wave2"]:
                response = client.get(route)
                body = response.get_data(as_text=True)
                ok = response.status_code == 200 and "Open Action Safety Contract" in body
                print(("[PASS]" if ok else "[FAIL]"), f"safety contract link {route}", response.status_code)
                if not ok:
                    failures.append((f"safety contract link {route}", response.status_code, body[:2500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.1.1 action safety contract smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
