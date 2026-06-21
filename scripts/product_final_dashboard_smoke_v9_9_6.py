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

    with tempfile.TemporaryDirectory(prefix="socmint-v996-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v996-final-dashboard-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v996-final-dashboard-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v996-csrf"

            failures = []

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve final dashboard smoke"},
                headers={"X-CSRF-Token": "v996-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("gate", {}).get("gate_status") == "approved"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "approve final gate",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "approve final gate",
                        response.status_code,
                        response.get_data(as_text=True)[:2000],
                    )
                )

            client.post(
                "/api/v1/product/final-gate/write",
                headers={"X-CSRF-Token": "v996-csrf"},
            )

            package_root = Path(
                "storage/product_packages/v9_9_6_final_dashboard_package"
            )
            package_root.mkdir(parents=True, exist_ok=True)
            (package_root / "PACKAGE_MANIFEST.json").write_text(
                json.dumps(
                    {
                        "selected_count": 1,
                        "copied_artifact_count": 1,
                        "metadata_file_count": 2,
                    },
                    indent=2,
                )
            )
            (package_root / "PACKAGE_INDEX.md").write_text("# package index\n")
            package_zip = Path(
                "storage/product_packages/v9_9_6_final_dashboard_package.zip"
            )
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v9_9_6_final_dashboard_release"
            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v996-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("status") == "published"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "publish final release",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "publish final release",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.post(
                f"/api/v1/product/final-release/archive/{release_name}/create",
                headers={"X-CSRF-Token": "v996-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("version") == "9.9.3"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "create archive seal",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "create archive seal",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.get(
                f"/api/v1/product/final-release/verify?release_name={release_name}"
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("status") == "pass"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "verify final release",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "verify final release",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final-release/distribution/decision",
                json={
                    "decision": "ready",
                    "release_name": release_name,
                    "reason": "ready final dashboard smoke",
                },
                headers={"X-CSRF-Token": "v996-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("state", {}).get("ready") is True
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "mark distribution ready",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "mark distribution ready",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get(f"/api/v1/product/final?release_name={release_name}")
            final_payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and final_payload.get("version") == "9.9.6"
                and final_payload.get("status") == "ready"
                and final_payload.get("distribution_ready") is True
                and final_payload.get("version_freeze", {}).get("final_version")
                == "v9.9.6"
                and final_payload.get("chain", {}).get("distribution", {}).get("ready")
                is True
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET final dashboard API",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET final dashboard API",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/write",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v996-csrf"},
            )
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and written.get("status") == "ready"
                and Path("release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.json").exists()
                and Path("release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.md").exists()
                and Path("release/V9_9_6_FINAL_PRODUCT_VERSION_FREEZE.json").exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write final product release index",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write final product release index",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get(f"/product/final?release_name={release_name}")
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Final Product Release Dashboard" in body
                and "v9.9.6" in body
                and "Distribution" in body
                and "READY" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET final product dashboard UI",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET final product dashboard UI",
                        response.status_code,
                        body[:2500],
                    )
                )

            response = client.get("/product/final-release/distribution")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Final Product Dashboard" in body
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET distribution final dashboard link",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET distribution final dashboard link",
                        response.status_code,
                        body[:2000],
                    )
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.6 final product dashboard smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
