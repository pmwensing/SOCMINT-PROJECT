import pytest

from src.socmint.dossier_export_audit import audit_summary
from src.socmint.dossier_export_pack import build_export_pack
from src.socmint.dossier_export_pack import export_preflight
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.dossier_builder_v3 import build_dossier_payload


def _subject():
    return {
        "subject_id": "subject-policy-137",
        "display_name": "Policy Blocker Subject",
        "case_id": "case-policy-137",
        "aliases": ["policy-export"],
    }


def test_export_preflight_blocks_unreviewed_assertions():
    dossier = build_dossier_payload(
        _subject(),
        [
            {
                "evidence_id": "ev-policy-1",
                "claim_id": "claim-unreviewed",
                "source": "public_profile",
                "confidence": 0.95,
                "artifact_id": "art-policy-1",
                "review_state": "unreviewed",
            },
            {
                "evidence_id": "ev-policy-2",
                "claim_id": "claim-unreviewed",
                "source": "public_registry",
                "confidence": 0.91,
                "artifact_id": "art-policy-2",
                "review_state": "confirmed",
            },
        ],
        analyst_reviewed=True,
    )

    preflight = export_preflight(dossier)

    assert preflight["ready"] is False
    assert preflight["blockers"][0]["code"] == "unreviewed_assertions"


def test_export_preflight_blocks_single_source_claims():
    pack = build_export_pack(
        _subject(),
        [
            {
                "evidence_id": "ev-policy-1",
                "claim_id": "claim-single",
                "source": "public_profile",
                "confidence": 0.95,
                "artifact_id": "art-policy-1",
                "review_state": "confirmed",
            }
        ],
        analyst_reviewed=True,
    )

    assert pack["status"] == "needs_review"
    assert any(blocker["code"] == "single_source_claims" for blocker in pack["preflight"]["blockers"])


def test_export_preflight_blocks_contradictory_identity_claims():
    pack = build_export_pack(
        _subject(),
        [
            {
                "evidence_id": "ev-policy-1",
                "claim_id": "claim-conflict",
                "source": "public_profile",
                "confidence": 0.95,
                "artifact_id": "art-policy-1",
                "review_state": "confirmed",
                "status": "contradicted",
            },
            {
                "evidence_id": "ev-policy-2",
                "claim_id": "claim-conflict",
                "source": "public_registry",
                "confidence": 0.9,
                "artifact_id": "art-policy-2",
                "review_state": "confirmed",
            },
        ],
        analyst_reviewed=True,
    )

    assert pack["status"] == "needs_review"
    assert any(blocker["code"] == "contradictory_identity_claims" for blocker in pack["preflight"]["blockers"])


def test_export_scope_allow_and_block_decisions_are_audited(tmp_path):
    result = persist_export_pack(
        _subject(),
        [
            {"evidence_id": "ev-ok-1", "source": "public_profile", "confidence": 0.95, "artifact_id": "art-ok-1"},
            {"evidence_id": "ev-ok-2", "source": "public_registry", "confidence": 0.91, "artifact_id": "art-ok-2"},
        ],
        analyst_reviewed=True,
        root=tmp_path,
        audit=True,
        expected_subject_id="subject-policy-137",
        expected_case_id="case-policy-137",
    )
    with pytest.raises(ValueError, match="outside the requested case scope"):
        persist_export_pack(
            _subject(),
            [],
            analyst_reviewed=True,
            root=tmp_path,
            audit=True,
            expected_subject_id="subject-policy-137",
            expected_case_id="case-other",
        )

    allowed = audit_summary("case-policy-137", "subject-policy-137", root=tmp_path)
    blocked = audit_summary("case-other", "subject-policy-137", root=tmp_path)

    assert result["scope_audit_event"]["action"] == "export_scope_allowed"
    assert allowed["counts"]["export_scope_allowed"] == 1
    assert blocked["counts"]["export_scope_blocked"] == 1
