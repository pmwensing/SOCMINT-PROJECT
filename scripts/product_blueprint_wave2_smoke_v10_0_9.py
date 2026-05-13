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


WAVE2_ROUTES = {
    "/api/v1/product/final-release": "product_release_flow",
    "/api/v1/product/artifact-review-state": "product_artifacts",
    "/api/v1/product/artifact-review-audit": "product_artifacts",
    "/api/v1/product/artifact-export-manifest": "product_artifacts",
    "/api/v1/product/release-packages": "product_artifacts",
}

FORBIDDEN = ("write", "build", "download", "archive", "publish", "decision", "signoff")


def first_endpoint_for(app, route: str) -> str | None:
    for rule in app.url_map.iter_rules():
        if rule.rule == route:
            return rule.endpoint
    return None


def has_dashboard_fallback(app, route: str) -> bool:
    return any(rule.rule == route and rule.endpoint.startswith("dashboard.") for rule in app.url_map.iter_rules())


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="socmint-v1009-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1009-wave2-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1009-wave2-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1009-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/blueprint-guardrails")
            wave1 = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and wave1.get("status") == "pass"
            print(("[PASS]" if ok else "[FAIL]"), "Wave 1 guardrails still pass", response.status_code)
            if not ok:
                failures.append(("Wave 1 guardrails still pass", response.status_code, response.get_data(as_text=True)[:4000]))

            for route, owner in WAVE2_ROUTES.items():
                endpoint = first_endpoint_for(app, route)
                ok = bool(endpoint and endpoint.startswith(owner + "."))
                print(("[PASS]" if ok else "[FAIL]"), f"Wave 2 endpoint ownership {route}", endpoint)
                if not ok:
                    failures.append((f"Wave 2 endpoint ownership {route}", 0, f"endpoint={endpoint!r}, expected={owner!r}"))

                ok = has_dashboard_fallback(app, route)
                print(("[PASS]" if ok else "[FAIL]"), f"Wave 2 dashboard fallback {route}", 0)
                if not ok:
                    failures.append((f"Wave 2 dashboard fallback {route}", 0, "missing dashboard fallback"))

                ok = not any(token in route.lower() for token in FORBIDDEN)
                print(("[PASS]" if ok else "[FAIL]"), f"Wave 2 no blocked action token {route}", 0)
                if not ok:
                    failures.append((f"Wave 2 blocked action token {route}", 0, route))

                response = client.get(route)
                ok = response.status_code == 200
                print(("[PASS]" if ok else "[FAIL]"), f"GET Wave 2 moved route {route}", response.status_code)
                if not ok:
                    failures.append((f"GET Wave 2 moved route {route}", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.get("/api/v1/product/v10/blueprint-wave2")
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("version") == "10.0.9"
                and payload.get("status") == "pass"
                and payload.get("wave1_status") == "pass"
                and payload.get("wave2_route_count") == len(WAVE2_ROUTES)
                and payload.get("wave2_failed_route_count") == 0
                and payload.get("no_post_write_build_download_archive_routes_moved") is True
                and payload.get("rollback_ready_count") == len(WAVE2_ROUTES)
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET Wave 2 API", response.status_code)
            if not ok:
                failures.append(("GET Wave 2 API", response.status_code, response.get_data(as_text=True)[:7000]))

            response = client.post("/api/v1/product/v10/blueprint-wave2/write", headers={"X-CSRF-Token": "v1009-csrf"})
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and written.get("version") == "10.0.9"
                and written.get("status") == "pass"
                and Path("release/V10_0_9_BLUEPRINT_WAVE2_REPORT.json").exists()
                and Path("release/V10_0_9_BLUEPRINT_WAVE2_REPORT.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "write Wave 2 report", response.status_code)
            if not ok:
                failures.append(("write Wave 2 report", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.get("/product/v10/blueprint-wave2")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Blueprint Migration Wave 2" in body and "Wave 2 Routes" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET Wave 2 UI", response.status_code)
            if not ok:
                failures.append(("GET Wave 2 UI", response.status_code, body[:2500]))

            for route in ["/product/v10", "/product/v10/blueprint-guardrails", "/product/v10/migration-plan"]:
                response = client.get(route)
                body = response.get_data(as_text=True)
                ok = response.status_code == 200 and "Open Blueprint Wave 2" in body
                print(("[PASS]" if ok else "[FAIL]"), f"Wave 2 link {route}", response.status_code)
                if not ok:
                    failures.append((f"Wave 2 link {route}", response.status_code, body[:2500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.9 blueprint wave 2 smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
