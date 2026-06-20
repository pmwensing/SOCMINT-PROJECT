from src.socmint import database
from src.socmint import analytic_conflict_v30_3 as conflict


def _claim(claim_id: str, value: str):
    return {
        "claim_id": claim_id,
        "claim_state": "proposed",
        "case_id": "case-1",
        "entity_id": "entity-1",
        "claim_type": "location",
        "normalized_value": value,
        "claim_event_sha256": ("a" if claim_id.endswith("a") else "b") * 64,
    }


def test_v30_3_records_and_resolves_contradiction(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'conflicts.db'}")
    claims = {"claim-a": _claim("claim-a", "Kingston"), "claim-b": _claim("claim-b", "Ottawa")}
    monkeypatch.setattr(conflict, "find_claim", lambda claim_id: claims.get(claim_id))

    created = conflict.record_conflict(
        actor="analyst",
        conflict_type="contradiction",
        claim_a_id="claim-a",
        claim_b_id="claim-b",
        disagreement_basis="different normalized locations",
        reason="preserve conflicting claims",
        confirmed=True,
    )
    assert created["status"] == "analytic_conflict_recorded"
    assert created["resolution"] == "unresolved"
    assert created["claim_mutated"] is False

    resolved = conflict.resolve_conflict(
        actor="reviewer",
        conflict_id=created["conflict_id"],
        resolution="both_retained",
        reason="both sources remain material",
        confirmed=True,
    )
    assert resolved["status"] == "analytic_conflict_resolved"
    current = conflict.current_conflicts()[0]
    assert current["resolution"] == "both_retained"
    assert len(current["history"]) == 2


def test_v30_3_blocks_invalid_and_duplicate_conflicts(monkeypatch, tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    claims = {"claim-a": _claim("claim-a", "Kingston"), "claim-b": _claim("claim-b", "Ottawa")}
    monkeypatch.setattr(conflict, "find_claim", lambda claim_id: claims.get(claim_id))

    created = conflict.record_conflict(actor="analyst", conflict_type="contradiction", claim_a_id="claim-a", claim_b_id="claim-b", disagreement_basis="different values", reason="record", confirmed=True)
    duplicate = conflict.record_conflict(actor="analyst", conflict_type="contradiction", claim_a_id="claim-b", claim_b_id="claim-a", disagreement_basis="different values", reason="repeat", confirmed=True)
    assert created["status"] == "analytic_conflict_recorded"
    assert duplicate["status"] == "blocked"

    claims["claim-b"] = _claim("claim-b", "Kingston")
    same_value = conflict.record_conflict(actor="analyst", conflict_type="contradiction", claim_a_id="claim-a", claim_b_id="claim-b", disagreement_basis="none", reason="invalid", confirmed=True)
    assert same_value["status"] == "blocked"
    assert same_value["blockers"][0]["key"] == "distinct_claim_values_required"
