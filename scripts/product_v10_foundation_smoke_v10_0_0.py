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
    with tempfile.TemporaryDirectory(prefix="socmint-v1000-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1000-product-foundation-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1000-product-foundation-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1000-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/architecture")
            architecture = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and architecture.get("version") == "10.0.0"
                and architecture.get("compatibility", {}).get("required_route_count", 0) >= 10
                and architecture.get("compatibility", {}).get("missing") == []
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET v10 architecture API", response.status_code)
            if not ok:
                failures.append(("GET v10 architecture API", response.status_code, response.get_data(as_text=True)[:4000]))

            response = client.get("/api/v1/product/v10/compatibility")
            compatibility = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and compatibility.get("version") == "10.0.0"
                and compatibility.get("compatibility", {}).get("missing") == []
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET v10 compatibility API", response.status_code)
            if not ok:
                failures.append(("GET v10 compatibility API", response.status_code, response.get_data(as_text=True)[:4000]))

            response = client.post("/api/v1/product/v10/architecture/write", headers={"X-CSRF-Token": "v1000-csrf"})
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("version") == "10.0.0"
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.json").exists()
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "POST v10 architecture manifest write", response.status_code)
            if not ok:
                failures.append(("POST v10 architecture manifest write", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.get("/product/v10")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Product v10 Foundation" in body and "v9.9.x Compatibility Routes" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET v10 foundation UI", response.status_code)
            if not ok:
                failures.append(("GET v10 foundation UI", response.status_code, body[:2500]))

            # Migration-safe compatibility checks: these v9.9.x final routes must still respond.
            v9_routes = [
                "/product/final/v10-bootstrap",
                "/api/v1/product/final/v10-bootstrap",
                "/product/final/self-test",
                "/api/v1/product/final/self-test",
                "/product/final/handoff",
                "/api/v1/product/final/handoff",
                "/product/final",
                "/api/v1/product/final",
                "/product/final-release/distribution",
                "/api/v1/product/final-release/distribution",
                "/product/final-release/verify",
                "/api/v1/product/final-release/verify",
                "/product/final-release/archive",
                "/api/v1/product/final-release/archives",
                "/product/final-release",
                "/api/v1/product/final-release",
                "/product/final-gate",
                "/api/v1/product/final-gate",
                "/product/release-candidate",
            ]

            for route in v9_routes:
                response = client.get(route)
                ok = response.status_code == 200
                print(("[PASS]" if ok else "[FAIL]"), f"compat route {route}", response.status_code)
                if not ok:
                    failures.append((f"compat route {route}", response.status_code, response.get_data(as_text=True)[:1000]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.0 product foundation smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
