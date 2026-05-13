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
    with tempfile.TemporaryDirectory(prefix="socmint-v1005-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1005-module-health-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1005-module-health-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1005-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/module-health")
            health = response.get_json() if response.is_json else {}
            modules = {item.get("key"): item for item in health.get("modules", [])}
            required_keys = {"release_flow", "post_release", "artifact_pipeline", "module_registry"}
            ok = (
                response.status_code == 200
                and health.get("version") == "10.0.5"
                and health.get("status") == "healthy"
                and health.get("ready_for_deeper_blueprint_extraction") is True
                and required_keys.issubset(modules)
                and all(modules[key].get("total_score", 0) >= 90 for key in required_keys)
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET module health API", response.status_code)
            if not ok:
                failures.append(("GET module health API", response.status_code, response.get_data(as_text=True)[:6000]))

            for key in required_keys:
                module = modules.get(key, {})
                ok = (
                    module.get("present_route_count") == module.get("route_count")
                    and module.get("helper_export_count", 0) >= module.get("helper_export_floor", 0)
                    and module.get("missing_smoke_targets") == []
                )
                print(("[PASS]" if ok else "[FAIL]"), f"module health {key}", module.get("total_score"))
                if not ok:
                    failures.append((f"module health {key}", 0, str(module)[:3000]))

            response = client.get("/product/v10/module-health")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Product Module Health Console" in body and "Module Scores" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET module health UI", response.status_code)
            if not ok:
                failures.append(("GET module health UI", response.status_code, body[:2500]))

            response = client.post("/api/v1/product/v10/module-health/write", headers={"X-CSRF-Token": "v1005-csrf"})
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and written.get("version") == "10.0.5"
                and Path("release/V10_0_5_MODULE_HEALTH_READINESS_REPORT.json").exists()
                and Path("release/V10_0_5_MODULE_HEALTH_READINESS_REPORT.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "write module health report", response.status_code)
            if not ok:
                failures.append(("write module health report", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.get("/product/v10/modules")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Module Health Console" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET registry module health link", response.status_code)
            if not ok:
                failures.append(("GET registry module health link", response.status_code, body[:2500]))

            response = client.get("/product/v10")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Module Health Console" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET v10 dashboard module health link", response.status_code)
            if not ok:
                failures.append(("GET v10 dashboard module health link", response.status_code, body[:2500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.5 product module health smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
