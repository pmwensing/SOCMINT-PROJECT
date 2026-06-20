from src.socmint import database
from src.socmint.corroboration_claim_v30_1 import change_claim_state, create_corroboration_claim, current_claims


def test_v30_1_creates_append_only_claim_and_withdraws(tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'claims.db'}")
    created = create_corroboration_claim(
        actor="analyst",
        case_id="case-1",
        entity_id="entity-1",
        claim_type="username",
        normalized_value="alice",
        purpose="identity assessment",
        source_refs=[{"source_type":"observation","source_id":"obs-1","source_sha256":"a" * 64}],
        reason="propose corroboration claim",
        confirmed=True,
    )
    assert created["status"] == "corroboration_claim_created"
    assert created["claim_state"] == "proposed"
    assert created["truth_assigned"] is False
    assert created["confidence_assigned"] is False
    assert created["dossier_mutated"] is False

    withdrawn = change_claim_state(
        actor="analyst",
        claim_id=created["claim_id"],
        to_state="withdrawn",
        reason="source requires reassessment",
        confirmed=True,
    )
    assert withdrawn["status"] == "corroboration_claim_state_changed"
    assert current_claims()[0]["claim_state"] == "withdrawn"
    assert len(current_claims()[0]["state_history"]) == 2


def test_v30_1_blocks_missing_sources_duplicates_and_invalid_state(tmp_path):
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    base = dict(
        actor="analyst", case_id="case-2", entity_id="entity-2",
        claim_type="location", normalized_value="Kingston",
        purpose="location assessment", reason="propose claim", confirmed=True,
    )
    blocked = create_corroboration_claim(**base, source_refs=[])
    assert blocked["status"] == "blocked"

    created = create_corroboration_claim(**base, source_refs=[{"source_type":"artifact","source_id":"artifact-2"}])
    duplicate = create_corroboration_claim(**base, source_refs=[{"source_type":"artifact","source_id":"artifact-2"}])
    assert created["status"] == "corroboration_claim_created"
    assert duplicate["status"] == "blocked"

    invalid = change_claim_state(actor="analyst", claim_id=created["claim_id"], to_state="approved", reason="not allowed here", confirmed=True)
    assert invalid["status"] == "blocked"
