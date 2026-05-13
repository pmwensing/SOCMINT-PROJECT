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


FORBIDDEN_TOKENS = ("write", "build", "download", "archive", "publish", "decision", "signoff")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="socmint-v1008-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1008-guardrails-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1008-guardrails-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1008-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/blueprint-guardrails")
            payload = response.get_json() if response.is_json else {}
            rows = payload.get("routes", [])
            ok = (
                response.status_code == 200
                and payload.get("version") == "10.0.8"
                and payload.get("status") == "pass"
                and payload.get("moved_route_count", 0) >= 16
                and payload.get("failed_route_count") == 0
                and payload.get("no_action_routes_moved") is True
                and payload.get("rollback_readiness", {}).get("rollback_ready_count") == payload.get("moved_route_count")
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET blueprint guardrails API", response.status_code)
            if not ok:
                failures.append(("GET blueprint guardrails API", response.status_code, response.get_data(as_text=True)[:7000]))

            for row in rows:
                route = row.get("route", "")
                ok = (
                    row.get("has_blueprint_primary") is True
                    and row.get("has_dashboard_fallback") is True
                    and row.get("rollback_ready") is True
                    and row.get("action_route_moved") is False
                    and not any(token in route.lower() for token in FORBIDDEN_TOKENS)
                    and row.get("non_get_blueprint_methods") == []
                )
                print(("[PASS]" if ok else "[FAIL]"), f"guardrail row {route}", row.get("status"))
                if not ok:
                    failures.append((f"guardrail row {route}", 0, str(row)[:3000]))

                response = client.get(route)
                ok = response.status_code == 200
                print(("[PASS]" if ok else "[FAIL]"), f"GET moved route {route}", response.status_code)
                if not ok:
                    failures.append((f"GET moved route {route}", response.status_code, response.get_data(as_text=True)[:2000]))

            response = client.get("/product/v10/blueprint-guardrails")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Blueprint Migration Wave 1 Guardrails" in body and "Moved Wave 1 Routes" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET blueprint guardrails UI", response.status_code)
            if not ok:
                failures.append(("GET blueprint guardrails UI", response.status_code, body[:2500]))

            response = client.post("/api/v1/product/v10/blueprint-guardrails/write", headers={"X-CSRF-Token": "v1008-csrf"})
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and written.get("version") == "10.0.8"
                and written.get("status") == "pass"
                and Path("release/V10_0_8_BLUEPRINT_GUARDRAILS_REPORT.json").exists()
                and Path("release/V10_0_8_BLUEPRINT_GUARDRAILS_REPORT.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "write blueprint guardrails report", response.status_code)
            if not ok:
                failures.append(("write blueprint guardrails report", response.status_code, response.get_data(as_text=True)[:3000]))

            for route in ["/product/v10", "/product/v10/modules", "/product/v10/module-health", "/product/v10/migration-plan"]:
                response = client.get(route)
                body = response.get_data(as_text=True)
                ok = response.status_code == 200 and "Open Blueprint Guardrails" in body
                print(("[PASS]" if ok else "[FAIL]"), f"guardrails link {route}", response.status_code)
                if not ok:
                    failures.append((f"guardrails link {route}", response.status_code, body[:2500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.8 blueprint guardrails smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
