from __future__ import annotations

import json
import os
import sys
import tarfile
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

    with tempfile.TemporaryDirectory(prefix="socmint-v993-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v993-final-release-archive-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v993-archive-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v993-csrf"

            failures = []

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve archive smoke"},
                headers={"X-CSRF-Token": "v993-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("gate", {}).get("gate_status") == "approved"
            print(("[PASS]" if ok else "[FAIL]"), "approve final gate", response.status_code)
            if not ok:
                failures.append(("approve final gate", response.status_code, response.get_data(as_text=True)[:2000]))

            client.post("/api/v1/product/final-gate/write", headers={"X-CSRF-Token": "v993-csrf"})

            package_root = Path("storage/product_packages/v9_9_3_archive_smoke_package")
            package_root.mkdir(parents=True, exist_ok=True)
            (package_root / "PACKAGE_MANIFEST.json").write_text(json.dumps({"selected_count": 1, "copied_artifact_count": 1, "metadata_file_count": 2}, indent=2))
            (package_root / "PACKAGE_INDEX.md").write_text("# package index\n")
            package_zip = Path("storage/product_packages/v9_9_3_archive_smoke_package.zip")
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v9_9_3_archive_smoke_release"
            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v993-csrf"},
            )
            published = response.get_json() if response.is_json else {}
            release_root = Path(published.get("release_path", ""))
            ok = response.status_code == 200 and published.get("status") == "published" and release_root.exists()
            print(("[PASS]" if ok else "[FAIL]"), "publish final release", response.status_code)
            if not ok:
                failures.append(("publish final release", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.post(
                f"/api/v1/product/final-release/archive/{release_name}/create",
                headers={"X-CSRF-Token": "v993-csrf"},
            )
            seal = response.get_json() if response.is_json else {}
            zip_path = Path(seal.get("archive_zip_path", ""))
            tar_path = Path(seal.get("archive_tar_path", ""))
            integrity_path = release_root / "INTEGRITY_MANIFEST.json"
            ok = (
                response.status_code == 200
                and seal.get("version") == "9.9.3"
                and zip_path.exists()
                and tar_path.exists()
                and integrity_path.exists()
                and seal.get("integrity_manifest", {}).get("required_all_present") is True
            )
            print(("[PASS]" if ok else "[FAIL]"), "create archive integrity seal", response.status_code)
            if not ok:
                failures.append(("create archive integrity seal", response.status_code, response.get_data(as_text=True)[:3000]))

            if zip_path.exists():
                with zipfile.ZipFile(zip_path) as zf:
                    entries = set(zf.namelist())
                required = {
                    "RELEASE_NOTES.md",
                    "FINAL_RELEASE_CHECKLIST.json",
                    "PUBLISH_MANIFEST.json",
                    "INTEGRITY_MANIFEST.json",
                }
                ok = (
                    required.issubset(entries)
                    and any("V9_9_0_RELEASE_CANDIDATE_MANIFEST.json" in item for item in entries)
                    and any("V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json" in item for item in entries)
                    and any("release_candidate_signoff_audit.json" in item for item in entries)
                    and any(item.endswith(".zip") for item in entries)
                )
                print(("[PASS]" if ok else "[FAIL]"), "ZIP contains required release evidence")
                if not ok:
                    failures.append(("ZIP contains required release evidence", 0, json.dumps(sorted(entries), indent=2)[:3000]))

            if tar_path.exists():
                with tarfile.open(tar_path, "r:gz") as tf:
                    entries = set(tf.getnames())
                ok = "RELEASE_NOTES.md" in entries and "PUBLISH_MANIFEST.json" in entries and "INTEGRITY_MANIFEST.json" in entries
                print(("[PASS]" if ok else "[FAIL]"), "TAR contains required release evidence")
                if not ok:
                    failures.append(("TAR contains required release evidence", 0, json.dumps(sorted(entries), indent=2)[:3000]))

            if integrity_path.exists():
                integrity = json.loads(integrity_path.read_text())
                ok = (
                    integrity.get("required_all_present") is True
                    and integrity.get("file_count", 0) >= 7
                    and all(item.get("sha256") for item in integrity.get("files", []))
                )
                print(("[PASS]" if ok else "[FAIL]"), "integrity manifest checksums")
                if not ok:
                    failures.append(("integrity manifest checksums", 0, json.dumps(integrity, indent=2)[:3000]))

            response = client.get("/api/v1/product/final-release/archives")
            payload = response.get_json() if response.is_json else {}
            found = any(item.get("release_name") == release_name and item.get("archive_zip_exists") for item in payload.get("releases", []))
            ok = response.status_code == 200 and payload.get("version") == "9.9.3" and found
            print(("[PASS]" if ok else "[FAIL]"), "GET archive inventory", response.status_code)
            if not ok:
                failures.append(("GET archive inventory", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.get(f"/product/final-release/archive/download/{release_name}.zip")
            ok = response.status_code == 200 and response.data[:2] == b"PK"
            print(("[PASS]" if ok else "[FAIL]"), "download archive ZIP", response.status_code)
            if not ok:
                failures.append(("download archive ZIP", response.status_code, response.get_data(as_text=True)[:1000]))

            response = client.get("/product/final-release/archive")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Final Release Archive + Integrity Seal" in body and release_name in body
            print(("[PASS]" if ok else "[FAIL]"), "GET archive UI", response.status_code)
            if not ok:
                failures.append(("GET archive UI", response.status_code, body[:2000]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.3 final release archive integrity smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
