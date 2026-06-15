from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service as ChromeService  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import Select, WebDriverWait  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

CASE_ID = "case-v22"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _export_event() -> dict:
    return {
        "schema": "socmint.dossier_final_export_package.v21_6",
        "version": "v21.6.0",
        "case_id": CASE_ID,
        "subject_id": 42,
        "export_package_id": "dossier-export-v22-browser",
        "export_package_sha256": "a" * 64,
        "dossier_content": {
            "section_count": 1,
            "sections": [{
                "section_id": "key_findings",
                "title": "Key Findings",
                "position": 1,
                "citation_ready_narrative": "Reviewed evidence supports the approved finding.",
                "findings": [{
                    "finding_id": "finding-1",
                    "citation_ready_text": "The reviewed account is attributable to the subject [C1].",
                }],
            }],
        },
        "citation_catalog": [{
            "label": "C1",
            "claim_id": "claim-1",
            "claim_value": "account attribution",
            "source": "browser_e2e_fixture",
            "evidence_refs": ["evidence-1"],
            "artifact_links": [{
                "artifact_id": "artifact-1",
                "path": "evidence/report.pdf",
                "sha256": "b" * 64,
                "media_type": "application/pdf",
            }],
        }],
        "source_manifest": {"package_id": "findings-package-1"},
        "approval_record": {
            "approval_id": "approval-v22-browser",
            "approval_record_id": 11,
            "reviewer": "supervisor",
        },
        "quality_review": {
            "review_id": "review-v22-browser",
            "review_sha256": "c" * 64,
            "ready": True,
        },
        "export_metadata": {
            "format": "socmint-json",
            "media_type": "application/json",
            "classification": "case-dossier",
        },
        "integrity": {
            "content_sha256": "1" * 64,
            "dossier_sha256": "2" * 64,
            "citation_catalog_sha256": "3" * 64,
            "source_manifest_sha256": "4" * 64,
            "approval_record_sha256": "5" * 64,
            "quality_review_sha256": "6" * 64,
        },
        "source_records_mutated": False,
    }


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = (
        "v22-browser-e2e-stable-high-entropy-secret-"
        "f82c2368ab4d49d6a1e4fe799c591205"
    )
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"
    os.environ["SOCMINT_AUTHORIZED_RECIPIENTS"] = json.dumps([{
        "recipient_id": "recipient-v22",
        "display_name": "V22 Authorized Recipient",
        "organization": "SOCMINT Validation",
        "role": "case officer",
        "authorized": True,
        "allowed_channels": ["secure_portal"],
    }])

    from src.socmint import database
    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import (
        register_dossier_assembly_routes_v21_0,
    )
    from src.socmint.dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage
    from src.socmint.dossier_final_export_package_v21_6 import FINAL_EXPORT_ACTION

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)
    _ensure_storage()
    session = database.Session()
    try:
        session.add(database.AuditLog(
            actor="supervisor",
            action=FINAL_EXPORT_ACTION,
            target_value=CASE_ID,
            details=_canonical(_export_event()),
        ))
        session.commit()
    finally:
        session.close()
    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def _reload_after_click(browser, wait, root_selector: str, button_id: str) -> None:
    old_root = browser.find_element(By.CSS_SELECTOR, root_selector)
    browser.find_element(By.ID, button_id).click()
    wait.until(EC.staleness_of(old_root))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, root_selector)))


