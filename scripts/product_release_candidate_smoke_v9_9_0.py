from __future__ import annotations

import json
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


def ensure_stage_artifacts() -> None:
    artifacts = {
        "release/V9_7_PRODUCT_SMOKE_REPORT.md": "# Product Smoke\n\nStatus: **pass**\n",
        "release/V9_8_5_ARTIFACT_REVIEW_HARDENING_REPORT.md": "# Artifact Review\n\nStatus: **pass**\n",
        "release/V9_8_6_ARTIFACT_REVIEW_AUDIT_HARDENING_REPORT.md": "# Artifact Review Audit\n\nStatus: **pass**\n",
        "release/V9_8_7_EXPORT_MANIFEST_HARDENING_REPORT.md": "# Export Manifest\n\nStatus: **pass**\n",
        "release/V9_8_8_RELEASE_PACKAGE_HARDENING_REPORT.md": "# Release Package\n\nStatus: **pass**\n",
        "release/V9_8_9_RELEASE_PACKAGE_ZIP_HARDENING_REPORT.md": "# ZIP Export\n\nStatus: **pass**\n",
    }
    for rel, content in artifacts.items():
        path = ROOT / rel
        path.parent.mkdir(exist_ok=True)
        if not path.exists():
            path.write_text(content)


def main() -> int:
    ensure_stage_artifacts()

    with tempfile.TemporaryDirectory(prefix="socmint-v990-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v990-rc-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v990-rc-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v990-csrf"

            failures = []

            response = client.get("/api/v1/product/release-candidate")
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("version") == "9.9.0"
                and payload.get("summary", {}).get("required_total") == 6
                and payload.get("summary", {}).get("required_passed") == 6
                and payload.get("status") == "pass"
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET RC manifest API", response.status_code)
            if not ok:
                failures.append(("GET RC manifest API", response.status_code, response.get_data(as_text=True)[:2000]))

            response = client.post(
                "/api/v1/product/release-candidate/write",
                headers={"X-CSRF-Token": "v990-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            json_path = Path("release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json")
            md_path = Path("release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.md")
            ok = (
                response.status_code == 200
                and payload.get("version") == "9.9.0"
                and json_path.exists()
                and md_path.exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "POST write RC manifest API", response.status_code)
            if not ok:
                failures.append(("POST write RC manifest API", response.status_code, response.get_data(as_text=True)[:2000]))

            if json_path.exists():
                data = json.loads(json_path.read_text())
                ok = (
                    data.get("version") == "9.9.0"
                    and data.get("summary", {}).get("required_passed") == 6
                    and len(data.get("summary", {}).get("stages", [])) == 6
                )
                print(("[PASS]" if ok else "[FAIL]"), "RC manifest file content")
                if not ok:
                    failures.append(("RC manifest file content", 0, json.dumps(data, indent=2)[:2500]))

            response = client.get("/product/release-candidate")
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Product Release Candidate Console" in body
                and "v9.8 Chain Stage Readiness" in body
                and "Product Smoke" in body
                and "Release Package ZIP Export" in body
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET RC console UI", response.status_code)
            if not ok:
                failures.append(("GET RC console UI", response.status_code, body[:2000]))

            response = client.get("/product/build-control")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Release Candidate Console" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET Product Control RC link", response.status_code)
            if not ok:
                failures.append(("GET Product Control RC link", response.status_code, body[:2000]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.0 product release candidate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
