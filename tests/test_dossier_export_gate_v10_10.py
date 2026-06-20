from pathlib import Path

from src.socmint.dossier_export_gate import export_gate_decision
from src.socmint.dossier_export_gate import export_gate_report
from src.socmint.dossier_export_gate import export_gate_summary
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.wsgi import app


def _subject():
    return {
        "subject_id": "subject-gate-1010",
        "display_name": "Gate Export Subject",
        "case_id": "case-gate-1010",
        "aliases": ["gate-export"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-gate-1",
            "label": "gated profile artifact",
            "source": "public_profile",
            "confidence": 0.96,
            "artifact_id": "art-gate-1",
        },
        {
            "evidence_id": "ev-gate-2",
            "label": "gated registry artifact",
            "source": "public_registry",
            "confidence": 0.92,
            "artifact_id": "art-gate-2",
        },
    ]


def test_v10_10_gate_allows_when_verification_passes(tmp_path):
    persist_export_pack(
        _subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=True
    )
    report = export_gate_report("subject-gate-1010", "case-gate-1010", root=tmp_path)
    summary = export_gate_summary("subject-gate-1010", "case-gate-1010", root=tmp_path)
    decision = export_gate_decision(
        "subject-gate-1010", "case-gate-1010", root=tmp_path
    )

    assert report["schema"] == "socmint.dossier_export_gate.v10_10_0"
    assert report["status"] == "ready"
    assert report["ready"] is True
    assert report["blockers"] == []
    assert summary["status"] == "ready"
    assert decision["decision"] == "allow"


def test_v10_10_gate_blocks_missing_audit_coverage(tmp_path):
    persist_export_pack(
        _subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False
    )
    report = export_gate_report("subject-gate-1010", "case-gate-1010", root=tmp_path)
    decision = export_gate_decision(
        "subject-gate-1010", "case-gate-1010", root=tmp_path
    )

    assert report["status"] == "blocked"
    assert report["ready"] is False
    assert "audit_coverage" in report["blockers"]
    assert decision["decision"] == "deny"


def test_v10_10_gate_blocks_hash_mismatch(tmp_path):
    persisted = persist_export_pack(
        _subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=True
    )
    Path(persisted["artifacts"][0]["path"]).write_text("tampered", encoding="utf-8")
    report = export_gate_report("subject-gate-1010", "case-gate-1010", root=tmp_path)

    assert report["status"] == "blocked"
    assert "artifact_hashes" in report["blockers"]


def test_v10_10_gate_blocks_missing_export(tmp_path):
    report = export_gate_report("missing-subject", "missing-case", root=tmp_path)
    summary = export_gate_summary("missing-subject", "missing-case", root=tmp_path)

    assert report["status"] == "blocked"
    assert report["ready"] is False
    assert summary["status"] == "blocked"
    assert summary["passed_checks"] < summary["total_checks"]


def test_v10_10_gate_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>" in routes
    assert (
        "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/summary"
        in routes
    )
    assert (
        "/api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/decision"
        in routes
    )
