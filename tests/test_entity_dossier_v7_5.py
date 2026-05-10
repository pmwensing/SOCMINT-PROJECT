from pathlib import Path
import json
import zipfile

from socmint.dashboard import create_app
from socmint.entity_dossier_v2 import build_full_entity_dossier_v2
from socmint.entity_dossier_v2 import export_full_entity_dossier_v2
from socmint.entity_dossier_v2 import safe_dossier_path
from socmint.full_report_alias import register_full_report_aliases


def test_build_full_entity_dossier_v2_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    payload = build_full_entity_dossier_v2(1)

    assert payload["schema"] == "socmint.full_entity_profile_dossier.v7_5"
    assert payload["subject_id"] == 1
    assert "identity_summary" in payload["sections"]
    assert "linked_evidence" in payload["sections"]
    assert "custody_hash_status" in payload["sections"]


def test_export_full_entity_dossier_v2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = export_full_entity_dossier_v2(22)

    assert result["schema"] in {
        "socmint.full_entity_profile_dossier_export.v7_5",
        "socmint.full_entity_profile_dossier_export.v7_5_1",
    }
    assert Path(result["json_path"]).exists()
    assert Path(result["markdown_path"]).exists()
    assert Path(result["html_path"]).exists()
    assert Path(result["manifest_path"]).exists()
    assert Path(result["zip_path"]).exists()

    safe = safe_dossier_path(Path(result["zip_path"]).name)
    assert safe.exists()

    with zipfile.ZipFile(result["zip_path"]) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        assert Path(result["manifest_path"]).name in names
        assert any(name.endswith(".json") for name in names)
        assert any(name.endswith(".md") for name in names)
        assert any(name.endswith(".html") for name in names)


def test_export_full_entity_dossier_v2_manifest_hashes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = export_full_entity_dossier_v2(23)

    manifest_path = Path(result["manifest_path"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())

    assert manifest["schema"] == "socmint.full_entity_profile_dossier_manifest.v7_5_1"
    assert manifest["subject_id"] == 23
    assert manifest["artifact_count"] == len(manifest["files"])

    roles = {entry["role"] for entry in manifest["files"]}
    assert {"dossier_json", "dossier_markdown", "dossier_html", "export_manifest", "zip_bundle"} <= roles

    for entry in manifest["files"]:
        assert len(entry["sha256"]) == 64
        assert entry["size_bytes"] > 0

    with zipfile.ZipFile(result["zip_path"]) as zf:
        names = set(zf.namelist())
        assert Path(result["manifest_path"]).name in names

    assert result["manifest"]["artifact_count"] == len(result["manifest"]["files"])
    assert result["full_report_download_url"].startswith(
        "/api/v1/spine/subjects/23/full-report/download?name="
    )


def test_dossier_v2_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/spine/subjects/<int:subject_id>/dossier-v2" in rules
    assert "/api/v1/spine/subjects/<int:subject_id>/dossier-v2/export" in rules
    assert "/spine/subjects/<int:subject_id>/dossier" in rules
    assert "/spine/subjects/<int:subject_id>/dossier-v2/export/run" in rules
    assert (
        "/spine/subjects/<int:subject_id>/dossier-v2/export/"
        "<path:name>/download"
        in rules
    )


def test_full_report_alias_routes_registered():
    app = create_app()
    register_full_report_aliases(app)
    register_full_report_aliases(app)
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/spine/subjects/<int:subject_id>/full-report" in rules
    assert "/api/v1/spine/subjects/<int:subject_id>/full-report/run" in rules
    assert "/api/v1/spine/subjects/<int:subject_id>/full-report/latest" in rules
    assert "/api/v1/spine/subjects/<int:subject_id>/full-report/download" in rules
    assert "/spine/subjects/<int:subject_id>/full-report/run" in rules
