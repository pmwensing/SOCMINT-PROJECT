from __future__ import annotations

from src.socmint import database
from src.socmint import source_independence_v36_4 as independence


def _source(source_id: str, content_hash: str, case_id: str = "case-a"):
    return {
        "source_id": source_id,
        "case_id": case_id,
        "source_event_sha256": source_id.ljust(64, "a")[:64],
        "capture_sha256": source_id.ljust(64, "b")[:64],
        "capture": {
            "content_sha256": content_hash,
            "canonical_url": f"https://{source_id}.example.test/record",
        },
    }


def _assess(monkeypatch, tmp_path, sources, **overrides):
    database.configure_database(f"sqlite:///{tmp_path / 'independence.db'}")
    monkeypatch.setattr(
        independence,
        "find_source",
        lambda source_id: sources.get(source_id),
    )
    values = {
        "actor": "admin",
        "case_id": "case-a",
        "source_ids": sorted(sources),
        "relationship": "independent",
        "signals": [
            {
                "signal_type": "independent_primary_capture",
                "reason": "Separately produced primary records.",
            }
        ],
        "limitations": [],
        "reason": "Assess source origin dependency.",
        "confirmed": True,
    }
    values.update(overrides)
    return independence.assess_source_independence(**values)


def test_v36_4_accepts_independent_primary_captures(monkeypatch, tmp_path):
    sources = {
        "source-a": _source("source-a", "a" * 64),
        "source-b": _source("source-b", "b" * 64),
    }
    result = _assess(monkeypatch, tmp_path, sources)
    assert result["status"] == "source_independence_assessed"
    assert result["relationship"] == "independent"
    assert result["independence_score"] == 100
    assert result["source_mutated"] is False
    assert result["truth_assigned"] is False
    current = independence.find_independence_group(
        result["independence_group_id"]
    )
    assert current is not None
    assert current["source_ids"] == ["source-a", "source-b"]


def test_v36_4_same_hash_cannot_be_independent(monkeypatch, tmp_path):
    sources = {
        "source-a": _source("source-a", "a" * 64),
        "source-b": _source("source-b", "a" * 64),
    }
    result = _assess(monkeypatch, tmp_path, sources)
    assert result["blockers"] == [
        {"key": "independent_relationship_conflicts_with_dependency_evidence"}
    ]


def test_v36_4_same_hash_creates_mirror_group(monkeypatch, tmp_path):
    sources = {
        "source-a": _source("source-a", "a" * 64),
        "source-b": _source("source-b", "a" * 64),
    }
    result = _assess(
        monkeypatch,
        tmp_path,
        sources,
        relationship="mirror",
        signals=[
            {
                "signal_type": "quoted_passage_overlap",
                "reason": "Matching reproduced passage.",
            }
        ],
    )
    assert result["status"] == "source_independence_assessed"
    assert result["relationship"] == "mirror"
    assert result["independence_score"] == 0
    assert any(
        item["signal_type"] == "exact_content_hash"
        for item in result["signals"]
    )


def test_v36_4_blocks_unproven_mirror_and_unproven_independence(
    monkeypatch,
    tmp_path,
):
    sources = {
        "source-a": _source("source-a", "a" * 64),
        "source-b": _source("source-b", "b" * 64),
    }
    mirror = _assess(
        monkeypatch,
        tmp_path,
        sources,
        relationship="mirror",
        signals=[
            {
                "signal_type": "quoted_passage_overlap",
                "reason": "Some similar text.",
            }
        ],
    )
    assert mirror["blockers"] == [
        {"key": "mirror_relationship_requires_matching_signal"}
    ]

    unproven = _assess(
        monkeypatch,
        tmp_path,
        sources,
        signals=[
            {
                "signal_type": "quoted_passage_overlap",
                "reason": "No independent origin proof.",
            }
        ],
    )
    assert unproven["blockers"] == [
        {"key": "independent_relationship_conflicts_with_dependency_evidence"}
    ]


def test_v36_4_requires_sources_from_same_case(monkeypatch, tmp_path):
    sources = {
        "source-a": _source("source-a", "a" * 64),
        "source-b": _source("source-b", "b" * 64, "case-other"),
    }
    result = _assess(monkeypatch, tmp_path, sources)
    assert result["blockers"] == [
        {"key": "source_independence_case_mismatch"}
    ]


def test_v36_4_duplicate_assessment_is_blocked(monkeypatch, tmp_path):
    sources = {
        "source-a": _source("source-a", "a" * 64),
        "source-b": _source("source-b", "b" * 64),
    }
    first = _assess(monkeypatch, tmp_path, sources)
    second = independence.assess_source_independence(
        actor="admin",
        case_id="case-a",
        source_ids=["source-a", "source-b"],
        relationship="independent",
        signals=[
            {
                "signal_type": "independent_primary_capture",
                "reason": "Separately produced primary records.",
            }
        ],
        limitations=[],
        reason="Assess source origin dependency.",
        confirmed=True,
    )
    assert first["status"] == "source_independence_assessed"
    assert second["blockers"] == [
        {"key": "source_independence_assessment_already_exists"}
    ]
