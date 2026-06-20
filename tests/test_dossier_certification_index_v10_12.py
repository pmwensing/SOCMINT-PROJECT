from src.socmint.dossier_certification_index import certification_index
from src.socmint.dossier_certification_index import certification_index_entry
from src.socmint.dossier_certification_index import certification_index_markdown
from src.socmint.dossier_certification_index import certification_index_summary
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject(subject_id="subject-cert-index-1", case_id="case-cert-index-1012"):
    return {
        "subject_id": subject_id,
        "display_name": "Certification Index Subject",
        "case_id": case_id,
        "aliases": ["cert-index"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-cert-index-1",
            "label": "profile artifact",
            "source": "public_profile",
            "confidence": 0.97,
            "artifact_id": "art-cert-index-1",
        },
        {
            "evidence_id": "ev-cert-index-2",
            "label": "registry artifact",
            "source": "public_registry",
            "confidence": 0.94,
            "artifact_id": "art-cert-index-2",
        },
    ]


def test_v10_12_index_entry_reports_export_artifacts_verification_and_certification(
    tmp_path,
):
    persist_export_pack(
        _subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=True
    )

    entry = certification_index_entry(
        "case-cert-index-1012", "subject-cert-index-1", root=tmp_path
    )

    assert entry["schema"] == "socmint.dossier_certification_index.v10_12_0"
    assert entry["status"] == "ready"
    assert entry["manifest_status"] == "ready"
    assert entry["artifact_count"] == 2
    assert entry["hash_count"] == 2
    assert entry["missing_hash_count"] == 0
    assert entry["verification_status"] == "pass"
    assert entry["gate_decision"] == "allow"
    assert entry["certified"] is True
    assert entry["safe_to_distribute"] is True
    assert entry["distribution_decision"] == "allow"
    assert entry["audit_event_count"] >= 1
    assert entry["recommended_bundle"].endswith("manifest.json")


def test_v10_12_index_blocks_export_without_audit_coverage(tmp_path):
    persist_export_pack(
        _subject("subject-cert-index-no-audit"),
        _evidence(),
        analyst_reviewed=True,
        root=tmp_path,
        audit=False,
    )

    entry = certification_index_entry(
        "case-cert-index-1012", "subject-cert-index-no-audit", root=tmp_path
    )

    assert entry["certified"] is False
    assert entry["safe_to_distribute"] is False
    assert entry["distribution_decision"] == "hold"
    assert "audit_coverage" in entry["blockers"]
    assert entry["audit_event_count"] == 0
    assert entry["recommended_bundle"] is None


def test_v10_12_case_index_and_summary_count_safe_and_held_exports(tmp_path):
    persist_export_pack(
        _subject("subject-cert-index-safe"),
        _evidence(),
        analyst_reviewed=True,
        root=tmp_path,
        audit=True,
    )
    persist_export_pack(
        _subject("subject-cert-index-held"),
        _evidence(),
        analyst_reviewed=True,
        root=tmp_path,
        audit=False,
    )

    index = certification_index("case-cert-index-1012", root=tmp_path)
    summary = certification_index_summary("case-cert-index-1012", root=tmp_path)

    assert index["export_count"] == 2
    assert index["safe_to_distribute_count"] == 1
    assert index["hold_count"] == 1
    assert len(index["safe_to_distribute"]) == 1
    assert len(index["held"]) == 1
    assert summary["certified_count"] == 1
    assert summary["not_certified_count"] == 1
    assert summary["blocker_counts"]["audit_coverage"] == 1
    assert "subject-cert-index-safe" in summary["safe_subjects"]
    assert "subject-cert-index-held" in summary["held_subjects"]


def test_v10_12_missing_entry_is_held_with_manifest_blocker(tmp_path):
    entry = certification_index_entry(
        "case-missing-1012", "subject-missing-1012", root=tmp_path
    )

    assert entry["status"] == "missing"
    assert entry["safe_to_distribute"] is False
    assert entry["distribution_decision"] == "hold"
    assert entry["blockers"] == ["missing_export_manifest"]


def test_v10_12_markdown_contains_distribution_readiness_table(tmp_path):
    persist_export_pack(
        _subject("subject-cert-index-md"),
        _evidence(),
        analyst_reviewed=True,
        root=tmp_path,
        audit=True,
    )

    markdown = certification_index_markdown("case-cert-index-1012", root=tmp_path)

    assert "# Certification Index — case-cert-index-1012" in markdown
    assert "Certified / safe to distribute: 1" in markdown
    assert "Subject | Decision | Certified" in markdown
    assert "subject-cert-index-md" in markdown
    assert "allow" in markdown


def test_v10_12_certification_index_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/certification-index/<case_id>" in routes
    assert "/api/v1/dossier-builder/v3/certification-index/<case_id>/summary" in routes
    assert "/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown" in routes
    assert (
        "/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>"
        in routes
    )
