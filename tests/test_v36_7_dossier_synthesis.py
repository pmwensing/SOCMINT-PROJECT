from __future__ import annotations

from src.socmint import database
from src.socmint import dossier_synthesis_v36_7 as synthesis


def _claim(claim_id: str, value: str):
    return {
        "claim_id": claim_id,
        "case_id": "case-a",
        "entity_id": "entity-a",
        "claim_type": "attribute",
        "normalized_value": value,
        "claim_event_sha256": claim_id.ljust(64, "a")[:64],
    }


def _verification(claim_id: str, band: str, score: int, conflicts=None):
    return {
        "claim_id": claim_id,
        "confidence_band": band,
        "support_score": score,
        "ranking": {"position": 1, "most_likely_supported": True},
        "source_ids": ["source-1"],
        "limitations": [],
        "unresolved_conflict_ids": conflicts or [],
        "claim_verification_assessment_sha256": claim_id.ljust(64, "b")[:64],
    }


def _configure(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'synthesis.db'}")
    claims = {
        "claim-1": _claim("claim-1", "Value A"),
        "claim-2": _claim("claim-2", "Value B"),
        "claim-3": _claim("claim-3", "Value C"),
    }
    verifications = {
        "claim-1": _verification("claim-1", "substantial", 75),
        "claim-2": _verification("claim-2", "moderate", 55),
        "claim-3": _verification("claim-3", "substantial", 70, ["conflict-1"]),
    }
    monkeypatch.setattr(
        synthesis,
        "_current_contributions",
        lambda: [
            {
                "claim_id": "claim-1",
                "decision": "approved",
                "target_dossier_section": "identity_summary",
                "dossier_contribution_id": "contribution-1",
                "dossier_contribution_sha256": "c" * 64,
            },
            {
                "claim_id": "claim-2",
                "decision": "approved",
                "target_dossier_section": "digital_presence",
                "dossier_contribution_id": "contribution-2",
                "dossier_contribution_sha256": "d" * 64,
            },
            {
                "claim_id": "claim-3",
                "decision": "approved",
                "target_dossier_section": "relationships",
                "dossier_contribution_id": "contribution-3",
                "dossier_contribution_sha256": "e" * 64,
            },
            {
                "claim_id": "claim-held",
                "decision": "held",
                "target_dossier_section": "identity_summary",
            },
        ],
    )
    monkeypatch.setattr(synthesis, "find_claim", lambda claim_id: claims.get(claim_id))
    monkeypatch.setattr(
        synthesis,
        "find_verification",
        lambda claim_id: verifications.get(claim_id),
    )
    monkeypatch.setattr(
        synthesis,
        "current_conflicts",
        lambda: [
            {
                "conflict_id": "conflict-1",
                "claim_a_id": "claim-3",
                "claim_b_id": "claim-other",
                "conflict_event_sha256": "f" * 64,
            }
        ],
    )
    monkeypatch.setattr(
        synthesis,
        "current_relationship_assessments",
        lambda: [
            {
                "claim_id": "claim-3",
                "relationship_timeline_assessment_id": "relationship-1",
                "relationship_timeline_assessment_sha256": "1" * 64,
            }
        ],
    )


def _create(**overrides):
    values = {
        "actor": "admin",
        "case_id": "case-a",
        "entity_id": "entity-a",
        "display_label": "Entity A",
        "purpose": "Authorized entity dossier synthesis.",
        "limitations": ["Snapshot is not an export."],
        "reason": "Create reproducible approved-contribution projection.",
        "confirmed": True,
    }
    values.update(overrides)
    return synthesis.create_dossier_synthesis_snapshot(**values)


def test_v36_7_synthesizes_only_approved_verified_contributions(
    monkeypatch,
    tmp_path,
):
    _configure(monkeypatch, tmp_path)
    result = _create()
    assert result["status"] == "dossier_synthesis_snapshot_created"
    assert result["snapshot_version"] == 1
    assert result["coverage"] == {
        "approved_contribution_count": 3,
        "section_count": 3,
        "substantial_count": 1,
        "moderate_count": 1,
        "disputed_count": 1,
    }
    assert result["categories"]["substantially_supported"] == ["claim-1"]
    assert result["categories"]["moderately_supported"] == ["claim-2"]
    assert result["categories"]["disputed"] == ["claim-3"]
    assert result["sections"]["relationships"][0][
        "relationship_assessment_ids"
    ] == ["relationship-1"]
    assert result["export_created"] is False
    assert result["published"] is False
    assert result["dossier_backend_mutated"] is False


def test_v36_7_snapshot_versions_and_chains_previous_hash(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    first = _create()
    second = _create(reason="Create a later reproducible projection.")
    assert first["snapshot_version"] == 1
    assert second["snapshot_version"] == 2
    assert second["previous_snapshot_id"] == first[
        "dossier_synthesis_snapshot_id"
    ]
    assert second["previous_snapshot_sha256"] == first[
        "dossier_synthesis_snapshot_sha256"
    ]
    assert synthesis.latest_snapshot("case-a", "entity-a")[
        "snapshot_version"
    ] == 2


def test_v36_7_requires_approved_verified_contribution(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setattr(
        synthesis,
        "_current_contributions",
        lambda: [{"claim_id": "claim-1", "decision": "held"}],
    )
    result = _create()
    assert result["blockers"] == [
        {"key": "approved_verified_dossier_contribution_required"}
    ]


def test_v36_7_manifest_binds_claim_verification_contribution_and_relationship(
    monkeypatch,
    tmp_path,
):
    _configure(monkeypatch, tmp_path)
    result = _create()
    manifest = {
        item["claim_id"]: item for item in result["integrity_manifest"]
    }
    assert manifest["claim-1"]["claim_event_sha256"]
    assert manifest["claim-1"]["verification_sha256"]
    assert manifest["claim-1"]["contribution_event_sha256"] == "c" * 64
    assert manifest["claim-3"]["relationship_assessment_sha256"] == [
        "1" * 64
    ]
    assert result["integrity_manifest_sha256"]
