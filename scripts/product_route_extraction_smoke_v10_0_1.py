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
from socmint.product_release_flow import product_release_flow_manifest  # noqa: E402


def main() -> int:
    manifest = product_release_flow_manifest()
    if manifest.get("status") != "ok":
        print("[FAIL] product_release_flow manifest")
        return 1

    with tempfile.TemporaryDirectory(prefix="socmint-v1001-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1001-route-extraction-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1001-route-extraction-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1001-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/architecture")
            architecture = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and architecture.get("version") == "10.0.0"
                and architecture.get("compatibility", {}).get("missing") == []
                and "product_release_flow.product_release_flow_manifest"
                in architecture.get("foundation", {}).get("extracted_modules", [])
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "v10 architecture includes extracted module",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "v10 architecture includes extracted module",
                        response.status_code,
                        response.get_data(as_text=True)[:4000],
                    )
                )

            required_routes = [
                "/product/release-candidate",
                "/api/v1/product/release-candidate",
                "/product/final-gate",
                "/api/v1/product/final-gate",
                "/product/final-release",
                "/api/v1/product/final-release",
                "/product/final-release/archive",
                "/api/v1/product/final-release/archives",
                "/product/final-release/verify",
                "/api/v1/product/final-release/verify",
                "/product/final",
                "/api/v1/product/final",
                "/product/final/v10-bootstrap",
                "/api/v1/product/final/v10-bootstrap",
            ]

            for route in required_routes:
                response = client.get(route)
                ok = response.status_code == 200
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    f"compat GET {route}",
                    response.status_code,
                )
                if not ok:
                    failures.append(
                        (
                            f"compat GET {route}",
                            response.status_code,
                            response.get_data(as_text=True)[:1500],
                        )
                    )

            response = client.post(
                "/api/v1/product/v10/architecture/write",
                headers={"X-CSRF-Token": "v1001-csrf"},
            )
            ok = (
                response.status_code == 200
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.json").exists()
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.md").exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write v10 architecture manifest",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write v10 architecture manifest",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.1 product route extraction smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
