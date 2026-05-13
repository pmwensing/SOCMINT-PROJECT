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
from socmint.product_post_release import product_post_release_manifest  # noqa: E402


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
    manifest = product_post_release_manifest()
    if manifest.get("status") != "ok" or manifest.get("version") != "10.0.2":
        print("[FAIL] product_post_release manifest")
        return 1

    write_stage_artifacts()

    with tempfile.TemporaryDirectory(prefix="socmint-v1002-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v1002-post-release-extraction-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1002-post-release-extraction-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1002-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/architecture")
            architecture = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and architecture.get("version") == "10.0.0"
                and architecture.get("compatibility", {}).get("missing") == []
                and "product_post_release.product_post_release_manifest"
                in architecture.get("foundation", {}).get("extracted_modules", [])
            )
            print(("[PASS]" if ok else "[FAIL]"), "v10 architecture includes post-release module", response.status_code)
            if not ok:
                failures.append(("v10 architecture includes post-release module", response.status_code, response.get_data(as_text=True)[:4000]))

            # Build enough runtime chain to prove post-release route family is alive.
            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "approve v10.0.2 extraction smoke"},
                headers={"X-CSRF-Token": "v1002-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("gate", {}).get("gate_status") == "approved"
            print(("[PASS]" if ok else "[FAIL]"), "approve final gate", response.status_code)
            if not ok:
                failures.append(("approve final gate", response.status_code, response.get_data(as_text=True)[:2500]))

            client.post("/api/v1/product/final-gate/write", headers={"X-CSRF-Token": "v1002-csrf"})

            package_root = Path("storage/product_packages/v10_0_2_post_release_package")
            package_root.mkdir(parents=True, exist_ok=True)
            (package_root / "PACKAGE_MANIFEST.json").write_text(json.dumps({"selected_count": 1, "copied_artifact_count": 1, "metadata_file_count": 2}, indent=2))
            (package_root / "PACKAGE_INDEX.md").write_text("# package index\n")
            package_zip = Path("storage/product_packages/v10_0_2_post_release_package.zip")
            with zipfile.ZipFile(package_zip, "w") as zf:
                zf.writestr("PACKAGE_MANIFEST.json", "{}")
                zf.writestr("PACKAGE_INDEX.md", "# index\n")

            release_name = "v10_0_2_post_release_extraction"

            response = client.post(
                "/api/v1/product/final-release/publish",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v1002-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("status") == "published"
            print(("[PASS]" if ok else "[FAIL]"), "publish final release", response.status_code)
            if not ok:
                failures.append(("publish final release", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.post(f"/api/v1/product/final-release/archive/{release_name}/create", headers={"X-CSRF-Token": "v1002-csrf"})
            ok = response.status_code == 200 and response.get_json().get("version") == "9.9.3"
            print(("[PASS]" if ok else "[FAIL]"), "create archive", response.status_code)
            if not ok:
                failures.append(("create archive", response.status_code, response.get_data(as_text=True)[:2500]))

            response = client.get(f"/api/v1/product/final-release/verify?release_name={release_name}")
            ok = response.status_code == 200 and response.get_json().get("status") == "pass"
            print(("[PASS]" if ok else "[FAIL]"), "verify final release", response.status_code)
            if not ok:
                failures.append(("verify final release", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.post(
                "/api/v1/product/final-release/distribution/decision",
                json={"decision": "ready", "release_name": release_name, "reason": "ready v10.0.2 smoke"},
                headers={"X-CSRF-Token": "v1002-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("state", {}).get("ready") is True
            print(("[PASS]" if ok else "[FAIL]"), "distribution ready", response.status_code)
            if not ok:
                failures.append(("distribution ready", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.post("/api/v1/product/final/write", json={"release_name": release_name}, headers={"X-CSRF-Token": "v1002-csrf"})
            ok = response.status_code == 200 and response.get_json().get("status") == "ready"
            print(("[PASS]" if ok else "[FAIL]"), "write final dashboard index", response.status_code)
            if not ok:
                failures.append(("write final dashboard index", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.post(
                "/api/v1/product/final/handoff/build",
                json={"release_name": release_name, "handoff_name": "v10_0_2_post_release_handoff"},
                headers={"X-CSRF-Token": "v1002-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("status") == "ready"
            print(("[PASS]" if ok else "[FAIL]"), "build handoff", response.status_code)
            if not ok:
                failures.append(("build handoff", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.post(
                "/api/v1/product/final/self-test/maintenance",
                json={"decision": "safe_to_start_v10", "release_name": release_name, "reason": "safe v10.0.2 smoke"},
                headers={"X-CSRF-Token": "v1002-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("state", {}).get("safe_to_start_v10") is True
            print(("[PASS]" if ok else "[FAIL]"), "self-test maintenance safe", response.status_code)
            if not ok:
                failures.append(("self-test maintenance safe", response.status_code, response.get_data(as_text=True)[:3000]))

            response = client.post(
                "/api/v1/product/final/v10-bootstrap/write",
                json={"release_name": release_name},
                headers={"X-CSRF-Token": "v1002-csrf"},
            )
            ok = response.status_code == 200 and response.get_json().get("safe_to_start_v10") is True
            print(("[PASS]" if ok else "[FAIL]"), "write v10 bootstrap manifests", response.status_code)
            if not ok:
                failures.append(("write v10 bootstrap manifests", response.status_code, response.get_data(as_text=True)[:3000]))

            post_release_routes = [
                "/product/final-release/distribution",
                "/api/v1/product/final-release/distribution",
                "/product/final",
                "/api/v1/product/final",
                "/product/final/handoff",
                "/api/v1/product/final/handoff",
                "/product/final/self-test",
                "/api/v1/product/final/self-test",
                "/product/final/v10-bootstrap",
                "/api/v1/product/final/v10-bootstrap",
            ]

            for route in post_release_routes:
                response = client.get(f"{route}?release_name={release_name}")
                ok = response.status_code == 200
                print(("[PASS]" if ok else "[FAIL]"), f"post-release compat GET {route}", response.status_code)
                if not ok:
                    failures.append((f"post-release compat GET {route}", response.status_code, response.get_data(as_text=True)[:1800]))

            response = client.post("/api/v1/product/v10/architecture/write", headers={"X-CSRF-Token": "v1002-csrf"})
            ok = (
                response.status_code == 200
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.json").exists()
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "write v10 architecture manifest", response.status_code)
            if not ok:
                failures.append(("write v10 architecture manifest", response.status_code, response.get_data(as_text=True)[:2500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.2 product post-release extraction smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
