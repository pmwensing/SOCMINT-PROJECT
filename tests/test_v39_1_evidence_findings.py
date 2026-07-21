from __future__ import annotations

import importlib

import pytest


def _configure_tmp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "evidence-findings.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))
    from src.socmint import database

    importlib.reload(database)
    from src.socmint import evidence_os, evidence_findings

    importlib.reload(evidence_os)
    importlib.reload(evidence_findings)
    return evidence_os, evidence_findings


def _observation(evidence_os, *, case_id=46, key="OBS-1"):
    evidence = evidence_os.ingest_evidence(
        case_id=case_id,
        evidence_key=f"E-{key}",
        payload=f"source-{case_id}-{key}".encode(),
        media_type="text/plain",
        source_name="test",
        actor="tester",
    )["evidence"]
    return evidence_os.create_observation(
        case_id=case_id,
        evidence_item_id=evidence["id"],
        observation_key=key,
        statement="The source records notice of the issue.",
        classification="documented_fact",
        confidence=0.9,
        actor="analyst",
    )["observation"]


def test_finding_cannot_be_approved_without_approved_support(monkeypatch, tmp_path):
    evidence_os, findings = _configure_tmp_db(monkeypatch, tmp_path)
    observation = _observation(evidence_os)
    finding = findings.create_finding(
        case_id=46,
        finding_key="FIND-1",
        statement="Management received notice.",
        classification="documented_fact",
        observation_ids=[observation["id"]],
        actor="analyst",
    )["finding"]

    assert finding["status"] == "proposed"
    with pytest.raises(ValueError, match="approved supporting observation"):
        findings.review_finding(finding["id"], decision="approved", actor="reviewer")


def test_approved_observation_allows_finding_approval_and_claim_link(monkeypatch, tmp_path):
    evidence_os, findings = _configure_tmp_db(monkeypatch, tmp_path)
    observation = _observation(evidence_os)
    evidence_os.review_observation(
        observation["id"], decision="approved", actor="reviewer"
    )
    finding = findings.create_finding(
        case_id=46,
        finding_key="FIND-2",
        statement="Management received notice.",
        classification="documented_fact",
        observation_ids=[observation["id"]],
        actor="analyst",
    )["finding"]

    approved = findings.review_finding(
        finding["id"], decision="approved", actor="senior-reviewer"
    )["finding"]
    link = findings.link_finding_target(
        finding["id"],
        target_type="claim",
        target_key="PF-T6-HEAT-01",
        relationship="supports",
        actor="analyst",
    )["target_link"]
    summary = findings.finding_summary(finding["id"])

    assert approved["status"] == "approved"
    assert approved["approved_by"] == "senior-reviewer"
    assert link["target_key"] == "PF-T6-HEAT-01"
    assert len(summary["observations"]) == 1
    assert len(summary["targets"]) == 1


def test_finding_rejects_cross_case_observation(monkeypatch, tmp_path):
    evidence_os, findings = _configure_tmp_db(monkeypatch, tmp_path)
    observation = _observation(evidence_os, case_id=99, key="OBS-X")

    with pytest.raises(ValueError, match="belong to the finding case"):
        findings.create_finding(
            case_id=46,
            finding_key="FIND-X",
            statement="Cross-case contamination must be rejected.",
            classification="reasonable_inference",
            observation_ids=[observation["id"]],
        )


def test_finding_requires_valid_classification_and_source(monkeypatch, tmp_path):
    _, findings = _configure_tmp_db(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="classification"):
        findings.create_finding(
            case_id=46,
            finding_key="FIND-BAD",
            statement="Invalid classification.",
            classification="truth",
            observation_ids=[1],
        )

    with pytest.raises(ValueError, match="at least one observation"):
        findings.create_finding(
            case_id=46,
            finding_key="FIND-NONE",
            statement="No source.",
            classification="unresolved_question",
            observation_ids=[],
        )
