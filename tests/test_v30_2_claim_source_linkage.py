from src.socmint import database
from src.socmint import claim_source_linkage_v30_2 as linkage


def _accepted_artifact():
    return {
        "artifact_id": "artifact-1",
        "artifact_state": "accepted",
        "content_sha256": "a" * 64,
        "artifact_event_sha256": "b" * 64,
        "state_history": [
            {
                "artifact_event_id": "artifact-event-accepted",
                "artifact_event_sha256": "c" * 64,
                "to_state": "accepted",
            }
        ],
    }


def _observation():
    return {
        "observation_id": "observation-1",
        "artifact_id": "artifact-1",
        "observation_sha256": "d" * 64,
        "artifact_binding_sha256": "e" * 64,
    }


def test_v30_2_links_accepted_evidence_and_observation(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'linkage.db'}")
    monkeypatch.setattr(linkage, "find_claim", lambda claim_id: {
        "claim_id": claim_id,
        "claim_state": "proposed",
        "claim_event_sha256": "f" * 64,
        "case_id": "case-1",
        "entity_id": "entity-1",
    })
    monkeypatch.setattr(linkage, "current_artifacts", lambda: [_accepted_artifact()])
    monkeypatch.setattr(linkage, "observations", lambda: [_observation()])

    result = linkage.link_claim_sources(
        actor="analyst",
        claim_id="claim-1",
        artifact_ids=["artifact-1"],
        observation_ids=["observation-1"],
        reason="bind immutable analytic sources",
        confirmed=True,
    )

    assert result["status"] == "corroboration_claim_sources_linked"
    assert result["artifact_count"] == 1
    assert result["observation_count"] == 1
    assert result["evidence_mutated"] is False
    assert result["observation_mutated"] is False
    assert result["claim_mutated"] is False
    assert len(linkage.claim_linkages("claim-1")) == 1

    duplicate = linkage.link_claim_sources(
        actor="analyst",
        claim_id="claim-1",
        artifact_ids=["artifact-1"],
        observation_ids=["observation-1"],
        reason="repeat identical binding",
        confirmed=True,
    )
    assert duplicate["status"] == "blocked"
    assert duplicate["blockers"][0]["key"] == "claim_source_linkage_already_exists"


def test_v30_2_blocks_unaccepted_and_mismatched_sources(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    monkeypatch.setattr(linkage, "find_claim", lambda claim_id: {
        "claim_id": claim_id,
        "claim_state": "proposed",
        "claim_event_sha256": "f" * 64,
        "case_id": "case-2",
        "entity_id": "entity-2",
    })
    artifact = _accepted_artifact()
    artifact["artifact_state"] = "registered"
    monkeypatch.setattr(linkage, "current_artifacts", lambda: [artifact])
    monkeypatch.setattr(linkage, "observations", lambda: [_observation()])

    unaccepted = linkage.link_claim_sources(
        actor="analyst",
        claim_id="claim-2",
        artifact_ids=["artifact-1"],
        observation_ids=[],
        reason="attempt invalid linkage",
        confirmed=True,
    )
    assert unaccepted["status"] == "blocked"
    assert unaccepted["blockers"][0]["key"] == "accepted_evidence_artifact_required"

    artifact["artifact_state"] = "accepted"
    other_observation = _observation()
    other_observation["artifact_id"] = "artifact-2"
    monkeypatch.setattr(linkage, "observations", lambda: [other_observation])
    mismatch = linkage.link_claim_sources(
        actor="analyst",
        claim_id="claim-2",
        artifact_ids=["artifact-1"],
        observation_ids=["observation-1"],
        reason="attempt mismatched linkage",
        confirmed=True,
    )
    assert mismatch["status"] == "blocked"
    assert mismatch["blockers"][0]["key"] == "observation_artifact_binding_mismatch"
