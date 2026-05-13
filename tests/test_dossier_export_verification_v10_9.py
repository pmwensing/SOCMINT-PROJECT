from pathlib import Path

from src.socmint.dossier_export_audit import audit_event
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.dossier_export_verification import export_verification_report
from src.socmint.dossier_export_verification import export_verification_summary
from src.socmint.dossier_export_verification import verify_artifact_hashes
from src.socmint.dossier_export_verification import verify_audit_coverage
from src.socmint.dossier_export_verification import verify_manifest_index
from src.socmint.wsgi import app


def _subject():
    return {
        "subject_id": "subject-verify-109",
        "display_name": "Verify Export Subject",
        "case_id": "case-verify-109",
        "aliases": ["verify-export"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-verify-1",
            "label": "verified profile artifact",
            "source": "public_profile",
            "confidence": 0.96,
            "artifact_id": "art-verify-1",
        },
        {
            "evidence_id": "ev-verify-2",
            "label": "verified registry artifact",
            "source": "public_registry",
            "confidence": 0.91,
            "artifact_id": "art-verify-2",
        },
    ]


def test_v10_9_artifact_hashes_pass_for_persisted_export(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False)
    report = verify_artifact_hashes("subject-verify-109", "case-verify-109", root=tmp_path)

    assert report["schema"] == "socmint.dossier_export_verification.v10_9_0"
    assert report["status"] == "pass"
    assert report["artifact_count"] == 2
    assert all(item["match"] for item in report["checks"])


def test_v10_9_artifact_hashes_detect_tampering(tmp_path):
    persisted = persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False)
    Path(persisted["artifacts"][0]["path"]).write_text("tampered", encoding="utf-8")
    report = verify_artifact_hashes("subject-verify-109", "case-verify-109", root=tmp_path)

    assert report["status"] == "needs_review"
    assert any(item["status"] == "hash_mismatch" for item in report["checks"])


def test_v10_9_manifest_index_passes_for_persisted_export(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False)
    report = verify_manifest_index("subject-verify-109", "case-verify-109", root=tmp_path)

    assert report["schema"] == "socmint.dossier_export_verification.v10_9_0"
    assert report["status"] == "pass"
    assert all(report["checks"].values())


def test_v10_9_audit_coverage_requires_export_created_event(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False)
    missing = verify_audit_coverage("subject-verify-109", "case-verify-109", root=tmp_path)
    audit_event("export_created", "case-verify-109", "subject-verify-109", root=tmp_path)
    present = verify_audit_coverage("subject-verify-109", "case-verify-109", root=tmp_path)

    assert missing["status"] == "needs_review"
    assert present["status"] == "pass"


def test_v10_9_full_verification_report_and_summary_pass(tmp_path):
    persist_export_pack(_subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=True)
    report = export_verification_report("subject-verify-109", "case-verify-109", root=tmp_path)
    summary = export_verification_summary("subject-verify-109", "case-verify-109", root=tmp_path)

    assert report["schema"] == "socmint.dossier_export_verification.v10_9_0"
    assert report["status"] == "pass"
    assert summary["status"] == "pass"
    assert summary["passed_checks"] == summary["total_checks"]


def test_v10_9_verification_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>" in routes
    assert "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/summary" in routes
    assert "/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/hashes" in routes
