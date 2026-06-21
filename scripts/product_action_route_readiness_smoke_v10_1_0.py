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
    with tempfile.TemporaryDirectory(prefix="socmint-v1010-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1010-action-readiness-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1010-action-readiness-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1010-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/blueprint-wave2")
            wave2 = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and wave2.get("status") == "pass"
            print(
                ("[PASS]" if ok else "[FAIL]"), "Wave 2 pass gate", response.status_code
            )
            if not ok:
                failures.append(
                    (
                        "Wave 2 pass gate",
                        response.status_code,
                        response.get_data(as_text=True)[:4000],
                    )
                )

            response = client.get("/api/v1/product/v10/action-route-readiness")
            payload = response.get_json() if response.is_json else {}
            rows = payload.get("action_routes", [])
            ok = (
                response.status_code == 200
                and payload.get("version") == "10.1.0"
                and payload.get("status") == "pass"
                and payload.get("wave2_status") == "pass"
                and payload.get("action_route_count", 0) > 0
                and payload.get("extracted_blueprint_owned_count") == 0
                and payload.get("safe_to_migrate_count") == 0
                and payload.get("blocked_count") == payload.get("action_route_count")
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET action readiness API",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET action readiness API",
                        response.status_code,
                        response.get_data(as_text=True)[:7000],
                    )
                )

            for row in rows:
                ok = (
                    row.get("is_dashboard_owned") is True
                    and row.get("is_extracted_blueprint_owned") is False
                    and row.get("safe_to_migrate") is False
                    and row.get("blocked_from_blueprint_migration") is True
                    and row.get("requires_session") is True
                    and row.get("requires_write_safety_review") is True
                )
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    f"action route blocked {row.get('route')}",
                    row.get("status"),
                )
                if not ok:
                    failures.append(
                        (f"action route blocked {row.get('route')}", 0, str(row)[:3000])
                    )

            response = client.post(
                "/api/v1/product/v10/action-route-readiness/write",
                headers={"X-CSRF-Token": "v1010-csrf"},
            )
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and written.get("version") == "10.1.0"
                and written.get("status") == "pass"
                and Path("release/V10_1_0_ACTION_ROUTE_READINESS_REPORT.json").exists()
                and Path("release/V10_1_0_ACTION_ROUTE_READINESS_REPORT.md").exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write action readiness report",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write action readiness report",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get("/product/v10/action-route-readiness")
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Action Route Readiness" in body
                and "Action Route Inventory" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET action readiness UI",
                response.status_code,
            )
            if not ok:
                failures.append(
                    ("GET action readiness UI", response.status_code, body[:2500])
                )

            for route in [
                "/product/v10",
                "/product/v10/blueprint-wave2",
                "/product/v10/blueprint-guardrails",
            ]:
                response = client.get(route)
                body = response.get_data(as_text=True)
                ok = (
                    response.status_code == 200
                    and "Open Action Route Readiness" in body
                )
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    f"action readiness link {route}",
                    response.status_code,
                )
                if not ok:
                    failures.append(
                        (
                            f"action readiness link {route}",
                            response.status_code,
                            body[:2500],
                        )
                    )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.1.0 action route readiness smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
