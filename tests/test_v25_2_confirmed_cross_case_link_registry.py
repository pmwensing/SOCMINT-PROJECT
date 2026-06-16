from src.socmint import database
from src.socmint import cross_case_confirmed_link_registry_v25_2 as service


def _accepted_review(decision="accept"):
    return {
        "schema": "socmint.cross_case_correlation_review.v25_1",
        "version": "v25.1.0",
        "correlation_id": "cross-case-entity-abc",
        "category": "entity",
        "decision": decision,
        "reason": "Analyst confirmed matching source occurrences.",
        "reviewer": "reviewer-one",
        "review_decision_id": "correlation-review-accepted-1",
        "review_decision_sha256": "d" * 64,
        "candidate_sha256": "c" * 64,
        "action_record_id": 11,
        "recorded_at": "2026-06-16T05:00:00+00:00",
        "workspace_access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-alpha", "case-bravo"],
        },
        "candidate_snapshot": {
            "correlation_id": "cross-case-entity-abc",
            "category": "entity",
            "match_value": "entity-42",
            "display_values": ["entity-42", "ENTITY-42"],
            "case_ids": ["case-alpha", "case-bravo"],
            "case_count": 2,
            "occurrence_count": 2,
            "occurrences": [
                {
                    "case_id": "case-alpha",
                    "record_id": 1,
                    "source_action": "case_entity_observed",
                    "field_path": "entity_id",
                    "actor": "analyst-a",
                    "occurred_at": "2026-06-16T02:00:00+00:00",
                    "display_value": "entity-42",
                    "provenance_sha256": "a" * 64,
                },
                {
                    "case_id": "case-bravo",
                    "record_id": 2,
                    "source_action": "case_entity_observed",
                    "field_path": "entity_id",
                    "actor": "analyst-b",
                    "occurred_at": "2026-06-16T03:00:00+00:00",
                    "display_value": "ENTITY-42",
                    "provenance_sha256": "b" * 64,
                },
            ],
            "human_review_required": True,
            "confirmed_match": False,
        },
    }


def _setup(tmp_path, monkeypatch, review=None):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)
    monkeypatch.setattr(
        service,
        "latest_correlation_review",
        lambda correlation_id: review,
    )


def test_v25_2_materializes_only_accepted_review_and_preserves_occurrences(tmp_path, monkeypatch):
    review = _accepted_review()
    _setup(tmp_path, monkeypatch, review)

    result = service.register_confirmed_cross_case_link(
        "cross-case-entity-abc",
        registered_by="registry-manager",
        confirmed=True,
        allowed_case_ids={"case-alpha", "case-bravo"},
        note="Approved for confirmed-link registry.",
    )

    assert result["status"] == "confirmed_link_registered"
    assert result["link_status"] == "confirmed"
    assert result["accepted_review_decision_id"] == review["review_decision_id"]
    assert result["accepted_review_decision_sha256"] == review["review_decision_sha256"]
    assert result["accepted_review"]["action_record_id"] == 11
    assert result["source_occurrence_count"] == 2
    assert [item["case_id"] for item in result["source_occurrences"]] == [
        "case-alpha", "case-bravo"
    ]
    assert len(result["source_occurrences_sha256"]) == 64
    assert len(result["confirmed_link_sha256"]) == 64
    assert result["source_occurrences_preserved"] is True
    assert result["source_records_mutated"] is False
    assert result["review_history_mutated"] is False
    assert result["candidate_mutated"] is False

    registry = service.confirmed_link_registry(
        allowed_case_ids={"case-alpha", "case-bravo"}
    )
    assert len(registry) == 1
    assert registry[0]["confirmed_link_id"] == result["confirmed_link_id"]
    assert registry[0]["registry_record_id"] == result["registry_record_id"]

    duplicate = service.register_confirmed_cross_case_link(
        "cross-case-entity-abc",
        registered_by="registry-manager",
        confirmed=True,
        allowed_case_ids={"case-alpha", "case-bravo"},
    )
    assert duplicate["status"] == "confirmed_link_already_registered"
    assert duplicate["duplicate"] is True
    assert duplicate["registry_record_id"] == result["registry_record_id"]


def test_v25_2_blocks_unreviewed_nonaccepted_and_inaccessible_candidates(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, None)
    unreviewed = service.register_confirmed_cross_case_link(
        "candidate", registered_by="manager", confirmed=True
    )
    assert unreviewed["blockers"][0]["key"] == "accepted_correlation_review_required"

    for decision in ("reject", "defer", "split"):
        monkeypatch.setattr(
            service,
            "latest_correlation_review",
            lambda correlation_id, value=decision: _accepted_review(value),
        )
        blocked = service.register_confirmed_cross_case_link(
            "candidate", registered_by="manager", confirmed=True
        )
        assert blocked["blockers"][0]["key"] == "latest_correlation_review_must_be_accept"

    monkeypatch.setattr(
        service,
        "latest_correlation_review",
        lambda correlation_id: _accepted_review(),
    )
    denied = service.register_confirmed_cross_case_link(
        "candidate",
        registered_by="manager",
        confirmed=True,
        allowed_case_ids={"case-alpha"},
    )
    assert denied["blockers"][0]["key"] == "confirmed_link_case_access_required"

    no_confirmation = service.register_confirmed_cross_case_link(
        "candidate", registered_by="manager", confirmed=False
    )
    assert no_confirmation["blockers"][0]["key"] == "explicit_confirmed_link_registration_required"


def test_v25_2_workspace_retains_all_review_dispositions_and_pending_accepts(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, _accepted_review())
    histories = {
        "accepted": [_accepted_review("accept")],
        "rejected": [_accepted_review("reject")],
        "deferred": [_accepted_review("defer")],
        "split": [_accepted_review("split")],
    }
    for key, history in histories.items():
        history[0] = {**history[0], "correlation_id": key, "review_decision_id": f"review-{key}"}
        history[0]["candidate_snapshot"] = {
            **history[0]["candidate_snapshot"],
            "correlation_id": key,
        }
    monkeypatch.setattr(service, "_all_review_histories", lambda: histories)
    monkeypatch.setattr(service, "confirmed_link_registry", lambda **kwargs: [])

    result = service.build_confirmed_link_registry_workspace(
        allowed_case_ids={"case-alpha", "case-bravo"}
    )

    assert result["review_disposition_counts"] == {
        "accept": 1,
        "defer": 1,
        "reject": 1,
        "split": 1,
    }
    assert result["accepted_pending_count"] == 1
    assert result["accepted_pending_registration"][0]["correlation_id"] == "accepted"
    assert result["unreviewed_candidates_materialized"] is False
    assert result["rejected_deferred_split_history_retained"] is True
    assert result["registry_record_created_by_view"] is False
