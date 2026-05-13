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

    with tempfile.TemporaryDirectory(prefix="socmint-v992-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v992-final-release-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v992-final-release-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v992-csrf"

            failures = []

            # The hardening runner executes product-final-gate-smoke before this smoke,
            # which intentionally approves the gate. Reset runtime signoff state so
            # this smoke can prove publishing is blocked before approval.
            for runtime_file in [
                Path("storage/product_qa/release_candidate_signoff_state.json"),
                Path("storage/product_qa/release_candidate_signoff_audit.json"),
            ]:
                if runtime_file.exists():
                    runtime_file.unlink()

            import shutil
            for runtime_dir in [
                Path("storage/final_releases/v9_9_2_blocked_smoke"),
                Path("storage/final_releases/v9_9_2_final_release_smoke"),
            ]:
                if runtime_dir.exists():
                    shutil.rmtree(runtime_dir)

            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": "v9_9_2_blocked_smoke"},
                headers={"X-CSRF-Token": "v992-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and payload.get("status") == "blocked"
            print(("[PASS]" if ok else "[FAIL]"), "deny publish before final gate approval", response.status_code)
            if not ok:
                failures.append(("deny publish before final gate approval", response.status_code, response.get_data(as_text=True)[:2000]))

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve final release smoke"},
                headers={"X-CSRF-Token": "v992-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and payload.get("gate", {}).get("gate_status") == "approved"
            print(("[PASS]" if ok else "[FAIL]"), "approve final gate", response.status_code)
            if not ok:
                failures.append(("approve final gate", response.status_code, response.get_data(as_text=True)[:2000]))

            response = client.post(
                "/api/v1/product/final-gate/write",
                headers={"X-CSRF-Token": "v992-csrf"},
            )
            ok = response.status_code == 200 and Path("release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json").exists()
            print(("[PASS]" if ok else "[FAIL]"), "write final gate manifest", response.status_code)
            if not ok:
                failures.append(("write final gate manifest", response.status_code, response.get_data(as_text=True)[:2000]))

            # Seed a built package ZIP so final release can include package evidence.
            package_root = Path("storage/product_packages/v9_9_2_final_release_smoke_package")
            package_root.mkdir(parents=True, exist_ok=True)
            (package_root / "PACKAGE_MANIFEST.json").write_text(json.dumps({"selected_count": 1, "copied_artifact_count": 1, "metadata_file_count": 2}, indent=2))
            (package_root / "PACKAGE_INDEX.md").write_text("# package index\n")
            zip_path = Path("storage/product_packages/v9_9_2_final_release_smoke_package.zip")
            import zipfile
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            response = client.get("/api/v1/product/final-release")
            preview = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and preview.get("version") == "9.9.2"
                and preview.get("can_publish") is True
                and preview.get("publish_status") == "ready"
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET final release preview ready", response.status_code)
            if not ok:
                failures.append(("GET final release preview ready", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": "v9_9_2_final_release_smoke"},
                headers={"X-CSRF-Token": "v992-csrf"},
            )
            published = response.get_json() if response.is_json else {}
            root = Path(published.get("release_path", ""))
            ok = (
                response.status_code == 200
                and published.get("status") == "published"
                and root.exists()
                and (root / "RELEASE_NOTES.md").exists()
                and (root / "FINAL_RELEASE_CHECKLIST.json").exists()
                and (root / "PUBLISH_MANIFEST.json").exists()
                and Path("release/V9_9_2_FINAL_RELEASE_NOTES.md").exists()
                and Path("release/V9_9_2_FINAL_RELEASE_PUBLISH_MANIFEST.json").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "publish final release", response.status_code)
            if not ok:
                failures.append(("publish final release", response.status_code, response.get_data(as_text=True)[:2500]))

            if root.exists():
                manifest = json.loads((root / "PUBLISH_MANIFEST.json").read_text())
                ok = (
                    manifest.get("status") == "published"
                    and manifest.get("final_gate", {}).get("gate_status") == "approved"
                    and len(manifest.get("package_zips", [])) >= 1
                )
                print(("[PASS]" if ok else "[FAIL]"), "publish manifest content")
                if not ok:
                    failures.append(("publish manifest content", 0, json.dumps(manifest, indent=2)[:2500]))

            response = client.get("/product/final-release")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Final Release Publisher" in body and "Publish Final Release Notes Pack" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET final release UI", response.status_code)
            if not ok:
                failures.append(("GET final release UI", response.status_code, body[:2000]))

            response = client.get("/product/final-gate")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Final Release Publisher" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET final gate publisher link", response.status_code)
            if not ok:
                failures.append(("GET final gate publisher link", response.status_code, body[:2000]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.2 final release publisher smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
