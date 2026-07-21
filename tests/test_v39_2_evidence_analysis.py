from __future__ import annotations

import importlib

import pytest


def _modules(monkeypatch, tmp_path):
    db_path = tmp_path / "evidence-analysis.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    from src.socmint import database

    importlib.reload(database)
    from src.socmint import evidence_os, evidence_findings, evidence_analysis

    importlib.reload(evidence_os)
    importlib.reload(evidence_findings)
    importlib.reload(evidence_analysis)
    return evidence_os, evidence_findings, evidence_analysis


def _observation(evidence_os, *, case_id, evidence_key, observation_key, payload=b"record"):
    evidence = evidence_os.ingest_evidence(
        case_id=case_id,
        evidence_key=evidence_key,
        payload=payload,
        media_type="application/pdf",
        source_name="test",
        actor="tester",
    )["evidence"]
    return evidence, evidence_os.create_observation(
        case_id=case_id,
        evidence_item_id=evidence["id"],
        observation_key=observation_key,
        statement=f"Observation {observation_key}",
        classification="documented_fact",
        confidence=0.8,
        actor="analyst",
    )["observation"]


def test_observation_contradiction_link(monkeypatch, tmp_path):
    evidence_os, _, analysis = _modules(monkeypatch, tmp_path)
    _, first = _observation(evidence_os, case_id=46, evidence_key="E-1", observation_key="O-1", payload=b"one")
    _, second = _observation(evidence_os, case_id=46, evidence_key="E-2", observation_key="O-2", payload=b"two")

    link = analysis.link_observations(
        first["id"], second["id"], relationship="contradicts", actor="reviewer"
    )["relationship"]

    assert link["relationship"] == "contradicts"
    assert link["case_id"] == 46


def test_cross_case_observation_link_is_rejected(monkeypatch, tmp_path):
    evidence_os, _, analysis = _modules(monkeypatch, tmp_path)
    _, first = _observation(evidence_os, case_id=46, evidence_key="E-1", observation_key="O-1", payload=b"one")
    _, second = _observation(evidence_os, case_id=47, evidence_key="E-2", observation_key="O-2", payload=b"two")

    with pytest.raises(ValueError, match="cross-case"):
        analysis.link_observations(first["id"], second["id"], relationship="context")


def test_source_quality_changes_effective_confidence(monkeypatch, tmp_path):
    evidence_os, _, analysis = _modules(monkeypatch, tmp_path)
    evidence, observation = _observation(
        evidence_os, case_id=46, evidence_key="CITY-1", observation_key="O-1"
    )
    analysis.assess_source_quality(
        evidence["id"], source_class="official_record", actor="reviewer"
    )

    result = analysis.observation_effective_confidence(observation["id"])

    assert result["source_quality"] == 1.0
    assert result["effective_confidence"] == 0.8
    assert result["source_class"] == "official_record"


def test_claim_coverage_uses_only_approved_findings(monkeypatch, tmp_path):
    evidence_os, findings, analysis = _modules(monkeypatch, tmp_path)
    _, observation = _observation(
        evidence_os, case_id=46, evidence_key="CITY-1", observation_key="O-1"
    )
    evidence_os.review_observation(observation["id"], decision="approved", actor="reviewer")
    finding = findings.create_finding(
        case_id=46,
        finding_key="F-1",
        statement="Management received documented notice.",
        classification="documented_fact",
        observation_ids=[observation["id"]],
        actor="analyst",
    )["finding"]
    findings.link_finding_target(
        finding["id"], target_type="claim", target_key="HEATING-NOTICE", actor="analyst"
    )

    before = analysis.claim_proof_coverage(46, "HEATING-NOTICE")
    assert before["coverage_state"] == "unproven"

    findings.review_finding(finding["id"], decision="approved", actor="reviewer")
    after = analysis.claim_proof_coverage(46, "HEATING-NOTICE")

    assert after["coverage_state"] == "supported"
    assert after["approved_finding_count"] == 1
    assert after["approved_observation_count"] == 1
    assert after["distinct_source_count"] == 1


def test_invalid_source_quality_is_rejected(monkeypatch, tmp_path):
    evidence_os, _, analysis = _modules(monkeypatch, tmp_path)
    evidence, _ = _observation(evidence_os, case_id=46, evidence_key="E-1", observation_key="O-1")

    with pytest.raises(ValueError, match="invalid source class"):
        analysis.assess_source_quality(evidence["id"], source_class="rumour")
