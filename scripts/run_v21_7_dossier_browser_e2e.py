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
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

CASE_ID = "case-v21"
SUBJECT_ID = 42


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _ledger() -> dict:
    return {
        "schema": "socmint.claim_evidence_ledger.v13_5",
        "subject_id": SUBJECT_ID,
        "subject_exists": True,
        "rows": [
            {
                "claim_id": "assertion:1",
                "claim_type": "ownership",
                "claim_value": "subject controls the reviewed account",
                "confidence": 0.98,
                "review_state": "confirmed",
                "source": "browser_e2e_fixture",
                "evidence_refs": ["evidence-1"],
                "artifact_links": [],
            }
        ],
    }


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = (
        "v21-browser-e2e-stable-high-entropy-secret-b821db23f2324a09a9a3472df2e74a51"
    )
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.case_findings_v20 import (
        build_dossier_promotion_package,
        decide_finding,
        propose_finding,
    )
    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import (
        register_dossier_assembly_routes_v21_0,
    )
    from src.socmint import dossier_citation_mapping_v21_3

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)
    dossier_citation_mapping_v21_3.build_claim_evidence_ledger = (
        lambda subject_id: _ledger()
    )

    item = propose_finding(
        CASE_ID,
        {
            "text": "The reviewed account is attributable to the subject.",
            "confidence": "high",
            "claim_ids": ["assertion:1"],
            "evidence_ids": ["evidence-1"],
        },
        actor="analyst",
    )
    decide_finding(
        CASE_ID,
        item["finding_id"],
        "approve",
        actor="supervisor",
    )
    build_dossier_promotion_package(
        CASE_ID,
        actor="supervisor",
        promote=True,
    )
    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def run(output: Path) -> dict:
    report = {
        "schema": "socmint.dossier_browser_e2e.v21_7",
        "version": "v21.7.0",
        "status": "passed",
        "checks": [],
    }
    with tempfile.TemporaryDirectory(prefix="socmint-v21-") as temp:
        app = _app(Path(temp) / "v21.db")
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
        wait = WebDriverWait(browser, 15)
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            browser.get(base + "/")
            serializer = app.session_interface.get_signing_serializer(app)
            browser.add_cookie(
                {
                    "name": app.config.get("SESSION_COOKIE_NAME", "session"),
                    "value": serializer.dumps(
                        {
                            "user": "supervisor",
                            "_csrf_token": "v21-csrf",
                        }
                    ),
                    "path": "/",
                }
            )

            assembly = base + f"/dossier-assembly/{CASE_ID}?subject_id={SUBJECT_ID}"
            browser.get(assembly)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-dossier-assembly-workspace]")
                )
            )
            _check(report, "assembly_workspace_render", True)

            old_root = browser.find_element(
                By.CSS_SELECTOR, "[data-dossier-assembly-workspace]"
            )
            browser.find_element(By.ID, "import-findings-package").click()
            wait.until(EC.staleness_of(old_root))
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-dossier-assembly-workspace]")
                )
            )
            _check(
                report,
                "package_import",
                "imported_current" in browser.page_source,
            )

            for textarea in browser.find_elements(By.CLASS_NAME, "section-narrative"):
                if not textarea.get_attribute("value"):
                    textarea.clear()
                    textarea.send_keys(
                        "Reviewed evidence supports this dossier section."
                    )
            old_root = browser.find_element(
                By.CSS_SELECTOR, "[data-dossier-assembly-workspace]"
            )
            browser.find_element(By.ID, "save-dossier-arrangement").click()
            wait.until(EC.staleness_of(old_root))
            _check(report, "arrangement_saved", True)

            browser.find_element(By.ID, "refresh-dossier-draft").click()
            wait.until(
                lambda drv: "dossier-draft-"
                in drv.find_element(By.ID, "dossier-draft-output").text
            )
            _check(report, "draft_generation", True)

            citations = (
                base + f"/dossier-assembly/{CASE_ID}/citations?subject_id={SUBJECT_ID}"
            )
            browser.get(citations)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-dossier-citation-workspace]")
                )
            )
            _check(
                report,
                "citation_mapping",
                "Citation-Ready Dossier Content" in browser.page_source,
            )
            old_root = browser.find_element(
                By.CSS_SELECTOR, "[data-dossier-citation-workspace]"
            )
            browser.find_element(By.ID, "save-citation-snapshot").click()
            wait.until(EC.staleness_of(old_root))
            _check(report, "citation_snapshot", True)

            quality = (
                base
                + f"/dossier-assembly/{CASE_ID}/quality-review?subject_id={SUBJECT_ID}"
            )
            browser.get(quality)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-dossier-quality-review]")
                )
            )
            _check(report, "quality_review_ready", "ready" in browser.page_source)
            old_root = browser.find_element(
                By.CSS_SELECTOR, "[data-dossier-quality-review]"
            )
            browser.find_element(By.ID, "save-quality-review-snapshot").click()
            wait.until(EC.staleness_of(old_root))
            _check(report, "quality_review_snapshot", True)

            approval = (
                base
                + f"/dossier-assembly/{CASE_ID}/supervisor-approval?subject_id={SUBJECT_ID}"
            )
            browser.get(approval)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-dossier-supervisor-approval]")
                )
            )
            browser.find_element(By.ID, "supervisor-decision-note").send_keys(
                "Approved during v21.7 browser validation."
            )
            old_root = browser.find_element(
                By.CSS_SELECTOR, "[data-dossier-supervisor-approval]"
            )
            browser.find_element(By.ID, "save-supervisor-decision").click()
            wait.until(EC.staleness_of(old_root))
            _check(report, "supervisor_approval", "approved" in browser.page_source)

            export_url = (
                base
                + f"/dossier-assembly/{CASE_ID}/final-export?subject_id={SUBJECT_ID}"
            )
            browser.get(export_url)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-dossier-final-export]")
                )
            )
            _check(
                report,
                "final_export_ready",
                "Integrity Manifest" in browser.page_source,
            )
            old_root = browser.find_element(
                By.CSS_SELECTOR, "[data-dossier-final-export]"
            )
            browser.find_element(By.ID, "generate-final-export").click()
            wait.until(EC.staleness_of(old_root))
            _check(
                report,
                "final_export_generated",
                "Latest Generated Export" in browser.page_source,
            )

            browser.get(base + "/api/v1/dossier-assembly/product-review-checkpoint")
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
    parser.add_argument("--output", default="artifacts/v21_7_dossier_browser_e2e.json")
    args = parser.parse_args()
    report = run(Path(args.output))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
