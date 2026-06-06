import hashlib
import json
from pathlib import Path

from scripts.refresh_export_blocker_screenshot_manifest_v13_43 import refresh_manifest


def test_refresh_manifest_adds_hash_size_and_exists_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifact = tmp_path / "runtime_screenshots_v13_40" / "export-blockers-allowed-top.png"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"fake-png")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "socmint.release_artifact_manifest.v13_42",
                "version": "v13.42",
                "artifacts": [{"path": "runtime_screenshots_v13_40/export-blockers-allowed-top.png"}],
            }
        )
    )

    result = refresh_manifest(manifest_path, root=tmp_path)

    item = result["artifacts"][0]
    assert result["schema"] == "socmint.release_artifact_manifest.v13_43"
    assert result["refresh_script"] == "scripts/refresh_export_blocker_screenshot_manifest_v13_43.py"
    assert item["exists"] is True
    assert item["size_bytes"] == len(b"fake-png")
    assert item["sha256"] == hashlib.sha256(b"fake-png").hexdigest()


def test_release_manifest_has_refreshed_screenshot_hashes():
    manifest = json.loads(Path("release/V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json").read_text())

    assert manifest["schema"] == "socmint.release_artifact_manifest.v13_43"
    assert manifest["version"] == "v13.43"
    assert manifest["refresh_script"] == "scripts/refresh_export_blocker_screenshot_manifest_v13_43.py"
    for item in manifest["artifacts"]:
        assert item["exists"] is True
        assert item["size_bytes"] > 0
        assert len(item["sha256"]) == 64


def test_ci_can_upload_runtime_screenshot_artifacts_on_manual_request():
    source = Path(".github/workflows/ci.yml").read_text()

    assert "upload_runtime_screenshots" in source
    assert "Upload runtime screenshots" in source
    assert "runtime_screenshots_v13_40/**" in source
    assert "V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json" in source


def test_makefile_exposes_manifest_refresh_target():
    source = Path("Makefile").read_text()

    assert "refresh-export-blocker-screenshot-manifest" in source
    assert "scripts/refresh_export_blocker_screenshot_manifest_v13_43.py" in source
