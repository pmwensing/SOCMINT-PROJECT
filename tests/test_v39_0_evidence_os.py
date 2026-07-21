from __future__ import annotations

import importlib

import pytest


def _configure_tmp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "evidence-os.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    from src.socmint import database

    importlib.reload(database)
    from src.socmint import evidence_os

    importlib.reload(evidence_os)
    return database, evidence_os


def test_evidence_ingest_is_hash_deduplicated(monkeypatch, tmp_path):
    _, evidence_os = _configure_tmp_db(monkeypatch, tmp_path)

    first = evidence_os.ingest_evidence(
        case_id=46,
        evidence_key="PF-GMAIL-001",
        payload=b"tenant notified management about heating",
        media_type="message/rfc822",
        source_name="gmail",
        actor="tester",
    )
    duplicate = evidence_os.ingest_evidence(
        case_id=46,
        evidence_key="ANOTHER-KEY",
        payload=b"tenant notified management about heating",
        media_type="message/rfc822",
        source_name="gmail",
        actor="tester",
    )

    assert first["created"] is True
    assert duplicate["created"] is False
    assert first["evidence"]["sha256"] == duplicate["evidence"]["sha256"]


def test_observation_requires_human_review(monkeypatch, tmp_path):
    _, evidence_os = _configure_tmp_db(monkeypatch, tmp_path)
    evidence = evidence_os.ingest_evidence(
        case_id=46,
        evidence_key="PF-CITY-001",
        payload=b"official order",
        media_type="application/pdf",
        source_name="city_records",
        actor="tester",
    )["evidence"]

    observation = evidence_os.create_observation(
        case_id=46,
        evidence_item_id=evidence["id"],
        observation_key="OBS-0001",
        statement="The record contains an order with a compliance deadline.",
        classification="documented_fact",
        confidence=0.95,
        actor="analyst",
    )["observation"]

    assert observation["status"] == "proposed"

    reviewed = evidence_os.review_observation(
        observation["id"], decision="approved", actor="reviewer"
    )["observation"]
    assert reviewed["status"] == "approved"


def test_confidence_is_bounded(monkeypatch, tmp_path):
    _, evidence_os = _configure_tmp_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        evidence_os.create_observation(
            case_id=46,
            evidence_item_id=1,
            observation_key="OBS-BAD",
            statement="invalid",
            confidence=1.1,
        )
