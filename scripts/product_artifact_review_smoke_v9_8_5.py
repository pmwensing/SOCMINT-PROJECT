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
    seeded = ROOT / "release" / "V9_8_5_REVIEW_SMOKE_ARTIFACT.md"
    seeded.parent.mkdir(exist_ok=True)
    seeded.write_text("# v9.8.5 review smoke artifact\n\nUsed to verify review-state persistence.\n")

    with tempfile.TemporaryDirectory(prefix="socmint-v985-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v985-artifact-review-smoke")

        path = "release/V9_8_5_REVIEW_SMOKE_ARTIFACT.md"

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v985-review-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v985-csrf"

            failures = []

            response = client.post(
                "/api/v1/product/artifacts/review",
                json={
                    "path": path,
                    "reviewed": True,
                    "important": True,
                    "archived": False,
                    "note": "smoke reviewed",
                },
                headers={"X-CSRF-Token": "v985-csrf"},
            )
            ok = response.status_code == 200 and response.is_json
            print(("[PASS]" if ok else "[FAIL]"), "POST review", response.status_code)
            if not ok:
                failures.append(("POST review", response.status_code, response.get_data(as_text=True)[:800]))

            response = client.get("/api/v1/product/artifact-review-state")
            data = response.get_json() if response.is_json else {}
            state = data.get("artifacts", {}).get(path, {})
            ok = (
                response.status_code == 200
                and state.get("reviewed") is True
                and state.get("important") is True
                and state.get("archived") is False
                and state.get("note") == "smoke reviewed"
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET review state", response.status_code)
            if not ok:
                failures.append(("GET review state", response.status_code, response.get_data(as_text=True)[:800]))

            response = client.get("/api/v1/product/artifacts?reviewed=true&important=true&archived=false")
            payload = response.get_json() if response.is_json else {}
            found = any(item.get("path") == path for item in payload.get("artifacts", []))
            ok = response.status_code == 200 and found
            print(("[PASS]" if ok else "[FAIL]"), "GET filtered artifacts", response.status_code)
            if not ok:
                failures.append(("GET filtered artifacts", response.status_code, response.get_data(as_text=True)[:1000]))

            response = client.get("/product/artifacts?reviewed=true")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Review Filters" in body and "reviewed=True" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET artifact UI filters", response.status_code)
            if not ok:
                failures.append(("GET artifact UI filters", response.status_code, body[:1000]))

            response = client.post(
                "/product/artifacts/review",
                data={
                    "path": path,
                    "reviewed": "1",
                    "important": "1",
                    "archived": "1",
                    "note": "form archived",
                    "csrf_token": "v985-csrf",
                },
                headers={"X-CSRF-Token": "v985-csrf"},
            )
            ok = response.status_code in {200, 302}
            print(("[PASS]" if ok else "[FAIL]"), "POST form review", response.status_code)
            if not ok:
                failures.append(("POST form review", response.status_code, response.get_data(as_text=True)[:800]))

            response = client.get("/api/v1/product/artifacts?archived=true")
            payload = response.get_json() if response.is_json else {}
            found = any(item.get("path") == path and item.get("archived") is True for item in payload.get("artifacts", []))
            ok = response.status_code == 200 and found
            print(("[PASS]" if ok else "[FAIL]"), "GET archived filter", response.status_code)
            if not ok:
                failures.append(("GET archived filter", response.status_code, response.get_data(as_text=True)[:1000]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.8.5 product artifact review smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
