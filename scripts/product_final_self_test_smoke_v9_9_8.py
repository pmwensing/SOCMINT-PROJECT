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

    with tempfile.TemporaryDirectory(prefix="socmint-v998-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v998-self-test-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v998-self-test-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v998-csrf"

            failures = []

            response = client.post(
                "/api/v1/product/final/self-test/maintenance",
                json={
                    "decision": "safe_to_start_v10",
                    "release_name": "missing-release",
                    "reason": "should be denied",
                },
                headers={"X-CSRF-Token": "v998-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and payload.get("status") == "blocked"
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "deny v10 readiness without handoff",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "deny v10 readiness without handoff",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve self-test smoke"},
                headers={"X-CSRF-Token": "v998-csrf"},
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
                headers={"X-CSRF-Token": "v998-csrf"},
            )

            package_root = Path("storage/product_packages/v9_9_8_self_test_package")
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
            package_zip = Path("storage/product_packages/v9_9_8_self_test_package.zip")
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v9_9_8_self_test_release"

            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v998-csrf"},
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
                headers={"X-CSRF-Token": "v998-csrf"},
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
                    "reason": "ready self-test smoke",
                },
                headers={"X-CSRF-Token": "v998-csrf"},
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
                headers={"X-CSRF-Token": "v998-csrf"},
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
                    "handoff_name": "v9_9_8_self_test_handoff",
                },
                headers={"X-CSRF-Token": "v998-csrf"},
            )
            ok = (
                response.status_code == 200
                and response.get_json().get("status") == "ready"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "build operator handoff",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "build operator handoff",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get(
                f"/api/v1/product/final/self-test?release_name={release_name}"
            )
            self_test = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and self_test.get("version") == "9.9.8"
                and self_test.get("status") == "pass"
                and self_test.get("checks_passed") == self_test.get("checks_total")
                and self_test.get("safe_to_start_v10_allowed") is True
                and "operator_handoff" not in self_test.get("failures", [])
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET final self-test API",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET final self-test API",
                        response.status_code,
                        response.get_data(as_text=True)[:4000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/self-test/write",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v998-csrf"},
            )
            report = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and report.get("status") == "pass"
                and Path("release/V9_9_8_POST_RELEASE_MAINTENANCE_REPORT.json").exists()
                and Path("release/V9_9_8_POST_RELEASE_MAINTENANCE_REPORT.md").exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write maintenance report",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write maintenance report",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/self-test/maintenance",
                json={
                    "decision": "safe_to_start_v10",
                    "release_name": release_name,
                    "reason": "safe to start v10 smoke",
                },
                headers={"X-CSRF-Token": "v998-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("status") == "ok"
                and payload.get("state", {}).get("safe_to_start_v10") is True
                and payload.get("self_test", {}).get("status") == "pass"
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "mark safe to start v10",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "mark safe to start v10",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get("/api/v1/product/final/self-test/maintenance-audit")
            audit = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and audit.get("count", 0) >= 2
                and any(
                    event.get("action") == "safe_to_start_v10_denied"
                    for event in audit.get("events", [])
                )
                and any(
                    event.get("action") == "maintenance_safe_to_start_v10"
                    for event in audit.get("events", [])
                )
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET maintenance audit",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET maintenance audit",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.get(
                f"/product/final/self-test?release_name={release_name}"
            )
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Final Release Self-Test" in body
                and "Mark Safe to Start v10" in body
                and "PASS" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"), "GET self-test UI", response.status_code
            )
            if not ok:
                failures.append(("GET self-test UI", response.status_code, body[:2500]))

            response = client.get(f"/product/final/handoff?release_name={release_name}")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Final Self-Test" in body
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET handoff self-test link",
                response.status_code,
            )
            if not ok:
                failures.append(
                    ("GET handoff self-test link", response.status_code, body[:2500])
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.8 final release self-test smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
