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


def remove_one_stage_artifact() -> Path:
    missing = ROOT / "release/V9_8_9_RELEASE_PACKAGE_ZIP_HARDENING_REPORT.md"
    if missing.exists():
        missing.unlink()
    return missing


def main() -> int:
    write_stage_artifacts()

    with tempfile.TemporaryDirectory(prefix="socmint-v991-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v991-final-gate-smoke")

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v991-gate-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v991-csrf"

            failures = []

            missing = remove_one_stage_artifact()
            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "should be denied"},
                headers={"X-CSRF-Token": "v991-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("status") == "blocked"
                and payload.get("approved") is False
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "deny approval when RC warn",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "deny approval when RC warn",
                        response.status_code,
                        response.get_data(as_text=True)[:1500],
                    )
                )

            write_stage_artifacts()

            response = client.get("/api/v1/product/final-gate")
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("rc_status") == "pass"
                and payload.get("can_approve") is True
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET final gate ready",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET final gate ready",
                        response.status_code,
                        response.get_data(as_text=True)[:1500],
                    )
                )

            response = client.post(
                "/api/v1/product/final-gate/signoff",
                json={"decision": "approve", "reason": "smoke approved"},
                headers={"X-CSRF-Token": "v991-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and payload.get("status") == "ok"
                and payload.get("signoff", {}).get("approved") is True
                and payload.get("gate", {}).get("gate_status") == "approved"
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

            response = client.get("/api/v1/product/final-gate/signoff-audit")
            audit = response.get_json() if response.is_json else {}
            events = audit.get("events", [])
            ok = (
                response.status_code == 200
                and len(events) >= 2
                and any(event.get("action") == "approve_denied" for event in events)
                and any(event.get("action") == "signoff_approve" for event in events)
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET signoff audit",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET signoff audit",
                        response.status_code,
                        response.get_data(as_text=True)[:2000],
                    )
                )

            response = client.post(
                "/api/v1/product/final-gate/write",
                headers={"X-CSRF-Token": "v991-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            json_path = Path("release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json")
            md_path = Path("release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.md")
            ok = (
                response.status_code == 200
                and payload.get("version") == "9.9.1"
                and json_path.exists()
                and md_path.exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write final gate manifest",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write final gate manifest",
                        response.status_code,
                        response.get_data(as_text=True)[:2000],
                    )
                )

            if json_path.exists():
                data = json.loads(json_path.read_text())
                ok = (
                    data.get("gate_status") == "approved"
                    and data.get("signoff", {}).get("approved") is True
                )
                print(("[PASS]" if ok else "[FAIL]"), "final gate manifest content")
                if not ok:
                    failures.append(
                        (
                            "final gate manifest content",
                            0,
                            json.dumps(data, indent=2)[:2500],
                        )
                    )

            response = client.get("/product/final-gate")
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Final Product Gate" in body
                and "Approve RC" in body
                and "Block RC" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET final gate UI",
                response.status_code,
            )
            if not ok:
                failures.append(
                    ("GET final gate UI", response.status_code, body[:2000])
                )

            response = client.get("/product/release-candidate")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Open Final Product Gate" in body
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET RC console final gate link",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET RC console final gate link",
                        response.status_code,
                        body[:2000],
                    )
                )

            # Restore in case later checks expect it on disk.
            missing.write_text(
                STAGE_ARTIFACTS[missing.as_posix().replace(str(ROOT) + "/", "")]
            )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.9.1 final product gate smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
