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

    with tempfile.TemporaryDirectory(prefix="socmint-v997-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v997-handoff-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v997-handoff-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v997-csrf"

            failures = []

            # Build the v9.9.0-v9.9.6 chain.
            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve handoff smoke"},
                headers={"X-CSRF-Token": "v997-csrf"},
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
                headers={"X-CSRF-Token": "v997-csrf"},
            )

            package_root = Path("storage/product_packages/v9_9_7_handoff_package")
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
            package_zip = Path("storage/product_packages/v9_9_7_handoff_package.zip")
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v9_9_7_handoff_release"
            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v997-csrf"},
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
                headers={"X-CSRF-Token": "v997-csrf"},
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
                    "reason": "ready handoff smoke",
                },
                headers={"X-CSRF-Token": "v997-csrf"},
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
                headers={"X-CSRF-Token": "v997-csrf"},
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

            response = client.get(
                f"/api/v1/product/final/handoff?release_name={release_name}"
            )
            preview = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and preview.get("version") == "9.9.7"
                and preview.get("status") == "ready"
                and preview.get("required_present") == preview.get("required_total")
                and preview.get("distribution_ready") is True
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET handoff preview",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET handoff preview",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            response = client.post(
                "/api/v1/product/final/handoff/build",
                json={
                    "release_name": release_name,
                    "handoff_name": "v9_9_7_handoff_smoke",
                },
                headers={"X-CSRF-Token": "v997-csrf"},
            )
            handoff = response.get_json() if response.is_json else {}
            handoff_root = Path(handoff.get("handoff_path", ""))
            ok = (
                response.status_code == 200
                and handoff.get("status") == "ready"
                and handoff_root.exists()
                and (handoff_root / "HANDOFF_MANIFEST.json").exists()
                and (handoff_root / "PRINTABLE_HANDOFF_CHECKLIST.md").exists()
                and Path("release/V9_9_7_OPERATOR_HANDOFF_MANIFEST.json").exists()
                and Path("release/V9_9_7_PRINTABLE_HANDOFF_CHECKLIST.md").exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "build operator handoff pack",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "build operator handoff pack",
                        response.status_code,
                        response.get_data(as_text=True)[:3000],
                    )
                )

            if handoff_root.exists():
                manifest = json.loads(
                    (handoff_root / "HANDOFF_MANIFEST.json").read_text()
                )
                versions = {item.get("version") for item in manifest.get("copied", [])}
                required_versions = {
                    "v9.9.0",
                    "v9.9.1",
                    "v9.9.2",
                    "v9.9.3",
                    "v9.9.4",
                    "v9.9.5",
                    "v9.9.6",
                }
                ok = (
                    required_versions.issubset(versions)
                    and manifest.get("copied_count") >= 16
                )
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    "handoff contains every final release artifact version",
                )
                if not ok:
                    failures.append(
                        (
                            "handoff contains every final release artifact version",
                            0,
                            json.dumps(manifest, indent=2)[:3000],
                        )
                    )

            response = client.get(f"/product/final/handoff?release_name={release_name}")
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Product Release Closeout" in body
                and "Required Handoff Artifacts" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"), "GET handoff UI", response.status_code
            )
            if not ok:
                failures.append(("GET handoff UI", response.status_code, body[:2500]))

            response = client.get(f"/product/final?release_name={release_name}")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Operator Handoff Pack" in body
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET final dashboard handoff link",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET final dashboard handoff link",
                        response.status_code,
                        body[:2500],
                    )
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.7 operator handoff smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
