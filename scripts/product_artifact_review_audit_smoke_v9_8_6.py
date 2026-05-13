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
    seeded = ROOT / "release" / "V9_8_6_AUDIT_SMOKE_ARTIFACT.md"
    seeded.parent.mkdir(exist_ok=True)
    seeded.write_text("# v9.8.6 audit smoke artifact\n\nUsed to verify review audit persistence.\n")

    with tempfile.TemporaryDirectory(prefix="socmint-v986-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v986-artifact-audit-smoke")

        path = "release/V9_8_6_AUDIT_SMOKE_ARTIFACT.md"

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v986-audit-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v986-csrf"

            failures = []

            updates = [
                {
                    "path": path,
                    "reviewed": True,
                    "important": False,
                    "archived": False,
                    "note": "first audit state",
                },
                {
                    "path": path,
                    "reviewed": True,
                    "important": True,
                    "archived": True,
                    "note": "second audit state",
                },
            ]

            for idx, payload in enumerate(updates, start=1):
                response = client.post(
                    "/api/v1/product/artifacts/review",
                    json=payload,
                    headers={"X-CSRF-Token": "v986-csrf"},
                )
                ok = response.status_code == 200 and response.is_json
                if ok:
                    data = response.get_json()
                    ok = data.get("audit_event", {}).get("path") == path
                print(("[PASS]" if ok else "[FAIL]"), f"POST audit update {idx}", response.status_code)
                if not ok:
                    failures.append((f"POST audit update {idx}", response.status_code, response.get_data(as_text=True)[:1000]))

            response = client.get(f"/api/v1/product/artifact-review-audit?path={path}")
            data = response.get_json() if response.is_json else {}
            events = data.get("events", [])
            ok = response.status_code == 200 and len(events) >= 2
            if ok:
                latest = events[-1]
                ok = (
                    latest.get("before", {}).get("important") is False
                    and latest.get("after", {}).get("important") is True
                    and latest.get("after", {}).get("archived") is True
                    and "important" in latest.get("changed_fields", [])
                    and "archived" in latest.get("changed_fields", [])
                )
            print(("[PASS]" if ok else "[FAIL]"), "GET artifact audit JSON", response.status_code)
            if not ok:
                failures.append(("GET artifact audit JSON", response.status_code, response.get_data(as_text=True)[:1500]))

            response = client.get(f"/product/artifacts/audit/{path}")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Artifact Review Audit Trail" in body and "second audit state" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET artifact audit UI", response.status_code)
            if not ok:
                failures.append(("GET artifact audit UI", response.status_code, body[:1500]))

            response = client.get("/product/artifacts")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Artifact Audit Trail" in body and "/product/artifacts/audit/" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET artifact browser audit links", response.status_code)
            if not ok:
                failures.append(("GET artifact browser audit links", response.status_code, body[:1500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.8.6 product artifact review audit smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
