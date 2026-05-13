from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from socmint import database as db  # noqa: E402
from socmint.dashboard import create_app  # noqa: E402


STAGE_ARTIFACTS = {
    "release/V9_7_PRODUCT_SMOKE_REPORT.md": "# Product Smoke\n\nStatus: **pass**\n",
    "release/V9_8_5_ARTIFACT_REVIEW_HARDENING_REPORT.md": "# Artifact Review\n\nStatus: **pass**\n",
    "release/V9_8_6_ARTIFACT_REVIEW_AUDIT_HARDENING_REPORT.md": "# Artifact Review Audit\n\nStatus: **pass**\n",
    "release/V9_8_7_EXPORT_MANIFEST_HARDENING_REPORT.md": "# Export Manifest\n\nStatus: **pass**\n",
    "release/V9_8_8_RELEASE_PACKAGE_HARDENING_REPORT.md": "# Release Package\n\nStatus: **pass**\n",
    "release/V9_8_9_RELEASE_PACKAGE_ZIP_HARDENING_REPORT.md": "# ZIP Export\n\nStatus: **pass**\n",
}


def write_stage_artifacts() -> None:
    for rel, content in STAGE_ARTIFACTS.items():
        path = ROOT / rel
        path.parent.mkdir(exist_ok=True)
        path.write_text(content)


def main() -> int:
    write_stage_artifacts()

    with tempfile.TemporaryDirectory(prefix="socmint-v994-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v994-final-release-verify-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v994-verify-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v994-csrf"

            failures = []

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve verify smoke"},
                headers={"X-CSRF-Token": "v994-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("gate", {}).get("gate_status") == "approved"
            print(("[PASS]" if ok else "[FAIL]"), "approve final gate", response.status_code)
            if not ok:
                failures.append(("approve final gate", response.status_code, response.get_data(as_text=True)[:2000]))

            client.post("/api/v1/product/final-gate/write", headers={"X-CSRF-Token": "v994-csrf"})

            package_root = Path("storage/product_packages/v9_9_4_verify_smoke_package")
            package_root.mkdir(parents=True, exist_ok=True)
            (package_root / "PACKAGE_MANIFEST.json").write_text(json.dumps({"selected_count": 1, "copied_artifact_count": 1, "metadata_file_count": 2}, indent=2))
            (package_root / "PACKAGE_INDEX.md").write_text("# package index\n")
            package_zip = Path("storage/product_packages/v9_9_4_verify_smoke_package.zip")
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v9_9_4_verify_smoke_release"
            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v994-csrf"},
            )
            published = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and published.get("status") == "published"
            print(("[PASS]" if ok else "[FAIL]"), "publish final release", response.status_code)
            if not ok:
                failures.append(("publish final release", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.post(
                f"/api/v1/product/final-release/archive/{release_name}/create",
                headers={"X-CSRF-Token": "v994-csrf"},
            )
            seal = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and seal.get("version") == "9.9.3"
            print(("[PASS]" if ok else "[FAIL]"), "create archive seal", response.status_code)
            if not ok:
                failures.append(("create archive seal", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.get(f"/api/v1/product/final-release/verify?release_name={release_name}")
            verification = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and verification.get("version") == "9.9.4"
                and verification.get("status") == "pass"
                and verification.get("checks_passed") == verification.get("checks_total")
                and "archive_zip_checksum" not in verification.get("failures", [])
                and "archive_tar_checksum" not in verification.get("failures", [])
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET final release verification API", response.status_code)
            if not ok:
                failures.append(("GET final release verification API", response.status_code, response.get_data(as_text=True)[:3000]))

            report_json = Path("release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.json")
            report_md = Path("release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.md")
            ok = report_json.exists() and report_md.exists()
            print(("[PASS]" if ok else "[FAIL]"), "verification report artifacts")
            if not ok:
                failures.append(("verification report artifacts", 0, "missing v9.9.4 verification reports"))

            response = client.get(f"/product/final-release/verify?release_name={release_name}")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Final Release Verification Console" in body and release_name in body and "PASS" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET verification UI", response.status_code)
            if not ok:
                failures.append(("GET verification UI", response.status_code, body[:2000]))

            response = client.get(f"/product/final-release/archive/download/{release_name}.zip")
            ok = response.status_code == 200 and response.data[:2] == b"PK"
            print(("[PASS]" if ok else "[FAIL]"), "download verified ZIP", response.status_code)
            if not ok:
                failures.append(("download verified ZIP", response.status_code, response.get_data(as_text=True)[:1000]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.4 final release verification smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
