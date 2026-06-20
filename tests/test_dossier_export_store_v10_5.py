from pathlib import Path

from src.socmint.dossier_export_store import export_store_summary
from src.socmint.dossier_export_store import load_export_manifest
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.dossier_export_store import safe_slug
from src.socmint.wsgi import app


def _subject():
    return {
        "subject_id": "sub/store 105",
        "display_name": "Stored Export Subject",
        "case_id": "case/store 105",
        "aliases": ["stored-export"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-store-1",
            "label": "stored profile artifact",
            "source": "public_profile",
            "confidence": 0.93,
            "artifact_id": "art-store-1",
        },
        {
            "evidence_id": "ev-store-2",
            "label": "stored registry artifact",
            "source": "public_registry",
            "confidence": 0.89,
            "artifact_id": "art-store-2",
        },
    ]


def test_v10_5_safe_slug_normalizes_path_parts():
    assert safe_slug("case/store 105") == "case-store-105"
    assert safe_slug("***", fallback="fallback") == "fallback"


def test_v10_5_persist_export_pack_writes_artifacts(tmp_path):
    result = persist_export_pack(
        _subject(), _evidence(), analyst_reviewed=True, root=tmp_path
    )

    assert result["schema"] == "socmint.dossier_export_store.v10_5_0"
    assert result["status"] == "ready"
    assert result["artifact_count"] == 2
    assert Path(result["manifest_path"]).exists()
    for artifact in result["artifacts"]:
        assert Path(artifact["path"]).exists()
        assert artifact["sha256"]


def test_v10_5_load_manifest_and_summary(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path)
    manifest = load_export_manifest("sub/store 105", "case/store 105", root=tmp_path)
    summary = export_store_summary("sub/store 105", "case/store 105", root=tmp_path)

    assert manifest["schema"] == "socmint.dossier_export_store.v10_5_0"
    assert manifest["status"] == "ready"
    assert len(manifest["artifacts"]) == 2
    assert summary["artifact_count"] == 2
    assert summary["status"] == "ready"


def test_v10_5_missing_manifest_returns_missing_status(tmp_path):
    manifest = load_export_manifest("missing-subject", "missing-case", root=tmp_path)

    assert manifest["status"] == "missing"
    assert manifest["artifacts"] == []


def test_v10_5_export_store_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-store" in routes
    assert (
        "/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/manifest"
        in routes
    )
    assert (
        "/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/summary"
        in routes
    )
