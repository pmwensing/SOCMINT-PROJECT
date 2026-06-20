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
    with tempfile.TemporaryDirectory(prefix="socmint-v982-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v982-product-ux-smoke")

        endpoints = [
            "/",
            "/product/build-control",
            "/product/operator-runbook",
            "/api/v1/product/operator-runbook",
            "/api/v1/product/build-status",
            "/api/v1/product/release-readiness",
            "/api/v1/dossier/demo-subject/quality-gate",
            "/api/v1/dossier/demo-subject/traceability",
        ]

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v982-ux-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v982-csrf"

            failures = []
            for endpoint in endpoints:
                response = client.get(endpoint)
                body = response.get_data(as_text=True)
                ok = response.status_code == 200
                if endpoint == "/":
                    ok = (
                        ok
                        and "Product Release Readiness" in body
                        and "Product Control" in body
                    )
                if endpoint == "/product/build-control":
                    ok = ok and "Operator Actions" in body
                if endpoint == "/product/operator-runbook":
                    ok = ok and "Release Workflow" in body
                print(("[PASS]" if ok else "[FAIL]"), endpoint, response.status_code)
                if not ok:
                    failures.append((endpoint, response.status_code, body[:800]))

            if failures:
                for endpoint, status, body in failures:
                    print(f"\n--- FAILURE {endpoint} {status} ---\n{body}")
                return 1

    print("v9.8.2 product UX smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
