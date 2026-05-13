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
from socmint.product_artifacts import product_artifacts_manifest  # noqa: E402
from socmint.product_post_release import product_post_release_manifest  # noqa: E402
from socmint.product_release_flow import product_release_flow_manifest  # noqa: E402


def main() -> int:
    manifests = [
        product_release_flow_manifest(),
        product_post_release_manifest(),
        product_artifacts_manifest(),
    ]
    if any(item.get("status") != "ok" for item in manifests):
        print("[FAIL] extracted module manifests")
        return 1

    with tempfile.TemporaryDirectory(prefix="socmint-v1004-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1004-module-registry-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1004-module-registry-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1004-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/modules")
            registry = response.get_json() if response.is_json else {}
            module_names = {item.get("module") for item in registry.get("modules", [])}
            ok = (
                response.status_code == 200
                and registry.get("version") == "10.0.4"
                and registry.get("status") == "ok"
                and "socmint.product_release_flow" in module_names
                and "socmint.product_post_release" in module_names
                and "socmint.product_artifacts" in module_names
                and registry.get("missing_route_count") == 0
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET module registry API", response.status_code)
            if not ok:
                failures.append(("GET module registry API", response.status_code, response.get_data(as_text=True)[:5000]))

            response = client.get("/api/v1/product/v10/route-ownership")
            ownership = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and ownership.get("version") == "10.0.4"
                and ownership.get("missing_route_count") == 0
                and ownership.get("present_route_count", 0) >= 20
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET route ownership API", response.status_code)
            if not ok:
                failures.append(("GET route ownership API", response.status_code, response.get_data(as_text=True)[:5000]))

            response = client.get("/product/v10/modules")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Product Module Registry" in body and "Route Ownership Map" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET module registry UI", response.status_code)
            if not ok:
                failures.append(("GET module registry UI", response.status_code, body[:2500]))

            response = client.get("/product/v10")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Product Module Registry" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET v10 dashboard registry link", response.status_code)
            if not ok:
                failures.append(("GET v10 dashboard registry link", response.status_code, body[:2500]))

            response = client.post("/api/v1/product/v10/modules/write", headers={"X-CSRF-Token": "v1004-csrf"})
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("version") == "10.0.4"
                and Path("release/V10_0_4_PRODUCT_MODULE_REGISTRY.json").exists()
                and Path("release/V10_0_4_PRODUCT_MODULE_REGISTRY.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "write product module registry", response.status_code)
            if not ok:
                failures.append(("write product module registry", response.status_code, response.get_data(as_text=True)[:3000]))

            compatibility_routes = [
                "/product/release-candidate",
                "/product/final-gate",
                "/product/final-release",
                "/product/artifacts",
                "/product/release-package",
                "/product/final",
                "/product/final/handoff",
                "/product/final/self-test",
                "/product/final/v10-bootstrap",
            ]

            for route in compatibility_routes:
                response = client.get(route)
                ok = response.status_code == 200
                print(("[PASS]" if ok else "[FAIL]"), f"compat route {route}", response.status_code)
                if not ok:
                    failures.append((f"compat route {route}", response.status_code, response.get_data(as_text=True)[:1800]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.4 product module registry smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
