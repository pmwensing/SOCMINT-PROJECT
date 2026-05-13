from src.socmint.dossier_export_certification import artifact_digest_summary
from src.socmint.dossier_export_certification import export_certification_bundle
from src.socmint.dossier_export_certification import export_certification_statement
from src.socmint.dossier_export_certification import export_certification_summary
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject():
    return {
        "subject_id": "subject-cert-1011",
        "display_name": "Certified Export Subject",
        "case_id": "case-cert-1011",
        "aliases": ["cert-export"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-cert-1",
            "label": "certified profile artifact",
            "source": "public_profile",
            "confidence": 0.96,
            "artifact_id": "art-cert-1",
        },
        {
            "evidence_id": "ev-cert-2",
            "label": "certified registry artifact",
            "source": "public_registry",
            "confidence": 0.93,
            "artifact_id": "art-cert-2",
        },
    ]


def test_v10_11_artifact_digest_summary_lists_hashes(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=True)
    summary = artifact_digest_summary("subject-cert-1011", "case-cert-1011", root=tmp_path)

    assert summary["schema"] == "socmint.dossier_export_certification.v10_11_0"
    assert summary["status"] == "ready"
    assert summary["artifact_count"] == 2
    assert all(item["sha256"] for item in summary["artifacts"])


def test_v10_11_certification_bundle_certifies_when_gate_allows(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=True)
    bundle = export_certification_bundle("subject-cert-1011", "case-cert-1011", root=tmp_path)
    summary = export_certification_summary("subject-cert-1011", "case-cert-1011", root=tmp_path)
    statement = export_certification_statement("subject-cert-1011", "case-cert-1011", root=tmp_path)

    assert bundle["schema"] == "socmint.dossier_export_certification.v10_11_0"
    assert bundle["status"] == "certified"
    assert bundle["certified"] is True
    assert summary["certified"] is True
    assert summary["decision"] == "allow"
    assert statement["certified"] is True
    assert "certified" in statement["statement"]


def test_v10_11_certification_blocks_without_audit_coverage(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False)
    bundle = export_certification_bundle("subject-cert-1011", "case-cert-1011", root=tmp_path)
    summary = export_certification_summary("subject-cert-1011", "case-cert-1011", root=tmp_path)
    statement = export_certification_statement("subject-cert-1011", "case-cert-1011", root=tmp_path)

    assert bundle["status"] == "not_certified"
    assert bundle["certified"] is False
    assert summary["certified"] is False
    assert "audit_coverage" in summary["blockers"]
    assert statement["certified"] is False


def test_v10_11_certification_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/summary" in routes
    assert "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/statement" in routes
