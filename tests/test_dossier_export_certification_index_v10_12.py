from src.socmint.dossier_export_certification_index import certification_index
from src.socmint.dossier_export_certification_index import certification_index_review_items
from src.socmint.dossier_export_certification_index import certification_index_summary
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject(subject_id: str, case_id: str, name: str):
    return {
        "subject_id": subject_id,
        "display_name": name,
        "case_id": case_id,
        "aliases": [name.lower().replace(" ", "-")],
    }


def _evidence(prefix: str):
    return [
        {
            "evidence_id": f"ev-{prefix}-1",
            "label": "certification index profile artifact",
            "source": "public_profile",
            "confidence": 0.96,
            "artifact_id": f"art-{prefix}-1",
        },
        {
            "evidence_id": f"ev-{prefix}-2",
            "label": "certification index registry artifact",
            "source": "public_registry",
            "confidence": 0.93,
            "artifact_id": f"art-{prefix}-2",
        },
    ]


def test_v10_12_certification_index_counts_certified_and_review_items(tmp_path):
    persist_export_pack(
        _subject("subject-cert-index-1", "case-cert-index-1", "Certified Index Subject"),
        _evidence("cert-index-1"),
        analyst_reviewed=True,
        root=tmp_path,
        audit=True,
    )
    persist_export_pack(
        _subject("subject-cert-index-2", "case-cert-index-2", "Review Index Subject"),
        _evidence("cert-index-2"),
        analyst_reviewed=True,
        root=tmp_path,
        audit=False,
    )

    index = certification_index(root=tmp_path)
    summary = certification_index_summary(root=tmp_path)
    review = certification_index_review_items(root=tmp_path)

    assert index["schema"] == "socmint.dossier_export_certification_index.v10_12_0"
    assert index["status"] == "ready"
    assert index["export_count"] == 2
    assert index["certified_count"] == 1
    assert index["review_count"] == 1
    assert summary["ready_for_release"] is False
    assert review["status"] == "needs_review"
    assert review["review_count"] == 1


def test_v10_12_certification_index_ready_for_release_when_all_certified(tmp_path):
    persist_export_pack(
        _subject("subject-cert-index-ready", "case-cert-index-ready", "Ready Index Subject"),
        _evidence("cert-index-ready"),
        analyst_reviewed=True,
        root=tmp_path,
        audit=True,
    )

    summary = certification_index_summary(root=tmp_path)
    review = certification_index_review_items(root=tmp_path)

    assert summary["export_count"] == 1
    assert summary["certified_count"] == 1
    assert summary["review_count"] == 0
    assert summary["ready_for_release"] is True
    assert review["status"] == "clear"


def test_v10_12_certification_index_handles_empty_root(tmp_path):
    index = certification_index(root=tmp_path)
    summary = certification_index_summary(root=tmp_path)
    review = certification_index_review_items(root=tmp_path)

    assert index["export_count"] == 0
    assert summary["ready_for_release"] is False
    assert review["status"] == "clear"


def test_v10_12_certification_index_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-certification-index" in routes
    assert "/api/v1/dossier-builder/v3/export-certification-index/summary" in routes
    assert "/api/v1/dossier-builder/v3/export-certification-index/review" in routes
