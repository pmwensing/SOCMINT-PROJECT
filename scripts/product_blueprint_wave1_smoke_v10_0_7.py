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


WAVE1_ROUTES = {
    "/product/release-candidate": "product_release_flow",
    "/api/v1/product/release-candidate": "product_release_flow",
    "/product/final-gate": "product_release_flow",
    "/api/v1/product/final-gate": "product_release_flow",
    "/product/final": "product_post_release",
    "/api/v1/product/final": "product_post_release",
    "/product/final/handoff": "product_post_release",
    "/api/v1/product/final/handoff": "product_post_release",
    "/product/final/self-test": "product_post_release",
    "/api/v1/product/final/self-test": "product_post_release",
    "/product/final/v10-bootstrap": "product_post_release",
    "/api/v1/product/final/v10-bootstrap": "product_post_release",
    "/product/artifacts": "product_artifacts",
    "/api/v1/product/artifacts": "product_artifacts",
    "/product/release-package": "product_artifacts",
    "/api/v1/product/release-package": "product_artifacts",
}


def first_endpoint_for(app, route: str) -> str | None:
    for rule in app.url_map.iter_rules():
        if rule.rule == route:
            return rule.endpoint
    return None


def has_dashboard_fallback(app, route: str) -> bool:
    return any(
        rule.rule == route and rule.endpoint.startswith("dashboard.")
        for rule in app.url_map.iter_rules()
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="socmint-v1007-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1007-wave1-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1007-wave1-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1007-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/migration-plan")
            plan = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and plan.get("status") == "ready"
                and plan.get("module_health_status") == "healthy"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "migration plan ready gate",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "migration plan ready gate",
                        response.status_code,
                        response.get_data(as_text=True)[:4000],
                    )
                )

            for route, owner in WAVE1_ROUTES.items():
                endpoint = first_endpoint_for(app, route)
                ok = bool(endpoint and endpoint.startswith(owner + "."))
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    f"endpoint ownership {route}",
                    endpoint,
                )
                if not ok:
                    failures.append(
                        (
                            f"endpoint ownership {route}",
                            0,
                            f"endpoint={endpoint!r}, expected={owner!r}",
                        )
                    )

                ok = has_dashboard_fallback(app, route)
                print(("[PASS]" if ok else "[FAIL]"), f"dashboard fallback {route}", 0)
                if not ok:
                    failures.append(
                        (f"dashboard fallback {route}", 0, "missing dashboard fallback")
                    )

                response = client.get(route)
                ok = response.status_code == 200
                print(
                    ("[PASS]" if ok else "[FAIL]"), f"GET {route}", response.status_code
                )
                if not ok:
                    failures.append(
                        (
                            f"GET {route}",
                            response.status_code,
                            response.get_data(as_text=True)[:2000],
                        )
                    )

            response = client.get("/api/v1/product/v10/route-ownership")
            ownership = response.get_json() if response.is_json else {}
            ownership_rows = {
                row.get("route"): row
                for row in ownership.get("ownership", [])
                if row.get("route") in WAVE1_ROUTES
            }
            ok = (
                response.status_code == 200
                and len(ownership_rows) == len(WAVE1_ROUTES)
                and all(
                    row.get("ownership") == "blueprint-owned"
                    for row in ownership_rows.values()
                )
                and all(
                    row.get("wave1_blueprint_owned") is True
                    for row in ownership_rows.values()
                )
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "ownership map shows wave1 blueprint-owned",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "ownership map shows wave1 blueprint-owned",
                        response.status_code,
                        response.get_data(as_text=True)[:6000],
                    )
                )

            response = client.get("/api/v1/product/v10/module-health")
            health = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and health.get("status") == "healthy"
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "module health remains healthy",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "module health remains healthy",
                        response.status_code,
                        response.get_data(as_text=True)[:4000],
                    )
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.7 blueprint migration wave 1 smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
