from pathlib import Path

from src.socmint.dossier_export_index import export_index
from src.socmint.dossier_export_index import find_export_entry
from src.socmint.dossier_export_index import resolve_export_download_path
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject():
    return {
        "subject_id": "sub-index-106",
        "display_name": "Indexed Export Subject",
        "case_id": "case-index-106",
        "aliases": ["indexed-export"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-index-1",
            "label": "indexed profile artifact",
            "source": "public_profile",
            "confidence": 0.94,
            "artifact_id": "art-index-1",
        },
        {
            "evidence_id": "ev-index-2",
            "label": "indexed registry artifact",
            "source": "public_registry",
            "confidence": 0.91,
            "artifact_id": "art-index-2",
        },
    ]


def test_v10_6_export_index_lists_persisted_manifest(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path)
    index = export_index(root=tmp_path)

    assert index["schema"] == "socmint.dossier_export_index.v10_6_0"
    assert index["status"] == "ready"
    assert index["export_count"] == 1
    assert index["entries"][0]["artifact_count"] == 2
    assert index["entries"][0]["case_id"] == "case-index-106"


def test_v10_6_find_export_entry_returns_artifacts(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path)
    entry = find_export_entry("case-index-106", "sub-index-106", root=tmp_path)

    assert entry["schema"] == "socmint.dossier_export_index.v10_6_0"
    assert entry["status"] == "ready"
    assert entry["case_id"] == "case-index-106"
    assert entry["subject_id"] == "sub-index-106"
    assert len(entry["artifacts"]) == 2


def test_v10_6_download_path_allows_known_files(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path)
    resolved = resolve_export_download_path("case-index-106", "sub-index-106", "dossier.html", root=tmp_path)

    assert resolved["schema"] == "socmint.dossier_export_index.v10_6_0"
    assert resolved["status"] == "ready"
    assert resolved["filename"] == "dossier.html"
    assert Path(resolved["path"]).exists()


def test_v10_6_download_path_blocks_unknown_files(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path)
    resolved = resolve_export_download_path("case-index-106", "sub-index-106", "../../secret.txt", root=tmp_path)

    assert resolved["status"] == "blocked"
    assert resolved["reason"] == "unsupported_filename"


def test_v10_6_index_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-index" in routes
    assert "/api/v1/dossier-builder/v3/export-index/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/export-download/<case_id>/<subject_id>/<filename>" in routes
