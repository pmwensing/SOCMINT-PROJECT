from src.socmint.dossier_export_gate import export_gate_decision
from src.socmint.dossier_export_pack import build_export_pack
from src.socmint.dossier_export_pack import export_pack_summary
from src.socmint.dossier_export_store import persist_export_pack


def test_export_pack_summary_surfaces_policy_blocker_details():
    pack = build_export_pack(
        {"subject_id": "subject-surface-138", "display_name": "Surface", "case_id": "case-surface-138"},
        [
            {
                "evidence_id": "ev-surface-1",
                "claim_id": "claim-surface",
                "source": "public_profile",
                "confidence": 0.95,
                "artifact_id": "art-surface-1",
                "review_state": "unreviewed",
            }
        ],
        analyst_reviewed=True,
    )

    summary = export_pack_summary(pack)

    assert summary["ready"] is False
    assert summary["blocker_count"] == 2
    assert set(summary["blocker_codes"]) == {"unreviewed_assertions", "single_source_claims"}
    assert summary["blockers"][0]["severity"] == "block"


def test_export_gate_decision_includes_verification_summary_for_operators(tmp_path):
    persist_export_pack(
        {"subject_id": "subject-surface-138", "display_name": "Surface", "case_id": "case-surface-138"},
        [
            {"evidence_id": "ev-ok-1", "source": "public_profile", "confidence": 0.95, "artifact_id": "art-ok-1"},
            {"evidence_id": "ev-ok-2", "source": "public_registry", "confidence": 0.91, "artifact_id": "art-ok-2"},
        ],
        analyst_reviewed=True,
        root=tmp_path,
        audit=False,
    )

    decision = export_gate_decision("subject-surface-138", "case-surface-138", root=tmp_path)

    assert decision["decision"] == "deny"
    assert "audit_coverage" in decision["blockers"]
    assert decision["verification_summary"]["checks"]["audit_coverage"] is False
