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
    with tempfile.TemporaryDirectory(prefix="socmint-v983-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v983-runtime-actions-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v983-runtime-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v983-csrf"

            get_checks = [
                "/product/build-control",
                "/api/v1/product/runtime-actions",
                "/api/v1/product/build-status",
                "/api/v1/product/release-readiness",
            ]

            failures = []
            for endpoint in get_checks:
                response = client.get(endpoint)
                body = response.get_data(as_text=True)
                ok = response.status_code == 200
                if endpoint == "/product/build-control":
                    ok = ok and "Runtime Actions" in body
                if endpoint == "/api/v1/product/runtime-actions":
                    ok = ok and response.is_json and response.get_json().get("version") == "9.8.3"
                print(("[PASS]" if ok else "[FAIL]"), "GET", endpoint, response.status_code)
                if not ok:
                    failures.append(("GET", endpoint, response.status_code, body[:800]))

            post_checks = [
                "/api/v1/product/actions/write-reports",
                "/api/v1/product/actions/export-control-snapshot",
                "/product/actions/refresh-readiness",
                "/product/actions/write-reports",
                "/product/actions/export-control-snapshot",
            ]

            for endpoint in post_checks:
                response = client.post(endpoint, headers={"X-CSRF-Token": "v983-csrf"})
                ok = response.status_code in {200, 302}
                print(("[PASS]" if ok else "[FAIL]"), "POST", endpoint, response.status_code)
                if not ok:
                    failures.append(("POST", endpoint, response.status_code, response.get_data(as_text=True)[:800]))

            if failures:
                for method, endpoint, status, body in failures:
                    print(f"\n--- FAILURE {method} {endpoint} {status} ---\n{body}")
                return 1

    print("v9.8.3 product runtime actions smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
