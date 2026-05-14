from socmint.dossier_export_enforcement_v7_5 import attach_export_enforcement
from socmint.dossier_export_enforcement_v7_5 import evaluate_dossier_export
from socmint.entity_profile_intelligence import build_entity_profile_intelligence


def _failing_payload():
    return build_entity_profile_intelligence(
        {
            "subject_id": "sub-fail",
            "case_id": "case-1",
            "display_name": "Failing Subject",
            "attributes": [{"name": "location", "value": "Unbacked"}],
        },
        evidence=[],
        analyst_reviewed=False,
    )


def _passing_payload():
    return build_entity_profile_intelligence(
        {
            "subject_id": "sub-pass",
            "case_id": "case-1",
            "display_name": "Passing Subject",
        },
        evidence=[
            {
                "evidence_id": "ev-1",
                "source": "public_profile",
                "platform": "example",
                "handle": "passing",
                "confidence": 0.91,
            }
        ],
        analyst_reviewed=True,
    )


def test_final_export_blocks_failed_quality_gate():
    payload = _failing_payload()
    decision = evaluate_dossier_export(payload, mode="final")

    assert payload["quality_gate"]["status"] == "fail"
    assert decision["allowed"] is False
    assert decision["status"] == "blocked"
    assert decision["final_export_blocked"] is True
    assert decision["quality_finding_count"] >= 1


def test_draft_export_allows_failed_quality_gate_for_review():
    payload = _failing_payload()
    decision = evaluate_dossier_export(payload, mode="draft")

    assert decision["allowed"] is True
    assert decision["status"] == "allowed"
    assert decision["mode"] == "draft"
    assert decision["quality_status"] == "fail"


def test_preview_export_allows_failed_quality_gate_for_review():
    payload = _failing_payload()
    decision = evaluate_dossier_export(payload, mode="preview")

    assert decision["allowed"] is True
    assert decision["status"] == "allowed"
    assert decision["mode"] == "preview"


def test_final_export_allows_passing_quality_gate():
    payload = _passing_payload()
    decision = evaluate_dossier_export(payload, mode="final")

    assert payload["quality_gate"]["status"] == "pass"
    assert decision["allowed"] is True
    assert decision["status"] == "allowed"
    assert decision["final_export_blocked"] is False


def test_attach_export_enforcement_adds_decision_block():
    payload = _passing_payload()
    enriched = attach_export_enforcement(payload, mode="final")

    assert enriched["export_enforcement"]["schema"] == "socmint.v7_5.dossier_export_enforcement"
    assert enriched["final_export_allowed"] is True
