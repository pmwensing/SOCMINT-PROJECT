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
    with tempfile.TemporaryDirectory(prefix="socmint-v1006-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1006-migration-plan-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1006-migration-plan-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1006-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/module-health")
            health = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and health.get("status") == "healthy"
            print(("[PASS]" if ok else "[FAIL]"), "module health gate healthy", response.status_code)
            if not ok:
                failures.append(("module health gate healthy", response.status_code, response.get_data(as_text=True)[:5000]))

            response = client.get("/api/v1/product/v10/migration-plan")
            plan = response.get_json() if response.is_json else {}
            safe_routes = plan.get("first_wave_routes", [])
            ok = (
                response.status_code == 200
                and plan.get("version") == "10.0.6"
                and plan.get("status") == "ready"
                and plan.get("module_health_status") == "healthy"
                and plan.get("safe_candidate_count", 0) > 0
                and plan.get("first_wave_count", 0) > 0
                and all(route.get("readiness_gate_passed") is True for route in safe_routes)
                and all(route.get("risk_score", 100) < 55 for route in safe_routes)
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET migration plan API", response.status_code)
            if not ok:
                failures.append(("GET migration plan API", response.status_code, response.get_data(as_text=True)[:6000]))

            # Explicitly prove the safety gate: no safe route unless module health is healthy.
            ok = not any(
                route.get("safe_to_migrate") and plan.get("module_health_status") != "healthy"
                for route in plan.get("candidates", [])
            )
            print(("[PASS]" if ok else "[FAIL]"), "safe routes gated by healthy module health", 0)
            if not ok:
                failures.append(("safe routes gated by healthy module health", 0, "unsafe route marked safe"))

            response = client.get("/product/v10/migration-plan")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Blueprint Ownership Migration Plan" in body and "First Wave Routes" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET migration plan UI", response.status_code)
            if not ok:
                failures.append(("GET migration plan UI", response.status_code, body[:2500]))

            response = client.post("/api/v1/product/v10/migration-plan/write", headers={"X-CSRF-Token": "v1006-csrf"})
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and written.get("version") == "10.0.6"
                and Path("release/V10_0_6_BLUEPRINT_MIGRATION_PLAN.json").exists()
                and Path("release/V10_0_6_BLUEPRINT_MIGRATION_PLAN.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "write migration plan report", response.status_code)
            if not ok:
                failures.append(("write migration plan report", response.status_code, response.get_data(as_text=True)[:3000]))

            for route in ["/product/v10/module-health", "/product/v10/modules", "/product/v10"]:
                response = client.get(route)
                body = response.get_data(as_text=True)
                ok = response.status_code == 200 and "Open Migration Plan" in body
                print(("[PASS]" if ok else "[FAIL]"), f"migration link {route}", response.status_code)
                if not ok:
                    failures.append((f"migration link {route}", response.status_code, body[:2500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.6 blueprint migration plan smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
