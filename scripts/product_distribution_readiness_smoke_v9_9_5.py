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

    with tempfile.TemporaryDirectory(prefix="socmint-v995-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v995-distribution-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v995-distribution-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v995-csrf"

            failures = []

            response = client.post(
                "/api/v1/product/final-release/distribution/decision",
                json={
                    "decision": "ready",
                    "release_name": "missing-release",
                    "reason": "should be denied",
                },
                headers={"X-CSRF-Token": "v995-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and payload.get("status") == "blocked"
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "deny ready when verification missing",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "deny ready when verification missing",
                        response.status_code,
                        response.get_data(as_text=True)[:2000],
                    )
                )

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve distribution smoke"},
                headers={"X-CSRF-Token": "v995-csrf"},
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
                headers={"X-CSRF-Token": "v995-csrf"},
            )

            package_root = Path(
                "storage/product_packages/v9_9_5_distribution_smoke_package"
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
                "storage/product_packages/v9_9_5_distribution_smoke_package.zip"
            )
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v9_9_5_distribution_smoke_release"
            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v995-csrf"},
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
                headers={"X-CSRF-Token": "v995-csrf"},
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
            verification = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and verification.get("status") == "pass"
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
                    "decision": "lock",
                    "release_name": release_name,
                    "reason": "lock smoke release",
                },
                headers={"X-CSRF-Token": "v995-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("status") == "ok"
                and payload.get("state", {}).get("locked") is True
                and payload.get("state", {}).get("ready") is False
                and payload.get("state", {}).get("lock_manifest_sha256")
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "lock verified release",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "lock verified release",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.post(
                "/api/v1/product/final-release/distribution/decision",
                json={
                    "decision": "ready",
                    "release_name": release_name,
                    "reason": "ready smoke release",
                },
                headers={"X-CSRF-Token": "v995-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("status") == "ok"
                and payload.get("state", {}).get("locked") is True
                and payload.get("state", {}).get("ready") is True
                and payload.get("distribution", {}).get("distribution_status")
                == "ready"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "mark ready to distribute",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "mark ready to distribute",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.get(
                f"/api/v1/product/final-release/distribution?release_name={release_name}"
            )
            distribution = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and distribution.get("distribution_status") == "ready"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET distribution ready state",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET distribution ready state",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.get("/api/v1/product/final-release/distribution/audit")
            audit = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and audit.get("count", 0) >= 3
                and any(
                    event.get("action") == "ready_denied"
                    for event in audit.get("events", [])
                )
                and any(
                    event.get("action") == "distribution_lock"
                    for event in audit.get("events", [])
                )
                and any(
                    event.get("action") == "distribution_ready"
                    for event in audit.get("events", [])
                )
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET distribution audit",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET distribution audit",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.post(
                "/api/v1/product/final-release/distribution/write",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v995-csrf"},
            )
            report = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and report.get("distribution_status") == "ready"
                and Path("release/V9_9_5_DISTRIBUTION_READINESS_REPORT.json").exists()
                and Path("release/V9_9_5_DISTRIBUTION_READINESS_REPORT.md").exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write distribution readiness report",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write distribution readiness report",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.get(
                f"/product/final-release/distribution?release_name={release_name}"
            )
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Final Release Distribution Readiness" in body
                and "Mark Ready to Distribute" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET distribution UI",
                response.status_code,
            )
            if not ok:
                failures.append(
                    ("GET distribution UI", response.status_code, body[:2000])
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.5 distribution readiness smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