def run(output: Path) -> dict:
    report = {
        "schema": "socmint.dossier_release_browser_e2e.v22_7",
        "version": "v22.7.0",
        "status": "passed",
        "checks": [],
    }
    with tempfile.TemporaryDirectory(prefix="socmint-v22-") as temp:
        app = _app(Path(temp) / "v22.db")
        server = make_server("127.0.0.1", _port(), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        chromium = shutil.which("chromium") or shutil.which("google-chrome")
        if chromium:
            options.binary_location = chromium
        driver_path = shutil.which("chromedriver")
        browser = webdriver.Chrome(
            options=options,
            service=ChromeService(driver_path) if driver_path else None,
        )
        wait = WebDriverWait(browser, 20)
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            browser.get(base + "/")
            serializer = app.session_interface.get_signing_serializer(app)
            browser.add_cookie({
                "name": app.config.get("SESSION_COOKIE_NAME", "session"),
                "value": serializer.dumps({
                    "user": "supervisor",
                    "_csrf_token": "v22-csrf",
                }),
                "path": "/",
            })

            workspace = base + f"/dossier-release/{CASE_ID}"
            browser.get(workspace)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-dossier-release-workspace]")
            ))
            _check(report, "release_workspace_render", True)
            _check(
                report,
                "recovery_controls_render",
                "Failed Delivery, Recall, and Reissue Controls" in browser.page_source,
            )

            Select(browser.find_element(By.ID, "release-recipient")).select_by_value(
                "recipient-v22"
            )
            Select(browser.find_element(By.ID, "release-channel")).select_by_value(
                "secure_portal"
            )
            browser.find_element(By.ID, "release-authorization-note").send_keys(
                "Authorized during v22.7 browser validation."
            )
            browser.find_element(By.ID, "release-authorization-confirmed").click()
            _reload_after_click(
                browser,
                wait,
                "[data-dossier-release-workspace]",
                "authorize-release-selection",
            )
            _check(report, "release_authorization", "V22 Authorized Recipient" in browser.page_source)

            browser.find_element(By.ID, "release-preview-note").send_keys(
                "Reviewed exact release material."
            )
            browser.find_element(By.ID, "release-preview-acknowledged").click()
            _reload_after_click(
                browser,
                wait,
                "[data-dossier-release-workspace]",
                "acknowledge-release-preview",
            )
            _check(report, "release_preview_acknowledged", True)

            browser.find_element(By.ID, "secure-distribution-note").send_keys(
                "Final distribution confirmation."
            )
            browser.find_element(By.ID, "secure-distribution-confirmed").click()
            _reload_after_click(
                browser,
                wait,
                "[data-dossier-release-workspace]",
                "dispatch-secure-distribution",
            )
            _check(report, "secure_distribution", "Latest distribution" in browser.page_source)

            Select(browser.find_element(By.ID, "delivery-result")).select_by_value("delivered")
            browser.find_element(By.ID, "provider-message-id").send_keys("provider-v22-1")
            browser.find_element(By.ID, "transport-status").send_keys("delivered")
            browser.find_element(By.ID, "delivered-at").send_keys("2026-06-14T20:15:00Z")
            _reload_after_click(
                browser,
                wait,
                "[data-dossier-release-workspace]",
                "record-delivery-receipt",
            )
            _check(report, "delivery_receipt", "Delivery succeeded" in browser.page_source)
            _check(report, "acknowledgement_outstanding", "Acknowledgement outstanding" in browser.page_source)

            browser.find_element(By.ID, "recipient-acknowledged").click()
            browser.find_element(By.ID, "recipient-ack-name").send_keys(
                "V22 Authorized Recipient"
            )
            browser.find_element(By.ID, "recipient-ack-method").send_keys(
                "secure_portal_confirmation"
            )
            browser.find_element(By.ID, "recipient-ack-at").send_keys(
                "2026-06-14T20:20:00Z"
            )
            _reload_after_click(
                browser,
                wait,
                "[data-dossier-release-workspace]",
                "record-recipient-acknowledgement",
            )
            _check(report, "recipient_acknowledgement", True)

            browser.get(base + f"/api/v1/dossier-release/{CASE_ID}/delivery-recovery")
            recovery = json.loads(browser.find_element(By.TAG_NAME, "body").text)
            _check(
                report,
                "recovery_state",
                recovery.get("acknowledgement_received") is True,
            )

            browser.get(base + f"/dossier-release/{CASE_ID}/history")
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-dossier-release-history]")
            ))
            _check(report, "consolidated_history", "Consolidated Timeline" in browser.page_source)
            _check(report, "closure_ready", "delivered_and_acknowledged" in browser.page_source)

            browser.get(base + "/api/v1/dossier-release/product-review-checkpoint")
            checkpoint = json.loads(browser.find_element(By.TAG_NAME, "body").text)
            _check(report, "product_checkpoint", checkpoint.get("ready") is True)
        except Exception as exc:
            report["status"] = "failed"
            _check(report, "browser_exception", False, f"{type(exc).__name__}: {exc}")
        finally:
            browser.quit()
            server.shutdown()
            thread.join(timeout=5)

    report["passed_count"] = sum(1 for item in report["checks"] if item["ok"])
    report["failed_count"] = len(report["checks"]) - report["passed_count"]
    if report["failed_count"]:
        report["status"] = "failed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", default="artifacts/v22_7_dossier_release_browser_e2e.json"
    )
    args = parser.parse_args()
    report = run(Path(args.output))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
