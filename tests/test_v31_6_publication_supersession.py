from src.socmint import publication_supersession_v31_6 as supersession


PREDECESSOR = {
    "published_revision_id": "published-dossier-revision-1",
    "published_revision_sha256": "revision-sha-1",
    "case_id": "case-1",
}
SUCCESSOR = {
    "published_revision_id": "published-dossier-revision-2",
    "published_revision_sha256": "revision-sha-2",
    "case_id": "case-1",
}


def test_v31_6_requires_same_case_revisions(monkeypatch):
    other = {**SUCCESSOR, "case_id": "case-2"}
    monkeypatch.setattr(
        supersession,
        "find_published_revision",
        lambda revision_id: PREDECESSOR if revision_id.endswith("1") else other,
    )

    result = supersession.record_publication_supersession(
        actor="admin",
        predecessor_revision_id="published-dossier-revision-1",
        successor_revision_id="published-dossier-revision-2",
        reason="corrected publication",
        note="new version",
        confirmed=True,
    )

    assert result["status"] == "blocked"
    assert result["blockers"][0]["key"] == "same_case_revision_history_required"


def test_v31_6_records_append_only_supersession(monkeypatch):
    monkeypatch.setattr(
        supersession,
        "find_published_revision",
        lambda revision_id: PREDECESSOR if revision_id.endswith("1") else SUCCESSOR,
    )
    monkeypatch.setattr(supersession, "supersession_history", lambda: [])
    monkeypatch.setattr(
        supersession,
        "_record",
        lambda actor, target_value, event, ip_address: {**event, "actor": actor},
    )

    result = supersession.record_publication_supersession(
        actor="admin",
        predecessor_revision_id="published-dossier-revision-1",
        successor_revision_id="published-dossier-revision-2",
        reason="corrected publication",
        note="new version",
        confirmed=True,
    )

    assert result["status"] == "supersession_recorded"
    assert result["predecessor_revision_id"] == "published-dossier-revision-1"
    assert result["successor_revision_id"] == "published-dossier-revision-2"
    assert result["predecessor_mutated"] is False
    assert result["successor_mutated"] is False
    assert result["published_history_deleted"] is False


def test_v31_6_history_marks_active_and_superseded(monkeypatch):
    monkeypatch.setattr(
        supersession,
        "current_published_revisions",
        lambda: [PREDECESSOR, SUCCESSOR],
    )
    monkeypatch.setattr(
        supersession,
        "supersession_history",
        lambda: [
            {
                "predecessor_revision_id": "published-dossier-revision-1",
                "successor_revision_id": "published-dossier-revision-2",
            }
        ],
    )

    result = supersession.revision_history_for_case("case-1")
    by_id = {item["published_revision_id"]: item for item in result["revisions"]}

    assert by_id["published-dossier-revision-1"]["revision_status"] == "superseded"
    assert by_id["published-dossier-revision-2"]["revision_status"] == "active"
    assert result["active_revision_ids"] == ["published-dossier-revision-2"]
