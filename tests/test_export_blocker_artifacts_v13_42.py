import json
from pathlib import Path

from src.socmint.export_blocker_demo_v13_40 import ALLOWED_CASE_ID
from src.socmint.export_blocker_demo_v13_40 import ALLOWED_SUBJECT_ID
from src.socmint.export_blocker_demo_v13_40 import DENIED_CASE_ID
from src.socmint.export_blocker_demo_v13_40 import DENIED_SUBJECT_ID
from src.socmint.export_blocker_demo_v13_40 import create_export_blocker_demo
from src.socmint.wsgi import app


def _login(client):
    with client.session_transaction() as sess:
        sess["user"] = "operator"


def test_export_blocker_screenshot_artifact_manifest_lists_expected_outputs():
    manifest = json.loads(Path("release/V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json").read_text())

    assert manifest["schema"] == "socmint.release_artifact_manifest.v13_42"
    assert manifest["source_workflow"] == "make export-blocker-runtime-screenshots"
    paths = {item["path"] for item in manifest["artifacts"]}
    assert "runtime_screenshots_v13_40/export-blockers-allowed-top.png" in paths
    assert "runtime_screenshots_v13_40/export-blockers-denied-top.png" in paths


def test_export_blocker_screenshot_targets_return_200_before_capture(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_export_blocker_demo()
    client = app.test_client()
    _login(client)

    allowed = client.get(f"/dossier/export-blockers?case_id={ALLOWED_CASE_ID}&subject_id={ALLOWED_SUBJECT_ID}")
    denied = client.get(f"/dossier/export-blockers?case_id={DENIED_CASE_ID}&subject_id={DENIED_SUBJECT_ID}")

    assert allowed.status_code == 200
    assert denied.status_code == 200
    assert "allow" in allowed.get_data(as_text=True)
    assert "audit_coverage" in denied.get_data(as_text=True)


def test_runbook_documents_export_blocker_screenshot_workflow():
    source = Path("RUNBOOK.md").read_text()

    assert "Export Blocker Screenshots" in source
    assert "make export-blocker-runtime-screenshots" in source
    assert "V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json" in source
