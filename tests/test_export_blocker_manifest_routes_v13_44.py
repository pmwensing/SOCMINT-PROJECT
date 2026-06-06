import json
from pathlib import Path

import pytest

from scripts.refresh_export_blocker_screenshot_manifest_v13_43 import refresh_manifest
from src.socmint.wsgi import app


def _login(client):
    with client.session_transaction() as sess:
        sess["user"] = "operator"


def test_manifest_refresh_fails_when_required_artifact_is_missing(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "socmint.release_artifact_manifest.v13_42",
                "version": "v13.42",
                "artifacts": [{"path": "runtime_screenshots_v13_40/missing.png"}],
            }
        )
    )

    with pytest.raises(FileNotFoundError, match="Missing screenshot artifact"):
        refresh_manifest(manifest_path, root=tmp_path)


def test_export_blocker_manifest_routes_return_json_and_download():
    client = app.test_client()
    _login(client)

    api = client.get("/api/v1/dossier-builder/v3/export-blockers/screenshot-manifest")
    download = client.get("/dossier/export-blockers/screenshot-manifest/download")

    assert api.status_code == 200
    assert api.mimetype == "application/json"
    assert api.get_json()["schema"] == "socmint.release_artifact_manifest.v13_43"
    assert download.status_code == 200
    assert "attachment" in download.headers.get("Content-Disposition", "")


def test_export_blockers_ui_links_to_manifest_routes():
    client = app.test_client()
    _login(client)

    response = client.get("/dossier/export-blockers")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "/api/v1/dossier-builder/v3/export-blockers/screenshot-manifest" in body
    assert "/dossier/export-blockers/screenshot-manifest/download" in body


def test_dedicated_screenshot_workflow_is_available():
    source = Path(".github/workflows/export-blocker-screenshots.yml").read_text()

    assert "Export Blocker Screenshots" in source
    assert "Start local runtime" in source
    assert "python -m gunicorn --bind 127.0.0.1:5000 src.socmint.wsgi:app" in source
    assert "make export-blocker-runtime-screenshots" in source
    assert "actions/upload-artifact@v4" in source
    assert "if-no-files-found: error" in source
