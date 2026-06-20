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

    with tempfile.TemporaryDirectory(prefix="socmint-v999-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v999-bootstrap-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v999-bootstrap-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v999-csrf"

            failures = []

            response = client.post(
                "/api/v1/product/final/v10-bootstrap/decision",
                json={
                    "decision": "approve_v10_bootstrap",
                    "release_name": "missing-release",
                    "reason": "should be denied",
                },
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and payload.get("status") == "blocked"
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "deny v10 bootstrap before v9.9.8 safe gate",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "deny v10 bootstrap before v9.9.8 safe gate",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve bootstrap smoke"},
                headers={"X-CSRF-Token": "v999-csrf"},
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
                headers={"X-CSRF-Token": "v999-csrf"},
            )

            package_root = Path("storage/product_packages/v9_9_9_bootstrap_package")
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
            package_zip = Path("storage/product_packages/v9_9_9_bootstrap_package.zip")
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v9_9_9_bootstrap_release"

            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v999-csrf"},
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
                headers={"X-CSRF-Token": "v999-csrf"},
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
                    "reason": "ready bootstrap smoke",
                },
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("state", {}).get("ready") is True
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

            response = client.post(
                "/api/v1/product/final/write",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("status") == "ready"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write final dashboard index",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write final dashboard index",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/handoff/build",
                json={
                    "release_name": release_name,
                    "handoff_name": "v9_9_9_bootstrap_handoff",
                },
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("status") == "ready"
            )
            print(("[PASS]" if ok else "[FAIL]"), "build handoff", response.status_code)
            if not ok:
                failures.append(
                    (
                        "build handoff",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/self-test/maintenance",
                json={
                    "decision": "safe_to_start_v10",
                    "release_name": release_name,
                    "reason": "safe bootstrap smoke",
                },
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("state", {}).get("safe_to_start_v10")
                is True
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "mark v9.9.8 safe to start v10",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "mark v9.9.8 safe to start v10",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get(
                f"/api/v1/product/final/v10-bootstrap?release_name={release_name}"
            )
            closure = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and closure.get("version") == "9.9.9"
                and closure.get("safe_to_start_v10") is True
                and closure.get("required_present") == closure.get("required_total")
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET v10 bootstrap closure payload",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET v10 bootstrap closure payload",
                        response.status_code,
                        response.get_data(as_text=True)[:4000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/v10-bootstrap/write",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            written = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and Path("release/V9_9_9_FINAL_V9_CLOSURE_MANIFEST.json").exists()
                and Path("release/V9_9_9_FINAL_V9_CLOSURE_MANIFEST.md").exists()
                and Path(
                    "release/V9_9_9_V10_BOOTSTRAP_READINESS_MANIFEST.json"
                ).exists()
                and Path("release/V9_9_9_V10_BOOTSTRAP_READINESS_MANIFEST.md").exists()
                and written.get("safe_to_start_v10") is True
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write closure/bootstrap manifests",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write closure/bootstrap manifests",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/v10-bootstrap/decision",
                json={
                    "decision": "close_v9",
                    "release_name": release_name,
                    "reason": "close v9 smoke",
                },
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("state", {}).get("v9_closed") is True
            )
            print(("[PASS]" if ok else "[FAIL]"), "close v9 line", response.status_code)
            if not ok:
                failures.append(
                    (
                        "close v9 line",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/v10-bootstrap/decision",
                json={
                    "decision": "approve_v10_bootstrap",
                    "release_name": release_name,
                    "reason": "approve v10 bootstrap smoke",
                },
                headers={"X-CSRF-Token": "v999-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("status") == "ok"
                and payload.get("state", {}).get("v9_closed") is True
                and payload.get("state", {}).get("v10_bootstrap_ready") is True
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "approve v10 bootstrap",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "approve v10 bootstrap",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get("/api/v1/product/final/v10-bootstrap/audit")
            audit = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and audit.get("count", 0) >= 3
                and any(
                    event.get("action") == "approve_v10_bootstrap_denied"
                    for event in audit.get("events", [])
                )
                and any(
                    event.get("action") == "bootstrap_close_v9"
                    for event in audit.get("events", [])
                )
                and any(
                    event.get("action") == "bootstrap_approve_v10_bootstrap"
                    for event in audit.get("events", [])
                )
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET v10 bootstrap audit",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET v10 bootstrap audit",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get(
                f"/product/final/v10-bootstrap?release_name={release_name}"
            )
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Final v9 Line Closure" in body
                and "Approve v10 Bootstrap" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET v10 bootstrap UI",
                response.status_code,
            )
            if not ok:
                failures.append(
                    ("GET v10 bootstrap UI", response.status_code, body[:2500])
                )

            response = client.get(
                f"/product/final/self-test?release_name={release_name}"
            )
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open v10 Bootstrap Gate" in body
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET self-test bootstrap link",
                response.status_code,
            )
            if not ok:
                failures.append(
                    ("GET self-test bootstrap link", response.status_code, body[:2500])
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.9 v10 bootstrap smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
