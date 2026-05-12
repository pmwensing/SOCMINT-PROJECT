from pathlib import Path
import json
import zipfile

from socmint.dashboard import create_app
from socmint.entity_dossier_v2 import build_full_entity_dossier_v2
from socmint.entity_dossier_v2 import export_full_entity_dossier_v2
from socmint.entity_dossier_v2 import safe_dossier_path
from socmint.full_report_alias import latest_full_report_export
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow


def test_build_full_entity_dossier_v2_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    payload = build_full_entity_dossier_v2(1)

    assert payload["schema"] in {
        "socmint.full_entity_profile_dossier.v7_5",
        "socmint.full_entity_profile_dossier.v7_8_1",
    }
    assert payload["subject_id"] == 1
    assert "identity_summary" in payload["sections"]
    assert "linked_evidence" in payload["sections"]
    assert "custody_hash_status" in payload["sections"]
    assert "connector_diagnostics" in payload["sections"]


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


def test_latest_full_report_export_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = export_full_entity_dossier_v2(24)
    latest = latest_full_report_export(24)

    assert latest["available"] is True
    assert latest["subject_id"] == 24
    assert latest["zip_name"] == Path(result["zip_path"]).name
    assert latest["manifest_name"] == Path(result["manifest_path"]).name
    assert latest["html_name"] == Path(result["html_path"]).name
    assert latest["manifest"]["artifact_count"] == len(latest["manifest"]["files"])


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


def test_full_report_browser_flow_routes_registered():
    app = create_app()
    register_full_report_aliases(app)
    register_full_report_browser_flow(app)
    register_full_report_browser_flow(app)
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/spine/subjects/<int:subject_id>/full-report/view" in rules
    assert "/spine/subjects/<int:subject_id>/full-report/open" in rules
    assert "/spine/subjects/<int:subject_id>/full-report/artifact" in rules


def test_entity_dossier_v2_template_has_v7_5_2_controls():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()

    assert "Run Full Report" in template
    assert "Latest Full Report Export" in template
    assert "Download Manifest" in template
    assert "Download ZIP" in template
    assert "api_full_report_download" in template
    assert "latest_full_report_export" in template


def test_entity_dossier_v2_template_has_v7_5_3_open_view_controls():
    template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()

    assert "View Export Panel" in template
    assert "Open Latest HTML Report" in template
    assert "View Manifest" in template
    assert "ui_full_report_view_panel" in template
    assert "ui_full_report_open_latest" in template
    assert "ui_full_report_view_artifact" in template


def test_entity_dossier_v2_diagnostic_hygiene(monkeypatch, tmp_path):
    from socmint import database as db
    from socmint.spine import create_subject

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/socmint.db")
    db.configure_database(f"sqlite:///{tmp_path}/socmint.db")

    subject_id = create_subject("Diagnostic Hygiene", [{"type": "username", "value": "diaguser"}])
    run_id = db.create_spine_connector_run(
        subject_id=subject_id,
        connector_key="sherlock",
        seed_id=None,
        status="dry_run",
        raw_result={"status": "dry_run", "findings": []},
    )
    db.create_spine_observation(
        subject_id=subject_id,
        run_id=run_id,
        observation_type="connector_no_result",
        normalized_value="sherlock:username",
        confidence="0.05",
        source_ref=f"run:{run_id}:sherlock",
        evidence_ref="sha256:diagnostic",
        payload={"type": "connector_no_result", "diagnostic": True},
    )
    archive_run_id = db.create_spine_connector_run(
        subject_id=subject_id,
        connector_key="archivebox",
        seed_id=None,
        status="dry_run",
        raw_result={"status": "dry_run", "findings": []},
    )
    db.create_spine_observation(
        subject_id=subject_id,
        run_id=archive_run_id,
        observation_type="archive_candidate",
        normalized_value="https://example.com",
        confidence="0.82",
        source_ref=f"run:{archive_run_id}:archivebox",
        evidence_ref="sha256:archive-diagnostic",
        payload={"type": "archive_candidate", "connector": "archivebox", "status": "dry_run"},
    )
    real_run_id = db.create_spine_connector_run(
        subject_id=subject_id,
        connector_key="sherlock",
        seed_id=None,
        status="completed",
        raw_result={"status": "completed", "findings": []},
    )
    db.create_spine_observation(
        subject_id=subject_id,
        run_id=real_run_id,
        observation_type="profile_url",
        normalized_value="https://x.com/diaguser",
        confidence="0.77",
        source_ref=f"run:{real_run_id}:sherlock",
        evidence_ref="sha256:real",
        payload={"type": "profile_url", "diagnostic": False},
    )
    db.upsert_spine_assertion(
        subject_id=subject_id,
        assertion_type="profile_url",
        normalized_value="https://x.com/diaguser",
        confidence="0.77",
        validation_state="unreviewed",
        payload={"source_refs": [f"run:{real_run_id}:sherlock"], "evidence_refs": ["sha256:real"]},
    )

    payload = build_full_entity_dossier_v2(subject_id)

    assert payload["schema"] == "socmint.full_entity_profile_dossier.v7_8_1"
    assert payload["score"]["real_observation_count"] == 1
    assert payload["score"]["diagnostic_count"] == 2
    assert payload["score"]["assertion_count"] == 1
    assert payload["sections"]["observations"]["count"] == 1
    assert payload["sections"]["connector_diagnostics"]["count"] == 2
    assert payload["sections"]["dossier_assertions"]["count"] == 1
    assert payload["sections"]["observations"]["items"][0]["observation_type"] == "profile_url"
    diagnostic_types = {item["observation_type"] for item in payload["sections"]["connector_diagnostics"]["items"]}
    assert diagnostic_types == {"connector_no_result", "archive_candidate"}
