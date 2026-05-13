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
    with tempfile.TemporaryDirectory(prefix="socmint-v984-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v984-product-artifacts-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v984-artifact-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v984-csrf"

            failures = []

            endpoints = [
                "/product/artifacts",
                "/api/v1/product/artifacts",
                "/product/build-control",
            ]

            artifact_payload = None
            for endpoint in endpoints:
                response = client.get(endpoint)
                body = response.get_data(as_text=True)
                ok = response.status_code == 200
                if endpoint == "/product/artifacts":
                    ok = ok and "Product Runtime History" in body and "Artifacts JSON" in body
                if endpoint == "/product/build-control":
                    ok = ok and "Runtime History" in body and "Product Artifact Browser" in body
                if endpoint == "/api/v1/product/artifacts":
                    ok = ok and response.is_json
                    if ok:
                        artifact_payload = response.get_json()
                        ok = artifact_payload.get("version") == "9.8.4" and artifact_payload.get("count", 0) > 0
                print(("[PASS]" if ok else "[FAIL]"), endpoint, response.status_code)
                if not ok:
                    failures.append((endpoint, response.status_code, body[:1000]))

            if artifact_payload and artifact_payload.get("artifacts"):
                first = artifact_payload["artifacts"][0]
                for endpoint in [first["view_url"], first["download_url"]]:
                    response = client.get(endpoint)
                    ok = response.status_code == 200
                    print(("[PASS]" if ok else "[FAIL]"), endpoint, response.status_code)
                    if not ok:
                        failures.append((endpoint, response.status_code, response.get_data(as_text=True)[:1000]))

            if failures:
                for endpoint, status, body in failures:
                    print(f"\n--- FAILURE {endpoint} {status} ---\n{body}")
                return 1

    print("v9.8.4 product artifact browser smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
